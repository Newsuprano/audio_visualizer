import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen
from .base_template import BaseTemplate

class LineTemplate(BaseTemplate):
    def draw_item(self, painter, x, y, length, angle, color, width, symmetric=False, inner_radius=120, **kwargs):
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        if angle is not None:
            # Rotated line (Circular / Burst / Orbit)
            start_x = x + math.cos(angle) * inner_radius
            start_y = y + math.sin(angle) * inner_radius
            outer_radius = inner_radius + max(3, int(length))
            end_x = x + math.cos(angle) * outer_radius
            end_y = y + math.sin(angle) * outer_radius
            painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
        else:
            # Cartesian lines
            if symmetric:
                h_half = int(length // 2)
                painter.drawLine(int(x), int(y - 1), int(x), int(y + 1)) # Center anchor dot/line
                painter.drawLine(int(x), int(y), int(x), int(y - h_half))
                painter.drawLine(int(x), int(y), int(x), int(y + h_half))
            else:
                painter.drawLine(int(x), int(y), int(x), int(y - int(length)))