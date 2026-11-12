# Implementation Plan: Regex Stripper (RegexStripper)

## 1. Project Overview & Objectives

**Regex Stripper** is a fast, responsive desktop utility designed for rapid text processing and regex-based content cleaning. It allows users to paste text blocks, define regular expressions with real-time visual syntax and match highlighting, delete either matching or non-matching text, and instantly copy the cleansed output to the clipboard.

### Core Goals
- **Dual Deletion Modes (Bidirectional)**:
  - **Default Mode (Delete Matches)**: Strips all regex matches and retains the surrounding text.
  - **Inverted Mode (Delete Non-Matches / Keep Matches)**: Strips all text that does *not* match the regex, leaving only the matched content.
- **Dynamic Real-Time Highlighting**: Highlighting updates in real-time and dynamically adapts to the selected mode—highlighting the exact text spans targeted for deletion so the user has 100% visual confidence before acting.
- **Safety Confirmation Dialog**: Clicking the delete button opens a confirmation popup detailing the action (mode, match count, character impact) before mutating text.
- **Streamlined Workflow & Button Lifecycle**: The Copy button activates strictly after a confirmed delete operation is performed, resetting if the text is cleared or reset.
- **Persistent Pattern History**: Remembers recently used expressions across restarts, registering patterns into history **only** upon a confirmed delete operation.
- **Clean Modern Desktop Experience**: Distraction-free PySide6 interface with monospace typography, responsive debounce, and keyboard shortcuts.

---

## 2. Technical Stack & Architecture

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ / 3.14 | Robust standard library, native regex module, cross-platform. |
| **GUI Framework** | **PySide6** (Qt for Python) | High performance, native look & feel, robust `QSyntaxHighlighter`, `QPlainTextEdit`, and `QMessageBox`. |
| **Regex Engine** | Standard `re` module | Full standard regex support (groups, lookarounds, flags). |
| **State & Persistence** | JSON (`.regexstripper_history.json`) | Lightweight, portable, no external database dependencies. |
| **Testing** | `pytest`, `pytest-qt` | Headless, reliable automated testing for UI state transitions, dialogs, and matching logic. |

---

## 3. UI/UX Layout & Component Specification

```
+-------------------------------------------------------------------------------+
|  Regex Stripper                                                    [_] [O] [X]|
+-------------------------------------------------------------------------------+
| Pattern: [ v \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b ] [x]       |
| Options: [x] Case Insensitive (i)  [ ] Dot Matches All (s)                   |
| Mode:    (●) Delete Matches (Default)   ( ) Delete Non-Matches (Keep Matches) |
| Status:  ● 14 matches found (highlighting target deletion text)               |
+-------------------------------------------------------------------------------+
|                                                                               |
|  Lorem ipsum dolor sit amet, john.doe@example.com consetetur sadipscing      |
|  elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna...   |
|  Contact support at admin@domain.org for inquiries.                           |
|                                                                               |
|  [ Large Monospace QPlainTextEdit with live deletion-target highlights ]      |
|                                                                               |
+-------------------------------------------------------------------------------+
|  [ Clear Text ]   [ Paste Clipboard ]          [ 🗑️ Delete Matches... ] [ 📋 Copy Result ] |
|                                                (Primary Action Button)  (Active post-delete)
+-------------------------------------------------------------------------------+
```

### 3.1. Top Control Bar (Regex, Flags & Mode Toggle)
- **Regex ComboBox (`QComboBox`)**:
  - Editable input with clear icon button.
  - Dropdown containing recently executed expressions.
  - Placeholder: `Enter regex pattern (e.g. \d{4}-\d{2}-\d{2})...`.
  - Clean monospace typography.
- **Regex Options / Flags**:
  - `Ignore Case` (`re.I`): Case-insensitive toggle.
  - `Dot All` (`re.S`): Dot matches newline toggle.
- **Mode Toggle (`QRadioButton` Group or Segmented Switch)**:
  - **Mode A (Default)**: `Delete Matches` — Strips matching strings, preserves surrounding text.
  - **Mode B (Inverted)**: `Delete Non-Matches` (Keep Matches) — Strips all non-matching text, preserving only matched segments.
  - *Toggling immediately re-renders the text highlights to preview the new deletion target spans!*
