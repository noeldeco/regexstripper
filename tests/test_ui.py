"""
UI integration tests for Regex Stripper
Tests MainWindow, mode toggles, confirmation dialog, copy button lifecycle, and history registration.
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from src.config import DeletionMode, AppTheme
from src.core.history_manager import HistoryManager
from src.ui.main_window import MainWindow
from src.ui.confirmation_dialog import (
    DeleteConfirmationDialog,
    DeleteDuplicatesConfirmationDialog,
)

# Ensure single QApplication instance across tests
app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestUI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.history_file = Path(self.temp_dir.name) / "test_history.json"
        self.history_manager = HistoryManager(file_path=self.history_file, max_items=10)
        self.window = MainWindow(history_manager=self.history_manager)

    def tearDown(self):
        self.window.close()
        self.temp_dir.cleanup()

    def test_initial_state(self):
        # Copy button must be disabled initially
        self.assertFalse(self.window.copy_btn.isEnabled())
        # Delete button disabled with empty pattern/text
        self.assertFalse(self.window.delete_btn.isEnabled())
        # Default mode is DELETE_MATCHES
        self.assertTrue(self.window.mode_delete_matches.isChecked())
        self.assertEqual(self.window.active_mode, DeletionMode.DELETE_MATCHES)

    def test_highlighting_on_pattern_and_text(self):
        self.window.editor.setPlainText("user123 and user456")
        self.window.pattern_combo.setEditText(r"\d+")
        # Trigger immediate highlight update
        self.window._apply_highlights()

        # ExtraSelections should reflect matches
        selections = self.window.editor.extraSelections()
        self.assertEqual(len(selections), 2)
        self.assertTrue(self.window.delete_btn.isEnabled())

    def test_mode_toggle_updates_button_and_highlights(self):
        self.window.editor.setPlainText("abc123def")
        self.window.pattern_combo.setEditText(r"\d+")
        self.window._apply_highlights()

        # Default mode: matches highlighted
        self.assertEqual(self.window.active_mode, DeletionMode.DELETE_MATCHES)
        self.assertEqual(len(self.window.editor.extraSelections()), 1)

        # Toggle to DELETE_NON_MATCHES
        self.window.mode_delete_non_matches.setChecked(True)
        self.assertEqual(self.window.active_mode, DeletionMode.DELETE_NON_MATCHES)
        self.assertIn("Delete Non-Matches", self.window.delete_btn.text())

        # Inverted mode: non-matching text (abc, def) highlighted -> 2 selections
        selections = self.window.editor.extraSelections()
        self.assertEqual(len(selections), 2)

    @patch.object(DeleteConfirmationDialog, "confirm", return_value=False)
    def test_delete_cancelled_leaves_state_intact(self, mock_confirm):
        initial_text = "Keep this [REMOVE] and this [REMOVE]."
        self.window.editor.setPlainText(initial_text)
        self.window.pattern_combo.setEditText(r"\[REMOVE\]")
        self.window._apply_highlights()

        # Click delete but cancel dialog
        self.window._on_delete_clicked()

        # Text must remain untouched
        self.assertEqual(self.window.editor.toPlainText(), initial_text)
        # History must NOT register the pattern
        self.assertEqual(self.history_manager.history, [])
        # Copy button must remain disabled
        self.assertFalse(self.window.copy_btn.isEnabled())

    @patch.object(DeleteConfirmationDialog, "confirm", return_value=True)
    def test_delete_confirmed_strips_matches_and_enables_copy(self, mock_confirm):
        text = "Hello 123 World 456"
        self.window.editor.setPlainText(text)
        self.window.pattern_combo.setEditText(r"\d+")
        self.window._apply_highlights()

        # Click delete and confirm
        self.window._on_delete_clicked()

        # Text must have matches removed
        self.assertEqual(self.window.editor.toPlainText(), "Hello  World ")
        # History must now contain the pattern
        self.assertIn(r"\d+", self.history_manager.history)
        # Copy button must now be enabled
        self.assertTrue(self.window.copy_btn.isEnabled())

    @patch.object(DeleteConfirmationDialog, "confirm", return_value=True)
    def test_delete_non_matches_mode(self, mock_confirm):
        text = "Contact: test@example.com or admin@foo.org"
        self.window.editor.setPlainText(text)
        self.window.pattern_combo.setEditText(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        self.window.mode_delete_non_matches.setChecked(True)
        self.window._apply_highlights()

        self.window._on_delete_clicked()

        # Only matches retained
        self.assertEqual(self.window.editor.toPlainText(), "test@example.com\nadmin@foo.org")
        self.assertTrue(self.window.copy_btn.isEnabled())

    def test_clear_editor_resets_copy_button(self):
        # Enable copy button manually to simulate post-delete state
        self.window.copy_btn.setEnabled(True)
        self.window.editor.setPlainText("Some text")

        # Clear text
        self.window.editor.clear()
        self.window._on_text_changed()

        # Copy button must reset to disabled
        self.assertFalse(self.window.copy_btn.isEnabled())

    @patch.object(DeleteConfirmationDialog, "confirm", return_value=True)
    def test_copy_button_copies_to_clipboard(self, mock_confirm):
        self.window.editor.setPlainText("Delete 123 this")
        self.window.pattern_combo.setEditText(r"\d+\s*")
        self.window._apply_highlights()
        self.window._on_delete_clicked()

        # Copy button should be enabled
        self.assertTrue(self.window.copy_btn.isEnabled())

        # Click Copy button
        self.window._on_copy_clicked()

        # Clipboard content should match editor
        clipboard_text = QApplication.clipboard().text()
        self.assertEqual(clipboard_text, self.window.editor.toPlainText())

    def test_theme_toggle(self):
        initial_theme = self.window.current_theme
        self.assertEqual(initial_theme, AppTheme.LIGHT)

        # Click theme toggle button -> should switch to DARK
        self.window._toggle_theme()
        self.assertEqual(self.window.current_theme, AppTheme.DARK)
        self.assertEqual(self.window.highlighter.theme, AppTheme.DARK)

        # Click again -> should switch back to LIGHT
        self.window._toggle_theme()
        self.assertEqual(self.window.current_theme, AppTheme.LIGHT)
        self.assertEqual(self.window.highlighter.theme, AppTheme.LIGHT)

    def test_replace_matches_ui(self):
        self.window.editor.setPlainText("user: alice, user: bob")
        self.window.pattern_combo.setEditText(r"user:\s*(\w+)")
        self.window.replace_input.setText(r"admin[\1]")
        self.window._apply_highlights()

        # Replace button should be enabled
        self.assertTrue(self.window.replace_btn.isEnabled())

        # Execute replace
        self.window._on_replace_clicked()

        # Text should be replaced
        self.assertEqual(self.window.editor.toPlainText(), "admin[alice], admin[bob]")
        # History must have registered the pattern
        self.assertIn(r"user:\s*(\w+)", self.history_manager.history)
        # Copy button must now be enabled
        self.assertTrue(self.window.copy_btn.isEnabled())

    def test_literal_match_ui(self):
        # Initial label
        self.assertEqual(self.window.pattern_label.text(), "Regex Pattern:")

        # Toggle literal match
        self.window.literal_match_cb.setChecked(True)
        self.assertEqual(self.window.pattern_label.text(), "Literal Text:")

        # Test matching with literal token
        self.window.editor.setPlainText(r"test \n word")
        self.window.pattern_combo.setEditText(r"\n")
        self.window._apply_highlights()

        # Should match literal "\n"
        self.assertEqual(len(self.window.editor.extraSelections()), 1)

        # Toggle back
        self.window.literal_match_cb.setChecked(False)
        self.assertEqual(self.window.pattern_label.text(), "Regex Pattern:")

    @patch.object(DeleteConfirmationDialog, "confirm", return_value=True)
    def test_multi_level_undo_ui(self, mock_confirm):
        initial_text = "Step 0: original"
        self.window.editor.setPlainText(initial_text)
        self.assertFalse(self.window.undo_btn.isEnabled())

        # Operation 1: Replace
        self.window.pattern_combo.setEditText("original")
        self.window.replace_input.setText("first")
        self.window._apply_highlights()
        self.window._on_replace_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "Step 0: first")
        self.assertTrue(self.window.undo_btn.isEnabled())

        # Operation 2: Delete
        self.window.pattern_combo.setEditText("first")
        self.window._apply_highlights()
        self.window._on_delete_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "Step 0: ")

        # Undo 1: should restore "Step 0: first"
        self.window._on_undo_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "Step 0: first")
        self.assertTrue(self.window.undo_btn.isEnabled())

        # Undo 2: should restore initial text "Step 0: original"
        self.window._on_undo_clicked()
        self.assertEqual(self.window.editor.toPlainText(), initial_text)
        self.assertFalse(self.window.undo_btn.isEnabled())

    def test_quick_reference_dialog(self):
        from src.ui.regex_reference_dialog import RegexReferenceDialog
        dialog = RegexReferenceDialog()
        self.assertEqual(dialog.tabs.count(), 4)
        dialog.close()

    def test_match_navigation_ui(self):
        self.window.editor.setPlainText("first 100, second 200, third 300")
        self.window.pattern_combo.setEditText(r"\d+")
        self.window._apply_highlights()

        self.assertEqual(len(self.window.current_match_spans), 3)
        self.assertTrue(self.window.next_match_btn.isEnabled())
        self.assertTrue(self.window.prev_match_btn.isEnabled())

        # Navigate next
        self.window._navigate_match(1)
        self.assertEqual(self.window.current_match_index, 0)
        self.assertIn("1/3", self.window.match_nav_label.text())

        # Navigate next again
        self.window._navigate_match(1)
        self.assertEqual(self.window.current_match_index, 1)
        self.assertIn("2/3", self.window.match_nav_label.text())

    def test_extraction_panel_visibility(self):
        self.assertTrue(self.window.extraction_panel.isHidden())
        self.window.mode_delete_non_matches.setChecked(True)
        self.assertFalse(self.window.extraction_panel.isHidden())
        self.window.mode_delete_matches.setChecked(True)
        self.assertTrue(self.window.extraction_panel.isHidden())

    def test_inline_replace_diff_preview_ui(self):
        initial_text = "user: alice, user: bob"
        self.window.editor.setPlainText(initial_text)
        self.window.pattern_combo.setEditText(r"user:\s*(\w+)")
        self.window.replace_input.setText(r"admin[\1]")
        self.window._apply_highlights()

        # Preview mode must be active
        self.assertTrue(self.window._is_previewing)
        self.assertTrue(self.window.editor.isReadOnly())

        # Editor displays diff text: replacement to the right of the replaced text
        preview_text = self.window.editor.previewPlainText()
        self.assertEqual(preview_text, "user: aliceadmin[alice], user: bobadmin[bob]")
        self.assertEqual(self.window.editor.toPlainText(), initial_text)

        # Extra selections must have 4 selections (2 red originals + 2 green replacements)
        selections = self.window.editor.extraSelections()
        self.assertEqual(len(selections), 4)

        # Check format properties: green format has bold, red format has strikeout and italics
        has_bold = any(s.format.fontWeight() == 700 for s in selections)
        has_strikeout = any(s.format.fontStrikeOut() for s in selections)
        has_italic = any(s.format.fontItalic() for s in selections)
        self.assertTrue(has_bold)
        self.assertTrue(has_strikeout)
        self.assertTrue(has_italic)

        # Status indicates Replace Preview mode
        self.assertIn("Replace Preview", self.window.status_label.text())

        # Clearing replace input exits preview mode and restores original text
        self.window.replace_input.setText("")
        self.window._apply_highlights()
        self.assertFalse(self.window._is_previewing)
        self.assertFalse(self.window.editor.isReadOnly())
        self.assertEqual(self.window.editor.toPlainText(), initial_text)

        # Testing Esc key clears replace input
        self.window.replace_input.setText("test")
        self.window._on_escape_pressed()
        self.assertEqual(self.window.replace_input.text(), "")

        # Execute replace
        self.window.replace_input.setText(r"admin[\1]")
        self.window._apply_highlights()
        self.window._on_replace_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "admin[alice], admin[bob]")

    def test_replace_caret_and_dollar_anchors_ui(self):
        self.window.editor.setPlainText("Line One\nLine Two\nLine Three\n")

        # Caret replacement
        self.window.pattern_combo.setEditText("^")
        self.window.replace_input.setText("♪")
        self.window._apply_highlights()
        self.assertTrue(self.window.replace_btn.isEnabled())

        self.window._on_replace_clicked()
        self.assertEqual(
            self.window.editor.toPlainText(),
            "♪Line One\n♪Line Two\n♪Line Three\n"
        )

        # Undo caret replacement
        self.window._on_undo_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "Line One\nLine Two\nLine Three\n")

        # Dollar replacement
        self.window.pattern_combo.setEditText("$")
        self.window.replace_input.setText("♪")
        self.window._apply_highlights()
        self.assertTrue(self.window.replace_btn.isEnabled())

        self.window._on_replace_clicked()
        self.assertEqual(
            self.window.editor.toPlainText(),
            "Line One♪\nLine Two♪\nLine Three♪\n"
        )

    def test_disable_multiline_checkbox_ui(self):
        # 1. By default, "Disable multiline" is NOT checked -> multiline is ON
        self.assertFalse(self.window.disable_multiline_cb.isChecked())
        self.window.editor.setPlainText("Line One\nLine Two\nLine Three\n")
        self.window.pattern_combo.setEditText("^")
        self.window._apply_highlights()
        # In multiline mode, ^ matches all 3 lines
        self.assertEqual(len(self.window.current_match_spans), 3)

        # 2. Check "Disable multiline" -> single line mode
        self.window.disable_multiline_cb.setChecked(True)
        self.window._apply_highlights()
        # In single-line mode, ^ matches only at position 0 (1 match)
        self.assertEqual(len(self.window.current_match_spans), 1)

        # 3. In single-line mode, replacement prepends only at the beginning of the text
        self.window.replace_input.setText("♪")
        self.window._apply_highlights()
        self.window._on_replace_clicked()
        self.assertEqual(
            self.window.editor.toPlainText(),
            "♪Line One\nLine Two\nLine Three\n"
        )

    def test_delete_duplicates_button_enabled_state(self):
        # When editor is empty, button is disabled
        self.window.editor.clear()
        self.window._apply_highlights()
        self.assertFalse(self.window.delete_duplicates_btn.isEnabled())

        # When editor has text and Disable multiline is unchecked -> enabled
        self.window.editor.setPlainText("Alpha\nBeta\nAlpha\n")
        self.window._apply_highlights()
        self.assertFalse(self.window.disable_multiline_cb.isChecked())
        self.assertTrue(self.window.delete_duplicates_btn.isEnabled())

        # When Disable multiline is checked -> button must become disabled
        self.window.disable_multiline_cb.setChecked(True)
        self.assertFalse(self.window.delete_duplicates_btn.isEnabled())

        # Unchecking Disable multiline re-enables it
        self.window.disable_multiline_cb.setChecked(False)
        self.assertTrue(self.window.delete_duplicates_btn.isEnabled())

    @patch.object(DeleteDuplicatesConfirmationDialog, "confirm", return_value=False)
    def test_delete_duplicates_action_cancel(self, mock_confirm):
        original = "apple\nbanana\napple\ncherry\n"
        self.window.editor.setPlainText(original)
        self.window._apply_highlights()
        self.window.copy_btn.setEnabled(False)

        # Click Delete Duplicates but cancel dialog
        self.window._on_delete_duplicates_clicked()
        mock_confirm.assert_called_once()
        # Text and states must remain untouched
        self.assertEqual(self.window.editor.toPlainText(), original)
        self.assertFalse(self.window.copy_btn.isEnabled())

    @patch.object(DeleteDuplicatesConfirmationDialog, "confirm", return_value=True)
    def test_delete_duplicates_action_confirm_and_undo(self, mock_confirm):
        original = "apple\nbanana\napple\ncherry\nbanana\n"
        self.window.editor.setPlainText(original)
        self.window._apply_highlights()
        self.window.copy_btn.setEnabled(False)

        # Click Delete Duplicates and accept dialog
        self.window._on_delete_duplicates_clicked()
        mock_confirm.assert_called_once()

        # Duplicates deleted, first occurrence and order preserved
        expected = "apple\nbanana\ncherry\n"
        self.assertEqual(self.window.editor.toPlainText(), expected)
        self.assertTrue(self.window.copy_btn.isEnabled())
        self.assertIn("Deleted 2 duplicate line(s)", self.window.status_label.text())

        # Test Undo restores original text
        self.window._on_undo_clicked()
        self.assertEqual(self.window.editor.toPlainText(), original)

    @patch.object(DeleteConfirmationDialog, "confirm", return_value=True)
    def test_line_level_modes_and_redo(self, mock_confirm):
        original = "INFO a\nERROR b\nINFO c\nERROR d\n"
        self.window.editor.setPlainText(original)
        self.window.pattern_combo.setEditText("ERROR")

        # Delete Matching Lines
        self.window.mode_delete_matching_lines.setChecked(True)
        self.assertEqual(self.window.active_mode, DeletionMode.DELETE_MATCHING_LINES)
        self.window._on_delete_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "INFO a\nINFO c\n")
        self.assertIn("Deleted 2 matching line(s)", self.window.status_label.text())

        # Undo then Redo
        self.window._on_undo_clicked()
        self.assertEqual(self.window.editor.toPlainText(), original)
        self.assertTrue(self.window.redo_btn.isEnabled())
        self.assertIn("Undid last operation", self.window.status_label.text())

        self.window._on_redo_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "INFO a\nINFO c\n")
        self.assertIn("Redid operation", self.window.status_label.text())

        # Keep Matching Lines
        self.window.editor.setPlainText(original)
        self.window.mode_keep_matching_lines.setChecked(True)
        self.window._on_delete_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "ERROR b\nERROR d\n")

    def test_line_utilities_ui(self):
        self.window.editor.setPlainText("  b  \n\n  a  \n")
        self.window._on_line_utility("trim")
        self.assertEqual(self.window.editor.toPlainText(), "b\n\na\n")

        self.window._on_line_utility("remove_blank")
        self.assertEqual(self.window.editor.toPlainText(), "b\na\n")

        self.window._on_line_utility("sort_asc")
        self.assertEqual(self.window.editor.toPlainText(), "a\nb\n")

    def test_step_through_replace_next_ui(self):
        self.window.editor.setPlainText("cat 1, cat 2, cat 3")
        self.window.pattern_combo.setEditText("cat")
        self.window.replace_input.setText("dog")
        self.window._apply_highlights()

        # Navigate matches in replace preview should not double count (3, not 6)
        self.assertEqual(len(self.window.current_match_spans), 3)

        # Replace only the first match
        self.window._on_replace_next_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "dog 1, cat 2, cat 3")

        # Replace next match
        self.window._on_replace_next_clicked()
        self.assertEqual(self.window.editor.toPlainText(), "dog 1, dog 2, cat 3")

    def test_live_extraction_preview_pane(self):
        self.window.editor.setPlainText("id=10 id=20 id=10")
        self.window.pattern_combo.setEditText(r"id=(\d+)")
        self.window.mode_delete_non_matches.setChecked(True)
        self.window.unique_cb.setChecked(True)
        self.window.capture_group_input.setText("1")
        self.window.live_extract_preview_cb.setChecked(True)

        self.assertFalse(self.window.preview_container.isHidden())
        self.assertEqual(self.window.extraction_preview_editor.toPlainText(), "10\n20")

    def test_bugfixes_noop_replace_theme_preview_zoom_and_dark_qss(self):
        from src.ui.styles import DARK_STYLESHEET, LIGHT_STYLESHEET
        from src.ui.editor import DragDropEditor

        # 1. No-op replace must not push to undo stack
        self.window.editor.setPlainText("hello world")
        self.window.pattern_combo.setEditText(r"\d+")
        self.window.replace_input.setText("X")
        self.window._apply_highlights()
        self.assertEqual(len(self.window.undo_stack), 0)
        self.window._on_replace_clicked()
        self.assertEqual(len(self.window.undo_stack), 0)

        # 2. Theme toggle during active replace preview preserves diff highlights
        self.window.editor.setPlainText("foo 123")
        self.window.pattern_combo.setEditText(r"\d+")
        self.window.replace_input.setText("999")
        self.window._apply_highlights()
        self.assertTrue(self.window._is_previewing)
        self.window._toggle_theme()
        self.assertTrue(self.window.highlighter._is_diff_mode)
        self.assertEqual(len(self.window.editor.extraSelections()), 2)

        # 3. Font zoom works and QSS does not hardcode font-size on #editor
        initial_pt = self.window.editor.current_font_size
        self.window.editor.zoom_in()
        self.assertEqual(self.window.editor.current_font_size, initial_pt + 1)
        self.assertEqual(self.window.editor.font().pointSize(), initial_pt + 1)
        self.assertEqual(self.window.settings_manager.font_size, initial_pt + 1)
        self.assertIn(f"font-size: {initial_pt + 1}pt;", self.window.editor.styleSheet())

        # 4. Dark theme navBtn and saveBtn:disabled use dark colors, not light copy-paste
        self.assertNotIn("background-color: #D1FAE5;", DARK_STYLESHEET)
        self.assertNotIn("background-color: #F1F5F9;", DARK_STYLESHEET)

        # 5. CRLF file normalization
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "crlf.txt"
            p.write_bytes(b"line1\r\nline2\r\n")
            norm, eol = DragDropEditor.read_file_normalized(str(p))
            self.assertEqual(norm, "line1\nline2\n")
            self.assertEqual(eol, "\r\n")

    def test_responsive_icon_only_buttons_on_narrow_width(self):
        # Wide window: full text visible on all buttons
        self.window.resize(1100, 780)
        self.window._apply_responsive_button_labels(1100)
        self.assertEqual(self.window.undo_btn.text(), " Undo")
        self.assertEqual(self.window.delete_btn.text(), " Delete Matches...")

        # Medium-narrow window: utility buttons collapse to icon-only, primary buttons keep text
        self.window._apply_responsive_button_labels(950)
        self.assertEqual(self.window.undo_btn.text(), "")
        self.assertTrue(bool(self.window.undo_btn.toolTip()))
        self.assertEqual(self.window.delete_btn.text(), " Delete Matches...")

        # Minimum width: all action buttons collapse to icon-only with tooltips
        self.window._apply_responsive_button_labels(820)
        self.assertEqual(self.window.undo_btn.text(), "")
        self.assertEqual(self.window.delete_duplicates_btn.text(), "")
        self.assertEqual(self.window.delete_btn.text(), "")
        self.assertEqual(self.window.copy_btn.text(), "")
        self.assertEqual(self.window.save_btn.text(), "")
        self.assertTrue(bool(self.window.delete_btn.toolTip()))

        # Expanding back restores full labels
        self.window._apply_responsive_button_labels(1100)
        self.assertEqual(self.window.undo_btn.text(), " Undo")
        self.assertEqual(self.window.copy_btn.text(), " Copy Result")


if __name__ == "__main__":
    unittest.main()

