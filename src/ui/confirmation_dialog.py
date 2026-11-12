"""
Confirmation Dialog for Regex Stripper
Pops up a safety dialog before deleting matching or non-matching text.
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
from PySide6.QtCore import Qt
from src.config import DeletionMode


class DeleteConfirmationDialog(QDialog):
    """Modal dialog prompting the user to confirm a deletion operation."""

    def __init__(
        self,
        parent: Optional[QWidget],
        mode: DeletionMode,
        match_count: int,
        pattern: str
    ):
        super().__init__(parent)
        self.mode = mode
        self.match_count = match_count
        self.pattern = pattern

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

        title_text = (
            "Delete All Matches?"
            if self.mode == DeletionMode.DELETE_MATCHES
            else "Delete All Non-Matching Text?"
        )
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

        # Description / details
        if self.mode == DeletionMode.DELETE_MATCHES:
            desc_text = (
                f"You are about to remove all <b>{self.match_count}</b> matching segment(s) "
                f"for the pattern:<br><br>"
                f"<code style='background: rgba(128,128,128,0.2); padding:3px 6px; border-radius:3px;'>"
                f"{self.escape_html(self.pattern)}</code><br><br>"
                f"The surrounding non-matching text will be retained."
            )
        else:
            desc_text = (
                f"You are about to delete all non-matching text and keep only the "
                f"<b>{self.match_count}</b> matched segment(s) for the pattern:<br><br>"
                f"<code style='background: rgba(128,128,128,0.2); padding:3px 6px; border-radius:3px;'>"
                f"{self.escape_html(self.pattern)}</code><br><br>"
                f"<b>Warning:</b> All content outside the matched segments will be permanently deleted."
            )

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
        pattern: str
    ) -> bool:
        """Convenience method to show the dialog and return True if accepted."""
        dialog = cls(parent, mode, match_count, pattern)
        return dialog.exec() == QDialog.Accepted

