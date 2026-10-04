"""Small, independent examples for timing, portfolio arithmetic, and inference."""
import math
import unittest

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.ds_baseline import (
    assign_quantiles,
    form_portfolios,
    hac_mean,
    monthly_panel,
    summarize,
)


def raw_inputs(rows):
    """Rows are (stock, date, unadjusted close); all adjustment factors are 1."""
    close = pd.DataFrame(rows, columns=["S_INFO_WINDCODE", "TRADE_DT", "S_DQ_CLOSE"])
    close["S_DQ_ADJFACTOR"] = 1.0
    value = close[["S_INFO_WINDCODE", "TRADE_DT"]].copy()
    value["S_VAL_MV"] = 100.0
    industry = close[["S_INFO_WINDCODE", "TRADE_DT"]].rename(
        columns={"S_INFO_WINDCODE": "wind_code", "TRADE_DT": "date"}
    )
    industry["ind"] = "industry"
    return close, value, industry


def simple_panel():
    records = []
    stocks = ["A", "B", "C", "D"]
    for month, returns, caps in [
        ("2020-01", [-0.2, -0.1, 0.1, 0.2], [1.0, 2.0, 3.0, 4.0]),
        ("2020-02", [2.0, -0.5, 0.0, 0.1], [1000.0, 1.0, 1.0, 1.0]),
        ("2020-03", [0.03, 0.01, 0.02, -0.01], [1.0, 2.0, 3.0, 4.0]),
    ]:
        for stock, ret, cap in zip(stocks, returns, caps):
            records.append({"stock": stock, "month": pd.Period(month, "M"),
                            "price": 100.0, "ret": ret, "cap": cap,
                            "industry": "industry"})
    return pd.DataFrame(records)


def january(frame):
    return frame.loc[frame["formation_month"].eq(pd.Period("2020-01", "M"))]


class MonthlyPanelTests(unittest.TestCase):
    def test_return_uses_previous_month_end(self):
        inputs = raw_inputs([("A", "2020-01-31", 100.0),
                             ("A", "2020-02-03", 110.0),
                             ("A", "2020-02-28", 121.0)])
        panel, _ = monthly_panel(*inputs)
        self.assertAlmostEqual(panel.iloc[-1]["ret"], 0.21)
        self.assertTrue(pd.isna(panel.iloc[0]["ret"]))

    def test_calendar_gap_never_becomes_multimonth_return(self):
        inputs = raw_inputs([("A", "2020-01-31", 100.0),
                             ("A", "2020-03-31", 133.0),
                             ("B", "2020-01-31", 100.0),
                             ("B", "2020-02-28", 110.0),
                             ("B", "2020-03-31", 121.0)])
        panel, _ = monthly_panel(*inputs)
        row = panel.loc[panel["stock"].eq("A") & panel["month"].eq(pd.Period("2020-03", "M"))].iloc[0]
        self.assertTrue(pd.isna(row["ret"]))

    def test_stale_stock_price_does_not_replace_market_endpoint(self):
        inputs = raw_inputs([("A", "2020-01-31", 100.0),
                             ("A", "2020-02-27", 110.0),
                             ("B", "2020-01-31", 100.0),
                             ("B", "2020-02-28", 120.0)])
        panel, diagnostics = monthly_panel(*inputs)
        self.assertFalse(((panel["stock"] == "A") &
                          (panel["month"] == pd.Period("2020-02", "M"))).any())
        self.assertEqual(diagnostics["stock_months_with_any_daily_row"], 4)
        self.assertEqual(diagnostics["endpoint_stock_months"], 3)

    def test_missing_fundamentals_do_not_delete_price_returns(self):
        close, value, industry = raw_inputs([("A", "2020-01-31", 100.0),
                                            ("A", "2020-02-28", 121.0)])
        panel, _ = monthly_panel(close, value.iloc[:1], industry.iloc[:1])
        self.assertEqual(len(panel), 2)
        self.assertAlmostEqual(panel.iloc[-1]["ret"], 0.21)
        self.assertTrue(pd.isna(panel.iloc[-1]["cap"]))
        self.assertTrue(pd.isna(panel.iloc[-1]["industry"]))

    def test_duplicate_stock_date_is_rejected(self):
        inputs = raw_inputs([("A", "2020-01-31", 100.0),
                             ("A", "2020-01-31", 100.0)])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            monthly_panel(*inputs)


