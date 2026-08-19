from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QSlider, QStyleOptionSlider, QStyle
from PyQt6.QtGui import QIcon
from .popups import VolumePopup
from assets import Icons

class TimelineControl(QFrame):
    play_clicked = pyqtSignal()
    seek_moved = pyqtSignal(int)
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: #181818; border-top: 1px solid #282828;")
        
        bar_layout = QHBoxLayout(self)
        bar_layout.setContentsMargins(15, 0, 15, 0)
        bar_layout.setSpacing(15)

        control_btn_style = """
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: #2a2a2a; border-radius: 4px; }
        """

        # Play / Pause Button with fixed custom icon styling
        self.play_btn = QPushButton()
        self.play_btn.setIcon(QIcon(str(Icons.PLAY_BTN_24)))
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setStyleSheet(control_btn_style)
        self.play_btn.clicked.connect(self.play_clicked.emit)
        bar_layout.addWidget(self.play_btn)

        # Volume Button with fixed custom icon styling
        self.vol_btn = QPushButton()
        self.vol_btn.setIcon(QIcon(str(Icons.VOLUME_UP_24)))
        self.vol_btn.setFixedSize(30, 30)
        self.vol_btn.setStyleSheet(control_btn_style)
        
        self.vol_popup = VolumePopup(self)
        self.vol_popup.hide()
        self.vol_popup.slider.setValue(50)
        self.vol_popup.slider.valueChanged.connect(self.on_volume_slider_changed)
        
        self.vol_btn.enterEvent = self.show_volume_popup
        self.vol_btn.leaveEvent = self.check_hide_volume_popup
        bar_layout.addWidget(self.vol_btn)

        # Time Label
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        bar_layout.addWidget(self.time_label)

        # Timeline Slider with forced circular handle fix
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 1000)
        self.timeline_slider.setValue(0)
        self.timeline_slider.setStyleSheet("""
            QSlider::groove:horizontal { 
                background: #666666; 
                height: 4px; 
                border-radius: 2px; 
            }
            QSlider::sub-page:horizontal { 
                background: #33b5e5; 
                height: 4px; 
                border-radius: 2px; 
            }
            QSlider::handle:horizontal { 
                background: #33b5e5; 
                border: none; 
                outline: none;
                width: 12px; 
                min-width: 12px;
                max-width: 12px;
                height: 12px; 
                min-height: 12px;
                max-height: 12px;
                margin: -4px 0; 
                border-radius: 6px; 
            }
            QSlider::handle:horizontal:hover { 
                background: #4deeea; 
                outline: 2px solid #444444; 
                width: 16px; 
                min-width: 16px;
                max-width: 16px;
                height: 16px; 
                min-height: 16px;
                max-height: 16px;
                margin: -6px 0; 
                border-radius: 8px; 
            }
            QSlider::handle:horizontal:pressed { 
                background: #2ca0c9; 
                outline: 2px solid #222222; 
                width: 16px; 
                min-width: 16px;
                max-width: 16px;
                height: 16px; 
                min-height: 16px;
                max-height: 16px;
                margin: -6px 0; 
                border-radius: 8px; 
            }
        """)
        
        self.timeline_slider.sliderMoved.connect(self.seek_moved.emit)
        self.timeline_slider.installEventFilter(self)
        bar_layout.addWidget(self.timeline_slider, stretch=1)

    def on_volume_slider_changed(self, value):
        # Update icon based on volume level thresholds
        if value == 0:
            self.vol_btn.setIcon(QIcon(str(Icons.VOLUME_OFF_24)))  # Replace with your muted icon constant if named differently
        elif value < 50:
            self.vol_btn.setIcon(QIcon(str(Icons.VOLUME_DOWN_24))) # Replace with your medium icon constant if named differently
        else:
            self.vol_btn.setIcon(QIcon(str(Icons.VOLUME_UP_24)))
            
        self.volume_changed.emit(value)

    def show_volume_popup(self, event):
        global_pos = self.vol_btn.mapToGlobal(QPoint(0, 0)) if hasattr(self, 'vol_btn') else self.mapToGlobal(event.pos())
        x = global_pos.x() + (self.vol_btn.width() - self.vol_popup.width()) // 2
        y = global_pos.y() - self.vol_popup.height() - 5
        self.vol_popup.move(x, y)
        self.vol_popup.show()

    def check_hide_volume_popup(self, event):
        QTimer.singleShot(150, self._delayed_hide_check)

    def _delayed_hide_check(self):
        if hasattr(self, "vol_popup") and hasattr(self, "vol_btn"):
            is_over_popup = self.vol_popup.underMouse() or self.vol_popup.rect().contains(self.vol_popup.mapFromGlobal(self.cursor().pos()))
            is_over_btn = self.vol_btn.underMouse()
            if not is_over_popup and not is_over_btn:
                self.vol_popup.hide()

    def eventFilter(self, obj, event):
        if obj == self.timeline_slider and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                opt = QStyleOptionSlider()
                self.timeline_slider.initStyleOption(opt)
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                
                style = self.timeline_slider.style()
                handle_rect = style.subControlRect(
                    QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self.timeline_slider
                )
                
                if handle_rect.contains(pos):
                    return super().eventFilter(obj, event)
                
                val = QStyle.sliderValueFromPosition(
                    self.timeline_slider.minimum(), self.timeline_slider.maximum(),
                    pos.x(), self.timeline_slider.width(), opt.upsideDown
                )
                self.timeline_slider.setValue(val)
                self.seek_moved.emit(val)
                return True
        return super().eventFilter(obj, event)