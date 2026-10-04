#!/usr/bin/env python3
"""Run the included synthetic sample without generating or changing input data."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.make_demo_data import run_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/sample",
                        help="Synthetic sample directory containing its manifest and three Parquet files")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/demo")
    args = parser.parse_args()
    run_demo(args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
