# Deviation Salience, Short-Term Momentum, and Reversal in China's A-Share Market

A replication-and-extension project that adapts the **deviation salience (DS)** model of
Chen, Wang & Yu (2024), *"Salience and Short-term Momentum and Reversals,"* from the U.S.
market to **China A-shares**, where price limits, ST/\*ST rules, T+1 settlement,
short-sale constraints, and high retail participation may reshape the original behavioral
mechanism.

> **Status:** research design + runnable analysis skeleton. The pipeline runs end-to-end
> on **simulated data** so the plumbing can be verified before any real Wind data is loaded.
> No empirical claim about A-shares has been tested yet. See *Claims discipline* below.

---

## Central research question

> Does deviation salience explain the coexistence of short-term momentum and reversal in
> China's A-share market, and do China-specific frictions — price limits and short-sale
> constraints in particular — change that relationship relative to the U.S. evidence?

## What the original paper establishes (U.S.) vs. what this project tests (A-shares)

The distinction matters and is kept throughout the repo.

| | Original paper (Chen, Wang & Yu 2024) | This project |
|---|---|---|
| Market | U.S. (NYSE/NASDAQ/AMEX), 1983–2021 | China A-shares, 2010–2024 (baseline) |
| Status of finding | **Documented result** | **Hypothesis under test** |
| Baseline peer | Shared-analyst-coverage peers | **Industry (Shenwan L1) peers** |
| Headline U.S. result | High-DS → reversal (−1.30%/mo); Low-DS → momentum (+1.41%/mo) | We test whether a similar two-regime pattern appears, and how frictions distort it |

We do **not** assume the effect exists in A-shares. The language in the code, docs, and any
generated tables is deliberately of the form *"we test whether…"*, *"the hypothesis is…"*,
*"the evidence would support…"* — not *"this factor works."*

## The DS measure

At the end of each month *t*, for stock *i* with peer set *p*:

```
            | r_{i,t} − r^p_{i,t} |
DS_{i,t} = --------------------------------------
           | r_{i,t} − r_f,t | + | r^p_{i,t} − r_f,t |
```

where `r_{i,t}` is the stock's monthly return, `r^p_{i,t}` the (peer-weighted) average peer
return, and `r_f,t` the monthly risk-free rate. DS ∈ [0, 1], is non-directional (sign of the
return does not matter), and rises when a stock's move diverges from its peers'. DS is
measured at *t* and used to predict *t+1* returns — nothing in its construction may use
information after the close of *t* (see [`docs/variable_definitions.md`](docs/variable_definitions.md)).

## Repository layout

```
salience-ds-ashares/
├── README.md                  ← you are here
├── config/config.yaml         ← every result-affecting knob (period, filters, sorts, NW lags)
├── docs/
│   ├── research_design.md      ← the full 9-part design (read this first)
│   ├── variable_definitions.md ← exact formulas, timing (t−1/t/t+1), Wind fields, look-ahead notes
│   ├── ashare_institutional_background.md ← price limits, ST/*ST, T+1, short-sale, boards
│   └── data_dictionary.md      ← Wind field → variable mapping and pull list
├── src/                        ← importable library (no side effects on import)
│   ├── utils.py                ← winsorize, Newey-West, weighted means, quantile bucketing
│   ├── data_loading.py         ← load Wind exports → tidy monthly panel (+ synthetic fallback)
│   ├── filters.py              ← ST/*ST, financials, IPO age, trading days, microcaps, limit hits
│   ├── peers.py                ← industry / characteristic / analyst peer returns
│   ├── deviation_salience.py   ← the DS formula (3 peer variants)
│   ├── controls.py             ← size, B/M, momentum, Amihud illiq, idio vol, turnover, coverage
│   ├── portfolios.py           ← 5×10 double sort, winner−loser, EW & VW
│   ├── regressions.py          ← Fama-MacBeth with Newey-West t-stats
│   └── extensions.py           ← A-share interaction tests (limits, board, ST, shortable, retail, SOE)
├── scripts/                    ← thin orchestration; run in order
│   ├── 00_simulate_data.py     ← write a fake Wind-like panel so the pipeline runs
│   ├── 01_build_panel.py       ← load + filter + build controls → processed panel
│   ├── 02_construct_ds.py      ← peer returns + DS
│   ├── 03_double_sorts.py      ← Table 2-style double-sort results
│   ├── 04_fama_macbeth.py      ← Table 3-style Fama-MacBeth regressions
│   └── 05_extensions.py        ← Tables 4+ A-share-specific tests
├── tests/                      ← pytest unit tests (DS formula, sort logic)
├── data/{raw,interim,processed}  ← gitignored; your Wind pulls live in raw/
└── output/{tables,figures}     ← gitignored; generated results
```

## Quickstart (runs on simulated data — no Wind needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Generate a synthetic Wind-like panel, then run the whole pipeline on it.
python scripts/00_simulate_data.py
python scripts/01_build_panel.py
python scripts/02_construct_ds.py
python scripts/03_double_sorts.py
python scripts/04_fama_macbeth.py
python scripts/05_extensions.py

pytest -q          # unit tests for the DS formula and sort logic
```

> **The simulated run is a smoke test, not a finding.** The synthetic data contain no
> behavioral mechanism, so the double-sort and regression numbers it prints are
> economically meaningless. Their only job is to prove the code runs end-to-end and the
> shapes line up. Real conclusions require real Wind data.

## Using real Wind data

1. Pull the fields listed in [`docs/data_dictionary.md`](docs/data_dictionary.md) (monthly returns,
   Shenwan industry, market cap, B/M inputs, turnover, daily returns/volume for Amihud & idio
   vol, ST flags, board, margin/short-eligibility list, ownership nature; analyst coverage and
   institutional holdings for robustness).
2. Drop the exports into `data/raw/` and set `data_loading.SOURCE = "wind"` (or pass `--source wind`).
3. Re-run scripts `01`→`05`. Edit `config/config.yaml`, never the modules, to change the sample,
   filters, or sort parameters.

## Claims discipline (project ground rules)

This repo follows a strict standard, baked into how results are reported:

- **Statistical predictability ≠ economic significance ≠ real-world tradability.** Each is
  reported separately. A long–short DS spread that is statistically significant on paper is
  *not* called tradable until short-sale eligibility, T+1, price-limit execution risk,
  suspensions, turnover, and transaction costs are accounted for.
- **Pre-registration of the main hypothesis.** Pre-planned tests, robustness checks, and
  exploratory tests are labeled as such (see `docs/research_design.md` §7). Filters are not
  to be added until a result "looks good."
- **Look-ahead bias** is treated as the cardinal sin: anything used to predict *t+1* must be
  known by the close of *t*.

## Source

Chen, Yili; Wang, Huaixin; Yu, Jianfeng. *"Salience and Short-term Momentum and Reversals."*
Working paper, December 2024. The PDF is **not** redistributed in this repo.
