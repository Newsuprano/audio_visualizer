from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QRect, QPoint
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
    QScrollArea,
    QStackedWidget,
    QButtonGroup,
    QLineEdit,
    QFileDialog,
    QColorDialog,
    QInputDialog,
    QMessageBox
)
from PyQt6.QtGui import QIcon, QPixmap, QColor
from src.ui.template_dialog import TemplateDialog
from src.preset_manager.preset_manager import save_current_preset, apply_preset_to_ui, load_default_preset
import sounddevice as sd
import numpy as np

from assets import Icons

class CollapsibleSection(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        
        self.toggle_btn = QPushButton(f"▾  {title}")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                color: #00ff96;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 8px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
        """)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.clicked.connect(self.on_toggle)

        self.content_area = QWidget()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        main_layout.addWidget(self.toggle_btn)
        main_layout.addWidget(self.content_area)

    def on_toggle(self, checked):
        if checked:
            self.toggle_btn.setText(self.toggle_btn.text().replace("▸", "▾"))
            self.content_area.show()
        else:
            self.toggle_btn.setText(self.toggle_btn.text().replace("▾", "▸"))
            self.content_area.hide()


class SidebarPanel(QFrame):
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
    audio_file_selected = pyqtSignal(str)
    color_changed = pyqtSignal(object)
    color_mode_changed = pyqtSignal(str)
    cycle_speed_changed = pyqtSignal(int)
    glow_changed = pyqtSignal(int)
    glow_style_changed = pyqtSignal(str)
    glow_angle_changed = pyqtSignal(int)
    glow_distance_changed = pyqtSignal(int)
    glow_layers_changed = pyqtSignal(int)
    

    def __init__(self, parent=None, initial_bar_width=10, initial_gap_size=4):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==========================================
        # 1. LEFT ICON NAVIGATION STRIP
        # ==========================================
        icon_strip_container = QWidget(self)
        icon_strip_container.setFixedWidth(50)
        icon_strip_container.setStyleSheet("background-color: #141414; border-right: 1px solid #282828;")
        
        # Single layout directly on the container widget
        icon_layout = QVBoxLayout(icon_strip_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        # Initialize buttons
        self.btn_mode = self.create_icon_btn(Icons.HOME_48C, Icons.HOME_48F, "General Parameters")
        self.btn_control = self.create_icon_btn(Icons.TUNE_48, Icons.TUNE_48, "Visualizer Parameters")
        self.btn_presets = self.create_icon_btn(Icons.BOOKMARK_48C, Icons.BOOKMARK_48F, "Presect Selection")
        self.btn_color = self.create_icon_btn(Icons.PALETTE_48C, Icons.PALETTE_48F, "Color Grading")
        self.btn_templates = self.create_icon_btn(Icons.BROWSE_48C, Icons.BROWSE_48F, "Templates")
        self.btn_settings = self.create_icon_btn(Icons.SETTINGS_48C, Icons.SETTINGS_48F, "Settings")

        icon_layout.addWidget(self.btn_mode)
        icon_layout.addWidget(self.btn_control)
        icon_layout.addWidget(self.btn_presets)
        icon_layout.addWidget(self.btn_color)
        icon_layout.addWidget(self.btn_templates)
        icon_layout.addWidget(self.btn_settings)
        icon_layout.addStretch()

        self.hide_btn = QPushButton("◀")
        self.hide_btn.setFixedSize(36, 36)
        self.hide_btn.setStyleSheet("""
            QPushButton { background-color: #222; color: #aaa; border: none; border-radius: 4px; font-size: 14px; }
            QPushButton:hover { background-color: #333; color: white; }
        """)
        self.hide_btn.clicked.connect(self.hide_requested.emit)
        icon_layout.addWidget(self.hide_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addWidget(icon_strip_container)

        # Standalone indicator bar parented to the container
        self.active_indicator = QFrame(icon_strip_container)
        self.active_indicator.setFixedWidth(4)
        self.active_indicator.setFixedHeight(50)  # Matches button height perfectly
        self.active_indicator.setStyleSheet("background-color: #00a8ff; border-radius: 0px;")
        self.active_indicator.show()

        # Setup property animation for the indicator bar
        self.indicator_anim = QPropertyAnimation(self.active_indicator, b"geometry")
        self.indicator_anim.setDuration(200)
        self.indicator_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # ==========================================
        # 2. RIGHT CONTENT AREA (Stacked Categories)
        # ==========================================
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Build pages and dialogs first
        self.setup_general_page(initial_bar_width, initial_gap_size)       # Index 0: Audio Source
        self.setup_canvas_layout_page(initial_bar_width, initial_gap_size) # Index 1: Canvas Layout
        self.setup_presets_page() # Index 2: Presets
        self.setup_color_page() # Index 3: Visuals/Geometry

        self.current_template = "lines"

        self.template_dialog = TemplateDialog(self)
        self.template_dialog.template_selected.connect(self._on_template_selected)

        # Connect icon buttons after stack and widgets are fully created
        self.btn_mode.clicked.connect(lambda: self.switch_category(0))
        self.btn_control.clicked.connect(lambda: self.switch_category(1))
        self.btn_presets.clicked.connect(lambda: self.switch_category(2))
        self.btn_color.clicked.connect(lambda: self.switch_category(3))
        self.btn_templates.clicked.connect(self.show_template_dialog)
        self.btn_templates.clicked.connect(lambda: self.switch_category(4))
        self.btn_settings.clicked.connect(lambda: self.switch_category(5))

        # Set initial active state safely
        self.switch_category(0)

    def showEvent(self, event):
        super().showEvent(event)
        # Force a precise sync once the UI is fully visible and laid out
        self.switch_category(self.stack.currentIndex())

    def create_icon_btn(self, icon_path_normal, icon_path_selected, tooltip):
        btn = QPushButton()
        btn.setFixedSize(50, 50)  # Make it a 50x50 square block
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        
        icon = QIcon()
        icon.addPixmap(QPixmap(str(icon_path_normal)), QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(QPixmap(str(icon_path_selected)), QIcon.Mode.Normal, QIcon.State.On)
        
        btn.setIcon(icon)
        btn.setIconSize(QSize(22, 22))
        
        # Transparent background, no color changes
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0px;
            }
        """)
        return btn

    def wrap_in_scroll(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Kill the horizontal scrollbar entirely
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(widget)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        return scroll

    def setup_general_page(self, initial_bar_width, initial_gap_size):
        page = QWidget()
        page.setFixedWidth(270)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 1. Modern Segmented Control at the top
        segmented_control = self.create_segmented_audio_selector()
        layout.addWidget(segmented_control)

        # 2. Source Properties Collapsible Section
        source_section = CollapsibleSection("Source Properties")
        
        # We use a container widget inside the content area to easily swap parameters layout
        self.source_params_container = QWidget(source_section.content_area)
        self.source_params_layout = QVBoxLayout(self.source_params_container)
        self.source_params_layout.setContentsMargins(5, 5, 5, 5)

        # Build initial view (Audio File mode is checked by default)
        self._update_source_parameters_view(0)

        # Add container to collapsible section's form area
        section_main_layout = QVBoxLayout(source_section.content_area)
        section_main_layout.setContentsMargins(0, 0, 0, 0)
        section_main_layout.addWidget(self.source_params_container)

        layout.addWidget(source_section)
        layout.addStretch()
        self.stack.addWidget(self.wrap_in_scroll(page))

    def setup_canvas_layout_page(self, initial_bar_width, initial_gap_size):
        page = QWidget()
        page.setFixedWidth(270)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Canvas Layout Section
        pos_section = CollapsibleSection("Canvas Layout")
        pos_form = QFormLayout(pos_section.content_area)
        pos_form.setContentsMargins(5, 5, 5, 5)
        
        spin_stylesheet = f"""
            QSpinBox {{
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                padding-right: 22px;
                border-radius: 4px;
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                background-color: #383838;
                border-left: 1px solid #444;
                border-bottom: 1px solid #444;
                border-top-right-radius: 4px;
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                background-color: #383838;
                border-left: 1px solid #444;
                border-top: 1px solid #444;
                border-bottom-right-radius: 4px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: #484848;
            }}
            /* Point directly to your assets.py icon paths */
            QSpinBox::up-arrow {{
                image: url("{Icons.ARROW_DROP_UP.as_posix()}");
                width: 12px;
                height: 12px;
            }}
            QSpinBox::down-arrow {{
                image: url("{Icons.ARROW_DROP_DOWN.as_posix()}");
                width: 12px;
                height: 12px;
            }}
        """
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-2000, 2000)
        self.spin_x.setValue(0)
        self.spin_x.setStyleSheet(spin_stylesheet)
        self.spin_x.valueChanged.connect(self._emit_position)

        self.spin_y = QSpinBox()
        self.spin_y.setRange(-2000, 2000)
        self.spin_y.setValue(0)
        self.spin_y.setStyleSheet(spin_stylesheet)
        self.spin_y.valueChanged.connect(self._emit_position)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.spin_x)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.spin_y)
        pos_form.addRow("Position:", pos_layout)

        self.spin_bar_width = QSpinBox()
        self.spin_bar_width.setRange(1, 50)
        self.spin_bar_width.setValue(initial_bar_width)
        self.spin_bar_width.setStyleSheet(spin_stylesheet)
        self.spin_bar_width.valueChanged.connect(self.bar_width_changed.emit)
        pos_form.addRow("Bar Width:", self.spin_bar_width)

        self.spin_gap_size = QSpinBox()
        self.spin_gap_size.setRange(0, 50)
        self.spin_gap_size.setValue(initial_gap_size)
        self.spin_gap_size.setStyleSheet(spin_stylesheet)
        self.spin_gap_size.valueChanged.connect(self.gap_size_changed.emit)
        pos_form.addRow("Gap Size:", self.spin_gap_size)

        self.check_square_blocks = QCheckBox()
        self.check_square_blocks.stateChanged.connect(lambda state: self.force_squares_changed.emit(state))
        pos_form.addRow("Force Squares:", self.check_square_blocks)

        layout.addWidget(pos_section)

        # 2. Visualizer Geometry Section
        geom_section = CollapsibleSection("Visualizer Geometry")
        geom_form = QFormLayout(geom_section.content_area)
        geom_form.setContentsMargins(5, 5, 5, 5)

        self.bars_slider = QSlider(Qt.Orientation.Horizontal)
        self.bars_slider.setRange(16, 256)
        self.bars_slider.setValue(64)
        self.bars_label = QLabel("64")
        self.bars_slider.valueChanged.connect(lambda v: self.bars_label.setText(str(v)))
        self.bars_slider.valueChanged.connect(lambda v: self.bar_count_changed.emit(v))
        geom_form.addRow("Bar Count:", self.bars_slider)
        geom_form.addRow("", self.bars_label)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(50, 300)
        self.radius_slider.setValue(120)
        self.radius_label = QLabel("120")
        self.radius_slider.valueChanged.connect(lambda v: self.radius_label.setText(str(v)))
        self.radius_slider.valueChanged.connect(lambda v: self.radius_changed.emit(v))
        geom_form.addRow("Inner Radius:", self.radius_slider)
        geom_form.addRow("", self.radius_label)

        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setRange(50, 400)
        self.length_slider.setValue(180)
        self.length_label = QLabel("180")
        self.length_slider.valueChanged.connect(lambda v: self.length_label.setText(str(v)))
        self.length_slider.valueChanged.connect(lambda v: self.max_length_changed.emit(v))
        geom_form.addRow("Max Height:", self.length_slider)
        geom_form.addRow("", self.length_label)

        layout.addWidget(geom_section)

        # 3. Shape & Style Section
        style_section = CollapsibleSection("Shape & Style")
        style_form = QFormLayout(style_section.content_area)
        style_form.setContentsMargins(5, 5, 5, 5)

        self.style_combo = QComboBox()
        self.style_combo.addItems(["Circular", "Linear", "Symmetric Waveform", "Equalizer Orbit", "Dual Wave"])
        self.style_combo.setStyleSheet("""
            QComboBox { background-color: #2d2d2d; color: #00ff96; border: 1px solid #444; padding: 4px; border-radius: 4px; }
        """)
        self.style_combo.currentTextChanged.connect(self.style_changed.emit)
        style_form.addRow("Visual Style:", self.style_combo)

        layout.addWidget(style_section)
        
        layout.addStretch()
        self.stack.addWidget(self.wrap_in_scroll(page))

    def setup_presets_page(self):
        page = QWidget()
        page.setFixedWidth(270)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Section for Presets Management
        preset_section = CollapsibleSection("Preset Management")
        preset_form = QFormLayout(preset_section.content_area)
        preset_form.setContentsMargins(5, 5, 5, 5)

        # Save Preset Button styled to match your theme
        save_btn = QPushButton("Save Current as Preset")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #383838;
                color: #00ff96;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #484848;
            }
        """)
        save_btn.clicked.connect(self._handle_save_preset)
        preset_form.addRow(save_btn)

        layout.addWidget(preset_section)
        layout.addStretch()
        
        # Wrap in scroll and add to your stacked widget at index 2 (the third icon)
        self.stack.addWidget(self.wrap_in_scroll(page))

    def _handle_save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        if not ok:
            return
            
        try:
            saved_path = save_current_preset(self, name if name.strip() else None)
            print(f"Preset successfully saved to: {saved_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save preset:\n{str(e)}")

    def load_initial_defaults(self):
        config = load_default_preset()
        if config:
            apply_preset_to_ui(self, config)

    def setup_color_page(self):
        page = QWidget()
        page.setFixedWidth(270)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        color_section = CollapsibleSection("Color Customization")
        color_form = QFormLayout(color_section.content_area)
        color_form.setContentsMargins(5, 5, 5, 5)

        # 1. Color Mode Selector
        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems(["Gradient (Rainbow)", "Solid Color", "Color Cycle"])
        self.color_mode_combo.setStyleSheet("""
            QComboBox { background-color: #2d2d2d; color: #00ff96; border: 1px solid #444; padding: 4px; border-radius: 4px; }
        """)
        self.color_mode_combo.currentTextChanged.connect(self.color_mode_changed.emit)
        color_form.addRow("Color Mode:", self.color_mode_combo)

        # 2. Solid Color Picker Button
        self.selected_solid_color = QColor(0, 255, 150)  
        self.solid_color_btn = QPushButton("Choose Color...")
        self.update_color_button_style(self.selected_solid_color)
        self.solid_color_btn.clicked.connect(self._open_color_picker)
        color_form.addRow("Solid Color:", self.solid_color_btn)

        # 3. Color Cycle Speed Slider
        self.cycle_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.cycle_speed_slider.setRange(1, 10)
        self.cycle_speed_slider.setValue(3)
        self.cycle_speed_slider.valueChanged.connect(self.cycle_speed_changed.emit)
        color_form.addRow("Cycle Speed:", self.cycle_speed_slider)

        # --- 4. Glow Controls ---
        # Glow Intensity Slider (0 = Off)
        self.glow_slider = QSlider(Qt.Orientation.Horizontal)
        self.glow_slider.setRange(0, 200)
        self.glow_slider.setValue(0)  
        
        self.glow_label = QLabel("Off")
        self.glow_slider.valueChanged.connect(lambda v: self.glow_label.setText(str(v) if v > 0 else "Off"))
        self.glow_slider.valueChanged.connect(self.glow_changed.emit)
        
        color_form.addRow("Glow Intensity:", self.glow_slider)
        color_form.addRow("", self.glow_label)

        # Glow Distance Slider
        self.glow_distance_slider = QSlider(Qt.Orientation.Horizontal)
        self.glow_distance_slider.setRange(0, 200)
        self.glow_distance_slider.setValue(50)  
        
        self.glow_distance_label = QLabel("50")
        self.glow_distance_slider.valueChanged.connect(lambda v: self.glow_distance_label.setText(str(v)))
        self.glow_distance_slider.valueChanged.connect(self.glow_distance_changed.emit)
        
        color_form.addRow("Glow Distance:", self.glow_distance_slider)
        color_form.addRow("", self.glow_distance_label)

        # --- NEW: Glow Layers Slider ---
        self.glow_layers_slider = QSlider(Qt.Orientation.Horizontal)
        self.glow_layers_slider.setRange(1, 12)
        self.glow_layers_slider.setValue(6)  # Default layer count
        
        self.glow_layers_label = QLabel("6")
        self.glow_layers_slider.valueChanged.connect(lambda v: self.glow_layers_label.setText(str(v)))
        self.glow_layers_slider.valueChanged.connect(self.glow_layers_changed.emit)
        
        color_form.addRow("Glow Layers:", self.glow_layers_slider)
        color_form.addRow("", self.glow_layers_label)

        # Glow Style Dropdown
        self.glow_style_combo = QComboBox()
        self.glow_style_combo.addItems(["Burst", "Standard Bloom"])
        self.glow_style_combo.setStyleSheet("""
            QComboBox { background-color: #2d2d2d; color: #00ff96; border: 1px solid #444; padding: 4px; border-radius: 4px; }
        """)
        self.glow_style_combo.currentTextChanged.connect(self.glow_style_changed.emit)
        color_form.addRow("Glow Style:", self.glow_style_combo)

        # Glow Angle Slider (0 to 360 degrees)
        self.angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.angle_slider.setRange(0, 360)
        self.angle_slider.setValue(0)
        
        self.angle_label = QLabel("0°")
        self.angle_slider.valueChanged.connect(lambda v: self.angle_label.setText(f"{v}°"))
        self.angle_slider.valueChanged.connect(self.glow_angle_changed.emit)
        
        color_form.addRow("Glow Angle:", self.angle_slider)
        color_form.addRow("", self.angle_label)

        layout.addWidget(color_section)
        layout.addStretch()
        self.stack.addWidget(self.wrap_in_scroll(page))

    def _open_color_picker(self):
        # Open PyQt6's native QColorDialog anchored to the sidebar
        color = QColorDialog.getColor(self.selected_solid_color, self, "Select Solid Visualizer Color")
        if color.isValid():
            self.selected_solid_color = color
            self.update_color_button_style(color)
            self.color_changed.emit(color)

    def update_color_button_style(self, color):
        # Dynamically change the button's background and text color based on brightness
        hex_val = color.name()
        # Simple contrast check for text color
        text_color = "#000000" if color.lightness() > 128 else "#ffffff"
        self.solid_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_val};
                color: {text_color};
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }}
            QPushButton:hover {{
                border: 1px solid #fff;
            }}
        """)

    def show_template_dialog(self):
        self.template_dialog.set_shape(self.canvas.visualizer_style if hasattr(self, 'canvas') else "circular")
        self.template_dialog.exec()

    def _on_template_selected(self, key):
        self.current_template = key
        self.template_selected.emit(key)

    def _emit_position(self):
        self.position_changed.emit(self.spin_x.value(), self.spin_y.value())

    def update_position_spinboxes(self, canvas_x, canvas_y):
        target_y = -canvas_y
        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)
        if self.spin_x.value() != canvas_x:
            self.spin_x.setValue(canvas_x)
        if self.spin_y.value() != target_y:
            self.spin_y.setValue(target_y)
        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)

    def switch_category(self, index):
        if index < self.stack.count():
            self.stack.setCurrentIndex(index)
            
        buttons = [self.btn_mode, self.btn_control, self.btn_presets, self.btn_color, self.btn_templates, self.btn_settings]
        for i, btn in enumerate(buttons):
            btn.setChecked(i == index)
            if i == index:
                target_pos = btn.mapTo(self.active_indicator.parentWidget(), QPoint(0, 0))
                
                start_rect = self.active_indicator.geometry()
                # X=0 pins it precisely to the outer border, Y matches the active button block
                end_rect = QRect(0, target_pos.y(), 4, btn.height())
                
                self.indicator_anim.stop()
                self.indicator_anim.setStartValue(start_rect)
                self.indicator_anim.setEndValue(end_rect)
                self.indicator_anim.start()

    def create_segmented_audio_selector(self):
        container = QWidget()
        container.setFixedHeight(48)
        container.setStyleSheet("""
            QWidget {
                background-color: #242424;
                border-radius: 24px;
            }
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Sliding background indicator
        self.segment_indicator = QFrame(container)
        self.segment_indicator.setFixedHeight(40)
        self.segment_indicator.setStyleSheet("""
            QFrame {
                background-color: #3d3d3d;
                border-radius: 20px;
            }
        """)
        self.segment_indicator.lower()

        self.segment_anim = QPropertyAnimation(self.segment_indicator, b"geometry")
        self.segment_anim.setDuration(200)
        self.segment_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.audio_mode_group = QButtonGroup(self)
        self.audio_mode_group.setExclusive(True)

        # Helper function to adapt your existing create_icon_btn for the pill segments
        def create_segment_btn(normal_icon, selected_icon, tooltip):
            btn = self.create_icon_btn(normal_icon, selected_icon, tooltip)
            btn.setFixedHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            return btn

        # 1. Audio File Button
        self.btn_mode_file = create_segment_btn(Icons.AUDIO_FILE_24C, Icons.AUDIO_FILE_24F, "Audio File")
        self.btn_mode_file.setChecked(True)
        self.audio_mode_group.addButton(self.btn_mode_file, 0)
        layout.addWidget(self.btn_mode_file)

        # 2. Microphone Button
        self.btn_mode_mic = create_segment_btn(Icons.MIC_24C, Icons.MIC_24F, "Microphone") # Update with your mic icons
        self.audio_mode_group.addButton(self.btn_mode_mic, 1)
        layout.addWidget(self.btn_mode_mic)

        # 3. Desktop Audio Button
        self.btn_mode_desktop = create_segment_btn(Icons.DESKTOP_AUDIO_24C, Icons.DESKTOP_AUDIO_24F, "Desktop Audio")
        self.audio_mode_group.addButton(self.btn_mode_desktop, 2)
        layout.addWidget(self.btn_mode_desktop)

        self.audio_mode_group.idClicked.connect(self._animate_segment_to)
        container.showEvent = lambda event: self._init_segment_position()

        return container

    def _init_segment_position(self):
        checked_btn = self.audio_mode_group.checkedButton()
        if checked_btn:
            pos = checked_btn.pos()
            self.segment_indicator.setGeometry(pos.x(), pos.y(), checked_btn.width(), checked_btn.height())

    def _animate_segment_to(self, mode_id):
        buttons = [self.btn_mode_file, self.btn_mode_mic, self.btn_mode_desktop]
        
        for i, btn in enumerate(buttons):
            btn.setChecked(i == mode_id)

        target_btn = buttons[mode_id]
        start_rect = self.segment_indicator.geometry()
        end_rect = QRect(target_btn.x(), target_btn.y(), target_btn.width(), target_btn.height())
        
        self.segment_anim.stop()
        self.segment_anim.setStartValue(start_rect)
        self.segment_anim.setEndValue(end_rect)
        self.segment_anim.start()

        # Update the parameter section UI dynamically based on the active mode
        self._update_source_parameters_view(mode_id)

        modes = ["📁 Audio File", "🎙️ Microphone", "🖥️ Desktop Audio"]
        if mode_id < len(modes):
            self.audio_source_changed.emit(modes[mode_id])

    def _update_source_parameters_view(self, mode_id):
        # Clear existing widgets from parameters layout
        while self.source_params_layout.count():
            item = self.source_params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        input_field_style = "QLineEdit { background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 5px; border-radius: 4px; }"
        btn_style = "QPushButton { background-color: #333; color: white; border: 1px solid #555; padding: 5px 10px; border-radius: 4px; } QPushButton:hover { background-color: #3d3d3d; }"

        if mode_id == 0:
            # --- Audio File Mode UI ---
            file_label = QLabel("Audio File :")
            self.file_path_input = QLineEdit()
            self.file_path_input.setStyleSheet(input_field_style)
            self.file_path_input.setPlaceholderText("Select an audio file...")
            
            browse_btn = QPushButton("Browse File")
            browse_btn.setStyleSheet(btn_style)
            browse_btn.clicked.connect(self._browse_audio_file)

            path_layout = QHBoxLayout()
            path_layout.addWidget(self.file_path_input)
            path_layout.addWidget(browse_btn)

            # --- New Professional "Load Track" Action Button ---
            self.load_track_btn = QPushButton("Load Track")
            self.load_track_btn.setStyleSheet("""
                QPushButton { background-color: #00ff96; color: #121212; font-weight: bold; border-radius: 4px; padding: 6px; }
                QPushButton:hover { background-color: #00cca3; }
            """)
            # Connect this button to emit your custom signal using the text box's current path
            self.load_track_btn.clicked.connect(lambda: self.audio_file_selected.emit(self.file_path_input.text()))

            self.source_params_layout.addWidget(file_label)
            self.source_params_layout.addLayout(path_layout)
            self.source_params_layout.addWidget(self.load_track_btn)

        else:
            # --- Microphone / Desktop Audio Mode UI ---
            device_label = QLabel("Input Device:")
            self.device_combo = QComboBox()
            self.device_combo.setStyleSheet("""
                QComboBox { background-color: #2d2d2d; color: #00ff96; border: 1px solid #444; padding: 4px; border-radius: 4px; }
            """)
            try:
                devices = sd.query_devices()
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0 or dev['max_output_channels'] > 0:
                        self.device_combo.addItem(f"[{i}] {dev['name']}", userData=i)
            except Exception:
                pass
            self.device_combo.currentIndexChanged.connect(self.device_selected.emit)

            self.source_params_layout.addWidget(device_label)
            self.source_params_layout.addWidget(self.device_combo)

    def _browse_audio_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.flac *.ogg)"
        )
        if file_name:
            self.file_path_input.setText(file_name)