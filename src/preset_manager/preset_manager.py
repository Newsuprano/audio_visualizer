from pathlib import Path
import json
from datetime import datetime
from PyQt6.QtWidgets import QSpinBox, QSlider, QCheckBox, QComboBox, QLineEdit
from PyQt6.QtGui import QColor

PRESETS_DIR = Path("presets")

def ensure_presets_folder():
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)

def get_widget_mapping(sidebar_panel):
    """Centralized mapping of all JSON configuration paths to UI widgets."""
    return {
        "canvas_layout": {
            "x": getattr(sidebar_panel, 'spin_x', None),
            "y": getattr(sidebar_panel, 'spin_y', None),
            "bar_width": getattr(sidebar_panel, 'spin_bar_width', None),
            "gap_size": getattr(sidebar_panel, 'spin_gap_size', None),
            "force_squares": getattr(sidebar_panel, 'check_square_blocks', None),
        },
        "geometry": {
            "bar_count": getattr(sidebar_panel, 'bars_slider', None),
            "inner_radius": getattr(sidebar_panel, 'radius_slider', None),
            "max_height": getattr(sidebar_panel, 'length_slider', None),
        },
        "style": {
            "visual_style": getattr(sidebar_panel, 'style_combo', None),
        },
        "colors": {
            "color_mode": getattr(sidebar_panel, 'color_mode_combo', None), # Update name to match your sidebar
            "cycle_speed": getattr(sidebar_panel, 'cycle_speed_spin', None),   # Update name to match your sidebar
            # Note: For solid color buttons, you can store RGB lists [r, g, b] or hex strings
        },
        "glow_settings": {
            "intensity": getattr(sidebar_panel, 'glow_intensity_slider', None), # Update to match your widget names
            "distance": getattr(sidebar_panel, 'glow_distance_slider', None),
            "angle": getattr(sidebar_panel, 'glow_angle_spin', None),
            "style": getattr(sidebar_panel, 'glow_style_combo', None),
            "layers": getattr(sidebar_panel, 'glow_layers_spin', None),
        }
    }

def load_preset(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_default_preset():
    default_path = PRESETS_DIR / "default.json"
    if default_path.exists():
        try:
            return load_preset(default_path)
        except Exception as e:
            print(f"Failed to load default preset: {e}")
            
    # Fallback default dictionary so the canvas never renders blank
    return {
        "canvas_layout": {
            "x": 0,
            "y": 0,
            "bar_width": 10,
            "gap_size": 4,
            "force_squares": False,
        },
        "geometry": {
            "bar_count": 64,
            "inner_radius": 120,
            "max_height": 180,
        },
        "style": {
            "visual_style": "Lines",
        },
        "colors": {
            "color_mode": "Gradient (Rainbow)",
            "cycle_speed": 3,
            "solid_color": [0, 255, 150]
        },
        "glow_settings": {
            "intensity": 0.0,
            "distance": 50.0,
            "angle": 0.0,
            "style": "Burst",
            "layers": 6
        }
    }

def apply_preset_to_ui(sidebar_panel, config_data):
    """Loops through the mapping to populate UI widgets from a loaded preset."""
    mapping = get_widget_mapping(sidebar_panel)
    
    for section_key, section_dict in mapping.items():
        section_values = config_data.get(section_key, {})
        for prop_key, widget in section_dict.items():
            if widget is None or prop_key not in section_values:
                continue
                
            val = section_values[prop_key]
            
            if isinstance(widget, (QSpinBox, QSlider)):
                widget.setValue(int(val))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QComboBox):
                index = widget.findText(str(val))
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val))

def save_current_preset(sidebar_panel, preset_name=None):
    """Loops through the mapping to serialize active UI states into JSON."""
    ensure_presets_folder()
    
    if not preset_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preset_name = f"preset_{timestamp}"
        
    if not preset_name.endswith(".json"):
        preset_name += ".json"
        
    file_path = PRESETS_DIR / preset_name
    mapping = get_widget_mapping(sidebar_panel)
    config_data = {}
    
    for section_key, section_dict in mapping.items():
        config_data[section_key] = {}
        for prop_key, widget in section_dict.items():
            if widget is None:
                continue
                
            if isinstance(widget, (QSpinBox, QSlider)):
                config_data[section_key][prop_key] = widget.value()
            elif isinstance(widget, QCheckBox):
                config_data[section_key][prop_key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                config_data[section_key][prop_key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                config_data[section_key][prop_key] = widget.text()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
        
    return file_path