"""Synthetic fixture checks; none of these are investment-performance tests."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.make_demo_data import KIND, MARKER, make_inputs, write_inputs
from src.ds_baseline import form_portfolios, monthly_panel


class SyntheticDemoTests(unittest.TestCase):
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
