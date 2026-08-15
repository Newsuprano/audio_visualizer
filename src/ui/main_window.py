from pathlib import Path
import math
import numpy as np
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
    QFrame
)
import pygame

# Import your canvas and audio functions
from .visualizer_canvas import VisualizerCanvas
from audio import open_audio_stream, read_chunk_at_position
from ui.template_dialog import TemplateDialog


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Custom Audio Visualizer Studio")
        self.resize(1100, 700)
        
        # Enable mouse tracking on the main window
        self.setMouseTracking(True)

        # --- ROOT CONTAINER & LAYOUT ---
        root_widget = QWidget(self)
        root_layout = QHBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- 1. PARAMETER PANEL (Sidebar) ---
        self.sidebar = QFrame(root_widget)
        self.sidebar.setFixedWidth(280)
        self.sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.sidebar.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # Header layout with a collapse button
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

        # Form layout for your controls
        form_layout = QFormLayout()
        sidebar_layout.addLayout(form_layout)

        # Slider: Number of Bars
        self.bars_slider = QSlider(Qt.Orientation.Horizontal)
        self.bars_slider.setRange(16, 128)
        self.bars_slider.setValue(64)
        self.bars_slider.valueChanged.connect(self.update_bar_count)
        self.bars_label = QLabel(str(64))
        form_layout.addRow("Bar Count:", self.bars_slider)
        form_layout.addRow("", self.bars_label)

        # Slider: Inner Radius
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(50, 300)
        self.radius_slider.setValue(120)
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.radius_label = QLabel(str(120))
        form_layout.addRow("Inner Radius:", self.radius_slider)
        form_layout.addRow("", self.radius_label)

        # Slider: Max Bar Length
        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setRange(50, 400)
        self.length_slider.setValue(180)
        self.length_slider.valueChanged.connect(self.update_max_length)
        self.length_label = QLabel(str(180))
        form_layout.addRow("Max Bar Height:", self.length_slider)
        form_layout.addRow("", self.length_label)

        # Dropdown: Visualizer Style Selection
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "Circular",
            "Linear",
            "Symmetric Waveform",
            "Equalizer Orbit",
            "Dual Wave",
        ])
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        form_layout.addRow("Style:", self.style_combo)

        # Template Dialog
        self.template_dialog = TemplateDialog(self)
        self.template_dialog.template_selected.connect(self.apply_template_selection)

        self.open_templates_btn = QPushButton("Templates Menu")
        self.open_templates_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #353535;
                border: 1px solid #00ff96;
            }
        """)
        self.open_templates_btn.clicked.connect(self.show_template_dialog)
        form_layout.addRow("Templates:", self.open_templates_btn)

        # --- 2. VISUALIZER CANVAS ---
        self.canvas = VisualizerCanvas(root_widget)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Add sidebar and canvas to root layout
        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.canvas)
        
        self.setCentralWidget(root_widget)
        self.sidebar_visible = True

        # --- 3. HOVER TRIGGER RECTANGLE (Arrow Handle) ---
        # A floating button styled as a slim edge handle, positioned as a child overlay
        self.trigger_btn = QPushButton("▶", self)
        self.trigger_btn.setFixedWidth(24)
        self.trigger_btn.setFixedHeight(80)
        self.trigger_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #00ff96;
                border: 1px solid #444;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #00ff96;
            }
        """)
        self.trigger_btn.hide()  # Hidden by default when sidebar is visible
        self.trigger_btn.clicked.connect(self.show_sidebar)
        self.trigger_btn.raise_()  # Ensure it renders on top of the canvas

    def resizeEvent(self, event):
        """Keep the hover handle vertically centered on the left edge when resized."""
        super().resizeEvent(event)
        if hasattr(self, 'trigger_btn'):
            # Position it vertically centered on the far left edge (x=0)
            y_pos = (self.height() - self.trigger_btn.height()) // 2
            self.trigger_btn.move(0, y_pos)

    def hide_sidebar(self):
        """Collapses the sidebar and reveals the edge handle."""
        self.sidebar.setVisible(False)
        self.sidebar_visible = False
        self.trigger_btn.show()
        self.canvas.updateGeometry()
        self.canvas.update()

    def show_sidebar(self):
        """Expands the sidebar and hides the edge handle."""
        self.trigger_btn.hide()
        self.sidebar.setVisible(True)
        self.sidebar_visible = True
        self.canvas.updateGeometry()
        self.canvas.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Triggers the handle to appear when hovering near the left edge if sidebar is hidden."""
        if not self.sidebar_visible:
            # If mouse is within 25px of the left edge, make sure the handle is visible/interactive
            if event.pos().x() <= 25:
                self.trigger_btn.show()
            else:
                # Optional: auto-hide the trigger handle if user moves away from the edge
                pass
        super().mouseMoveEvent(event)

    # Slot functions to link UI controls live to the canvas
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