"""
Unit and UI tests for PipelineManager and PipelineDialog
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication

from src.core.pipeline_manager import PipelineManager, BUILTIN_PIPELINES
from src.ui.pipeline_dialog import PipelineDialog

app = QApplication.instance()
if app is None:
    app = QApplication(["-platform", "offscreen"])


class TestPipelines(unittest.TestCase):

    def test_run_builtin_phrase_tag_pipeline(self):
        raw = "  {tag>Hello<tag}  \n\n  {x}World  \n  Hello  \n"
        steps = BUILTIN_PIPELINES[0]["steps"]
        out, summaries = PipelineManager.run_pipeline(raw, steps)
        self.assertEqual(out, "Hello\nWorld\n")
        self.assertEqual(len(summaries), 4)

    def test_run_mixed_pipeline_steps(self):
        text = "INFO item10\nDEBUG skip\nINFO item2\nINFO item10\n"
        steps = [
            {"action": "delete_matching_lines", "pattern": "DEBUG"},
            {"action": "replace_matches", "pattern": r"^INFO\s+", "replacement": ""},
            {"action": "delete_duplicates"},
            {"action": "sort_lines", "sort_mode": "natural"},
        ]
        out, summaries = PipelineManager.run_pipeline(text, steps)
        self.assertEqual(out, "item2\nitem10\n")
        self.assertEqual(len(summaries), 4)

    def test_pipeline_persistence_and_delete(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "pipelines.json"
            mgr = PipelineManager(file_path=f)
            base_count = len(mgr.get_all_pipelines())
            self.assertEqual(base_count, len(BUILTIN_PIPELINES))

            steps = [{"action": "trim_lines"}, {"action": "remove_blank_lines"}]
            self.assertTrue(mgr.save_pipeline("My Cleanup", steps, "Trim & strip blanks"))
            self.assertEqual(len(mgr.get_all_pipelines()), base_count + 1)

            reloaded = PipelineManager(file_path=f)
            self.assertEqual(len(reloaded.get_all_pipelines()), base_count + 1)

            self.assertTrue(reloaded.remove_pipeline("My Cleanup"))
            self.assertEqual(len(reloaded.get_all_pipelines()), base_count)

    def test_pipeline_dialog_instantiation(self):
        with tempfile.TemporaryDirectory() as td:
            mgr = PipelineManager(file_path=Path(td) / "pipelines.json")
            dlg = PipelineDialog(pipeline_manager=mgr)
            self.assertEqual(dlg.pipeline_list.count(), len(BUILTIN_PIPELINES))
            self.assertGreater(dlg.steps_list.count(), 0)
            dlg.close()


if __name__ == "__main__":
    unittest.main()
