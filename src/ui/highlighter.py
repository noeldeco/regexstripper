"""
Highlighter for Regex Stripper
Dynamically applies non-destructive ExtraSelections to QPlainTextEdit
reflecting matching spans, inverted spans, line-level spans, or inline replace diffs.
Uses viewport-scoped rendering with bisect so multi-MB files with tens of thousands
of matches stay smooth without freezing Qt's UI thread.
"""

from __future__ import annotations
from bisect import bisect_left
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


# Below this span count, rendering all spans is instantaneous (<1ms) and keeps
# offscreen/headless UI tests deterministic without viewport geometry requirements.
_VIEWPORT_CULL_THRESHOLD = 400


class MatchHighlighter:
    """Manages real-time, viewport-optimized visual highlight selections on a QPlainTextEdit."""

    def __init__(self, editor: QPlainTextEdit, theme: AppTheme = AppTheme.LIGHT):
        self.editor = editor
        self.theme: AppTheme = theme
        self.mode: DeletionMode = DeletionMode.DELETE_MATCHES
        self.pattern: str = ""
        self.flags: int = 0
        self.is_literal: bool = False

        # Cached spans for fast viewport re-rendering on scroll or theme toggle
        self._is_diff_mode: bool = False
        self._cached_target_spans: List[Tuple[int, int]] = []
        self._cached_target_starts: List[int] = []
        self._cached_green_spans: List[Tuple[int, int]] = []
        self._cached_green_starts: List[int] = []
        self._cached_red_spans: List[Tuple[int, int]] = []
        self._cached_red_starts: List[int] = []
        self._last_visible_range: Optional[Tuple[int, int]] = None

        self.match_format = QTextCharFormat()
        self.invert_format = QTextCharFormat()
        self.diff_insert_format = QTextCharFormat()
        self.diff_delete_format = QTextCharFormat()
        self._update_formats()

        # Re-render visible highlights when scrolling large documents
        self.editor.verticalScrollBar().valueChanged.connect(self._on_viewport_scrolled)
        self.editor.updateRequest.connect(self._on_update_request)

    def _update_formats(self) -> None:
        """Re-configures highlight colors based on the current theme."""
        if self.theme == AppTheme.DARK:
            self.match_format.setBackground(QColor(COLOR_MATCH_HIGHLIGHT_DARK_BG))
            self.match_format.setForeground(QColor(COLOR_MATCH_HIGHLIGHT_DARK_FG))
            self.invert_format.setBackground(QColor(COLOR_INVERT_HIGHLIGHT_DARK_BG))
            self.invert_format.setForeground(QColor(COLOR_INVERT_HIGHLIGHT_DARK_FG))

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

    def _get_visible_char_range(self) -> Optional[Tuple[int, int]]:
        """Returns (start_pos, end_pos) of characters currently visible in the viewport."""
        if not self.editor.isVisible():
            return None
        vp_height = self.editor.viewport().height()
        if vp_height <= 0:
            return None

        block = self.editor.firstVisibleBlock()
        if not block.isValid():
            return None

        vis_start = block.position()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        last_block = block
        while block.isValid() and top <= vp_height + 200:
            last_block = block
            block = block.next()
            if not block.isValid():
                break
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()

        vis_end = last_block.position() + last_block.length()
        return (vis_start, vis_end)

    def _slice_spans_for_viewport(
        self,
        spans: List[Tuple[int, int]],
        starts: List[int],
        vis_range: Optional[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Slices sorted spans to those overlapping `vis_range` when culling is needed."""
        if not spans:
            return []
        if len(spans) <= _VIEWPORT_CULL_THRESHOLD or vis_range is None:
            return spans

        vis_start, vis_end = vis_range
        # Back up 1 element in case a long span started before vis_start and overlaps into it
        idx = max(0, bisect_left(starts, vis_start) - 1)
        result: List[Tuple[int, int]] = []
        n = len(spans)
        while idx < n:
            s, e = spans[idx]
            if s > vis_end:
                break
            if e > vis_start:
                result.append((s, e))
            idx += 1
        return result

    def _on_viewport_scrolled(self, _value: int) -> None:
        if self._needs_viewport_culling():
            self._render_cached(force=False)

    def _on_update_request(self, _rect, dy: int) -> None:
        if dy != 0 and self._needs_viewport_culling():
            self._render_cached(force=False)

    def _needs_viewport_culling(self) -> bool:
        if self._is_diff_mode:
            return (len(self._cached_green_spans) + len(self._cached_red_spans)) > _VIEWPORT_CULL_THRESHOLD
        return len(self._cached_target_spans) > _VIEWPORT_CULL_THRESHOLD

    def _render_cached(self, force: bool = True) -> None:
        """Applies ExtraSelections from cached spans, culling to viewport on large docs."""
        vis_range = self._get_visible_char_range() if self._needs_viewport_culling() else None
        if not force and vis_range == self._last_visible_range:
            return
        self._last_visible_range = vis_range

        doc = self.editor.document()
        doc_length = max(0, doc.characterCount() - 1)
        selections: List[QTextEdit.ExtraSelection] = []

        if self._is_diff_mode:
            g_spans = self._slice_spans_for_viewport(self._cached_green_spans, self._cached_green_starts, vis_range)
            r_spans = self._slice_spans_for_viewport(self._cached_red_spans, self._cached_red_starts, vis_range)

            for start, end in g_spans:
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

            for start, end in r_spans:
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
        else:
            fmt = (
                self.match_format
                if self.mode in (DeletionMode.DELETE_MATCHES, DeletionMode.DELETE_MATCHING_LINES)
                else self.invert_format
            )
            t_spans = self._slice_spans_for_viewport(self._cached_target_spans, self._cached_target_starts, vis_range)
            for start, end in t_spans:
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

    def set_theme(self, theme: AppTheme) -> None:
        """Updates the theme and re-renders cached highlights (preserving diff preview mode)."""
        if self.theme != theme:
            self.theme = theme
            self._update_formats()
            self._render_cached(force=True)

    def set_mode(self, mode: DeletionMode) -> None:
        """Sets the active deletion mode."""
        if self.mode != mode:
            self.mode = mode

    def apply_spans(self, target_spans: List[Tuple[int, int]], mode: DeletionMode) -> None:
        """Applies pre-computed highlight spans directly (single-pass optimization)."""
        self.mode = mode
        self._is_diff_mode = False
        self._cached_target_spans = target_spans
        self._cached_target_starts = [s for s, _ in target_spans]
        self._cached_green_spans = []
        self._cached_green_starts = []
        self._cached_red_spans = []
        self._cached_red_starts = []
        self._render_cached(force=True)

    def apply_diff_highlights(
        self,
        green_spans: List[Tuple[int, int]],
        red_spans: List[Tuple[int, int]]
    ) -> None:
        """Applies green bold format to inserted replacements and red strikethrough to originals."""
        self._is_diff_mode = True
        self._cached_target_spans = []
        self._cached_target_starts = []
        self._cached_green_spans = green_spans
        self._cached_green_starts = [s for s, _ in green_spans]
        self._cached_red_spans = red_spans
        self._cached_red_starts = [s for s, _ in red_spans]
        self._render_cached(force=True)

    def set_pattern_and_flags(
        self,
        pattern: str,
        flags: int,
        is_literal: bool = False
    ) -> Tuple[int, bool, str]:
        """Sets pattern, flags, and literal mode, then updates highlights (single-pass)."""
        self.pattern = pattern
        self.flags = flags
        self.is_literal = is_literal
        return self.update_highlights()

    def clear_highlights(self) -> None:
        """Removes all extra selections and clears cached spans."""
        self._is_diff_mode = False
        self._cached_target_spans = []
        self._cached_target_starts = []
        self._cached_green_spans = []
        self._cached_green_starts = []
        self._cached_red_spans = []
        self._cached_red_starts = []
        self._last_visible_range = None
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

        analysis = RegexEngine.analyze(
            text, self.pattern, self.flags, is_literal=self.is_literal, mode=self.mode
        )
        if not analysis.is_valid:
            self.clear_highlights()
            return 0, False, analysis.error_message

        if not text:
            self.clear_highlights()
            return 0, True, ""

        self.apply_spans(analysis.target_spans, self.mode)
        return analysis.match_count, True, ""