- **Match Status & Error Display**:
  - Real-time indicator label:
    - Normal matches: `● 14 matches found (Mode: Delete Matches)` or `● 14 matches found (Mode: Keep Matches)`.
    - No matches: `○ No matches found`.
    - Invalid regex: `⚠️ Invalid pattern: <error summary>` (soft red highlight, no crashes).

### 3.2. Central Text Canvas & Dynamic Highlighting
- **Text Box (`QPlainTextEdit`)**:
  - High-performance multi-line text editor with monospace font (`Cascadia Code`, `Consolas`, or system monospace).
  - Placeholder: `Paste or type text to inspect and process...`.
  - Full Undo/Redo support (`Ctrl+Z`, `Ctrl+Y`).
- **Dynamic Mode-Aware Match Highlighter (`QSyntaxHighlighter`)**:
  - **In Delete Matches Mode**:
    - Highlights every regex match span `[m.start(), m.end()]` with target-deletion styling (e.g. warm amber/salmon highlight).
  - **In Delete Non-Matches Mode**:
    - Inverts highlighting: calculates non-matching intervals `[0, m1.start()]`, `[m1.end(), m2.start()]`, ..., `[mN.end(), len(text)]` and highlights them as target deletion spans.
  - **Debounce Timer**: 100ms debounce prevents UI freezing when editing large texts or typing complex regexes.

### 3.3. Delete Confirmation Dialog
When the user clicks the Delete button (or presses `Ctrl+Enter`):
- A confirmation dialog (`QMessageBox` / custom styled modal) is displayed:
  - **Title**: `Confirm Deletion`
  - **Message Details**:
    - Mode: *Delete Matches* → `"Are you sure you want to delete all 14 matching segments from the text?"`
    - Mode: *Delete Non-Matches* → `"Are you sure you want to delete all non-matching text and keep only the 14 matched segments?"`
    - Shows match count and preview snippet if helpful.
  - **Actions**:
    - **`Delete`** (Primary / Destructive styling) → Executes deletion, adds pattern to history, enables Copy button.
    - **`Cancel`** (Default focus) → Dismisses dialog with **zero** changes to text, history, or Copy button.

### 3.4. Action Bar & State Controls
- **Delete Button (`QPushButton`)**:
  - Label dynamically reflects active mode:
    - Mode A: `🗑️ Delete Matches...`
    - Mode B: `🗑️ Delete Non-Matches...` (or `Keep Matches Only...`)
  - Triggers the Confirmation Dialog before performing any action.
  - Disabled if text box is empty or regex has 0 matches.
- **Copy Result Button (`QPushButton`)**:
  - Initial state: **Disabled** (`setEnabled(False)`).
  - Enabled state: **Activated strictly after a confirmed deletion has occurred**.
  - Action: Copies entire current text buffer to clipboard (`QGuiApplication.clipboard()`).
  - Visual feedback: Briefly changes text to `"✓ Copied!"` or displays a status toast.
  - Reset condition: Automatically disabled if the user clears the editor or resets text.
- **Utility Buttons**:
  - **Clear Text**: Clears editor content (with Undo support).
  - **Paste Clipboard**: Pastes clipboard contents directly into the editor.

---

## 4. History Management Specifications

1. **Strict Registration Rule**:
   - A pattern is **only registered** in history when the user clicks Delete **and confirms the deletion** in the popup dialog.
   - If the user cancels the confirmation dialog, or only types/previews without deleting, the pattern is **not** registered.
2. **Deduplication & LRU Ordering**:
   - Re-using an existing pattern moves it to index `0` (top of list).
   - Maximum capacity: 25 items.
3. **Persistence**:
   - Stored in a lightweight JSON file (`.regexstripper_history.json`).
   - Saved immediately upon confirmed deletion and restored on application startup.

---

## 5. File Structure

```
regexstripper/
├── .gitignore                      # Git ignore rules (.venv, __pycache__, history caches)
├── requirements.txt                # PySide6 and test dependencies
├── implementation_plan.md          # Architecture, specifications, and progress
├── run.py                          # Application entry point
├── src/
│   ├── __init__.py
│   ├── app.py                      # Application bootstrap & theme setup
│   ├── config.py                   # Constants, limits, colors, storage paths
│   ├── core/
│   │   ├── __init__.py
│   │   ├── regex_engine.py         # Regex compilation, validation, span extraction & stripping (both modes)
│   │   └── history_manager.py      # Recent patterns storage, LRU logic, JSON file I/O
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py          # Main UI assembly, signal-slot wiring & mode toggles
│       ├── highlighter.py          # Mode-aware QSyntaxHighlighter (direct & inverted spans)
│       ├── confirmation_dialog.py  # Modal confirmation popup for delete operations
│       └── styles.py               # Modern QSS styling, typography & color palette
└── tests/
    ├── __init__.py
    ├── test_engine.py              # Unit tests for RegexEngine (strip matches, strip non-matches, invert spans)
    ├── test_history.py             # Unit tests for HistoryManager (persistence, LRU, dedup)
    └── test_ui.py                  # Integration tests for UI, mode toggling, dialog confirmation/cancel, Copy button lifecycle
```

