"""
Application Configuration and Constants
Regex Stripper (RegexStripper)
"""

import sys
from enum import Enum
from pathlib import Path

# Application Metadata
APP_NAME = "Regex Stripper"
APP_VERSION = "1.3.0"
APP_TITLE = f"{APP_NAME} v{APP_VERSION}"

# Project Paths & Asset Directories
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
APP_ICON_PATH = ASSETS_DIR / "app.ico"
APP_PNG_PATH = ASSETS_DIR / "app.png"

ICON_SUN = ICONS_DIR / "sun.svg"
ICON_MOON = ICONS_DIR / "moon.svg"
ICON_REPLACE = ICONS_DIR / "replace_white.svg"
ICON_DELETE = ICONS_DIR / "delete_white.svg"
ICON_COPY = ICONS_DIR / "copy_white.svg"
ICON_PASTE = ICONS_DIR / "paste.svg"
ICON_CLEAR = ICONS_DIR / "clear.svg"
ICON_UNDO = ICONS_DIR / "undo.svg"
ICON_BOOK = ICONS_DIR / "book.svg"
ICON_BOOKMARK = ICONS_DIR / "bookmark.svg"
ICON_SAVE = ICONS_DIR / "save_white.svg"
ICON_ARROW_UP = ICONS_DIR / "arrow_up.svg"
ICON_ARROW_DOWN = ICONS_DIR / "arrow_down.svg"
ICON_DIFF = ICONS_DIR / "diff.svg"
ICON_DEDUP = ICONS_DIR / "dedup.svg"
ICON_REDO = ICONS_DIR / "redo.svg"
ICON_OPEN = ICONS_DIR / "open.svg"
ICON_PIPELINE = ICONS_DIR / "pipeline.svg"
ICON_LINES = ICONS_DIR / "lines.svg"

# Window Dimensions
DEFAULT_WINDOW_WIDTH = 1100
DEFAULT_WINDOW_HEIGHT = 780
MIN_WINDOW_WIDTH = 820
MIN_WINDOW_HEIGHT = 540

# History & Settings Configuration
MAX_HISTORY_ITEMS = 30
MAX_UNDO_STEPS = 20
HISTORY_FILE_NAME = ".regexstripper_history.json"
HISTORY_FILE_PATH = Path.home() / HISTORY_FILE_NAME
SETTINGS_FILE_NAME = ".regexstripper_settings.json"
SETTINGS_FILE_PATH = Path.home() / SETTINGS_FILE_NAME
PRESETS_FILE_NAME = ".regexstripper_user_presets.json"
PRESETS_FILE_PATH = Path.home() / PRESETS_FILE_NAME
PIPELINES_FILE_NAME = ".regexstripper_pipelines.json"
PIPELINES_FILE_PATH = Path.home() / PIPELINES_FILE_NAME

# Debounce Timing (milliseconds)
HIGHLIGHT_DEBOUNCE_MS = 120

# Deletion Modes
class DeletionMode(str, Enum):
    DELETE_MATCHES = "delete_matches"
    DELETE_NON_MATCHES = "delete_non_matches"
    DELETE_MATCHING_LINES = "delete_matching_lines"
    KEEP_MATCHING_LINES = "keep_matching_lines"

# Themes
class AppTheme(str, Enum):
    LIGHT = "light"
    DARK = "dark"

# Highlight Colors - Light Theme
COLOR_MATCH_HIGHLIGHT_LIGHT_BG = "#FFE082"   # Warm amber
COLOR_MATCH_HIGHLIGHT_LIGHT_FG = "#1E1E1E"
COLOR_INVERT_HIGHLIGHT_LIGHT_BG = "#FFCCBC"  # Soft peach/coral
COLOR_INVERT_HIGHLIGHT_LIGHT_FG = "#1E1E1E"

# Diff Preview Colors - Light Theme
COLOR_DIFF_INSERT_LIGHT_BG = "#C8E6C9"       # Material Green 100
COLOR_DIFF_INSERT_LIGHT_FG = "#1B5E20"       # Material Green 900
COLOR_DIFF_DELETE_LIGHT_BG = "#FFCDD2"       # Material Red 100
COLOR_DIFF_DELETE_LIGHT_FG = "#B71C1C"       # Material Red 900

# Highlight Colors - Dark Theme
COLOR_MATCH_HIGHLIGHT_DARK_BG = "#B45309"    # High-contrast amber/gold
COLOR_MATCH_HIGHLIGHT_DARK_FG = "#FFFFFF"
COLOR_INVERT_HIGHLIGHT_DARK_BG = "#991B1B"   # High-contrast deep red
COLOR_INVERT_HIGHLIGHT_DARK_FG = "#FFFFFF"

# Diff Preview Colors - Dark Theme
COLOR_DIFF_INSERT_DARK_BG = "#1E4620"        # Forest Green
COLOR_DIFF_INSERT_DARK_FG = "#A5D6A7"        # Pastel Green
COLOR_DIFF_DELETE_DARK_BG = "#4A1515"        # Dark Maroon
COLOR_DIFF_DELETE_DARK_FG = "#EF9A9A"        # Salmon Red

# Status Colors
COLOR_STATUS_MATCH = "#16A34A"               # Emerald green
COLOR_STATUS_NO_MATCH = "#94A3B8"            # Slate gray
COLOR_STATUS_ERROR = "#DC2626"               # Crimson red

# Monospace Font Fallbacks
MONOSPACE_FONTS = ["Cascadia Code", "Consolas", "Courier New", "monospace"]
