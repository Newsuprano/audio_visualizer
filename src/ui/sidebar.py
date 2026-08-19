from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QComboBox,
    QPushButton,
    QLabel,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QSizePolicy,
    QFrame,
    QSpinBox,
    QCheckBox,
)
from src.ui.template_dialog import TemplateDialog
import sounddevice as sd

import numpy as np
import pyaudiowpatch as pyaudio

class SidebarPanel(QFrame):
    # Signals to pass parameter changes back up to MainWindow/Canvas
    bar_width_changed = pyqtSignal(int)
    gap_size_changed = pyqtSignal(int)
    force_squares_changed = pyqtSignal(int)
    bar_count_changed = pyqtSignal(int)
    radius_changed = pyqtSignal(int)
    max_length_changed = pyqtSignal(int)
    style_changed = pyqtSignal(str)
    audio_source_changed = pyqtSignal(str)
    device_selected = pyqtSignal(int)
    position_changed = pyqtSignal(int, int)
    template_selected = pyqtSignal(str)
    hide_requested = pyqtSignal()

    def __init__(self, parent=None, initial_bar_width=10, initial_gap_size=4):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        # The main layout for this sidebar panel
        sidebar_layout = QVBoxLayout(self)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        
        header_layout = QHBoxLayout()
        title_label = QLabel("<b>Parameters</b>")
        title_label.setStyleSheet("font-size: 14px; color: #00ff96;")
        
        self.hide_btn = QPushButton("◀ Hide")
        self.hide_btn.setStyleSheet("""
            QPushButton {
                background-color: #333; color: white; border: none; 
                padding: 4px 8px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #444; }
        """)
        self.hide_btn.clicked.connect(self.hide_requested.emit)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.hide_btn)
        sidebar_layout.addLayout(header_layout)

        form_layout = QFormLayout()
        sidebar_layout.addLayout(form_layout)

        self.bars_slider = QSlider(Qt.Orientation.Horizontal)
        self.bars_slider.setRange(16, 256)
        self.bars_slider.setValue(64)
        self.bars_slider.valueChanged.connect(lambda v: self.bar_count_changed.emit(v))
        self.bars_label = QLabel(str(64))
        self.bars_slider.valueChanged.connect(lambda v: self.bars_label.setText(str(v)))
        form_layout.addRow("Bar Count:", self.bars_slider)
        form_layout.addRow("", self.bars_label)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(50, 300)
        self.radius_slider.setValue(120)
        self.radius_slider.valueChanged.connect(lambda v: self.radius_changed.emit(v))
        self.radius_label = QLabel(str(120))
        self.radius_slider.valueChanged.connect(lambda v: self.radius_label.setText(str(v)))
        form_layout.addRow("Inner Radius:", self.radius_slider)
        form_layout.addRow("", self.radius_label)

        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setRange(50, 400)
        self.length_slider.setValue(180)
        self.length_slider.valueChanged.connect(lambda v: self.max_length_changed.emit(v))
        self.length_label = QLabel(str(180))
        self.length_slider.valueChanged.connect(lambda v: self.length_label.setText(str(v)))
        form_layout.addRow("Max Bar Height:", self.length_slider)
        form_layout.addRow("", self.length_label)

        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "Circular", "Linear", 
            "Symmetric Waveform", 
            "Equalizer Orbit", 
            "Dual Wave",
        ])
        self.style_combo.currentTextChanged.connect(self.style_changed.emit)
        form_layout.addRow("Style:", self.style_combo)

        self.template_dialog = TemplateDialog(self)
        self.template_dialog.template_selected.connect(self.template_selected.emit)

        self.open_templates_btn = QPushButton("Templates Menu")
        self.open_templates_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 8px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #353535; border: 1px solid #00ff96; }
        """)
        self.open_templates_btn.clicked.connect(self.show_template_dialog)
        form_layout.addRow("Templates:", self.open_templates_btn)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["📁 Audio File", "🎙️ Microphone", "🖥️ Desktop Audio"])
        self.source_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d; color: #00ff96; border: 1px solid #444; 
                padding: 4px 8px; border-radius: 4px; font-weight: bold;
            }
            QComboBox:hover { background-color: #353535; border-color: #00ff96; }
            QComboBox::drop-down { border: 0px; }
        """)
        self.source_combo.currentTextChanged.connect(self.audio_source_changed.emit)
        form_layout.addRow("Change mode :", self.source_combo)

        self.device_combo = QComboBox()
        self.device_combo.setStyleSheet(self.source_combo.styleSheet())
        
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 or dev['max_output_channels'] > 0:
                    self.device_combo.addItem(f"[{i}] {dev['name']}", userData=i)
        except Exception:
            pass
                
        self.device_combo.currentIndexChanged.connect(self.device_selected.emit)
        form_layout.addRow("Select Device :", self.device_combo)
        self.device_combo.setVisible(True)

        # Create X and Y spin boxes for the sidebar
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-2000, 2000)
        self.spin_x.setValue(0)
        self.spin_x.valueChanged.connect(self._emit_position)

        self.spin_y = QSpinBox()
        self.spin_y.setRange(-2000, 2000)
        self.spin_y.setValue(0)
        self.spin_y.valueChanged.connect(self._emit_position)

        spin_stylesheet = """
            QSpinBox {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                padding-right: 4px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
            }
        """

        self.spin_x.setStyleSheet(spin_stylesheet)
        self.spin_y.setStyleSheet(spin_stylesheet)

        # Bar Width & Gap Size Controls
        self.spin_bar_width = QSpinBox()
        self.spin_bar_width.setRange(1, 50)
        self.spin_bar_width.setValue(initial_bar_width)
        self.spin_bar_width.valueChanged.connect(self.bar_width_changed.emit)
        self.spin_bar_width.setStyleSheet(spin_stylesheet)

        self.spin_gap_size = QSpinBox()
        self.spin_gap_size.setRange(0, 50)
        self.spin_gap_size.setValue(initial_gap_size)
        self.spin_gap_size.valueChanged.connect(self.gap_size_changed.emit)
        self.spin_gap_size.setStyleSheet(spin_stylesheet)

        # Pack X and Y position controls
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.spin_x)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.spin_y)
        form_layout.addRow("Position:", pos_layout)

        form_layout.addRow("Bar Width:", self.spin_bar_width)
        form_layout.addRow("Gap Size:", self.spin_gap_size)

        # Force Square Blocks Checkbox
        self.check_square_blocks = QCheckBox()
        self.check_square_blocks.setChecked(False)
        self.check_square_blocks.setStyleSheet("color: white;")
        self.check_square_blocks.stateChanged.connect(lambda state: self.force_squares_changed.emit(state))
        form_layout.addRow("Force Squares:", self.check_square_blocks)

    # ==========================================
    # VISIBILITY & LAYOUT MANAGEMENT METHODS
    # ==========================================

    # ==========================================
    # PARAMETER & VISUALIZER UPDATERS
    # ==========================================

    def update_bar_count(self, value):
        self.canvas.num_bars = value
        self.canvas.current_amplitudes = np.zeros(value)
        self.canvas.target_amplitudes = np.zeros(value)
        self.canvas.update()
        self.bars_label.setText(str(value))

    def update_radius(self, value):
        self.canvas.inner_radius = value
        self.radius_label.setText(str(value))

    def update_max_length(self, value):
        self.canvas.max_bar_length = value
        self.length_label.setText(str(value))

    def on_style_changed(self, text):
        style_map = {
            "Circular": "circular", 
            "Linear": "linear", 
            "Symmetric Waveform": "symmetric",
            "Equalizer Orbit": "orbit", 
            "Dual Wave": "dual_wave",
        }
        style_key = style_map.get(text, "circular")
        self.canvas.set_style(style_key)
        self.template_dialog.set_shape(style_key)

    def on_bar_width_changed(self, value):
        """Updates the canvas bar width and repaints live."""
        self.canvas.bar_width = value
        self.canvas.update()

    def on_gap_size_changed(self, value):
        """Updates the canvas gap size and repaints live."""
        self.canvas.gap_size = value
        self.canvas.update()

    def on_force_squares_changed(self, state):
        # state is 2 for checked, 0 for unchecked in PyQt6
        self.canvas.force_squares = (state == Qt.CheckState.Checked.value or state == 2)
        self.canvas.update()

    # ==========================================
    # TEMPLATE DIALOG HANDLERS
    # ==========================================

    def show_template_dialog(self):
        self.template_dialog.set_shape(self.canvas.visualizer_style)
        self.template_dialog.exec()
        
    def apply_template_selection(self, template_key):
        self.canvas.set_template(template_key)

    # ==========================================
    # AUDIO STREAMING & DEVICE HANDLERS
    # ==========================================

    def on_audio_source_changed(self, text):
        self.stop_live_stream()
        
        if not hasattr(self, 'pyaudio_instance') or self.pyaudio_instance is None:
            self.pyaudio_instance = pyaudio.PyAudio()

        is_desktop = "Desktop" in text
        is_mic = "Microphone" in text

        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        if not is_desktop and not is_mic:
            self.current_mode = "file"
            self.setup_file_mode_ui(enabled=True)
            self.device_combo.setVisible(False)
            self.device_combo.blockSignals(False)
            if hasattr(self, "audio_player") and self.audio_player.is_loaded:
                self.audio_player.unpause()
            return

        if is_desktop:
            self.current_mode = "desktop"
            self.setup_file_mode_ui(enabled=False)
            self.device_combo.setVisible(False)
            self.device_combo.blockSignals(False)

            try:
                wasapi_info = self.pyaudio_instance.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers = self.pyaudio_instance.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                
                target_loopback = None
                for loopback in self.pyaudio_instance.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        target_loopback = loopback
                        break
                
                if target_loopback is None:
                    target_loopback = self.pyaudio_instance.get_default_wasapi_loopback()

                device_idx = target_loopback['index']
                channels = int(target_loopback['maxInputChannels']) if int(target_loopback['maxInputChannels']) >= 1 else 2
                rate = int(target_loopback['defaultSampleRate']) if int(target_loopback['defaultSampleRate']) > 0 else 44100

                self.start_audio_stream(device_idx, channels, rate, is_loopback=True)
            except Exception as e:
                print(f"Failed to initialize explicit desktop loopback: {e}")

        elif is_mic:
            self.current_mode = "mic"
            self.setup_file_mode_ui(enabled=False)
            self.device_combo.setVisible(True)

            target_index = None
            try:
                device_count = self.pyaudio_instance.get_device_count()
                for i in range(device_count):
                    dev_info = self.pyaudio_instance.get_device_info_by_index(i)
                    dev_name = dev_info['name']
                    if "loopback" not in dev_name.lower() and dev_info['maxInputChannels'] > 0:
                        self.device_combo.addItem(f"[{i}] {dev_name}", userData=i)
                        if target_index is None:
                            target_index = i

                if target_index is not None:
                    for idx in range(self.device_combo.count()):
                        if self.device_combo.itemData(idx) == target_index:
                            self.device_combo.setCurrentIndex(idx)
                            break
            except Exception as e:
                print(f"Error enumerating microphones: {e}")

            self.device_combo.blockSignals(False)
            if self.device_combo.count() > 0:
                self.on_device_selected(self.device_combo.currentIndex())

    def on_device_selected(self, index):
        if index < 0:
            return

        current_mode_text = self.source_combo.currentText() if hasattr(self, 'source_combo') else ""
        if "Microphone" not in current_mode_text:
            return

        device_idx = self.device_combo.itemData(index)
        if device_idx is None:
            return

        try:
            dev_info = self.pyaudio_instance.get_device_info_by_index(device_idx)
            channels = min(2, max(1, int(dev_info['maxInputChannels'])))
            rate = int(dev_info['defaultSampleRate']) if int(dev_info['defaultSampleRate']) > 0 else 44100

            self.start_audio_stream(device_idx, channels, rate, is_loopback=False)
        except Exception as e:
            print(f"Failed to open microphone device {device_idx}: {e}")

    # ==========================================
    # POSITION & SPINBOX SYNCHRONIZATION
    # ==========================================

    def _emit_position(self):
        self.position_changed.emit(self.spin_x.value(), self.spin_y.value())

    def on_spinbox_position_changed(self):
        """Sends the typed values from the sidebar to the canvas, inverting Y so positive = up."""
        x = self.spin_x.value()
        # Invert the Y value sent to the canvas so positive values go up
        y = -self.spin_y.value()
        self.canvas.set_offset(x, y)

    def update_position_labels(self, x, y):
        # Temporarily block signals so setting the value programmatically doesn't re-trigger valueChanged
        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)
        
        self.spin_x.setValue(x)
        self.spin_y.setValue(y)
        
        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)

    def update_position_spinboxes(self, canvas_x, canvas_y):
        """Updates the sidebar numbers live during a drag without triggering infinite feedback loops."""
        target_y = -canvas_y  # Invert back so the sidebar shows positive/negative correctly

        # Block signals so setting the value doesn't accidentally trigger a re-entry loop
        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)

        if self.spin_x.value() != canvas_x:
            self.spin_x.setValue(canvas_x)
        if self.spin_y.value() != target_y:
            self.spin_y.setValue(target_y)

        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)