class QuantileTests(unittest.TestCase):
    def test_ties_preserved_with_empty_nominal_bins(self):
        result = assign_quantiles(pd.Series([0.0, 1.0, 1.0, 1.0, 2.0]), 5)
        self.assertEqual(result.tolist(), [1, 4, 4, 4, 5])
        self.assertEqual(assign_quantiles(pd.Series([1.0] * 10), 5).tolist(), [5] * 10)

    def test_quantiles_are_permutation_invariant(self):
        series = pd.Series([0.0, 1.0, 1.0, 1.0, 2.0], index=list("ABCDE"))
        expected = assign_quantiles(series, 5)
        actual = assign_quantiles(series.sample(frac=1, random_state=4), 5)
        pd.testing.assert_series_equal(actual.sort_index(), expected.sort_index())

    def test_nonfinite_values_are_not_ranked(self):
        result = assign_quantiles(pd.Series([0.0, 1.0, np.nan, np.inf, -np.inf]), 2)
        self.assertEqual(result.iloc[:2].tolist(), [1, 2])
        self.assertTrue(result.iloc[2:].isna().all())


class PortfolioTests(unittest.TestCase):
    def test_raw_holding_returns_and_formation_cap_weights(self):
        members, returns, _ = form_portfolios(simple_panel(), ds_bins=1, ret_bins=1, min_cell=4)
        formed = january(members).set_index("stock")
        self.assertAlmostEqual(formed.loc["A", "peer_ret"], (0.2 + 0.1 - 0.1) / 3)
        self.assertEqual(formed.loc["A", "peer_count"], 3)
        self.assertTrue(formed["ds"].eq(1.0).all())
        np.testing.assert_allclose(formed.loc[list("ABCD"), "weight_value"], [0.1, 0.2, 0.3, 0.4])
        result = january(returns).set_index("weighting")
        self.assertAlmostEqual(result.loc["equal", "ret"], (2.0 - 0.5 + 0.0 + 0.1) / 4)
        self.assertAlmostEqual(result.loc["value", "ret"], (2.0 * 1 - 0.5 * 2 + 0.0 * 3 + 0.1 * 4) / 10)
        self.assertTrue(result["status"].eq("complete").all())

    def test_future_missingness_does_not_change_formation(self):
        original = simple_panel()
        changed = original.loc[~(original["stock"].eq("A") &
                                 original["month"].eq(pd.Period("2020-02", "M")))].copy()
        first, _, _ = form_portfolios(original, ds_bins=5, ret_bins=2, min_cell=1)
        second, _, _ = form_portfolios(changed, ds_bins=5, ret_bins=2, min_cell=1)
        columns = ["stock", "ret", "ds", "peer_ret", "peer_count", "ds_bin", "ret_bin", "cap", "weight_equal", "weight_value"]
        pd.testing.assert_frame_equal(january(first)[columns].reset_index(drop=True),
                                      january(second)[columns].reset_index(drop=True))
        missing = january(second).set_index("stock").loc["A"]
        self.assertTrue(pd.isna(missing["future_ret"]))
        self.assertEqual(missing["holding_month"], pd.Period("2020-02", "M"))

    def test_unknown_holding_blocks_primary_without_reweighting(self):
        panel = simple_panel()
        panel.loc[panel["stock"].eq("A") & panel["month"].eq(pd.Period("2020-02", "M")), "ret"] = np.nan
        members, returns, _ = form_portfolios(panel, ds_bins=1, ret_bins=1, min_cell=4)
        result = january(returns).set_index("weighting")
        self.assertTrue(result["ret"].isna().all())
        self.assertTrue(result["status"].eq("missing_holding_return").all())
        self.assertTrue(result["n_formed"].eq(4).all())
        self.assertTrue(result["n_observed"].eq(3).all())
        self.assertAlmostEqual(result.loc["equal", "observed_weight"], 0.75)
        self.assertAlmostEqual(result.loc["value", "observed_weight"], 0.9)
        self.assertAlmostEqual(result.loc["equal", "observed_only_ret"], (-0.5 + 0 + 0.1) / 3)
        self.assertAlmostEqual(result.loc["value", "observed_only_ret"], (-0.5 * 2 + 0 * 3 + 0.1 * 4) / 9)
        self.assertAlmostEqual(january(members)["weight_value"].sum(), 1.0)

    def test_minimum_count_applies_to_final_cell(self):
        _, returns, _ = form_portfolios(simple_panel(), ds_bins=1, ret_bins=2, min_cell=3)
        result = january(returns)
        self.assertTrue(result["n_formed"].eq(2).all())
        self.assertTrue(result["status"].eq("below_minimum").all())
        self.assertTrue(result["ret"].isna().all())

    def test_exact_ds_boundary_is_not_split_and_empty_cells_visible(self):
        members, returns, _ = form_portfolios(simple_panel(), ds_bins=5, ret_bins=1, min_cell=1)
        self.assertTrue(january(members)["ds_bin"].eq(5).all())
        empty = january(returns).loc[lambda frame: frame["ds_bin"].lt(5)]
        self.assertEqual(len(empty), 8)
        self.assertTrue(empty["status"].eq("empty").all())
        self.assertTrue(empty["ret"].isna().all())

    def test_all_zero_returns_have_undefined_ds(self):
        panel = simple_panel()
        panel["ret"] = 0.0
        with self.assertRaisesRegex(ValueError, "No valid DS"):
            form_portfolios(panel, ds_bins=1, ret_bins=1, min_cell=1)


