"""
Pipeline Dialog for Regex Stripper
Allows building, saving, editing, reordering, and running multi-step
cleaning recipes (chained regex operations + line utilities).
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QWidget,
    QMessageBox,
    QSplitter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.core.pipeline_manager import PipelineManager, PIPELINE_ACTION_LABELS


class StepEditorDialog(QDialog):
    """Form dialog to configure a single pipeline step."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configure Pipeline Step")
        self.setModal(True)
        self.setMinimumWidth(460)
        self._initial = initial or {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.action_combo = QComboBox()
        for key, label in PIPELINE_ACTION_LABELS.items():
            self.action_combo.addItem(label, key)
        init_action = self._initial.get("action", "delete_matches")
        idx = self.action_combo.findData(init_action)
        if idx >= 0:
            self.action_combo.setCurrentIndex(idx)
        self.action_combo.currentIndexChanged.connect(self._update_field_visibility)
        form.addRow("Action:", self.action_combo)

        mono = QFont("Cascadia Code", 10)
        mono.setStyleHint(QFont.Monospace)

        self.pattern_input = QLineEdit(str(self._initial.get("pattern", "")))
        self.pattern_input.setFont(mono)
        self.pattern_input.setPlaceholderText("Regex or literal pattern...")
        form.addRow("Pattern:", self.pattern_input)

        self.repl_input = QLineEdit(str(self._initial.get("replacement", "")))
        self.repl_input.setFont(mono)
        self.repl_input.setPlaceholderText("Replacement text (for Replace Matches)...")
        form.addRow("Replacement:", self.repl_input)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Ascending (A → Z)", "asc")
        self.sort_combo.addItem("Descending (Z → A)", "desc")
        self.sort_combo.addItem("Natural Numeric", "natural")
        self.sort_combo.addItem("By Line Length", "length")
        s_idx = self.sort_combo.findData(self._initial.get("sort_mode", "asc"))
        if s_idx >= 0:
            self.sort_combo.setCurrentIndex(s_idx)
        form.addRow("Sort Order:", self.sort_combo)

        flags_row = QHBoxLayout()
        self.ignore_case_cb = QCheckBox("Ignore Case")
        self.ignore_case_cb.setChecked(bool(self._initial.get("ignore_case", False)))
        self.literal_cb = QCheckBox("Literal")
        self.literal_cb.setChecked(bool(self._initial.get("is_literal", False)))
        self.dot_all_cb = QCheckBox("Dot All")
        self.dot_all_cb.setChecked(bool(self._initial.get("dot_all", False)))
        self.escapes_cb = QCheckBox(r"Interpret \n/\t")
        self.escapes_cb.setChecked(bool(self._initial.get("interpret_escapes", False)))
        flags_row.addWidget(self.ignore_case_cb)
        flags_row.addWidget(self.literal_cb)
        flags_row.addWidget(self.dot_all_cb)
        flags_row.addWidget(self.escapes_cb)
        form.addRow("Flags:", flags_row)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("utilBtn")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        ok_btn = QPushButton("Save Step")
        ok_btn.setObjectName("copyBtn")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

        self._update_field_visibility()

    def _update_field_visibility(self) -> None:
        action = self.action_combo.currentData()
        needs_pattern = action in (
            "delete_matches", "replace_matches", "delete_non_matches",
            "delete_matching_lines", "keep_matching_lines"
        )
        needs_repl = action == "replace_matches"
        needs_sort = action == "sort_lines"
        self.pattern_input.setEnabled(needs_pattern)
        self.repl_input.setEnabled(needs_repl)
        self.sort_combo.setEnabled(needs_sort)
        self.literal_cb.setEnabled(needs_pattern)
        self.dot_all_cb.setEnabled(needs_pattern)
        self.escapes_cb.setEnabled(needs_repl)

    def _on_ok(self) -> None:
        action = self.action_combo.currentData()
        needs_pattern = action in (
            "delete_matches", "replace_matches", "delete_non_matches",
            "delete_matching_lines", "keep_matching_lines"
        )
        if needs_pattern and not self.pattern_input.text().strip():
            QMessageBox.warning(self, "Pattern Required", "Please enter a pattern for this step.")
            return
        self.accept()

    def get_step(self) -> Dict[str, Any]:
        action = self.action_combo.currentData()
        step: Dict[str, Any] = {"action": action}
        if self.pattern_input.isEnabled():
            step["pattern"] = self.pattern_input.text()
        if self.repl_input.isEnabled():
            step["replacement"] = self.repl_input.text()
            if self.escapes_cb.isChecked():
                step["interpret_escapes"] = True
        if self.sort_combo.isEnabled():
            step["sort_mode"] = self.sort_combo.currentData()
        if self.ignore_case_cb.isChecked():
            step["ignore_case"] = True
        if self.literal_cb.isEnabled() and self.literal_cb.isChecked():
            step["is_literal"] = True
        if self.dot_all_cb.isEnabled() and self.dot_all_cb.isChecked():
            step["dot_all"] = True
        return step


class PipelineDialog(QDialog):
    """Dialog for managing and running multi-step text cleaning pipelines."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        pipeline_manager: Optional[PipelineManager] = None,
        current_step_template: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent)
        self.pipeline_manager = pipeline_manager or PipelineManager()
        self.current_step_template = current_step_template
        self.selected_pipeline: Optional[Dict[str, Any]] = None

        self.setWindowTitle("Cleaning Pipelines (Multi-Step Recipes)")
        self.resize(840, 520)
        self.setMinimumSize(640, 420)

        self._pipelines: List[Dict[str, Any]] = []
        self._working_steps: List[Dict[str, Any]] = []
        self._init_ui()
        self._load_pipelines()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("Cleaning Pipelines (Multi-Step Recipes)")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        sub = QLabel(
            "Chain multiple regex and line-cleanup operations into reusable 1-click recipes."
        )
        sub.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(sub)

        splitter = QSplitter(Qt.Horizontal)

        # Left pane: Saved pipelines list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.addWidget(QLabel("Saved Pipelines:"))

        self.pipeline_list = QListWidget()
        self.pipeline_list.currentRowChanged.connect(self._on_pipeline_selected)
        left_layout.addWidget(self.pipeline_list, stretch=1)

        left_btns = QHBoxLayout()
        self.new_btn = QPushButton("+ New")
        self.new_btn.setObjectName("utilBtn")
        self.new_btn.clicked.connect(self._on_new_pipeline)
        left_btns.addWidget(self.new_btn)

        self.del_pipeline_btn = QPushButton("Delete")
        self.del_pipeline_btn.setObjectName("utilBtn")
        self.del_pipeline_btn.clicked.connect(self._on_delete_pipeline)
        left_btns.addWidget(self.del_pipeline_btn)
        left_layout.addLayout(left_btns)

        splitter.addWidget(left_widget)

        # Right pane: Pipeline details & steps editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)

        meta_form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Pipeline name...")
        meta_form.addRow("Name:", self.name_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Short description...")
        meta_form.addRow("Description:", self.desc_edit)
        right_layout.addLayout(meta_form)

        right_layout.addWidget(QLabel("Steps (executed top to bottom):"))
        self.steps_list = QListWidget()
        right_layout.addWidget(self.steps_list, stretch=1)

        step_btns = QHBoxLayout()
        self.add_step_btn = QPushButton("+ Add Step")
        self.add_step_btn.setObjectName("utilBtn")
        self.add_step_btn.clicked.connect(self._on_add_step)
        step_btns.addWidget(self.add_step_btn)

        self.add_current_btn = QPushButton("+ Current Pattern")
        self.add_current_btn.setObjectName("utilBtn")
        self.add_current_btn.setToolTip("Append current main window pattern/mode as a step")
        self.add_current_btn.setEnabled(bool(self.current_step_template and self.current_step_template.get("pattern")))
        self.add_current_btn.clicked.connect(self._on_add_current_step)
        step_btns.addWidget(self.add_current_btn)

        self.up_btn = QPushButton("▲")
        self.up_btn.setObjectName("utilBtn")
        self.up_btn.clicked.connect(lambda: self._move_step(-1))
        step_btns.addWidget(self.up_btn)

        self.down_btn = QPushButton("▼")
        self.down_btn.setObjectName("utilBtn")
        self.down_btn.clicked.connect(lambda: self._move_step(1))
        step_btns.addWidget(self.down_btn)

        self.remove_step_btn = QPushButton("Remove Step")
        self.remove_step_btn.setObjectName("utilBtn")
        self.remove_step_btn.clicked.connect(self._on_remove_step)
        step_btns.addWidget(self.remove_step_btn)

        right_layout.addLayout(step_btns)

        save_row = QHBoxLayout()
        save_row.addStretch()
        self.save_pipeline_btn = QPushButton("Save Changes")
        self.save_pipeline_btn.setObjectName("utilBtn")
        self.save_pipeline_btn.clicked.connect(self._on_save_pipeline)
        save_row.addWidget(self.save_pipeline_btn)
        right_layout.addLayout(save_row)

        splitter.addWidget(right_widget)
        splitter.setSizes([250, 560])
        layout.addWidget(splitter, stretch=1)

        # Bottom dialog buttons
        bottom = QHBoxLayout()
        bottom.addStretch()

        self.cancel_btn = QPushButton("Close")
        self.cancel_btn.setObjectName("utilBtn")
        self.cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(self.cancel_btn)

        self.run_btn = QPushButton("Run Pipeline")
        self.run_btn.setObjectName("copyBtn")
        self.run_btn.setMinimumWidth(130)
        self.run_btn.clicked.connect(self._on_run_clicked)
        bottom.addWidget(self.run_btn)

        layout.addLayout(bottom)

    def _load_pipelines(self, select_name: Optional[str] = None) -> None:
        self._pipelines = self.pipeline_manager.get_all_pipelines()
        self.pipeline_list.clear()
        target_row = 0
        for idx, p in enumerate(self._pipelines):
            prefix = "★ " if p.get("_builtin") else ""
            self.pipeline_list.addItem(f"{prefix}{p['name']}")
            if select_name and p["name"] == select_name:
                target_row = idx
        if self._pipelines:
            self.pipeline_list.setCurrentRow(target_row)

    def _refresh_steps_list(self) -> None:
        self.steps_list.clear()
        for idx, step in enumerate(self._working_steps, start=1):
            self.steps_list.addItem(f"{idx}. {PipelineManager.format_step_summary(step)}")
        self.run_btn.setEnabled(len(self._working_steps) > 0)

    def _on_pipeline_selected(self, row: int) -> None:
        if 0 <= row < len(self._pipelines):
            p = self._pipelines[row]
            self.name_edit.setText(p["name"])
            self.desc_edit.setText(p.get("description", ""))
            self._working_steps = [dict(s) for s in p.get("steps", [])]
            is_builtin = bool(p.get("_builtin", False))
            self.del_pipeline_btn.setEnabled(not is_builtin)
            self._refresh_steps_list()
        else:
            self.name_edit.clear()
            self.desc_edit.clear()
            self._working_steps = []
            self.del_pipeline_btn.setEnabled(False)
            self._refresh_steps_list()

    def _on_new_pipeline(self) -> None:
        self.pipeline_list.clearSelection()
        self.name_edit.setText("New Cleaning Pipeline")
        self.desc_edit.clear()
        self._working_steps = []
        self.del_pipeline_btn.setEnabled(False)
        self._refresh_steps_list()
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _on_delete_pipeline(self) -> None:
        row = self.pipeline_list.currentRow()
        if 0 <= row < len(self._pipelines):
            p = self._pipelines[row]
            if p.get("_builtin"):
                return
            self.pipeline_manager.remove_pipeline(p["name"])
            self._load_pipelines()

    def _on_add_step(self) -> None:
        dlg = StepEditorDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._working_steps.append(dlg.get_step())
            self._refresh_steps_list()

    def _on_add_current_step(self) -> None:
        if self.current_step_template:
            self._working_steps.append(dict(self.current_step_template))
            self._refresh_steps_list()

    def _move_step(self, delta: int) -> None:
        row = self.steps_list.currentRow()
        new_row = row + delta
        if 0 <= row < len(self._working_steps) and 0 <= new_row < len(self._working_steps):
            self._working_steps[row], self._working_steps[new_row] = (
                self._working_steps[new_row], self._working_steps[row]
            )
            self._refresh_steps_list()
            self.steps_list.setCurrentRow(new_row)

    def _on_remove_step(self) -> None:
        row = self.steps_list.currentRow()
        if 0 <= row < len(self._working_steps):
            self._working_steps.pop(row)
            self._refresh_steps_list()

    def _on_save_pipeline(self) -> None:
        name = self.name_edit.text().strip()
        if not name or not self._working_steps:
            QMessageBox.warning(self, "Invalid Pipeline", "Provide a pipeline name and at least one step.")
            return
        if PipelineManager.is_builtin(name):
            name = f"{name} (Custom)"
            self.name_edit.setText(name)
        self.pipeline_manager.save_pipeline(name, self._working_steps, self.desc_edit.text().strip())
        self._load_pipelines(select_name=name)

    def _on_run_clicked(self) -> None:
        if not self._working_steps:
            return
        self.selected_pipeline = {
            "name": self.name_edit.text().strip() or "Pipeline",
            "steps": [dict(s) for s in self._working_steps],
        }
        self.accept()

    @classmethod
    def choose_pipeline(
        cls,
        parent: Optional[QWidget] = None,
        pipeline_manager: Optional[PipelineManager] = None,
        current_step_template: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        dialog = cls(parent, pipeline_manager=pipeline_manager, current_step_template=current_step_template)
        if dialog.exec() == QDialog.Accepted:
            return dialog.selected_pipeline
        return None
