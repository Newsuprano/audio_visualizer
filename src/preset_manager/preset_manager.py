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
            "color_mode": getattr(sidebar_panel, 'color_mode_combo', None),
            "cycle_speed": getattr(sidebar_panel, 'cycle_speed_slider', None),
        },
        "glow_settings": {
            "intensity": getattr(sidebar_panel, 'glow_slider', None),
            "distance": getattr(sidebar_panel, 'glow_distance_slider', None),
            "angle": getattr(sidebar_panel, 'angle_slider', None),
            "style": getattr(sidebar_panel, 'glow_style_combo', None),
            "layers": getattr(sidebar_panel, 'glow_layers_slider', None),
        }
    }

def load_preset(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_default_preset():
    default_path = PRESETS_DIR / "default.json"
    
    # If default.json doesn't exist yet, create it with baseline values
    if not default_path.exists():
        ensure_presets_folder()
        default_config = {
            "canvas_layout": {
                "x": 0,
                "y": 0,
                "bar_width": 10,
                "gap_size": 4,
                "force_squares": False
            },
            "geometry": {
                "bar_count": 64,
                "inner_radius": 120,
                "max_height": 180
            },
            "style": {
                "template": "lines",
                "visualizer_style": "circular"
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
        try:
            with open(default_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            print(f"Created new default preset at: {default_path}")
        except Exception as e:
            print(f"Failed to create default preset file: {e}")
            return default_config

    # Now load and return it normally from the file
    try:
        return load_preset(default_path)
    except Exception as e:
        print(f"Failed to load default preset: {e}")
        return {}

def apply_preset_to_ui(sidebar_panel, config_data):
    """Loops through the mapping to populate UI widgets and non-widget states from a loaded preset."""
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

    # Explicitly restore template string state
    style_vals = config_data.get("style", {})
    if "template" in style_vals and hasattr(sidebar_panel, 'current_template'):
        sidebar_panel.current_template = style_vals["template"]

    # Explicitly restore solid color RGB values
    color_vals = config_data.get("colors", {})
    if "solid_color" in color_vals and hasattr(sidebar_panel, 'selected_solid_color'):
        rgb = color_vals["solid_color"]
        if isinstance(rgb, list) and len(rgb) == 3:
            sidebar_panel.selected_solid_color = QColor(rgb[0], rgb[1], rgb[2])
            if hasattr(sidebar_panel, 'update_color_button_style'):
                sidebar_panel.update_color_button_style(sidebar_panel.selected_solid_color)

def save_current_preset(sidebar_panel, preset_name=None):
    """Loops through mapping and explicitly serializes templates and solid color RGB into JSON."""
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
                print(f"⚠️ Warning: Widget for '{section_key} -> {prop_key}' was None and skipped!")
                continue
                
            if isinstance(widget, (QSpinBox, QSlider)):
                config_data[section_key][prop_key] = widget.value()
            elif isinstance(widget, QCheckBox):
                config_data[section_key][prop_key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                config_data[section_key][prop_key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                config_data[section_key][prop_key] = widget.text()

    # Explicitly save template state
    if "style" not in config_data:
        config_data["style"] = {}
    if hasattr(sidebar_panel, 'current_template'):
        config_data["style"]["template"] = sidebar_panel.current_template

    # Explicitly save solid color RGB values
    if hasattr(sidebar_panel, 'selected_solid_color'):
        c = sidebar_panel.selected_solid_color
        if "colors" not in config_data:
            config_data["colors"] = {}
        config_data["colors"]["solid_color"] = [c.red(), c.green(), c.blue()]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
        
    return file_path