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


if __name__ == "__main__":
    unittest.main()

