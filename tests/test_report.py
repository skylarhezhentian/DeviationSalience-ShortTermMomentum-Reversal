"""Regressions for publishing a report after optional inputs disappear."""
import tempfile
import unittest
from pathlib import Path

from scripts.build_research_report import copy_aggregate_tables


class ReportTablesTests(unittest.TestCase):
    def test_rebuild_without_rf_removes_stale_tables_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, tables = root / "source", root / "tables"
            source.mkdir()
            for name in ("spread_summary.csv", "regression_summary.csv", "rf_spread_summary.csv"):
                (source / name).write_text("mean,n\n0.01,24\n")
            self.assertTrue(copy_aggregate_tables(source, tables))
            (tables / "risk_free_sensitivity.csv").write_text("old result")
            (tables / "notes.txt").write_text("keep this")
            (source / "rf_spread_summary.csv").unlink()
            self.assertFalse(copy_aggregate_tables(source, tables))
            self.assertFalse((tables / "full/rf_spread_summary.csv").exists())
            self.assertFalse((tables / "risk_free_sensitivity.csv").exists())
            self.assertEqual((tables / "notes.txt").read_text(), "keep this")
            self.assertEqual((tables / "full/spread_summary.csv").read_bytes(),
                             (source / "spread_summary.csv").read_bytes())

    def test_missing_required_input_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, tables = root / "source", root / "tables"
            source.mkdir()
            (tables / "full").mkdir(parents=True)
            (source / "spread_summary.csv").write_text("new")
            (tables / "full/spread_summary.csv").write_text("old")
            with self.assertRaises(FileNotFoundError):
                copy_aggregate_tables(source, tables)
            self.assertEqual((tables / "full/spread_summary.csv").read_text(), "old")


if __name__ == "__main__":
    unittest.main()
