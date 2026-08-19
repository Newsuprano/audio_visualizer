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
    HOME_48C = (CLEAR_DIR_48 / "home_48.svg")

    ## Head Categories - FILL
    SETTINGS_48F = (FILL_DIR_48 / "settings_48F.svg")
    PALETTE_48F = (FILL_DIR_48 / "palette_48F.svg")
    BROWSE_48F = (FILL_DIR_48 / "browse_48F.svg")
    BOOKMARK_48F = (FILL_DIR_48 / "bookmark_48F.svg")
    HOME_48F = (FILL_DIR_48 / "home_48F.svg")

    # ====================

    ## Audio Mode - CLEAR
    AUDIO_FILE_24C = (CLEAR_DIR_24 / "audio_file_24.svg")
    MIC_24C = (CLEAR_DIR_24 / "mic_24.svg")
    DESKTOP_AUDIO_24C = (CLEAR_DIR_24 / "computer_sound_24.svg") 

    ## Audio Mode - FILL
    AUDIO_FILE_24F = (FILL_DIR_24 / "audio_file_24F.svg")
    MIC_24F = (FILL_DIR_24 / "mic_24F.svg")
    DESKTOP_AUDIO_24F = (FILL_DIR_24 / "computer_sound_24F.svg")

    # ====================

    ## Timeline
    PLAY_BTN_24 = (FILL_DIR_24 / "play_arrow_24F.svg")
    PAUSE_BTN_24 = (FILL_DIR_24 / "pause_24F.svg")
    VOLUME_OFF_24 = (CLEAR_DIR_24 / "volume_off_24.svg")
    VOLUME_DOWN_24 = (CLEAR_DIR_24 / "volume_down_24.svg")
    VOLUME_UP_24 = (CLEAR_DIR_24 / "volume_up_24.svg")