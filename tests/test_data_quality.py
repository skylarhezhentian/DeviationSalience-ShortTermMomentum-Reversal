import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.audit_data_quality import (
    MISSING_COLUMNS, RF_SERIES, ROOT, audit_missing_holdings, classify_missing,
    monthly_components, normalize_rf, prepare_rf,
)


class MissingHoldingsTests(unittest.TestCase):
    def classify(self, dates):
        member = {"stock": "A", "formation_month": "2020-01", "holding_month": "2020-02",
                  "weight_equal": 0.25, "weight_value": 0.1, "ds_bin": 1, "ret_bin": 1}
        daily = pd.DataFrame({"date": pd.to_datetime(dates)})
        return classify_missing(member, daily, {"2020-02": "2020-02-28"})

    def test_terminal_is_observational_not_delisting(self):
        result = self.classify(["2020-01-31", "2020-02-20"])
        self.assertEqual(result["classification"], "terminal_disappearance_in_extract")
        self.assertEqual(result["holding_month_daily_rows"], 1)
        self.assertFalse(result["cause_verified"])

    def test_intramonth_gap_and_later_resumption(self):
        result = self.classify(["2020-01-31", "2020-02-20", "2020-03-04"])
        self.assertEqual(result["classification"], "intramonth_endpoint_gap_later_resumption")
        self.assertEqual(result["first_observation_after_endpoint"], "2020-03-04")

    def test_whole_month_gap_and_endpoint_inconsistency(self):
        self.assertEqual(self.classify(["2020-01-31", "2020-03-04"])["classification"], "whole_month_gap_later_resumption")
        self.assertEqual(self.classify(["2020-01-31", "2020-02-28"])["classification"], "endpoint_present_requires_investigation")

    def test_fully_observed_holdings_produce_readable_empty_audit(self):
        members = pd.DataFrame({"stock": ["A"], "future_ret": [0.05]})
        raw = pd.DataFrame({"stock": ["A"], "date": pd.to_datetime(["2020-02-28"])})
        audit = audit_missing_holdings(members, raw, {"2020-02": "2020-02-28"})
        self.assertTrue(audit.empty)
        self.assertEqual(list(audit), MISSING_COLUMNS + ["verified_event", "event_source_url"])
        self.assertEqual(audit.classification.value_counts().to_dict(), {})
        self.assertEqual(int(audit.holding_month_daily_rows.gt(0).sum()), 0)
        self.assertEqual(int(audit.cause_verified.sum()), 0)
        self.assertEqual(list(pd.read_csv(io.StringIO(audit.to_csv(index=False)))), list(audit))


class ComponentTests(unittest.TestCase):
    def test_split_factor_offsets_raw_price_change(self):
        raw = pd.DataFrame({"stock": ["A", "A", "A"], "date": pd.to_datetime(["2020-01-31", "2020-02-28", "2020-04-30"]),
                            "close": [100.0, 50.0, 60.0], "factor": [1.0, 2.0, 2.0]})
        result = monthly_components(raw, {"2020-01": "2020-01-31", "2020-02": "2020-02-28", "2020-04": "2020-04-30"})
        self.assertAlmostEqual(result.iloc[1].raw_close_return, -0.5)
        self.assertAlmostEqual(result.iloc[1].adjustment_factor_ratio, 2.0)
        self.assertAlmostEqual(result.iloc[1].adjusted_return, 0.0)
        self.assertTrue(pd.isna(result.iloc[2].adjusted_return))


