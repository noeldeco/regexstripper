"""
Main Window for Regex Stripper
Coordinates UI components, single-pass real-time highlighting, line-level modes,
confirmation dialogs, history persistence, clipboard/file operations,
theme switching (Dark/Light with SVG icons), bulk & step-through replacement,
literal match mode, multi-level undo/redo, regex quick reference, rich presets,
multi-step cleaning pipelines, quick line utilities, live extraction preview,
and session persistence.
"""

from __future__ import annotations
import re
import threading
from collections import deque
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

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
    QSplitter,
    QPlainTextEdit,
    QMenu,
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal
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
    ICON_REDO,
    ICON_OPEN,
    ICON_BOOK,
    ICON_BOOKMARK,
    ICON_PIPELINE,
    ICON_LINES,
    ICON_SAVE,
    ICON_ARROW_UP,
    ICON_ARROW_DOWN,
    ICON_DEDUP,
)
from src.core.regex_engine import RegexEngine, AnalysisResult
from src.core.history_manager import HistoryManager
from src.core.settings_manager import SettingsManager
from src.core.preset_manager import PresetManager
from src.core.pipeline_manager import PipelineManager
from src.ui.editor import DragDropEditor
from src.ui.highlighter import MatchHighlighter
from src.ui.confirmation_dialog import (
    DeleteConfirmationDialog,
    DeleteDuplicatesConfirmationDialog,
)
from src.ui.regex_reference_dialog import RegexReferenceDialog
from src.ui.presets_dialog import PresetsDialog
from src.ui.pipeline_dialog import PipelineDialog
from src.ui.styles import get_stylesheet


# Documents larger than this threshold run debounced regex analysis in a background
# thread with staleness cancellation so catastrophic regexes never freeze the UI.
_ASYNC_ANALYSIS_THRESHOLD = 100_000


