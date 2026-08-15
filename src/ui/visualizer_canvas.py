from pathlib import Path
import math
import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QSizePolicy
import pygame

# Import your audio functions
from audio import open_audio_stream, read_chunk_at_position

# Import modular templates
from templates.line_template import LineTemplate
from templates.block_template import BlockTemplate


class VisualizerCanvas(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Allow the canvas to expand natively in all directions
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Configurable parameters (linked to your sliders/controls)
        self.num_bars = 64
        self.inner_radius = 120
        self.max_bar_length = 180
        self.bar_width = 3
        
        # Style and Template toggles
        self.visualizer_style = "circular"
        
        self.templates = {
            "lines": LineTemplate(),
            "blocks": BlockTemplate()
        }
        self.current_template = self.templates["lines"]

        # Position offset for customizable visualizer placement
        self.offset_x = 0
        self.offset_y = 0

        # Initialize audio file and frame tracker
        self.audio_file_path = Path("src/audio/krunk.mp3")
        self.audio_file = open_audio_stream()
        self.current_frame = 0
        self.chunk_size = 1024
        self.current_amplitudes = np.array([])

        pygame.mixer.init()
        try:
            pygame.mixer.music.load(self.audio_file_path)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"Could not start audio playback: {e}")

        # State tracking for smooth decay
        self.previous_heights = {}

        # 60 FPS Render Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_visualizer)
        self.timer.start(16)  # ~60 frames per second

    def set_style(self, style_name):
        """Call this method to switch shapes."""
        if style_name in ["circular", "linear", "symmetric", "burst", "orbit", "dual_wave", "radar"]:
            self.visualizer_style = style_name
            self.previous_heights.clear()

    def set_template(self, template_name):
        """Call this method to switch templates (lines vs blocks)."""
        if template_name in self.templates:
            self.current_template = self.templates[template_name]

    def update_visualizer(self):
        if self.audio_file is not None:
            ms_elapsed = pygame.mixer.music.get_pos()

            if ms_elapsed >= 0:
                sampling_rate = self.audio_file.samplerate
                self.current_frame = int((ms_elapsed / 1000.0) * sampling_rate)

            _, amplitudes = read_chunk_at_position(
                self.audio_file,
                self.current_frame,
                chunk_size=self.chunk_size,
                num_bins=self.num_bars,
            )

            if amplitudes is not None:
                self.current_amplitudes = amplitudes

        self.update()

    def _get_smoothed_height(self, idx, am):
        """Helper to maintain smooth amplitude decay across frames."""
        target_length = am * self.max_bar_length
        prev_h = self.previous_heights.get(idx, 0)
        bar_height = max(5, target_length if target_length > prev_h else prev_h * 0.75 + target_length * 0.25)
        self.previous_heights[idx] = bar_height
        return bar_height

    def _get_color(self, idx):
        """Helper to compute gradient color for bars."""
        red = min(255, int(idx * 4))
        green = min(255, max(0, int(255 - abs(idx - (self.num_bars / 2)) * 3)))
        blue = max(0, int(255 - (idx * 4)))
        return QColor(red, green, blue)

    def resizeEvent(self, event):
        """Natively handle window resizes, full-screen toggles, and restoration."""
        super().resizeEvent(event)
        # Force the widget to update its layout region immediately
        self.updateGeometry()
        self.update()

    def showEvent(self, event):
        """Ensure proper geometry mapping when window visibility or state changes."""
        super().showEvent(event)
        self.updateGeometry()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background black
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        # --- KEEP THIS: Live parent container bounds mapping ---
        container = self.parentWidget()
        if container:
            target_rect = container.rect()
        else:
            target_rect = self.rect()

        width = self.width()
        height = self.height()
        # ------------------------------------------------------

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
                
                # Orbit centers bars symmetrically across the inner_radius ring
                orbit_inner = max(0, self.inner_radius - (bar_length / 2))

                self.current_template.draw_item(
                    painter, center_x, center_y, bar_length, angle_rad, color, self.bar_width, 
                    symmetric=False, inner_radius=orbit_inner
                )

        # --- 5. DUAL WAVE (MIRRORED CIRCULAR) STYLE ---
        elif self.visualizer_style == "dual_wave":
            angle_step = 360.0 / self.num_bars
            for idx, am in enumerate(amplitudes):
                bar_length = self._get_smoothed_height(idx, am)
                angle_rad = math.radians((idx * angle_step) - 90.0)
                color = self._get_color(idx)

                # Draw primary circular wave
                self.current_template.draw_item(
                    painter, center_x, center_y, bar_length, angle_rad, color, self.bar_width, 
                    symmetric=False, inner_radius=self.inner_radius
                )
                # Draw mirrored opposite wave (shifted by 180 degrees / pi)
                self.current_template.draw_item(
                    painter, center_x, center_y, bar_length, angle_rad + math.pi, color, self.bar_width, 
                    symmetric=False, inner_radius=self.inner_radius
                )