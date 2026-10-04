import unittest

import numpy as np
import pandas as pd

from scripts.audit_data_quality import RF_SERIES, classify_missing, monthly_components, normalize_rf


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


if __name__ == "__main__":
    unittest.main()
