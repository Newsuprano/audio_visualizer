from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QWidget
import math

class TemplateDialog(QDialog):
    template_selected = pyqtSignal(str) # Emits the chosen template key (e.g., "lines", "blocks")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Visualizer Template")
        self.setFixedSize(400, 300)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        self.current_shape = "circular" # Default shape tracker
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        title_label = QLabel("Choose Template")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Grid container for the squares
        self.grid_layout = QGridLayout()
        main_layout.addLayout(self.grid_layout)

        # Define available templates
        self.templates = [
            {"key": "lines", "name": "Lines"},
            {"key": "blocks", "name": "Blocks"}
        ]

        self.populate_grid()

    def set_shape(self, shape_name):
        """Updates the active shape and refreshes the preview icons in the grid."""
        self.current_shape = shape_name
        self.populate_grid()

    def populate_grid(self):
        # Safely remove and delete all existing widgets from the layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        # Build grid squares strictly based on the defined templates list
        for i, tmpl in enumerate(self.templates):
            card = QPushButton()
            card.setFixedSize(140, 140)
            card.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    border: 2px solid #444;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    border: 2px solid #00ff96;
                    background-color: #353535;
                }
            """)
            
            card_layout = QVBoxLayout(card)
            
            # Generate a dynamic preview image based on the current shape and template
            preview_label = QLabel()
            pixmap = self.generate_preview_pixmap(tmpl["key"], self.current_shape)
            preview_label.setPixmap(pixmap)
            preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(preview_label)

            name_label = QLabel(tmpl["name"])
            name_label.setStyleSheet("font-size: 12px; color: #ccc; background: transparent;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(name_label)

            # Connect click event
            key = tmpl["key"]
            card.clicked.connect(lambda checked, k=key: self.select_template(k))

            row = i // 2
            col = i % 2
            self.grid_layout.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

    def generate_preview_pixmap(self, template_key, shape_name):
        """Draws a mini thumbnail representation adapting to the selected shape and template."""
        pixmap = QPixmap(100, 80)
        pixmap.fill(QColor(30, 30, 30))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw a tiny mockup based on whether it's circular/linear and lines/blocks
        # (This is a lightweight preview generator rendering a mini shape layout)
        if shape_name in ["circular", "burst", "orbit", "dual_wave"]:
            # Draw mini circular visualizer icon
            cx, cy, r = 50, 40, 20
            for a in range(0, 360, 45):
                rad = math.radians(a)
                x2 = cx + math.cos(rad) * (r + 10)
                y2 = cy + math.sin(rad) * (r + 10)
                
                if template_key == "lines":
                    painter.setPen(QPen(QColor(0, 255, 150), 2))
                    painter.drawLine(int(cx + math.cos(rad)*r), int(cy + math.sin(rad)*r), int(x2), int(y2))
                else: # blocks
                    painter.setBrush(QColor(0, 255, 150))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRect(int(x2 - 2), int(y2 - 2), 4, 4)
        else:
            # Draw mini linear visualizer icon
            for x_pos in range(20, 80, 10):
                if template_key == "lines":
                    painter.setPen(QPen(QColor(0, 255, 150), 3))
                    painter.drawLine(x_pos, 60, x_pos, 25)
                else: # blocks
                    painter.setBrush(QColor(0, 255, 150))
                    painter.setPen(Qt.PenStyle.NoPen)
                    for y_pos in range(25, 60, 6):
                        painter.drawRect(x_pos - 2, y_pos, 4, 4)

        painter.end()
        return pixmap

    def select_template(self, key):
        self.template_selected.emit(key)
        self.accept()