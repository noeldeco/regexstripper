"""
Pipeline Manager for Regex Stripper
Persists and executes multi-step cleaning recipes (chained regex + line utilities).
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.config import PIPELINES_FILE_PATH
from src.core.regex_engine import RegexEngine


BUILTIN_PIPELINES: List[Dict[str, Any]] = [
    {
        "name": "Clean Phrase Tags & Deduplicate",
        "description": "Strips phrase tags, trims whitespace, removes blank lines, and deletes duplicate lines",
        "steps": [
            {"action": "delete_matches", "pattern": r"\{.+?>|<.+?\}|\{.}"},
            {"action": "trim_lines"},
            {"action": "remove_blank_lines"},
            {"action": "delete_duplicates"},
        ],
    },
    {
        "name": "Normalize & Sort Unique Lines",
        "description": "Trims lines, removes blank lines, deduplicates, and sorts alphabetically",
        "steps": [
            {"action": "trim_lines"},
            {"action": "remove_blank_lines"},
            {"action": "delete_duplicates"},
            {"action": "sort_lines", "sort_mode": "asc"},
        ],
    },
]

PIPELINE_ACTION_LABELS: Dict[str, str] = {
    "delete_matches": "Delete Matches",
    "replace_matches": "Replace Matches",
    "delete_non_matches": "Delete Non-Matches (Extract)",
    "delete_matching_lines": "Delete Matching Lines",
    "keep_matching_lines": "Keep Matching Lines",
    "delete_duplicates": "Delete Duplicate Lines",
    "remove_blank_lines": "Remove Blank Lines",
    "trim_lines": "Trim Line Whitespace",
    "sort_lines": "Sort Lines",
}


class PipelineManager:
    """Manages persistent multi-step text cleaning pipelines."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or PIPELINES_FILE_PATH
        self._user_pipelines: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.file_path.exists():
            self._user_pipelines = []
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._user_pipelines = [
                        dict(item) for item in data
                        if isinstance(item, dict) and item.get("name") and isinstance(item.get("steps"), list)
                    ]
        except Exception:
            self._user_pipelines = []

    def save(self) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._user_pipelines, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def is_builtin(name: str) -> bool:
        return any(p["name"] == name for p in BUILTIN_PIPELINES)

    def get_all_pipelines(self) -> List[Dict[str, Any]]:
        combined: List[Dict[str, Any]] = []
        for p in BUILTIN_PIPELINES:
            entry = dict(p)
            entry["steps"] = [dict(s) for s in p["steps"]]
            entry["_builtin"] = True
            combined.append(entry)

        builtin_names = {p["name"] for p in BUILTIN_PIPELINES}
        for u in self._user_pipelines:
            if u["name"] not in builtin_names:
                entry = dict(u)
                entry["steps"] = [dict(s) for s in u.get("steps", [])]
                entry["_builtin"] = False
                combined.append(entry)
        return combined

    def save_pipeline(self, name: str, steps: List[Dict[str, Any]], description: str = "") -> bool:
        if not name or not steps:
            return False
        record = {
            "name": name,
            "description": description,
            "steps": [dict(s) for s in steps],
        }
        for idx, item in enumerate(self._user_pipelines):
            if item["name"] == name:
                self._user_pipelines[idx] = record
                self.save()
                return True
        self._user_pipelines.append(record)
        self.save()
        return True

    def remove_pipeline(self, name: str) -> bool:
        initial = len(self._user_pipelines)
        self._user_pipelines = [p for p in self._user_pipelines if p["name"] != name]
        if len(self._user_pipelines) < initial:
            self.save()
            return True
        return False

    @staticmethod
    def format_step_summary(step: Dict[str, Any]) -> str:
        action = step.get("action", "")
        label = PIPELINE_ACTION_LABELS.get(action, action)
        pat = step.get("pattern", "")
        repl = step.get("replacement", "")
        if action == "replace_matches":
            return f"{label}: '{pat}' -> '{repl}'"
        if pat:
            return f"{label}: '{pat}'"
        if action == "sort_lines":
            return f"{label} ({step.get('sort_mode', 'asc')})"
        return label

    @classmethod
    def run_pipeline(cls, text: str, steps: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """
        Executes an ordered list of cleaning steps on `text`.

        Returns:
            (final_text, list_of_step_result_summaries)
        """
        current = text
        summaries: List[str] = []

        for step in steps:
            action = step.get("action", "")
            pattern = str(step.get("pattern", ""))
            replacement = str(step.get("replacement", ""))
            ignore_case = bool(step.get("ignore_case", False))
            disable_multiline = bool(step.get("disable_multiline", False))
            dot_all = bool(step.get("dot_all", False))
            is_literal = bool(step.get("is_literal", False))
            interpret_escapes = bool(step.get("interpret_escapes", False))

            flags = 0
            if ignore_case:
                flags |= re.IGNORECASE
            if not disable_multiline:
                flags |= re.MULTILINE
            if dot_all:
                flags |= re.DOTALL

            if action == "delete_matches":
                current, count = RegexEngine.strip_matches(current, pattern, flags, is_literal=is_literal)
                summaries.append(f"Deleted {count} match(es)")
            elif action == "replace_matches":
                current, count = RegexEngine.replace_matches(
                    current, pattern, replacement, flags,
                    is_literal=is_literal, interpret_escapes=interpret_escapes
                )
                summaries.append(f"Replaced {count} match(es)")
            elif action == "delete_non_matches":
                current, count = RegexEngine.strip_non_matches(
                    current, pattern, flags,
                    separator=str(step.get("delimiter", "\n")),
                    is_literal=is_literal,
                    unique=bool(step.get("unique", False)),
                    capture_group=str(step.get("capture_group", "0")),
                )
                summaries.append(f"Extracted {count} match(es)")
            elif action == "delete_matching_lines":
                current, count = RegexEngine.strip_matching_lines(current, pattern, flags, is_literal=is_literal)
                summaries.append(f"Deleted {count} matching line(s)")
            elif action == "keep_matching_lines":
                current, count = RegexEngine.keep_matching_lines(current, pattern, flags, is_literal=is_literal)
                summaries.append(f"Kept {count} matching line(s)")
            elif action == "delete_duplicates":
                current, count = RegexEngine.delete_duplicate_lines(current, ignore_case=ignore_case)
                summaries.append(f"Removed {count} duplicate line(s)")
            elif action == "remove_blank_lines":
                current, count = RegexEngine.remove_blank_lines(current)
                summaries.append(f"Removed {count} blank line(s)")
            elif action == "trim_lines":
                current, count = RegexEngine.trim_lines(current)
                summaries.append(f"Trimmed {count} line(s)")
            elif action == "sort_lines":
                sort_mode = str(step.get("sort_mode", "asc"))
                current, count = RegexEngine.sort_lines(current, mode=sort_mode, ignore_case=ignore_case)
                summaries.append(f"Sorted {count} line(s) ({sort_mode})")

        return current, summaries
