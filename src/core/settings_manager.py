"""
Settings Manager for Regex Stripper
Persists user preferences across sessions: theme, window geometry,
editor font zoom, word wrap, and default regex/replacement options.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from src.config import SETTINGS_FILE_PATH, AppTheme


class SettingsManager:
    """Manages persistent application settings in JSON."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or SETTINGS_FILE_PATH
        self._settings: Dict[str, Any] = {
            "theme": AppTheme.LIGHT.value,
            "font_size": 11,
            "word_wrap": True,
            "ignore_case": False,
            "disable_multiline": False,
            "dot_all": False,
            "interpret_escapes": False,
            "window_geometry": None,  # {"x": int, "y": int, "width": int, "height": int}
        }
        self.load()

    @property
    def theme(self) -> AppTheme:
        val = self._settings.get("theme", AppTheme.LIGHT.value)
        try:
            return AppTheme(val)
        except ValueError:
            return AppTheme.LIGHT

    @theme.setter
    def theme(self, value: AppTheme) -> None:
        self._settings["theme"] = value.value
        self.save()

    @property
    def font_size(self) -> int:
        val = self._settings.get("font_size", 11)
        return int(val) if isinstance(val, (int, float)) and 7 <= val <= 32 else 11

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._settings["font_size"] = max(7, min(32, int(value)))
        self.save()

    @property
    def word_wrap(self) -> bool:
        return bool(self._settings.get("word_wrap", True))

    @word_wrap.setter
    def word_wrap(self, value: bool) -> None:
        self._settings["word_wrap"] = bool(value)
        self.save()

    @property
    def ignore_case(self) -> bool:
        return bool(self._settings.get("ignore_case", False))

    @ignore_case.setter
    def ignore_case(self, value: bool) -> None:
        self._settings["ignore_case"] = bool(value)
        self.save()

    @property
    def disable_multiline(self) -> bool:
        return bool(self._settings.get("disable_multiline", False))

    @disable_multiline.setter
    def disable_multiline(self, value: bool) -> None:
        self._settings["disable_multiline"] = bool(value)
        self.save()

    @property
    def dot_all(self) -> bool:
        return bool(self._settings.get("dot_all", False))

    @dot_all.setter
    def dot_all(self, value: bool) -> None:
        self._settings["dot_all"] = bool(value)
        self.save()

    @property
    def interpret_escapes(self) -> bool:
        return bool(self._settings.get("interpret_escapes", False))

    @interpret_escapes.setter
    def interpret_escapes(self, value: bool) -> None:
        self._settings["interpret_escapes"] = bool(value)
        self.save()

    @property
    def window_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        geom = self._settings.get("window_geometry")
        if isinstance(geom, dict):
            try:
                return (int(geom["x"]), int(geom["y"]), int(geom["width"]), int(geom["height"]))
            except (KeyError, ValueError, TypeError):
                return None
        return None

    @window_geometry.setter
    def window_geometry(self, value: Optional[Tuple[int, int, int, int]]) -> None:
        if value is None:
            self._settings["window_geometry"] = None
        else:
            x, y, w, h = value
            self._settings["window_geometry"] = {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
        self.save()

    def load(self) -> None:
        """Loads settings from JSON file."""
        if not self.file_path.exists():
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._settings.update(data)
        except Exception:
            pass

    def save(self) -> None:
        """Saves current settings to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass
