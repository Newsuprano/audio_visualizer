from PyQt6.QtWidgets import (
    QFrame, 
    QVBoxLayout, 
    QToolBox, 
    QCheckBox, 
    QSpinBox, 
    QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt

class SidebarPanel(QFrame):
    # Example signals to pass settings changes back to MainWindow/Canvas
    bar_width_changed = pyqtSignal(int)
    force_squares_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        layout = QVBoxLayout(self)
        
        # Add your QToolBox categories, custom checkboxes, and styled widgets here...
        self.check_square_blocks = QCheckBox("Force Squares")
        self.check_square_blocks.stateChanged.connect(self.force_squares_changed.emit)
        layout.addWidget(self.check_square_blocks)