---

## 6. Implementation Phases & Action Items

### Phase 1: Environment & Project Foundation (COMPLETED)
- [x] Initialize Python environment and `requirements.txt` (`PySide6>=6.5.0`, `pytest>=7.0.0`, `pytest-qt>=4.0.0`).
- [x] Set up directory structure (`src/core/`, `src/ui/`, `tests/`).
- [x] Implement `src/config.py` with UI constants, deletion mode enum (`DELETE_MATCHES`, `DELETE_NON_MATCHES`), highlight colors, and paths.

### Phase 2: Core Engine & Inverted Logic (COMPLETED)
- [x] Implement `src/core/regex_engine.py`:
  - Regex compilation & validation (`re.IGNORECASE`, `re.DOTALL`).
  - `find_match_spans(text, pattern, flags)`: returns list of `(start, end)` tuples.
  - `find_inverted_spans(text, pattern, flags)`: returns complementary non-matching intervals `[0, s1]`, `[e1, s2]`, ..., `[eN, len(text)]`.
  - `strip_matches(text, pattern, flags)`: removes matching text.
  - `strip_non_matches(text, pattern, flags, separator="\n")`: extracts and keeps only matched text.
- [x] Implement `src/core/history_manager.py`:
  - Persistent JSON load/save.
  - Deduping, LRU cap (30 items).
- [x] Unit tests in `tests/test_engine.py` and `tests/test_history.py` (19 passing tests).

### Phase 3: Mode-Aware Highlighting & UI Construction (COMPLETED)
- [x] Implement `src/ui/highlighter.py`:
  - Mode-aware match selection manager supporting both `DELETE_MATCHES` and `DELETE_NON_MATCHES` modes.
  - Highlights exact text ranges targeted for deletion based on active mode.
- [x] Implement `src/ui/confirmation_dialog.py`:
  - Clean popup summarizing deletion type, match count, and warning.
  - Returns `True` (Confirmed) or `False` (Cancelled).
- [x] Implement `src/ui/main_window.py`:
  - Top bar with regex combo box, options checkboxes, and Mode toggle (`Delete Matches` vs `Delete Non-Matches`).
  - Central `QPlainTextEdit` with monospace styling.
  - Bottom bar with Delete button (dynamic label), Copy button (initially disabled), Clear, and Paste.
  - Mode toggle signal triggers instant highlight update and button label change.

### Phase 4: State Machine & Workflow Integration (COMPLETED)
- [x] Wire Delete action:
  - Validates pattern and match presence.
  - Triggers `ConfirmationDialog`.
  - If **Confirmed**:
    - Executes deletion (matching or non-matching according to mode).
    - Commits pattern to `HistoryManager` and updates combo box.
    - Enables **Copy Result** button.
    - Shows feedback in status bar.
  - If **Cancelled**:
    - Aborts cleanly without touching text, history, or Copy button state.
- [x] Wire Copy action:
  - Copies text buffer to clipboard.
  - Shows temporary `"✓ Copied!"` visual indicator.
- [x] Wire reset conditions:
  - If editor text is cleared or reset, disable Copy button.
- [x] Keyboard shortcuts:
  - `Ctrl+Enter`: Trigger Delete action (opens confirmation).
  - `Ctrl+Shift+C`: Copy result (when enabled).
  - Standard `Ctrl+Z` / `Ctrl+Y` Undo / Redo.

### Phase 5: Styling, Polish & Comprehensive Testing (COMPLETED)
- [x] Implement `src/ui/styles.py` with sleek modern dark/light styling and clear button visual hierarchies.
- [x] Automated tests in `tests/test_ui.py`:
  - Verify real-time highlight switching on mode toggle.
  - Verify confirmation dialog cancel leaves text & history untouched and Copy button disabled.
  - Verify confirmation dialog accept mutates text, updates history, and enables Copy button.
  - Verify Copy button behavior and clipboard interaction.
