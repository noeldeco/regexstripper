"""
Unit tests for Presets and PresetsDialog
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
from PySide6.QtWidgets import QApplication

from src.presets import PRESET_EXPRESSIONS
from src.ui.presets_dialog import PresetsDialog

app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestPresets(unittest.TestCase):

    def test_strip_phrase_tags_preset_exists(self):
        # Must have "Strip Phrase tags" with expression r"\{.+?>|<.+?\}"
        first_entry = PRESET_EXPRESSIONS[0]
        self.assertEqual(first_entry["name"], "Strip Phrase tags")
        self.assertEqual(first_entry["expression"], r"\{.+?>|<.+?\}")

    def test_presets_dialog_filtering(self):
        dialog = PresetsDialog()
        self.assertGreater(dialog.table.rowCount(), 0)

        # Filter by "Phrase"
        dialog._on_filter_changed("Phrase")
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(dialog.table.item(0, 0).text(), "Strip Phrase tags")

        # Clear filter
        dialog._on_filter_changed("")
        self.assertEqual(dialog.table.rowCount(), len(dialog._all_presets))
        dialog.close()

    def test_preset_manager_persistence(self):
        import tempfile
        from pathlib import Path
        from src.core.preset_manager import PresetManager

        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "custom_presets.json"
            mgr = PresetManager(file_path=f)
            self.assertEqual(len(mgr.get_all_presets()), len(PRESET_EXPRESSIONS))

            # Add user preset
            mgr.add_user_preset("My Tags", r"\[tag:\w+\]", "Custom tags")
            all_presets = mgr.get_all_presets()
            self.assertEqual(len(all_presets), len(PRESET_EXPRESSIONS) + 1)
            self.assertEqual(all_presets[-1]["name"], "My Tags")

            # Reload
            reloaded = PresetManager(file_path=f)
            self.assertEqual(len(reloaded.get_all_presets()), len(PRESET_EXPRESSIONS) + 1)


if __name__ == "__main__":
    unittest.main()

