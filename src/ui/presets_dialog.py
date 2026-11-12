"""
Presets Dialog for Regex Stripper
Displays commonly used regex expressions and allows one-click insertion
or saving the current pattern directly from the UI.
"""

from __future__ import annotations
from typing import Optional, List, Dict
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
    QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.preset_manager import PresetManager


class PresetsDialog(QDialog):
    """Dialog displaying saved and commonly used regex expressions."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        preset_manager: Optional[PresetManager] = None,
        current_pattern: str = ""
    ):
        super().__init__(parent)
        self.preset_manager = preset_manager or PresetManager()
        self.current_pattern = current_pattern
        self.setWindowTitle("Commonly Used Expressions")
        self.resize(760, 500)
        self.setMinimumSize(580, 400)
        self.selected_expression: Optional[str] = None
        self._all_presets: List[Dict[str, str]] = self.preset_manager.get_all_presets()
        self._filtered_presets: List[Dict[str, str]] = list(self._all_presets)

        self._init_ui()
        self._populate_table()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header & Subtitle
        header = QLabel("Commonly Used Expressions (Presets)")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        sub_label = QLabel(
            "Select an expression and click 'Use Expression' or double-click to insert it.\n"
            "You can also save the current pattern as a new preset directly using '+ Add Custom Preset'."
        )
        sub_label.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(sub_label)

        # Top Bar: Search / Filter & Add Preset Button
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter presets by name or pattern...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.search_input, stretch=1)

        self.add_preset_btn = QPushButton("+ Add Custom Preset")
        self.add_preset_btn.setObjectName("utilBtn")
        self.add_preset_btn.setToolTip("Save the current regex pattern as a new preset")
        self.add_preset_btn.clicked.connect(self._on_add_preset_clicked)
        filter_row.addWidget(self.add_preset_btn)

        layout.addLayout(filter_row)

        # Presets Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Expression", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("utilBtn")
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.use_btn = QPushButton("Use Expression")
        self.use_btn.setObjectName("copyBtn")
        self.use_btn.setMinimumWidth(130)
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._on_use_clicked)
        btn_layout.addWidget(self.use_btn)

        layout.addLayout(btn_layout)

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self._filtered_presets))
        mono_font = QFont("Cascadia Code", 10)
        mono_font.setStyleHint(QFont.Monospace)

        for row, item in enumerate(self._filtered_presets):
            name_item = QTableWidgetItem(item.get("name", ""))
            name_item.setFont(QFont("", 10, QFont.Bold))

            exp_item = QTableWidgetItem(item.get("expression", ""))
            exp_item.setFont(mono_font)

            desc_item = QTableWidgetItem(item.get("description", ""))

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, exp_item)
            self.table.setItem(row, 2, desc_item)

        if self._filtered_presets:
            self.table.selectRow(0)

    def _on_filter_changed(self, text: str) -> None:
        query = text.lower().strip()
        if not query:
            self._filtered_presets = list(self._all_presets)
        else:
            self._filtered_presets = [
                p for p in self._all_presets
                if query in p.get("name", "").lower()
                or query in p.get("expression", "").lower()
                or query in p.get("description", "").lower()
            ]
        self._populate_table()

    def _on_selection_changed(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        self.use_btn.setEnabled(len(selected_rows) > 0)

    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if 0 <= row < len(self._filtered_presets):
            self.selected_expression = self._filtered_presets[row].get("expression", "")
            self.accept()

    def _on_use_clicked(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if 0 <= row < len(self._filtered_presets):
                self.selected_expression = self._filtered_presets[row].get("expression", "")
                self.accept()

    def _on_add_preset_clicked(self) -> None:
        """Prompts to add a new preset, prefilling current pattern."""
        name, ok1 = QInputDialog.getText(
            self, "New Preset Name", "Enter a descriptive name for this preset:"
        )
        if not ok1 or not name.strip():
            return

        expr, ok2 = QInputDialog.getText(
            self, "Preset Regex Pattern", "Pattern expression:", text=self.current_pattern
        )
        if not ok2 or not expr.strip():
            return

        desc, ok3 = QInputDialog.getText(
            self, "Preset Description (Optional)", "Description / Notes:"
        )

        self.preset_manager.add_user_preset(name.strip(), expr.strip(), desc.strip() if ok3 else "")
        self._all_presets = self.preset_manager.get_all_presets()
        self._on_filter_changed(self.search_input.text())

    @classmethod
    def select_preset(
        cls,
        parent: Optional[QWidget] = None,
        current_pattern: str = ""
    ) -> Optional[str]:
        """Convenience method that shows the dialog and returns the selected expression string."""
        dialog = cls(parent, current_pattern=current_pattern)
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_expression
        return None
