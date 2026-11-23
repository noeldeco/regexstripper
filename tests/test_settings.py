"""
Unit tests for SettingsManager
"""

import unittest
import tempfile
from pathlib import Path
from src.config import AppTheme
from src.core.settings_manager import SettingsManager


class TestSettingsManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = Path(self.temp_dir.name) / "test_settings.json"
        self.manager = SettingsManager(file_path=self.settings_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_theme(self):
        self.assertEqual(self.manager.theme, AppTheme.LIGHT)

    def test_save_and_reload_theme(self):
        self.manager.theme = AppTheme.DARK
        self.assertEqual(self.manager.theme, AppTheme.DARK)

        # Create new instance pointing to same file
        reloaded = SettingsManager(file_path=self.settings_file)
        self.assertEqual(reloaded.theme, AppTheme.DARK)

    def test_save_and_reload_session_preferences(self):
        self.manager.font_size = 15
        self.manager.word_wrap = False
        self.manager.ignore_case = True
        self.manager.disable_multiline = True
        self.manager.dot_all = True
        self.manager.interpret_escapes = True
        self.manager.window_geometry = (100, 120, 1100, 800)

        reloaded = SettingsManager(file_path=self.settings_file)
        self.assertEqual(reloaded.font_size, 15)
        self.assertFalse(reloaded.word_wrap)
        self.assertTrue(reloaded.ignore_case)
        self.assertTrue(reloaded.disable_multiline)
        self.assertTrue(reloaded.dot_all)
        self.assertTrue(reloaded.interpret_escapes)
        self.assertEqual(reloaded.window_geometry, (100, 120, 1100, 800))


if __name__ == "__main__":
    unittest.main()

