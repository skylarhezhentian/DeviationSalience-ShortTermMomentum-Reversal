> Early research proposal. Some proposed fields and tests were not implemented. See the [current project](../../README.md) and [evaluation protocol](../research_protocol.md).

# Research Design — Deviation Salience in China A-Shares

*A replication and friction-aware extension of Chen, Wang & Yu (2024), "Salience and
Short-term Momentum and Reversals," adapted to the China A-share market.*

**Reading note on claims.** This document separates three things at every step: what the
original paper *documents* (U.S. evidence), what this project *hypothesizes*, and what it
*tests*. The verbs are chosen deliberately — "the paper finds," versus "we test whether,"
"the hypothesis is," "the evidence would support." Nothing here should be read as a claim
that deviation salience "works" in A-shares; that is the open question.

---

## 1. Research question and contribution

### 1.1 Refined research question

The umbrella question is:

> **Does deviation salience explain the coexistence of short-term momentum and reversal in
> China's A-share market, and do China-specific frictions — price limits and short-sale
> constraints in particular — change that relationship relative to the U.S. evidence?**

It decomposes into four testable sub-questions.

1. **Baseline (out-of-sample replication).** Conditioning on month-*t* deviation salience,
   does the sign of one-month return predictability flip — reversal among high-DS stocks,
   continuation among low-DS stocks — as documented in the U.S.? *We test whether* the
   two-regime pattern appears in A-shares using industry-peer DS.
2. **Price limits.** Do daily price limits truncate within-month price adjustment so that
   the high-DS reversal is *delayed or smeared* across several months rather than completing
   in *t+1*, and do formation-day limit hits make the headline spread partly non-transactable?
3. **Short-sale constraints / limits to arbitrage.** Because the high-DS leg is "short the
   overpriced salient winners," and most A-shares cannot be shorted, is the *statistical*
   reversal possibly *larger* among non-shortable names (mispricing persists) while being
   *non-tradable* there — i.e., a wedge between predictability and tradability?
4. **Attention and market design.** Is the effect stronger where retail attention is higher,
   and does it differ across boards (Main Board ±10% vs. STAR/ChiNext ±20%)?

### 1.2 Why A-shares are an interesting setting

Three reasons, each of which also shapes a prior.

*A retail-dominated market.* Individual investors have historically accounted for the large
majority of A-share trading volume. Deviation salience is, mechanically, an *attention*
story: investors overweight stocks whose recent return stands out against peers and overreact;
they overlook stocks that blend in and underreact. A market where attention-driven retail
flow dominates price formation is, a priori, a setting where this mechanism should be *more*
visible than in the institutionally intermediated U.S. market. That makes A-shares a
high-powered out-of-sample test rather than a mere geographic repeat.

*A natural laboratory of frictions.* A-shares impose daily price limits, T+1 settlement, a
restrictive and time-varying short-sale regime, trading suspensions, and an ST/\*ST distress
label — each of which can be turned on or off in the cross-section or time series. This lets
us ask not just "is the anomaly here?" but "does market design change a behavioral anomaly?"
— a question the U.S. data cannot answer.

*Novelty.* The original paper includes an international panel that shows the pattern is broad,
but a dedicated A-share study that (i) takes the frictions seriously rather than filtering
them away, (ii) separates statistical predictability from tradability under those frictions,
and (iii) uses the regime variation (board reforms, the expanding short-eligibility list) as
identification, is not, to our knowledge, in the literature.

### 1.3 How regulation may change the salience mechanism

This is the conceptual heart of the project. The behavioral primitive (salient moves →
overreaction → reversal; non-salient moves → underreaction → continuation) is held fixed;
the frictions act on how and whether that primitive shows up in measured returns.

- **Daily price limits (±10% Main Board, ±20% STAR/ChiNext, ±5% ST).** Limits cap how much of
  a salient shock can be incorporated into the month-*t* return. If a high-DS overreaction is
  partly suppressed by a limit, the subsequent correction need not concentrate in *t+1*; the
  reversal may be *weaker at one month but more persistent*, the opposite of the transient
  one-month U.S. reversal. *We test this,* not assume it.
- **T+1 settlement.** No same-day round trips. This removes one channel of intraday liquidity
  reversal and lengthens the horizon over which corrections play out, again pushing toward a
  slower, smeared reversal.
