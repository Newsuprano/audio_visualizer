import math
import numpy as np
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QImage
from PyQt6.QtWidgets import QWidget, QSizePolicy, QGraphicsBlurEffect

# Import modular templates
from src.templates.line_template import LineTemplate
from src.templates.block_template import BlockTemplate
from src.audio.audio import read_chunk_at_position
from src.preset_manager.preset_manager import load_default_preset


class VisualizerCanvas(QWidget):

    position_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Load default preset config
        config = load_default_preset()
        layout_cfg = config.get("canvas_layout", {})
        geom_cfg = config.get("geometry", {})
        style_cfg = config.get("style", {})
        color_cfg = config.get("colors", {})
        glow_cfg = config.get("glow_settings", {})

        # Geometry & Layout Mapping
        self.num_bars = geom_cfg.get("bar_count", 64)
        if not self.num_bars: 
            self.num_bars = 64

        self.inner_radius = geom_cfg.get("inner_radius", 120)
        self.max_bar_length = geom_cfg.get("max_height", 180)
        self.bar_width = layout_cfg.get("bar_width", 10) 
        self.gap_size = layout_cfg.get("gap_size", 4)
        self.force_squares = layout_cfg.get("force_squares", False)

        self.current_amplitudes = np.zeros(self.num_bars)
        self.target_amplitudes = np.zeros(self.num_bars)
        
        # Style & Template Mapping
        visual_style_name = style_cfg.get("visualizer_style", style_cfg.get("visual_style", "lines"))
        self.visualizer_style = str(visual_style_name).lower()
        
        self.templates = {
            "lines": LineTemplate(),
            "blocks": BlockTemplate()
        }
        # Safely match style or default to lines
        template_key = style_cfg.get("template", "lines")
        self.current_template = self.templates.get(template_key, self.templates["lines"])

        self.offset_x = layout_cfg.get("x", 0)
        self.offset_y = layout_cfg.get("y", 0)
        
        # References for file mode
        self.audio_file_stream = None
        self.current_frame = 0
        self.chunk_size = 1024

        self.previous_heights = {}

        # 60 FPS Render Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_visualizer)
        self.timer.start(16)

        # Color Customization States
        self.color_mode = color_cfg.get("color_mode", "Gradient (Rainbow)")
        rgb = color_cfg.get("solid_color", [0, 255, 150])
        self.solid_color = QColor(rgb[0], rgb[1], rgb[2])
        self.cycle_speed = color_cfg.get("cycle_speed", 3)
        self._color_cycle_hue = 0.0

        # Glow Effect States
        self.glow_intensity = glow_cfg.get("intensity", 0.0)    
        self.glow_distance = glow_cfg.get("distance", 50.0)      
        self.glow_angle = glow_cfg.get("angle", 0.0)
        self.glow_style = glow_cfg.get("style", "Burst")
        self.glow_layers = glow_cfg.get("layers", 6)

    def set_glow_style(self, style_name):
        self.glow_style = style_name
        self.update()

    def set_glow_angle(self, angle):
        self.glow_angle = float(angle)
        self.update()

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
        """Triggers a re-paint frame and advances color cycling if active."""
        if self.color_mode == "Color Cycle":
            self._color_cycle_hue = (self._color_cycle_hue + (self.cycle_speed * 0.002)) % 1.0
            
        self.update()

    def _get_smoothed_height(self, idx, am):
        """Interpolates smoothly toward the target amplitude on every frame."""
        if idx >= len(self.current_amplitudes) or idx >= len(self.target_amplitudes):
            target_length = am * self.max_bar_length
            return max(5, target_length)

        target_val = self.target_amplitudes[idx]
        current_val = self.current_amplitudes[idx]

        smoothed_val = current_val + (target_val - current_val) * 0.25
        self.current_amplitudes[idx] = smoothed_val

        target_length = smoothed_val * self.max_bar_length
        return max(5, target_length)

    def _get_color(self, idx):
        if self.color_mode == "Solid Color":
            return self.solid_color
            
        elif self.color_mode == "Color Cycle":
            hue = (self._color_cycle_hue + (idx / max(1, self.num_bars))) % 1.0
            return QColor.fromHsvF(hue, 1.0, 1.0)
            
        else:
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
        if self.offset_x != x or self.offset_y != y:
            self.offset_x = x
            self.offset_y = y
            self.update()

    def set_color_mode(self, mode_name):
        self.color_mode = mode_name
        self.update()

    def set_solid_color(self, color):
        if isinstance(color, QColor) and color.isValid():
            self.solid_color = color
            self.update()

    def set_cycle_speed(self, speed):
        self.cycle_speed = speed

    def set_glow_intensity(self, value):
        self.glow_intensity = value
        self.update()

    def _draw_geometry(self, painter, width, height, amplitudes, active_count):
        """Universal geometry renderer used for both the glow buffer and main sharp layer."""
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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        width = self.width()
        height = self.height()

        if len(self.current_amplitudes) == 0 or self.num_bars <= 0:
            return

        amplitudes = self.current_amplitudes[:self.num_bars]
        active_count = len(amplitudes)
        
        if active_count == 0:
            return

        # --- GLOW PASS BASED ON SELECTED STYLE ---
        if self.glow_intensity > 0:
            center_x = (width // 2) + getattr(self, 'offset_x', 0)
            center_y = (height // 2) + getattr(self, 'offset_y', 0)

            if self.glow_style == "Burst":
                import math
                
                # Use distance for geometry scaling & spreading
                distance = float(getattr(self, 'glow_distance', self.glow_intensity))
                # Use intensity strictly for brightness/opacity
                intensity = float(self.glow_intensity)
                
                # --- UPDATED: Dynamic layers from slider ---
                layers = int(getattr(self, 'glow_layers', 6))
                layers = max(1, layers) # Prevent division by zero

                has_angle = abs(self.glow_angle) > 0.001
                rad = math.radians(self.glow_angle) if has_angle else 0
                
                total_shift_distance = distance * 1.5 if has_angle else 0
                shift_x = math.cos(rad) * total_shift_distance if has_angle else 0
                shift_y = math.sin(rad) * total_shift_distance if has_angle else 0

                # Brightness factor is now driven purely by the intensity slider
                brightness_factor = intensity * 0.08

                for i in range(layers, 0, -1):
                    fraction = i / layers
                    
                    # Opacity responds to the intensity slider
                    alpha = (0.04 + (brightness_factor * 0.12)) * (1.0 - (i / (layers + 1)))
                    
                    painter.save()
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
                    painter.setOpacity(alpha)
                    
                    half_layers = layers / 2
                    if i > half_layers:
                        sub_frac = (i - half_layers) / half_layers if half_layers > 0 else 0.5
                        # Scale and spread respond to the distance slider
                        scale = 1.0 + (sub_frac * distance * 0.008)
                        layer_cx = center_x + (shift_x * sub_frac)
                        layer_cy = center_y + (shift_y * sub_frac)
                    else:
                        sub_frac = i / half_layers if half_layers > 0 else 0.5
                        scale = 1.0 - ((1.0 - sub_frac) * distance * 0.004)
                        layer_cx = center_x
                        layer_cy = center_y
                    
                    painter.translate(layer_cx, layer_cy)
                    painter.scale(scale, scale)
                    painter.translate(-center_x, -center_y)
                    
                    self._draw_geometry(painter, width, height, amplitudes, active_count)
                    painter.restore()

            elif self.glow_style == "Standard Bloom":
                glow_img = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
                glow_img.fill(Qt.GlobalColor.transparent)
                
                img_painter = QPainter(glow_img)
                img_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self._draw_geometry(img_painter, width, height, amplitudes, active_count)
                img_painter.end()

                painter.save()
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
                scale_factor = 1.0 + (float(self.glow_intensity) * 0.003)
                bloomed_w = int(width * scale_factor)
                bloomed_h = int(height * scale_factor)
                smooth_glow = glow_img.scaled(
                    bloomed_w, bloomed_h, 
                    Qt.AspectRatioMode.IgnoreAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                dx = (width - bloomed_w) // 2
                dy = (height - bloomed_h) // 2
                
                painter.setOpacity(0.4)
                painter.drawImage(dx, dy, smooth_glow)
                painter.restore()

        # --- MAIN CRISP PASS ---
        self._draw_geometry(painter, width, height, amplitudes, active_count)