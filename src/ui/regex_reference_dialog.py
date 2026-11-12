"""
Regex Quick Reference Dialog
Provides a cleanly formatted cheat sheet of regex syntax, tokens, and examples.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QWidget,
    QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class RegexReferenceDialog(QDialog):
    """Nicely formatted regex reference window."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Regex Quick Reference")
        self.resize(750, 560)
        self.setMinimumSize(600, 420)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("Regex Quick Reference & Cheat Sheet")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Tabs for categories
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        # 1. Characters & Classes
        char_data = [
            (r"\d", "Digit (0-9)", "Matches any numerical character"),
            (r"\D", "Non-digit", "Matches any non-numerical character"),
            (r"\w", "Word character", "Matches letters, numbers, and underscore [a-zA-Z0-9_]"),
            (r"\W", "Non-word character", "Matches symbols, punctuation, spaces"),
            (r"\s", "Whitespace", "Matches space, tab, newline, form feed"),
            (r"\S", "Non-whitespace", "Matches any non-whitespace character"),
            (r".", "Any character", "Matches any character except newline (unless DOTALL set)"),
            (r"[abc]", "Character set", "Matches 'a', 'b', or 'c'"),
            (r"[^abc]", "Negated set", "Matches anything EXCEPT 'a', 'b', or 'c'"),
            (r"[a-z]", "Range", "Matches lowercase letters between a and z"),
            (r"\\", "Escaped backslash", "Matches a literal backslash"),
        ]
        self.tabs.addTab(self._create_table(char_data), "Characters & Classes")

        # 2. Anchors & Quantifiers
        quant_data = [
            (r"^", "Start of line/string", "Asserts position at the start"),
            (r"$", "End of line/string", "Asserts position at the end"),
            (r"\b", "Word boundary", "Asserts position at start/end of a word"),
            (r"\B", "Non-word boundary", "Asserts position not at word edge"),
            (r"*", "0 or more (Greedy)", "Matches previous item zero or multiple times"),
            (r"+", "1 or more (Greedy)", "Matches previous item at least once"),
            (r"?", "0 or 1 (Optional)", "Matches previous item zero or one time"),
            (r"{n}", "Exactly n times", r"e.g. \d{4} matches a 4-digit number"),
            (r"{n,}", "At least n times", r"e.g. \w{3,} matches 3 or more word characters"),
            (r"{n,m}", "Between n and m times", "e.g. [A-Z]{2,5} matches 2 to 5 uppercase letters"),
            (r"*?, +?, ??", "Lazy / Non-greedy", "Matches as few characters as possible"),
        ]
        self.tabs.addTab(self._create_table(quant_data), "Anchors & Quantifiers")

        # 3. Groups & Lookarounds
        group_data = [
            (r"(...)", "Capture group", "Extracts matched substring for extraction or replacement"),
            (r"(?:...)", "Non-capturing group", "Groups expressions without capturing for backreference"),
            (r"(?P<name>...)", "Named group", "Names a capture group for easy reference"),
            (r"|", "Alternation (OR)", "Matches expression on left OR right (e.g. cat|dog)"),
            (r"(?=...)", "Positive lookahead", "Asserts that following text matches pattern"),
            (r"(?!...)", "Negative lookahead", "Asserts that following text does NOT match pattern"),
            (r"(?<=...)", "Positive lookbehind", "Asserts that preceding text matches pattern"),
            (r"(?<!...)", "Negative lookbehind", "Asserts that preceding text does NOT match pattern"),
        ]
        self.tabs.addTab(self._create_table(group_data), "Groups & Lookaround")

        # 4. Replacement Syntax
        repl_data = [
            (r"\1, \2, ...", "Group Backreference", "Inserts captured group 1, 2 in replacement string"),
            (r"\g<1>", "Numbered group", "Equivalent to \\1, disambiguates e.g. \\g<1>0"),
            (r"\g<name>", "Named group reference", "Inserts group captured by (?P<name>...)"),
            (r"\\", "Literal backslash", "Inserts a single literal backslash in replacement"),
        ]
        self.tabs.addTab(self._create_table(repl_data), "Replacement Syntax")

        # Bottom row with Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("utilBtn")
        close_btn.setMinimumWidth(90)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _create_table(self, data: list) -> QTableWidget:
        table = QTableWidget(len(data), 3)
        table.setHorizontalHeaderLabels(["Pattern", "Name", "Description"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        for row, (pattern, name, desc) in enumerate(data):
            pat_item = QTableWidgetItem(pattern)
            pat_item.setFont(self._get_mono_font())
            name_item = QTableWidgetItem(name)
            desc_item = QTableWidgetItem(desc)

            table.setItem(row, 0, pat_item)
            table.setItem(row, 1, name_item)
            table.setItem(row, 2, desc_item)

        return table

    def _get_mono_font(self) -> QFont:
        font = QFont("Cascadia Code", 10)
        font.setStyleHint(QFont.Monospace)
        return font