class InferenceTests(unittest.TestCase):
    def test_hac_matches_analytic_examples(self):
        zero = hac_mean([1.0, 2.0, 3.0, 4.0], lags=0)
        one = hac_mean([1.0, 2.0, 3.0, 4.0], lags=1)
        self.assertAlmostEqual(zero["mean"], 2.5)
        self.assertAlmostEqual(zero["se"], math.sqrt(5 / 16))
        self.assertAlmostEqual(one["se"], 0.625)

    def test_hac_matches_statsmodels_for_complete_series(self):
        values = np.array([0.02, -0.01, 0.04, 0.03, -0.05, 0.0, 0.06, -0.02, 0.01, 0.07])
        model = sm.OLS(values, np.ones((len(values), 1))).fit(
            cov_type="HAC", cov_kwds={"maxlags": 3, "use_correction": False})
        result = hac_mean(values, lags=3)
        self.assertAlmostEqual(result["mean"], model.params[0])
        self.assertAlmostEqual(result["se"], model.bse[0])
        self.assertAlmostEqual(result["t"], model.tvalues[0])
        np.testing.assert_allclose([result["ci_low"], result["ci_high"]], model.conf_int()[0])

    def test_missing_calendar_month_is_not_compressed(self):
        result = hac_mean([1.0, np.nan, 3.0], lags=1)
        self.assertEqual(result["n"], 2)
        self.assertAlmostEqual(result["mean"], 2.0)
        self.assertAlmostEqual(result["se"], math.sqrt(2 / 4))
        self.assertNotAlmostEqual(result["se"], hac_mean([1.0, 3.0], lags=1)["se"])

    def test_empty_singleton_and_constant_series_are_explicit(self):
        self.assertEqual(hac_mean([np.nan])["n"], 0)
        self.assertTrue(math.isnan(hac_mean([np.nan])["mean"]))
        self.assertTrue(math.isnan(hac_mean([2.0])["se"]))
        self.assertEqual(hac_mean([2.0, 2.0, 2.0])["se"], 0.0)
        self.assertTrue(math.isnan(hac_mean([2.0, 2.0, 2.0])["t"]))

    def test_interaction_uses_matched_month_spreads(self):
        rows = []
        for month, low, high in zip(pd.period_range("2020-01", "2020-03", freq="M"),
                                    [1.0, 5.0, 3.0], [0.5, np.nan, 2.0]):
            for ds, winner in [(1, low), (2, high)]:
                for rb, ret in [(1, 0.0), (2, winner)]:
                    rows.append({"holding_month": month, "weighting": "equal",
                                 "ds_bin": ds, "ret_bin": rb, "ret": ret})
        _, spreads, monthly = summarize(pd.DataFrame(rows), lags=1)
        interaction = spreads.set_index("series").loc["LowDS_minus_HighDS"]
        self.assertEqual(interaction["n"], 2)
        self.assertAlmostEqual(interaction["mean"], 0.75)
        values = monthly.loc[monthly["series"].eq("LowDS_minus_HighDS"), "ret"]
        np.testing.assert_allclose(values.to_numpy(), [0.5, np.nan, 1.0], equal_nan=True)


if __name__ == "__main__":
    unittest.main()
