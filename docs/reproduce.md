# Reproduce the calculations

The public demonstration requires no provider account, private data, API key,
or network connection after dependencies are installed. It runs the same
baseline code used for the local research sample, using clearly marked
synthetic inputs.

## Environment

Use Python 3.11. From the repository root, create an isolated environment and
install the direct dependency versions used in the verified local run:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tested.txt
```

On Windows, activate with `.venv\Scripts\activate` instead. The version list
pins direct dependencies, not the full transitive environment or operating
system. Package versions and code hashes are recorded in each run manifest.

## One-command public demonstration

```bash
python scripts/make_demo_data.py --run
```

This creates `outputs/synthetic_inputs/`, runs the baseline into
`outputs/demo/`, renders PNG and SVG figures, and runs the independent output
validator and unit tests. `outputs/demo/validation.json` records the result.
The report and every figure are marked **synthetic software demo**. Synthetic
outputs must never be presented as empirical findings about real stocks.

The fixed seed is `20261004`. The default fixture has 6,000 invented
`DEMO*.SYN` identifiers and 26 monthly price endpoints, yielding 24 holding
months after the required return and formation lags. Each month independently
draws a fair common sign and bounded pair-specific return magnitudes. The
conditional expected next-month return is zero. There is no planted DS or
momentum effect. Paired stocks share prices and shocks to exercise exact ties.
The same-sign cross sections are an intentional software fixture that keeps
all target cells populated, not a realistic market model. No licensed input
values or real stock identifiers are copied.

Re-running the command replaces only directories bearing the synthetic marker.
It refuses to overwrite nonempty, unmarked directories. Optional size and
location controls are available through `python scripts/make_demo_data.py --help`.
Very small fixtures can fail the baseline's 20-stock minimum; the documented
default exercises all cells without changing that threshold.

## Individual stages

```bash
python -m unittest discover -s tests -v
python scripts/make_demo_data.py
python scripts/run_baseline.py --data-dir outputs/synthetic_inputs --output-dir outputs/demo
python scripts/plot_results.py --output-dir outputs/demo --hac-lags 3 --synthetic
python scripts/validate_outputs.py --data-dir outputs/synthetic_inputs --output-dir outputs/demo
```

Prefer the one-command demo for shareable outputs: it also adds the synthetic
notice to the generated report and copies the fixture manifest. Do not remove
`--synthetic` when plotting generated demo data. For a same-environment
determinism check, run the baseline into a second directory, then pass that
directory to the validator with `--repeat-output-dir`.

## Licensed local data

The research baseline reads these three Parquet files from a directory you
provide. Raw files are not included in this repository.

| File | Required columns | Meaning |
|---|---|---|
| `close.parquet` | `TRADE_DT`, `S_INFO_WINDCODE`, `S_DQ_CLOSE`, `S_DQ_ADJFACTOR` | Date, stable stock identifier, close, multiplicative price-adjustment factor |
| `value.parquet` | `TRADE_DT`, `S_INFO_WINDCODE`, `S_VAL_MV` | Date, stock identifier, positive capitalization used for formation weights |
| `industry.parquet` | `date`, `wind_code`, `ind` | Date, stock identifier, dated industry label |

Date columns must be timestamp-compatible. Within each input, date and stock
identify a unique row. Capitalization units must be consistent across stocks.
Price-adjustment conventions and the historical validity of classifications
must be established separately; accepting a schema does not establish these.

The monthly builder selects the global last observed price date per month.
It requires both adjacent calendar endpoints for returns and joins
capitalization and industry only on the formation endpoint. The example
generator supplies only those endpoints; real daily files are also accepted.

```bash
python scripts/run_baseline.py --data-dir /path/to/licensed-inputs --output-dir outputs
python scripts/plot_results.py --output-dir outputs --hac-lags 3
python scripts/validate_outputs.py --data-dir /path/to/licensed-inputs --output-dir outputs
```

Keep the output directory outside the input directory. The runner hashes
inputs and checks preservation. Stock-level derived files, identifiers, local
paths, and manifests remain under the ignored `outputs/` directory. Public
redistribution of provider-derived material requires separate review of the
provider's terms.

## Local data audit and optional rate sensitivity

After the baseline finishes, the local audit reads its saved memberships and
the original price inputs. It writes observation classifications and source
checks under `outputs/data_quality/` without changing the baseline tables:

```bash
python scripts/audit_data_quality.py --data-dir /path/to/licensed-inputs --output-dir outputs
```

For the optional interest-rate sensitivity, supply a locally saved FRED CSV
containing `observation_date` and `IR3TTS01CNM156N` columns:

```bash
python scripts/audit_data_quality.py --data-dir /path/to/licensed-inputs --output-dir outputs --rf-csv /path/to/local/fred_IR3TTS01CNM156N.csv
```

Neither command downloads data. The audit may reuse a rate snapshot already
stored under `outputs/data_quality/`. The rate input, stock-level audit outputs,
and provenance records stay local. The normalized rate file is
`outputs/data_quality/rf_proxy_monthly.csv`, the path selected by
`configs/robustness.json`. Run this audit before hypothesis evaluation if the
optional sensitivity is wanted. Annual quoted percentage yield divided by
100 and 12 is a retrospective carry proxy, not a verified contemporaneous
cash return. Missing source observations are not filled.

## Fixed hypothesis evaluation and aggregate report

These commands use the completed baseline and the fixed specifications in
`configs/robustness.json` and `docs/research_protocol.md`:

```bash
python scripts/evaluate_hypothesis.py --baseline-dir outputs --output-dir outputs/research
python scripts/build_research_report.py --baseline-output outputs --research-output outputs/research --docs-dir docs
```

`outputs` holds the baseline; `outputs/research` holds the subsequent
comparisons and regressions. The evaluation verifies the saved monthly panel's
hash and checks that baseline files remain unchanged. Rate sensitivity runs
only when the configured normalized rate file exists. The report builder
writes aggregate tables, figures, and `docs/results.md`; it does not publish
them to GitHub.

The supplied protocol and report narrative describe the documented 2021–2025
A-share study. They are not a generic report template for a different date
range or the synthetic fixture. Keep demo outputs under `outputs/demo`, and
adapt the protocol and study-specific narrative before using another dataset.

## Validation and CI scope

The test suite exercises return timing, missing endpoints, future-data
independence, ties, fixed weights, raw holding returns, missing holdings,
minimum cell sizes, matched spreads, and HAC arithmetic. The separate validator
reconstructs portfolio arithmetic and selected price returns from saved files,
checks source hashes, and records tests in `validation.json`.

The GitHub workflow discovers every `tests/test_*.py` file, including the
hypothesis and data-quality fixtures, and runs the synthetic demonstration
without private data or network-dependent tests. Its existence does not imply
a successful hosted run. Passing a local or
hosted check supports software consistency, not economic validity, historical
point-in-time availability, tradability, or future investment performance.

Research context remains Chen, Wang and Yu,
[Salience and Short-term Momentum and Reversals](https://ssrn.com/abstract=4649393).
This baseline uses an industry-peer, zero-risk-free-rate adaptation; neither
the synthetic fixture nor its generated numbers replicate the paper's results.
