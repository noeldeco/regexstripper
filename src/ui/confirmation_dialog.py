"""
Confirmation Dialogs for Regex Stripper
Pops up safety modals before deleting matching/non-matching text,
matching/non-matching lines, or duplicate lines.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QWidget
)
from src.config import DeletionMode


class DeleteConfirmationDialog(QDialog):
    """Modal dialog prompting the user to confirm a deletion operation."""

    def __init__(
        self,
        parent: Optional[QWidget],
        mode: DeletionMode,
        match_count: int,
        pattern: str,
        impact_summary: str = ""
    ):
        super().__init__(parent)
        self.mode = mode
        self.match_count = match_count
        self.pattern = pattern
        self.impact_summary = impact_summary

        self.setWindowTitle("Confirm Deletion")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header with icon and title
        header_layout = QHBoxLayout()
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(icon_label)

        title_map = {
            DeletionMode.DELETE_MATCHES: "Delete All Matches?",
            DeletionMode.DELETE_NON_MATCHES: "Delete All Non-Matching Text?",
            DeletionMode.DELETE_MATCHING_LINES: "Delete All Matching Lines?",
            DeletionMode.KEEP_MATCHING_LINES: "Keep Only Matching Lines?",
        }
        title_text = title_map.get(self.mode, "Confirm Deletion?")
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        escaped_pat = self.escape_html(self.pattern)
        pat_html = (
            f"<code style='background: rgba(128,128,128,0.2); padding:3px 6px; border-radius:3px;'>"
            f"{escaped_pat}</code>"
        )

        # Description / details
        if self.mode == DeletionMode.DELETE_MATCHES:
            desc_text = (
                f"You are about to remove all <b>{self.match_count}</b> matching segment(s) "
                f"for the pattern:<br><br>{pat_html}<br><br>"
                f"The surrounding non-matching text will be retained."
            )
        elif self.mode == DeletionMode.DELETE_NON_MATCHES:
            if self.match_count == 0:
                desc_text = (
                    f"<b>0 matches found.</b> Deleting non-matches will clear the entire text "
                    f"for the pattern:<br><br>{pat_html}<br><br>"
                    f"<b>Warning:</b> All content will be permanently removed (Undo is available)."
                )
            else:
                desc_text = (
                    f"You are about to delete all non-matching text and keep only the "
                    f"<b>{self.match_count}</b> matched segment(s) for the pattern:<br><br>"
                    f"{pat_html}<br><br>"
                    f"<b>Warning:</b> All content outside the matched segments will be permanently deleted."
                )
        elif self.mode == DeletionMode.DELETE_MATCHING_LINES:
            desc_text = (
                f"You are about to delete every entire line matching the pattern "
                f"(<b>{self.match_count}</b> matching line(s)):<br><br>{pat_html}<br><br>"
                f"Non-matching lines will be retained (Undo is available)."
            )
        else:  # KEEP_MATCHING_LINES
            desc_text = (
                f"You are about to delete all non-matching lines and keep only the "
                f"<b>{self.match_count}</b> line(s) matching:<br><br>{pat_html}<br><br>"
                f"<b>Warning:</b> Every line that does not contain a match will be removed (Undo is available)."
            )

        if self.impact_summary:
            desc_text += f"<br><br><i>Estimated impact: {self.escape_html(self.impact_summary)}</i>"

        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc_label)

        layout.addSpacing(8)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("utilBtn")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.setMinimumWidth(90)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setDefault(True)  # Safe default
        btn_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("Delete")
        self.confirm_btn.setObjectName("deleteBtn")
        self.confirm_btn.setMinimumHeight(32)
        self.confirm_btn.setMinimumWidth(100)
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    @staticmethod
    def escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @classmethod
    def confirm(
        cls,
        parent: Optional[QWidget],
        mode: DeletionMode,
        match_count: int,
        pattern: str,
        impact_summary: str = ""
    ) -> bool:
        """Convenience method to show the dialog and return True if accepted."""
        dialog = cls(parent, mode, match_count, pattern, impact_summary=impact_summary)
        return dialog.exec() == QDialog.Accepted


class DeleteDuplicatesConfirmationDialog(QDialog):
    """Modal dialog prompting the user to confirm duplicate lines deletion."""

    def __init__(
        self,
        parent: Optional[QWidget],
        duplicate_count: int,
        total_lines: int
    ):
        super().__init__(parent)
        self.duplicate_count = duplicate_count
        self.total_lines = total_lines

        self.setWindowTitle("Confirm Delete Duplicates")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        header_layout = QHBoxLayout()
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(icon_label)

        title_label = QLabel("Delete All Duplicate Lines?")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        unique_count = self.total_lines - self.duplicate_count
        desc_text = (
            f"You are about to delete <b>{self.duplicate_count}</b> duplicate line(s) from the text.<br><br>"
            f"The first occurrence of each unique line will be kept in its original order "
            f"(<b>{unique_count}</b> unique line(s) remaining out of {self.total_lines} total lines).<br><br>"
            f"<b>Warning:</b> All duplicate line occurrences will be removed. (Undo is available)."
        )

        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc_label)

        layout.addSpacing(8)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("utilBtn")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.setMinimumWidth(90)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setDefault(True)
        btn_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("Delete Duplicates")
        self.confirm_btn.setObjectName("deleteBtn")
        self.confirm_btn.setMinimumHeight(32)
        self.confirm_btn.setMinimumWidth(140)
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    @classmethod
    def confirm(
        cls,
        parent: Optional[QWidget],
        duplicate_count: int,
        total_lines: int
    ) -> bool:
        """Convenience method to show the dialog and return True if accepted."""
        dialog = cls(parent, duplicate_count, total_lines)
        return dialog.exec() == QDialog.Accepted
