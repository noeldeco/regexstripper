"""
Preset Manager for Regex Stripper
Merges built-in presets from src/presets.py with user-saved presets in ~/.regexstripper_user_presets.json.
Allows saving and removing presets directly from the GUI (works in frozen EXE too).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Optional
from src.config import PRESETS_FILE_PATH
from src.presets import PRESET_EXPRESSIONS


class PresetManager:
    """Manages preset regex expressions across sessions."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or PRESETS_FILE_PATH
        self._user_presets: List[Dict[str, str]] = []
        self.load()

    def load(self) -> None:
        """Loads user presets from JSON."""
        if not self.file_path.exists():
            self._user_presets = []
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._user_presets = [
                        item for item in data
                        if isinstance(item, dict) and "name" in item and "expression" in item
                    ]
        except Exception:
            self._user_presets = []

    def save(self) -> None:
        """Saves user presets to JSON."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._user_presets, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_all_presets(self) -> List[Dict[str, str]]:
        """Returns built-in presets followed by user custom presets."""
        combined = list(PRESET_EXPRESSIONS)
        # Avoid duplicating names
        builtin_names = {p["name"] for p in PRESET_EXPRESSIONS}
        for u in self._user_presets:
            if u["name"] not in builtin_names:
                combined.append(u)
        return combined

    def add_user_preset(self, name: str, expression: str, description: str = "") -> bool:
        """Adds a new user preset and persists to disk."""
        if not name or not expression:
            return False

        # If name already exists in user presets, update it
        for item in self._user_presets:
            if item["name"] == name:
                item["expression"] = expression
                item["description"] = description
                self.save()
                return True

        self._user_presets.append({
            "name": name,
            "expression": expression,
            "description": description
        })
        self.save()
        return True

    def remove_user_preset(self, name: str) -> bool:
        """Removes a user preset if present."""
        initial_len = len(self._user_presets)
        self._user_presets = [p for p in self._user_presets if p["name"] != name]
        if len(self._user_presets) < initial_len:
            self.save()
            return True
        return False

