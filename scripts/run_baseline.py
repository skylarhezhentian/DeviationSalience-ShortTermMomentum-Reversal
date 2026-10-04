#!/usr/bin/env python3
"""Reproduce the local DS baseline without modifying source data."""
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
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ds_baseline import monthly_panel, form_portfolios, summarize


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=str) + "\n")


def csv(frame, path):
    frame.to_csv(path, index=False, float_format="%.12g")


def read_endpoint_data(path, endpoint_dates, kind):
    """Read only formation-date fields; raw Parquet files remain untouched."""
    if kind == "value":
        columns, date_col = ["TRADE_DT", "S_INFO_WINDCODE", "S_VAL_MV"], "TRADE_DT"
    else:
        columns, date_col = ["date", "wind_code", "ind"], "date"
    table = pq.read_table(path, columns=columns, filters=[(date_col, "in", endpoint_dates)])
    # Ignore stored pandas index metadata; keep the join keys as columns.
    return table.to_pandas(ignore_metadata=True)


def table_text(frame, weighting):
    rows = ["| DS group | RET1 | RET2 | RET3 | RET4 | RET5 | RET6 | RET7 | RET8 | RET9 | RET10 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for ds in range(1, 6):
        g = frame[(frame.weighting == weighting) & (frame.ds_bin == ds)].set_index("ret_bin")
        values = [f"{100 * g.loc[r, 'mean']:.3f}" if pd.notna(g.loc[r, "mean"]) else "n.a." for r in range(1, 11)]
        rows.append("| " + f"DS{ds}" + " | " + " | ".join(values) + " |")
    return "\n".join(rows)


def report(config, diagnostics, portfolio_summary, spread_summary):
    d = diagnostics["formation"]
    lines = ["# Corrected local Deviation Salience baseline", "",
             f"Holding months: **{d['holding_start']} through {d['holding_end']}**. Descriptive analysis of the supplied historical sample.", "",
             "This is a zero-risk-free-rate, industry-peer adaptation. It is not an exact replication of the cited paper, an out-of-sample test, or an executable trading backtest.", "",
             "## Baseline choices", "",
             "- Monthly return is adjusted month-end price divided by the immediately preceding calendar month-end price, minus one. Endpoints must match the last market date present in that month.",
             "- Peers are other eligible stocks in the same dated industry. Each peer contributes once. At least three peers are required. Historical point-in-time classification and vendor return-adjustment conventions remain unverified.",
             "- DS = |stock return − peer return| / (|stock return| + |peer return|). No risk-free series is available in the selected inputs, so zero is an explicit proxy. Returns are not winsorized.",
             "- Five target DS groups and ten within-group return groups use the right-end empirical CDF. Equal signals stay together; unequal sizes and empty nominal bins are retained.",
             f"- Final cells require at least {config['minimum_stocks_per_final_cell']} stocks. Equal and formation-capitalization weights use identical memberships. The full holding month is evaluated from month-end to month-end under a statistical same-close convention.",
             "- Future-return availability does not change formation membership, breakpoints, or weights. Any unknown holding return makes the primary cell return unavailable. Observed-only diagnostics are stored separately and are not headline results.",
             f"- Reported means use only available complete-cell months. HAC inference uses {config['hac_lags']} calendar lags, Bartlett weights, no finite-sample correction, and normal 95% confidence intervals. Missing calendar months are not compressed. This does not remove selection bias caused by missing months.", "",
             "## Formation and missingness", "",
             f"- Formed stock-months: {d['formed_stock_months']:,}.",
             f"- Unknown holding returns: {d['unknown_holding_returns']:,}.",
             f"- Fraction at DS = 1: {d['ds_exactly_one_fraction']:.2%}.",
             f"- Held stock returns above +100%: {d['holding_returns_above_100_percent']:,}. Largest observed holding return: {100*d['largest_holding_return']:.2f}%; smallest: {100*d['smallest_holding_return']:.2f}%.",
             f"- Cell-month status counts, for each weighting: `{d['portfolio_status_counts_per_weighting']}`.", "",
             "Large returns are retained, not automatically declared errors or removed. The 20 largest absolute holding returns are saved in extreme_returns.csv for a vendor/corporate-action audit. Their economic validity has not been independently verified.", "",
             "Cell means can cover different subsets of months. WML is calculated only where both legs exist; the low-minus-high DS contrast uses the intersection of all four legs. See monthly_spreads.csv for exact months.", "",
             "## Matched-month spreads", "",
             "All returns and confidence intervals below are percentage points per month. WML means RET10 minus RET1. LowDS_minus_HighDS means WML_DS1 minus WML_DS5.", "",
             "| Weighting | Series | Mean | HAC t | 95% CI | Months |",
             "|---|---|---:|---:|---|---:|"]
    for row in spread_summary.itertuples():
        if pd.isna(row.mean):
            lines.append(f"| {row.weighting} | {row.series} | n.a. | n.a. | n.a. | {row.n} |")
        else:
            t = f"{row.t:.2f}" if pd.notna(row.t) else "n.a."
            ci = f"[{100*row.ci_low:.3f}, {100*row.ci_high:.3f}]" if pd.notna(row.ci_low) else "n.a."
            lines.append(f"| {row.weighting} | {row.series} | {100*row.mean:.3f} | {t} | {ci} | {row.n} |")
    for w in ("equal", "value"):
        lines += ["", f"## {w.capitalize()}-weighted cell means", "", "Percent per month. Per-cell sample counts and uncertainty are in portfolio_summary.csv.", "", table_text(portfolio_summary, w)]
    lines += ["", "## Files and scope", "",
              "- `input_manifest.json`: input file hashes, sizes and dates; no raw inputs copied.",
              "- `run_manifest.json`: configuration, code hashes, package versions and original-file preservation checks.",
              "- `monthly_panel.parquet` and `memberships.parquet`: local, inspectable derived records; not approved for public redistribution.",
              "- `formation_diagnostics.csv` and `bin_occupancy.csv`: period-level coverage, ties and final-cell sizes.",
              "- `extreme_returns.csv`: largest absolute raw holding returns for source verification; no selection change.",
              "- `portfolio_returns.csv`: full monthly cell returns, counts, coverage and separate observed-only diagnostics.",
              "- `portfolio_summary.csv`, `spread_summary.csv`, `monthly_spreads.csv`: figures and tables trace back to these generated files.",
              "- `figures/`: regenerated PNG and SVG figures.", "",
              "## Remaining limitations", "",
              "The inputs do not establish ST status, suspension/execution feasibility, delisting payouts, stock-level liquidity, short availability, or historical data vintages. An unchanged price is not proof of tradability. No transaction costs, risk-factor alpha, or market-neutral implementability are claimed. Vendor adjustments are not independently verified as total returns. The last supplied month is not certified against an external exchange calendar. No performance-based parameter search or newly declared holdout was used. Primary complete-cell estimates can still be selected by missing-return availability; attrition is reported, not cured.", "",
              "Research context: Chen, Wang and Yu, [Salience and Short-term Momentum and Reversals](https://ssrn.com/abstract=4649393). Their published findings are not results of this local analysis.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    args = ap.parse_args()
    data, out = args.data_dir.resolve(), args.output_dir.resolve()
    if out == data or data in out.parents:
        raise ValueError("Output must be outside the original data directory")
    config = json.loads((ROOT / "config.json").read_text())
    sources = [data / name for name in ("close.parquet", "value.parquet", "industry.parquet")]
    for p in sources:
        if not p.is_file():
            raise FileNotFoundError(p)
    out.mkdir(parents=True, exist_ok=True)
    input_manifest = []
    for p in sources:
        meta = pq.ParquetFile(p).metadata
        input_manifest.append({"name": p.name, "path": str(p), "bytes": p.stat().st_size,
                               "mtime_ns": p.stat().st_mtime_ns, "sha256": digest(p), "rows": meta.num_rows})
    originals = list(data.glob("*.py")) + list(data.glob("*.ipynb")) + list(data.glob("*.xlsx")) + list(data.glob("*.png")) + list(data.glob("*.pdf"))
    original_hashes = {str(p): digest(p) for p in originals if not p.name.startswith("~$")}
    print("Reading price endpoints and dated formation fields...", flush=True)
    close = pd.read_parquet(sources[0])
    dates = pd.to_datetime(close["TRADE_DT"])
    endpoint_dates = dates.groupby(dates.dt.to_period("M")).max().tolist()
    value = read_endpoint_data(sources[1], endpoint_dates, "value")
    industry = read_endpoint_data(sources[2], endpoint_dates, "industry")
    panel, panel_diagnostics = monthly_panel(close, value, industry)
    del close, value, industry
    print(f"Monthly panel: {len(panel):,} endpoint observations", flush=True)
    memberships, returns, formation_diagnostics = form_portfolios(
        panel, min_peers=config["min_peers"], ds_bins=config["ds_bins"],
        ret_bins=config["return_bins"], min_cell=config["minimum_stocks_per_final_cell"])
    portfolio_summary, spread_summary, monthly_spreads = summarize(returns, lags=config["hac_lags"])
    formation_diagnostics["holding_returns_above_100_percent"] = int(memberships["future_ret"].gt(1).sum())
    formation_diagnostics["largest_holding_return"] = float(memberships["future_ret"].max())
    formation_diagnostics["smallest_holding_return"] = float(memberships["future_ret"].min())
    diagnostics = {"panel": panel_diagnostics, "formation": formation_diagnostics}

    # Keep derived stock-level data local, with unambiguous month serialization.
    for frame, filename in ((panel, "monthly_panel.parquet"), (memberships, "memberships.parquet")):
        frame = frame.copy()
        for col in frame.columns:
            if isinstance(frame[col].dtype, pd.PeriodDtype):
                frame[col] = frame[col].astype(str)
        frame.to_parquet(out / filename, index=False)
    for frame, filename in ((returns, "portfolio_returns.csv"), (portfolio_summary, "portfolio_summary.csv"),
                            (spread_summary, "spread_summary.csv"), (monthly_spreads, "monthly_spreads.csv")):
        csv(frame, out / filename)
    by_month = memberships.groupby("formation_month").agg(
        stocks=("stock", "size"), industries=("industry", "nunique"),
        ds_at_one=("ds", lambda x: x.eq(1).sum()), unknown_returns=("future_ret", lambda x: x.isna().sum()),
        smallest_return=("ret", "min"), largest_return=("ret", "max"))
    by_month["fraction_ds_at_one"] = by_month.ds_at_one / by_month.stocks
    csv(by_month.reset_index(), out / "formation_diagnostics.csv")
    occupancy = memberships.groupby(["formation_month", "ds_bin", "ret_bin"]).agg(
        stocks=("stock", "size"), minimum_ds=("ds", "min"), maximum_ds=("ds", "max"),
        largest_cap_weight=("weight_value", "max"), unknown_returns=("future_ret", lambda x: x.isna().sum()))
    csv(occupancy.reset_index(), out / "bin_occupancy.csv")
    extremes = memberships.loc[memberships["future_ret"].abs().nlargest(20).index,
        ["stock", "formation_month", "holding_month", "industry", "ret", "peer_ret", "ds", "cap", "future_ret"]]
    csv(extremes, out / "extreme_returns.csv")
    write_json(out / "input_manifest.json", input_manifest)
    write_json(out / "diagnostics.json", diagnostics)
    unchanged = all(digest(Path(p)) == h for p, h in original_hashes.items())
    unchanged_data = all(digest(Path(m["path"])) == m["sha256"] for m in input_manifest)
    if not unchanged or not unchanged_data:
        raise RuntimeError("Original file preservation check failed")
    code_paths = sorted((ROOT / "src").glob("*.py")) + [Path(__file__).resolve(), ROOT / "config.json"]
    run_manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "config": config,
                    "python": platform.python_version(),
                    "packages": {p: importlib.metadata.version(p) for p in ("pandas", "numpy", "pyarrow", "statsmodels")},
                    "code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in code_paths},
                    "original_data_unchanged": unchanged_data, "original_research_files_unchanged": unchanged,
                    "original_research_sha256": original_hashes,
                    "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir()) if p.suffix in (".csv", ".parquet")}}
    write_json(out / "run_manifest.json", run_manifest)
    (out / "RESULTS.md").write_text(report(config, diagnostics, portfolio_summary, spread_summary))
    print(json.dumps(formation_diagnostics, indent=2), flush=True)
    print(spread_summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
