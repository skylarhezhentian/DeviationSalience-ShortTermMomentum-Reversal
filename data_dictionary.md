# Data Dictionary — Wind Pull List

What to pull from Wind, mapped to the variables in
[`variable_definitions.md`](variable_definitions.md). Wind field codes evolve and some have
multiple variants; **confirm each code in your Wind terminal** (right-click → "复制指标" or the
WindPy help) before a production pull. WindPy entry points referenced: `w.wsd` (one
security, time series), `w.wss` (cross-section snapshot), `w.wset` (sets/constituents),
`w.edb` (economic database, for the risk-free rate).

> Frequency strategy: pull a **daily** panel (for returns, Amihud, idio vol, limit flags,
> trading-day counts) and roll it up to **monthly**, rather than pulling monthly returns
> directly — it keeps total-return handling and limit detection consistent and auditable.

---

## 1. Identifiers and universe

| Variable | Suggested Wind source | Notes |
|---|---|---|
| Stock list (point-in-time) | `w.wset("sectorconstituent", "date=YYYY-MM-DD;sectorid=<all A-shares>")` | Pull membership each month to avoid survivorship bias |
| IPO date | `w.wss(code, "ipo_date")` | For the `listing_months` filter |
| Delist date | `w.wss(code, "delist_date")` | Keep delisted names in history (no survivorship) |
| Board | derive from code prefix (688→STAR, 300/301→ChiNext, 600/000/…→Main) or `w.wss(code,"mkt")` | Drives price-limit width |
| Shenwan industry | `w.wsd(code, "industry_sw", d, d, "industryType=1")` (L1) / `industryType=2` (L2) | **Peer grouping for baseline DS** |
| Ownership nature (SOE/private) | `w.wss(code, "nature_of_enterprise")` (a.k.a. enterprise-nature field) | Confirm exact field; values like 央企/地方国企/民营 |

## 2. Prices, returns, size, liquidity

| Variable | Suggested Wind field | Notes |
|---|---|---|
| Total return (div-reinvested) | daily `close` with `PriceAdj=F` (forward-adjusted) → compute returns | Forward-adjusted close embeds dividends/splits → total return |
| Raw close / prev close | `close`, `pre_close` | For limit detection vs. prior close |
| Daily % change | `pct_chg` | Cross-check returns |
| Total market cap | `mkt_cap_ard` | `Size = log(mkt_cap)` at month end |
| Float market cap | `mkt_cap_float` (free-float variant) | VW weighting / robustness |
| Trading amount (CNY) | `amt` | Amihud denominator; liquidity |
| Volume (shares) | `volume` | Turnover cross-check |
| Turnover rate | `turn` (daily, %) | Monthly `Turnover`; abnormal-volume proxy |
| Trading status | `trade_status` | Detect suspensions → `trading_days_t` |

## 3. Accounting (for book-to-market)

| Variable | Suggested Wind field | Timing care |
|---|---|---|
| Book equity | `tot_shrhldr_eqy_excl_min_int` (total equity excl. minority interest) | Use latest report **published** before close of `t` |
| Report publication date | `stm_issuingdate` (statement issuing date) | **Align on this**, not the period-end, to avoid look-ahead |
| Quick route: P/B | `pb_lf` (latest), then `BM ≈ 1/pb_lf` | Convenient but check how Wind times it; the explicit route above is cleaner |

## 4. Risk-free rate

| Variable | Suggested Wind source | Notes |
|---|---|---|
| 1-year treasury yield | `w.edb("<CN 1Y treasury yield code>", start, end)` | Convert annualized yield → monthly `r_f` |
| Deposit-rate proxy | benchmark 1-year deposit rate via EDB | Alternative; both are small vs. equity moves |

## 5. Friction / extension fields

| Variable | Suggested Wind source | Notes |
|---|---|---|
| Limit-up/down day | compute: `close == round(pre_close × (1 ± limit_pct), 2)` with board/ST-specific `limit_pct` | More robust than relying on a single flag; handle ±10/±20/±5 |
| ST / \*ST status | `riskwarning` field, or detect `ST`/`*ST` prefix in `sec_name` | Confirm field; name-prefix detection is a reliable fallback |
| Margin/short eligibility (融资融券标的) | `w.wset("sectorconstituent", "date=…;sectorid=<margin-target sector>")` per month | **Point-in-time** membership with effective dates |
| Abnormal volume / attention | derived from `turn` (month vs. trailing average) | Baseline retail-attention proxy |

## 6. Robustness-only data (heavier)

| Variable | Suggested Wind source | Difficulty |
|---|---|---|
| Analyst coverage count | `west_instnum` (number of forecasting institutions, trailing window) | Moderate — gives counts, not analyst-level links |
| Shared-analyst peer links | Wind analyst/research-report database (analyst ↔ firm ↔ date) | **Hard** — needed only for analyst-peer DS; sparse for small caps |
| Institutional ownership | institutional holding-ratio field (quarterly) | Moderate — quarterly, publication-date timing |
| Retail search attention | Baidu Index / East Money Guba (external to Wind) | Hard — scraping/licensing |
| Salience-theory value (ST_CF) | derive from daily returns per Cosemans & Frehen (2021) | Code, not a pull |
| China factor returns (CH-3/CH-4) | construct, or source Liu–Stambaugh–Yuan factors | For alphas in Table 2 |

---

## 7. Minimal pull for the baseline (do this first)

To run scripts `01`→`04` on real data, you only need:

1. **Daily** per stock: forward-adjusted `close`, `pre_close`, `amt`, `turn`, `trade_status`.
2. **Monthly/snapshot** per stock: `mkt_cap_ard`, Shenwan L1 industry, IPO date, board, ST flag.
3. **Book equity** (+ issuing date) for B/M.
4. **Risk-free**: 1-year treasury yield via EDB.

Everything in §5–§6 is for the extensions and robustness and can wait until the baseline
replicates cleanly.

---

## 8. Expected tidy schema after loading

The loader (`src/data_loading.py`) should emit a **monthly panel** with at least these columns
(one row per stock-month); this is the contract the rest of the pipeline relies on:

```
stock, month, ret, rf, mktcap, float_mktcap, industry, board,
book_equity, turnover, amihud, ivol, n_trading_days, listing_months,
is_st, is_soe, is_shortable, n_limit_up, n_limit_down, formation_limit_hit,
analyst_cov (opt), inst_own (opt), abn_volume (opt)
```

The synthetic generator (`scripts/00_simulate_data.py`) emits exactly this schema, so code
written against simulated data runs unchanged on real Wind data once the loader is pointed at
`data/raw/`.
