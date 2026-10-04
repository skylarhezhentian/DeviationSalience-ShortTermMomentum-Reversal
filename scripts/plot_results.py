"""Plot saved baseline estimates without rerunning or changing the analysis.

Usage:
    python scripts/plot_results.py --output-dir outputs

Input returns and confidence limits are decimal returns. Only display units
are converted to percent. Figures are written to OUTPUT_DIR/figures.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd


WEIGHTINGS = (("equal", "Equal-weighted", "#167D9A"),
              ("value", "Value-weighted", "#394B81"))
DS_SERIES = [f"WML_DS{i}" for i in range(1, 6)]
DS_LABELS = ["1\nLow DS", "2", "3", "4", "5\nHigh DS"]
NOTES = (
    "Descriptive sample. DS is an industry-peer proxy with the risk-free return set to zero. Strict complete-return handling.",
    "Statistical portfolio returns before trading costs; execution is not modeled. Values are read from saved estimates.",
)


def load_csv(path: Path, required: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    unknown = set(frame["weighting"].dropna()) - {item[0] for item in WEIGHTINGS}
    if unknown:
        raise ValueError(f"{path.name}: unknown weightings {sorted(unknown)}")
    return frame


def check_unique(frame: pd.DataFrame, keys: list[str], name: str) -> None:
    if frame.duplicated(keys).any():
        raise ValueError(f"{name}: duplicate keys {keys}")


def sample_label(monthly: pd.DataFrame, weighting: str | None = None) -> str:
    sample = monthly.loc[monthly["series"].isin(DS_SERIES)].copy()
    if weighting is not None:
        sample = sample.loc[sample["weighting"].eq(weighting)]
    sample = sample.loc[pd.to_numeric(sample["ret"], errors="coerce").notna()]
    dates = pd.to_datetime(sample["holding_month"], errors="raise")
    if dates.empty:
        return "No estimable holding months"
    return f"{dates.min():%b %Y} – {dates.max():%b %Y}"


def numeric_row(row: pd.Series, columns: list[str]) -> np.ndarray:
    return pd.to_numeric(row[columns], errors="coerce").to_numpy(dtype=float)


def contrast_label(summary: pd.DataFrame, weighting: str) -> str:
    rows = summary.loc[(summary["weighting"] == weighting)
                       & (summary["series"] == "LowDS_minus_HighDS")]
    if len(rows) != 1:
        raise ValueError(f"Expected one LowDS_minus_HighDS row for {weighting}")
    mean, low, high = numeric_row(rows.iloc[0], ["mean", "ci_low", "ci_high"]) * 100
    if not np.isfinite([mean, low, high]).all():
        return "Low DS minus high DS: not estimable"
    count = int(rows.iloc[0]["n"])
    return (f"Low DS minus high DS: {mean:+.2f}% per month\n"
            f"HAC 95% CI [{low:+.2f}%, {high:+.2f}%]; n = {count} matched months")


def save_figure(fig: plt.Figure, directory: Path, stem: str, synthetic: bool = False) -> None:
    if synthetic:
        fig.text(0.07, 0.975, "SYNTHETIC SOFTWARE DEMO — NOT RESEARCH EVIDENCE",
                 fontsize=10, weight="bold", color="#965300")
    for extension in ("png", "svg"):
        path = directory / f"{stem}.{extension}"
        fig.savefig(path, dpi=200, facecolor="white")
        print(path)
    plt.close(fig)


def plot_wml(summary: pd.DataFrame, monthly: pd.DataFrame,
             directory: Path, hac_lags: int | None, synthetic: bool = False) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 9.0), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.97, bottom=0.355, top=0.765, wspace=0.16)
    fig.text(0.075, 0.943, "Next-month winner–loser returns by deviation salience",
             fontsize=18, weight="bold", color="#182A39")
    fig.text(0.075, 0.899,
             "Prior-month return group 10 minus group 1, within each DS group",
             fontsize=11.5, color="#465968")
    lag_note = f"; {hac_lags} lags" if hac_lags is not None else ""
    fig.text(0.075, 0.859,
             f"Holding months: {sample_label(monthly)}  |  Points: monthly means; bars: HAC 95% CI{lag_note}",
             fontsize=10.5, color="#465968")

    plotted_limits: list[float] = [0.0]
    for ax, (weighting, label, color) in zip(axes, WEIGHTINGS):
        subset = summary.loc[summary["weighting"].eq(weighting)].set_index("series")
        if not set(DS_SERIES).issubset(subset.index):
            raise ValueError(f"Missing WML DS groups for {weighting}")
        subset = subset.loc[DS_SERIES]
        means = pd.to_numeric(subset["mean"], errors="coerce").to_numpy() * 100
        lows = pd.to_numeric(subset["ci_low"], errors="coerce").to_numpy() * 100
        highs = pd.to_numeric(subset["ci_high"], errors="coerce").to_numpy() * 100
        valid = np.isfinite(means) & np.isfinite(lows) & np.isfinite(highs)
        if np.any(lows[valid] > means[valid]) or np.any(highs[valid] < means[valid]):
            raise ValueError(f"Confidence limits do not contain the mean for {weighting}")
        x = np.arange(1, 6)
        ax.axhline(0, color="#6B7780", linestyle="--", linewidth=1, zorder=1)
        ax.errorbar(x[valid], means[valid],
                    yerr=np.vstack((means[valid] - lows[valid], highs[valid] - means[valid])),
                    fmt="o", markersize=7, color=color, ecolor=color,
                    elinewidth=2, capsize=5, capthick=1.6, zorder=3)
        for xi, value, is_valid in zip(x, means, valid):
            if is_valid:
                ax.annotate(f"{value:+.2f}", (xi, value), xytext=(9, 0),
                            textcoords="offset points", fontsize=9.5,
                            ha="left", va="center", color=color)
            else:
                ax.text(xi, 0.02, "n.a.", transform=ax.get_xaxis_transform(),
                        ha="center", color="#707A84", fontsize=9)
        counts = pd.to_numeric(subset["n"], errors="coerce").dropna()
        if counts.empty:
            n_text = "n unavailable"
        elif counts.min() == counts.max():
            n_text = f"n = {int(counts.min())} months per group"
        else:
            n_text = f"n = {int(counts.min())}–{int(counts.max())} months per group"
        ax.set_title(f"{label}\n{n_text}", fontsize=12, loc="left", pad=14,
                     color="#182A39", linespacing=1.6)
        tick_labels = [f"{label}\n(n={int(count)})" if pd.notna(count) else label
                       for label, count in zip(DS_LABELS, pd.to_numeric(subset["n"], errors="coerce"))]
        ax.set_xticks(x, tick_labels)
        ax.set_xlim(0.55, 5.7)
        ax.set_xlabel("Deviation-salience group", labelpad=10)
        ax.grid(axis="y", color="#E4E9ED", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#B7C2CB")
        ax.tick_params(length=0, pad=7, labelcolor="#334858")
        plotted_limits.extend(lows[valid].tolist())
        plotted_limits.extend(highs[valid].tolist())
        position = ax.get_position()
        fig.text(position.x0, 0.182, contrast_label(summary, weighting),
                 fontsize=10.4, color="#334858", linespacing=1.7)
    low, high = min(plotted_limits), max(plotted_limits)
    margin = max((high - low) * 0.14, 0.15)
    axes[0].set_ylim(low - margin, high + margin)
    axes[0].set_ylabel("Mean next-month return (% per month)", labelpad=12)
    fig.text(0.075, 0.124,
             "Each WML mean uses its own available months; the low-minus-high contrast uses only their matched months.",
             fontsize=9.2, color="#556774")
    fig.text(0.075, 0.105, "Tied signals stay together; groups may be unequal.",
             fontsize=9.2, color="#556774")
    fig.text(0.075, 0.089, NOTES[0], fontsize=9.2, color="#556774")
    fig.text(0.075, 0.058, NOTES[1], fontsize=9.2, color="#556774")
    fig.text(0.075, 0.027,
             "HAC intervals use normal 1.96 limits without finite-sample correction; missing calendar-month positions are retained.",
             fontsize=9.2, color="#556774")
    save_figure(fig, directory, "wml_by_ds", synthetic)


def plot_heatmaps(portfolios: pd.DataFrame, monthly: pd.DataFrame,
                  directory: Path, synthetic: bool = False) -> None:
    matrices = []
    for weighting, _, _ in WEIGHTINGS:
        subset = portfolios.loc[portfolios["weighting"].eq(weighting)].copy()
        subset["mean"] = pd.to_numeric(subset["mean"], errors="coerce")
        matrix = subset.pivot(index="ds_bin", columns="ret_bin", values="mean")
        matrices.append(matrix.reindex(index=range(1, 6), columns=range(1, 11)) * 100)
    values = np.concatenate([matrix.to_numpy().ravel() for matrix in matrices])
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("No finite portfolio means available for heatmaps")
    extent = max(float(np.abs(finite).max()), 0.01)
    norm = TwoSlopeNorm(vmin=-extent, vcenter=0, vmax=extent)
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad("#E8EDF1")

    fig, axes = plt.subplots(1, 2, figsize=(15.2, 6.8))
    fig.subplots_adjust(left=0.07, right=0.915, bottom=0.295, top=0.715, wspace=0.22)
    fig.text(0.07, 0.93, "Mean next-month returns across 50 sorted portfolios",
             fontsize=18, weight="bold", color="#182A39")
    fig.text(0.07, 0.88,
             f"Holding months: {sample_label(monthly)}  |  Monthly arithmetic means (%); common color scale",
             fontsize=11, color="#465968")
    for ax, matrix, (_, label, _) in zip(axes, matrices, WEIGHTINGS):
        array = matrix.to_numpy()
        im = ax.imshow(np.ma.masked_invalid(array), cmap=cmap, norm=norm, aspect="auto")
        ax.set_title(label, loc="left", fontsize=12, pad=13, color="#182A39")
        ax.set_xticks(range(10), range(1, 11))
        ax.set_yticks(range(5), ["1 (low)", "2", "3", "4", "5 (high)"])
        ax.set_xlabel("Prior-month return group (1 = lowest, 10 = highest)", labelpad=10)
        ax.set_ylabel("DS group", labelpad=8)
        ax.tick_params(length=0, pad=7)
        for row in range(5):
            for col in range(10):
                value = array[row, col]
                text = f"{value:.2f}" if np.isfinite(value) else "n.a."
                color = "white" if np.isfinite(value) and abs(value) > extent * 0.62 else "#182A39"
                ax.text(col, row, text, ha="center", va="center", color=color, fontsize=9)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks(np.arange(-0.5, 10, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.2)
        ax.tick_params(which="minor", bottom=False, left=False)
    colorbar_ax = fig.add_axes([0.936, 0.295, 0.012, 0.42])
    colorbar = fig.colorbar(im, cax=colorbar_ax)
    colorbar.set_label("% per month", labelpad=9)
    colorbar.outline.set_visible(False)
    fig.text(0.07, 0.184, "Cell means may use different available months. Color represents the mean return, not statistical significance.",
             fontsize=10, color="#334858")
    fig.text(0.07, 0.150, "Tied signals stay together; groups may be unequal.",
             fontsize=9.4, color="#556774")
    fig.text(0.07, 0.119, NOTES[0], fontsize=9.4, color="#556774")
    fig.text(0.07, 0.081, NOTES[1], fontsize=9.4, color="#556774")
    save_figure(fig, directory, "portfolio_return_heatmaps", synthetic)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="Directory containing the three saved result CSV files")
    parser.add_argument("--hac-lags", type=int, default=None,
                        help="Optional label only; must match the analysis that produced the CSVs")
    parser.add_argument("--synthetic", action="store_true",
                        help="Mark every figure as a synthetic software demo, not research evidence")
    args = parser.parse_args()
    if args.hac_lags is not None and args.hac_lags < 0:
        parser.error("--hac-lags must be nonnegative")
    statistics = {"weighting", "mean", "se", "t", "n", "ci_low", "ci_high"}
    portfolios = load_csv(args.output_dir / "portfolio_summary.csv",
                          statistics | {"ds_bin", "ret_bin"})
    spreads = load_csv(args.output_dir / "spread_summary.csv", statistics | {"series"})
    monthly = load_csv(args.output_dir / "monthly_spreads.csv",
                       {"holding_month", "weighting", "series", "ret"})
    check_unique(portfolios, ["weighting", "ds_bin", "ret_bin"], "portfolio_summary.csv")
    check_unique(spreads, ["weighting", "series"], "spread_summary.csv")
    check_unique(monthly, ["holding_month", "weighting", "series"], "monthly_spreads.csv")
    directory = args.output_dir / "figures"
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.labelcolor": "#334858", "svg.fonttype": "none"})
    plot_wml(spreads, monthly, directory, args.hac_lags, args.synthetic)
    plot_heatmaps(portfolios, monthly, directory, args.synthetic)


if __name__ == "__main__":
    main()