- **Short-sale constraints.** With limited shorting, overpricing among salient winners cannot
  be arbitraged away. The textbook prediction (Miller 1977; limits to arbitrage) is that
  *mispricing persists longer where shorting is harder*. So the high-DS reversal could be
  **larger** in the data precisely where it is **least tradable**. This is the central tension
  the project is built to expose.
- **Retail dominance.** More attention-driven marginal traders should *amplify* overreaction
  to salient moves, predicting a possibly *stronger* high-DS reversal than in the U.S.
- **ST/\*ST regime.** Distress label + ±5% limit + delisting risk + lottery-type demand create
  idiosyncratic dynamics; these names are excluded from the baseline and studied separately.

The net empirical prediction is therefore *ambiguous by design*: behavioral forces push the
A-share effect to be larger; microstructure truncation pushes the one-month reversal to be
smaller-but-slower; arbitrage limits push it to be larger-but-untradable. Disentangling these
is the contribution — *if* the evidence supports the decomposition.

### 1.4 Potential contribution (conditional)

Stated conditionally, because none of it is established yet. If the evidence supports the
hypotheses, the contributions would be: (1) an out-of-sample validation of the deviation-
salience mechanism in a retail-dominated market, strengthening or qualifying the behavioral
interpretation; (2) evidence on how specific, datable regulations (price limits, the expanding
short-eligibility list, the ±20% board reform) reshape a behavioral anomaly, using the
regulation changes as identification; and (3) a disciplined separation of *statistical
predictability* from *economic significance* from *real-world tradability* under genuine
A-share frictions — i.e., showing what part of a "factor" is real signal versus what part is
an artifact of assuming costless shorting and limit-free execution.

---

## 2. Replication design

### 2.1 Stock universe

All A-share **common stocks** listed on the Shanghai (SSE) and Shenzhen (SZSE) exchanges:
Main Board (SH 600/601/603/605; SZ 000/001 and the former SME board 002, merged into the SZ
Main Board in 2021), **ChiNext** (300/301), and the **STAR Market** (688). The baseline
**excludes**:

- **B-shares** (foreign-currency 200/900 lines) — different investor base and currency.
- **Beijing Stock Exchange** (BSE, 8xx/4xx) — short history and thin liquidity; can be added
  later as an extension.
- **Financial firms** (Shenwan "银行" banks and "非银金融" non-bank financials) — book-to-market,
  leverage, and accounting are not comparable to non-financials; this matches standard
  practice and the original paper's robustness of excluding financials.

### 2.2 Sample period

**Baseline: January 2010 – December 2024** (monthly). Rationale: margin trading and short
selling were introduced as a pilot on **2010-03-31**; before that, shorting was impossible for
*all* names, so the short-eligibility extension only has cross-sectional variation from 2010
onward. Data quality is also solid from the late 2000s.

Pre-planned **subsamples** for the time-series robustness section:

- **Pre-2010** (no short selling at all) vs. post-2010 — does the introduction of shorting
  change the high-DS reversal?
- **Around the board reforms**: STAR launch (2019-07) and ChiNext registration system + ±20%
  limits (2020-08) — pre/post comparison for the affected boards.
- **2015 boom-bust** flagged as a structural-break check (extreme retail churn, mass
  suspensions); report with and without 2015-H2.

> **Look-back requirement.** Constructing `Mom` (cumulative return *t−12* to *t−2*) and the
> 12-month analyst window needs data starting ~12 months before the sample. Pull raw data from
> **2008** so that January 2010 is the first *formation* month with complete inputs.

### 2.3 Exclusions and filters (applied at the close of each formation month *t*)

Every filter below uses only information known by the end of *t* (no look-ahead).

| Filter | Rule | Why (A-share specific) |
|---|---|---|
| ST / \*ST | Exclude in baseline | ±5% limit, distress/delisting risk, lottery demand; studied separately in §6 |
| Newly listed | Require ≥ 6 months since IPO (robustness: 12) | IPO no-limit pops / capped first-day rules distort returns; peer links unstable |
| Suspension / illiquidity | Require ≥ 10 actual trading days in *t* | Long suspensions make the month-*t* return stale and DS unreliable |
| Financials | Exclude | Non-comparable accounting/leverage |
| Microcaps | Baseline keeps all; robustness drops bottom 30% by month-end size and/or applies a price floor | A-share "shell value" inflates microcap reversal; CH-3 factor model itself drops the smallest 30% |
| Price-limit hits | Academic baseline keeps but **flags**; tradability variant drops formation-day limit closers | A limit-up winner cannot be bought at the close price (see §6, §7) |

### 2.4 Data required from Wind

