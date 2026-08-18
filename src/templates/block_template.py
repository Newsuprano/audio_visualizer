import math
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor
from .base_template import BaseTemplate

class BlockTemplate(BaseTemplate):
    def draw_item(self, painter, x, y, length, angle, color, width, symmetric=False, inner_radius=120, gap_size=2, force_squares=False):
        block_width = max(2, int(width))
        
        # If force_squares is True, make height match the width (making it a square)
        # Otherwise, use a fixed height like 8 to keep it a rectangle
        block_height = block_width if force_squares else 8 
        
        spacing = max(0, int(gap_size))
        step_stride = block_height + spacing

        painter.setPen(QPen(QColor(15, 15, 15), 1))
        painter.setBrush(color)

        if angle is not None:
            num_steps = max(1, int(length / step_stride))
            for s in range(num_steps):
                current_radius = inner_radius + (s * step_stride) + (block_height // 2)
                curr_x = x + math.cos(angle) * current_radius
                curr_y = y + math.sin(angle) * current_radius
                painter.drawRect(int(curr_x - block_width // 2), int(curr_y - block_height // 2), block_width, block_height)
        else:
            if symmetric:
                half_length = length / 2.0
                half_steps = int(half_length / step_stride)
                
                painter.drawRect(int(x - block_width // 2), int(y - block_height // 2), block_width, block_height)
                
                for b in range(1, half_steps + 1):
                    offset = b * step_stride
                    painter.drawRect(int(x - block_width // 2), int(y - offset - block_height // 2), block_width, block_height)
                    painter.drawRect(int(x - block_width // 2), int(y + offset - block_height // 2), block_width, block_height)
            else:
                num_steps = max(1, int(length / step_stride))
                for b in range(num_steps):
                    current_y = y - (b * step_stride) - (block_height // 2)
                    painter.drawRect(int(x - block_width // 2), int(current_y), block_width, block_height)