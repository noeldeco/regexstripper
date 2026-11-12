"""
Settings Manager for Regex Stripper
Persists user preferences such as active theme across sessions.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Dict, Any
from src.config import SETTINGS_FILE_PATH, AppTheme


class SettingsManager:
    """Manages persistent application settings in JSON."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or SETTINGS_FILE_PATH
        self._settings: Dict[str, Any] = {
            "theme": AppTheme.LIGHT.value
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

