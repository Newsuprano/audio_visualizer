from pathlib import Path
import queue
import math
import numpy as np
from sounddevice import WasapiSettings
import sounddevice as sd
from PyQt6.QtCore import QTimer, Qt, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen, QMouseEvent
from PyQt6.QtWidgets import (
    QWidget,
    QComboBox,
    QPushButton,
    QLabel,
    QSlider,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QSizePolicy,
    QFrame,
    QMenu,
    QStyleOptionSlider,
    QStyle
)

from .visualizer_canvas import VisualizerCanvas
from audio import open_audio_stream, process_live_chunk
from ui.template_dialog import TemplateDialog
from ui.popups import VolumePopup
from audio_player import AudioPlayer
import time

import pyaudiowpatch as pyaudio

audio_file_path = "src/audio/symphony.mp3"


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Custom Audio Visualizer Studio")
        self.resize(1100, 700)
        self.setMouseTracking(True)

        self.is_playing = True
        self.current_mode = "file"
        self.live_stream = None
        self.live_buffer = None
        self.audio_queue = queue.Queue()

        # --- ROOT CONTAINER & LAYOUT ---
        root_widget = QWidget(self)
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # --- 1. PARAMETER PANEL (Sidebar) ---
        self.sidebar = QFrame(root_widget)
        self.sidebar.setFixedWidth(280)
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.sidebar.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        
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
        self.hide_btn.clicked.connect(self.hide_sidebar)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.hide_btn)
        sidebar_layout.addLayout(header_layout)

        form_layout = QFormLayout()
        sidebar_layout.addLayout(form_layout)

        self.bars_slider = QSlider(Qt.Orientation.Horizontal)
        self.bars_slider.setRange(16, 128)
        self.bars_slider.setValue(64)
        self.bars_slider.valueChanged.connect(self.update_bar_count)
        self.bars_label = QLabel(str(64))
        form_layout.addRow("Bar Count:", self.bars_slider)
        form_layout.addRow("", self.bars_label)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(50, 300)
        self.radius_slider.setValue(120)
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.radius_label = QLabel(str(120))
        form_layout.addRow("Inner Radius:", self.radius_slider)
        form_layout.addRow("", self.radius_label)

        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setRange(50, 400)
        self.length_slider.setValue(180)
        self.length_slider.valueChanged.connect(self.update_max_length)
        self.length_label = QLabel(str(180))
        form_layout.addRow("Max Bar Height:", self.length_slider)
        form_layout.addRow("", self.length_label)

        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "Circular", "Linear", 
            "Symmetric Waveform", 
            "Equalizer Orbit", 
            "Dual Wave",
        ])
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        form_layout.addRow("Style:", self.style_combo)

        self.template_dialog = TemplateDialog(self)
        self.template_dialog.template_selected.connect(self.apply_template_selection)

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
        self.source_combo.currentTextChanged.connect(self.on_audio_source_changed)
        form_layout.addRow("Change mode :", self.source_combo)

        self.device_combo = QComboBox()
        self.device_combo.setStyleSheet(self.source_combo.styleSheet())
        
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 or dev['max_output_channels'] > 0:
                self.device_combo.addItem(f"[{i}] {dev['name']}", userData=i)
                
        self.device_combo.currentIndexChanged.connect(self.on_device_selected)
        form_layout.addRow("Select Device :", self.device_combo)
        self.device_combo.setVisible(True)

        # --- 2. VISUALIZER CANVAS ---
        self.canvas = VisualizerCanvas(root_widget)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.canvas)
        root_layout.addLayout(content_layout)

        # --- 3. BOTTOM MEDIA CONTROL BAR ---
        self.control_bar = QFrame(root_widget)
        self.control_bar.setFixedHeight(50)
        self.control_bar.setStyleSheet("background-color: #181818; border-top: 1px solid #282828;")
        bar_layout = QHBoxLayout(self.control_bar)
        bar_layout.setContentsMargins(15, 0, 15, 0)
        bar_layout.setSpacing(15)

        self.play_btn = QPushButton("⏸")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc0000; color: white; border-radius: 16px; font-weight: bold; border: none;
            }
            QPushButton:hover { background-color: #e60000; }
        """)
        self.play_btn.clicked.connect(self.toggle_play_pause)
        bar_layout.addWidget(self.play_btn)

        self.vol_btn = QPushButton("🔊")
        self.vol_btn.setFixedSize(30, 30)
        self.vol_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #cccccc; font-size: 16px; border: none; }
            QPushButton:hover { color: white; }
        """)
        
        self.vol_popup = VolumePopup(self)
        self.vol_popup.hide()
        self.vol_popup.slider.setValue(50)
        self.vol_popup.slider.valueChanged.connect(self.update_volume)
        
        self.vol_btn.enterEvent = self.show_volume_popup
        self.vol_btn.leaveEvent = self.check_hide_volume_popup
        bar_layout.addWidget(self.vol_btn)

        self.track_duration = 0.0
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        bar_layout.addWidget(self.time_label)

        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 1000)
        self.timeline_slider.setValue(0)
        self.timeline_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #444; height: 4px; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #cc0000; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #ff0000; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }
        """)
        
        self.timeline_slider.sliderMoved.connect(self.seek_timeline)
        self.timeline_slider.installEventFilter(self)
        bar_layout.addWidget(self.timeline_slider, stretch=1)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #cccccc; font-size: 16px; border: none; }
            QPushButton:hover { color: white; }
        """)
        bar_layout.addWidget(self.settings_btn)

        self.init_audio(audio_file_path)

        root_layout.addWidget(self.control_bar)
        self.setCentralWidget(root_widget)

        self.sidebar_visible = True

        self.trigger_btn = QPushButton("▶", self)
        self.trigger_btn.setFixedWidth(24)
        self.trigger_btn.setFixedHeight(80)
        self.trigger_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; color: #00ff96; border: 1px solid #444; border-top-right-radius: 4px; border-bottom-right-radius: 4px; }
            QPushButton:hover { background-color: #353535; border-color: #00ff96; }
        """)
        self.trigger_btn.hide()
        self.trigger_btn.clicked.connect(self.show_sidebar)

        # --- 4. PLAYBACK SYNC TIMER ---
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(16)
        self.playback_timer.timeout.connect(self.update_playback_progress)
        self.playback_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'trigger_btn'):
            y_pos = (self.height() - self.trigger_btn.height() - self.control_bar.height()) // 2
            self.trigger_btn.move(0, y_pos)

    def show_volume_popup(self, event):
        global_pos = self.vol_btn.mapToGlobal(QPoint(0, 0))
        x = global_pos.x() + (self.vol_btn.width() - self.vol_popup.width()) // 2
        y = global_pos.y() - self.vol_popup.height() - 5
        self.vol_popup.move(x, y)
        self.vol_popup.show()

    def check_hide_volume_popup(self, event):
        QTimer.singleShot(150, self._delayed_hide_check)

    def _delayed_hide_check(self):
        if hasattr(self, "vol_popup") and hasattr(self, "vol_btn"):
            is_over_popup = self.vol_popup.underMouse() or self.vol_popup.rect().contains(self.vol_popup.mapFromGlobal(self.cursor().pos()))
            is_over_btn = self.vol_btn.underMouse()
            if not is_over_popup and not is_over_btn:
                self.vol_popup.hide()

    def hide_sidebar(self):
        self.sidebar.setVisible(False)
        self.sidebar_visible = False
        self.trigger_btn.show()
        self.canvas.updateGeometry()
        self.canvas.update()

    def show_sidebar(self):
        self.trigger_btn.hide()
        self.sidebar.setVisible(True)
        self.sidebar_visible = True
        self.canvas.updateGeometry()
        self.canvas.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.sidebar_visible and event.pos().x() <= 25:
            self.trigger_btn.show()
        super().mouseMoveEvent(event)

    def toggle_play_pause(self):
        if not hasattr(self, "audio_player") or not self.audio_player.is_loaded:
            return

        if self.is_playing:
            self.audio_player.pause()
            self.play_btn.setText("▶")
            self.is_playing = False
        else:
            if self.current_time_sec >= self.track_duration:
                self.current_time_sec = 0.0
                self.audio_player.play(start_sec=0.0)
            else:
                self.audio_player.unpause()
            
            self.playback_start_wall_time = time.perf_counter()
            self.playback_start_audio_sec = self.current_time_sec

            self.play_btn.setText("⏸")
            self.is_playing = True

    def seek_timeline(self, position):
        if hasattr(self, "track_duration") and self.track_duration > 0:
            target_sec = (position / 1000.0) * self.track_duration
            self.current_time_sec = target_sec
            
            self.playback_start_wall_time = time.perf_counter()
            self.playback_start_audio_sec = target_sec
            
            if hasattr(self, "audio_player"):
                self.audio_player.seek(target_sec)
                if not self.is_playing:
                    self.audio_player.pause()
            
            self.time_label.setText(f"{self.format_time(target_sec)} / {self.format_time(self.track_duration)}")
            
            if hasattr(self.canvas, "seek_to_time") and hasattr(self, "audio_stream") and self.audio_stream is not None:
                self.canvas.seek_to_time(target_sec)
                amplitudes = self.audio_player.get_amplitudes_at_time(
                    target_sec,
                    chunk_size=self.canvas.chunk_size,
                    num_bins=self.canvas.num_bars,
                    audio_stream=self.audio_stream
                )
                self.canvas.push_amplitudes(amplitudes)

    def update_bar_count(self, value):
        self.canvas.num_bars = value
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

    def show_template_dialog(self):
        self.template_dialog.set_shape(self.canvas.visualizer_style)
        self.template_dialog.exec()

    def apply_template_selection(self, template_key):
        self.canvas.set_template(template_key)

    def format_time(self, seconds):
        if math.isnan(seconds) or seconds < 0:
            return "0:00"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    def init_audio(self, file_path):
        self.audio_player = AudioPlayer()
        success = self.audio_player.load_file(file_path)
        
        if success:
            self.track_duration = self.audio_player.get_duration()
            self.current_time_sec = 0.0

            self.audio_player.set_volume(50.0)
            
            self.audio_stream = open_audio_stream(file_path)
            self.canvas.set_audio_source(self.audio_stream)
            
            self.audio_player.play(start_sec=0.0)
            self.is_playing = True
            self.play_btn.setText("⏸")

            total_str = self.format_time(self.track_duration)
            self.time_label.setText(f"0:00 / {total_str}")

    def update_playback_progress(self):
        if not self.is_playing:
            return

        if self.current_mode in ["mic", "desktop"]:
            if hasattr(self, "audio_queue") and self.audio_queue is not None:
                try:
                    latest_chunk = None
                    while not self.audio_queue.empty():
                        latest_chunk = self.audio_queue.get_nowait()

                    if latest_chunk is not None and len(latest_chunk) > 0:
                        _, binned = process_live_chunk(
                            latest_chunk, 
                            sample_rate=44100, 
                            num_bins=self.canvas.num_bars,
                            gain=8.0
                        )

                        if binned is not None and len(binned) > 0:
                            if not hasattr(self, "previous_binned") or len(self.previous_binned) != len(binned):
                                self.previous_binned = binned
                            else:
                                binned = 0.4 * binned + 0.6 * self.previous_binned
                                self.previous_binned = binned

                            self.canvas.push_amplitudes(binned)
                            self.canvas.update()
                except Exception as e:
                    print(f"Live stream queue error: {e}")
            return

        if not hasattr(self, "audio_player") or not self.audio_player.is_loaded:
            return

        if not hasattr(self, "playback_start_wall_time"):
            self.playback_start_wall_time = time.perf_counter()
            self.playback_start_audio_sec = self.current_time_sec

        elapsed_real_time = time.perf_counter() - self.playback_start_wall_time
        current_sec = min(self.track_duration, self.playback_start_audio_sec + elapsed_real_time)

        self.current_time_sec = current_sec
        self.time_label.setText(f"{self.format_time(current_sec)} / {self.format_time(self.track_duration)}")
        
        if self.track_duration > 0 and not self.timeline_slider.isSliderDown():
            progress = int((current_sec / self.track_duration) * 1000)
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setValue(progress)
            self.timeline_slider.blockSignals(False)
        
        if hasattr(self, "audio_stream") and self.audio_stream is not None:
            amplitudes = self.audio_player.get_amplitudes_at_time(
                current_sec,
                chunk_size=self.canvas.chunk_size,
                num_bins=self.canvas.num_bars,
                audio_stream=self.audio_stream
            )
            self.canvas.push_amplitudes(amplitudes)
            self.canvas.update()

    def update_volume(self, value):
        if hasattr(self, "audio_player"):
            self.audio_player.set_volume(value)
            
        if value == 0:
            self.vol_btn.setText("🔇")
        elif value < 50:
            self.vol_btn.setText("🔉")
        else:
            self.vol_btn.setText("🔊")

    def eventFilter(self, obj, event):
        if obj == self.timeline_slider and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                opt = QStyleOptionSlider()
                self.timeline_slider.initStyleOption(opt)
                
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                
                style = self.timeline_slider.style()
                handle_rect = style.subControlRect(
                    QStyle.ComplexControl.CC_Slider, 
                    opt, 
                    QStyle.SubControl.SC_SliderHandle, 
                    self.timeline_slider
                )
                
                if handle_rect.contains(pos):
                    return super().eventFilter(obj, event)
                
                val = QStyle.sliderValueFromPosition(
                    self.timeline_slider.minimum(),
                    self.timeline_slider.maximum(),
                    pos.x(),
                    self.timeline_slider.width(),
                    opt.upsideDown
                )
                
                self.timeline_slider.setValue(val)
                self.seek_timeline(val)
                return True
                
        return super().eventFilter(obj, event)

    def stop_live_stream(self):
        if hasattr(self, 'live_stream') and self.live_stream is not None:
            try:
                self.live_stream.stop_stream()
                self.live_stream.close()
            except Exception:
                pass
            self.live_stream = None

    def toggle_audio_source_mode(self):
        pass

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

    def start_audio_stream(self, device_idx, channels, rate, is_loopback):
        self.stop_live_stream()

        self.audio_queue = queue.Queue()
        target_queue = self.audio_queue

        def pyaudio_callback(in_data, frame_count, time_info, status):
            audio_data = np.frombuffer(in_data, dtype=np.float32).copy()
            if channels > 1 and audio_data.size > 0:
                audio_data = audio_data[::channels]
            target_queue.put(audio_data)
            return (None, pyaudio.paContinue)

        try:
            self.live_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device_idx,
                frames_per_buffer=1024,
                stream_callback=pyaudio_callback
            )
            self.live_stream.start_stream()
            if hasattr(self, 'playback_timer'):
                self.playback_timer.start()
        except Exception as e:
            print(f"Stream start error on index {device_idx}: {e}")

    def setup_file_mode_ui(self, enabled: bool):
        has_play_btn = hasattr(self, "play_btn") and self.play_btn is not None
        has_slider = hasattr(self, "timeline_slider") and self.timeline_slider is not None

        if has_play_btn:
            self.play_btn.setEnabled(enabled)
        if has_slider:
            self.timeline_slider.setEnabled(enabled)

        if enabled:
            if has_play_btn:
                self.play_btn.setText("⏸")
            self.is_playing = True
        else:
            if hasattr(self, "audio_player") and self.audio_player.is_loaded:
                self.audio_player.pause()
            if has_play_btn:
                self.play_btn.setText("▶")
            self.is_playing = True