"""Synthetic fixture checks; none of these are investment-performance tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.make_demo_data import (
    DATA_FILES, KIND, MARKER, ROOT, make_inputs, run_demo, sha256,
    verify_inputs, write_inputs,
)
from src.ds_baseline import form_portfolios, monthly_panel


class SyntheticDemoTests(unittest.TestCase):
    def test_packaged_sample_is_unchanged_and_matches_the_generator(self):
        sample = ROOT / "data/sample"
        before = {name: (sha256(sample / name), (sample / name).stat().st_mtime_ns)
                  for name in (*DATA_FILES, MARKER)}
        manifest = verify_inputs(sample)
        generated = make_inputs(manifest["stocks"], manifest["holding_months"], manifest["seed"])
        for filename, expected in zip(DATA_FILES, generated):
            pd.testing.assert_frame_equal(pd.read_parquet(sample / filename), expected)
        after = {name: (sha256(sample / name), (sample / name).stat().st_mtime_ns)
                 for name in (*DATA_FILES, MARKER)}
        self.assertEqual(before, after)

    def test_corrupt_input_is_rejected_before_running_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            write_inputs(data, stocks=40, holding_months=3, seed=12)
            with (data / "close.parquet").open("ab") as stream:
                stream.write(b"unexpected change")
            with patch("scripts.make_demo_data.subprocess.run") as process:
                with self.assertRaisesRegex(ValueError, "integrity check failed"):
                    run_demo(data, Path(directory) / "out")
                process.assert_not_called()
            self.assertFalse((Path(directory) / "out").exists())

    def test_demo_never_overwrites_unmarked_research_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            data, out = Path(directory) / "data", Path(directory) / "research"
            write_inputs(data, stocks=40, holding_months=3, seed=12)
            out.mkdir()
            report = out / "RESULTS.md"
            report.write_text("Existing research results")
            with patch("scripts.make_demo_data.subprocess.run") as process:
                with self.assertRaisesRegex(ValueError, "not marked as a synthetic demo"):
                    run_demo(data, out)
                process.assert_not_called()
            self.assertEqual(report.read_text(), "Existing research results")

    def test_seed_repeats_exact_frames_and_different_seed_changes_prices(self):
        first = make_inputs(stocks=40, holding_months=3, seed=12)
        second = make_inputs(stocks=40, holding_months=3, seed=12)
        for left, right in zip(first, second):
            pd.testing.assert_frame_equal(left, right)
        other = make_inputs(stocks=40, holding_months=3, seed=13)
        self.assertFalse(first[0]["S_DQ_CLOSE"].equals(other[0]["S_DQ_CLOSE"]))

    def test_identifiers_and_marker_unambiguously_synthetic(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_inputs(directory, stocks=40, holding_months=3, seed=12)
            self.assertEqual(manifest["dataset_kind"], KIND)
            self.assertEqual(manifest["rows_per_input"], 40 * 5)
            self.assertEqual(json.loads((Path(directory) / MARKER).read_text()), manifest)
            close = pd.read_parquet(Path(directory) / "close.parquet")
            self.assertTrue(close["S_INFO_WINDCODE"].str.fullmatch(r"DEMO\d{6}\.SYN").all())
            repeated = write_inputs(directory, stocks=40, holding_months=3, seed=12)
            self.assertEqual(manifest["source_sha256"], repeated["source_sha256"])

    def test_nonempty_unmarked_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "close.parquet"
            original.write_bytes(b"existing user data")
            with self.assertRaisesRegex(ValueError, "not marked as synthetic"):
                write_inputs(directory, stocks=40, holding_months=3, seed=12)
            self.assertEqual(original.read_bytes(), b"existing user data")

    def test_fixture_populates_all_baseline_cells_while_preserving_ties(self):
        inputs = make_inputs(stocks=2000, holding_months=3, seed=12)
        panel, _ = monthly_panel(*inputs)
        members, returns, _ = form_portfolios(panel)
        self.assertEqual(returns["holding_month"].nunique(), 3)
        self.assertEqual(len(returns), 3 * 5 * 10 * 2)
        self.assertTrue(returns["status"].eq("complete").all())
        self.assertGreaterEqual(int(returns["n_formed"].min()), 20)
        self.assertTrue(np.isfinite(returns["ret"]).all())
        pair = members[members["stock"].isin(["DEMO000001.SYN", "DEMO000002.SYN"])]
        tied = pair.groupby("formation_month")[["ret", "ds", "ds_bin", "ret_bin"]].nunique()
        self.assertTrue(tied.eq(1).all().all())
        # Raw price ratios remain bounded by the declared synthetic model.
        self.assertTrue(panel["ret"].dropna().abs().between(0.005 - 1e-12, 0.08 + 1e-12).all())


if __name__ == "__main__":
    unittest.main()
