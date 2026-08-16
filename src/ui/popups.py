from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton,
    QLabel,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)

class VolumePopup(QFrame):
    """A sleek vertical volume slider popup that stays open during interaction."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 110)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        
        # Background frame for styling
        self.bg_frame = QFrame(self)
        self.bg_frame.setGeometry(0, 0, 36, 110)
        self.bg_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 24, 24, 230);
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(0, 8, 0, 8)
        
        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.setStyleSheet("""
            QSlider::groove:vertical { background: #444; width: 4px; border-radius: 2px; }
            QSlider::sub-page:vertical { background: #444; width: 4px; border-radius: 2px; }
            QSlider::add-page:vertical { background: #cc0000; width: 4px; border-radius: 2px; }
            QSlider::handle:vertical { background: #ff0000; height: 10px; width: 10px; margin: 0 -3px; border-radius: 5px; }
        """)
        bg_layout.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)

    def leaveEvent(self, event):
        # Only hide if the mouse has truly left the popup window boundaries
        if not self.rect().contains(self.mapFromGlobal(self.cursor().pos())):
            self.hide()
        super().leaveEvent(event)