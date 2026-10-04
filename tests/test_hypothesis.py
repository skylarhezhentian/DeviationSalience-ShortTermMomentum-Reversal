"""Synthetic protocol tests; no proprietary inputs or network required."""
import unittest

import numpy as np
import pandas as pd

from src.ds_baseline import form_portfolios
from src.research import (aggregate_memberships, calendar_controls, fama_macbeth,
    regression_design, restrict_universe, rf_portfolios, spread_series,
    summarize_series, unconditional_portfolios)


def panel_fixture(n=40):
    rng = np.random.default_rng(25)
    rows = []
    for month in pd.period_range("2020-01", "2021-04", freq="M"):
        for stock in range(n):
            rows.append(dict(stock=f"{stock:06d}.SH" if stock else "000000.BJ", month=month,
                date=month.end_time.normalize(), ret=float(rng.normal(0.01, 0.08)),
                cap=float(stock + 1), industry="I"))
    return pd.DataFrame(rows)


class CalendarAndUniverseTests(unittest.TestCase):
    def test_restricted_next_month_cap_cannot_remove_holding_return(self):
        p = panel_fixture()
        month = pd.Period("2020-06", "M")
        stock = "000039.SH"
        p.loc[p.month.eq(month+1) & p.stock.eq(stock), "cap"] = 0.001
        restricted, _ = restrict_universe(p, "no_bj_no_bottom20cap")
        m, _, _ = form_portfolios(restricted, ds_bins=1, ret_bins=1, min_cell=1)
        row = m[m.formation_month.eq(month) & m.stock.eq(stock)].iloc[0]
        raw = p[p.month.eq(month+1) & p.stock.eq(stock)].ret.iloc[0]
        self.assertAlmostEqual(row.future_ret, raw)
        self.assertFalse(m[m.formation_month.eq(month+1)].stock.eq(stock).any())

    def test_universe_selection_is_formation_only_and_tie_preserving(self):
        p = panel_fixture()
        first, _ = restrict_universe(p, "no_bj_no_bottom20cap")
        month = pd.Period("2020-06", "M")
        p.loc[p.month.gt(month), ["cap", "ret"]] = 12345
        second, _ = restrict_universe(p, "no_bj_no_bottom20cap")
        pd.testing.assert_series_equal(first.loc[first.month.eq(month), "cap"], second.loc[second.month.eq(month), "cap"])
        p.loc[p.month.eq(month), "cap"] = 1
        tied, _ = restrict_universe(p, "no_bj_no_bottom20cap")
        self.assertEqual(tied.loc[tied.month.eq(month), "cap"].notna().sum(), 39)

    def test_controls_use_exact_calendar_and_exclude_future(self):
        p = panel_fixture(n=1)
        p["ret"] = np.arange(len(p)) / 100
        c = calendar_controls(p).set_index("month")
        month = pd.Period("2021-01", "M")
        expected = np.prod(1 + np.arange(1, 12) / 100) - 1
        self.assertAlmostEqual(c.loc[month, "momentum_12_2"], expected)
        self.assertAlmostEqual(c.loc[month, "monthly_volatility_12"], np.std(np.arange(1, 13) / 100, ddof=1))
        changed = p.copy()
        changed.loc[changed.month.gt(month), "ret"] = 1000
        pd.testing.assert_series_equal(c.loc[month], calendar_controls(changed).set_index("month").loc[month])
        missing = p[~p.month.eq(pd.Period("2020-08", "M"))]
        gap = calendar_controls(missing).set_index("month")
        self.assertTrue(np.isnan(gap.loc[month, "momentum_12_2"]))
        self.assertTrue(np.isnan(gap.loc[month, "monthly_volatility_12"]))


