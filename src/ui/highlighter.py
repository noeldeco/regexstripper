"""
Highlighter for Regex Stripper
Dynamically applies non-destructive ExtraSelections to QPlainTextEdit
reflecting either matching spans (Delete Matches mode) or inverted spans (Delete Non-Matches mode).
Supports real-time theme adaptation (Light and Dark) and Literal Match mode.
"""

from __future__ import annotations
from typing import Tuple, List, Optional
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont
from src.config import (
    DeletionMode,
    AppTheme,
    COLOR_MATCH_HIGHLIGHT_LIGHT_BG,
    COLOR_MATCH_HIGHLIGHT_LIGHT_FG,
    COLOR_INVERT_HIGHLIGHT_LIGHT_BG,
    COLOR_INVERT_HIGHLIGHT_LIGHT_FG,
    COLOR_MATCH_HIGHLIGHT_DARK_BG,
    COLOR_MATCH_HIGHLIGHT_DARK_FG,
    COLOR_INVERT_HIGHLIGHT_DARK_BG,
    COLOR_INVERT_HIGHLIGHT_DARK_FG,
    COLOR_DIFF_INSERT_LIGHT_BG,
    COLOR_DIFF_INSERT_LIGHT_FG,
    COLOR_DIFF_DELETE_LIGHT_BG,
    COLOR_DIFF_DELETE_LIGHT_FG,
    COLOR_DIFF_INSERT_DARK_BG,
    COLOR_DIFF_INSERT_DARK_FG,
    COLOR_DIFF_DELETE_DARK_BG,
    COLOR_DIFF_DELETE_DARK_FG,
)
from src.core.regex_engine import RegexEngine