class RateAdapterTests(unittest.TestCase):
    def test_unit_conversion_and_missing_months_not_filled(self):
        raw = pd.DataFrame({"observation_date": ["2021-01-01", "2021-02-01", "2021-04-01"], RF_SERIES: [3.0, ".", 1.2]})
        result = normalize_rf(raw)
        self.assertEqual(result.month.tolist(), ["2021-01", "2021-04"])
        np.testing.assert_allclose(result.rf_monthly_proxy, [0.0025, 0.001])

    def test_duplicate_months_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            normalize_rf(pd.DataFrame({"observation_date": ["2021-01-01", "2021-01-20"], RF_SERIES: [3.0, 4.0]}))

    def test_malformed_rate_and_schema_rejected(self):
        with self.assertRaises(ValueError):
            normalize_rf(pd.DataFrame({"observation_date": ["2021-01-01"], RF_SERIES: ["oops"]}))
        with self.assertRaises(ValueError):
            normalize_rf(pd.DataFrame({"date": ["2021-01-01"], "rate": [1]}))


class RateImportTests(unittest.TestCase):
    snapshot = f"observation_date,{RF_SERIES}\n2021-01-01,3.0\n".encode()

    def test_external_snapshot_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, out = base / "snapshot.csv", base / "audit"
            source.write_bytes(self.snapshot)
            info = prepare_rf(out, source)
            self.assertTrue(info["available"])
            self.assertEqual(source.read_bytes(), self.snapshot)
            self.assertAlmostEqual(pd.read_csv(out / "rf_proxy_monthly.csv").rf_monthly_proxy.iloc[0], 0.0025)
            self.assertFalse((out / f"fred_{RF_SERIES}.csv").exists())

    def test_unavailable_source_removes_stale_normalized_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            normalized = out / "rf_proxy_monthly.csv"
            normalized.write_text("stale normalized rates")
            (out / "rf_source.json").write_text('{"available": true}')
            info = prepare_rf(out)
            self.assertFalse(info["available"])
            self.assertFalse(normalized.exists())
            self.assertFalse(json.loads((out / "rf_source.json").read_text())["available"])

    def test_failed_fetch_preserves_snapshot_and_invalidates_normalized_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            raw, normalized = out / f"fred_{RF_SERIES}.csv", out / "rf_proxy_monthly.csv"
            raw.write_bytes(self.snapshot)
            prepare_rf(out)
            with patch("scripts.audit_data_quality.urlopen", return_value=io.BytesIO(b"bad,schema\n1,2\n")):
                with self.assertRaises(ValueError):
                    prepare_rf(out, fetch=True)
            self.assertEqual(raw.read_bytes(), self.snapshot)
            self.assertFalse(normalized.exists())
            metadata = json.loads((out / "rf_source.json").read_text())
            self.assertFalse(metadata["available"])
            self.assertEqual(metadata["status"], "import_failed")

    def test_successful_fetch_writes_only_owned_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            with patch("scripts.audit_data_quality.urlopen", return_value=io.BytesIO(self.snapshot)):
                info = prepare_rf(out, fetch=True)
            self.assertTrue(info["available"])
            self.assertEqual((out / f"fred_{RF_SERIES}.csv").read_bytes(), self.snapshot)
            self.assertEqual(len(list(out.iterdir())), 3)

    def test_generated_output_cannot_be_used_as_input(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            source = out / "rf_proxy_monthly.csv"
            source.write_bytes(self.snapshot)
            with self.assertRaisesRegex(ValueError, "separate"):
                prepare_rf(out, source)
            self.assertEqual(source.read_bytes(), self.snapshot)

    def test_mutually_exclusive_cli_options_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, out = base / "snapshot.csv", base / "audit"
            source.write_bytes(self.snapshot)
            run = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_data_quality.py"),
                                  "--data-dir", str(base), "--output-dir", str(out),
                                  "--rf-csv", str(source), "--fetch-rf"], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("not allowed", run.stderr)
            self.assertEqual(source.read_bytes(), self.snapshot)
            self.assertFalse(out.exists())

    def test_missing_explicit_source_fails_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            out = base / "audit"
            run = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_data_quality.py"),
                                  "--data-dir", str(base), "--output-dir", str(out),
                                  "--rf-csv", str(base / "missing.csv")], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("Rate source does not exist", run.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
