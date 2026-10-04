# Data

`sample/` contains everything needed to run the public demo: **synthetic prices, capitalization, and industry labels**. No company observations were copied or anonymized to make it.

The historical results in `docs/results.md` use a separate company-supplied dataset. Those inputs are not included. Keep company and vendor extracts private unless you have explicit permission for public redistribution; access for research does not itself establish that permission.

## Included sample

- 2,000 fictitious stocks named `DEMO000001.SYN`, etc.
- 26 monthly endpoints, January 2000–February 2002; 24 holding months.
- 52,000 rows per file, about 0.90 MB altogether.
- Generator seed: `20261004`.

The three files use the same column names as the research inputs:

| File | Columns | Meaning |
|---|---|---|
| `close.parquet` | `TRADE_DT`, `S_INFO_WINDCODE`, `S_DQ_CLOSE`, `S_DQ_ADJFACTOR` | Date, stock ID, price, multiplicative adjustment factor |
| `value.parquet` | `TRADE_DT`, `S_INFO_WINDCODE`, `S_VAL_MV` | Date, stock ID, capitalization |
| `industry.parquet` | `date`, `wind_code`, `ind` | Date, stock ID, industry label |

Dates and stock IDs uniquely identify rows. Prices and capitalization use arbitrary synthetic units; adjustment factors are one. Each pair of stocks shares prices to exercise tied signals. Monthly shocks have no planted momentum or salience effect. The sample deliberately fills all 50 portfolio cells; it is a software fixture, not a realistic market model.

`SYNTHETIC_DATA.json` records the generation settings and each file's SHA-256 hash. The demo verifies those hashes before reading the data:

```bash
python scripts/run_demo.py
```

To regenerate the sample into a separate local directory:

```bash
python scripts/make_demo_data.py --stocks 2000 --holding-months 24 --seed 20261004 --data-dir outputs/synthetic_inputs
```

Generation uses only the stated random model. The [reproduction guide](../docs/reproduce.md) explains how to run the same pipeline on authorized historical inputs. Published [aggregate tables](../docs/tables/full/) contain study estimates, not individual stock records or the original dataset.
