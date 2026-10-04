# Deviation Salience in Chinese Equities

[![Tests](https://github.com/skylarhezhentian/DeviationSalience-ShortTermMomentum-Reversal/actions/workflows/tests.yml/badge.svg)](https://github.com/skylarhezhentian/DeviationSalience-ShortTermMomentum-Reversal/actions/workflows/tests.yml)

This project tests whether stocks that move unusually relative to their industry peers are more likely to reverse the following month. The question helps distinguish two explanations for a recent price move: information that continues to affect returns, or a temporary reaction that unwinds.

## Method

Using Chinese equity data from January 2021 to November 2025, the analysis measures each stock's deviation from its industry peers, sorts stocks by that signal and their past-month return, and compares next-month winner-minus-loser returns. Portfolio membership and weights are fixed before future returns are joined.

The study also tests different universes and portfolio sizes, compares an unconditional return sort, and runs monthly cross-sectional regressions with size, momentum, and volatility controls. See the [method and assumptions](docs/research_protocol.md).

## Results

The main comparison is **low-salience minus high-salience winner-minus-loser returns**:

| Weighting | Mean per month | HAC t-statistic | 95% confidence interval |
|---|---:|---:|---:|
| Equal | +0.156% | 0.10 | [−2.909%, +3.221%] |
| Market capitalization | +1.227% | 0.80 | [−1.794%, +4.248%] |

Both estimates use 36 complete months out of a 57-month holding window. The intervals include zero across all seven specifications, so this sample does not establish the proposed effect. Unresolved holding returns and trading constraints remain limitations.

[Full results and figure](docs/results.md) · [Aggregate result tables](docs/tables/full/) · [Data audit](docs/data_sources.md)

## Run

Requires **Python 3.11** and Git. On macOS or Linux:

```bash
git clone https://github.com/skylarhezhentian/DeviationSalience-ShortTermMomentum-Reversal.git deviation-salience
cd deviation-salience
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tested.txt
python scripts/run_demo.py
```

The demo uses the synthetic dataset included in `data/sample/`. It writes a report, charts, and validation results to `outputs/demo/`; no data account or download is needed. Its results demonstrate the software and are separate from the historical findings above.

Run tests with `python -m unittest discover -s tests -v`. [Reproduction instructions](docs/reproduce.md) cover Windows, individual commands, and the historical analysis.

## Files

| Folder | Contents |
|---|---|
| `data/` | Included synthetic sample, input schema, and data notes |
| `src/` | Return calculations, salience signal, portfolios, and statistical tests |
| `scripts/` | Commands to run the demo, audit data, evaluate the hypothesis, and build reports |
| `configs/` | Robustness specifications; baseline settings are in `config.json` |
| `tests/` | Tests for timing, ties, missing returns, inference, and file handling |
| `docs/` | Methods, results, figures, and aggregate tables; earlier proposals are in `docs/archive/` |
| `.github/` | Automated tests and a demo run on every push |
| `outputs/` | Generated local files; excluded from Git |

## Data and reference

The historical market data were supplied by a company and are not distributed here. Reproducing those estimates requires authorized access to the original inputs. The repository includes all data needed for the synthetic demo, along with the historical study's aggregate results. See [data details](data/README.md).

The research question comes from Chen, Wang and Yu, [*Salience and Short-term Momentum and Reversals*](https://ssrn.com/abstract=4649393). This project uses an industry-peer adaptation. The historical analysis is exploratory and does not establish an executable trading strategy.
