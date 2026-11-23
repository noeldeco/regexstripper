"""
Presets Dialog for Regex Stripper
Displays built-in and user-saved regex expressions with optional replacement,
flags, and mode. Supports creating, editing, deleting, and importing/exporting presets.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QLabel,
    QWidget,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtGui import QFont

from src.config import DeletionMode
from src.core.preset_manager import PresetManager


class PresetEditorDialog(QDialog):
    """Single-form dialog for creating or editing a rich preset."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Add Custom Preset",
        initial: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(480)
        self._initial = initial or {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit(str(self._initial.get("name", "")))
        self.name_input.setPlaceholderText("e.g., Strip HTML Comments")
        form.addRow("Name:", self.name_input)

        self.expr_input = QLineEdit(str(self._initial.get("expression", "")))
        self.expr_input.setPlaceholderText(r"e.g., <!--.*?-->")
        mono = QFont("Cascadia Code", 10)
        mono.setStyleHint(QFont.Monospace)
        self.expr_input.setFont(mono)
        form.addRow("Pattern:", self.expr_input)

        self.repl_input = QLineEdit(str(self._initial.get("replacement", "")))
        self.repl_input.setPlaceholderText("(Optional) Replacement string")
        self.repl_input.setFont(mono)
        form.addRow("Replacement:", self.repl_input)

        self.desc_input = QLineEdit(str(self._initial.get("description", "")))
        self.desc_input.setPlaceholderText("(Optional) Notes or description")
        form.addRow("Description:", self.desc_input)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("(Keep current mode)", None)
        self.mode_combo.addItem("Delete Matches", DeletionMode.DELETE_MATCHES.value)
        self.mode_combo.addItem("Delete Non-Matches", DeletionMode.DELETE_NON_MATCHES.value)
        self.mode_combo.addItem("Delete Matching Lines", DeletionMode.DELETE_MATCHING_LINES.value)
        self.mode_combo.addItem("Keep Matching Lines", DeletionMode.KEEP_MATCHING_LINES.value)
        init_mode = self._initial.get("mode")
        if init_mode:
            idx = self.mode_combo.findData(init_mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
        form.addRow("Action Mode:", self.mode_combo)

        flags_row = QHBoxLayout()
        self.literal_cb = QCheckBox("Literal")
        self.literal_cb.setChecked(bool(self._initial.get("is_literal", False)))
        self.ignore_case_cb = QCheckBox("Ignore Case (i)")
        self.ignore_case_cb.setChecked(bool(self._initial.get("ignore_case", False)))
        self.disable_multiline_cb = QCheckBox("Disable multiline")
        self.disable_multiline_cb.setChecked(bool(self._initial.get("disable_multiline", False)))
        self.dot_all_cb = QCheckBox("Dot All (s)")
        self.dot_all_cb.setChecked(bool(self._initial.get("dot_all", False)))
        flags_row.addWidget(self.literal_cb)
        flags_row.addWidget(self.ignore_case_cb)
        flags_row.addWidget(self.disable_multiline_cb)
        flags_row.addWidget(self.dot_all_cb)
        form.addRow("Options:", flags_row)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("utilBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Preset")
        save_btn.setObjectName("copyBtn")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        if not self.name_input.text().strip() or not self.expr_input.text().strip():
            QMessageBox.warning(self, "Missing Fields", "Both Name and Pattern are required.")
            return
        self.accept()

    def get_data(self) -> Dict[str, Any]:
        return {
            "name": self.name_input.text().strip(),
            "expression": self.expr_input.text().strip(),
            "replacement": self.repl_input.text(),
            "description": self.desc_input.text().strip(),
            "mode": self.mode_combo.currentData(),
            "is_literal": self.literal_cb.isChecked(),
            "ignore_case": self.ignore_case_cb.isChecked(),
            "disable_multiline": self.disable_multiline_cb.isChecked(),
            "dot_all": self.dot_all_cb.isChecked(),
        }


class PresetsDialog(QDialog):
    """Dialog displaying saved and commonly used regex expressions."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        preset_manager: Optional[PresetManager] = None,
        current_pattern: str = "",
        current_state: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent)
        self.preset_manager = preset_manager or PresetManager()
        self.current_pattern = current_pattern
        self.current_state = current_state or {}
        self.setWindowTitle("Commonly Used Expressions")
        self.resize(840, 520)
        self.setMinimumSize(620, 420)
        self.selected_expression: Optional[str] = None
        self.selected_preset: Optional[Dict[str, Any]] = None
        self._all_presets: List[Dict[str, Any]] = self.preset_manager.get_all_presets()
        self._filtered_presets: List[Dict[str, Any]] = list(self._all_presets)

        self._init_ui()
        self._populate_table()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("Commonly Used Expressions (Presets)")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        sub_label = QLabel(
            "Select an expression and click 'Use Expression' or double-click to insert it "
            "(presets with saved replacements or flags apply those automatically)."
        )
        sub_label.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(sub_label)

        # Top Bar: Search / Filter & CRUD Actions
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter presets by name, pattern, replacement, or description...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.search_input, stretch=1)

        self.add_preset_btn = QPushButton("+ Add")
        self.add_preset_btn.setObjectName("utilBtn")
        self.add_preset_btn.setToolTip("Save current pattern/replacement/flags as a new custom preset")
        self.add_preset_btn.clicked.connect(self._on_add_preset_clicked)
        filter_row.addWidget(self.add_preset_btn)

        self.edit_preset_btn = QPushButton("Edit")
        self.edit_preset_btn.setObjectName("utilBtn")
        self.edit_preset_btn.setToolTip("Edit selected custom preset")
        self.edit_preset_btn.setEnabled(False)
        self.edit_preset_btn.clicked.connect(self._on_edit_preset_clicked)
        filter_row.addWidget(self.edit_preset_btn)

        self.delete_preset_btn = QPushButton("Delete")
        self.delete_preset_btn.setObjectName("utilBtn")
        self.delete_preset_btn.setToolTip("Delete selected custom preset")
        self.delete_preset_btn.setEnabled(False)
        self.delete_preset_btn.clicked.connect(self._on_delete_preset_clicked)
        filter_row.addWidget(self.delete_preset_btn)

        layout.addLayout(filter_row)

        # Presets Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Expression", "Replacement", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, stretch=1)

        # Bottom Buttons: Import/Export on left, Cancel/Use on right
        btn_layout = QHBoxLayout()

        self.import_btn = QPushButton("Import JSON...")
        self.import_btn.setObjectName("utilBtn")
        self.import_btn.clicked.connect(self._on_import_clicked)
        btn_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export JSON...")
        self.export_btn.setObjectName("utilBtn")
        self.export_btn.clicked.connect(self._on_export_clicked)
        btn_layout.addWidget(self.export_btn)

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
            name_item = QTableWidgetItem(str(item.get("name", "")))
            name_item.setFont(QFont("", 10, QFont.Bold))

            exp_item = QTableWidgetItem(str(item.get("expression", "")))
            exp_item.setFont(mono_font)

            repl_item = QTableWidgetItem(str(item.get("replacement", "")))
            repl_item.setFont(mono_font)

            desc_text = str(item.get("description", ""))
            flags_badges = []
            if item.get("is_literal"):
                flags_badges.append("literal")
            if item.get("ignore_case"):
                flags_badges.append("i")
            if item.get("disable_multiline"):
                flags_badges.append("single-line")
            if item.get("dot_all"):
                flags_badges.append("s")
            if flags_badges:
                badge_str = f"[{', '.join(flags_badges)}]"
                desc_text = f"{badge_str} {desc_text}".strip()
            desc_item = QTableWidgetItem(desc_text)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, exp_item)
            self.table.setItem(row, 2, repl_item)
            self.table.setItem(row, 3, desc_item)

        if self._filtered_presets:
            self.table.selectRow(0)
        else:
            self._on_selection_changed()

    def _get_selected_preset(self) -> Optional[Dict[str, Any]]:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        if 0 <= row < len(self._filtered_presets):
            return self._filtered_presets[row]
        return None

    def _on_filter_changed(self, text: str) -> None:
        query = text.lower().strip()
        if not query:
            self._filtered_presets = list(self._all_presets)
        else:
            self._filtered_presets = [
                p for p in self._all_presets
                if query in str(p.get("name", "")).lower()
                or query in str(p.get("expression", "")).lower()
                or query in str(p.get("replacement", "")).lower()
                or query in str(p.get("description", "")).lower()
            ]
        self._populate_table()

    def _on_selection_changed(self) -> None:
        preset = self._get_selected_preset()
        has_sel = preset is not None
        is_user = has_sel and not bool(preset.get("_builtin", False))
        self.use_btn.setEnabled(has_sel)
        self.edit_preset_btn.setEnabled(is_user)
        self.delete_preset_btn.setEnabled(is_user)

    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if 0 <= row < len(self._filtered_presets):
            self.selected_preset = self._filtered_presets[row]
            self.selected_expression = str(self.selected_preset.get("expression", ""))
            self.accept()

    def _on_use_clicked(self) -> None:
        preset = self._get_selected_preset()
        if preset is not None:
            self.selected_preset = preset
            self.selected_expression = str(preset.get("expression", ""))
            self.accept()

    def _refresh_presets(self) -> None:
        self._all_presets = self.preset_manager.get_all_presets()
        self._on_filter_changed(self.search_input.text())

    def _on_add_preset_clicked(self) -> None:
        initial = dict(self.current_state)
        initial.setdefault("expression", self.current_pattern)
        dlg = PresetEditorDialog(self, title="Add Custom Preset", initial=initial)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            self.preset_manager.add_user_preset(**data)
            self._refresh_presets()

    def _on_edit_preset_clicked(self) -> None:
        preset = self._get_selected_preset()
        if not preset or preset.get("_builtin"):
            return
        old_name = str(preset["name"])
        dlg = PresetEditorDialog(self, title=f"Edit Preset: {old_name}", initial=preset)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            new_name = data.pop("name")
            self.preset_manager.update_user_preset(old_name=old_name, new_name=new_name, **data)
            self._refresh_presets()

    def _on_delete_preset_clicked(self) -> None:
        preset = self._get_selected_preset()
        if not preset or preset.get("_builtin"):
            return
        name = str(preset["name"])
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Delete custom preset '{name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.preset_manager.remove_user_preset(name)
            self._refresh_presets()

    def _on_import_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Presets JSON", "", "JSON Files (*.json)")
        if path:
            try:
                count = self.preset_manager.import_presets(Path(path))
                self._refresh_presets()
                QMessageBox.information(self, "Import Complete", f"Imported {count} preset(s).")
            except Exception as e:
                QMessageBox.warning(self, "Import Failed", str(e))

    def _on_export_clicked(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Custom Presets JSON", "presets.json", "JSON Files (*.json)")
        if path:
            try:
                count = self.preset_manager.export_presets(Path(path))
                QMessageBox.information(self, "Export Complete", f"Exported {count} custom preset(s).")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", str(e))

    @classmethod
    def select_preset(
        cls,
        parent: Optional[QWidget] = None,
        current_pattern: str = "",
        preset_manager: Optional[PresetManager] = None,
    ) -> Optional[str]:
        """Backwards-compatible helper returning the selected expression string."""
        dialog = cls(parent, preset_manager=preset_manager, current_pattern=current_pattern)
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_expression
        return None

    @classmethod
    def select_preset_full(
        cls,
        parent: Optional[QWidget] = None,
        current_pattern: str = "",
        preset_manager: Optional[PresetManager] = None,
        current_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Shows the dialog and returns the full preset dictionary (expression, replacement, flags, mode)."""
        dialog = cls(
            parent,
            preset_manager=preset_manager,
            current_pattern=current_pattern,
            current_state=current_state,
        )
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_preset
        return None