- [x] Create executable launcher `run.py` and `run_app.bat`. (Total: 27/27 automated tests passing).

---

## Phase 6: Dark/Light Mode Theme Toggle & Replace Feature (COMPLETED)

### 1. Theme Toggle System (Dark / Light Mode)
- [x] **SVG Vector Icons**:
  - `sun.svg`: Rendered when Dark Mode is active (clicking switches to Light Mode).
  - `moon.svg`: Rendered when Light Mode is active (clicking switches to Dark Mode).
- [x] **Comprehensive Theme Palettes**:
  - Light theme: `#F8F9FA` background, `#FFFFFF` panels/editor, `#0F172A` text, `#FFE082` / `#FFCCBC` match highlights.
  - Dark theme: `#181825` background, `#1E1E2E` panels, `#11111B` editor, `#CDD6F4` text, `#B45309` / `#991B1B` highlights.
- [x] **Dynamic Highlighter Adaptation**:
  - `MatchHighlighter` dynamically recalculates its text char formats according to active theme to ensure optimal contrast and readability.
- [x] **Theme Persistence**:
  - Remembers user's theme selection in `.regexstripper_settings.json` and restores it on startup.

### 2. Replace Field & Action Engine
- [x] **UI Positioning**:
  - Positioned directly beneath the regex pattern entry field in the top panel.
  - Consists of a label `Replace With:`, a monospace `QLineEdit` (with clear button & placeholder), and a dedicated `Replace Matches` button.
- [x] **Engine Logic**:
  - `RegexEngine.replace_matches(text, pattern, replacement, flags)`:
    - Supports backreferences (e.g. `\1`, `\g<name>`).
    - Returns updated text and replacement count.
- [x] **Workflow & State Integration**:
  - Clicking `Replace Matches` (or pressing `Ctrl+R`) executes the replacement and updates the editor.
  - Commits the regex pattern into history (just like deletion).
  - Activates the `Copy Result` button.
  - Status indicator displays count of replaced occurrences.
  - Undo (`Ctrl+Z`) remains fully functional.
- [x] **Automated Verification**:
  - All 34 automated unit and UI tests passing (`tests/test_engine.py`, `tests/test_history.py`, `tests/test_settings.py`, and `tests/test_ui.py`).

---

## Phase 7: SVG Icons, Multi-Level Undo, Literal Search, Regex Quick Reference & Preset Expressions (COMPLETED)

### 1. SVG Icons Across All UI Actions
- [x] Add scalable SVG icons for all action buttons:
  - `delete_white.svg` (primary action)
  - `copy_white.svg` (primary action)
  - `replace_white.svg` (primary action)
  - `paste.svg` (for paste clipboard)
  - `clear.svg` (for clear text)
  - `undo.svg` (for undo operation)
  - `book.svg` (for quick reference popup)
  - `bookmark.svg` (for user presets popup)
  - `sun.svg` & `moon.svg` (theme toggle)

### 2. Dedicated Multi-Level Undo Stack (Last 10 Operations)
- [x] Custom undo stack tracking up to 10 historical text snapshots.
- [x] Pushes snapshots prior to any destructive operation (`delete`, `replace`, `clear`).
- [x] UI `Undo` button (`Ctrl+Shift+Z`) restores prior states sequentially and dynamically enables/disables based on stack depth.

### 3. Literal Match Mode (Exact Text Substring)
- [x] Checkbox toggle: `[ ] Literal Match (No Regex)`.
- [x] Dynamically changes the label from `"Regex Pattern:"` to `"Literal Text:"`.
- [x] Escapes patterns (`re.escape`) so characters like `\n`, `.`, `*`, `+` match literal text rather than regex tokens.
- [x] Re-computes real-time highlights, deletes, and replaces literally.

### 4. Regex Quick Reference Modal Dialog
- [x] Popup dialog (`RegexReferenceDialog`) providing a clean, tabbed reference cheat sheet:
  - Characters & Classes (`\d`, `\w`, `\s`, `.`, etc.)
  - Anchors & Quantifiers (`*`, `+`, `?`, `{n,m}`, lazy versions)
  - Groups & Lookarounds (`(...)`, `(?:...)`, `(?=...)`, `(?!...)`, `(?<=...)`, `(?<!...)`)
  - Replacement Syntax (`\1`, `\g<name>`)

