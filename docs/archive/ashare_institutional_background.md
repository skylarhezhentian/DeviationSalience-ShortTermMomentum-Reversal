> Early research proposal. Some proposed fields and tests were not implemented. See the [current project](../../README.md) and [evaluation protocol](../research_protocol.md).

# A-Share Institutional Background

Why the China A-share market is not a drop-in for the U.S. setting, and how each feature may
bear on the deviation-salience mechanism. Dates and numbers reflect the rules as understood at
the time of writing; **market rules change — verify current values against exchange notices /
Wind before finalizing a paper.**

---

## 1. Daily price limits

- **Main Board** (SSE/SZSE): ±10% from the previous close (reintroduced December 1996).
- **STAR Market (科创板)** and **ChiNext (创业板)**: ±20% (STAR from its 2019 launch; ChiNext
  from the August 2020 registration-system reform — previously ±10%).
- **ST / \*ST stocks**: ±5%.
- **New listings**: STAR and ChiNext IPOs have **no price limit for the first 5 trading days**,
  then the ±20% band applies. Main Board IPOs are subject to special first-day mechanisms
  (call-auction caps and intraday volatility halts). These windows produce extreme, non-
  representative returns — a reason to exclude newly listed stocks for several months.

**Why it matters for DS.** A limit caps how much of a salient shock enters the month-`t`
return. If overreaction is partly suppressed by a limit, the subsequent correction need not
complete in `t+1`; the high-DS reversal may be **smaller at one month but more persistent**,
unlike the transient one-month U.S. reversal. Limits also create **execution risk correlated
with the signal**: the extreme winners/losers the strategy targets are the ones most likely to
be locked at a limit and untradeable.

---

## 2. ST / \*ST treatment

Stocks with two consecutive years of losses or other distress are flagged **ST** ("special
treatment"); more severe cases become **\*ST** (delisting risk). Consequences: a tighter **±5%**
limit, a stigma/【attention】 effect, elevated delisting probability, and lottery-like demand
from retail traders betting on restructuring. **Baseline excludes ST/\*ST**; §6.2 studies them
separately. Note ST status is **endogenous to past performance**, so any ST analysis carries a
selection caveat.

---

## 3. T+1 settlement

A-share equities settle **T+1**: shares bought today cannot be sold until the next trading day.
This removes intraday round-tripping (one channel of high-frequency liquidity reversal) and
**lengthens the horizon** over which mispricing corrects — again pushing toward a slower,
smeared reversal relative to the U.S.

---

## 4. Short-sale and margin-trading constraints

- Margin trading (融资, leveraged buying) and short selling (融券, security borrowing) launched
  as a **pilot on 2010-03-31**. Before that, shorting was impossible for all names.
- Only securities on the official **eligibility list (融资融券标的)** can be margined/shorted.
  The list started small and was **expanded in discrete steps**; membership is time-varying and
  must be handled **point-in-time** (pull effective dates from Wind).
- Even for eligible names, **securities-lending (融券) supply is scarce, costly, and
  recallable**, so practical shorting is far harder than in the U.S.

**Why it matters.** This is the project's central tension. Limited shorting means overpricing of
salient winners cannot be arbitraged away (Miller 1977; limits to arbitrage), so the high-DS
reversal could be **statistically larger** among non-shortable names while being **economically
untradeable** there. The academic long–short therefore overstates investability — separating
the two is a core contribution.

---

## 5. Trading suspensions

A-share firms can suspend trading for extended periods (pending announcements, restructuring,
or — historically, e.g., mid-2015 — en masse during market stress). Suspended stocks have stale
returns and can strand capital for weeks or months. The pipeline requires a **minimum number of
actual trading days** in `t` and flags suspensions; suspension risk is also a tradability
limitation in §7.

---

## 6. Board structure

| Board | Codes | Daily limit | Notes |
|---|---|---|---|
| Main Board (SH) | 600/601/603/605 | ±10% | Largest, most mature |
| Main Board (SZ) | 000/001 (+ former SME 002) | ±10% | SME board merged into SZ Main in 2021 |
| ChiNext (创业板) | 300/301 | ±20% (since 2020-08) | Growth/tech; registration-based |
| STAR Market (科创板) | 688 | ±20% (since 2019-07) | Tech focus; investor access ≥ ¥500k + experience |
| Beijing (BSE) | 4xx/8xx | ±30% | Excluded from baseline (short history, thin) |

**Why it matters.** Wider ±20% bands let salient moves express more fully within a month (less
truncation), and STAR/ChiNext carry higher retail interest and turnover — so the salience effect
may be **stronger/faster** there (§6.3). But their short samples and different investor mix mean
the limit-width and attention channels are bundled, not cleanly separated.

---

## 7. Retail participation

Individual investors have historically supplied the majority of A-share trading volume. Because
deviation salience is fundamentally an **attention/overreaction** mechanism, heavy retail flow
is a reason to expect the effect to be **at least as strong as, and plausibly stronger than**,
in the U.S. Retail attention can be proxied by abnormal turnover/volume (in Wind) or, with extra
effort, Baidu search or East Money Guba post counts (external).

---

## 8. Transaction costs (for the tradability analysis)

- **Stamp duty**: levied on the **sell** side; **0.05%** since 2023-08-28 (previously 0.1%).
- **Commission**: market-set, broker-dependent — on the order of a few basis points per side,
  with a per-order minimum (commonly ¥5).
- **Market impact / slippage**: material for the small, illiquid names where equal-weighted
  effects concentrate, and worsened by monthly rebalancing of *extreme* deciles.

These feed Table 11 (friction-constrained net returns). The headline academic spread is gross
of all of this and of the shorting infeasibility in §4.

---

## 9. Implications checklist for the model

| Feature | Likely effect on the measured DS pattern | Where handled |
|---|---|---|
| Price limits | Reversal delayed/smeared; execution risk on extremes | §6.1, Table 4 |
| ST/\*ST | Distinct dynamics; selection | §6.2, Table 6 |
| T+1 | Slower correction | discussion / horizon tests |
| Short-sale limits | Larger but untradeable reversal among non-shortables | §6.4, §7, Tables 7 & 11 |
| Suspensions | Stale returns; capital stranding | filters, §7 |
| Boards (±20%) | Possibly stronger/faster effect on STAR/ChiNext | §6.3, Table 5 |
| Retail dominance | Amplified overreaction | §6.5, Table 8 |
| Transaction costs | Erodes net tradable returns | §7, Table 11 |