You have Wind, so the plan is written against Wind fields; the exact field codes are in
[`data_dictionary.md`](data_dictionary.md). Grouped by use:

- **Monthly panel (core).** Monthly *total* return (dividend-reinclusive), month-end total and
  float market cap, Shenwan industry (L1 and L2), trading status, ST flag, board tag,
  ownership nature (central SOE / local SOE / private / foreign), and point-in-time membership
  of the margin/short-eligibility list (融资融券标的) with effective dates.
- **Daily panel (for derived controls and friction flags).** Daily return, close, traded
  amount (CNY) and turnover — needed for Amihud illiquidity, idiosyncratic volatility,
  abnormal volume/attention, trading-day counts, and limit-up/limit-down detection.
- **Accounting (for B/M).** Book equity from the most recent annual or interim report **whose
  publication date precedes the close of *t*** (A-share annuals are due by Apr 30, interims by
  Aug 31, Q1 by Apr 30, Q3 by Oct 31 — respect the *publication* date, not the period-end, to
  avoid look-ahead).
- **Risk-free rate (monthly).** 1-year treasury yield (or a deposit-rate proxy); used in the DS
  denominator. Note that in A-shares the monthly risk-free is small relative to equity moves,
  so DS is numerically dominated by the peer-divergence numerator.
- **Robustness data.** Analyst FY1/FY2 estimates (analyst↔firm↔date) to build coverage counts
  and shared-coverage peer links; quarterly institutional holdings; and, optionally, a retail-
  attention series (Baidu search index or East Money Guba post counts — external to Wind).

CSMAR/RESSET can substitute for any of the above and are noted as alternatives in the data
dictionary, but the baseline assumes Wind.

---

## 3. Deviation salience construction

### 3.1 The measure (unchanged from the paper)

At the end of month *t*, for stock *i* with peer set *p*:

```
              | r_{i,t} − r^p_{i,t} |
DS_{i,t} = ----------------------------------------------
           | r_{i,t} − r_{f,t} | + | r^p_{i,t} − r_{f,t} |
```

- `r_{i,t}` — stock *i*'s month-*t* total return.
- `r^p_{i,t}` — the (peer-weighted) average month-*t* return of *i*'s peers, the *context*.
- `r_{f,t}` — month-*t* risk-free rate.
- Properties (from Bordalo et al. 2012/2013): **ordering** (salience rises with divergence
  from peers — the numerator), **diminishing sensitivity** (normalization shrinks DS at large
  return magnitudes — the denominator), and **reflection** (DS depends only on magnitudes, not
  signs). DS ∈ [0, 1].
- **Edge case:** if `r_{i,t} = r^p_{i,t} = r_{f,t}` the denominator is 0 → set `DS = NaN`
  (rare). DS is already bounded, so no winsorization of DS itself.

**Timing.** All inputs are month-*t* quantities, so `DS_{i,t}` is known at the close of *t* and
is used to predict the *t+1* return. This is the only timing convention that avoids look-ahead.

### 3.2 Baseline peer definition — industry peers

The baseline uses **Shenwan level-1 industry** peers (the paper's own first robustness
alternative, and the cleanest, best-populated choice in A-shares):

- Peer set of *i* in month *t* = all other non-excluded A-shares in *i*'s Shenwan L1 industry.
- Peer return = **equal-weighted** mean of peer returns, *excluding the focal stock*
  (value-weighted peer mean is a robustness variant).
- Require **≥ 5 peers**, else `DS = NaN` that month.

