"""
Unit tests for HistoryManager
"""

import unittest
import tempfile
from pathlib import Path
from src.core.history_manager import HistoryManager


class TestHistoryManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.history_file = Path(self.temp_dir.name) / "test_history.json"
        self.manager = HistoryManager(file_path=self.history_file, max_items=5)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_empty(self):
        self.assertEqual(self.manager.history, [])

    def test_add_pattern(self):
        self.manager.add_pattern(r"\d+")
        self.manager.add_pattern(r"[a-z]+")
        self.assertEqual(self.manager.history, [r"[a-z]+", r"\d+"])

    def test_add_duplicate_moves_to_top(self):
        self.manager.add_pattern(r"\d+")
        self.manager.add_pattern(r"[a-z]+")
        self.manager.add_pattern(r"\d+")
        # \d+ should be moved to front, not duplicated
        self.assertEqual(self.manager.history, [r"\d+", r"[a-z]+"])

    def test_max_items_enforced(self):
        for i in range(10):
            self.manager.add_pattern(f"pattern_{i}")
        self.assertEqual(len(self.manager.history), 5)
        self.assertEqual(self.manager.history[0], "pattern_9")
        self.assertEqual(self.manager.history[-1], "pattern_5")

    def test_persistence_reload(self):
        self.manager.add_pattern("pat1")
        self.manager.add_pattern("pat2")

        # Create new manager pointing to same file
        new_manager = HistoryManager(file_path=self.history_file, max_items=5)
        self.assertEqual(new_manager.history, ["pat2", "pat1"])

    def test_clear(self):
        self.manager.add_pattern("pat1")
        self.manager.clear()
        self.assertEqual(self.manager.history, [])
        self.assertTrue(self.history_file.exists())


if __name__ == "__main__":
    unittest.main()

