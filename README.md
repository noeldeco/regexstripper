# Regex Stripper (RegexStripper)

A fast, responsive desktop utility built with **PySide6** designed for rapid text processing, pattern matching, regex-based content cleaning, string replacement, and phrase tag extraction.

---

## ✨ Features

- **📑 Multiline Flag (`re.MULTILINE` / `m`)**:
  - Essential regex flag toggle allowing `^` and `$` to match the beginning and end of each individual line.

- **✂️ Extraction Delimiter & Unique Deduplication**:
  - In *Delete Non-Matches (Keep Matches)* mode, choose how extracted matches are formatted:
    - **Delimiters**: Newline (`\n`), Comma-Space (`, `), Comma (`,`), Space, Semicolon (`;`), Tab (`\t`), or None.
    - **`Unique Only`**: Deduplicates extracted items in place while preserving first-seen order (ideal for unique lists of emails, IDs, URLs, or tags).
    - **`Capture Group`**: Extract specific capture groups (e.g. `1`, `2`) or formatted templates (e.g. `\1 - \2`).

- **🔍 Match Navigator (`▲ Prev` / `▼ Next`)**:
  - Jump directly between regex match highlights using `F3` (Next) and `Shift + F3` (Prev) or the toolbar buttons.
  - Live index indicator shows your current match position (e.g. `[1/14]`).

- **📁 File Drag & Drop & Direct Save**:
  - Drag and drop `.txt`, `.csv`, `.log`, `.md`, or `.html` files directly onto the editor to load them instantly.
  - Dedicated **`💾 Save As...`** button (`Ctrl + S`) to write processed text directly to disk.

- **🪟 Visual Diff Inspection**:
  - Click **`Diff Preview`** to open a side-by-side before-and-after view comparing original vs. processed text with character delta and percentage reduction stats.

- **⭐ Presets & UI Preset Management**:
  - Open commonly used regex patterns with the **`Presets`** button.
  - Includes pre-configured test preset:
    - **Strip Phrase tags**: `\{.+?>|<.+?\}`
  - **Save new presets directly from the GUI**: Click `+ Add Custom Preset` in the presets dialog to save your current pattern with a custom name. Presets are stored in `~/.regexstripper_user_presets.json` and persist across sessions (and inside standalone `.exe` builds).

- **↩️ Multi-Level Operation Undo**:
  - Automatically records text snapshots before any destructive operation.
  - Easily revert the last 10 operations via the **`Undo`** button or `Ctrl + Shift + Z`.

- **🔤 Literal Match Mode (No Regex)**:
  - Checkbox toggle: `[ ] Literal Match (No Regex)`.
  - When enabled, the pattern label switches from `"Regex Pattern:"` to `"Literal Text:"`.
  - Disables regex token interpretation: `\n` matches a literal backslash followed by the letter `n` (not a newline), `.` matches a period, etc.

- **📖 Regex Quick Reference Cheat Sheet**:
  - One-click **`Reference`** button opens a tabbed popup window covering character classes, anchors, quantifiers, groups/lookarounds, and replacement syntax.

- **🌓 Dark / Light Mode Toggle**:
  - One-click theme toggle in the header using `sun.svg` and `moon.svg`.
  - Automatically adapts match highlight colors for optimal contrast in each theme.
  - Remembers your chosen theme across app restarts in `.regexstripper_settings.json`.

- **🔄 Search & Replace Engine**:
  - Convenient replacement input field directly beneath the regex pattern entry.
  - Dedicated **`Replace Matches`** button to perform replacements across all matches.
  - Full support for regex backreferences (e.g. `\1`, `\2`, `\g<group_name>`).
  - Shortcut: `Ctrl + R`.

- **⚡ Bidirectional Deletion Modes**:
  - **Delete Matches (Default)**: Strips out all regex matches and retains surrounding text.
  - **Delete Non-Matches (Keep Matches)**: Strips out all non-matching text, leaving only the matched segments.

- **🎨 Dynamic Real-Time Highlighting**:
  - 120ms debounced highlighting updates in real time as you type your pattern.
  - Switching modes immediately changes highlighting to reflect the exact spans that will be removed.

- **🛡️ Safety Confirmation Modal**:
  - Before deleting text, clicking Delete prompts a confirmation dialog detailing match counts and action scope to prevent accidental data loss.

- **📋 Strict Copy Button Lifecycle**:
  - The Copy button is disabled by default and only becomes active after a delete or replace operation has been performed.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + Enter` | Trigger Delete operation (opens confirmation dialog) |
| `Ctrl + R` | Trigger Replace operation |
| `Ctrl + S` | Save processed text to a file |
| `Ctrl + Shift + Z` | Undo last operation (from multi-level undo stack) |
| `Ctrl + Shift + C` | Copy result to clipboard (when active) |
| `F3` | Jump to Next regex match in editor |
| `Shift + F3` | Jump to Previous regex match in editor |
| `Ctrl + Scroll` | Zoom text editor font size in / out |
| `Ctrl + Z` | Undo typing in text editor |
| `Ctrl + Y` | Redo typing in text editor |

---

## 🚀 Running the Application

Double-click `run_app.bat` or run from terminal:

```bash
# In the regexstripper directory:
.\.venv\Scripts\python.exe run.py
```

### Running Tests
```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

---

## 📦 Building Standalone Executable (.exe)

To compile a standalone, single-file Windows executable with custom regex icon:

Double-click `build_exe.bat` or run:

```cmd
build_exe.bat
```

Output binary: `dist\RegexStripper.exe`.