### 5. Customizable Preset Expressions Dialog
- [x] Centralized user preset file: `src/presets.py` structured with easy-to-edit list of entries containing `name`, `expression`, and `description`.
- [x] First default test entry:
  - Name: `"Strip Phrase tags"`
  - Expression: `r"\{.+?>|<.+?\}"`
- [x] Popup dialog (`PresetsDialog`) displaying all saved presets with search/filter.
- [x] Clicking or double-clicking an item instantly inserts the expression into the pattern input and triggers real-time highlighting.
- [x] 41/41 automated tests passing across engine, history, presets, settings, and UI.

---

## Phase 8: Advanced Extraction, Navigation, Diff, File I/O & Standalone Compilation (COMPLETED)

### 1. Multiline Flag (`re.MULTILINE` / `m`)
- [x] Added `Multiline (m)` checkbox in options toolbar.
- [x] Enables `^` and `$` to match start and end of every line.

### 2. Custom Extraction Delimiter, Deduplication & Capture Groups
- [x] Contextual extraction settings panel in `Delete Non-Matches` mode.
- [x] Delimiter dropdown: Newline, Comma+Space, Comma, Space, Semicolon, Tab, or None.
- [x] `Unique Only (Deduplicate)` checkbox: keeps only unique occurrences, removing subsequent duplicates while preserving first-seen order.
- [x] `Capture Group / Template`: extracts specific capture group or expands template e.g. `\1`.

### 3. Match Navigator (`▲ Prev` / `▼ Next` | `F3` / `Shift+F3`)
- [x] Compact navigation controls with live index counter (e.g. `[1/14]`).
- [x] Jumps cursor and smoothly scrolls editor to matches.

### 4. File Operations & Editor Ergonomics
- [x] Drag & drop file loading for `.txt`, `.csv`, `.log`, `.md`, `.html`.
- [x] Word wrap toggle (`Wrap Lines`).
- [x] Font zooming with `Ctrl + Wheel` (or `Ctrl++` / `Ctrl+-`).
- [x] Document statistics in status bar (`Ln X, Col Y | N chars | M words`).
- [x] `Save As...` button (`Ctrl + S`) to write processed text directly to a file.

### 5. Visual Diff View Dialog
- [x] `Diff Preview` button opens side-by-side comparison modal with character delta and percentage impact.

### 6. Full UI Presets Management
- [x] `PresetManager` merges default presets (`src/presets.py`) with user-created presets (`~/.regexstripper_user_presets.json`).
- [x] `+ Add Custom Preset` button in Presets dialog to save the current pattern with a custom name directly from the GUI (works seamlessly in both source and frozen EXE).

### 7. Standalone Executable Builder
- [x] Created `build_exe.bat` for one-click PyInstaller standalone binary compilation (`dist/RegexStripper.exe`).
- [x] Bundles custom 256x256 `.ico` regex icon and vector assets.
- [x] Verified with 48/48 automated tests passing.

---

## Phase 9: Line Anchor Prepending & Appending (`^` and `$`) (COMPLETED)
- [x] **Prepending with `^`**: Replacing `^` by itself with any string (e.g. `♪`) prepends each line with that string.
- [x] **Appending with `$`**: Replacing `$` by itself with any string (e.g. `♪`) appends each line with that string before line endings (`\r\n`, `\n`, `\r`).
- [x] **Clean Line Delimitation**: Avoids Python's default `re.MULTILINE` issue where EOF is treated as an empty line, ensuring clean line-by-line processing without trailing phantom characters.
- [x] **Literal Mode Protection**: When `Literal Match` is checked, `^` and `$` are matched literally rather than as line anchors.
- [x] **Full Integration**: Works with match counting, live visual highlighting, multi-level undo, and replace actions.
- [x] **Automated Test Coverage**: Added dedicated unit and UI tests in `tests/test_engine.py` and `tests/test_ui.py` (52/52 passing).

---

## Phase 10: Inline Replace Diff Preview & UI Refinements (COMPLETED)
- [x] **Removed Modal Diff Preview**: Removed `diff_btn`, `DiffDialog`, and obsolete modal comparison dialogs in favor of rich in-editor preview.
- [x] **Standard Diff Ordering & Styling**:
  - Follows universal diff convention: **Deleted First (Left) -> Replacement Second (Right)**.
  - **Replaced / Deleted text**: Highlighted in **red**, **strikethrough**, and **italics**.
  - **Replacement text**: Highlighted in **green** and **bold**, rendered immediately to the **right** of the text it replaces.
  - Supports capture group expansions (`\1`, `\g<name>`) and line anchors (`^`, `$`).
