import math
import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QSizePolicy

# Import modular templates
from templates.line_template import LineTemplate
from templates.block_template import BlockTemplate
from audio import read_chunk_at_position  # Moved to top


class VisualizerCanvas(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.num_bars = 64
        self.inner_radius = 120
        self.max_bar_length = 180
        self.bar_width = 3
        
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
        
        # References for file mode (to be cleanly abstracted later)
        self.audio_file_stream = None
        self.current_frame = 0
        self.chunk_size = 1024

        self.previous_heights = {}

        # 60 FPS Render Timer (Only handles redrawing UI smoothly)
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
        """Clean universal entry point for any audio source (File or Live Desktop) to feed data."""
        if amplitudes is not None:
            self.current_amplitudes = amplitudes

    def set_style(self, style_name):
        if style_name in ["circular", "linear", "symmetric", "burst", "orbit", "dual_wave", "radar"]:
            self.visualizer_style = style_name
            self.previous_heights.clear()

    def set_template(self, template_name):
        if template_name in self.templates:
            self.current_template = self.templates[template_name]

    def update_visualizer(self):
        """Triggers a re-paint frame. (Audio chunk polling can be managed by MainWindow timer or controller)."""
        self.update()

    def _get_smoothed_height(self, idx, am):
        target_length = am * self.max_bar_length
        prev_h = self.previous_heights.get(idx, 0)
        bar_height = max(5, target_length if target_length > prev_h else prev_h * 0.75 + target_length * 0.25)
        self.previous_heights[idx] = bar_height
        return bar_height

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        width = self.width()
        height = self.height()

        amplitudes = self.current_amplitudes
        num_bars = len(amplitudes)
        if num_bars == 0 or self.num_bars <= 0:
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
                    symmetric=False, inner_radius=self.inner_radius
                )

        # --- 2. LINEAR STYLE ---
        elif self.visualizer_style == "linear":
            total_spacing_space = width * 0.8
            start_margin_x = int(width * 0.1)
            column_width = int(total_spacing_space / self.num_bars)
            actual_bar_width = max(2, int(column_width * 0.75))
            base_y = int(height * 0.8)

            for idx, am in enumerate(amplitudes):
                bar_height = self._get_smoothed_height(idx, am)
                bar_x = start_margin_x + (idx * column_width) + (column_width // 2)
                color = self._get_color(idx)

                self.current_template.draw_item(
                    painter, bar_x, base_y, bar_height, None, color, actual_bar_width, 
                    symmetric=False, inner_radius=self.inner_radius
                )

        # --- 3. SYMMETRIC WAVEFORM STYLE ---
        elif self.visualizer_style == "symmetric":
            total_spacing_space = width * 0.8
            start_margin_x = int(width * 0.1)
            column_width = int(total_spacing_space / self.num_bars)
            actual_bar_width = max(2, int(column_width * 0.75))

            for idx, am in enumerate(amplitudes):
                bar_height = self._get_smoothed_height(idx, am)
                bar_x = start_margin_x + (idx * column_width) + (column_width // 2)
                color = self._get_color(idx)

                self.current_template.draw_item(
                    painter, bar_x, center_y, bar_height, None, color, actual_bar_width, 
                    symmetric=True, inner_radius=self.inner_radius
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
                    symmetric=False, inner_radius=orbit_inner
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
                    symmetric=False, inner_radius=self.inner_radius
                )
                self.current_template.draw_item(
                    painter, center_x, center_y, bar_length, angle_rad + math.pi, color, self.bar_width, 
                    symmetric=False, inner_radius=self.inner_radius
                )