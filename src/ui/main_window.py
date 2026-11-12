"""
Main Window for Regex Stripper
Coordinates UI components, real-time highlighting, mode toggling,
confirmation dialogs, history persistence, clipboard operations,
theme switching (Dark/Light with SVG icons), regex replacement,
literal match mode, multi-level undo, regex quick reference, presets,
file drag-and-drop, save-to-file, match navigation, word-wrap, and diff view.
"""

from __future__ import annotations
import re
from collections import deque
from pathlib import Path
from typing import Optional, List, Tuple

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
    QLabel,
    QFrame,
    QApplication,
    QFileDialog,
    QStatusBar,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QIcon, QTextCursor

from src.config import (
    APP_TITLE,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    HIGHLIGHT_DEBOUNCE_MS,
    MAX_UNDO_STEPS,
    DeletionMode,
    AppTheme,
    COLOR_STATUS_MATCH,
    COLOR_STATUS_NO_MATCH,
    COLOR_STATUS_ERROR,
    MONOSPACE_FONTS,
    APP_ICON_PATH,
    ICON_SUN,
    ICON_MOON,
    ICON_REPLACE,
    ICON_DELETE,
    ICON_COPY,
    ICON_PASTE,
    ICON_CLEAR,
    ICON_UNDO,
    ICON_BOOK,
    ICON_BOOKMARK,
    ICON_SAVE,
    ICON_ARROW_UP,
    ICON_ARROW_DOWN,
    ICON_DEDUP,
)
from src.core.regex_engine import RegexEngine
from src.core.history_manager import HistoryManager
from src.core.settings_manager import SettingsManager
from src.core.preset_manager import PresetManager
from src.ui.editor import DragDropEditor
from src.ui.highlighter import MatchHighlighter
from src.ui.confirmation_dialog import (
    DeleteConfirmationDialog,
    DeleteDuplicatesConfirmationDialog,
)
from src.ui.regex_reference_dialog import RegexReferenceDialog
from src.ui.presets_dialog import PresetsDialog
from src.ui.styles import get_stylesheet


