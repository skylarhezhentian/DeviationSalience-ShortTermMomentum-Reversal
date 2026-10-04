#!/usr/bin/env python3
"""Independently audit saved baseline outputs and their original-file provenance.

No baseline calculation functions are imported. Source data are read only.
Passing these checks establishes arithmetic/provenance consistency, not economic
validity, point-in-time data correctness, or executable trading performance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ATOL, RTOL = 5e-12, 5e-10  # CSVs intentionally retain twelve significant digits.


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def numeric_equal(left, right):
    return bool(np.allclose(np.asarray(left, dtype=float), np.asarray(right, dtype=float),
                            atol=ATOL, rtol=RTOL, equal_nan=True))


def finite_mean(values):
    values = np.asarray(values, dtype=float)
    good = values[np.isfinite(values)]
    return float(good.mean()) if len(good) else np.nan


def unittest_cache_identity(root=ROOT):
    """Fingerprint imported code, bundled fixtures, and the execution environment."""
    root = Path(root)
    paths = set()
    for folder in ("src", "scripts", "tests"):
        paths.update((root / folder).rglob("*.py"))
    paths.update((root / "configs").rglob("*.json"))
    for name in ("requirements.txt", "requirements-tested.txt", "config.json"):
        if (root / name).is_file():
            paths.add(root / name)
    sample = root / "data" / "sample"
    if sample.is_dir():
        paths.update(path for path in sample.rglob("*") if path.is_file())
    signature = {str(path.relative_to(root)): digest(path) for path in sorted(paths)}
    versions = {}
    for package in ("numpy", "pandas", "pyarrow", "matplotlib", "scipy", "statsmodels"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    environment = {"executable": str(Path(sys.executable).resolve()), "version": sys.version,
                   "implementation": sys.implementation.name, "platform": sys.platform,
                   "packages": versions}
    return signature, environment


def validate(data, out, repeat, result):
    def check(name, passed, **details):
        result["checks"].append({"name": name, "passed": bool(passed), **details})
        if not passed:
            raise AssertionError(name)

    manifest = read_json(out / "run_manifest.json")
    inputs = read_json(out / "input_manifest.json")
    diagnostics = read_json(out / "diagnostics.json")
    config = manifest["config"]

    for entry in inputs:
        path = data / entry["name"]
        check("original_data_sha256:" + entry["name"], digest(path) == entry["sha256"],
              bytes=path.stat().st_size)
    originals = manifest["original_research_sha256"]
    for original, expected in originals.items():
        # Resolve by filename under the explicitly supplied original directory.
        path = data / Path(original).name
        check("original_research_sha256:" + path.name, digest(path) == expected)
    for filename, expected in manifest["output_sha256"].items():
        check("saved_output_sha256:" + filename, digest(out / filename) == expected)

    panel = pd.read_parquet(out / "monthly_panel.parquet")
    members = pd.read_parquet(out / "memberships.parquet")
    cells = pd.read_csv(out / "portfolio_returns.csv")
    spreads = pd.read_csv(out / "monthly_spreads.csv")
    spread_summary = pd.read_csv(out / "spread_summary.csv")
    cell_summary = pd.read_csv(out / "portfolio_summary.csv")
    panel["month"] = pd.PeriodIndex(panel["month"], freq="M")
    for frame in (members, cells):
        for col in ("formation_month", "holding_month"):
            frame[col] = pd.PeriodIndex(frame[col], freq="M")
    spreads["holding_month"] = pd.PeriodIndex(spreads["holding_month"], freq="M")
    check("unique_panel_stock_month", not panel.duplicated(["stock", "month"]).any(), rows=len(panel))
    check("unique_membership_stock_month", not members.duplicated(["stock", "formation_month"]).any(), rows=len(members))
    cell_keys = ["formation_month", "ds_bin", "ret_bin"]
    check("unique_cell_records", not cells.duplicated(cell_keys + ["weighting"]).any(), rows=len(cells))
    check("strict_holding_calendar", members["holding_month"].eq(members["formation_month"] + 1).all()
          and cells["holding_month"].eq(cells["formation_month"] + 1).all())

    source = panel.set_index(["stock", "month"])
    formation_index = pd.MultiIndex.from_frame(members[["stock", "formation_month"]])
    holding_index = pd.MultiIndex.from_frame(members[["stock", "holding_month"]])
    formed_source = source.reindex(formation_index)
    held_source = source.reindex(holding_index)
    check("formation_fields_from_saved_panel",
          numeric_equal(members[["ret", "price", "cap"]], formed_source[["ret", "price", "cap"]])
          and np.array_equal(members["industry"].to_numpy(), formed_source["industry"].to_numpy()))
    expected_future = held_source["price"].to_numpy() / formed_source["price"].to_numpy() - 1
    expected_future[~np.isfinite(expected_future)] = np.nan
    check("holding_returns_are_raw_adjacent_endpoint_ratios", numeric_equal(members["future_ret"], expected_future),
          known=int(np.isfinite(expected_future).sum()), missing=int(np.isnan(expected_future).sum()))
    check("holding_returns_match_exact_next_calendar_panel_row", numeric_equal(members["future_ret"], held_source["ret"]))

    eligible = panel.loc[np.isfinite(panel["ret"]) & np.isfinite(panel["cap"]) & panel["cap"].gt(0)
                         & panel["industry"].notna() & panel["industry"].astype(str).str.len().gt(0)
                         & panel["month"].lt(panel["month"].max())].copy()
    peer_groups = list(eligible.groupby(["month", "industry"], sort=True))
    expected_rows = []
    direct_peer_checks = 0
    # Explicitly remove the focal stock rather than subtracting it from a group sum.
    # Audit every stock in 24 deterministic industry/month subgroups this way.
    sample_groups = set(np.linspace(0, len(peer_groups) - 1, min(24, len(peer_groups)), dtype=int))
    expected_keys = set()
    for position, ((month, industry), group) in enumerate(peer_groups):
        n = len(group)
        r = group["ret"].to_numpy()
        peers = (r.sum() - r) / (n - 1) if n > 1 else np.full(n, np.nan)
        denominator = np.abs(r) + np.abs(peers)
        with np.errstate(divide="ignore", invalid="ignore"):
            ds = np.abs(r - peers) / denominator
        good = np.isfinite(ds) & (n - 1 >= config["min_peers"])
        for stock, peer, signal, valid in zip(group["stock"], peers, ds, good):
            if valid:
                expected_keys.add((stock, month))
                expected_rows.append((stock, month, peer, signal, n - 1))
        if position in sample_groups and n > 1:
            for i in range(n):
                direct = float(np.concatenate([r[:i], r[i + 1:]]).mean())
                if not numeric_equal(direct, peers[i]):
                    raise AssertionError("independent focal-stock exclusion")
                direct_peer_checks += 1
    actual_keys = set(zip(members["stock"], members["formation_month"]))
    check("formation_universe_uses_only_current_information", actual_keys == expected_keys,
          eligible_rows=len(eligible), expected_members=len(expected_keys))
    peer_check = pd.DataFrame(expected_rows, columns=["stock", "formation_month", "peer", "signal", "count"])
    peer_check = members.merge(peer_check, on=["stock", "formation_month"], validate="one_to_one")
    check("industry_leave_one_out_peers_and_ds",
          numeric_equal(peer_check["peer_ret"], peer_check["peer"])
          and numeric_equal(peer_check["ds"], peer_check["signal"])
          and np.array_equal(peer_check["peer_count"], peer_check["count"]),
          all_members=len(peer_check), directly_excluded_focal_stocks=direct_peer_checks,
          directly_checked_groups=len(sample_groups))

    # Independently obtain empirical-CDF labels with searchsorted rather than rank.
    for _, group in members.groupby("formation_month"):
        values = group["ds"].to_numpy()
        expected = np.ceil(np.searchsorted(np.sort(values), values, side="right") * config["ds_bins"] / len(values))
        if not np.array_equal(expected, group["ds_bin"]):
            raise AssertionError("DS empirical-CDF labels")
    for _, group in members.groupby(["formation_month", "ds_bin"]):
        values = group["ret"].to_numpy()
        expected = np.ceil(np.searchsorted(np.sort(values), values, side="right") * config["return_bins"] / len(values))
        if not np.array_equal(expected, group["ret_bin"]):
            raise AssertionError("return empirical-CDF labels")
    check("independent_tie_preserving_empirical_cdf_assignments", True, rows=len(members))

    grouped = {key: group for key, group in members.groupby(cell_keys)}
    weight_ok = True
    for group in grouped.values():
        weight_ok &= numeric_equal(group["weight_equal"], np.repeat(1 / len(group), len(group)))
        weight_ok &= numeric_equal(group["weight_value"], group["cap"] / group["cap"].sum())
        weight_ok &= numeric_equal(group[["weight_equal", "weight_value"]].sum(), [1, 1])
    check("fixed_formation_weights_and_unit_sums", weight_ok, occupied_cells=len(grouped))

    complete_count = 0
    for row in cells.itertuples(index=False):
        group = grouped.get((row.formation_month, row.ds_bin, row.ret_bin))
        n = 0 if group is None else len(group)
        if n:
            observed = np.isfinite(group["future_ret"].to_numpy())
            weights = group["weight_" + row.weighting].to_numpy()
            holding = group["future_ret"].to_numpy()
            count = int(observed.sum())
            coverage = float(weights[observed].sum())
            partial = float(np.dot(weights[observed], holding[observed]) / coverage) if coverage else np.nan
        else:
            count, coverage, partial = 0, 0.0, np.nan
        status = ("empty" if n == 0 else "below_minimum" if n < config["minimum_stocks_per_final_cell"]
                  else "missing_holding_return" if count < n else "complete")
        primary = partial if status == "complete" else np.nan
        if not (n == row.n_formed and count == row.n_observed and status == row.status
                and numeric_equal(coverage, row.observed_weight)
                and numeric_equal(partial, row.observed_only_ret) and numeric_equal(primary, row.ret)):
            raise AssertionError(f"cell arithmetic {row.formation_month}/{row.weighting}/{row.ds_bin}/{row.ret_bin}")
        complete_count += status == "complete"
    check("every_saved_cell_mean_status_and_coverage", True, records=len(cells), complete_records=complete_count,
          unavailable_primary_records=int(cells["ret"].isna().sum()))

    cell_lookup = cells.set_index(["holding_month", "weighting", "ds_bin", "ret_bin"])["ret"]
    for row in spreads.itertuples(index=False):
        def wml(ds):
            return (cell_lookup.loc[(row.holding_month, row.weighting, ds, config["return_bins"])]
                    - cell_lookup.loc[(row.holding_month, row.weighting, ds, 1)])
        expected = wml(1) - wml(config["ds_bins"]) if row.series == "LowDS_minus_HighDS" else wml(int(row.series.removeprefix("WML_DS")))
        if not numeric_equal(expected, row.ret):
            raise AssertionError("matched-month spread arithmetic")
    check("matched_month_wml_and_four_leg_interactions", True, records=len(spreads))
    for summary, monthly, keys in [(spread_summary, spreads, ["weighting", "series"]),
                                   (cell_summary, cells, ["weighting", "ds_bin", "ret_bin"])]:
        groups = {key: g["ret"] for key, g in monthly.groupby(keys)}
        for row in summary.to_dict("records"):
            values = groups[tuple(row[key] for key in keys)].to_numpy()
            if not (int(np.isfinite(values).sum()) == row["n"] and numeric_equal(finite_mean(values), row["mean"])):
                raise AssertionError("summary mean/sample count")
    check("spread_and_cell_summary_means_and_sample_counts", True,
          spread_summaries=len(spread_summary), cell_summaries=len(cell_summary))

    stocks = sorted(panel["stock"].unique())
    chosen = {stocks[i] for i in np.linspace(0, len(stocks) - 1, min(18, len(stocks)), dtype=int)}
    chosen.update(members.loc[[members["future_ret"].idxmax(), members["future_ret"].idxmin()], "stock"])
    chosen = sorted(chosen)
    raw = pd.read_parquet(data / "close.parquet", columns=["TRADE_DT", "S_INFO_WINDCODE", "S_DQ_CLOSE", "S_DQ_ADJFACTOR"],
                          filters=[("S_INFO_WINDCODE", "in", chosen)])
    raw["TRADE_DT"] = pd.to_datetime(raw["TRADE_DT"])
    calendar = {pd.Period(month, "M"): pd.Timestamp(date) for month, date in diagnostics["panel"]["calendar"].items()}
    raw_lookup = raw.set_index(["S_INFO_WINDCODE", "TRADE_DT"])
    original_endpoint_keys = set()
    original_endpoint_prices = {}
    for stock in chosen:
        for month, date in calendar.items():
            key = (stock, date)
            if key in raw_lookup.index:
                row = raw_lookup.loc[key]
                price = float(row.S_DQ_CLOSE * row.S_DQ_ADJFACTOR)
                if row.S_DQ_CLOSE <= 0 or row.S_DQ_ADJFACTOR <= 0 or not np.isfinite(price):
                    price = np.nan
                original_endpoint_keys.add((stock, month))
                original_endpoint_prices[(stock, month)] = price
    sampled_panel = panel[panel["stock"].isin(chosen)]
    check("sampled_original_endpoint_membership", set(zip(sampled_panel.stock, sampled_panel.month)) == original_endpoint_keys,
          stocks=len(chosen), endpoint_rows=len(sampled_panel))
    for row in sampled_panel.itertuples(index=False):
        price = original_endpoint_prices[(row.stock, row.month)]
        previous = original_endpoint_prices.get((row.stock, row.month - 1), np.nan)
        expected = price / previous - 1 if np.isfinite(previous) and previous > 0 else np.nan
        if not (numeric_equal(price, row.price) and numeric_equal(previous, row.previous_price)
                and numeric_equal(expected, row.ret) and row.date == calendar[row.month]):
            raise AssertionError("original raw endpoint/return trace")
    check("sampled_returns_recomputed_from_original_adjusted_prices", True,
          stocks=chosen, endpoint_rows=len(sampled_panel), raw_daily_rows=len(raw),
          includes_maximum_and_minimum_future_return_stocks=True)

    signature, execution_environment = unittest_cache_identity()
    previous_validation = read_json(out / "validation.json") if (out / "validation.json").exists() else {}
    old_tests = previous_validation.get("unittest", {})
    if (old_tests.get("source_and_test_sha256") == signature
            and old_tests.get("execution_environment") == execution_environment
            and old_tests.get("returncode") == 0):
        result["unittest"] = {**old_tests, "reused_matching_source_and_test_result": True}
    else:
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        transcript = completed.stdout + completed.stderr
        match = re.search(r"Ran (\d+) tests?", transcript)
        result["unittest"] = {"command": command, "cwd": str(ROOT), "returncode": completed.returncode,
                              "tests_run": int(match.group(1)) if match else None, "output": transcript,
                              "source_and_test_sha256": signature, "execution_environment": execution_environment,
                              "reused_matching_source_and_test_result": False}
    check("targeted_unittest_suite", result["unittest"]["returncode"] == 0,
          tests_run=result["unittest"]["tests_run"])

    if repeat:
        originals = {p.name: digest(p) for p in out.iterdir() if p.suffix in (".csv", ".parquet")}
        repeated = {p.name: digest(p) for p in repeat.iterdir() if p.suffix in (".csv", ".parquet")}
        check("deterministic_repeat_csv_and_parquet_sha256", originals == repeated,
              first_directory=str(out), repeat_directory=str(repeat), files=len(originals),
              first_sha256=originals, repeat_sha256=repeated)
    result["totals"] = {"panel_rows": len(panel), "membership_rows": len(members), "cell_records": len(cells),
                        "complete_cell_records": complete_count, "monthly_spread_records": len(spreads),
                        "original_data_files": len(inputs), "original_research_files": len(manifest["original_research_sha256"]),
                        "raw_spotcheck_stocks": len(chosen), "raw_spotcheck_endpoint_rows": len(sampled_panel)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--repeat-output-dir", type=Path)
    args = parser.parse_args()
    data, out = args.data_dir.resolve(), args.output_dir.resolve()
    repeat = args.repeat_output_dir.resolve() if args.repeat_output_dir else None
    if out == data or data in out.parents:
        raise ValueError("Validation output must be outside the original data directory")
    result = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": "running", "checks": [],
              "validator_sha256": digest(Path(__file__)), "data_directory": str(data), "output_directory": str(out),
              "scope": "Arithmetic, timing, membership, provenance, and selected raw-price trace checks only. No economic-validity, vendor-correction, tradability, or out-of-sample claim."}
    try:
        validate(data, out, repeat, result)
        result["status"] = "passed"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (out / "validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        print(json.dumps({"status": result["status"], "checks": len(result["checks"]),
                          "totals": result.get("totals"), "validation": str(out / "validation.json")}, indent=2))


if __name__ == "__main__":
    main()