class MainWindow(QMainWindow):
    """Main application window for Regex Stripper."""

    _asyncAnalysisReady = Signal(int, object, str)  # (generation_id, AnalysisResult, raw_text)

    def __init__(
        self,
        history_manager: Optional[HistoryManager] = None,
        settings_manager: Optional[SettingsManager] = None,
        preset_manager: Optional[PresetManager] = None,
        pipeline_manager: Optional[PipelineManager] = None,
    ):
        super().__init__()
        self.history_manager = history_manager or HistoryManager()
        self.settings_manager = settings_manager or SettingsManager()
        self.preset_manager = preset_manager or PresetManager()
        self.pipeline_manager = pipeline_manager or PipelineManager()
        self.current_theme: AppTheme = self.settings_manager.theme
        self.active_mode: DeletionMode = DeletionMode.DELETE_MATCHES

        # Multi-level undo & redo stacks
        self.undo_stack: deque[str] = deque(maxlen=MAX_UNDO_STEPS)
        self.redo_stack: deque[str] = deque(maxlen=MAX_UNDO_STEPS)

        # Source text tracking & Inline Replace Diff state
        self._raw_text: str = ""
        self._is_previewing: bool = False

        # Cached document stats (avoids splitting full text on every cursor move)
        self._cached_chars: int = 0
        self._cached_words: int = 0
        self._cached_lines: int = 0

        # Background analysis generation counter for large-file ReDoS protection
        self._analysis_gen: int = 0
        self._last_analysis: AnalysisResult = AnalysisResult()

        # Match navigation cache
        self.current_match_spans: List[Tuple[int, int]] = []
        self.current_match_index: int = -1

        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        saved_geom = self.settings_manager.window_geometry
        if saved_geom:
            x, y, w, h = saved_geom
            self.resize(max(MIN_WINDOW_WIDTH, w), max(MIN_WINDOW_HEIGHT, h))
            self.move(x, y)
        else:
            self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        self.setStyleSheet(get_stylesheet(self.current_theme))

        # Setup Debounce Timer for real-time highlighting
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(HIGHLIGHT_DEBOUNCE_MS)
        self.debounce_timer.timeout.connect(self._on_debounce_timeout)

        self._asyncAnalysisReady.connect(self._on_async_analysis_ready)

        self._init_ui()
        self._init_responsive_buttons()
        self._restore_persisted_options()
        self._populate_history()
        self._setup_shortcuts()
        self._update_theme_button_ui()
        self._apply_responsive_button_labels(self.width())

        # Initial button states
        self.copy_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.replace_btn.setEnabled(False)
        self.replace_next_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self.redo_btn.setEnabled(False)
        self.prev_match_btn.setEnabled(False)
        self.next_match_btn.setEnabled(False)
        self._update_status(AnalysisResult(), "")

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
        top_layout.setSpacing(8)

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
        self.presets_btn.setToolTip("View, insert, edit & save regex presets")
        self.presets_btn.clicked.connect(self._on_presets_clicked)
        pattern_row.addWidget(self.presets_btn)

        # Multi-Step Pipelines Button
        self.pipelines_btn = QPushButton(" Pipelines")
        self.pipelines_btn.setObjectName("utilBtn")
        self.pipelines_btn.setIcon(QIcon(str(ICON_PIPELINE)))
        self.pipelines_btn.setIconSize(QSize(16, 16))
        self.pipelines_btn.setToolTip("Run or build multi-step cleaning recipes")
        self.pipelines_btn.clicked.connect(self._on_pipelines_clicked)
        pattern_row.addWidget(self.pipelines_btn)

        # Quick Reference Button
        self.ref_btn = QPushButton(" Reference")
        self.ref_btn.setObjectName("utilBtn")
        self.ref_btn.setIcon(QIcon(str(ICON_BOOK)))
        self.ref_btn.setIconSize(QSize(16, 16))
        self.ref_btn.setToolTip("Open Regex Quick Reference cheat sheet")
        self.ref_btn.clicked.connect(self._on_reference_clicked)
        pattern_row.addWidget(self.ref_btn)

        # Theme Toggle Button
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setIconSize(QSize(20, 20))
        self.theme_btn.clicked.connect(self._toggle_theme)
        pattern_row.addWidget(self.theme_btn)

        top_layout.addLayout(pattern_row)

        # Row 2: Replace Input Field, Escapes Toggle & Replace Button
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

        self.interpret_escapes_cb = QCheckBox(r"Interpret \n/\t")
        self.interpret_escapes_cb.setToolTip(
            r"Convert \n, \t, \r, and \\ in replacement text into literal newlines/tabs (helpful in Literal Mode)"
        )
        self.interpret_escapes_cb.toggled.connect(self._on_options_changed)
        replace_row.addWidget(self.interpret_escapes_cb)

        self.replace_btn = QPushButton(" Replace Matches")
        self.replace_btn.setObjectName("replaceBtn")
        self.replace_btn.setIcon(QIcon(str(ICON_REPLACE)))
        self.replace_btn.setIconSize(QSize(16, 16))
        self.replace_btn.setMinimumHeight(32)
        self.replace_btn.setToolTip("Replace all matching text with replacement string (Ctrl+R)")
        self.replace_btn.clicked.connect(self._on_replace_clicked)
        replace_row.addWidget(self.replace_btn)

        top_layout.addLayout(replace_row)

        # Row 3: Regex Options & Flags
        options_row = QHBoxLayout()
        options_row.setSpacing(14)

        self.literal_match_cb = QCheckBox("Literal Match (No Regex)")
        self.literal_match_cb.setToolTip(
            "Match exact text literally; disables regex tokens (e.g. \\n matches backslash and n)"
        )
        self.literal_match_cb.toggled.connect(self._on_literal_toggled)
        options_row.addWidget(self.literal_match_cb)

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

        options_row.addStretch()
        top_layout.addLayout(options_row)

        # Row 3.2: Action Mode Selection (4 modes cleanly laid out)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(14)

        mode_label = QLabel("Action Mode:")
        mode_label.setStyleSheet("font-weight: 600;")
        mode_row.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)
        self.mode_delete_matches = QRadioButton("Delete Matches (Default)")
        self.mode_delete_matches.setChecked(True)
        self.mode_group.addButton(self.mode_delete_matches)
        mode_row.addWidget(self.mode_delete_matches)

        self.mode_delete_non_matches = QRadioButton("Delete Non-Matches (Keep Matches)")
        self.mode_group.addButton(self.mode_delete_non_matches)
        mode_row.addWidget(self.mode_delete_non_matches)

        self.mode_delete_matching_lines = QRadioButton("Delete Matching Lines")
        self.mode_delete_matching_lines.setToolTip("Delete every entire line containing a match (grep -v)")
        self.mode_group.addButton(self.mode_delete_matching_lines)
        mode_row.addWidget(self.mode_delete_matching_lines)

        self.mode_keep_matching_lines = QRadioButton("Keep Matching Lines")
        self.mode_keep_matching_lines.setToolTip("Keep only entire lines containing a match (grep)")
        self.mode_group.addButton(self.mode_keep_matching_lines)
        mode_row.addWidget(self.mode_keep_matching_lines)

        self.mode_group.buttonToggled.connect(self._on_mode_toggled)

        mode_row.addStretch()
        top_layout.addLayout(mode_row)

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

        extract_layout.addWidget(QLabel("Delimiter:"))

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
        self.delimiter_combo.currentIndexChanged.connect(self._on_extraction_option_changed)
        extract_layout.addWidget(self.delimiter_combo)

        self.unique_cb = QCheckBox("Unique Only (Deduplicate)")
        self.unique_cb.setToolTip("Strip redundant duplicate matches, keeping only unique occurrences")
        self.unique_cb.toggled.connect(self._on_extraction_option_changed)
        extract_layout.addWidget(self.unique_cb)

        extract_layout.addWidget(QLabel("Capture Group:"))

        self.capture_group_input = QLineEdit("0")
        self.capture_group_input.setMaximumWidth(60)
        self.capture_group_input.setToolTip("0 for full match, 1/2 for capture group, or template e.g. \\1")
        self.capture_group_input.textChanged.connect(self._on_extraction_option_changed)
        extract_layout.addWidget(self.capture_group_input)

        self.live_extract_preview_cb = QCheckBox("Live Preview")
        self.live_extract_preview_cb.setToolTip("Show live split-pane preview of extracted matches")
        self.live_extract_preview_cb.toggled.connect(self._on_extraction_preview_toggled)
        extract_layout.addWidget(self.live_extract_preview_cb)

        extract_layout.addStretch()
        top_layout.addWidget(self.extraction_panel)
        self.extraction_panel.setVisible(False)

        # Row 4: Status Indicator & Match Navigation Controls
        status_row = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label, stretch=1)

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

        self.replace_next_btn = QPushButton("Replace Next")
        self.replace_next_btn.setObjectName("navBtn")
        self.replace_next_btn.setToolTip("Replace only the currently selected/next match and jump to the following one")
        self.replace_next_btn.clicked.connect(self._on_replace_next_clicked)
        status_row.addWidget(self.replace_next_btn)

        self.match_nav_label = QLabel("")
        self.match_nav_label.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        status_row.addWidget(self.match_nav_label)

        top_layout.addLayout(status_row)
        main_layout.addWidget(top_panel)

        # ==========================================
        # CENTRAL AREA: Splitter (Main Editor + Optional Live Extraction Preview)
        # ==========================================
        self.editor_splitter = QSplitter(Qt.Horizontal)

        self.editor = DragDropEditor()
        self.editor.setObjectName("editor")
        self.editor.setPlaceholderText(
            "Paste text here, click Open..., or drag & drop a file (.txt, .log, .csv, .md, .html)..."
        )
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._update_cursor_stats)
        self.editor.fileDropped.connect(self._on_file_dropped)
        self.editor.readOnlyAttempted.connect(self._on_editor_readonly_attempted)
        self.editor.zoomChanged.connect(self._on_zoom_changed)
        self.editor_splitter.addWidget(self.editor)

        # Right-side Live Extraction Preview pane (hidden unless Live Preview toggled in Extract mode)
        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(6, 0, 0, 0)
        preview_layout.setSpacing(4)
        preview_header = QLabel("Live Extraction Preview (Read-Only)")
        preview_header.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        preview_layout.addWidget(preview_header)

        self.extraction_preview_editor = QPlainTextEdit()
        self.extraction_preview_editor.setObjectName("previewEditor")
        self.extraction_preview_editor.setReadOnly(True)
        prev_font = QFont()
        prev_font.setFamilies(MONOSPACE_FONTS)
        prev_font.setPointSize(self.editor.font().pointSize())
        self.extraction_preview_editor.setFont(prev_font)
        preview_layout.addWidget(self.extraction_preview_editor, stretch=1)

        self.preview_container.setVisible(False)
        self.editor_splitter.addWidget(self.preview_container)
        self.editor_splitter.setSizes([650, 350])

        main_layout.addWidget(self.editor_splitter, stretch=1)

        # Setup Highlighter with initial theme
        self.highlighter = MatchHighlighter(self.editor, theme=self.current_theme)

        # ==========================================
        # BOTTOM ACTION BAR
        # ==========================================
        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottomBar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(4, 2, 4, 2)
        bottom_layout.setSpacing(6)

        # Undo & Redo Buttons
        self.undo_btn = QPushButton(" Undo")
        self.undo_btn.setObjectName("utilBtn")
        self.undo_btn.setIcon(QIcon(str(ICON_UNDO)))
        self.undo_btn.setIconSize(QSize(16, 16))
        self.undo_btn.setToolTip("Undo last operation (Ctrl+Shift+Z)")
        self.undo_btn.clicked.connect(self._on_undo_clicked)
        bottom_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton(" Redo")
        self.redo_btn.setObjectName("utilBtn")
        self.redo_btn.setIcon(QIcon(str(ICON_REDO)))
        self.redo_btn.setIconSize(QSize(16, 16))
        self.redo_btn.setToolTip("Redo last undone operation (Ctrl+Shift+Y)")
        self.redo_btn.clicked.connect(self._on_redo_clicked)
        bottom_layout.addWidget(self.redo_btn)

        # Open File, Paste & Clear Buttons
        self.open_btn = QPushButton(" Open")
        self.open_btn.setObjectName("utilBtn")
        self.open_btn.setIcon(QIcon(str(ICON_OPEN)))
        self.open_btn.setIconSize(QSize(16, 16))
        self.open_btn.setToolTip("Open a text file into the editor (Ctrl+O)")
        self.open_btn.clicked.connect(self._on_open_file_clicked)
        bottom_layout.addWidget(self.open_btn)

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

        # Quick Line Utilities Dropdown Button
        self.lines_btn = QPushButton(" Lines")
        self.lines_btn.setObjectName("utilBtn")
        self.lines_btn.setIcon(QIcon(str(ICON_LINES)))
        self.lines_btn.setIconSize(QSize(16, 16))
        self.lines_btn.setToolTip("Quick 1-click line cleanup utilities (blank lines, trim, sort)")
        self.lines_menu = QMenu(self)
        self.lines_menu.addAction("Remove Blank Lines", lambda: self._on_line_utility("remove_blank"))
        self.lines_menu.addAction("Trim Leading/Trailing Whitespace", lambda: self._on_line_utility("trim"))
        self.lines_menu.addSeparator()
        self.lines_menu.addAction("Sort Lines (A → Z)", lambda: self._on_line_utility("sort_asc"))
        self.lines_menu.addAction("Sort Lines (Z → A)", lambda: self._on_line_utility("sort_desc"))
        self.lines_menu.addAction("Sort Lines (Natural Numeric)", lambda: self._on_line_utility("sort_natural"))
        self.lines_menu.addAction("Sort Lines (By Length)", lambda: self._on_line_utility("sort_length"))
        self.lines_btn.setMenu(self.lines_menu)
        self.lines_btn.setEnabled(False)
        bottom_layout.addWidget(self.lines_btn)

        # Word Wrap Checkbox
        self.wrap_cb = QCheckBox("Wrap")
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
        self.cursor_stat_label = QLabel("Ln 1, Col 1 | 0 lines | 0 chars | 0 words")
        self.cursor_stat_label.setStyleSheet("color: #64748B; font-size: 11px;")
        status_bar.addPermanentWidget(self.cursor_stat_label)

    def _restore_persisted_options(self) -> None:
        """Restores saved user preferences (zoom, wrap, flags) without triggering saves."""
        for w in (
            self.wrap_cb, self.ignore_case_cb, self.disable_multiline_cb,
            self.dot_all_cb, self.interpret_escapes_cb
        ):
            w.blockSignals(True)

        self.wrap_cb.setChecked(self.settings_manager.word_wrap)
        self._apply_word_wrap(self.settings_manager.word_wrap)
        self.ignore_case_cb.setChecked(self.settings_manager.ignore_case)
        self.disable_multiline_cb.setChecked(self.settings_manager.disable_multiline)
        self.dot_all_cb.setChecked(self.settings_manager.dot_all)
        self.interpret_escapes_cb.setChecked(self.settings_manager.interpret_escapes)

        for w in (
            self.wrap_cb, self.ignore_case_cb, self.disable_multiline_cb,
            self.dot_all_cb, self.interpret_escapes_cb
        ):
            w.blockSignals(False)

        saved_size = self.settings_manager.font_size
        self.editor.set_font_size(saved_size, emit_signal=False)
        pf = self.extraction_preview_editor.font()
        pf.setPointSize(saved_size)
        self.extraction_preview_editor.setFont(pf)

    def _setup_shortcuts(self) -> None:
        """Configures keyboard shortcuts."""
        self.delete_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.delete_shortcut.activated.connect(self._on_delete_clicked)

        self.replace_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.replace_shortcut.activated.connect(self._on_replace_clicked)

        self.open_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.open_shortcut.activated.connect(self._on_open_file_clicked)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self._on_save_as_clicked)

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.undo_shortcut.activated.connect(self._on_undo_clicked)

        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Y"), self)
        self.redo_shortcut.activated.connect(self._on_redo_clicked)

        self.copy_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        self.copy_shortcut.activated.connect(self._on_copy_shortcut)

        self.next_match_shortcut = QShortcut(QKeySequence("F3"), self)
        self.next_match_shortcut.activated.connect(lambda: self._navigate_match(1))

        self.prev_match_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        self.prev_match_shortcut.activated.connect(lambda: self._navigate_match(-1))

        self.zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        self.zoom_in_shortcut.activated.connect(self.editor.zoom_in)

        self.zoom_in_eq_shortcut = QShortcut(QKeySequence("Ctrl+="), self)
        self.zoom_in_eq_shortcut.activated.connect(self.editor.zoom_in)

        self.zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        self.zoom_out_shortcut.activated.connect(self.editor.zoom_out)

        self.zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        self.zoom_reset_shortcut.activated.connect(self.editor.reset_zoom)

        self.esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.esc_shortcut.activated.connect(self._on_escape_pressed)

    def _init_responsive_buttons(self) -> None:
        """Registers full labels for responsive icon-only collapse on narrow windows."""
        self._utility_button_labels: List[Tuple[QPushButton, str]] = [
            (self.presets_btn, " Presets"),
            (self.pipelines_btn, " Pipelines"),
            (self.ref_btn, " Reference"),
            (self.undo_btn, " Undo"),
            (self.redo_btn, " Redo"),
            (self.open_btn, " Open"),
            (self.paste_btn, " Paste"),
            (self.clear_btn, " Clear"),
            (self.lines_btn, " Lines"),
        ]
        self._delete_btn_full_text: str = " Delete Matches..."
        self._copy_btn_is_copied: bool = False
        self._primary_button_labels: List[Tuple[QPushButton, str]] = [
            (self.delete_duplicates_btn, " Delete Duplicates"),
            (self.copy_btn, " Copy Result"),
            (self.save_btn, " Save As..."),
        ]
        self._compact_utilities: Optional[bool] = None
        self._compact_primaries: Optional[bool] = None

    def _apply_responsive_button_labels(self, width: int) -> None:
        """Collapses button labels to icon-only with hover tooltips when window narrows."""
        compact_util = width < 1040
        compact_prim = width < 880

        if compact_util != self._compact_utilities:
            self._compact_utilities = compact_util
            for btn, label in self._utility_button_labels:
                btn.setText("" if compact_util else label)

        if compact_prim != self._compact_primaries:
            self._compact_primaries = compact_prim
            for btn, label in self._primary_button_labels:
                if btn is self.copy_btn and self._copy_btn_is_copied:
                    continue
                btn.setText("" if compact_prim else label)
            self.delete_btn.setText("" if compact_prim else self._delete_btn_full_text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_utility_button_labels"):
            self._apply_responsive_button_labels(self.width())

    def closeEvent(self, event) -> None:
        """Persists window geometry on close."""
        geom = self.geometry()
        self.settings_manager.window_geometry = (geom.x(), geom.y(), geom.width(), geom.height())
        super().closeEvent(event)

    def _update_theme_button_ui(self) -> None:
        if self.current_theme == AppTheme.DARK:
            self.theme_btn.setIcon(QIcon(str(ICON_SUN)))
            self.theme_btn.setToolTip("Switch to Light Mode")
        else:
            self.theme_btn.setIcon(QIcon(str(ICON_MOON)))
            self.theme_btn.setToolTip("Switch to Dark Mode")

    def _toggle_theme(self) -> None:
        """Switches between Dark and Light mode without clobbering active diff preview."""
        self.current_theme = (
            AppTheme.LIGHT if self.current_theme == AppTheme.DARK else AppTheme.DARK
        )
        self.settings_manager.theme = self.current_theme
        self.setStyleSheet(get_stylesheet(self.current_theme))
        self.highlighter.set_theme(self.current_theme)
        self._update_theme_button_ui()

    def _populate_history(self) -> None:
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

    def _on_pattern_changed(self, _text: str) -> None:
        self.debounce_timer.start()

    def _on_replace_input_changed(self, _text: str) -> None:
        self.debounce_timer.start()

    def _on_extraction_option_changed(self, *_args) -> None:
        if self.active_mode == DeletionMode.DELETE_NON_MATCHES and self.live_extract_preview_cb.isChecked():
            self._update_extraction_preview()

    def _on_extraction_preview_toggled(self, checked: bool) -> None:
        show = checked and self.active_mode == DeletionMode.DELETE_NON_MATCHES
        self.preview_container.setVisible(show)
        if show:
            self._update_extraction_preview()

    def _update_extraction_preview(self) -> None:
        if self.active_mode != DeletionMode.DELETE_NON_MATCHES or not self.live_extract_preview_cb.isChecked():
            return
        pattern = self.pattern_combo.currentText()
        raw_text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not pattern or not raw_text:
            self.extraction_preview_editor.setPlainText("")
            return
        extracted, _ = RegexEngine.strip_non_matches(
            raw_text,
            pattern,
            self._get_current_flags(),
            separator=self._get_selected_delimiter(),
            is_literal=self.literal_match_cb.isChecked(),
            unique=self.unique_cb.isChecked(),
            capture_group=self.capture_group_input.text().strip() or "0",
        )
        self.extraction_preview_editor.setPlainText(extracted)

    def _on_escape_pressed(self) -> None:
        if self.replace_input.text():
            self.replace_input.clear()

    def _on_editor_readonly_attempted(self) -> None:
        if self._is_previewing:
            self.status_label.setText(
                "💡 In Replace Preview mode. Press Esc or clear 'Replace With' to edit original text."
            )
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")

    def _on_options_changed(self) -> None:
        """Persists flag toggles, updates Delete Duplicates button, and schedules re-highlight."""
        self.settings_manager.ignore_case = self.ignore_case_cb.isChecked()
        self.settings_manager.disable_multiline = self.disable_multiline_cb.isChecked()
        self.settings_manager.dot_all = self.dot_all_cb.isChecked()
        self.settings_manager.interpret_escapes = self.interpret_escapes_cb.isChecked()
        self._update_line_action_buttons_state()
        self.debounce_timer.start()

    def _on_mode_toggled(self, _button, checked: bool) -> None:
        if not checked:
            return
        if self.mode_delete_matches.isChecked():
            self.active_mode = DeletionMode.DELETE_MATCHES
            self._delete_btn_full_text = " Delete Matches..."
            self.delete_btn.setToolTip("Delete matching text (Ctrl+Enter)")
            self.extraction_panel.setVisible(False)
            self.preview_container.setVisible(False)
        elif self.mode_delete_non_matches.isChecked():
            self.active_mode = DeletionMode.DELETE_NON_MATCHES
            self._delete_btn_full_text = " Delete Non-Matches..."
            self.delete_btn.setToolTip("Delete non-matching text and keep matches (Ctrl+Enter)")
            self.extraction_panel.setVisible(True)
            self.preview_container.setVisible(self.live_extract_preview_cb.isChecked())
        elif self.mode_delete_matching_lines.isChecked():
            self.active_mode = DeletionMode.DELETE_MATCHING_LINES
            self._delete_btn_full_text = " Delete Matching Lines..."
            self.delete_btn.setToolTip("Delete every line containing a match (Ctrl+Enter)")
            self.extraction_panel.setVisible(False)
            self.preview_container.setVisible(False)
        else:
            self.active_mode = DeletionMode.KEEP_MATCHING_LINES
            self._delete_btn_full_text = " Keep Matching Lines..."
            self.delete_btn.setToolTip("Keep only lines containing a match (Ctrl+Enter)")
            self.extraction_panel.setVisible(False)
            self.preview_container.setVisible(False)

        self.delete_btn.setText("" if self._compact_primaries else self._delete_btn_full_text)
        self.highlighter.set_mode(self.active_mode)
        self._apply_highlights()

    def _refresh_cached_doc_stats(self, text: str) -> None:
        self._cached_chars = len(text)
        self._cached_words = len(text.split()) if text else 0
        self._cached_lines = len(text.splitlines()) if text else 0

    def _on_text_changed(self) -> None:
        if not self._is_previewing:
            self._raw_text = self.editor.toPlainText()
            self._refresh_cached_doc_stats(self._raw_text)
        if not self._raw_text.strip():
            self.copy_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
        self._update_line_action_buttons_state()
        self._update_cursor_stats()
        self.debounce_timer.start()

    def _apply_word_wrap(self, checked: bool) -> None:
        mode = DragDropEditor.LineWrapMode.WidgetWidth if checked else DragDropEditor.LineWrapMode.NoWrap
        self.editor.setLineWrapMode(mode)
        self.extraction_preview_editor.setLineWrapMode(mode)

    def _on_wrap_toggled(self, checked: bool) -> None:
        self._apply_word_wrap(checked)
        self.settings_manager.word_wrap = checked

    def _on_zoom_changed(self, point_size: int) -> None:
        self.settings_manager.font_size = point_size
        pf = self.extraction_preview_editor.font()
        pf.setPointSize(point_size)
        self.extraction_preview_editor.setFont(pf)
        self.extraction_preview_editor.setStyleSheet(f"font-size: {point_size}pt;")

    def _load_file_into_editor(self, path: str, content: str, eol: Optional[str] = None) -> None:
        """Shared single-pass loader for Drag & Drop and Open File..."""
        current = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if current:
            self._push_undo_state()
        if eol is not None:
            self.editor.preferred_eol = eol
        self._raw_text = content
        if self._is_previewing:
            self._is_previewing = False
            self.editor.setReadOnly(False)
        self.editor.setPlainText(content)
        self._apply_highlights()
        self.status_label.setText(f"✓ Loaded {Path(path).name} ({len(content):,} chars)")
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")

    def _on_file_dropped(self, path: str, content: str) -> None:
        self._load_file_into_editor(path, content)

    def _on_open_file_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Text File",
            "",
            "Text Files (*.txt *.log *.csv *.md *.html *.xml *.json *.srt);;All Files (*.*)"
        )
        if not file_path:
            return
        try:
            content, eol = DragDropEditor.read_file_normalized(file_path)
            self._load_file_into_editor(file_path, content, eol=eol)
        except Exception as e:
            self.status_label.setText(f"⚠️ Open Error: {e}")
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_ERROR}; font-weight: bold;")

    def _update_cursor_stats(self) -> None:
        """O(1) cursor position update using cached document statistics."""
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.cursor_stat_label.setText(
            f"Ln {line}, Col {col} | {self._cached_lines:,} lines | "
            f"{self._cached_chars:,} chars | {self._cached_words:,} words"
        )

    def _on_debounce_timeout(self) -> None:
        """Runs async worker for very large documents, or fast synchronous single-pass analysis."""
        raw_text = self.editor.toPlainText()
        pattern = self.pattern_combo.currentText()
        if len(raw_text) > _ASYNC_ANALYSIS_THRESHOLD and pattern:
            self._start_async_analysis(raw_text, pattern)
        else:
            self._apply_highlights()

    def _start_async_analysis(self, raw_text: str, pattern: str) -> None:
        self._analysis_gen += 1
        gen = self._analysis_gen
        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        mode = self.active_mode

        def worker() -> None:
            res = RegexEngine.analyze(raw_text, pattern, flags, is_literal=is_literal, mode=mode)
            self._asyncAnalysisReady.emit(gen, res, raw_text)

        threading.Thread(target=worker, daemon=True).start()

    def _on_async_analysis_ready(self, gen: int, analysis: AnalysisResult, raw_text: str) -> None:
        if gen != self._analysis_gen:
            return
        self._apply_highlights(precomputed=analysis, precomputed_raw=raw_text)

    def _compute_impact_summary(self, raw_text: str, analysis: AnalysisResult) -> str:
        """Estimates compact character / line delta for status display and confirmation dialog."""
        if not raw_text or not analysis.is_valid:
            return ""
        if self.active_mode == DeletionMode.DELETE_MATCHES:
            removed_chars = sum(e - s for s, e in analysis.target_spans)
            return f"-{removed_chars:,} chars" if removed_chars > 0 else ""
        if self.active_mode == DeletionMode.DELETE_NON_MATCHES:
            removed_chars = sum(e - s for s, e in analysis.target_spans)
            return f"-{removed_chars:,} chars" if removed_chars > 0 else ""
        if self.active_mode == DeletionMode.DELETE_MATCHING_LINES:
            n = analysis.matching_line_count
            return f"-{n:,} line(s)" if n > 0 else ""
        if self.active_mode == DeletionMode.KEEP_MATCHING_LINES:
            removed = max(0, analysis.total_line_count - analysis.matching_line_count)
            return f"-{removed:,} line(s)" if removed > 0 else ""
        return ""

    def _apply_highlights(
        self,
        precomputed: Optional[AnalysisResult] = None,
        precomputed_raw: Optional[str] = None,
    ) -> None:
        """Single-pass highlight update, inline replace preview, extraction preview, and status refresh."""
        pattern = self.pattern_combo.currentText()
        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        replacement = self.replace_input.text()
        interpret_escapes = self.interpret_escapes_cb.isChecked()

        raw_text = precomputed_raw if precomputed_raw is not None else self.editor.toPlainText()
        self._raw_text = raw_text
        self._refresh_cached_doc_stats(raw_text)

        if precomputed is not None:
            analysis = precomputed
        else:
            analysis = RegexEngine.analyze(
                raw_text, pattern, flags, is_literal=is_literal, mode=self.active_mode
            )
        self._last_analysis = analysis

        should_preview = (
            bool(replacement)
            and analysis.is_valid
            and analysis.match_count > 0
            and bool(raw_text)
            and self.active_mode == DeletionMode.DELETE_MATCHES
        )

        if should_preview:
            preview_text, green_spans, red_spans = RegexEngine.generate_diff_preview(
                raw_text, pattern, replacement, flags,
                is_literal=is_literal, interpret_escapes=interpret_escapes
            )
            self._is_previewing = True
            self.editor.set_diff_preview(preview_text, raw_text)
            self.highlighter.apply_diff_highlights(green_spans, red_spans)
            # Navigate originals (red_spans) in document order, or green_spans for zero-width anchors
            self.current_match_spans = red_spans if red_spans else green_spans
        else:
            if self._is_previewing:
                self._is_previewing = False
                self.editor.clear_diff_preview(raw_text)

            if analysis.is_valid and pattern and raw_text:
                self.highlighter.apply_spans(analysis.target_spans, self.active_mode)
                self.current_match_spans = analysis.match_spans
            else:
                self.highlighter.clear_highlights()
                self.current_match_spans = []

        self.current_match_index = -1
        self._update_navigation_controls()
        self._update_line_action_buttons_state()
        self._update_cursor_stats()
        impact = self._compute_impact_summary(raw_text, analysis)
        self._update_status(analysis, impact)

        if self.active_mode == DeletionMode.DELETE_NON_MATCHES and self.live_extract_preview_cb.isChecked():
            self._update_extraction_preview()

    def _update_navigation_controls(self) -> None:
        count = len(self.current_match_spans)
        has_matches = count > 0
        self.prev_match_btn.setEnabled(has_matches)
        self.next_match_btn.setEnabled(has_matches)
        can_replace_next = (
            has_matches
            and self.active_mode == DeletionMode.DELETE_MATCHES
            and bool(self.pattern_combo.currentText())
        )
        self.replace_next_btn.setEnabled(can_replace_next)

        if has_matches:
            if self.current_match_index >= 0:
                self.match_nav_label.setText(f"[{self.current_match_index + 1}/{count}]")
            else:
                self.match_nav_label.setText(f"[{count} match(es)]")
        else:
            self.match_nav_label.setText("")

    def _navigate_match(self, direction: int) -> None:
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

    def _update_status(self, analysis: AnalysisResult, impact_summary: str) -> None:
        pattern = self.pattern_combo.currentText()
        raw_text = self._raw_text if self._is_previewing else self.editor.toPlainText()

        if not pattern:
            self.status_label.setText("● Ready (Enter a pattern to preview targets)")
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_NO_MATCH};")
            self.delete_btn.setEnabled(False)
            self.replace_btn.setEnabled(False)
            return

        if not analysis.is_valid:
            self.status_label.setText(f"⚠️ Invalid Pattern: {analysis.error_message}")
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
        match_count = analysis.match_count
        impact_suffix = f" [{impact_summary}]" if impact_summary else ""

        if self._is_previewing:
            self.status_label.setText(
                f"● {match_count} {mode_name.lower()} match(es) targeted | "
                f"Replace Preview: [green bold] = replacement, [red strikeout] = original"
            )
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
            self.delete_btn.setEnabled(True)
            self.replace_btn.setEnabled(True)
            return

        if self.active_mode == DeletionMode.DELETE_MATCHES:
            target_desc = f"highlighting {mode_name.lower()} matches to delete"
        elif self.active_mode == DeletionMode.DELETE_NON_MATCHES:
            target_desc = "highlighting non-matching text to delete"
        elif self.active_mode == DeletionMode.DELETE_MATCHING_LINES:
            target_desc = f"{analysis.matching_line_count} line(s) targeted for deletion"
        else:
            target_desc = f"keeping {analysis.matching_line_count} matching line(s)"

        if match_count > 0:
            self.status_label.setText(
                f"● {match_count} {mode_name.lower()} match(es) found ({target_desc}){impact_suffix}"
            )
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
            self.delete_btn.setEnabled(True)
            self.replace_btn.setEnabled(True)
        else:
            self.replace_btn.setEnabled(False)
            if self.active_mode in (DeletionMode.DELETE_NON_MATCHES, DeletionMode.KEEP_MATCHING_LINES):
                self.status_label.setText("○ 0 matches found (Warning: all text is targeted for deletion)")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_ERROR}; font-weight: bold;")
                self.delete_btn.setEnabled(True)
            else:
                self.status_label.setText("○ No matches found")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_NO_MATCH};")
                self.delete_btn.setEnabled(False)

    def _push_undo_state(self) -> None:
        current = self._raw_text if self._is_previewing else self.editor.toPlainText()
        self.undo_stack.append(current)
        self.redo_stack.clear()
        self.undo_btn.setEnabled(True)
        self.redo_btn.setEnabled(False)

    def _apply_new_text(self, new_text: str, status_msg: str, enable_outputs: bool = True) -> None:
        """Applies mutated text, refreshes highlights, and preserves the action status message."""
        self._raw_text = new_text
        if self._is_previewing:
            self._is_previewing = False
            self.editor.setReadOnly(False)
        self.editor.setPlainText(new_text)
        if enable_outputs:
            self.copy_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
        self._apply_highlights()
        self.status_label.setText(status_msg)
        self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")

    def _on_undo_clicked(self) -> None:
        if not self.undo_stack:
            return
        current = self._raw_text if self._is_previewing else self.editor.toPlainText()
        self.redo_stack.append(current)
        prev_text = self.undo_stack.pop()
        self.undo_btn.setEnabled(len(self.undo_stack) > 0)
        self.redo_btn.setEnabled(True)
        self._apply_new_text(prev_text, "✓ Undid last operation.", enable_outputs=False)

    def _on_redo_clicked(self) -> None:
        if not self.redo_stack:
            return
        current = self._raw_text if self._is_previewing else self.editor.toPlainText()
        self.undo_stack.append(current)
        next_text = self.redo_stack.pop()
        self.undo_btn.setEnabled(True)
        self.redo_btn.setEnabled(len(self.redo_stack) > 0)
        self._apply_new_text(next_text, "✓ Redid operation.", enable_outputs=False)

    def _on_replace_clicked(self) -> None:
        pattern = self.pattern_combo.currentText()
        if not pattern:
            return

        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not text:
            return

        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        interpret_escapes = self.interpret_escapes_cb.isChecked()
        is_valid, _, _ = RegexEngine.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid:
            return

        replacement = self.replace_input.text()
        new_text, count = RegexEngine.replace_matches(
            text, pattern, replacement, flags,
            is_literal=is_literal, interpret_escapes=interpret_escapes
        )

        if count > 0:
            self._push_undo_state()
            self.history_manager.add_pattern(pattern)
            self._populate_history()
            self.pattern_combo.setEditText(pattern)
            self._apply_new_text(new_text, f"✓ Replaced {count} match(es).")

    def _on_replace_next_clicked(self) -> None:
        """Step-through replacement: replaces only the currently active (or first) match."""
        pattern = self.pattern_combo.currentText()
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not pattern or not text:
            return

        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        interpret_escapes = self.interpret_escapes_cb.isChecked()
        raw_spans = RegexEngine.find_match_spans(text, pattern, flags, is_literal=is_literal)
        if not raw_spans:
            return

        idx = self.current_match_index if 0 <= self.current_match_index < len(raw_spans) else 0
        target_span = raw_spans[idx]

        new_text, next_offset, did_replace = RegexEngine.replace_single_match(
            text, target_span, pattern, self.replace_input.text(),
            flags=flags, is_literal=is_literal, interpret_escapes=interpret_escapes
        )
        if not did_replace:
            return

        self._push_undo_state()
        self._apply_new_text(new_text, "✓ Replaced 1 match.")

        # Jump cursor to the next remaining match if available
        if self.current_match_spans:
            next_idx = min(idx, len(self.current_match_spans) - 1)
            self.current_match_index = next_idx - 1
            self._navigate_match(1)

    def _update_line_action_buttons_state(self) -> None:
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        has_text = bool(text)
        can_dedup = (not self.disable_multiline_cb.isChecked()) and has_text
        self.delete_duplicates_btn.setEnabled(can_dedup)
        self.lines_btn.setEnabled(has_text)

    def _on_line_utility(self, op: str) -> None:
        """Executes 1-click line cleanup utilities (blank lines, trim, sort) with Undo support."""
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not text:
            return

        ignore_case = self.ignore_case_cb.isChecked()
        if op == "remove_blank":
            new_text, count = RegexEngine.remove_blank_lines(text)
            msg = f"✓ Removed {count} blank line(s)." if count > 0 else "○ No blank lines found."
        elif op == "trim":
            new_text, count = RegexEngine.trim_lines(text)
            msg = f"✓ Trimmed whitespace on {count} line(s)." if count > 0 else "○ No leading/trailing whitespace found."
        elif op == "sort_asc":
            new_text, count = RegexEngine.sort_lines(text, mode="asc", ignore_case=ignore_case)
            msg = f"✓ Sorted {count} line(s) (A → Z)."
        elif op == "sort_desc":
            new_text, count = RegexEngine.sort_lines(text, mode="desc", ignore_case=ignore_case)
            msg = f"✓ Sorted {count} line(s) (Z → A)."
        elif op == "sort_natural":
            new_text, count = RegexEngine.sort_lines(text, mode="natural", ignore_case=ignore_case)
            msg = f"✓ Sorted {count} line(s) (Natural)."
        elif op == "sort_length":
            new_text, count = RegexEngine.sort_lines(text, mode="length", ignore_case=ignore_case)
            msg = f"✓ Sorted {count} line(s) (By length)."
        else:
            return

        if new_text != text:
            self._push_undo_state()
            self._apply_new_text(new_text, msg)
        else:
            self.status_label.setText(msg)
            self.status_label.setStyleSheet(f"color: {COLOR_STATUS_NO_MATCH};")

    def _on_delete_duplicates_clicked(self) -> None:
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

        self._push_undo_state()
        self._apply_new_text(deduped_text, f"✓ Deleted {dup_count} duplicate line(s).")

    def _on_delete_clicked(self) -> None:
        pattern = self.pattern_combo.currentText()
        if not pattern:
            return

        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        if not text:
            return

        flags = self._get_current_flags()
        is_literal = self.literal_match_cb.isChecked()
        analysis = RegexEngine.analyze(text, pattern, flags, is_literal=is_literal, mode=self.active_mode)
        if not analysis.is_valid:
            return

        dialog_count = (
            analysis.matching_line_count
            if self.active_mode in (DeletionMode.DELETE_MATCHING_LINES, DeletionMode.KEEP_MATCHING_LINES)
            else analysis.match_count
        )
        impact = self._compute_impact_summary(text, analysis)

        confirmed = DeleteConfirmationDialog.confirm(
            self,
            self.active_mode,
            dialog_count,
            pattern,
            impact_summary=impact,
        )
        if not confirmed:
            return

        self._push_undo_state()

        if self.active_mode == DeletionMode.DELETE_MATCHES:
            new_text, count = RegexEngine.strip_matches(text, pattern, flags, is_literal=is_literal)
            status_msg = f"✓ Deleted {count} match(es)."
        elif self.active_mode == DeletionMode.DELETE_NON_MATCHES:
            new_text, count = RegexEngine.strip_non_matches(
                text,
                pattern,
                flags,
                separator=self._get_selected_delimiter(),
                is_literal=is_literal,
                unique=self.unique_cb.isChecked(),
                capture_group=self.capture_group_input.text().strip() or "0",
            )
            status_msg = f"✓ Extracted {count} match(es) (non-matches removed)."
        elif self.active_mode == DeletionMode.DELETE_MATCHING_LINES:
            new_text, count = RegexEngine.strip_matching_lines(text, pattern, flags, is_literal=is_literal)
            status_msg = f"✓ Deleted {count} matching line(s)."
        else:
            new_text, count = RegexEngine.keep_matching_lines(text, pattern, flags, is_literal=is_literal)
            status_msg = f"✓ Kept {count} matching line(s)."

        self.history_manager.add_pattern(pattern)
        self._populate_history()
        self.pattern_combo.setEditText(pattern)
        self._apply_new_text(new_text, status_msg)

    def _on_copy_clicked(self) -> None:
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        QApplication.clipboard().setText(text)
        self._copy_btn_is_copied = True
        self.copy_btn.setText(" ✓" if self._compact_primaries else " Copied!")

        def _restore_copy_label() -> None:
            self._copy_btn_is_copied = False
            self.copy_btn.setText("" if self._compact_primaries else " Copy Result")

        QTimer.singleShot(1500, _restore_copy_label)

    def _on_copy_shortcut(self) -> None:
        if self.copy_btn.isEnabled():
            self._on_copy_clicked()

    def _on_save_as_clicked(self) -> None:
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
                out_text = text
                if self.editor.preferred_eol == "\r\n" and "\r\n" not in out_text:
                    out_text = out_text.replace("\n", "\r\n")
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    f.write(out_text)
                self.status_label.setText(f"✓ Saved to {Path(file_path).name}")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_MATCH}; font-weight: bold;")
            except Exception as e:
                self.status_label.setText(f"⚠️ Save Error: {e}")
                self.status_label.setStyleSheet(f"color: {COLOR_STATUS_ERROR}; font-weight: bold;")

    def _on_paste_clicked(self) -> None:
        text = QApplication.clipboard().text()
        if text:
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            self._push_undo_state()
            self._apply_new_text(normalized, "✓ Pasted clipboard text.", enable_outputs=False)

    def _on_clear_clicked(self) -> None:
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
            self._update_line_action_buttons_state()
            self._apply_highlights()

    def _on_reference_clicked(self) -> None:
        dialog = RegexReferenceDialog(self)
        dialog.exec()

    def _on_presets_clicked(self) -> None:
        current_state = {
            "expression": self.pattern_combo.currentText(),
            "replacement": self.replace_input.text(),
            "mode": self.active_mode.value,
            "is_literal": self.literal_match_cb.isChecked(),
            "ignore_case": self.ignore_case_cb.isChecked(),
            "disable_multiline": self.disable_multiline_cb.isChecked(),
            "dot_all": self.dot_all_cb.isChecked(),
        }
        preset = PresetsDialog.select_preset_full(
            self,
            current_pattern=current_state["expression"],
            preset_manager=self.preset_manager,
            current_state=current_state,
        )
        if not preset:
            return

        # Apply preset options cleanly
        if "is_literal" in preset:
            self.literal_match_cb.setChecked(bool(preset["is_literal"]))
        elif self.literal_match_cb.isChecked():
            self.literal_match_cb.setChecked(False)

        if "ignore_case" in preset:
            self.ignore_case_cb.setChecked(bool(preset["ignore_case"]))
        if "disable_multiline" in preset:
            self.disable_multiline_cb.setChecked(bool(preset["disable_multiline"]))
        if "dot_all" in preset:
            self.dot_all_cb.setChecked(bool(preset["dot_all"]))

        mode_val = preset.get("mode")
        if mode_val == DeletionMode.DELETE_MATCHES.value:
            self.mode_delete_matches.setChecked(True)
        elif mode_val == DeletionMode.DELETE_NON_MATCHES.value:
            self.mode_delete_non_matches.setChecked(True)
        elif mode_val == DeletionMode.DELETE_MATCHING_LINES.value:
            self.mode_delete_matching_lines.setChecked(True)
        elif mode_val == DeletionMode.KEEP_MATCHING_LINES.value:
            self.mode_keep_matching_lines.setChecked(True)

        if "replacement" in preset:
            self.replace_input.setText(str(preset["replacement"]))

        self.pattern_combo.setEditText(str(preset["expression"]))
        self._apply_highlights()

    def _on_pipelines_clicked(self) -> None:
        text = self._raw_text if self._is_previewing else self.editor.toPlainText()
        current_step: Dict[str, Any] = {
            "action": "replace_matches" if self.replace_input.text() else self.active_mode.value,
            "pattern": self.pattern_combo.currentText(),
            "replacement": self.replace_input.text(),
            "ignore_case": self.ignore_case_cb.isChecked(),
            "disable_multiline": self.disable_multiline_cb.isChecked(),
            "dot_all": self.dot_all_cb.isChecked(),
            "is_literal": self.literal_match_cb.isChecked(),
            "interpret_escapes": self.interpret_escapes_cb.isChecked(),
        }
        chosen = PipelineDialog.choose_pipeline(
            self,
            pipeline_manager=self.pipeline_manager,
            current_step_template=current_step,
        )
        if not chosen or not text:
            return

        new_text, summaries = PipelineManager.run_pipeline(text, chosen["steps"])
        self._push_undo_state()
        summary_str = " → ".join(summaries)
        self._apply_new_text(new_text, f"✓ Pipeline '{chosen['name']}' complete ({summary_str})")
