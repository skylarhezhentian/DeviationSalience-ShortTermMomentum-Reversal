#!/usr/bin/env python3
"""Generate a deterministic, wholly synthetic fixture; optionally run the demo.

This is a software demonstration, not market data, a realistic market model,
or evidence about an investment hypothesis. No private inputs are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KIND = "synthetic_software_fixture"
MARKER = "SYNTHETIC_DATA.json"
DEFAULT_SEED = 20261004
DATA_FILES = ("close.parquet", "value.parquet", "industry.parquet")


def make_inputs(stocks=6000, holding_months=24, seed=DEFAULT_SEED):
    """Return three frames with the public input schema and no real stock data.

    Every month independently draws a fair common sign and pair-specific
    magnitudes. Thus next month's stock return has conditional mean zero,
    independent of past returns and DS. Pairs share prices/shocks to exercise
    exact ties. Same-sign cross sections keep the nominal DS groups populated
    for the end-to-end software example; this is not a market assumption.
    """
    if stocks < 4 or stocks % 2:
        raise ValueError("stocks must be an even integer of at least 4")
    if holding_months < 1:
        raise ValueError("holding_months must be positive")
    rng = np.random.default_rng(seed)
    pairs = stocks // 2
    endpoint_count = holding_months + 2
    dates = pd.date_range("2000-01-01", periods=endpoint_count, freq="BME")
    codes = np.array([f"DEMO{i + 1:06d}.SYN" for i in range(stocks)])
    industry_count = min(20, max(1, pairs // 2))
    industries = np.array([f"SYNTHETIC_INDUSTRY_{(i // 2) % industry_count + 1:02d}"
                           for i in range(stocks)])
    starting_prices = rng.uniform(20.0, 80.0, size=pairs)
    # No lagged return, DS, stock ID, or future observation enters these draws.
    signs = rng.choice(np.array([-1.0, 1.0]), size=(endpoint_count - 1, 1))
    magnitudes = rng.uniform(0.005, 0.08, size=(endpoint_count - 1, pairs))
    pair_returns = signs * magnitudes
    paired_prices = np.vstack([starting_prices,
                               starting_prices * np.cumprod(1.0 + pair_returns, axis=0)])
    prices = np.repeat(paired_prices, 2, axis=1)
    shares = np.exp(rng.uniform(12.0, 16.0, size=stocks))
    keys = {"TRADE_DT": np.repeat(dates.to_numpy(), stocks),
            "S_INFO_WINDCODE": np.tile(codes, endpoint_count)}
    close = pd.DataFrame({**keys, "S_DQ_CLOSE": prices.ravel(), "S_DQ_ADJFACTOR": 1.0})
    value = pd.DataFrame({**keys, "S_VAL_MV": (prices * shares).ravel()})
    industry = pd.DataFrame({"date": keys["TRADE_DT"],
                             "wind_code": keys["S_INFO_WINDCODE"],
                             "ind": np.tile(industries, endpoint_count)})
    return close, value, industry


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_inputs(directory):
    """Check the declared fixture and all its hashes without writing to it."""
    directory = Path(directory).resolve()
    manifest = json.loads((directory / MARKER).read_text())
    if manifest.get("dataset_kind") != KIND:
        raise ValueError("Expected a clearly marked synthetic software fixture")
    hashes = manifest.get("source_sha256", {})
    if set(hashes) != set(DATA_FILES):
        raise ValueError("Synthetic manifest must name exactly the three expected input files")
    for filename in DATA_FILES:
        path = directory / filename
        if not path.is_file() or sha256(path) != hashes[filename]:
            raise ValueError(f"Synthetic input integrity check failed: {filename}")
    return manifest


def write_inputs(directory, stocks=6000, holding_months=24, seed=DEFAULT_SEED):
    directory = Path(directory).resolve()
    if directory.exists() and any(directory.iterdir()):
        marker = directory / MARKER
        if not marker.is_file() or json.loads(marker.read_text()).get("dataset_kind") != KIND:
            raise ValueError("Refusing to write into a nonempty directory not marked as synthetic")
    directory.mkdir(parents=True, exist_ok=True)
    frames = make_inputs(stocks, holding_months, seed)
    for filename, frame in zip(DATA_FILES, frames):
        frame.to_parquet(directory / filename, index=False)
    manifest = {
        "dataset_kind": KIND,
        "schema_version": 1,
        "warning": "SYNTHETIC SOFTWARE DEMO. Not real stock data or research evidence.",
        "seed": seed,
        "stocks": stocks,
        "holding_months": holding_months,
        "endpoint_months": holding_months + 2,
        "rows_per_input": len(frames[0]),
        "identifiers": "Invented DEMO*.SYN identifiers; no licensed values are copied.",
        "return_model": "Independent monthly fair sign times bounded pair-specific magnitude. Conditional expected next-month return is zero.",
        "ties": "Each pair shares prices and shocks. Tied signals are deliberately present.",
        "purpose": "Exercise schema, grouping, fixed weights, reports, plots, and validation; not realistic market simulation.",
        "source_sha256": {name: sha256(directory / name) for name in DATA_FILES},
    }
    (directory / MARKER).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def run_demo(data_dir, output_dir):
    data_dir, output_dir = Path(data_dir).resolve(), Path(output_dir).resolve()
    verify_inputs(data_dir)
    source_hashes = {name: sha256(data_dir / name) for name in (*DATA_FILES, MARKER)}
    if output_dir == data_dir or data_dir in output_dir.parents:
        raise ValueError("Demo output must be outside the synthetic input directory")
    if output_dir.exists() and any(output_dir.iterdir()):
        marker = output_dir / MARKER
        if not marker.is_file() or json.loads(marker.read_text()).get("dataset_kind") != KIND:
            raise ValueError("Refusing to overwrite outputs not marked as a synthetic demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / MARKER).write_text((data_dir / MARKER).read_text())
    config = json.loads((ROOT / "config.json").read_text())
    commands = [
        [sys.executable, str(ROOT / "scripts/run_baseline.py"), "--data-dir", str(data_dir), "--output-dir", str(output_dir)],
        [sys.executable, str(ROOT / "scripts/plot_results.py"), "--output-dir", str(output_dir),
         "--hac-lags", str(config["hac_lags"]), "--synthetic"],
        [sys.executable, str(ROOT / "scripts/validate_outputs.py"), "--data-dir", str(data_dir), "--output-dir", str(output_dir)],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    if any(sha256(data_dir / name) != expected for name, expected in source_hashes.items()):
        raise RuntimeError("Synthetic source files changed during the demonstration")
    report = output_dir / "RESULTS.md"
    report.write_text("# SYNTHETIC SOFTWARE DEMO\n\n"
                      "These outputs use invented identifiers and generated prices. They test the software only and provide no evidence about real returns or deviation salience. The generated baseline report below describes the software's calculations.\n\n"
                      + report.read_text())
    print(f"Synthetic demo completed: {output_dir}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stocks", type=int, default=6000)
    parser.add_argument("--holding-months", type=int, default=24)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "outputs/synthetic_inputs")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/demo")
    parser.add_argument("--run", action="store_true", help="Run baseline, synthetic-labeled figures, and independent validation")
    args = parser.parse_args()
    metadata = write_inputs(args.data_dir, args.stocks, args.holding_months, args.seed)
    print(json.dumps(metadata, indent=2), flush=True)
    if args.run:
        run_demo(args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
