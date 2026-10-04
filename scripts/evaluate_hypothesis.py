#!/usr/bin/env python3
"""Run the fixed, exploratory protocol without changing baseline artifacts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ds_baseline import form_portfolios
from src.research import (restrict_universe, unconditional_portfolios, spread_series,
                          summarize_series, calendar_controls, fama_macbeth, rf_portfolios)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv(frame, path):
    frame.to_csv(path, index=False, float_format="%.12g")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/research")
    args = parser.parse_args()
    base, out = args.baseline_dir.resolve(), args.output_dir.resolve()
    if out == base or out in base.parents:
        raise ValueError("Research outputs cannot replace the baseline directory")
    config_path, protocol_path = ROOT / "configs/robustness.json", ROOT / "docs/research_protocol.md"
    config = json.loads(config_path.read_text())
    predeclared = {str(p.relative_to(ROOT)): digest(p) for p in (config_path, protocol_path)}
    baseline_hashes = {p.name: digest(p) for p in base.iterdir() if p.is_file()}
    baseline_manifest = json.loads((base / "run_manifest.json").read_text())
    if digest(base / "monthly_panel.parquet") != baseline_manifest["output_sha256"]["monthly_panel.parquet"]:
        raise ValueError("Monthly panel differs from baseline run manifest")
    panel = pd.read_parquet(base / "monthly_panel.parquet")
    panel["month"] = pd.PeriodIndex(panel.month, freq="M")
    out.mkdir(parents=True, exist_ok=True)
    controls = calendar_controls(panel)
    all_monthly, all_portfolios, all_unconditional, all_universe = [], [], [], []
    all_coefficients, all_regdiag, all_scales, all_diag = [], [], [], []
    baseline_members, baseline_returns = None, None
    for spec in config["specifications"]:
        print(f"Evaluating {spec['name']}...", flush=True)
        universe, counts = restrict_universe(panel, spec["universe"])
        counts["specification"] = spec["name"]
        all_universe.append(counts)
        members, returns, diag = form_portfolios(universe, min_peers=spec["min_peers"], ds_bins=spec["ds_bins"],
                                                 ret_bins=spec["ret_bins"], min_cell=spec["min_cell"])
        calendar = pd.period_range(returns.formation_month.min(), returns.formation_month.max(), freq="M")
        benchmark = unconditional_portfolios(members, calendar, spec["ret_bins"], spec["min_cell"])
        if spec["name"] == "baseline":
            baseline_members, baseline_returns = members.copy(), returns.copy()
            old = pd.read_csv(base / "portfolio_returns.csv")
            np.testing.assert_allclose(returns.ret, old.ret, rtol=1e-9, atol=1e-11, equal_nan=True)
        for policy in config["missing_policies"]:
            monthly = spread_series(returns, benchmark, spec["ds_bins"], spec["ret_bins"], spec["min_cell"], policy)
            monthly["specification"], monthly["missing_policy"] = spec["name"], policy
            all_monthly.append(monthly)
        returns["specification"], benchmark["specification"] = spec["name"], spec["name"]
        all_portfolios.append(returns)
        all_unconditional.append(benchmark)
        all_diag.append({"specification": spec["name"], **diag})
        if spec["name"] in config["regression"]["specifications"]:
            coef, regdiag, scales = fama_macbeth(members, controls, calendar,
                config["regression"]["min_observations"], config["regression"]["max_condition_number"])
            for frame in (coef, regdiag, scales):
                frame["specification"] = spec["name"]
            all_coefficients.append(coef)
            all_regdiag.append(regdiag)
            all_scales.append(scales)
    monthly = pd.concat(all_monthly, ignore_index=True)
    summaries = summarize_series(monthly, config["periods"], config["hac_lags"], ["specification", "missing_policy", "weighting", "series"])
    coefficients = pd.concat(all_coefficients, ignore_index=True)
    coefficient_summary = summarize_series(coefficients, config["periods"], config["hac_lags"], ["specification", "model", "coefficient"], "estimate")
    tables = {
        "monthly_spreads.csv": monthly, "spread_summary.csv": summaries,
        "portfolio_returns.csv": pd.concat(all_portfolios, ignore_index=True),
        "unconditional_portfolio_returns.csv": pd.concat(all_unconditional, ignore_index=True),
        "universe_coverage.csv": pd.concat(all_universe, ignore_index=True),
        "regression_monthly_coefficients.csv": coefficients,
        "regression_summary.csv": coefficient_summary,
        "regression_diagnostics.csv": pd.concat(all_regdiag, ignore_index=True),
        "regression_standardization.csv": pd.concat(all_scales, ignore_index=True)
    }
    rf_path = ROOT / config["rf_sensitivity"]["file"]
    rf_manifest = {"status": "not_available"}
    if rf_path.is_file():
        print("Evaluating matched-window retrospective RF proxy...", flush=True)
        rf = pd.read_csv(rf_path)
        rf["month"] = pd.PeriodIndex(rf.month, freq="M")
        rf = rf[np.isfinite(rf.rf_monthly_proxy)]
        spec = config["specifications"][0]
        rmembers, rreturns, _ = rf_portfolios(panel, rf, spec)
        available = pd.PeriodIndex(sorted(set(rmembers.formation_month).intersection(rf.month)))
        rreturns = rreturns[rreturns.formation_month.isin(available)]
        rbenchmark = unconditional_portfolios(rmembers, available, spec["ret_bins"], spec["min_cell"])
        zreturns = baseline_returns[baseline_returns.formation_month.isin(available)]
        zmembers = baseline_members[baseline_members.formation_month.isin(available)]
        zbenchmark = unconditional_portfolios(zmembers, available, spec["ret_bins"], spec["min_cell"])
        rf_monthly = []
        for policy in config["missing_policies"]:
            for name, cell, uncond in (("zero_rf_matched", zreturns, zbenchmark), ("rf_proxy_matched", rreturns, rbenchmark)):
                frame = spread_series(cell, uncond, spec["ds_bins"], spec["ret_bins"], spec["min_cell"], policy)
                frame["missing_policy"], frame["rf_specification"] = policy, name
                rf_monthly.append(frame)
        rf_monthly = pd.concat(rf_monthly, ignore_index=True)
        paired_rows = []
        for keys, group in rf_monthly.groupby(["missing_policy", "weighting", "series"]):
            wide = group.pivot(index="holding_month", columns="rf_specification", values="ret")
            common = wide.notna().all(axis=1)
            for name, vals in (("rf_minus_zero", wide.rf_proxy_matched-wide.zero_rf_matched),
                               ("rf_on_common", wide.rf_proxy_matched.where(common)),
                               ("zero_on_common", wide.zero_rf_matched.where(common))):
                paired_rows += [dict(missing_policy=keys[0], weighting=keys[1], series=keys[2],
                    rf_specification=name, holding_month=m, ret=v) for m, v in vals.items()]
        rf_monthly = pd.concat([rf_monthly, pd.DataFrame(paired_rows)], ignore_index=True)
        tables["rf_monthly_spreads.csv"] = rf_monthly
        tables["rf_spread_summary.csv"] = summarize_series(rf_monthly, config["periods"], config["hac_lags"], ["rf_specification", "missing_policy", "weighting", "series"])
        common_stocks = zmembers[["stock", "formation_month", "ds", "ds_bin", "ret_bin"]].merge(
            rmembers[["stock", "formation_month", "ds", "ds_bin", "ret_bin"]], on=["stock", "formation_month"], suffixes=("_zero", "_proxy"), validate="one_to_one")
        common_stocks["ds_abs_change"] = (common_stocks.ds_proxy - common_stocks.ds_zero).abs()
        common_stocks["ds_bin_changed"] = common_stocks.ds_bin_proxy.ne(common_stocks.ds_bin_zero)
        common_stocks["cell_changed"] = common_stocks.ds_bin_changed | common_stocks.ret_bin_proxy.ne(common_stocks.ret_bin_zero)
        tables["rf_assignment_diagnostics.csv"] = common_stocks.groupby("formation_month").agg(
            matched_stocks=("stock", "size"), mean_abs_ds_change=("ds_abs_change", "mean"),
            fraction_ds_bin_changed=("ds_bin_changed", "mean"), fraction_cell_changed=("cell_changed", "mean")).reset_index()
        rf_manifest = dict(status="completed", input_sha256=digest(rf_path), formation_start=str(available.min()),
                           formation_end=str(available.max()), formation_months=len(available),
                           zero_formed_rows=len(zmembers), rf_formed_rows=len(rmembers), common_stock_rows=len(common_stocks))
    for filename, frame in tables.items():
        csv(frame, out / filename)
    preservation = all(digest(base / name) == h for name, h in baseline_hashes.items())
    declaration_unchanged = all(digest(ROOT / name) == h for name, h in predeclared.items())
    if not preservation or not declaration_unchanged:
        raise RuntimeError("Baseline/protocol preservation check failed")
    sources = [ROOT / "src/research.py", ROOT / "scripts/evaluate_hypothesis.py", ROOT / "src/ds_baseline.py", config_path, protocol_path]
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), config=config,
        protocol_hashes_before_run=predeclared, protocol_unchanged_during_run=declaration_unchanged,
        code_sha256={str(p.relative_to(ROOT)): digest(p) for p in sources},
        input_sha256={"monthly_panel.parquet": baseline_hashes["monthly_panel.parquet"], "baseline_run_manifest.json": baseline_hashes["run_manifest.json"]},
        baseline_outputs_unchanged=preservation, python=platform.python_version(),
        packages={p: importlib.metadata.version(p) for p in ("numpy", "pandas", "pyarrow")},
        rf_sensitivity=rf_manifest, formation_diagnostics=all_diag,
        output_sha256={name: digest(out / name) for name in tables})
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    view = summaries[summaries.period.eq("full") & summaries.hac_lags.eq(3) & summaries.missing_policy.eq("complete") & summaries.series.isin(["unconditional_WML", "lowDS_minus_highDS"])]
    print(view[["specification", "weighting", "series", "mean", "t", "n", "coverage"]].to_string(index=False), flush=True)
    print("Research outputs written; baseline files verified unchanged.", flush=True)


if __name__ == "__main__":
    main()
