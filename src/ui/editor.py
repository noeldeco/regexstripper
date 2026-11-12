"""
Enhanced Editor for Regex Stripper
Provides Drag & Drop file loading, Ctrl+Wheel font zooming, and cursor tracking.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QWheelEvent, QFont

from src.config import MONOSPACE_FONTS


class DragDropEditor(QPlainTextEdit):
    """Custom QPlainTextEdit with file drag-and-drop, font zooming, and read-only event hooks."""

    fileDropped = Signal(str, str)  # (file_path, content)
    zoomChanged = Signal(int)       # point_size
    readOnlyAttempted = Signal()    # Emitted when user tries typing while editor is read-only (preview)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.base_font_size = 11
        self._raw_text: Optional[str] = None

        editor_font = QFont()
        editor_font.setFamilies(MONOSPACE_FONTS)
        editor_font.setPointSize(self.base_font_size)
        self.setFont(editor_font)

    def setPlainText(self, text: str) -> None:
        """Sets clean document text, resetting any active preview mode."""
        self._raw_text = None
        self.setReadOnly(False)
        super().setPlainText(text)

    def clear(self) -> None:
        """Clears editor text, resetting any active preview mode."""
        self._raw_text = None
        self.setReadOnly(False)
        super().clear()

    def set_diff_preview(self, preview_text: str, raw_text: str) -> None:
        """Enables preview mode, storing raw_text and displaying preview_text."""
        self._raw_text = raw_text
        self.setReadOnly(True)
        v_val = self.verticalScrollBar().value()
        h_val = self.horizontalScrollBar().value()
        self.blockSignals(True)
        super().setPlainText(preview_text)
        self.blockSignals(False)
        self.verticalScrollBar().setValue(v_val)
        self.horizontalScrollBar().setValue(h_val)

    def clear_diff_preview(self, raw_text: Optional[str] = None) -> None:
        """Disables preview mode and restores the raw document text."""
        restored = raw_text if raw_text is not None else self._raw_text
        self._raw_text = None
        self.setReadOnly(False)
        if restored is not None:
            v_val = self.verticalScrollBar().value()
            h_val = self.horizontalScrollBar().value()
            self.blockSignals(True)
            super().setPlainText(restored)
            self.blockSignals(False)
            self.verticalScrollBar().setValue(v_val)
            self.horizontalScrollBar().setValue(h_val)

    @property
    def is_diff_previewing(self) -> bool:
        return self._raw_text is not None

    def toPlainText(self) -> str:
        """Returns the actual document text (raw text when in preview mode)."""
        if self._raw_text is not None:
            return self._raw_text
        return super().toPlainText()

    def previewPlainText(self) -> str:
        """Returns the rendered preview text if in preview mode, or raw text otherwise."""
        return super().toPlainText()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path:
                    try:
                        # Attempt UTF-8, then fallback to latin-1
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                        except UnicodeDecodeError:
                            with open(file_path, "r", encoding="latin-1") as f:
                                content = f.read()

                        self.setPlainText(content)
                        self.fileDropped.emit(file_path, content)
                        event.acceptProposedAction()
                        return
                    except Exception:
                        pass
        super().dropEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Ctrl + Wheel zooming."""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom_in(self) -> None:
        f = self.font()
        new_size = min(f.pointSize() + 1, 32)
        f.setPointSize(new_size)
        self.setFont(f)
        self.zoomChanged.emit(new_size)

    def zoom_out(self) -> None:
        f = self.font()
        new_size = max(f.pointSize() - 1, 7)
        f.setPointSize(new_size)
        self.setFont(f)
        self.zoomChanged.emit(new_size)

    def reset_zoom(self) -> None:
        f = self.font()
        f.setPointSize(self.base_font_size)
        self.setFont(f)
        self.zoomChanged.emit(self.base_font_size)

    def keyPressEvent(self, event) -> None:
        """Notifies when editing keys are pressed while in read-only preview mode."""
        if self.isReadOnly():
            nav_keys = {
                Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right,
                Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End,
                Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta,
                Qt.Key_Escape, Qt.Key_F3
            }
            # Allow Ctrl+C, Ctrl+A etc.
            is_copy_or_select = bool(
                event.modifiers() & Qt.ControlModifier and
                event.key() in (Qt.Key_C, Qt.Key_A, Qt.Key_Insert)
            )
            if event.key() not in nav_keys and not is_copy_or_select:
                self.readOnlyAttempted.emit()
        super().keyPressEvent(event)