class MainWindow(QMainWindow):
    """Main application window for Regex Stripper."""

    def __init__(
        self,
        history_manager: Optional[HistoryManager] = None,
        settings_manager: Optional[SettingsManager] = None,
        preset_manager: Optional[PresetManager] = None
    ):
        super().__init__()
        self.history_manager = history_manager or HistoryManager()
        self.settings_manager = settings_manager or SettingsManager()
        self.preset_manager = preset_manager or PresetManager()
        self.current_theme: AppTheme = self.settings_manager.theme
        self.active_mode: DeletionMode = DeletionMode.DELETE_MATCHES

        # Multi-level undo stack (stores historical text states)
        self.undo_stack: deque[str] = deque(maxlen=MAX_UNDO_STEPS)

        # Source text tracking & Inline Replace Diff state
        self._raw_text: str = ""
        self._is_previewing: bool = False

        # Match navigation cache
        self.current_match_spans: List[Tuple[int, int]] = []
        self.current_match_index: int = -1

        self.setWindowTitle(APP_TITLE)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        self.setStyleSheet(get_stylesheet(self.current_theme))

        # Setup Debounce Timer for real-time highlighting
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(HIGHLIGHT_DEBOUNCE_MS)
        self.debounce_timer.timeout.connect(self._apply_highlights)

        self._init_ui()
        self._populate_history()
        self._setup_shortcuts()
        self._update_theme_button_ui()

        # Initial button states
        self.copy_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.replace_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self.prev_match_btn.setEnabled(False)
        self.next_match_btn.setEnabled(False)
        self._update_status(0, True, "")

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # ==========================================
        # TOP PANEL: Pattern, Replace, Flags & Mode
        # ==========================================
        top_panel = QFrame()
        top_panel.setObjectName("topPanel")
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(10)

        # Row 1: Pattern Input & Helper Action Buttons
        pattern_row = QHBoxLayout()
        self.pattern_label = QLabel("Regex Pattern:")
        self.pattern_label.setStyleSheet("font-weight: 600; min-width: 95px;")
        pattern_row.addWidget(self.pattern_label)

        self.pattern_combo = QComboBox()
        self.pattern_combo.setObjectName("patternCombo")
        self.pattern_combo.setEditable(True)
        self.pattern_combo.setInsertPolicy(QComboBox.NoInsert)
        self.pattern_combo.lineEdit().setPlaceholderText(
            r"Enter regex pattern (e.g. \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b)..."
        )
        self.pattern_combo.lineEdit().setClearButtonEnabled(True)
        self.pattern_combo.editTextChanged.connect(self._on_pattern_changed)
        pattern_row.addWidget(self.pattern_combo, stretch=1)

        # Saved Presets Button
        self.presets_btn = QPushButton(" Presets")
        self.presets_btn.setObjectName("utilBtn")
        self.presets_btn.setIcon(QIcon(str(ICON_BOOKMARK)))
        self.presets_btn.setIconSize(QSize(16, 16))
        self.presets_btn.setToolTip("View, insert & save commonly used expressions")
        self.presets_btn.clicked.connect(self._on_presets_clicked)
        pattern_row.addWidget(self.presets_btn)

        # Quick Reference Button
        self.ref_btn = QPushButton(" Reference")
        self.ref_btn.setObjectName("utilBtn")
        self.ref_btn.setIcon(QIcon(str(ICON_BOOK)))
        self.ref_btn.setIconSize(QSize(16, 16))
        self.ref_btn.setToolTip("Open Regex Quick Reference cheat sheet")
        self.ref_btn.clicked.connect(self._on_reference_clicked)
        pattern_row.addWidget(self.ref_btn)

        # Theme Toggle Button (Light/Dark mode with SVG icon)
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setIconSize(QSize(20, 20))
        self.theme_btn.clicked.connect(self._toggle_theme)
        pattern_row.addWidget(self.theme_btn)

        top_layout.addLayout(pattern_row)

        # Row 2: Replace Input Field & Replace Button (Under Regex Entry)
        replace_row = QHBoxLayout()
        self.replace_label = QLabel("Replace With:")
        self.replace_label.setStyleSheet("font-weight: 600; min-width: 95px;")
        replace_row.addWidget(self.replace_label)

        self.replace_input = QLineEdit()
        self.replace_input.setObjectName("replaceInput")
        self.replace_input.setPlaceholderText(
            r"Enter replacement text (supports \1, \g<name>, etc.)..."
        )
        self.replace_input.setClearButtonEnabled(True)
        replace_font = QFont()
        replace_font.setFamilies(MONOSPACE_FONTS)
        replace_font.setPointSize(10)
        self.replace_input.setFont(replace_font)
        self.replace_input.textChanged.connect(self._on_replace_input_changed)
        replace_row.addWidget(self.replace_input, stretch=1)

        self.replace_btn = QPushButton(" Replace Matches")
        self.replace_btn.setObjectName("replaceBtn")
        self.replace_btn.setIcon(QIcon(str(ICON_REPLACE)))
        self.replace_btn.setIconSize(QSize(16, 16))
        self.replace_btn.setMinimumHeight(32)
        self.replace_btn.setToolTip("Replace all matching text with replacement string (Ctrl+R)")
        self.replace_btn.clicked.connect(self._on_replace_clicked)
        replace_row.addWidget(self.replace_btn)

        top_layout.addLayout(replace_row)

        # Row 3: Options (Literal Match, Flags & Mode Toggle)
        options_row = QHBoxLayout()
        options_row.setSpacing(14)

        # Literal Match Checkbox
        self.literal_match_cb = QCheckBox("Literal Match (No Regex)")
        self.literal_match_cb.setToolTip(
            "Match exact text literally; disables regex tokens (e.g. \\n matches backslash and n)"
        )
        self.literal_match_cb.toggled.connect(self._on_literal_toggled)
        options_row.addWidget(self.literal_match_cb)

        # Flags
        self.ignore_case_cb = QCheckBox("Ignore Case (i)")
        self.ignore_case_cb.setToolTip("Case-insensitive matching (re.IGNORECASE)")
        self.ignore_case_cb.toggled.connect(self._on_options_changed)
        options_row.addWidget(self.ignore_case_cb)

        self.disable_multiline_cb = QCheckBox("Disable multiline")
        self.disable_multiline_cb.setChecked(False)
        self.disable_multiline_cb.setToolTip(
            "When checked, treats text as a single line (^ and $ only match start/end of the entire text)."
        )
        self.disable_multiline_cb.toggled.connect(self._on_options_changed)
        options_row.addWidget(self.disable_multiline_cb)
        self.multiline_cb = self.disable_multiline_cb

        self.dot_all_cb = QCheckBox("Dot Matches All (s)")
        self.dot_all_cb.setToolTip("Dot matches newlines (re.DOTALL)")
        self.dot_all_cb.toggled.connect(self._on_options_changed)
        options_row.addWidget(self.dot_all_cb)

        # Separator line
        v_line = QFrame()
        v_line.setFrameShape(QFrame.VLine)
        v_line.setFrameShadow(QFrame.Sunken)
        options_row.addWidget(v_line)

        # Mode Selection
        mode_label = QLabel("Action Mode:")
        mode_label.setStyleSheet("font-weight: 600;")
        options_row.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)
        self.mode_delete_matches = QRadioButton("Delete Matches (Default)")
        self.mode_delete_matches.setChecked(True)
        self.mode_group.addButton(self.mode_delete_matches)
        options_row.addWidget(self.mode_delete_matches)

        self.mode_delete_non_matches = QRadioButton("Delete Non-Matches (Keep Matches)")
        self.mode_group.addButton(self.mode_delete_non_matches)
        options_row.addWidget(self.mode_delete_non_matches)

        self.mode_delete_matches.toggled.connect(self._on_mode_toggled)

        options_row.addStretch()
        top_layout.addLayout(options_row)

        # Row 3.5: Contextual Extraction Options (Visible in Delete Non-Matches mode)
        self.extraction_panel = QFrame()
        self.extraction_panel.setStyleSheet(
            "background-color: rgba(128, 128, 128, 0.08); border-radius: 6px; padding: 4px;"
        )
        extract_layout = QHBoxLayout(self.extraction_panel)
        extract_layout.setContentsMargins(8, 4, 8, 4)
        extract_layout.setSpacing(14)

        extract_label = QLabel("Extraction Settings:")
        extract_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        extract_layout.addWidget(extract_label)

        delim_label = QLabel("Delimiter:")
        extract_layout.addWidget(delim_label)

        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItems([
            r"\n (Newline)",
            r",  (Comma + Space)",
            r", (Comma)",
            r"  (Space)",
            r"; (Semicolon)",
            r"\t (Tab)",
            r"None (Concatenate)"
        ])
        extract_layout.addWidget(self.delimiter_combo)

        self.unique_cb = QCheckBox("Unique Only (Deduplicate)")
        self.unique_cb.setToolTip("Strip redundant duplicate matches, keeping only unique occurrences")
        extract_layout.addWidget(self.unique_cb)

        group_label = QLabel("Capture Group:")
        extract_layout.addWidget(group_label)

        self.capture_group_input = QLineEdit("0")
        self.capture_group_input.setMaximumWidth(60)
        self.capture_group_input.setToolTip("0 for full match, 1/2 for capture group, or template e.g. \\1")
        extract_layout.addWidget(self.capture_group_input)

        extract_layout.addStretch()
        top_layout.addWidget(self.extraction_panel)
        self.extraction_panel.setVisible(False)  # Hidden initially in Default Mode

        # Row 4: Status Indicator & Match Navigation Controls
        status_row = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label, stretch=1)

        # Match navigation buttons
        self.prev_match_btn = QPushButton(" ▲ Prev")
        self.prev_match_btn.setObjectName("navBtn")
        self.prev_match_btn.setIcon(QIcon(str(ICON_ARROW_UP)))
        self.prev_match_btn.setIconSize(QSize(12, 12))
        self.prev_match_btn.setToolTip("Jump to previous match (Shift+F3)")
        self.prev_match_btn.clicked.connect(lambda: self._navigate_match(-1))
        status_row.addWidget(self.prev_match_btn)

        self.next_match_btn = QPushButton(" ▼ Next")
        self.next_match_btn.setObjectName("navBtn")
        self.next_match_btn.setIcon(QIcon(str(ICON_ARROW_DOWN)))
        self.next_match_btn.setIconSize(QSize(12, 12))
        self.next_match_btn.setToolTip("Jump to next match (F3)")
        self.next_match_btn.clicked.connect(lambda: self._navigate_match(1))
        status_row.addWidget(self.next_match_btn)

        self.match_nav_label = QLabel("")
        self.match_nav_label.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        status_row.addWidget(self.match_nav_label)

        top_layout.addLayout(status_row)
        main_layout.addWidget(top_panel)

        # ==========================================
        # CENTRAL AREA: Drag & Drop Monospace Editor
        # ==========================================
        self.editor = DragDropEditor()
        self.editor.setObjectName("editor")
        self.editor.setPlaceholderText(
            "Paste text here or drag & drop a file (.txt, .log, .csv, .md, .html)..."
        )
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._update_cursor_stats)
        self.editor.fileDropped.connect(self._on_file_dropped)
        self.editor.readOnlyAttempted.connect(self._on_editor_readonly_attempted)

        main_layout.addWidget(self.editor, stretch=1)

        # Setup Highlighter with initial theme
        self.highlighter = MatchHighlighter(self.editor, theme=self.current_theme)

        # ==========================================
        # BOTTOM ACTION BAR
        # ==========================================
        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottomBar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(4, 4, 4, 4)
        bottom_layout.setSpacing(10)

        # Undo Button
        self.undo_btn = QPushButton(" Undo")
        self.undo_btn.setObjectName("utilBtn")
        self.undo_btn.setIcon(QIcon(str(ICON_UNDO)))
        self.undo_btn.setIconSize(QSize(16, 16))
        self.undo_btn.setToolTip("Undo last deletion or replacement operation (Ctrl+Shift+Z)")
        self.undo_btn.clicked.connect(self._on_undo_clicked)
        bottom_layout.addWidget(self.undo_btn)

        # Paste & Clear Buttons
        self.paste_btn = QPushButton(" Paste")
        self.paste_btn.setObjectName("utilBtn")
        self.paste_btn.setIcon(QIcon(str(ICON_PASTE)))
        self.paste_btn.setIconSize(QSize(16, 16))
        self.paste_btn.setToolTip("Paste clipboard content into the editor")
        self.paste_btn.clicked.connect(self._on_paste_clicked)
        bottom_layout.addWidget(self.paste_btn)

        self.clear_btn = QPushButton(" Clear")
        self.clear_btn.setObjectName("utilBtn")
        self.clear_btn.setIcon(QIcon(str(ICON_CLEAR)))
        self.clear_btn.setIconSize(QSize(16, 16))
        self.clear_btn.setToolTip("Clear all text from the editor")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        bottom_layout.addWidget(self.clear_btn)

        # Word Wrap Checkbox
        self.wrap_cb = QCheckBox("Wrap Lines")
        self.wrap_cb.setChecked(True)
        self.wrap_cb.setToolTip("Toggle soft word wrapping in the editor")
        self.wrap_cb.toggled.connect(self._on_wrap_toggled)
        bottom_layout.addWidget(self.wrap_cb)

        bottom_layout.addStretch()

        # Delete Duplicates Button
        self.delete_duplicates_btn = QPushButton(" Delete Duplicates")
        self.delete_duplicates_btn.setObjectName("deleteDupBtn")
        self.delete_duplicates_btn.setIcon(QIcon(str(ICON_DEDUP)))
        self.delete_duplicates_btn.setIconSize(QSize(16, 16))
        self.delete_duplicates_btn.setMinimumHeight(36)
        self.delete_duplicates_btn.setToolTip("Delete duplicate lines from the text (requires multiline mode)")
        self.delete_duplicates_btn.setEnabled(False)
        self.delete_duplicates_btn.clicked.connect(self._on_delete_duplicates_clicked)
        bottom_layout.addWidget(self.delete_duplicates_btn)

        # Primary Action: Delete Button
        self.delete_btn = QPushButton(" Delete Matches...")
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.setIcon(QIcon(str(ICON_DELETE)))
        self.delete_btn.setIconSize(QSize(16, 16))
        self.delete_btn.setMinimumHeight(36)
        self.delete_btn.setToolTip("Delete matching text (Ctrl+Enter)")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        bottom_layout.addWidget(self.delete_btn)

        # Secondary Action: Copy Result Button
        self.copy_btn = QPushButton(" Copy Result")
        self.copy_btn.setObjectName("copyBtn")
        self.copy_btn.setIcon(QIcon(str(ICON_COPY)))
        self.copy_btn.setIconSize(QSize(16, 16))
        self.copy_btn.setMinimumHeight(36)
        self.copy_btn.setToolTip("Copy stripped text to clipboard (Active after a delete or replace)")
        self.copy_btn.clicked.connect(self._on_copy_clicked)
        bottom_layout.addWidget(self.copy_btn)

        # Save to File Button
        self.save_btn = QPushButton(" Save As...")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.setIcon(QIcon(str(ICON_SAVE)))
        self.save_btn.setIconSize(QSize(16, 16))
        self.save_btn.setMinimumHeight(36)
        self.save_btn.setToolTip("Save processed text directly to a file (Ctrl+S)")
        self.save_btn.clicked.connect(self._on_save_as_clicked)
        bottom_layout.addWidget(self.save_btn)

        main_layout.addWidget(bottom_bar)

        # ==========================================
        # FOOTER STATUS BAR: Ln, Col, Stats
        # ==========================================
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self.cursor_stat_label = QLabel("Ln 1, Col 1 | 0 chars | 0 words")
        self.cursor_stat_label.setStyleSheet("color: #64748B; font-size: 11px;")
        status_bar.addPermanentWidget(self.cursor_stat_label)

    def _setup_shortcuts(self) -> None:
        """Configures keyboard shortcuts."""
        self.delete_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.delete_shortcut.activated.connect(self._on_delete_clicked)

        self.replace_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.replace_shortcut.activated.connect(self._on_replace_clicked)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self._on_save_as_clicked)

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.undo_shortcut.activated.connect(self._on_undo_clicked)

        self.copy_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        self.copy_shortcut.activated.connect(self._on_copy_shortcut)

        self.next_match_shortcut = QShortcut(QKeySequence("F3"), self)
        self.next_match_shortcut.activated.connect(lambda: self._navigate_match(1))

        self.prev_match_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        self.prev_match_shortcut.activated.connect(lambda: self._navigate_match(-1))

        self.esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.esc_shortcut.activated.connect(self._on_escape_pressed)

    def _update_theme_button_ui(self) -> None:
        """Updates the theme toggle button icon and tooltip based on active theme."""
        if self.current_theme == AppTheme.DARK:
            self.theme_btn.setIcon(QIcon(str(ICON_SUN)))
            self.theme_btn.setToolTip("Switch to Light Mode")
        else:
            self.theme_btn.setIcon(QIcon(str(ICON_MOON)))
            self.theme_btn.setToolTip("Switch to Dark Mode")

    def _toggle_theme(self) -> None:
        """Switches between Dark and Light mode."""
        self.current_theme = (
            AppTheme.LIGHT if self.current_theme == AppTheme.DARK else AppTheme.DARK
        )
        self.settings_manager.theme = self.current_theme
        self.setStyleSheet(get_stylesheet(self.current_theme))
        self.highlighter.set_theme(self.current_theme)
        self._update_theme_button_ui()

    def _populate_history(self) -> None:
        """Populates the pattern combo box with persistent history."""
        self.pattern_combo.blockSignals(True)
        self.pattern_combo.clear()
        for pat in self.history_manager.history:
            self.pattern_combo.addItem(pat)
        self.pattern_combo.setEditText("")
        self.pattern_combo.blockSignals(False)

    def _get_current_flags(self) -> int:
        flags = 0
        if self.ignore_case_cb.isChecked():
            flags |= re.IGNORECASE
        if not self.disable_multiline_cb.isChecked():
            flags |= re.MULTILINE
        if self.dot_all_cb.isChecked():
            flags |= re.DOTALL
        return flags

    def _get_selected_delimiter(self) -> str:
        """Returns the actual delimiter string selected in the dropdown."""
        text = self.delimiter_combo.currentText()
        if r"\n" in text:
            return "\n"
        if r", " in text:
            return ", "
        if r"," in text:
            return ","
        if r"Space" in text:
            return " "
        if r";" in text:
            return ";"
        if r"\t" in text:
            return "\t"
        if r"None" in text:
            return ""
        return "\n"

    def _on_literal_toggled(self, checked: bool) -> None:
        """Triggered when Literal Match mode is toggled."""
        if checked:
            self.pattern_label.setText("Literal Text:")
            self.pattern_combo.lineEdit().setPlaceholderText("Enter literal search text (no regex)...")
            self.dot_all_cb.setEnabled(False)
            self.disable_multiline_cb.setEnabled(False)
        else:
            self.pattern_label.setText("Regex Pattern:")
            self.pattern_combo.lineEdit().setPlaceholderText(
                r"Enter regex pattern (e.g. \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b)..."
            )
            self.dot_all_cb.setEnabled(True)
            self.disable_multiline_cb.setEnabled(True)

        self.debounce_timer.start()

    def _on_pattern_changed(self, text: str) -> None:
        """Triggered when the user types or selects a pattern."""
        self.debounce_timer.start()

    def _on_replace_input_changed(self, text: str) -> None:
        """Triggered when replacement text changes to update inline replace preview."""
        self.debounce_timer.start()

    def _on_escape_pressed(self) -> None:
        """Clears the replacement input on Escape, restoring raw edit mode."""
        if self.replace_input.text():
            self.replace_input.clear()

    def _on_editor_readonly_attempted(self) -> None:
        """Notifies user when typing into editor during active replacement preview."""
        if self._is_previewing:
            self.status_label.setText(
                "💡 In Replace Preview mode. Press Esc or clear 'Replace With' to edit original text."
            )
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")

    def _on_options_changed(self) -> None:
        """Triggered when flags are toggled."""
        self._update_delete_duplicates_btn_state()
        self.debounce_timer.start()

    def _on_mode_toggled(self, checked: bool) -> None:
        """Triggered when switching between Delete Matches and Delete Non-Matches."""
        if self.mode_delete_matches.isChecked():
            self.active_mode = DeletionMode.DELETE_MATCHES
            self.delete_btn.setText(" Delete Matches...")
            self.extraction_panel.setVisible(False)
        else:
            self.active_mode = DeletionMode.DELETE_NON_MATCHES
            self.delete_btn.setText(" Delete Non-Matches...")
            self.extraction_panel.setVisible(True)

        self.highlighter.set_mode(self.active_mode)
        self._apply_highlights()

    def _on_text_changed(self) -> None:
        """Triggered when editor text changes."""
        if not self._is_previewing:
            self._raw_text = self.editor.toPlainText()
        if not self._raw_text.strip():
            self.copy_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
        self._update_delete_duplicates_btn_state()
        self._update_cursor_stats()
        self.debounce_timer.start()

    def _on_wrap_toggled(self, checked: bool) -> None:
        """Toggles editor line wrapping."""
        if checked:
            self.editor.setLineWrapMode(DragDropEditor.LineWrapMode.WidgetWidth)
        else:
            self.editor.setLineWrapMode(DragDropEditor.LineWrapMode.NoWrap)

    def _on_file_dropped(self, path: str, content: str) -> None:
        """Triggered when a file is dropped into the editor."""
        self._raw_text = content
        if self._is_previewing:
            self._is_previewing = False
            self.editor.setReadOnly(False)
        self.editor.setPlainText(content)
        self.status_label.setText(f"✓ Loaded {Path(path).name} ({len(content):,} chars)")
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
        self._apply_highlights()

    def _update_cursor_stats(self) -> None:
        """Updates Ln, Col, character and word counts in the status bar."""
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        chars = len(text)
        words = len(text.split())
        self.cursor_stat_label.setText(
            f"Ln {line}, Col {col} | {chars:,} chars | {words:,} words"
        )

    def _apply_highlights(self) -> None:
        """Runs the highlighter update, inline replace preview, and refreshes status and match navigation."""
        pattern = self.pattern_combo.currentText()
        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        replacement = self.replace_input.text()

        raw_text = self.editor.toPlainText()
        self._raw_text = raw_text

        is_valid, err_msg, _ = RegexEngine.validate_pattern(
            pattern, flags, is_literal=is_literal
        )
        match_count = (
            RegexEngine.count_matches(raw_text, pattern, flags, is_literal=is_literal)
            if (is_valid and pattern and raw_text)
            else 0
        )

        # Inline Replace Diff Preview activates when:
        # 1. User has entered text in replace field
        # 2. Pattern is valid and has at least 1 match
        # 3. Text is not empty
        # 4. In Delete Matches (Default) mode
        should_preview = (
            bool(replacement)
            and is_valid
            and match_count > 0
            and bool(raw_text)
            and self.active_mode == DeletionMode.DELETE_MATCHES
        )

        if should_preview:
            preview_text, green_spans, red_spans = RegexEngine.generate_diff_preview(
                raw_text, pattern, replacement, flags, is_literal=is_literal
            )
            self._is_previewing = True
            self.editor.set_diff_preview(preview_text, raw_text)
            self.highlighter.apply_diff_highlights(green_spans, red_spans)
            self.current_match_spans = green_spans + red_spans
        else:
            if self._is_previewing:
                self._is_previewing = False
                self.editor.clear_diff_preview(raw_text)

            self.highlighter.set_pattern_and_flags(pattern, flags, is_literal=is_literal)
            if is_valid and pattern and raw_text:
                self.current_match_spans = RegexEngine.find_match_spans(
                    raw_text, pattern, flags, is_literal=is_literal
                )
            else:
                self.current_match_spans = []

        self.current_match_index = -1
        self._update_navigation_controls()
        self._update_delete_duplicates_btn_state()
        self._update_status(match_count, is_valid, err_msg)

    def _update_navigation_controls(self) -> None:
        count = len(self.current_match_spans)
        has_matches = count > 0
        self.prev_match_btn.setEnabled(has_matches)
        self.next_match_btn.setEnabled(has_matches)

        if has_matches:
            if self.current_match_index >= 0:
                self.match_nav_label.setText(f"[{self.current_match_index + 1}/{count}]")
            else:
                self.match_nav_label.setText(f"[{count} match(es)]")
        else:
            self.match_nav_label.setText("")

    def _navigate_match(self, direction: int) -> None:
        """Jumps cursor to the next or previous matching span."""
        if not self.current_match_spans:
            return

        count = len(self.current_match_spans)
        if self.current_match_index == -1:
            self.current_match_index = 0 if direction > 0 else count - 1
        else:
            self.current_match_index = (self.current_match_index + direction) % count

        start, end = self.current_match_spans[self.current_match_index]
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self._update_navigation_controls()

    def _update_status(self, match_count: int, is_valid: bool, err_msg: str) -> None:
        """Updates the status badge below the pattern input and button states."""
        pattern = self.pattern_combo.currentText()
        raw_text = self._raw_text if self._is_previewing else self.editor.toPlainText()

        if not pattern:
            self.status_label.setText("● Ready (Enter a pattern to preview targets)")
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_NO_MATCH};")
            self.delete_btn.setEnabled(False)
            self.replace_btn.setEnabled(False)
            return

        if not is_valid:
            self.status_label.setText(f"⚠️ Invalid Pattern: {err_msg}")
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_ERROR}; font-weight: bold;")
            self.delete_btn.setEnabled(False)
            self.replace_btn.setEnabled(False)
            return

        if not raw_text:
            self.status_label.setText("● Ready (Paste or enter text in the editor)")
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_NO_MATCH};")
            self.delete_btn.setEnabled(False)
            self.replace_btn.setEnabled(False)
            return

        mode_name = "Literal" if self.literal_match_cb.isChecked() else "Regex"

        # Special status description when inline replace diff preview is active
        if self._is_previewing:
            self.status_label.setText(
                f"● {match_count} {mode_name.lower()} match(es) targeted | Replace Preview: [green bold] = replacement, [red strikeout] = original"
            )
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
            self.delete_btn.setEnabled(True)
            self.replace_btn.setEnabled(True)
            return

        if self.active_mode == DeletionMode.DELETE_MATCHES:
            target_desc = f"highlighting {mode_name.lower()} matches to delete"
        else:
            target_desc = f"highlighting non-matching text to delete"

        if match_count > 0:
            self.status_label.setText(f"● {match_count} {mode_name.lower()} match(es) found ({target_desc})")
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
            self.delete_btn.setEnabled(True)
            self.replace_btn.setEnabled(True)
        else:
            self.replace_btn.setEnabled(False)
            if self.active_mode == DeletionMode.DELETE_NON_MATCHES:
                self.status_label.setText("○ 0 matches found (Warning: all text is targeted for deletion)")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_ERROR}; font-weight: bold;")
                self.delete_btn.setEnabled(True)
            else:
                self.status_label.setText("○ No matches found")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_NO_MATCH};")
                self.delete_btn.setEnabled(False)

    def _push_undo_state(self) -> None:
        """Pushes current editor text to the undo stack before mutation."""
        current = self._raw_text if self._is_previewing else self.editor.toPlainText()
        self.undo_stack.append(current)
        self.undo_btn.setEnabled(True)

    def _on_undo_clicked(self) -> None:
        """Restores previous text from the undo stack."""
        if not self.undo_stack:
            return

        prev_text = self.undo_stack.pop()
        self._raw_text = prev_text
        if self._is_previewing:
            self._is_previewing = False
            self.editor.setReadOnly(False)
        self.editor.setPlainText(prev_text)
        self.undo_btn.setEnabled(len(self.undo_stack) > 0)

        self.status_label.setText("✓ Undid last operation.")
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
        self._apply_highlights()

    def _on_replace_clicked(self) -> None:
        """Executes replacement of matching text with replacement string."""
        pattern = self.pattern_combo.currentText()
        if not pattern:
            return

        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not text:
            return

        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        is_valid, err_msg, _ = RegexEngine.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid:
            return

        replacement = self.replace_input.text()

        # Save snapshot for undo
        self._push_undo_state()

        new_text, count = RegexEngine.replace_matches(
            text, pattern, replacement, flags, is_literal=is_literal
        )

        if count > 0:
            self._raw_text = new_text
            if self._is_previewing:
                self._is_previewing = False
                self.editor.setReadOnly(False)
            self.editor.setPlainText(new_text)

            # Register pattern into history
            self.history_manager.add_pattern(pattern)
            self._populate_history()
            self.pattern_combo.setEditText(pattern)

            self.copy_btn.setEnabled(True)
            self.save_btn.setEnabled(True)

            status_msg = f"✓ Replaced {count} match(es)."
            self.status_label.setText(status_msg)
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
            self._apply_highlights()

    def _update_delete_duplicates_btn_state(self) -> None:
        """Enables the Delete Duplicates button only when Disable multiline is NOT checked and text is present."""
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        is_clickable = (not self.disable_multiline_cb.isChecked()) and bool(text)
        self.delete_duplicates_btn.setEnabled(is_clickable)

    def _on_delete_duplicates_clicked(self) -> None:
        """Removes all duplicate lines from the text after confirmation."""
        if self.disable_multiline_cb.isChecked():
            return

        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not text:
            return

        deduped_text, dup_count = RegexEngine.delete_duplicate_lines(
            text, ignore_case=self.ignore_case_cb.isChecked()
        )

        total_lines = len(text.splitlines())
        if dup_count == 0:
            QMessageBox.information(
                self,
                "No Duplicates",
                "No duplicate lines were found in the text."
            )
            return

        confirmed = DeleteDuplicatesConfirmationDialog.confirm(
            self, duplicate_count=dup_count, total_lines=total_lines
        )
        if not confirmed:
            return

        if self._is_previewing:
            self._is_previewing = False
            self.editor.setReadOnly(False)

        self._push_undo_state()
        self._raw_text = deduped_text
        self.editor.setPlainText(deduped_text)

        self.copy_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

        self._apply_highlights()
        status_msg = f"✓ Deleted {dup_count} duplicate line(s)."
        self.status_label.setText(status_msg)
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")

    def _on_delete_clicked(self) -> None:
        """Executes deletion with modal confirmation and registers pattern to history."""
        pattern = self.pattern_combo.currentText()
        if not pattern:
            return

        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not text:
            return

        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        is_valid, err_msg, _ = RegexEngine.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid:
            return

        match_count = RegexEngine.count_matches(text, pattern, flags, is_literal=is_literal)

        # 1. Pop up confirmation dialog
        confirmed = DeleteConfirmationDialog.confirm(
            self,
            self.active_mode,
            match_count,
            pattern
        )

        if not confirmed:
            return

        # 2. Save snapshot for undo
        self._push_undo_state()

        # 3. Perform the deletion operation
        if self.active_mode == DeletionMode.DELETE_MATCHES:
            new_text, count = RegexEngine.strip_matches(
                text, pattern, flags, is_literal=is_literal
            )
            status_msg = f"✓ Deleted {count} match(es)."
        else:
            delimiter = self._get_selected_delimiter()
            unique_only = self.unique_cb.isChecked()
            capture_group = self.capture_group_input.text().strip() or "0"

            new_text, count = RegexEngine.strip_non_matches(
                text,
                pattern,
                flags,
                separator=delimiter,
                is_literal=is_literal,
                unique=unique_only,
                capture_group=capture_group
            )
            status_msg = f"✓ Extracted {count} match(es) (non-matches removed)."

        self._raw_text = new_text
        if self._is_previewing:
            self._is_previewing = False
            self.editor.setReadOnly(False)
        self.editor.setPlainText(new_text)

        # 4. Register pattern into history
        self.history_manager.add_pattern(pattern)
        self._populate_history()
        self.pattern_combo.setEditText(pattern)

        self.copy_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

        self.status_label.setText(status_msg)
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
        self._apply_highlights()

    def _on_copy_clicked(self) -> None:
        """Copies editor text to clipboard and gives visual feedback."""
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        original_text = self.copy_btn.text()
        self.copy_btn.setText(" Copied!")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText(original_text))

    def _on_copy_shortcut(self) -> None:
        """Handles Ctrl+Shift+C shortcut for copy button."""
        if self.copy_btn.isEnabled():
            self._on_copy_clicked()

    def _on_save_as_clicked(self) -> None:
        """Saves current editor contents to a file."""
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not text:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Processed Text As...",
            "",
            "Text Files (*.txt);;CSV Files (*.csv);;Log Files (*.log);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.status_label.setText(f"✓ Saved to {Path(file_path).name}")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
            except Exception as e:
                self.status_label.setText(f"⚠️ Save Error: {e}")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_ERROR}; font-weight: bold;")

    def _on_paste_clicked(self) -> None:
        """Pastes clipboard contents into editor."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self._push_undo_state()
            self._raw_text = text
            if self._is_previewing:
                self._is_previewing = False
                self.editor.setReadOnly(False)
            self.editor.setPlainText(text)
            self._apply_highlights()

    def _on_clear_clicked(self) -> None:
        """Clears text from editor with undo tracking."""
        current = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if current:
            self._push_undo_state()
            self._raw_text = ""
            if self._is_previewing:
                self._is_previewing = False
                self.editor.setReadOnly(False)
            self.editor.clear()
            self.copy_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self._update_delete_duplicates_btn_state()
            self._apply_highlights()

    def _on_reference_clicked(self) -> None:
        """Opens the Regex Quick Reference cheat sheet dialog."""
        dialog = RegexReferenceDialog(self)
        dialog.exec()

    def _on_presets_clicked(self) -> None:
        """Opens the Commonly Used Expressions presets dialog."""
        current_pattern = self.pattern_combo.currentText()
        selected = PresetsDialog.select_preset(
            self,
            current_pattern=current_pattern
        )
        if selected:
            if self.literal_match_cb.isChecked():
                self.literal_match_cb.setChecked(False)
            self.pattern_combo.setEditText(selected)
            self._apply_highlights()
