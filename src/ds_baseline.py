"""Monthly statistical portfolios; no raw-input writes or network access.

DS uses raw monthly returns, leave-one-out industry peers, and a zero-RF
proxy. This is an industry adaptation, not an exact paper replication.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


def _unique(frame, keys, name):
    if frame[keys].isna().any().any():
        raise ValueError(f"{name}: missing key")
    n = int(frame.duplicated(keys).sum())
    if n:
        raise ValueError(f"{name}: {n} duplicate keys {keys}")


def monthly_panel(close, value, industry):
    """Build one row per stock at each observed market month-end.

    A stock must have a price on the global last observed trading date of
    the month. Never substitute its earlier last price. Returns require an
    endpoint in the immediately preceding calendar month. Valuation and
    industry joins use only the formation endpoint date; missing future
    fundamentals cannot remove a future realized price return.
    """
    c = close.rename(columns={"TRADE_DT": "date", "S_INFO_WINDCODE": "stock"}).copy()
    c["date"] = pd.to_datetime(c["date"])
    _unique(c, ["date", "stock"], "close")
    c["month"] = c["date"].dt.to_period("M")
    calendar = c.groupby("month")["date"].max().sort_index()
    endpoint_mask = c["date"].eq(c["month"].map(calendar))
    endpoints = c.loc[endpoint_mask, ["stock", "month", "date", "S_DQ_CLOSE", "S_DQ_ADJFACTOR"]].copy()
    endpoints["price"] = endpoints["S_DQ_CLOSE"] * endpoints["S_DQ_ADJFACTOR"]
    good = (endpoints["S_DQ_CLOSE"] > 0) & (endpoints["S_DQ_ADJFACTOR"] > 0) & np.isfinite(endpoints["price"])
    invalid = int((~good).sum())
    endpoints.loc[~good, "price"] = np.nan
    endpoints = endpoints.drop(columns=["S_DQ_CLOSE", "S_DQ_ADJFACTOR"])
    prev = endpoints[["stock", "month", "price"]].copy()
    prev["month"] = prev["month"] + 1
    prev = prev.rename(columns={"price": "previous_price"})
    p = endpoints.merge(prev, on=["stock", "month"], how="left", validate="one_to_one")
    p["ret"] = p["price"] / p["previous_price"] - 1
    p.loc[~np.isfinite(p["ret"]), "ret"] = np.nan

    v = value.rename(columns={"TRADE_DT": "date", "S_INFO_WINDCODE": "stock", "S_VAL_MV": "cap"})
    v = v[["date", "stock", "cap"]].copy()
    v["date"] = pd.to_datetime(v["date"])
    v = v[v["date"].isin(calendar.values)]
    _unique(v, ["date", "stock"], "value endpoints")
    ind = industry.copy()
    if "date" not in ind.columns or "wind_code" not in ind.columns:
        ind = ind.reset_index()
    ind = ind.rename(columns={"wind_code": "stock", "ind": "industry"})[["date", "stock", "industry"]]
    ind["date"] = pd.to_datetime(ind["date"])
    ind = ind[ind["date"].isin(calendar.values)]
    _unique(ind, ["date", "stock"], "industry endpoints")
    p = p.merge(v, on=["date", "stock"], how="left", validate="one_to_one")
    p = p.merge(ind, on=["date", "stock"], how="left", validate="one_to_one")
    p = p.sort_values(["month", "stock"]).reset_index(drop=True)
    diagnostics = {
        "raw_price_rows": int(len(c)),
        "raw_stock_count": int(c["stock"].nunique()),
        "price_date_start": str(c["date"].min().date()),
        "price_date_end": str(c["date"].max().date()),
        "calendar_months": int(len(calendar)),
        "calendar": {str(k): str(v.date()) for k, v in calendar.items()},
        "stock_months_with_any_daily_row": int(c.groupby(["stock", "month"]).ngroups),
        "endpoint_stock_months": int(len(p)),
        "invalid_endpoint_prices": invalid,
        "valid_consecutive_month_returns": int(p["ret"].notna().sum()),
        "missing_or_nonpositive_endpoint_cap": int((~np.isfinite(p["cap"]) | (p["cap"] <= 0)).sum()),
        "missing_endpoint_industry": int(p["industry"].isna().sum()),
        "last_month_calendar_completeness": "not certified against an independent exchange calendar",
    }
    return p, diagnostics


def assign_quantiles(series, n_bins):
    """Tie-preserving right-end empirical-CDF groups; empty bins are allowed.

    Identical values always receive the same group, independent of row order.
    This can produce unequal groups, especially at DS=1. It intentionally
    does not force a nominal quintile to contain precisely 20% of stocks.
    """
    if n_bins < 1:
        raise ValueError("n_bins must be positive")
    s = pd.Series(series, copy=True)
    good = s.notna() & np.isfinite(s)
    out = pd.Series(pd.NA, index=s.index, dtype="Int64")
    if good.any():
        rank = s[good].rank(method="max")
        out.loc[good] = np.ceil(rank * n_bins / good.sum()).clip(1, n_bins).astype(int)
    return out


def form_portfolios(panel, min_peers=3, ds_bins=5, ret_bins=10, min_cell=20):
    """Form all memberships before looking at next-calendar-month returns.

    Primary portfolio return is unavailable if any holding return is unknown
    or the final cell has fewer than min_cell stocks. Observed-only returns
    are exported strictly as missingness diagnostics, never primary evidence.
    Formation cap weights are normalized once, without ex-post reweighting.
    """
    if min_peers < 1 or min_cell < 1:
        raise ValueError("min_peers and min_cell must be positive")
    p = panel.copy().sort_values(["month", "stock"]).reset_index(drop=True)
    _unique(p, ["stock", "month"], "monthly panel")
    eligible = np.isfinite(p["ret"]) & np.isfinite(p["cap"]) & (p["cap"] > 0) & p["industry"].notna()
    eligible &= p["industry"].astype(str).str.len().gt(0)
    eligible &= p["month"] < p["month"].max()
    e = p.loc[eligible].copy()
    if e.empty:
        raise ValueError("No eligible formation observations")
    groups = e.groupby(["month", "industry"])["ret"]
    e["peer_count"] = groups.transform("size") - 1
    e["peer_ret"] = (groups.transform("sum") - e["ret"]) / e["peer_count"].replace(0, np.nan)
    denom = e["ret"].abs() + e["peer_ret"].abs()
    e["ds"] = (e["ret"] - e["peer_ret"]).abs() / denom.where(denom > 0)
    # Enforce the analytic upper boundary, avoiding machine-roundoff pseudo-ties.
    e["ds"] = e["ds"].clip(0, 1)
    e.loc[e["ret"].mul(e["peer_ret"]) <= 0, "ds"] = np.where(
        denom[e["ret"].mul(e["peer_ret"]) <= 0] > 0, 1.0, np.nan)
    invalid_peer = e["peer_count"] < min_peers
    bad_ds = ~np.isfinite(e["ds"])
    all_formation_months = pd.period_range(e["month"].min(), p["month"].max() - 1, freq="M")
    m = e.loc[~invalid_peer & ~bad_ds].copy()
    if m.empty:
        raise ValueError("No valid DS formation observations")
    m["ds_bin"] = m.groupby("month", group_keys=False)["ds"].transform(lambda s: assign_quantiles(s, ds_bins)).astype(int)
    m["ret_bin"] = m.groupby(["month", "ds_bin"], group_keys=False)["ret"].transform(lambda s: assign_quantiles(s, ret_bins)).astype(int)
    m = m.rename(columns={"month": "formation_month"})
    m["holding_month"] = m["formation_month"] + 1
    cell = m.groupby(["formation_month", "ds_bin", "ret_bin"])
    m["weight_equal"] = 1 / cell["stock"].transform("size")
    m["weight_value"] = m["cap"] / cell["cap"].transform("sum")
    # The future join occurs only AFTER DS bins, return bins, and weights exist.
    future = p[["stock", "month", "ret"]].rename(columns={"month": "holding_month", "ret": "future_ret"})
    m = m.merge(future, on=["stock", "holding_month"], how="left", validate="one_to_one")
    observed = np.isfinite(m["future_ret"])
    m.loc[~observed, "future_ret"] = np.nan

    records = []
    grouped = dict(tuple(m.groupby(["formation_month", "ds_bin", "ret_bin"])))
    for month in all_formation_months:
        for ds in range(1, ds_bins + 1):
            for rb in range(1, ret_bins + 1):
                sub = grouped.get((month, ds, rb))
                for weighting in ("equal", "value"):
                    n = len(sub) if sub is not None else 0
                    obs = sub["future_ret"].notna() if n else pd.Series(dtype=bool)
                    n_obs = int(obs.sum())
                    weights = sub[f"weight_{weighting}"] if n else pd.Series(dtype=float)
                    obs_weight = float(weights[obs].sum()) if n else 0.0
                    partial = float((weights[obs] * sub.loc[obs, "future_ret"]).sum() / obs_weight) if obs_weight > 0 else np.nan
                    status = "empty" if n == 0 else "below_minimum" if n < min_cell else "missing_holding_return" if n_obs != n else "complete"
                    records.append({"formation_month": month, "holding_month": month + 1,
                                    "weighting": weighting, "ds_bin": ds, "ret_bin": rb,
                                    "n_formed": n, "n_observed": n_obs, "observed_weight": obs_weight,
                                    "ret": partial if status == "complete" else np.nan,
                                    "observed_only_ret": partial, "status": status})
    returns = pd.DataFrame(records)
    diagnostics = {
        "base_eligible_formation_rows": int(len(e)),
        "excluded_fewer_than_minimum_peers": int(invalid_peer.sum()),
        "undefined_ds_rows": int(bad_ds.sum()),
        "formed_stock_months": int(len(m)),
        "ds_exactly_one_rows": int(m["ds"].eq(1).sum()),
        "ds_exactly_one_fraction": float(m["ds"].eq(1).mean()),
        "unknown_holding_returns": int(m["future_ret"].isna().sum()),
        "portfolio_status_counts_per_weighting": returns[returns["weighting"] == "equal"]["status"].value_counts().to_dict(),
        "formation_start": str(all_formation_months.min()),
        "formation_end": str(all_formation_months.max()),
        "holding_start": str(all_formation_months.min() + 1),
        "holding_end": str(all_formation_months.max() + 1),
    }
    return m.sort_values(["formation_month", "ds_bin", "ret_bin", "stock"]).reset_index(drop=True), returns, diagnostics


def hac_mean(values, lags=3):
    """Mean with calendar-position Bartlett HAC, no finite-sample correction.

    Keep missing calendar months in the input. Their scores are zero and
    contribute no lagged product; observed count n normalizes the estimate.
    This estimates uncertainty for the observed-month mean, not a correction
    for nonrandom missingness. CI uses a normal 1.96 critical value.
    """
    x = np.asarray(values, dtype=float)
    good = np.isfinite(x)
    n = int(good.sum())
    result = {"mean": np.nan, "se": np.nan, "t": np.nan, "n": n, "ci_low": np.nan, "ci_high": np.nan}
    if n == 0:
        return result
    mu = float(x[good].mean())
    result["mean"] = mu
    if n < 2:
        return result
    scores = np.where(good, x - mu, 0.0)
    variance_sum = float(scores @ scores)
    for lag in range(1, min(lags, len(scores) - 1) + 1):
        variance_sum += 2 * (1 - lag / (lags + 1)) * float(scores[lag:] @ scores[:-lag])
    se = math.sqrt(max(variance_sum, 0.0)) / n
    result.update(se=se, t=mu / se if se > 0 else np.nan,
                  ci_low=mu - 1.959963984540054 * se, ci_high=mu + 1.959963984540054 * se)
    return result


def summarize(portfolio_returns, lags=3):
    """Export primary means and matched-month WML/DS interaction spreads."""
    r = portfolio_returns.sort_values("holding_month")
    calendar = pd.period_range(r["holding_month"].min(), r["holding_month"].max(), freq="M")
    summaries = []
    for (w, ds, rb), g in r.groupby(["weighting", "ds_bin", "ret_bin"]):
        values = g.set_index("holding_month")["ret"].reindex(calendar)
        summaries.append({"weighting": w, "ds_bin": ds, "ret_bin": rb, **hac_mean(values, lags)})
    monthly, spread_summaries = [], []
    for w, g in r.groupby("weighting"):
        wide = g.pivot(index="holding_month", columns=["ds_bin", "ret_bin"], values="ret").reindex(calendar)
        series_map = {}
        max_ret, min_ret = int(r["ret_bin"].max()), int(r["ret_bin"].min())
        ds_values = sorted(r["ds_bin"].unique())
        for ds in ds_values:
            series_map[f"WML_DS{ds}"] = wide[(ds, max_ret)] - wide[(ds, min_ret)]
        series_map["LowDS_minus_HighDS"] = series_map[f"WML_DS{ds_values[0]}"] - series_map[f"WML_DS{ds_values[-1]}"]
        for name, vals in series_map.items():
            spread_summaries.append({"weighting": w, "series": name, **hac_mean(vals, lags)})
            monthly.extend({"holding_month": month, "weighting": w, "series": name, "ret": val} for month, val in vals.items())
    return pd.DataFrame(summaries), pd.DataFrame(spread_summaries), pd.DataFrame(monthly)
