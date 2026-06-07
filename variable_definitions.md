# Variable Definitions

Exact formula, data source, and **timing** for every variable. The governing rule is the
**no-look-ahead** principle from the project standard: *anything used to predict the month
`t+1` return must be knowable by the close of month `t`.*

Timing legend: a variable tagged **[t]** is measured using information through the close of
month `t` (the formation month); **[t−1]** uses information through `t−1`; the prediction
target is the **[t+1]** return. The DS signal and all controls are dated `t`; they predict
the `t+1` return.

---

## 1. Returns and the prediction target

| Variable | Formula / definition | Source (Wind) | Timing | Notes |
|---|---|---|---|---|
| `ret_{i,t}` | Monthly **total** return (price change + reinvested cash dividends) | monthly return field (dividend-reinvested) | **[t]** | Use the dividend-reinvested series, not raw price return |
| `r_f,t` | Monthly risk-free rate | 1-year treasury yield (or deposit-rate proxy), converted to monthly | **[t]** | Small vs. equity moves; matters mainly for the DS denominator |
| `exret_{i,t}` | `ret_{i,t} − r_f,t` | derived | **[t]** | Excess return |
| `RET_{i,t}` | The **sorting/conditioning** one-month return = `ret_{i,t}` | derived | **[t]** | Same as `ret`; named separately because it is the "past return" being conditioned on |
| `fwd_{i,t+1}` | **Prediction target** = `ret_{i,t+1}` | derived (`ret` shifted −1 within stock) | **[t+1]** | The held return; never used in any signal |

> **Look-ahead trap:** `fwd` is the only `t+1` object in the panel. It must never enter a peer
> mean, a DS value, a sort key, or a regressor.

---

## 2. Deviation salience and peer returns

| Variable | Formula | Timing | Notes |
|---|---|---|---|
| `peer_ret_{i,t}` (industry, baseline) | Leave-one-out mean of month-`t` returns of same Shenwan-L1 peers: `(Σ_{j∈ind} ret_j − ret_i)/(N−1)` | **[t]** | Require ≥ 5 peers (`min_peers`), else NaN. VW peer mean = robustness |
| `peer_ret_{i,t}` (characteristic) | Mean of month-`t` returns of stocks in the same size×B/M×mom bucket, ex-self | **[t]** | He et al. (2023) style; buckets formed on **[t]**-known characteristics |
| `peer_ret_{i,t}` (analyst) | Shared-analyst-weighted mean: `(Σ_j n_{i,j} ret_j)/(Σ_j n_{i,j})` | **[t]** | `n_{i,j}` = analysts covering both `i` and `j` in trailing 12m **[t−12, t]** |
| `DS_{i,t}` | `|ret_{i,t} − peer_ret_{i,t}| / (|ret_{i,t} − r_f,t| + |peer_ret_{i,t} − r_f,t|)` | **[t]** | ∈ [0,1]; NaN if denominator 0; non-directional |

Peer returns use **contemporaneous** month-`t` returns of peers (the context the focal stock
is contrasted against *within* the same month), which is exactly how the paper defines it and is
not look-ahead: both `ret_i` and `ret_peer` are known at the close of `t`.

---

## 3. Control variables

All controls are dated **[t]** (known by formation) and predict the **[t+1]** return.

| Variable | Formula | Source (Wind) | Timing | Notes |
|---|---|---|---|---|
| `Size` | `log(market cap)` at end of `t` | month-end total mkt cap | **[t]** | Float-cap variant as robustness |
| `LogBM` | `log(book equity / market equity)` | book equity from latest **published** report; market equity at end of `t` | book **[t−1 or earlier, by pub date]**, price **[t]** | Align by **publication date** (annual ≤ Apr 30, interim ≤ Aug 31, Q1 ≤ Apr 30, Q3 ≤ Oct 31). Never use a report period that has not been published by the close of `t` |
| `Mom` | Cumulative return from `t−12` to `t−2` (skip `t−1`) | derived | **[t−12, t−2]** | Skips the most recent month to separate medium-term momentum from the short-term signal |
| `Illiq` | Amihud (2002): monthly average of `|daily ret| / daily turnover amount (CNY)` over `t` | daily return + daily amount | **[t]** | Exclude limit/suspension days from the average; scale consistently |
| `IVol` | Std. dev. of daily residuals from a CH-3 (or FF3) regression within `t` | daily returns + daily factors | **[t]** | Require enough valid trading days in `t` |
| `Turnover` | Monthly trading volume / shares outstanding | monthly volume + shares | **[t]** | Medhat–Schmeling conditioning variable; A-share turnover is high |
| `AnalystCov` | `log(1 + #analysts issuing FY1/FY2 in trailing 12m)` | analyst estimates | **[t−12, t]** | Sparse for small caps |
| `InstOwn` | `log(institutional holding share)` | quarterly institutional holdings | most recent quarter **published before** end of `t` | Quarterly; carry forward with pub-date care |
| `ST` | Indicator: stock is ST / \*ST in `t` | ST flag / name prefix | **[t]** | Excluded in baseline; interaction term in §6.2 |
| `Board` | {Main, ChiNext, STAR} | board tag | static/**[t]** | Drives the price-limit width |
| `SOE` | Indicator: central or local state-owned | ownership nature | **[t]** | Exploratory split (§6.6) |
| `Shortable` | Indicator: on the 融资融券 eligibility list in `t` | point-in-time list membership | **[t]** | Time-varying; for §6.4 |
| `ST_value` (optional) | Salience-theory value of Cosemans & Frehen (2021) | derived from daily returns | **[t]** | Distinct from DS; control to show DS is not ST in disguise |

---

## 4. Friction / extension measures (from daily data)

| Variable | Definition | Timing | Notes |
|---|---|---|---|
| `limit_up_day` / `limit_down_day` | Daily close at the applicable limit (±10/±20/±5% vs. prior close) | daily | Width depends on board and ST status |
| `n_limit_up_t`, `n_limit_down_t` | Count of limit-up / limit-down days in `t` | **[t]** | Intensity of limit pressure |
| `formation_limit_hit` | Last trading day of `t` closed at a limit | **[t]** | Tradability flag — cannot transact at that close |
| `abn_volume_t` | Month-`t` turnover (or volume) minus its trailing average, scaled | **[t]** | Retail-attention proxy; also the DS-mechanism check `corr(DS, abn_volume)` |
| `trading_days_t` | Count of actual trading days in `t` | **[t]** | Filter: require ≥ 10 |
| `listing_months_t` | Months since IPO at end of `t` | **[t]** | Filter: require ≥ 6 (robustness 12) |

---

## 5. Timing summary (one screen)

```
 month t-1        month t (FORMATION)                 month t+1 (HELD)
 ........  | ret_i,t, peer_ret_i,t, r_f,t  →  DS_i,t |  fwd_i,t+1 = ret_i,t+1
           | all controls measured here            |  (the prediction target)
           | filters applied at the close of t      |
                         |---- everything left of this bar is known ----|
```

If a quantity cannot be placed strictly to the **left** of the formation bar, it cannot be used
to predict `t+1`. This single check is the most important guard in the whole project.