class PortfolioTests(unittest.TestCase):
    def test_unconditional_benchmark_uses_same_formed_cohort(self):
        p = panel_fixture()
        members, returns, _ = form_portfolios(p, ds_bins=2, ret_bins=2, min_cell=1)
        month = members.formation_month.min()
        u = unconditional_portfolios(members, [month], 2, 1)
        formed = members[members.formation_month.eq(month)].sort_values("ret")
        losers, winners = formed.iloc[:20], formed.iloc[20:]
        equal = u[u.weighting.eq("equal")].set_index("ret_bin")
        self.assertEqual(equal.n_formed.sum(), len(formed))
        self.assertAlmostEqual(equal.loc[1, "ret"], losers.future_ret.mean())
        self.assertAlmostEqual(equal.loc[2, "ret"], winners.future_ret.mean())
        value = u[u.weighting.eq("value")].set_index("ret_bin")
        self.assertAlmostEqual(value.loc[1, "ret"], np.average(losers.future_ret, weights=losers.cap))

    def test_common_month_contrasts_do_not_subtract_mismatched_means(self):
        records, unconditional = [], []
        months = pd.period_range("2020-01", periods=3, freq="M")
        for month, low, high, bench in zip(months, [1, 9, 5], [0.5, np.nan, 2], [0.1, 8, np.nan]):
            for w in ("equal", "value"):
                for ds, winner in ((1, low), (2, high)):
                    for rb, ret in ((1, 0), (2, winner)):
                        records.append(dict(holding_month=month,weighting=w,ds_bin=ds,ret_bin=rb,ret=ret))
                for rb, ret in ((1, 0), (2, bench)):
                    unconditional.append(dict(holding_month=month,weighting=w,ds_bin=1,ret_bin=rb,ret=ret))
        result = spread_series(pd.DataFrame(records), pd.DataFrame(unconditional), 2, 2, 1, "complete")
        result = result[result.weighting.eq("equal")].pivot(index="holding_month",columns="series",values="ret")
        np.testing.assert_allclose(result.lowDS_minus_highDS, [0.5,np.nan,3], equal_nan=True)
        np.testing.assert_allclose(result.common_lowDS_WML, [1,np.nan,np.nan], equal_nan=True)
        self.assertAlmostEqual(result.common_lowDS_minus_unconditional.iloc[0], 0.9)

    def test_missing_scenarios_retain_original_weights_and_cell_minimum(self):
        month = pd.Period("2020-01","M")
        m = pd.DataFrame(dict(stock=["A","B","C","D"], formation_month=[month]*4,
            ds_bin=[1]*4,ret_bin=[1,1,2,2],future_ret=[0.,0.,0.1,np.nan],
            weight_equal=[0.5]*4,weight_value=[0.5,0.5,0.2,0.8]))
        r = aggregate_memberships(m,[month],2,1,2)
        def wml(policy,weight="equal",minimum=2):
            result = spread_series(r,r,1,2,minimum,policy)
            return result[result.weighting.eq(weight)&result.series.eq("unconditional_WML")].ret.iloc[0]
        self.assertTrue(np.isnan(wml("complete")))
        self.assertAlmostEqual(wml("observed_only_selected_sample"),0.1)
        self.assertAlmostEqual(wml("unknown_return_zero_scenario"),0.05)
        self.assertAlmostEqual(wml("unknown_return_loss100_scenario"),-0.45)
        self.assertAlmostEqual(wml("unknown_return_zero_scenario","value"),0.02)
        self.assertAlmostEqual(wml("unknown_return_loss100_scenario","value"),-0.78)
        self.assertTrue(np.isnan(wml("unknown_return_loss100_scenario",minimum=3)))

    def test_rf_formula_and_raw_holding_returns(self):
        p = panel_fixture()
        rf = pd.DataFrame({"month": sorted(p.month.unique()), "rf_monthly_proxy":0.02})
        spec = dict(min_peers=3,ds_bins=2,ret_bins=2,min_cell=1)
        m, _, _ = rf_portfolios(p, rf, spec)
        expected = abs(m.ret-m.peer_ret)/(abs(m.ret-0.02)+abs(m.peer_ret-0.02))
        np.testing.assert_allclose(m.ds, expected, atol=1e-12)
        raw = p[["stock","month","ret"]].rename(columns={"month":"holding_month","ret":"raw"})
        joined = m.merge(raw,on=["stock","holding_month"])
        np.testing.assert_allclose(joined.future_ret, joined.raw)

    def test_rf_diagnostics_use_restored_raw_outcomes_and_available_window(self):
        p = panel_fixture()
        cutoff = pd.Period("2020-06","M")
        rf = pd.DataFrame({"month": sorted(p[p.month.le(cutoff)].month.unique()), "rf_monthly_proxy":0.002})
        m,r,diag = rf_portfolios(p,rf,dict(min_peers=3,ds_bins=1,ret_bins=1,min_cell=1))
        self.assertEqual(diag["formation_end"],"2020-06")
        self.assertEqual(diag["holding_end"],"2020-07")
        self.assertEqual(diag["unknown_holding_returns"],0)
        self.assertTrue(m.future_ret.notna().all())
        self.assertEqual(sum(diag["portfolio_status_counts_per_weighting"].values()),6)

    def test_rf_boundary_uses_excess_not_raw_sign(self):
        p = panel_fixture(n=4)
        for stock, ret in zip(p.stock.unique(), [0.001,-0.001,-0.001,-0.001]):
            p.loc[p.stock.eq(stock), "ret"] = ret
        rf = pd.DataFrame({"month": sorted(p.month.unique()), "rf_monthly_proxy":0.002})
        m,_,_ = rf_portfolios(p,rf,dict(min_peers=3,ds_bins=1,ret_bins=1,min_cell=1))
        # Stock raw return > 0 and peer raw return < 0, yet both excess
        # returns are negative; DS must be 0.5 rather than a forced one.
        stock = m[m.stock.eq(p.stock.iloc[0])]
        np.testing.assert_allclose(stock.ds,0.5,atol=1e-12)


