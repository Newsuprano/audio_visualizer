import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor
from .base_template import BaseTemplate

class BlockTemplate(BaseTemplate):
    def draw_item(self, painter, x, y, length, angle, color, width, symmetric=False, inner_radius=120):
        grid_size = max(4, int(width * 1.5))
        spacing = 2
        step_stride = grid_size + spacing

        painter.setPen(QPen(QColor(15, 15, 15), 1))
        painter.setBrush(color)

        if angle is not None:
            # Radial / Circular blocks (Circular, Burst, Orbit)
            num_steps = max(1, int(length / step_stride))
            for s in range(num_steps):
                current_radius = inner_radius + (s * step_stride) + (grid_size // 2)
                curr_x = x + math.cos(angle) * current_radius
                curr_y = y + math.sin(angle) * current_radius
                painter.drawRect(int(curr_x - grid_size // 2), int(curr_y - grid_size // 2), grid_size, grid_size)
        else:
            # Cartesian blocks
            if symmetric:
                # Use the full length mapped outward from center, ensuring each direction gets proper scaling
                half_length = length / 2.0
                half_steps = int(half_length / step_stride)
                
                # Draw a central anchor block if minimum amplitude is hit, 
                # then mirror steps outward above and below center y
                painter.drawRect(int(x - grid_size // 2), int(y - grid_size // 2), grid_size, grid_size)
                
                for b in range(1, half_steps + 1):
                    offset = b * step_stride
                    painter.drawRect(int(x - grid_size // 2), int(y - offset - grid_size // 2), grid_size, grid_size)
                    painter.drawRect(int(x - grid_size // 2), int(y + offset - grid_size // 2), grid_size, grid_size)
            else:
                # Standard linear upward blocks from baseline y
                num_steps = max(1, int(length / step_stride))
                for b in range(num_steps):
                    current_y = y - (b * step_stride) - (grid_size // 2)
                    painter.drawRect(int(x - grid_size // 2), int(current_y), grid_size, grid_size)