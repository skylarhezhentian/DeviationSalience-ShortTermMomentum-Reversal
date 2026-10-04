"""Configuration and output-lifecycle tests; no research data required."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from scripts.evaluate_hypothesis import (
    CORE_OUTPUTS, RF_OUTPUTS, ROOT, RUNNER_PATH, digest,
    validate_config, validate_output_directory, write_outputs,
)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "configs/robustness.json").read_text())

    def test_rf_baseline_is_identified_by_name_after_reordering(self):
        self.config["specifications"].reverse()
        baseline = validate_config(self.config)
        self.assertEqual(baseline["name"], "baseline")
        self.assertIsNot(baseline, self.config["specifications"][0])

    def test_unsupported_declared_methods_are_rejected(self):
        for field, value in (("controls", ["logcap"]), ("models", ["controls"]),
                             ("momentum_formation_lags", [1, 2, 3]),
                             ("volatility_formation_lags", [0, 1])):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config["regression"][field] = value
                with self.assertRaisesRegex(ValueError, "Unsupported regression"):
                    validate_config(config)
        self.config["weightings"] = ["equal"]
        with self.assertRaisesRegex(ValueError, "Unsupported weightings"):
            validate_config(self.config)

    def test_invalid_lags_counts_and_duplicate_specifications_fail(self):
        for field, value in (("ds_bins", 2.5), ("min_cell", 0), ("min_peers", True)):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config["specifications"][0][field] = value
                with self.assertRaisesRegex(ValueError, "must be an integer"):
                    validate_config(config)
        self.config["hac_lags"] = [-1, 3]
        with self.assertRaisesRegex(ValueError, "hac_lags must be an integer"):
            validate_config(self.config)
        self.config["hac_lags"] = [3, 6]
        self.config["specifications"].append(copy.deepcopy(self.config["specifications"][0]))
        with self.assertRaisesRegex(ValueError, "unique names"):
            validate_config(self.config)

    def test_primary_lag_and_periods_must_match_valid_configuration(self):
        self.config["primary_hac_lags"] = 12
        with self.assertRaisesRegex(ValueError, "must be included"):
            validate_config(self.config)
        self.config["primary_hac_lags"] = 6
        validate_config(self.config)
        self.config["periods"][0]["end"] = "2020-01"
        with self.assertRaisesRegex(ValueError, "Invalid period boundaries"):
            validate_config(self.config)


class OutputLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name) / "baseline"
        self.base.mkdir()
        self.out = self.base / "research"

    @staticmethod
    def tables(include_rf=False, value=1.0):
        names = (*CORE_OUTPUTS, *RF_OUTPUTS) if include_rf else CORE_OUTPUTS
        return {name: pd.DataFrame({"value": [value]}) for name in names}

    @staticmethod
    def manifest(include_rf=False):
        return {"code_sha256": {RUNNER_PATH: "synthetic-test"},
                "rf_sensitivity": {"status": "completed" if include_rf else "not_available"}}

    def test_unrelated_destination_and_baseline_paths_are_not_overwritten(self):
        self.out.mkdir()
        sentinel = self.out / "notes.txt"
        sentinel.write_text("keep me")
        with self.assertRaisesRegex(ValueError, "not a recognized research output"):
            write_outputs(self.base, self.out, self.tables(), self.manifest())
        self.assertEqual(sentinel.read_text(), "keep me")
        self.assertFalse((self.out / "run_manifest.json").exists())
        for path in (self.base, self.base.parent):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "cannot replace the baseline"):
                validate_output_directory(self.base, path)

    def test_rerun_without_rf_removes_only_stale_optional_files(self):
        write_outputs(self.base, self.out, self.tables(include_rf=True), self.manifest(include_rf=True))
        report = self.out / "notes.md"
        report.write_text("independent report")
        write_outputs(self.base, self.out, self.tables(value=2.0), self.manifest())
        self.assertFalse(any((self.out / name).exists() for name in RF_OUTPUTS))
        self.assertEqual(report.read_text(), "independent report")
        manifest = json.loads((self.out / "run_manifest.json").read_text())
        self.assertEqual(manifest["rf_sensitivity"]["status"], "not_available")
        self.assertEqual(set(manifest["output_sha256"]), set(CORE_OUTPUTS))
        for name, sha in manifest["output_sha256"].items():
            self.assertEqual(digest(self.out / name), sha)
            self.assertEqual(pd.read_csv(self.out / name).value.iloc[0], 2.0)

    def test_symlink_output_cannot_modify_a_baseline_file(self):
        write_outputs(self.base, self.out, self.tables(), self.manifest())
        protected = self.base / "original.csv"
        protected.write_text("original")
        target = self.out / CORE_OUTPUTS[0]
        target.unlink()
        target.symlink_to(protected)
        with self.assertRaisesRegex(ValueError, "non-regular output"):
            write_outputs(self.base, self.out, self.tables(value=2.0), self.manifest())
        self.assertEqual(protected.read_text(), "original")

    def test_serialization_failure_preserves_all_previous_outputs(self):
        write_outputs(self.base, self.out, self.tables(), self.manifest())
        before = {path.name: path.read_bytes() for path in self.out.iterdir()}
        with patch("scripts.evaluate_hypothesis.csv", side_effect=OSError("disk write failed")):
            with self.assertRaisesRegex(OSError, "disk write failed"):
                write_outputs(self.base, self.out, self.tables(value=2.0), self.manifest())
        after = {path.name: path.read_bytes() for path in self.out.iterdir()}
        self.assertEqual(before, after)

    def test_incomplete_output_bundle_is_rejected_before_writing(self):
        tables = self.tables()
        tables[RF_OUTPUTS[0]] = pd.DataFrame({"value": [1]})
        with self.assertRaisesRegex(ValueError, "written together"):
            write_outputs(self.base, self.out, tables, self.manifest(include_rf=True))
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
