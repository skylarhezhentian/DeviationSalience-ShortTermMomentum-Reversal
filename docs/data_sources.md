# Data sources, missing outcomes, and external checks

The baseline uses a private historical vendor extract. Raw vendor files, derived stock-level records, and local manifests are not public project assets. The code accepts local files so an authorized data holder can reproduce the work.

## Local inputs

| File | Required fields | Role |
|---|---|---|
| `close.parquet` | `TRADE_DT`, `S_INFO_WINDCODE`, `S_DQ_CLOSE`, `S_DQ_ADJFACTOR` | Dated closes and vendor adjustment factors |
| `value.parquet` | `TRADE_DT`, `S_INFO_WINDCODE`, `S_VAL_MV` | Formation-date market capitalization |
| `industry.parquet` | `date`, `wind_code`, `ind` | Dated industry grouping; index-backed join keys are supported |

Observed prices cover January 4, 2021 through November 28, 2025. The audit independently recomputes the global final observed date in each month and checks every adjusted monthly return against its close and adjustment-factor components. This verifies arithmetic consistency within the extract, not the vendor's treatment of corporate actions or historical information availability.

Listing `1222实习数据/data.rar` found only the same three Parquet filenames, with matching uncompressed byte sizes. There were no additional rate, volume, status, delisting-payment, or explanatory files. The archive was not extracted; matching sizes alone do not establish identical content.

## Missing holding outcomes

All **178** unavailable baseline holding returns correspond to a stock code that has no later daily observation in the supplied extract. **176** have some daily observations during the holding month but none at its common month-end endpoint; two have no holding-month observation. No same-code later resumption was found. `outputs/data_quality/missing_holdings.csv` records every case, dates, portfolio bin, and formation weight.

This classification describes disappearance from the extract. It does not establish that every company delisted, that every shareholder lost their investment, or that an absent return is zero. Successor securities, cash elections, and delisting payouts are missing.

A specific corporate-action example is **600068.SH in September 2021**. The Shanghai Stock Exchange confirmed a share-exchange merger and termination of listing effective September 13. The event cause is verified; the successor investment return is not reconstructed. This case remains an unavailable baseline holding outcome. [SSE notice, September 10, 2021](https://www.sse.com.cn/disclosure/announcement/general/c/c_20210910_5587127.shtml)

Complete-cell means can consequently be selected by missing corporate-action outcomes. Observed-only, zero-return, and total-loss scenarios are sensitivity assumptions, not estimates of the true missing returns.

## Extreme returns and execution

The audit flags all full-panel stock-months with adjusted return at least +100% or at most −50%. There are **734** such observations; **106** include a change in the vendor adjustment factor. These are inspection thresholds only: no observation is removed or winsorized. Every monthly return agrees with

`(current_close / previous_close) × (current_factor / previous_factor) − 1`.

The broad panel includes observations that are ineligible for baseline portfolio formation. Its largest values should not be confused with the largest return actually assigned to a holding. `monthly_extremes_decomposed.csv` separates close changes from adjustment changes; `top20_extreme_daily_paths.csv` records local paths for the largest full-panel cases.

**688585.SH, July 2025.** The issuer's August 5 announcement reports a 1,083.42% price rise over July 9–30 and a July 31 suspension. The local monthly price movement agrees with the announcement, with unchanged adjustment factor. The vendor still supplies a July 31 close of 92.07: a price recorded during suspension is not evidence that the month-end sale was executable. The baseline remains a statistical price-return experiment. [Issuer announcement 2025-063, published in Shanghai Securities News](https://paper.cnstock.com/html/2025-08/05/content_2101561.htm)

**688068.SH, April 2021.** The indexed text of the exchange's April statistical bulletin lists closing price 225.50 and monthly gain 425.64%, consistent with the local value. The official PDF could not be retrieved for visual verification during this audit, so this corroboration is limited to its indexed table text. [SSE April 2021 statistical bulletin, printed page 64](https://english.sse.com.cn/news/publications/monthly/c/10114327/files/6bedb1c35f7c4617a27661b38b5953f1.pdf)

These checks do not validate every tail event. Adjustment factors may reflect dividends, share changes, or other corporate actions; their individual legal/economic treatment remains unverified.

Historical rows can carry current `920...BJ` identifiers before the later code transition. Dated broker implementation notices describe the 2025 switch and historical-code lookup behavior. This is a warning against treating present-day ticker strings as point-in-time listings or inferring company identity solely from matching suffixes. Pre-BSE/NEEQ history, exchange membership, and identifier mappings require separate reference data. The reported analysis therefore includes a Shanghai/Shenzhen-only universe sensitivity. [Broker implementation notice, September 29, 2025](https://cms.crsec.com.cn/content/details1525922027043213313_1972588693799161858.html)

## External rate proxy

A single public FRED download adds OECD series **IR3TTS01CNM156N**, labeled China three-month/90-day Treasury rates, monthly, percent, not seasonally adjusted. The local snapshot contains **36 observations, December 2020–November 2023**. It does not cover the full equity sample. [FRED series definition and source notes](https://fred.stlouisfed.org/series/IR3TTS01CNM156N)

The adapter produces `outputs/data_quality/rf_proxy_monthly.csv`:

| Column | Definition |
|---|---|
| `month` | Source observation month, `YYYY-MM` |
| `annual_yield_percent` | Quoted source percentage |
| `rf_monthly_proxy` | `annual_yield_percent / 100 / 12` |
| `source_series` | `IR3TTS01CNM156N` |
| `source_url` | FRED definition/source-notes page |

This conversion is approximate monthly simple carry. It is **not** a realized one-month Treasury investment return, a security-level total-return series, or a historically available vintage. Observation month is not a verified publication date. Missing months remain absent. The research compares RF-adjusted and zero-RF signals on a matched historical window and restores raw stock holding returns; the original baseline stays unchanged.

The source is publicly downloadable without an API key, but FRED marks it copyrighted and requires attribution. OECD's source citation is *Main Economic Indicators — complete database*, [DOI: 10.1787/data-00052-en](https://doi.org/10.1787/data-00052-en), accessed October 4, 2026. The fetched snapshot stays local; public availability is not an assertion of unrestricted redistribution. `rf_source.json` records source links, hashes, coverage, and limitations.

## Reproduce the local audit

The normal command is offline and consumes any already-downloaded rate snapshot:

```sh
python scripts/audit_data_quality.py --data-dir /path/to/private/QuantProject
python -m unittest discover -s tests -p test_data_quality.py -v
```

To acquire the one external series explicitly:

```sh
python scripts/audit_data_quality.py --data-dir /path/to/private/QuantProject --fetch-rf
```

`--fetch-rf` makes one request to the fixed FRED CSV endpoint. It requires no paid subscription or credentials. A locally saved FRED file can instead be passed with `--rf-csv /path/to/snapshot.csv`. Demo and CI runs remain offline.

The audit verifies original hashes before and after its work and does not alter baseline numeric outputs. Seven focused tests cover missing-observation classifications, calendar gaps, split/factor decomposition, rate units, missing months, and invalid inputs. These checks establish consistency and explicit limitations, not investment performance or complete scientific validity.