class MatchHighlighter:
    """Manages real-time visual highlight selections on a QPlainTextEdit."""

    def __init__(self, editor: QPlainTextEdit, theme: AppTheme = AppTheme.LIGHT):
        self.editor = editor
        self.theme: AppTheme = theme
        self.mode: DeletionMode = DeletionMode.DELETE_MATCHES
        self.pattern: str = ""
        self.flags: int = 0
        self.is_literal: bool = False

        self.match_format = QTextCharFormat()
        self.invert_format = QTextCharFormat()
        self.diff_insert_format = QTextCharFormat()
        self.diff_delete_format = QTextCharFormat()
        self._update_formats()

    def _update_formats(self) -> None:
        """Re-configures highlight colors based on the current theme."""
        if self.theme == AppTheme.DARK:
            self.match_format.setBackground(QColor(COLOR_MATCH_HIGHLIGHT_DARK_BG))
            self.match_format.setForeground(QColor(COLOR_MATCH_HIGHLIGHT_DARK_FG))
            self.invert_format.setBackground(QColor(COLOR_INVERT_HIGHLIGHT_DARK_BG))
            self.invert_format.setForeground(QColor(COLOR_INVERT_HIGHLIGHT_DARK_FG))

            # Replace Diff formats: Green bold for insert, Red strikethrough & italics for delete
            self.diff_insert_format.setBackground(QColor(COLOR_DIFF_INSERT_DARK_BG))
            self.diff_insert_format.setForeground(QColor(COLOR_DIFF_INSERT_DARK_FG))
            self.diff_insert_format.setFontWeight(QFont.Bold)
            self.diff_insert_format.setFontStrikeOut(False)
            self.diff_insert_format.setFontItalic(False)

            self.diff_delete_format.setBackground(QColor(COLOR_DIFF_DELETE_DARK_BG))
            self.diff_delete_format.setForeground(QColor(COLOR_DIFF_DELETE_DARK_FG))
            self.diff_delete_format.setFontWeight(QFont.Normal)
            self.diff_delete_format.setFontStrikeOut(True)
            self.diff_delete_format.setFontItalic(True)
        else:
            self.match_format.setBackground(QColor(COLOR_MATCH_HIGHLIGHT_LIGHT_BG))
            self.match_format.setForeground(QColor(COLOR_MATCH_HIGHLIGHT_LIGHT_FG))
            self.invert_format.setBackground(QColor(COLOR_INVERT_HIGHLIGHT_LIGHT_BG))
            self.invert_format.setForeground(QColor(COLOR_INVERT_HIGHLIGHT_LIGHT_FG))

            # Replace Diff formats: Green bold for insert, Red strikethrough & italics for delete
            self.diff_insert_format.setBackground(QColor(COLOR_DIFF_INSERT_LIGHT_BG))
            self.diff_insert_format.setForeground(QColor(COLOR_DIFF_INSERT_LIGHT_FG))
            self.diff_insert_format.setFontWeight(QFont.Bold)
            self.diff_insert_format.setFontStrikeOut(False)
            self.diff_insert_format.setFontItalic(False)

            self.diff_delete_format.setBackground(QColor(COLOR_DIFF_DELETE_LIGHT_BG))
            self.diff_delete_format.setForeground(QColor(COLOR_DIFF_DELETE_LIGHT_FG))
            self.diff_delete_format.setFontWeight(QFont.Normal)
            self.diff_delete_format.setFontStrikeOut(True)
            self.diff_delete_format.setFontItalic(True)

    def set_theme(self, theme: AppTheme) -> None:
        """Updates the theme and reapplies highlights."""
        if self.theme != theme:
            self.theme = theme
            self._update_formats()
            self.update_highlights()

    def set_mode(self, mode: DeletionMode) -> None:
        """Sets the active deletion mode and re-applies highlights."""
        if self.mode != mode:
            self.mode = mode
            self.update_highlights()

    def set_pattern_and_flags(
        self,
        pattern: str,
        flags: int,
        is_literal: bool = False
    ) -> Tuple[int, bool, str]:
        """Sets pattern, flags, and literal mode, then updates highlights."""
        self.pattern = pattern
        self.flags = flags
        self.is_literal = is_literal
        return self.update_highlights()

    def clear_highlights(self) -> None:
        """Removes all extra selections from the editor."""
        self.editor.setExtraSelections([])

    def update_highlights(self) -> Tuple[int, bool, str]:
        """
        Calculates and applies the appropriate highlight spans according to mode.

        Returns:
            (match_count, is_valid, error_message)
        """
        text = self.editor.toPlainText()

        if not self.pattern:
            self.clear_highlights()
            return 0, True, ""

        is_valid, err_msg, compiled = RegexEngine.validate_pattern(
            self.pattern, self.flags, is_literal=self.is_literal
        )
        if not is_valid or compiled is None:
            self.clear_highlights()
            return 0, False, err_msg

        match_count = RegexEngine.count_matches(
            text, self.pattern, self.flags, is_literal=self.is_literal
        )

        if not text:
            self.clear_highlights()
            return match_count, True, ""

        # Determine target spans based on deletion mode
        if self.mode == DeletionMode.DELETE_MATCHES:
            target_spans = RegexEngine.find_match_spans(
                text, self.pattern, self.flags, is_literal=self.is_literal
            )
            fmt = self.match_format
        else:
            target_spans = RegexEngine.find_inverted_spans(
                text, self.pattern, self.flags, is_literal=self.is_literal
            )
            fmt = self.invert_format

        # Construct ExtraSelections
        doc = self.editor.document()
        doc_length = doc.characterCount() - 1
        selections: List[QTextEdit.ExtraSelection] = []

        for start, end in target_spans:
            start = max(0, min(start, doc_length))
            end = max(0, min(end, doc_length))
            if start >= end:
                continue

            sel = QTextEdit.ExtraSelection()
            sel.format = fmt

            cursor = QTextCursor(doc)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            sel.cursor = cursor
            selections.append(sel)

        self.editor.setExtraSelections(selections)
        return match_count, True, ""

    def apply_diff_highlights(
        self,
        green_spans: List[Tuple[int, int]],
        red_spans: List[Tuple[int, int]]
    ) -> None:
        """
        Applies green bold format to inserted replacements and red strikethrough to replaced originals.
        """
        doc = self.editor.document()
        doc_length = doc.characterCount() - 1
        selections: List[QTextEdit.ExtraSelection] = []

        # Green bold for inserted replacement text
        for start, end in green_spans:
            start = max(0, min(start, doc_length))
            end = max(0, min(end, doc_length))
            if start >= end:
                continue

            sel = QTextEdit.ExtraSelection()
            sel.format = self.diff_insert_format
            cursor = QTextCursor(doc)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            sel.cursor = cursor
            selections.append(sel)

        # Red strikethrough for replaced original text
        for start, end in red_spans:
            start = max(0, min(start, doc_length))
            end = max(0, min(end, doc_length))
            if start >= end:
                continue

            sel = QTextEdit.ExtraSelection()
            sel.format = self.diff_delete_format
            cursor = QTextCursor(doc)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            sel.cursor = cursor
            selections.append(sel)

        self.editor.setExtraSelections(selections)