class RegressionTests(unittest.TestCase):
    def test_predictor_scaling_cannot_depend_on_future_availability(self):
        p = pd.DataFrame(dict(ret=[-0.2,-0.1,0.1,0.4],ds=[0.1,0.3,0.8,1.0],future_ret=[0.1,np.nan,0.2,0.3]))
        x1, _, scale1 = regression_design(p,["ret","ds"])
        p.future_ret = [np.nan,0.3,np.nan,np.nan]
        x2, _, scale2 = regression_design(p,["ret","ds"])
        pd.testing.assert_frame_equal(x1,x2)
        pd.testing.assert_frame_equal(scale1,scale2)
        np.testing.assert_allclose(x1.ret_x_ds,x1.z_ret*x1.z_ds)

    def test_regression_recovers_known_interaction_and_rejects_rank_failure(self):
        rng = np.random.default_rng(100)
        month = pd.Period("2020-01","M")
        m = pd.DataFrame(dict(stock=[str(i) for i in range(150)],formation_month=month,
            holding_month=month+1,ret=rng.normal(size=150),ds=rng.uniform(size=150)))
        x,_,_ = regression_design(m,["ret","ds"])
        m["future_ret"] = x.to_numpy() @ np.array([0.01,-0.03,0.02,-0.04])
        controls = pd.DataFrame(dict(stock=m.stock,month=month,logcap=np.nan,momentum_12_2=np.nan,monthly_volatility_12=np.nan))
        coef, diag, _ = fama_macbeth(m,controls,[month,month+1])
        fitted = coef[coef.holding_month.eq(month+1)&coef.model.eq("uncontrolled")].set_index("coefficient").estimate
        np.testing.assert_allclose(fitted.loc[["intercept","z_ret","z_ds","ret_x_ds"]], [0.01,-0.03,0.02,-0.04],atol=1e-12)
        self.assertEqual(diag.iloc[0].status,"ok")
        self.assertTrue(coef[coef.holding_month.eq(month+2)].estimate.isna().all())
        m["ds"] = m.ret
        _,diag,_ = fama_macbeth(m,controls,[month])
        self.assertEqual(diag.iloc[0].status,"rank_deficient")

    def test_hac_summary_keeps_missing_months_and_period_coverage(self):
        monthly = pd.DataFrame(dict(holding_month=pd.PeriodIndex(["2020-01","2020-03"],freq="M"),series="x",ret=[1.,3.]))
        out = summarize_series(monthly,[dict(name="full",start="2020-01",end="2020-03")],[1],["series"])
        self.assertEqual(out.iloc[0].n,2)
        self.assertEqual(out.iloc[0].calendar_months,3)
        self.assertAlmostEqual(out.iloc[0].se,np.sqrt(0.5))


if __name__ == "__main__":
    unittest.main()
