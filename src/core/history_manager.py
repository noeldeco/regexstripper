"""
History Manager for Regex Stripper
Persists and manages recently used regex patterns using an LRU policy.
Patterns are registered ONLY upon confirmed delete operations.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional
from src.config import MAX_HISTORY_ITEMS, HISTORY_FILE_PATH


class HistoryManager:
    """Manages persistent recent regex patterns."""

    def __init__(self, file_path: Optional[Path] = None, max_items: int = MAX_HISTORY_ITEMS):
        self.file_path = file_path or HISTORY_FILE_PATH
        self.max_items = max_items
        self._history: List[str] = []
        self.load()

    @property
    def history(self) -> List[str]:
        """Returns a copy of the current history list (most recent first)."""
        return list(self._history)

    def add_pattern(self, pattern: str) -> bool:
        """
        Adds a pattern to the top of the history list.
        Deduplicates if the pattern already exists and enforces max_items.
        Saves changes to disk.

        Returns:
            True if history was updated, False otherwise.
        """
        if not pattern:
            return False

        # If already present, remove existing entry so it gets moved to top
        if pattern in self._history:
            self._history.remove(pattern)

        # Insert at front (most recent)
        self._history.insert(0, pattern)

        # Enforce maximum capacity
        if len(self._history) > self.max_items:
            self._history = self._history[: self.max_items]

        self.save()
        return True

    def remove_pattern(self, pattern: str) -> bool:
        """Removes a pattern from history."""
        if pattern in self._history:
            self._history.remove(pattern)
            self.save()
            return True
        return False

    def clear(self) -> None:
        """Clears all history entries and updates disk."""
        self._history.clear()
        self.save()

    def load(self) -> None:
        """Loads patterns from JSON storage file."""
        if not self.file_path.exists():
            self._history = []
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Ensure items are strings and unique while preserving order
                    seen = set()
                    cleaned = []
                    for item in data:
                        if isinstance(item, str) and item and item not in seen:
                            seen.add(item)
                            cleaned.append(item)
                    self._history = cleaned[: self.max_items]
                else:
                    self._history = []
        except Exception:
            # Fallback gracefully if corrupted or unreadable
            self._history = []

    def save(self) -> None:
        """Saves current history patterns to JSON storage file."""
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
        except Exception:
            # Gracefully ignore save errors (e.g. read-only filesystem)
            pass

