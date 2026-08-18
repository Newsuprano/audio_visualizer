import math
import numpy as np
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QSizePolicy

# Import modular templates
from src.templates.line_template import LineTemplate
from src.templates.block_template import BlockTemplate
from src.audio import read_chunk_at_position


class VisualizerCanvas(QWidget):

    position_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.num_bars = 64
        self.inner_radius = 120
        self.max_bar_length = 180
        self.bar_width = 10 
        self.gap_size = 4
        self.force_squares = False  # <-- Added flag for square blocks toggle

        self.current_amplitudes = np.zeros(self.num_bars)
        self.target_amplitudes = np.zeros(self.num_bars)
        
        self.visualizer_style = "circular"
        
        self.templates = {
            "lines": LineTemplate(),
            "blocks": BlockTemplate()
        }
        self.current_template = self.templates["lines"]

        self.offset_x = 0
        self.offset_y = 0

        # Data states
        self.current_amplitudes = np.array([])
        self.target_amplitudes = np.array([])
        
        # References for file mode
        self.audio_file_stream = None
        self.current_frame = 0
        self.chunk_size = 1024

        self.previous_heights = {}

        # 60 FPS Render Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_visualizer)
        self.timer.start(16)

    def set_audio_source(self, audio_stream):
        """Links the raw PCM audio stream data source."""
        self.audio_file_stream = audio_stream

    def seek_to_time(self, time_sec):
        """Updates internal frame tracking based on timestamp."""
        if self.audio_file_stream is not None:
            sampling_rate = getattr(self.audio_file_stream, 'samplerate', 44100)
            self.current_frame = int(time_sec * sampling_rate)

    def push_amplitudes(self, amplitudes):
        """Clean universal entry point to update target amplitudes."""
        if amplitudes is not None:
            self.target_amplitudes = amplitudes
            if len(self.current_amplitudes) != len(amplitudes):
                self.current_amplitudes = amplitudes.copy()

    def set_style(self, style_name):
        styles = ["circular", "linear", "symmetric", "burst", "orbit", "dual_wave", "radar"]
        if style_name in styles:
            self.visualizer_style = style_name
            self.previous_heights.clear()

    def set_template(self, template_name):
        if template_name in self.templates:
            self.current_template = self.templates[template_name]

    def update_visualizer(self):
        """Triggers a re-paint frame."""
        self.update()

    def _get_smoothed_height(self, idx, am):
        """Interpolates smoothly toward the target amplitude on every frame."""
        if idx >= len(self.current_amplitudes) or idx >= len(self.target_amplitudes):
            target_length = am * self.max_bar_length
            return max(5, target_length)

        target_val = self.target_amplitudes[idx]
        current_val = self.current_amplitudes[idx]

        # --- BUTTERY SMOOTH LERP ---
        smoothed_val = current_val + (target_val - current_val) * 0.25
        self.current_amplitudes[idx] = smoothed_val

        target_length = smoothed_val * self.max_bar_length
        return max(5, target_length)

    def _get_color(self, idx):
        red = min(255, int(idx * 4))
        green = min(255, max(0, int(255 - abs(idx - (self.num_bars / 2)) * 3)))
        blue = max(0, int(255 - (idx * 4)))
        return QColor(red, green, blue)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateGeometry()
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.updateGeometry()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.position()
            self._initial_offset_x = self.offset_x
            self._initial_offset_y = self.offset_y
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, '_dragging', False):
            delta = event.position() - self._drag_start_pos
            self.offset_x = int(self._initial_offset_x + delta.x())
            self.offset_y = int(self._initial_offset_y + delta.y())
            self.update()
            event.accept()
            self.position_changed.emit(int(self.offset_x), int(self.offset_y))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()

    def set_offset(self, x, y):
        """Manually sets visualizer offsets from the sidebar inputs."""
        if self.offset_x != x or self.offset_y != y:
            self.offset_x = x
            self.offset_y = y
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        width = self.width()
        height = self.height()

        if len(self.current_amplitudes) == 0 or self.num_bars <= 0:
            return

        # Slice the amplitudes array to respect your bar-count slider
        amplitudes = self.current_amplitudes[:self.num_bars]
        active_count = len(amplitudes)
        
        if active_count == 0:
            return

        center_x = (width // 2) + getattr(self, 'offset_x', 0)
        center_y = (height // 2) + getattr(self, 'offset_y', 0)

        # --- 1. CIRCULAR STYLE ---
        if self.visualizer_style == "circular":
            angle_step = 360.0 / self.num_bars
            for idx, am in enumerate(amplitudes):
                bar_height = self._get_smoothed_height(idx, am)
                angle_rad = math.radians((idx * angle_step) - 90.0)
                color = self._get_color(idx)

                self.current_template.draw_item(
                    painter, center_x, center_y, bar_height, angle_rad, color, self.bar_width, 
                    symmetric=False, inner_radius=self.inner_radius, 
                    gap_size=self.gap_size, force_squares=self.force_squares
                )

        # --- 2. LINEAR STYLE ---
        elif self.visualizer_style == "linear":
            # Include offset_y so the Y-axis position controls actually move it up and down
            base_y = int(height * 0.8) + getattr(self, 'offset_y', 0)
            
            total_block_width = active_count * (self.bar_width + self.gap_size) - self.gap_size
            start_x = (width - total_block_width) // 2 + getattr(self, 'offset_x', 0)

            for idx, am in enumerate(amplitudes):
                bar_height = self._get_smoothed_height(idx, am)
                bar_x = start_x + (idx * (self.bar_width + self.gap_size))
                color = self._get_color(idx)

                self.current_template.draw_item(
                    painter, bar_x, base_y, bar_height, None, color, self.bar_width, 
                    symmetric=False, inner_radius=self.inner_radius, 
                    gap_size=self.gap_size, force_squares=self.force_squares
                )

        # --- 3. SYMMETRIC WAVEFORM STYLE ---
        elif self.visualizer_style == "symmetric":
            total_block_width = active_count * (self.bar_width + self.gap_size) - self.gap_size
            start_x = (width - total_block_width) // 2 + getattr(self, 'offset_x', 0)

            for idx, am in enumerate(amplitudes):
                bar_height = self._get_smoothed_height(idx, am)
                bar_x = start_x + (idx * (self.bar_width + self.gap_size))
                color = self._get_color(idx)

                self.current_template.draw_item(
                    painter, bar_x, center_y, bar_height, None, color, self.bar_width, 
                    symmetric=True, inner_radius=self.inner_radius, 
                    gap_size=self.gap_size, force_squares=self.force_squares
                )

        # --- 4. EQUALIZER ORBIT STYLE ---
        elif self.visualizer_style == "orbit":
            angle_step = 360.0 / self.num_bars
            for idx, am in enumerate(amplitudes):
                bar_length = self._get_smoothed_height(idx, am)
                angle_rad = math.radians((idx * angle_step) - 90.0)
                color = self._get_color(idx)
                
                orbit_inner = max(0, self.inner_radius - (bar_length / 2))

                self.current_template.draw_item(
                    painter, center_x, center_y, bar_length, angle_rad, color, self.bar_width, 
                    symmetric=False, inner_radius=orbit_inner, 
                    gap_size=self.gap_size, force_squares=self.force_squares
                )

        # --- 5. DUAL WAVE STYLE ---
        elif self.visualizer_style == "dual_wave":
            angle_step = 360.0 / self.num_bars
            for idx, am in enumerate(amplitudes):
                bar_length = self._get_smoothed_height(idx, am)
                angle_rad = math.radians((idx * angle_step) - 90.0)
                color = self._get_color(idx)

                self.current_template.draw_item(
                    painter, center_x, center_y, bar_length, angle_rad, color, self.bar_width, 
                    symmetric=False, inner_radius=self.inner_radius, 
                    gap_size=self.gap_size, force_squares=self.force_squares
                )
                self.current_template.draw_item(
                    painter, center_x, center_y, bar_length, angle_rad + math.pi, color, self.bar_width, 
                    symmetric=False, inner_radius=self.inner_radius, 
                    gap_size=self.gap_size, force_squares=self.force_squares
                )