- [x] **Default Multiline Behavior**:
  - `Multiline (m)` checkbox is now **enabled by default** (`setChecked(True)`), matching standard user expectations for multi-line text processing.
  - Users can uncheck to restrict `^` and `$` to document boundaries.
- [x] **High-Contrast "Save As..." Button**:
  - Upgraded button styling to darker emerald greens (`#047857` / `#065F46`), providing crisp, high-contrast readability with white text in both Light and Dark themes.
- [x] **Theme-Aware Colors**: Tailored contrast for both Light Mode (`#C8E6C9` green / `#FFCDD2` red) and Dark Mode (`#1E4620` green / `#4A1515` red).
- [x] **Editor Ergonomics & Read-Only Protection**:
  - Editor automatically locks to read-only during active replacement preview to prevent corrupting synthetic preview text.
  - Pressing `Esc` or clearing the replace field immediately exits preview mode and restores the editable clean text.
  - Copying (`Ctrl+C` or "Copy Result") and "Save As..." always preserve and write the clean raw text.
- [x] **Comprehensive Test Suite**: 56/56 unit and UI tests passing.

---

## Phase 11: Disable Multiline Toggle & Delete Duplicates Feature (COMPLETED)
- [x] **Renamed Multiline Checkbox**:
  - Renamed from "Multiline (m)" to "Disable multiline".
  - Default: Unchecked (`setChecked(False)`), ensuring multiline is active by default.
  - When checked: treats text as a single line, omitting `re.MULTILINE` from flags so line anchors (`^` and `$`) match only the start and end of the entire text buffer.
- [x] **Engine Anchor Flag Support**:
  - Updated `RegexEngine.find_match_spans`, `count_matches`, `strip_matches`, `replace_matches`, and `generate_diff_preview` to respect `flags & re.MULTILINE` when evaluating anchors `^` and `$`.
- [x] **New "Delete Duplicates" Button**:
  - Positioned directly to the left of the "Delete Matches" button in the bottom action bar.
  - Dynamically enabled only when "Disable multiline" is unchecked and text is present; immediately disabled when "Disable multiline" is checked.
  - Bundled custom vector SVG icon (`assets/icons/dedup.svg`) with styled amber theme palettes in both Light and Dark modes.
- [x] **Duplicate Lines Deletion Engine & Modal Confirmation**:
  - Implemented `RegexEngine.delete_duplicate_lines` to remove subsequent occurrences of duplicate lines while preserving first-seen order, line ending formats (CRLF/LF), and trailing newlines.
  - Implemented `DeleteDuplicatesConfirmationDialog` safety modal displaying duplicate count and total lines, with safe Cancel default.
  - Full workflow integration: multi-level undo stack push (`Ctrl+Shift+Z`), Copy Result button activation, status feedback, and real-time highlight refresh.
- [x] **Button Padding Optimization**:
  - Reduced horizontal (left/right) padding across all buttons by 40% (base buttons reduced from 16px to 10px; theme/nav buttons reduced from 8px to 5px) for a tighter, more compact layout.
- [x] **Automated Test Coverage**: 61/61 unit and UI tests passing.

---

## 7. Edge Cases & Safeguards

1. **Inverted Spans Calculation**:
   - When text has zero matches, in *Delete Non-Matches* mode the entire text is a non-match (everything would be deleted). The confirmation dialog must clearly warn: `"0 matches found. Deleting non-matches will clear the entire text."`
   - Handle overlapping or adjacent matches cleanly when calculating complementary intervals.
2. **Invalid Regex Handling**:
   - Incomplete patterns during typing (e.g. unclosed parenthesis) are caught via `re.error`; highlights clear gracefully and status shows the exact syntax problem without throwing uncaught exceptions.
3. **Cancellation Safeguard**:
   - History must *never* record aborted attempts. Only confirmed deletions write to the LRU cache.
4. **Undo Support for Destructive Actions**:
   - Deletions are applied through Qt's text cursor or document batch so standard `Ctrl+Z` undo continues to function even after a confirmed deletion.
