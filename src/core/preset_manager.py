"""
Preset Manager for Regex Stripper
Merges built-in presets from src/presets.py with user-saved presets in ~/.regexstripper_user_presets.json.
Supports rich presets (optional replacement, flags, literal mode, action mode), editing, deletion,
and JSON import/export (works in both source and frozen EXE).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.config import PRESETS_FILE_PATH
from src.presets import PRESET_EXPRESSIONS


class PresetManager:
    """Manages preset regex expressions across sessions."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or PRESETS_FILE_PATH
        self._user_presets: List[Dict[str, Any]] = []
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
                        dict(item) for item in data
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

    @staticmethod
    def is_builtin(name: str) -> bool:
        """Returns True if the preset name belongs to the built-in presets list."""
        return any(p["name"] == name for p in PRESET_EXPRESSIONS)

    def get_all_presets(self) -> List[Dict[str, Any]]:
        """Returns built-in presets followed by user custom presets."""
        combined: List[Dict[str, Any]] = []
        for p in PRESET_EXPRESSIONS:
            entry = dict(p)
            entry["_builtin"] = True
            combined.append(entry)

        builtin_names = {p["name"] for p in PRESET_EXPRESSIONS}
        for u in self._user_presets:
            if u["name"] not in builtin_names:
                entry = dict(u)
                entry["_builtin"] = False
                combined.append(entry)
        return combined

    def get_user_presets(self) -> List[Dict[str, Any]]:
        """Returns a copy of user-created presets."""
        return [dict(p) for p in self._user_presets]

    def add_user_preset(
        self,
        name: str,
        expression: str,
        description: str = "",
        replacement: str = "",
        mode: Optional[str] = None,
        ignore_case: Optional[bool] = None,
        disable_multiline: Optional[bool] = None,
        dot_all: Optional[bool] = None,
        is_literal: Optional[bool] = None,
    ) -> bool:
        """Adds or updates a user preset and persists to disk."""
        if not name or not expression:
            return False

        record: Dict[str, Any] = {
            "name": name,
            "expression": expression,
            "description": description,
        }
        if replacement:
            record["replacement"] = replacement
        if mode is not None:
            record["mode"] = mode
        if ignore_case is not None:
            record["ignore_case"] = bool(ignore_case)
        if disable_multiline is not None:
            record["disable_multiline"] = bool(disable_multiline)
        if dot_all is not None:
            record["dot_all"] = bool(dot_all)
        if is_literal is not None:
            record["is_literal"] = bool(is_literal)

        for idx, item in enumerate(self._user_presets):
            if item["name"] == name:
                self._user_presets[idx] = record
                self.save()
                return True

        self._user_presets.append(record)
        self.save()
        return True

    def update_user_preset(
        self,
        old_name: str,
        new_name: str,
        expression: str,
        description: str = "",
        replacement: str = "",
        mode: Optional[str] = None,
        ignore_case: Optional[bool] = None,
        disable_multiline: Optional[bool] = None,
        dot_all: Optional[bool] = None,
        is_literal: Optional[bool] = None,
    ) -> bool:
        """Updates an existing user preset (supporting rename)."""
        if not old_name or not new_name or not expression:
            return False

        if old_name != new_name:
            self._user_presets = [p for p in self._user_presets if p["name"] != old_name]

        return self.add_user_preset(
            name=new_name,
            expression=expression,
            description=description,
            replacement=replacement,
            mode=mode,
            ignore_case=ignore_case,
            disable_multiline=disable_multiline,
            dot_all=dot_all,
            is_literal=is_literal,
        )

    def remove_user_preset(self, name: str) -> bool:
        """Removes a user preset if present."""
        initial_len = len(self._user_presets)
        self._user_presets = [p for p in self._user_presets if p["name"] != name]
        if len(self._user_presets) < initial_len:
            self.save()
            return True
        return False

    def export_presets(self, dest_path: Path) -> int:
        """Exports user presets to a JSON file. Returns count exported."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(self._user_presets, f, indent=2, ensure_ascii=False)
        return len(self._user_presets)

    def import_presets(self, src_path: Path) -> int:
        """Imports presets from a JSON file, merging into user presets. Returns count imported."""
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return 0
        imported = 0
        for item in data:
            if isinstance(item, dict) and item.get("name") and item.get("expression"):
                self.add_user_preset(
                    name=str(item["name"]),
                    expression=str(item["expression"]),
                    description=str(item.get("description", "")),
                    replacement=str(item.get("replacement", "")),
                    mode=item.get("mode"),
                    ignore_case=item.get("ignore_case"),
                    disable_multiline=item.get("disable_multiline"),
                    dot_all=item.get("dot_all"),
                    is_literal=item.get("is_literal"),
                )
                imported += 1
        return imported