Why industry is the right A-share baseline: analyst coverage in China is sparse and skewed to
large caps, so analyst-linkage peers (the paper's main measure) drop most small caps and induce
selection. Industry membership is universal, point-in-time stable, and available directly in
Wind. The user-specified plan also designates industry-peer DS as the baseline.

### 3.3 Robustness peer definitions

**Characteristic peers** (after He et al. 2023). Peers = stocks in the same size × B/M ×
momentum bucket (e.g., 5×5×5 independent sorts) in month *t*; peer return is the bucket mean
excluding self. This strips out industry composition as a confound and tests whether DS is
about *peer divergence* generally, not industry comovement.

**Analyst-linkage peers** (closest to the original). Two firms are peers in month *t* if at
least one analyst issued an FY1 or FY2 forecast for *both* within the trailing 12 months. The
peer return is weighted by the number of shared analysts:

```
r^p_{i,t} = ( Σ_j  n_{i,j} · r_{j,t} ) / ( Σ_j  n_{i,j} )
```

where `n_{i,j}` is the count of analysts covering both *i* and *j*. This is the heaviest to
build and the most selection-prone in A-shares (no coverage → no peers → dropped); it is a
robustness check, not the baseline.

### 3.4 Placebo / falsification constructions (pre-planned)

To show that it is the *salience contrast* doing the work and not a mechanical artifact, we
replicate the paper's placebos: (1) replace the salience-normalized measure with the **raw
absolute return difference** `|r_i − r^p|`; and (2) compute "DS" against the **market return**
or against **randomly matched peers** instead of true peers. The hypothesis is that these
should *fail* to produce the two-regime pattern. A placebo that "works" would be a red flag
that the result is mechanical.

---

## 4. Portfolio test

### 4.1 Double sort

Each month *t*:

1. Sort eligible stocks into **5 DS groups** (quintiles) on `DS_{i,t}`.
2. *Within each DS group*, sort into **10 deciles** on the month-*t* return `RET_{i,t}`
   (a dependent sort, DS first — matching the paper).
3. Hold each of the 5×10 = 50 portfolios for **one month** (*t+1*); compute both
   **equal-weighted** and **value-weighted** average returns.

### 4.2 Winner-minus-loser (WML) construction

Within each DS group, `WML = (decile-10 winners) − (decile-1 losers)`, formed on month-*t*
return and held in *t+1*. The three objects of interest:

- `WML_high-DS` — expected **negative** (reversal) under the hypothesis.
- `WML_low-DS` — expected **positive** (continuation).
- `WML_high − WML_low` — the difference-in-differences, expected **strongly negative**; this is
  the single number that most directly mirrors the paper's headline (U.S.: −2.71%/month).

t-statistics on each monthly spread series use **Newey-West** standard errors (lag ≈ 6).

### 4.3 Risk adjustment

Report raw spreads and alphas against China-appropriate factor models, **not** the U.S. model:

- CAPM and a China **FF3**, and especially the **Liu, Stambaugh & Yuan (2019) CH-3** (market,
  size, value-by-EP) and **CH-4** (adding a turnover/sentiment factor). CH-3 deliberately
  **drops the smallest 30%** of stocks when forming breakpoints to purge the shell-value
  effect that contaminates A-share size and reversal sorts — a detail that matters here.

### 4.4 What result would support the original finding, and how to read EW vs. VW

A supportive result is: `WML_high-DS` significantly **negative**, `WML_low-DS`
**positive** (or at least significantly *less negative*), a roughly monotone gradient across
the DS quintiles, and a significant `high − low` difference that survives CH-3/CH-4 alphas.

**Equal- vs. value-weighting carries real interpretive weight in A-shares:**

- **Equal-weighted** gives small caps full influence. Behavioral mispricing and retail
  attention effects are typically strongest there, so EW is likely the *high-powered* test and
  may be the headline. **But** EW results can be driven by tiny, illiquid, near-untradable
  names — so a significant EW spread is evidence of *predictability*, not of *tradability*.
- **Value-weighted** down-weights small caps and asks whether the effect survives among
  economically meaningful positions. A VW spread is a tougher, more tradable-relevant test.
- **Strong-form test:** restrict to large, liquid names (e.g., **CSI 300** constituents) — the
  A-share analogue of the paper's "largest 500 stocks" check, where the *unconditional*
  reversal vanishes but the *DS-conditioned* effect survived in the U.S. If the DS pattern
  holds among CSI 300 names, that is the cleanest evidence it is not a microcap/liquidity
  artifact.

The discipline: an EW-only result is reported as statistical predictability; an economic-
significance claim requires the VW and liquid-universe versions to hold too.

---

## 5. Regression test (Fama-MacBeth)

### 5.1 Specification

For each month *t*, estimate the cross-sectional regression predicting the *t+1* return:

```
r_{i,t+1} = a_t
          + b1 · DS_{i,t}
          + b2 · RET_{i,t}
          + b3 · ( DS_{i,t} × RET_{i,t} )            ← coefficient of interest
          + Σ_k γ_k · X_{k,i,t}
          + Σ_k δ_k · ( X_{k,i,t} × RET_{i,t} )       ← control interactions
          + ε_{i,t+1}
```

Then average the monthly coefficients over time and compute **Newey-West** t-statistics
(lag ≈ 6). Regressors are **winsorized monthly at 1%/99%**; optionally standardized for
comparability of magnitudes.

### 5.2 The key coefficient and its expected sign

`b3` on **DS × RET** is the A-share analogue of the paper's central result. The hypothesis
predicts **b3 < 0** and significant: a high-DS stock's recent return *reverses* (negative
contribution), while a low-DS stock's recent return *continues* (the interaction shrinks the
reversal toward continuation). In the U.S., `DS × RET` is negative and its predictive power is
comparable to, or stronger than, `RET` itself — that is the benchmark to compare against.

