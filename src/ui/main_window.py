from pathlib import Path
import math
import numpy as np
from PyQt6.QtCore import QTimer, Qt, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen, QMouseEvent, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QSlider,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QFrame,
    QStyleOptionSlider,
    QStyle,
)

from .visualizer_canvas import VisualizerCanvas
from src.audio.audio import open_audio_stream, process_live_chunk
from src.ui.popups import VolumePopup
from src.ui.sidebar import SidebarPanel
from src.audio.audio_player import AudioPlayer
from src.audio.audio_manager import AudioManager
from src.ui.timeline_control import TimelineControl
from assets import Icons

import time


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Custom Audio Visualizer Studio")
        self.resize(1100, 700)
        self.setMouseTracking(True)

        self.is_playing = False
        self.current_mode = "file"
        self.sidebar_visible = True
        self.track_duration = 0.0
        
        # Instantiate dedicated Audio Manager
        self.audio_manager = AudioManager()

        # --- ROOT CONTAINER & LAYOUT ---
        root_widget = QWidget(self)
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.canvas = VisualizerCanvas(root_widget)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # --- 1. PARAMETER PANEL (Sidebar) ---
        self.sidebar = SidebarPanel(
            root_widget, 
            initial_bar_width=self.canvas.bar_width, 
            initial_gap_size=self.canvas.gap_size
        )

        # Connect sidebar signals cleanly
        self.sidebar.hide_requested.connect(self.hide_sidebar)
        self.sidebar.bar_width_changed.connect(lambda v: setattr(self.canvas, 'bar_width', v) or self.canvas.update())
        self.sidebar.gap_size_changed.connect(lambda v: setattr(self.canvas, 'gap_size', v) or self.canvas.update())
        self.sidebar.force_squares_changed.connect(lambda s: setattr(self.canvas, 'force_squares', (s == 2)) or self.canvas.update())
        self.sidebar.position_changed.connect(lambda x, y: self.canvas.set_offset(x, -y))
        self.canvas.position_changed.connect(self.sidebar.update_position_spinboxes)
        
        self.sidebar.bar_count_changed.connect(lambda v: setattr(self.canvas, 'num_bars', v) or setattr(self.canvas, 'current_amplitudes', np.zeros(v)) or setattr(self.canvas, 'target_amplitudes', np.zeros(v)) or self.canvas.update())
        self.sidebar.radius_changed.connect(lambda v: setattr(self.canvas, 'inner_radius', v))
        self.sidebar.max_length_changed.connect(lambda v: setattr(self.canvas, 'max_bar_length', v))
        self.sidebar.style_changed.connect(lambda text: self.canvas.set_style({"Circular": "circular", "Linear": "linear", "Symmetric Waveform": "symmetric", "Equalizer Orbit": "orbit", "Dual Wave": "dual_wave"}.get(text, "circular")))
        self.sidebar.template_selected.connect(self.canvas.set_template)
        
        self.sidebar.audio_file_selected.connect(self.update_audio_path)
        self.sidebar.audio_source_changed.connect(self.on_audio_source_changed)
        self.sidebar.device_selected.connect(self.on_device_selected)

        # Connect color customization widgets to the canvas
        self.sidebar.color_mode_changed.connect(self.canvas.set_color_mode)
        self.sidebar.color_changed.connect(self.canvas.set_solid_color)
        self.sidebar.cycle_speed_changed.connect(self.canvas.set_cycle_speed)

        self.sidebar.glow_changed.connect(self.canvas.set_glow_intensity)
        self.sidebar.glow_style_changed.connect(self.canvas.set_glow_style)
        self.sidebar.glow_angle_changed.connect(self.canvas.set_glow_angle)

        self.sidebar.glow_distance_changed.connect(lambda val: setattr(self.canvas, 'glow_distance', float(val)))
        self.sidebar.glow_distance_changed.connect(self.canvas.update)

        self.sidebar.glow_layers_changed.connect(lambda val: setattr(self.canvas, 'glow_layers', int(val)))
        self.sidebar.glow_layers_changed.connect(self.canvas.update)

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.canvas)
        root_layout.addLayout(content_layout)

        # --- 3. BOTTOM MEDIA CONTROL BAR (Initialize FIRST so attributes exist) ---
        self.timeline_control = TimelineControl(root_widget)
        self.timeline_control.play_clicked.connect(self.toggle_play_pause)
        self.timeline_control.seek_moved.connect(self.seek_timeline)
        self.timeline_control.volume_changed.connect(self.update_volume)
        self.timeline_control.setVisible(False)

        # Expose references safely after TimelineControl is created
        self.play_btn = self.timeline_control.play_btn
        self.vol_btn = self.timeline_control.vol_btn
        self.vol_popup = self.timeline_control.vol_popup
        self.time_label = self.timeline_control.time_label
        self.timeline_slider = self.timeline_control.timeline_slider
        self.control_bar = self.timeline_control

        root_layout.addWidget(self.timeline_control)
        self.setCentralWidget(root_widget)

        # --- TRIGGER BUTTON (Attached to root_widget and raised on top) ---
        self.trigger_btn = QPushButton("▶", root_widget)
        self.trigger_btn.setFixedWidth(24)
        self.trigger_btn.setFixedHeight(80)
        self.trigger_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; color: #00ff96; border: 1px solid #444; border-top-right-radius: 4px; border-bottom-right-radius: 4px; }
            QPushButton:hover { background-color: #353535; border-color: #00ff96; }
        """)
        self.trigger_btn.hide()
        self.trigger_btn.raise_()
        self.trigger_btn.clicked.connect(self.show_sidebar)

        # --- 4. PLAYBACK SYNC TIMER ---
        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(16)
        self.playback_timer.timeout.connect(self.update_playback_progress)
        self.playback_timer.start()

    def hide_sidebar(self):
        self.sidebar.setVisible(False)
        self.sidebar_visible = False
        if hasattr(self, 'trigger_btn'):
            self.trigger_btn.show()
        self.canvas.updateGeometry()
        self.canvas.update()

    def show_sidebar(self):
        if hasattr(self, 'trigger_btn'):
            self.trigger_btn.hide()
        self.sidebar.setVisible(True)
        self.sidebar_visible = True
        self.canvas.updateGeometry()
        self.canvas.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'trigger_btn') and hasattr(self, 'control_bar'):
            y_pos = (self.height() - self.trigger_btn.height() - self.control_bar.height()) // 2
            self.trigger_btn.move(0, y_pos)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.sidebar_visible and event.pos().x() <= 25:
            self.trigger_btn.show()
        super().mouseMoveEvent(event)

    def toggle_play_pause(self):
        if not hasattr(self, "audio_player") or not self.audio_player.is_loaded:
            return

        if self.is_playing:
            self.audio_player.pause()
            self.play_btn.setIcon(QIcon(str(Icons.PLAY_BTN_24)))
            self.is_playing = False
        else:
            if self.current_time_sec >= self.track_duration:
                self.current_time_sec = 0.0
                self.audio_player.play(start_sec=0.0)
            else:
                self.audio_player.unpause()
            
            self.playback_start_wall_time = time.perf_counter()
            self.playback_start_audio_sec = self.current_time_sec

            self.play_btn.setIcon(QIcon(str(Icons.PAUSE_BTN_24)))
            self.is_playing = True

    def seek_timeline(self, position):
        if hasattr(self, "track_duration") and self.track_duration > 0:
            target_sec = (position / 1000.0) * self.track_duration
            self.current_time_sec = target_sec
            
            self.playback_start_wall_time = time.perf_counter()
            self.playback_start_audio_sec = target_sec
            
            if hasattr(self, "audio_player"):
                self.audio_player.seek(target_sec)
                if not self.is_playing:
                    self.audio_player.pause()
            
            self.time_label.setText(f"{self.format_time(target_sec)} / {self.format_time(self.track_duration)}")
            
            if hasattr(self.canvas, "seek_to_time") and hasattr(self, "audio_stream") and self.audio_stream is not None:
                self.canvas.seek_to_time(target_sec)
                amplitudes = self.audio_player.get_amplitudes_at_time(
                    target_sec,
                    chunk_size=self.canvas.chunk_size,
                    num_bins=self.canvas.num_bars,
                    audio_stream=self.audio_stream
                )
                self.canvas.push_amplitudes(amplitudes)

    def format_time(self, seconds):
        if math.isnan(seconds) or seconds < 0:
            return "0:00"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    def init_audio(self, file_path):
        if not file_path:
            return
            
        self.audio_file_path = file_path
        self.audio = Path(file_path)

        self.audio_player = AudioPlayer()
        success = self.audio_player.load_file(file_path)
        
        if success:
            self.track_duration = self.audio_player.get_duration()
            self.current_time_sec = 0.0

            self.audio_player.set_volume(50.0)
            
            self.audio_stream = open_audio_stream(file_path)
            self.canvas.set_audio_source(self.audio_stream)
            
            self.is_playing = False

            total_str = self.format_time(self.track_duration)
            self.time_label.setText(f"0:00 / {total_str}")
            self.timeline_control.setVisible(True)

    def update_playback_progress(self):
        if not self.is_playing:
            return

        if self.current_mode in ["mic", "desktop"]:
            if hasattr(self.audio_manager, "audio_queue") and self.audio_manager.audio_queue is not None:
                try:
                    latest_chunk = None
                    while not self.audio_manager.audio_queue.empty():
                        latest_chunk = self.audio_manager.audio_queue.get_nowait()

                    if latest_chunk is not None and len(latest_chunk) > 0:
                        _, binned = process_live_chunk(
                            latest_chunk, 
                            sample_rate=44100, 
                            num_bins=self.canvas.num_bars,
                            gain=8.0
                        )

                        if binned is not None and len(binned) > 0:
                            if not hasattr(self, "previous_binned") or len(self.previous_binned) != len(binned):
                                self.previous_binned = binned
                            else:
                                binned = 0.4 * binned + 0.6 * self.previous_binned
                                self.previous_binned = binned

                            self.canvas.push_amplitudes(binned)
                            self.canvas.update()
                except Exception as e:
                    print(f"Live stream queue error: {e}")
            return

        if not hasattr(self, "audio_player") or not self.audio_player.is_loaded:
            return

        if not hasattr(self, "playback_start_wall_time"):
            self.playback_start_wall_time = time.perf_counter()
            self.playback_start_audio_sec = self.current_time_sec

        elapsed_real_time = time.perf_counter() - self.playback_start_wall_time
        current_sec = min(self.track_duration, self.playback_start_audio_sec + elapsed_real_time)

        self.current_time_sec = current_sec
        self.time_label.setText(f"{self.format_time(current_sec)} / {self.format_time(self.track_duration)}")
        
        if self.track_duration > 0 and not self.timeline_slider.isSliderDown():
            progress = int((current_sec / self.track_duration) * 1000)
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setValue(progress)
            self.timeline_slider.blockSignals(False)
        
        if hasattr(self, "audio_stream") and self.audio_stream is not None:
            amplitudes = self.audio_player.get_amplitudes_at_time(
                current_sec,
                chunk_size=self.canvas.chunk_size,
                num_bins=self.canvas.num_bars,
                audio_stream=self.audio_stream
            )
            self.canvas.push_amplitudes(amplitudes)
            self.canvas.update()

    def update_volume(self, value):
        if hasattr(self, "audio_player"):
            self.audio_player.set_volume(value)

    def eventFilter(self, obj, event):
        if obj == self.timeline_slider and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                opt = QStyleOptionSlider()
                self.timeline_slider.initStyleOption(opt)
                
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                
                style = self.timeline_slider.style()
                handle_rect = style.subControlRect(
                    QStyle.ComplexControl.CC_Slider, 
                    opt, 
                    QStyle.SubControl.SC_SliderHandle, 
                    self.timeline_slider
                )
                
                if handle_rect.contains(pos):
                    return super().eventFilter(obj, event)
                
                val = QStyle.sliderValueFromPosition(
                    self.timeline_slider.minimum(),
                    self.timeline_slider.maximum(),
                    pos.x(),
                    self.timeline_slider.width(),
                    opt.upsideDown
                )
                
                self.timeline_slider.setValue(val)
                self.seek_timeline(val)
                return True
                
        return super().eventFilter(obj, event)

    def on_audio_source_changed(self, text):
        self.audio_manager.stop_stream()

        is_desktop = "Desktop" in text
        is_mic = "Microphone" in text

        # Safely check and handle sidebar device combo if it exists
        if hasattr(self.sidebar, "device_combo") and self.sidebar.device_combo is not None:
            self.sidebar.device_combo.blockSignals(True)
            self.sidebar.device_combo.clear()

        if is_desktop or is_mic:
            if hasattr(self, "audio_player") and self.audio_player.is_loaded:
                self.audio_player.pause()
            self.is_playing = False
            self.timeline_control.setVisible(False)
            self.play_btn.setIcon(QIcon(str(Icons.PLAY_BTN_24)))
            
            # Clear out the visualizer bars so they flatline immediately
            if hasattr(self, "canvas") and hasattr(self.canvas, "num_bars"):
                self.canvas.push_amplitudes(np.zeros(self.canvas.num_bars))
                self.canvas.update()

        if not is_desktop and not is_mic:
            self.current_mode = "file"
            self.is_playing = False
            
            # Clear out the audio stream and flatline the visualizer canvas
            if hasattr(self, "audio_stream") and self.audio_stream is not None:
                self.audio_stream = None
            if hasattr(self, "canvas") and hasattr(self.canvas, "num_bars"):
                self.canvas.push_amplitudes(np.zeros(self.canvas.num_bars))
                self.canvas.update()
                
            # Hide the timeline until a new track is explicitly loaded
            if hasattr(self, "timeline_control"):
                self.timeline_control.setVisible(False)
                
            self.setup_file_mode_ui(enabled=True)
            if hasattr(self, "sidebar") and hasattr(self.sidebar, "device_combo") and self.sidebar.device_combo is not None:
                self.sidebar.device_combo.setVisible(False)
                self.sidebar.device_combo.blockSignals(False)
            return

        if is_desktop:
            self.current_mode = "desktop"
            self.setup_file_mode_ui(enabled=False)
            if hasattr(self.sidebar, "device_combo") and self.sidebar.device_combo is not None:
                self.sidebar.device_combo.setVisible(False)
                self.sidebar.device_combo.blockSignals(False)

            info = self.audio_manager.get_default_desktop_loopback()
            if info:
                self.audio_manager.start_stream(info['index'], info['channels'], info['rate'])

        elif is_mic:
            self.current_mode = "mic"
            self.setup_file_mode_ui(enabled=False)
            if hasattr(self.sidebar, "device_combo") and self.sidebar.device_combo is not None:
                self.sidebar.device_combo.setVisible(True)

                devices = self.audio_manager.get_devices()
                target_index = None
                for idx, name in devices:
                    self.sidebar.device_combo.addItem(f"[{idx}] {name}", userData=idx)
                    if target_index is None:
                        target_index = idx

                self.sidebar.device_combo.blockSignals(False)
                if self.sidebar.device_combo.count() > 0:
                    self.on_device_selected(self.sidebar.device_combo.currentIndex())

    def on_device_selected(self, index):
        if index < 0:
            return

        # Ensure we are currently in microphone mode
        if self.current_mode != "mic":
            return

        device_idx = self.sidebar.device_combo.itemData(index)
        if device_idx is None:
            return

        try:
            dev_info = self.audio_manager.pyaudio_instance.get_device_info_by_index(device_idx)
            channels = min(2, max(1, int(dev_info['maxInputChannels'])))
            rate = int(dev_info['defaultSampleRate']) if int(dev_info['defaultSampleRate']) > 0 else 44100

            self.audio_manager.start_stream(device_idx, channels, rate)
        except Exception as e:
            print(f"Failed to open microphone device {device_idx}: {e}")

    def setup_file_mode_ui(self, enabled: bool):
        has_play_btn = hasattr(self, "play_btn") and self.play_btn is not None
        has_slider = hasattr(self, "timeline_slider") and self.timeline_slider is not None

        if has_play_btn:
            self.play_btn.setEnabled(enabled)
        if has_slider:
            self.timeline_slider.setEnabled(enabled)

        if enabled:
            if has_play_btn:
                self.play_btn.setIcon(QIcon(str(Icons.PAUSE_BTN_24)))
            self.is_playing = True
        else:
            if hasattr(self, "audio_player") and self.audio_player.is_loaded:
                self.audio_player.pause()
            if has_play_btn:
                self.play_btn.setIcon(QIcon(str(Icons.PLAY_BTN_24)))
            self.is_playing = True

    def update_audio_path(self, path_str):
        if not path_str:
            return
            
        # Initialize and load the dynamically selected file
        self.init_audio(path_str)
        
        # Automatically start playing and visualizing the chosen file
        if hasattr(self, "audio_player") and self.audio_player.is_loaded:
            self.audio_player.play(start_sec=0.0)
            self.playback_start_wall_time = time.perf_counter()
            self.playback_start_audio_sec = 0.0
            
            self.is_playing = True
            self.play_btn.setIcon(QIcon(str(Icons.PAUSE_BTN_24)))
            print(f"Loaded and started dynamic audio path: {self.audio}")
