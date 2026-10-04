"""Fixed exploratory DS evaluation; formation-only predictors and calendar joins."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .ds_baseline import assign_quantiles, form_portfolios, hac_mean


def restrict_universe(panel, universe):
    """Disable formation eligibility only; preserve all future raw returns."""
    p = panel.copy()
    if universe not in ("all", "no_bj", "no_bj_no_bottom20cap"):
        raise ValueError(f"Unknown universe: {universe}")
    valid = np.isfinite(p.ret) & np.isfinite(p.cap) & p.cap.gt(0) & p.industry.notna()
    valid &= p.industry.astype(str).str.len().gt(0)
    keep = valid.copy()
    if universe != "all":
        keep &= ~p.stock.str.endswith(".BJ")
    if universe == "no_bj_no_bottom20cap":
        ranks = p.loc[keep].groupby("month").cap.rank(method="max", pct=True)
        keep.loc[ranks.index] &= ranks.gt(0.2)
    # Future return matching uses ret, never cap, so an ineligible next month
    # cannot remove an otherwise available holding-period return.
    p.loc[~keep, "cap"] = np.nan
    diagnostics = p[["month"]].copy()
    diagnostics["base_eligible"] = valid.astype(int)
    diagnostics["universe_eligible"] = keep.astype(int)
    return p, diagnostics.groupby("month").sum().reset_index()


def aggregate_memberships(members, calendar, min_cell, ds_bins, ret_bins):
    """Aggregate fixed formations using complete or diagnostic return policies."""
    rows = []
    grouped = dict(tuple(members.groupby(["formation_month", "ds_bin", "ret_bin"])))
    for month in calendar:
        for ds in range(1, ds_bins + 1):
            for rb in range(1, ret_bins + 1):
                sub = grouped.get((month, ds, rb))
                for weighting in ("equal", "value"):
                    n = len(sub) if sub is not None else 0
                    obs = np.isfinite(sub.future_ret) if n else pd.Series(dtype=bool)
                    nobs = int(obs.sum())
                    weights = sub[f"weight_{weighting}"] if n else pd.Series(dtype=float)
                    observed_weight = float(weights[obs].sum()) if n else 0.0
                    val = float(np.dot(weights[obs], sub.loc[obs, "future_ret"]) / observed_weight) if observed_weight else np.nan
                    status = "empty" if not n else "below_minimum" if n < min_cell else "missing_holding_return" if nobs < n else "complete"
                    rows.append(dict(formation_month=month, holding_month=month + 1,
                                     weighting=weighting, ds_bin=ds, ret_bin=rb,
                                     n_formed=n, n_observed=nobs, observed_weight=observed_weight,
                                     ret=val if status == "complete" else np.nan,
                                     observed_only_ret=val, status=status))
    return pd.DataFrame(rows)


def unconditional_portfolios(members, calendar, ret_bins, min_cell):
    """Benchmark return sorts on the same DS-eligible formation cohort."""
    m = members.copy()
    # These assignments never examine the already-joined outcome column.
    m["ds_bin"] = 1
    m["ret_bin"] = m.groupby("formation_month").ret.transform(lambda s: assign_quantiles(s, ret_bins)).astype(int)
    cells = m.groupby(["formation_month", "ret_bin"])
    m["weight_equal"] = 1 / cells.stock.transform("size")
    m["weight_value"] = m.cap / cells.cap.transform("sum")
    return aggregate_memberships(m, calendar, min_cell, 1, ret_bins)


def spread_series(returns, unconditional, ds_bins, ret_bins, min_cell, policy):
    """Calendar-indexed, within-month contrasts, never differences of means."""
    if policy not in ("complete", "observed_only_selected_sample", "unknown_return_zero_scenario", "unknown_return_loss100_scenario"):
        raise ValueError("Unknown return policy")
    def values(frame):
        f = frame.copy()
        if policy == "complete":
            f["value"] = f.ret
        elif policy == "observed_only_selected_sample":
            f["value"] = f.observed_only_ret.where(f.n_formed.ge(min_cell))
        else:
            known_contribution = f.observed_only_ret.fillna(0) * f.observed_weight
            missing_assumption = 0.0 if policy == "unknown_return_zero_scenario" else -1.0
            f["value"] = (known_contribution + missing_assumption * (1 - f.observed_weight)).where(f.n_formed.ge(min_cell))
        return f
    r, u = values(returns), values(unconditional)
    calendar = pd.period_range(r.holding_month.min(), r.holding_month.max(), freq="M")
    records = []
    for weighting in ("equal", "value"):
        wide = r[r.weighting.eq(weighting)].pivot(index="holding_month", columns=["ds_bin", "ret_bin"], values="value").reindex(calendar)
        uwide = u[u.weighting.eq(weighting)].pivot(index="holding_month", columns="ret_bin", values="value").reindex(calendar)
        s = {f"WML_DS{ds}": wide[(ds, ret_bins)] - wide[(ds, 1)] for ds in range(1, ds_bins + 1)}
        s["unconditional_WML"] = uwide[ret_bins] - uwide[1]
        s["lowDS_WML"] = s["WML_DS1"]
        s["highDS_WML"] = s[f"WML_DS{ds_bins}"]
        s["lowDS_minus_highDS"] = s["lowDS_WML"] - s["highDS_WML"]
        s["lowDS_minus_unconditional"] = s["lowDS_WML"] - s["unconditional_WML"]
        s["highDS_minus_unconditional"] = s["highDS_WML"] - s["unconditional_WML"]
        common = pd.concat([s[k] for k in ("lowDS_WML", "highDS_WML", "unconditional_WML")], axis=1).notna().all(axis=1)
        for name in ("lowDS_WML", "highDS_WML", "unconditional_WML", "lowDS_minus_highDS", "lowDS_minus_unconditional", "highDS_minus_unconditional"):
            s[f"common_{name}"] = s[name].where(common)
        records += [dict(holding_month=m, weighting=weighting, series=name, ret=v)
                    for name, series in s.items() for m, v in series.items()]
    return pd.DataFrame(records)


def summarize_series(monthly, periods, lags, groups, value="ret"):
    rows = []
    for keys, group in monthly.groupby(groups, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        series = group.set_index("holding_month")[value].sort_index()
        if series.index.has_duplicates:
            raise ValueError("Duplicate group-month summary")
        for period in periods:
            start = max(series.index.min(), pd.Period(period["start"], "M"))
            end = min(series.index.max(), pd.Period(period["end"], "M"))
            if end < start:
                continue
            vals = series.reindex(pd.period_range(start, end, freq="M"))
            observed = vals.dropna()
            for lag in lags:
                rows.append(dict(zip(groups, keys)) | dict(period=period["name"], hac_lags=lag,
                    calendar_months=len(vals), coverage=float(vals.notna().mean()),
                    first_observed=str(observed.index.min()) if len(observed) else "",
                    last_observed=str(observed.index.max()) if len(observed) else "",
                    **hac_mean(vals, lag)))
    return pd.DataFrame(rows)


def calendar_controls(panel):
    """Explicit monthly lag joins; no shifting across missing months."""
    p = panel[["stock", "month", "ret", "cap"]].copy()
    if p.duplicated(["stock", "month"]).any():
        raise ValueError("Duplicate stock-month controls")
    for lag in range(1, 12):
        previous = panel[["stock", "month", "ret"]].copy()
        previous["month"] += lag
        p = p.merge(previous.rename(columns={"ret": f"lag_{lag}"}), on=["stock", "month"], how="left", validate="one_to_one")
    previous = [f"lag_{i}" for i in range(1, 12)]
    p["momentum_12_2"] = (1 + p[previous]).prod(axis=1, min_count=11) - 1
    all_returns = p[["ret"] + previous]
    p["monthly_volatility_12"] = all_returns.std(axis=1, ddof=1).where(all_returns.notna().all(axis=1))
    p["logcap"] = np.log(p.cap.where(p.cap.gt(0)))
    return p[["stock", "month", "logcap", "momentum_12_2", "monthly_volatility_12"]]


def regression_design(formation, predictors):
    """Scales use only complete formation predictors, never future availability."""
    raw = formation[predictors].replace([np.inf, -np.inf], np.nan)
    good = raw.notna().all(axis=1)
    raw = raw.loc[good]
    scales = raw.std(ddof=0)
    if len(raw) == 0 or not np.isfinite(scales).all() or (scales <= 1e-12).any():
        return None, good, pd.DataFrame()
    means = raw.mean()
    z = (raw - means) / scales
    X = pd.DataFrame({"intercept": 1.0}, index=raw.index)
    X["z_ret"] = z.ret
    X["z_ds"] = z.ds
    X["ret_x_ds"] = z.ret * z.ds
    for control in predictors[2:]:
        X[f"z_{control}"] = z[control]
    scale_table = pd.DataFrame({"predictor": predictors, "formation_mean": means.values, "formation_sd": scales.values})
    return X, good, scale_table


def fama_macbeth(members, controls, calendar, min_obs=100, max_condition=1e8):
    """Monthly raw-return OLS; failure rows retain their calendar positions."""
    m = members.drop(columns=["future_ret"], errors="ignore").merge(
        controls.rename(columns={"month": "formation_month"}), on=["stock", "formation_month"], how="left", validate="one_to_one")
    # Labels are attached only after all dated predictors are assembled.
    m = m.merge(members[["stock", "formation_month", "holding_month", "future_ret"]].drop(columns="holding_month"),
                on=["stock", "formation_month"], how="left", validate="one_to_one")
    coef_rows, diagnostics, scales = [], [], []
    by_month = dict(tuple(m.groupby("formation_month")))
    for month in calendar:
        group = by_month.get(month, m.iloc[:0])
        for model in ("uncontrolled", "controls"):
            predictors = ["ret", "ds"] + (["logcap", "momentum_12_2", "monthly_volatility_12"] if model == "controls" else [])
            terms = ["intercept", "z_ret", "z_ds", "ret_x_ds"] + [f"z_{x}" for x in predictors[2:]]
            X, complete, scale = regression_design(group, predictors)
            n_eligible, n_predictors = len(group), int(complete.sum())
            nobs = int(np.isfinite(group.loc[complete, "future_ret"]).sum())
            rank, condition, r2, residual_df = 0, np.nan, np.nan, 0
            status, coefficients = "invalid_or_constant_predictors", np.full(len(terms), np.nan)
            if X is not None:
                outcome = group.loc[X.index, "future_ret"]
                observed = np.isfinite(outcome)
                xx, yy = X.loc[observed].to_numpy(), outcome.loc[observed].to_numpy()
                nobs = len(yy)
                rank = int(np.linalg.matrix_rank(xx)) if nobs else 0
                condition = float(np.linalg.cond(xx)) if nobs else np.nan
                residual_df = nobs - len(terms)
                status = "too_few_observations" if nobs < max(min_obs, len(terms) + 1) else "rank_deficient" if rank < len(terms) else "ill_conditioned" if not np.isfinite(condition) or condition > max_condition else "ok"
                if status == "ok":
                    coefficients = np.linalg.lstsq(xx, yy, rcond=None)[0]
                    sst = np.square(yy - yy.mean()).sum()
                    r2 = 1 - np.square(yy - xx @ coefficients).sum() / sst if sst > 0 else np.nan
                scale["formation_month"], scale["model"] = month, model
                scales.append(scale)
            diagnostics.append(dict(formation_month=month, holding_month=month+1, model=model, status=status,
                n_eligible=n_eligible, n_predictor_complete=n_predictors, n_observed=nobs,
                missing_outcomes=n_predictors-nobs, predictor_coverage=n_predictors/n_eligible if n_eligible else np.nan,
                outcome_coverage=nobs/n_predictors if n_predictors else np.nan,
                rank=rank, condition_number=condition, residual_df=residual_df, r_squared=r2))
            coef_rows += [dict(holding_month=month+1, model=model, coefficient=term, estimate=coefficient)
                          for term, coefficient in zip(terms, coefficients)]
    return pd.DataFrame(coef_rows), pd.DataFrame(diagnostics), pd.concat(scales, ignore_index=True) if scales else pd.DataFrame()


def rf_portfolios(panel, rf, spec):
    """Compute DS on excess signal returns, then restore raw holding returns."""
    if rf.month.duplicated().any():
        raise ValueError("Duplicate RF month")
    p = panel.merge(rf[["month", "rf_monthly_proxy"]], on="month", how="left", validate="many_to_one")
    p["ret"] = p.ret - p.rf_monthly_proxy
    m, _, diagnostics = form_portfolios(p, min_peers=spec["min_peers"], ds_bins=spec["ds_bins"], ret_bins=spec["ret_bins"], min_cell=spec["min_cell"])
    m["ret"] += m.rf_monthly_proxy
    m["peer_ret"] += m.rf_monthly_proxy
    future = panel[["stock", "month", "ret"]].rename(columns={"month": "holding_month", "ret": "future_ret"})
    m = m.drop(columns="future_ret").merge(future, on=["stock", "holding_month"], how="left", validate="one_to_one")
    calendar = pd.period_range(m.formation_month.min(), m.formation_month.max(), freq="M")
    returns = aggregate_memberships(m, calendar, spec["min_cell"], spec["ds_bins"], spec["ret_bins"])
    diagnostics.update(unknown_holding_returns=int(m.future_ret.isna().sum()),
        formation_start=str(calendar.min()), formation_end=str(calendar.max()),
        holding_start=str(calendar.min()+1), holding_end=str(calendar.max()+1),
        portfolio_status_counts_per_weighting=returns[returns.weighting.eq("equal")].status.value_counts().to_dict())
    return m, returns, diagnostics