`b2` on `RET` alone is the predictability at the low-DS end and has an ambiguous sign net of
the interaction.

### 5.3 Controls (levels, plus the interactions with RET that matter)

Including **interactions** of the controls with `RET` is essential — it is how we show that
`DS × RET` is not just proxying some other conditioning variable:

| Control `X` | Definition | Why included / which interaction matters |
|---|---|---|
| Size | log market cap, end of *t* | Microcap reversal; `Size × RET` |
| LogBM | log book-to-market (lagged, publication-aligned) | Value |
| Mom | cumulative return *t−12* to *t−2* | Medium-term momentum |
| Illiq | Amihud (2002), daily-averaged over *t* | Liquidity-provision reversal; `Illiq × RET` |
| IVol | idio vol from daily CH-3/FF3 residuals in *t* | Volatility reversal (Dai et al. 2024); `IVol × RET` |
| Turnover | monthly volume / shares | Medhat–Schmeling: `Turnover × RET` expected **positive** — must be in the model so DS×RET isn't capturing it |
| Analyst coverage | log(1 + #analysts, trailing 12m) | Attention proxy |
| Inst ownership | log institutional holding share (quarterly) | Attention/sophistication |
| SOE, Board | dummies | A-share structure controls |

The paper specifically shows DS×RET survives controlling for the size, illiquidity, volatility,
and turnover *interactions*; reproducing that in A-shares is the robustness bar.

---

## 6. A-share-specific extensions

Each extension states a **hypothesis** (conditional), a **test**, an **expected sign**, and a
**caveat**. These are where the project earns its novelty.

### 6.1 Price-limit hits

*Measures.* From daily data, for month *t*: count of limit-up and limit-down days; an
indicator that the **formation day** (last trading day of *t*) closed at a limit; and the
fraction of the month's |return| realized on limit days.

*Hypothesis 1 (incomplete adjustment).* When a salient move repeatedly hits the limit, the
month-*t* return *understates* the shock and the correction cannot complete in *t+1* → the
high-DS reversal is **delayed/smeared** across *t+1…t+k* rather than concentrated at one month.
*Test:* the triple interaction `DS × RET × LimitHit`, and multi-horizon WML (1–6 months) for
limit-hit vs. non-limit subsamples.

*Hypothesis 2 (tradability).* A winner that closes limit-up at formation cannot be bought at
that close; the reported WML overstates achievable returns. *Test:* re-form the portfolios
(a) excluding formation-day limit closers and (b) executing at the next day's open/VWAP;
compare to the close-price WML.

*Caveat.* Limit hits correlate with extreme `RET` and small size — control for the RET decile
and size; the effect must survive within-decile.

### 6.2 ST / \*ST stocks

*Hypothesis.* ST names (±5% limit, distress, delisting risk, lottery-like retail demand) have
distinct salience dynamics; including them may inflate or distort the high-DS reversal. *Test:*
baseline excludes ST; the extension adds an ST indicator and `ST × DS × RET`, reporting results
with and without ST. *Caveat:* ST status is endogenous to past performance (poor performers get
labeled), so this is partly a selection test.

### 6.3 Main Board vs. STAR / ChiNext

*Background.* STAR (688) and ChiNext (300/301) carry **±20%** daily limits (since 2019/2020),
registration-based listing, higher turnover and retail interest, and no-limit windows for new
listings; STAR additionally restricts direct access to investors with ≥ ¥500k assets.

*Hypothesis.* Wider bands let salient moves express more fully within the month (less
truncation) and higher attention amplifies overreaction → the high-DS reversal may be
**stronger and/or faster** on STAR/ChiNext than on the Main Board. *Test:* estimate `DS × RET`
separately by board and via `Board × DS × RET`. *Caveat:* short STAR/ChiNext samples and a
different investor mix mean this is *not* a clean ceteris-paribus comparison; treat the
limit-width channel and the attention channel as bundled.

### 6.4 Short-sale / margin eligibility

*Background.* Only stocks on the **融资融券标的** list can be shorted (融券) or margined (融资).
The list started small in 2010 and was expanded in discrete steps; pull the **point-in-time**
membership with effective dates from Wind.

*Hypothesis (limits to arbitrage).* Among **non-shortable** names, overpricing of salient
winners cannot be corrected → the high-DS reversal may be **larger** there (mispricing
persists), even though it is **not tradable** on the short side. Among shortable names,
arbitrage should shrink the anomaly. *Test:* split by time-varying eligibility; `DS × RET ×
Shortable`; and an event study around additions to the list. *Tradability note:* even on the
eligible list, 融券 borrow is scarce, expensive, and recallable — so the academic long–short
overstates what is investable, which feeds directly into §7.

### 6.5 Retail attention (high vs. low)

*Proxy.* Abnormal turnover / abnormal volume (baseline, in Wind); Baidu search index or East
Money Guba post counts (robustness, external). The paper used abnormal Google search.

*Hypothesis.* Salience is an attention mechanism, so the high-DS reversal should be stronger
among high-attention stocks; and, as a mechanism check, **DS should be positively correlated
with abnormal volume/attention** (replicating the paper). *Test:* split by attention,
`Attention × DS × RET`, and report `corr(DS, abnormal volume)`. *Caveat:* attention, turnover,
volatility, and small size are entangled — control jointly.

### 6.6 SOE vs. private firms (exploratory)

*Hypothesis.* SOEs — more stable, lower retail attention, possible implicit price support — may
show **weaker** salience overreaction than retail-favored private firms. *Test:* `SOE × DS ×
RET` and subsample split using Wind ownership nature. *Caveat:* SOEs cluster in particular
industries and skew large, confounding with size/industry; this is explicitly **exploratory**,
not a pre-planned core test.

---

## 7. Feasibility analysis

### 7.1 What to build first (minimum viable replication)

**Industry-peer DS, Main Board + ChiNext, 2010–2024, monthly EW & VW double sorts + the
Fama-MacBeth regression with size / B-M / momentum / Amihud / idio-vol / turnover controls.**
Everything it needs is a Wind monthly pull plus one daily pull. Get this working and trustworthy
before touching analyst peers, attention data, or the extensions. The repo's scripts `01`→`04`
are exactly this path.

### 7.2 What is likely hard (data availability)

- **Analyst-peer DS** — assembling the monthly analyst↔firm shared-coverage matrix is heavy,
  and coverage is sparse/large-cap-biased, so it induces selection. *Robustness, not baseline.*
- **Institutional ownership** — quarterly only; timing/interpolation care; early-sample gaps.
- **Retail-attention series (Baidu/Guba)** — external to Wind; licensing/scraping effort.
- **Short-eligibility history** — available in Wind but must be handled strictly point-in-time.
- **Amihud & idio vol** — require clean daily data with correct handling of limit/suspension days.

### 7.3 Academic feasibility vs. live-trading feasibility (kept separate)

**Academic.** The DS-conditioned long–short WML is a legitimate *statistical* test under the
usual assumption of frictionless shorting and execution at the formation close. This is
feasible now and is the project's first deliverable.

**Live trading — why A-share frictions make the long–short largely non-implementable:**

1. **Shorting.** Most stocks are not on the eligibility list; even for those that are, 融券
   borrow is scarce, costly, and recallable. The high-DS leg — *short the overpriced salient
   winners* — is the part that cannot be executed for most names. This alone means the headline
   long–short is mostly a paper portfolio.
2. **T+1 settlement.** Shares bought today cannot be sold today; rebalancing is constrained.
3. **Price limits and execution risk.** A formation-day limit-up winner cannot be bought, and a
   limit-down loser cannot be sold — i.e., *the extreme names the strategy most wants to trade
   are the ones it cannot transact*, and this execution risk is **correlated with the signal**.
4. **Suspensions.** Positions can be frozen for weeks or months (especially pre-2016), stranding
   capital.
5. **Transaction costs.** Commission (~2–3 bps/side today), stamp duty on sells (0.05% since
   Aug 2023, previously 0.1%), plus market impact. Monthly rebalancing of *extreme* deciles
   means high turnover, so costs bite hard.
6. **Microcap concentration.** If the effect lives mainly in EW small caps, those are exactly
   the names with the worst liquidity and the largest impact costs.

*Disciplined conclusion (to test, not assert):* even if DS-conditioned predictability is
statistically robust, the *tradable* implementation is likely a **long-only or long-tilt**
strategy — buy low-DS winners and high-DS losers — rather than the full long–short, and **net-
of-cost, friction-constrained** returns must be shown before any tradability claim is made.

---

## 8. Suggested paper structure

### 8.1 Title

> **Deviation Salience and the Coexistence of Short-Term Momentum and Reversal in China's
> A-Share Market: The Role of Price Limits and Short-Sale Constraints**

### 8.2 Abstract (draft)

> We adapt the deviation-salience (DS) framework of Chen, Wang & Yu (2024) to China's
> A-share market and test whether the sign of one-month return predictability depends on
> salience — reversal among stocks whose return diverges sharply from industry peers,
> continuation among those that blend in. Because A-shares combine heavy retail participation
> with daily price limits, T+1 settlement, and tight short-sale constraints, the setting lets
> us ask not only whether the behavioral pattern replicates out of sample but also how market
> design reshapes it. We examine whether price limits delay and smear the high-DS reversal
> relative to the transient one-month U.S. reversal, and whether short-sale constraints make
> the reversal statistically larger yet economically untradable among non-shortable names.
> Throughout, we separate statistical predictability, economic significance, and real-world
> tradability under realistic frictions. [Findings to be added once estimated.]

### 8.3 Section outline

1. **Motivation** — why short-term momentum and reversal matter; why salience may explain both;
   why A-shares are a useful, high-powered setting.
2. **Original paper summary** — what deviation salience is; what Chen, Wang & Yu (2024)
   document in the U.S.; precisely what we replicate vs. extend.
3. **A-share institutional background** — price limits, ST/\*ST, T+1, short-sale/margin regime,
   suspensions, boards, retail dominance (see `ashare_institutional_background.md`).
4. **Data** — universe, period, sources (Wind), filters.
5. **Methodology** — DS construction (industry baseline; characteristic and analyst robustness),
   peer-return construction, portfolio sorts, Fama-MacBeth design, factor models (CH-3/CH-4).
6. **Baseline results** — summary statistics, double sorts, Fama-MacBeth.
7. **China-specific extensions** — price-limit interaction, board differences, ST/\*ST,
   short-sale eligibility, retail attention, SOE vs. private.
8. **Robustness** — alternative peers, weighting, holding horizons (1–12m), subperiods,
   microcap/price screens, transaction costs, placebos.
9. **Limitations** — data limits, shorting constraints, execution risk; whether the factor is
   tradable.
10. **Conclusion** — what the evidence supports, what remains uncertain, what to test next.

### 8.4 Table and figure list

| # | Content |
|---|---|
| Table 1 | Summary statistics by DS quintile; firm characteristics and correlations with DS |
| Table 2 | Double-sort 5×10 returns (EW & VW); WML by DS group and high−low, with CH-3/CH-4 alphas |
| Table 3 | Fama-MacBeth regressions: `DS × RET` plus controls and control×RET interactions |
| Table 4 | Price-limit interaction: limit-hit subsamples, multi-horizon WML, re-execution at open/VWAP |
| Table 5 | Board-level results: Main Board vs. STAR/ChiNext |
| Table 6 | ST/\*ST inclusion vs. exclusion |
| Table 7 | Short-sale eligibility split; tradable vs. non-tradable leg decomposition |
| Table 8 | Retail-attention split; `corr(DS, abnormal volume)` mechanism check |
| Table 9 | SOE vs. private (exploratory) |
| Table 10 | Robustness: alternative peers, weighting, holding horizons, subperiods, screens |
| Table 11 | Transaction-cost-adjusted / friction-constrained net returns (tradability) |
| Table 12 | Placebo tests: absolute return difference; market-return / random peers |
| Figure 1 | WML by DS quintile (bar chart) |
| Figure 2 | Cumulative WML for high- vs. low-DS over 1–12 months |

---

## 9. Python implementation plan

The repository already lays this out as importable modules (`src/`) driven by thin scripts
(`scripts/`). Roadmap and pseudocode below; the working code lives in the modules named.

### 9.1 Roadmap (phases)

- **Phase 0 — Plumbing (done in this repo).** Config, synthetic-data generator, end-to-end run
  on fake data so the pipeline is verified before real data arrives.
- **Phase 1 — Data layer.** `data_loading.py` turns Wind exports into a tidy monthly panel
  keyed by `(stock, month)` plus a daily panel; `filters.py` applies §2.3.
- **Phase 2 — Signal layer.** `peers.py` builds industry/characteristic/analyst peer returns;
  `deviation_salience.py` computes DS; `controls.py` builds the control set.
- **Phase 3 — Tests.** `portfolios.py` (double sort + WML, EW/VW), `regressions.py`
  (Fama-MacBeth + Newey-West).
- **Phase 4 — Extensions.** `extensions.py` runs the §6 interaction tests.
- **Phase 5 — Reporting.** Scripts write tables to `output/tables/` and figures to
  `output/figures/`.

### 9.2 Pseudocode

**Monthly panel and returns**

```python
# data_loading.build_monthly_panel
raw   = load_wind_monthly(paths.raw)          # stock, month, ret, mktcap, industry, st, board, ...
panel = raw.sort_values(["stock", "month"])
panel["ret"]  = monthly_total_return(panel)   # dividend-reinvested
panel["rf"]   = merge_riskfree(panel["month"])
panel["exret"] = panel["ret"] - panel["rf"]
return panel
```

**Industry peer return (exclude self)**

```python
# peers.industry_peer_return
g = panel.groupby(["month", "industry"])
sum_ret = g["ret"].transform("sum")
n       = g["ret"].transform("size")
panel["peer_ret"] = (sum_ret - panel["ret"]) / (n - 1)     # leave-one-out mean
panel.loc[n < min_peers + 1, "peer_ret"] = np.nan          # require >= min_peers peers
return panel
```

**Deviation salience**

```python
# deviation_salience.compute_ds
num = (panel["ret"] - panel["peer_ret"]).abs()
den = (panel["ret"] - panel["rf"]).abs() + (panel["peer_ret"] - panel["rf"]).abs()
panel["DS"] = np.where(den > 0, num / den, np.nan)         # DS in [0, 1]
return panel
```

**Double sort and WML**

```python
# portfolios.double_sort
panel["ds_q"]  = panel.groupby("month")["DS"].transform(qcut_labels, q=5)
panel["ret_d"] = panel.groupby(["month", "ds_q"])["ret"].transform(qcut_labels, q=10)
panel["fwd"]   = panel.groupby("stock")["ret"].shift(-1)   # t+1 return (held one month)

port = (panel.groupby(["month", "ds_q", "ret_d"])
             .apply(lambda x: weighted_mean(x["fwd"], x["mktcap"] if vw else None)))
wml  = port.xs(10, level="ret_d") - port.xs(1, level="ret_d")   # winners - losers per DS group
# spreads: wml[ds_q=5] (expect <0), wml[ds_q=1] (expect >0), and their difference
tstat = newey_west_tstat(spread_timeseries, lags=6)
```

**Fama-MacBeth**

```python
# regressions.fama_macbeth
rows = []
for m, x in panel.groupby("month"):
    x = winsorize_cols(x, cols=regressors, pct=0.01)
    x["DS_x_RET"] = x["DS"] * x["RET"]
    X = add_constant(x[["DS", "RET", "DS_x_RET", *controls, *control_interactions]])
    rows.append(OLS(x["fwd"], X, missing="drop").fit().params)
betas = pd.DataFrame(rows)                       # one row per month
mean_beta = betas.mean()
tstat     = mean_beta / newey_west_se(betas, lags=6)   # report b3 on DS_x_RET (expect < 0)
```

### 9.3 Stack and conventions

`pandas` + `numpy` for the panel, `statsmodels` for OLS and Newey-West, `scipy` where needed,
`matplotlib` for the two figures, `pytest` for unit tests. All result-affecting parameters live
in `config/config.yaml`, never hard-coded in modules. Intermediate panels are cached as parquet
in `data/interim` and `data/processed`.

---

## Appendix — Test taxonomy (anti-overfitting discipline)

To keep the project from becoming data mining, every test is tagged **before** results are seen:

- **Pre-planned (confirmatory):** the §1.1 sub-questions; the §4 double sort; the §5
  Fama-MacBeth with `DS × RET`; the §6.1 price-limit and §6.4 short-eligibility extensions;
  the §3.4 placebos.
- **Robustness:** alternative peers (characteristic, analyst), EW vs. VW, holding horizons
  (1–12m), subperiods, microcap/price screens, transaction-cost adjustment.
- **Exploratory (clearly labeled):** §6.6 SOE vs. private; any new filter or peer definition
  introduced *after* seeing baseline results.

The main hypothesis (DS governs the sign of short-horizon predictability; frictions modulate
it) is fixed in advance. Filters are not added until a result "looks good"; any deviation from
this plan is documented as exploratory.

