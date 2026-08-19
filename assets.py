from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
ICONS_DIR = ROOT_DIR / "assets" / "images" / "icons"

CLEAR_DIR_24 = ROOT_DIR / ICONS_DIR / "x24" / "clear"
FILL_DIR_24 = ROOT_DIR / ICONS_DIR / "x24" / "fill"
CLEAR_DIR_48 = ROOT_DIR / ICONS_DIR / "x48" / "clear"
FILL_DIR_48 = ROOT_DIR / ICONS_DIR / "x48" / "fill"

class Icons:

    ## Head Categories - CLEAR
    SETTINGS_48C = (CLEAR_DIR_48 / "settings_48.svg")
    TUNE_48 = (CLEAR_DIR_48 / "tune_48.svg")
    PALETTE_48C = (CLEAR_DIR_48 / "palette_48.svg")
    BOOKMARK_48C = (CLEAR_DIR_48 / "bookmark_48.svg")
    BROWSE_48C = (CLEAR_DIR_48 / "browse_48.svg")
    EQUALIZER_48 = (CLEAR_DIR_48 / "equalizer_48.svg")

    ## Head Categories - FILL
    SETTINGS_48F = (FILL_DIR_48 / "settings_48.svg")
    PALETTE_48F = (FILL_DIR_48 / "palette_48F.svg")
    BROWSE_48F = (FILL_DIR_48 / "browse_48F.svg")
    BOOKMARK_48F = (FILL_DIR_48 / "bookmark_48F.svg")


    ##Regular Icons
    
