#!/usr/bin/env python3
"""Build aggregate research documentation and figures from saved estimates.

No raw market records, identifiers, local manifests or local source paths are
copied into the public report. This does not redistribute the source datasets.
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "baseline": "Baseline (5 × 10)",
    "no_bj": "Exclude Beijing exchange",
    "no_bj_no_bottom20cap": "Also exclude smallest 20%",
    "coarse_3x5": "Coarser groups (3 × 5)",
    "minimum_5_peers": "At least 5 peers",
    "minimum_cell_10": "At least 10 stocks per cell",
    "minimum_cell_30": "At least 30 stocks per cell",
}


def selected(frame, **filters):
    mask = pd.Series(True, index=frame.index)
    for key, val in filters.items():
        if key not in frame:
            raise ValueError(f"Missing report field: {key}")
        mask &= frame[key].eq(val)
    return frame.loc[mask].copy()


def pct(value):
    return f"{100*value:+.3f}%" if pd.notna(value) else "n.a."


def statistics_table(frame, labels):
    lines = ["| " + " | ".join(labels.values()) + " | Mean | HAC t | 95% CI | Months |",
             "|" + "---|" * (len(labels) + 4)]
    for _, row in frame.iterrows():
        keys = [str(row[k]) for k in labels]
        t = f"{row['t']:.2f}" if pd.notna(row["t"]) else "n.a."
        ci = f"[{pct(row['ci_low'])}, {pct(row['ci_high'])}]"
        lines.append("| " + " | ".join(keys + [pct(row["mean"]), t, ci, str(int(row["n"]))]) + " |")
    return "\n".join(lines)


def robustness_plot(frame, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.9), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.245, right=0.965, top=0.75, bottom=0.20, wspace=0.16)
    names = list(LABELS)
    finite_limits = []
    for ax, weighting, color in zip(axes, ["equal", "value"], ["#167D9A", "#394B81"]):
        sample = frame[frame.weighting.eq(weighting)].set_index("specification").reindex(names)
        for y, (_, row) in enumerate(sample.iterrows()):
            if pd.isna(row["mean"]) or pd.isna(row["se"]):
                ax.text(0.02, y, "Not estimable", transform=ax.get_yaxis_transform(), va="center")
                continue
            mean, low, high = 100 * row[["mean", "ci_low", "ci_high"]].to_numpy(float)
            ax.errorbar(mean, y, xerr=[[mean-low], [high-mean]], fmt="o", color=color, capsize=4, linewidth=1.7)
            ax.annotate(f"n={int(row['n'])}", (mean, y), xytext=(0, -16), textcoords="offset points", ha="center", color=color, fontsize=8)
            finite_limits.extend([low, high])
        ax.set_title("Equal-weighted" if weighting == "equal" else "Value-weighted", loc="left", fontsize=12, pad=16)
        ax.axvline(0, color="#7B858C", linewidth=1, linestyle="--")
        ax.grid(axis="x", color="#E4E9ED", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_xlabel("Low-DS WML minus high-DS WML (% per month)", labelpad=12, fontsize=9)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#BAC5CD")
        ax.tick_params(length=0, pad=7)
        ax.set_yticks(range(len(names)), [LABELS[n] for n in names])
    axes[0].set_ylim(len(names)-0.45, -0.65)
    if finite_limits:
        lo, hi = min(finite_limits), max(finite_limits)
        margin = max((hi-lo)*.08, .2)
        axes[0].set_xlim(lo-margin, hi+margin)
    fig.text(.07, .935, "Deviation salience: fixed robustness checks", fontsize=19, weight="bold", color="#182A39")
    fig.text(.07, .882, "Seven specifications, reported together without selecting a preferred result", fontsize=11, color="#465968")
    fig.text(.07, .838, "March 2021–November 2025 holding window; available matched months vary by specification", fontsize=10, color="#465968")
    fig.text(.07, .106, "Points: mean low-minus-high contrast. Bars: 95% normal HAC intervals, three calendar lags. n: complete matched months.", fontsize=9, color="#556774")
    fig.text(.07, .065, "Exploratory historical analysis. Industry-peer DS uses a zero risk-free proxy; ties stay together. No trading-cost or execution model.", fontsize=9, color="#556774")
    for ext in ("png", "svg"):
        fig.savefig(destination / f"robustness.{ext}", dpi=180, facecolor="white")
    plt.close(fig)


def copy_aggregate_tables(research_output, tables):
    """Publish current summaries and remove only obsolete generated RF tables."""
    required = ("spread_summary.csv", "regression_summary.csv")
    for filename in required:
        if not (research_output / filename).is_file():
            raise FileNotFoundError(research_output / filename)
    full = tables / "full"
    full.mkdir(parents=True, exist_ok=True)
    for filename in required:
        shutil.copyfile(research_output / filename, full / filename)
    rf_source = research_output / "rf_spread_summary.csv"
    if rf_source.is_file():
        shutil.copyfile(rf_source, full / rf_source.name)
        return True
    (full / rf_source.name).unlink(missing_ok=True)
    (tables / "risk_free_sensitivity.csv").unlink(missing_ok=True)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-output", type=Path, default=ROOT / "outputs")
    parser.add_argument("--research-output", type=Path, default=ROOT / "outputs/research")
    parser.add_argument("--docs-dir", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    docs = args.docs_dir
    assets, tables = docs / "assets", docs / "tables"
    assets.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    has_rf = copy_aggregate_tables(args.research_output, tables)
    summary = pd.read_csv(args.research_output / "spread_summary.csv")
    regression = pd.read_csv(args.research_output / "regression_summary.csv")
    contrast = selected(summary, series="lowDS_minus_highDS", missing_policy="complete", period="full", hac_lags=3)
    benchmark = selected(summary, specification="baseline", missing_policy="complete", period="full", hac_lags=3)
    benchmark = benchmark[benchmark.series.isin(["unconditional_WML", "common_unconditional_WML", "common_lowDS_WML", "common_highDS_WML", "common_lowDS_minus_highDS"])]
    coefficients = selected(regression, coefficient="ret_x_ds", period="full", hac_lags=3)
    missing = selected(summary, specification="baseline", series="lowDS_minus_highDS", period="full", hac_lags=3)
    periods = selected(summary, specification="baseline", series="lowDS_minus_highDS", missing_policy="complete", hac_lags=3)
    robustness_plot(contrast, assets)
    for name, data in [("robustness", contrast), ("benchmark", benchmark), ("regression_interaction", coefficients),
                       ("missing_return_scenarios", missing), ("subperiods", periods)]:
        data.to_csv(tables / f"{name}.csv", index=False, float_format="%.12g")
    baseline = pd.read_csv(args.baseline_output / "spread_summary.csv")
    base = baseline[baseline.series.eq("LowDS_minus_HighDS")]
    diagnostics = json.loads((args.baseline_output / "diagnostics.json").read_text())
    lines = ["# Empirical results", "",
        "The corrected baseline does not provide strong evidence for the central low-DS versus high-DS portfolio contrast. The study reports fixed alternatives and controlled regressions alongside that baseline; these use an already-examined historical sample and are exploratory.", "",
        "## Baseline", "",
        "The signal is an industry-peer, zero-risk-free-rate adaptation. WML is the next-month return of the highest formation-return group minus the lowest. The central contrast subtracts high-DS WML from low-DS WML using identical available holding months.", "",
        statistics_table(base, {"weighting":"Weighting"}), "",
        f"The input price window is {diagnostics['panel']['price_date_start']} to {diagnostics['panel']['price_date_end']}. Portfolio holding months run from March 2021 through November 2025. There are {diagnostics['formation']['formed_stock_months']:,} formation stock-month observations and {diagnostics['formation']['unknown_holding_returns']} unknown holding returns. Primary estimates require every holding's return, so the central contrast uses only 36 of 57 months. The available-month estimates can remain selected by missingness.", "",
        "## Fixed alternatives", "",
        "![Fixed robustness comparisons](assets/robustness.svg)", "",
        statistics_table(contrast, {"specification":"Specification", "weighting":"Weighting"}), "",
        "All fourteen headline confidence intervals include zero. The 3 × 5 specification changes group breadth. Universe exclusions use formation-time data. Minimum-count and peer choices are fixed sensitivity checks, not an optimization grid. Identical headline estimates for some thresholds reflect unchanged contributing corner portfolios; they are not independent confirmations. An isolated significant result is not treated as confirmatory evidence.", "",
        "## Reversal benchmark", "",
        "The unconditional WML sort uses the same formation cohort without sorting on DS. Rows beginning `common_` use the intersection of low-DS, high-DS and unconditional WML months; compare those rows with each other. The standalone unconditional row has its own available-month sample.", "",
        statistics_table(benchmark, {"weighting":"Weighting", "series":"Series"}), "",
        "## Controlled cross-sectional regressions", "",
        "Monthly regressions predict raw next-calendar-month returns. The reported coefficient multiplies standardized formation return by standardized DS. A negative coefficient is consistent with a more negative return slope at higher DS. The controlled model adds log capitalization, prior 12–2 momentum, and trailing monthly volatility. In the table, percentages express percentage points of next-month return per standardized interaction unit. These month-specific units are not directly comparable to the portfolio spread above.", "",
        statistics_table(coefficients, {"specification":"Universe", "model":"Model"}), "",
        "Regression outcomes use observed-return complete cases, with coverage reported by the script. No liquidity control, factor alpha, causal identification, or out-of-sample validation is claimed.", "",
        "## Missing-return sensitivity", "",
        statistics_table(missing, {"missing_policy":"Missing-return treatment", "weighting":"Weighting"}), "",
        "Only `complete` is the primary portfolio treatment. Observed-only weights are renormalized over a selected sample. Assigning 0% or −100% to unknown holdings is an explicit scenario; neither assignment recovers actual delisting payouts, and these are not sharp bounds for a long-minus-short contrast.", "",
        "## Historical subperiods", "",
        statistics_table(periods, {"period":"Holding period", "weighting":"Weighting"}), "",
        "These subperiods were not held out from the earlier exploratory work. Their short samples and changing coverage limit the interpretation of differences.", ""]
    rf_path = args.research_output / "rf_spread_summary.csv"
    if has_rf:
        rf = pd.read_csv(rf_path)
        filt = {k:v for k,v in {"series":"lowDS_minus_highDS", "period":"full", "hac_lags":3, "missing_policy":"complete"}.items() if k in rf}
        rf = selected(rf, **filt)
        rf.to_csv(tables / "risk_free_sensitivity.csv", index=False, float_format="%.12g")
        lines += ["## Targeted interest-rate enrichment", "",
            "The official FRED/OECD China three-month Treasury yield series supplies formation-month proxies through November 2023, allowing holding returns through December 2023. Annual percentage yield /100/12 approximates monthly carry. It is not a realized bill return or a verified point-in-time vintage. No absent months are filled. The names `rf_proxy_matched` and `zero_rf_matched` denote the same formation window but have 25 and 24 usable contrast months respectively. Compare `rf_on_common`, `zero_on_common`, and `rf_minus_zero` for the identical 24 holding months.", "",
            statistics_table(rf, {"rf_specification":"Comparison", "weighting":"Weighting"}), ""]
    else:
        lines += ["## Targeted interest-rate enrichment", "", "No RF sensitivity output was found. See the data-source record for availability; no completed RF test is claimed here.", ""]
    aggregate_links = "the [portfolio grid](tables/full/spread_summary.csv) and [all regression coefficients](tables/full/regression_summary.csv)"
    if has_rf:
        aggregate_links += ", plus [rate-proxy comparisons](tables/full/rf_spread_summary.csv)"
    lines += ["## Interpretation and remaining limits", "",
        "The study produces inconclusive estimates with explicit sensitivity checks. Provider price adjustments, dated identifier histories, delisting consideration and execution constraints require further evidence. Public issuer/exchange checks and the added interest-rate data are documented in [Data sources and quality](data_sources.md).", "",
        "The original research inspiration is Chen, Wang and Yu, [Salience and Short-term Momentum and Reversals](https://ssrn.com/abstract=4649393). Its published U.S. findings are not results of this A-share study.", "",
        "## Reproduce and inspect", "",
        f"Read the [fixed evaluation protocol](research_protocol.md) and [reproduction instructions](reproduce.md). Complete aggregate estimates include {aggregate_links}, including six-lag HAC and all subperiods. These are correlated exploratory estimates, not independent confirmatory tests. Tables contain only aggregate estimates. Raw vendor data, stock-level derived records and local file-path manifests are excluded from this public report.", ""]
    (docs / "results.md").write_text("\n".join(lines))
    print(docs / "results.md")
    print(assets / "robustness.png")


if __name__ == "__main__":
    main()
