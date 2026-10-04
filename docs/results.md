# Empirical results

The corrected baseline does not provide strong evidence for the central low-DS versus high-DS portfolio contrast. The study reports fixed alternatives and controlled regressions alongside that baseline; these use an already-examined historical sample and are exploratory.

## Baseline

The signal is an industry-peer, zero-risk-free-rate adaptation. WML is the next-month return of the highest formation-return group minus the lowest. The central contrast subtracts high-DS WML from low-DS WML using identical available holding months.

| Weighting | Mean | HAC t | 95% CI | Months |
|---|---|---|---|---|
| equal | +0.156% | 0.10 | [-2.909%, +3.221%] | 36 |
| value | +1.227% | 0.80 | [-1.794%, +4.248%] | 36 |

The input price window is 2021-01-04 to 2025-11-28. Portfolio holding months run from March 2021 through November 2025. There are 287,316 formation stock-month observations and 178 unknown holding returns. Primary estimates require every holding's return, so the central contrast uses only 36 of 57 months. The available-month estimates can remain selected by missingness.

## Fixed alternatives

![Fixed robustness comparisons](assets/robustness.svg)

| Specification | Weighting | Mean | HAC t | 95% CI | Months |
|---|---|---|---|---|---|
| baseline | equal | +0.156% | 0.10 | [-2.909%, +3.221%] | 36 |
| baseline | value | +1.227% | 0.80 | [-1.794%, +4.248%] | 36 |
| coarse_3x5 | equal | +0.662% | 0.56 | [-1.649%, +2.974%] | 33 |
| coarse_3x5 | value | +1.457% | 1.05 | [-1.264%, +4.177%] | 33 |
| minimum_5_peers | equal | +0.156% | 0.10 | [-2.909%, +3.221%] | 36 |
| minimum_5_peers | value | +1.227% | 0.80 | [-1.794%, +4.248%] | 36 |
| minimum_cell_10 | equal | +0.156% | 0.10 | [-2.909%, +3.221%] | 36 |
| minimum_cell_10 | value | +1.227% | 0.80 | [-1.794%, +4.248%] | 36 |
| minimum_cell_30 | equal | +0.156% | 0.10 | [-2.909%, +3.221%] | 36 |
| minimum_cell_30 | value | +1.227% | 0.80 | [-1.794%, +4.248%] | 36 |
| no_bj | equal | +0.073% | 0.05 | [-2.759%, +2.905%] | 36 |
| no_bj | value | +1.557% | 1.07 | [-1.304%, +4.417%] | 36 |
| no_bj_no_bottom20cap | equal | +0.973% | 0.82 | [-1.341%, +3.288%] | 55 |
| no_bj_no_bottom20cap | value | +1.804% | 1.44 | [-0.659%, +4.267%] | 55 |

All fourteen headline confidence intervals include zero. The 3 × 5 specification changes group breadth. Universe exclusions use formation-time data. Minimum-count and peer choices are fixed sensitivity checks, not an optimization grid. Identical headline estimates for some thresholds reflect unchanged contributing corner portfolios; they are not independent confirmations. An isolated significant result is not treated as confirmatory evidence.

## Reversal benchmark

The unconditional WML sort uses the same formation cohort without sorting on DS. Rows beginning `common_` use the intersection of low-DS, high-DS and unconditional WML months; compare those rows with each other. The standalone unconditional row has its own available-month sample.

| Weighting | Series | Mean | HAC t | 95% CI | Months |
|---|---|---|---|---|---|
| equal | common_highDS_WML | +0.102% | 0.15 | [-1.242%, +1.446%] | 28 |
| equal | common_lowDS_WML | -0.328% | -0.20 | [-3.499%, +2.844%] | 28 |
| equal | common_lowDS_minus_highDS | -0.430% | -0.21 | [-4.358%, +3.499%] | 28 |
| equal | common_unconditional_WML | -0.776% | -0.61 | [-3.288%, +1.736%] | 28 |
| equal | unconditional_WML | -0.794% | -0.64 | [-3.217%, +1.630%] | 29 |
| value | common_highDS_WML | -0.242% | -0.28 | [-1.967%, +1.483%] | 28 |
| value | common_lowDS_WML | +0.469% | 0.27 | [-2.965%, +3.903%] | 28 |
| value | common_lowDS_minus_highDS | +0.711% | 0.35 | [-3.249%, +4.672%] | 28 |
| value | common_unconditional_WML | -0.089% | -0.05 | [-3.401%, +3.222%] | 28 |
| value | unconditional_WML | -0.012% | -0.01 | [-3.245%, +3.222%] | 29 |

## Controlled cross-sectional regressions

Monthly regressions predict raw next-calendar-month returns. The reported coefficient multiplies standardized formation return by standardized DS. A negative coefficient is consistent with a more negative return slope at higher DS. The controlled model adds log capitalization, prior 12–2 momentum, and trailing monthly volatility. In the table, percentages express percentage points of next-month return per standardized interaction unit. These month-specific units are not directly comparable to the portfolio spread above.

| Universe | Model | Mean | HAC t | 95% CI | Months |
|---|---|---|---|---|---|
| baseline | controls | -0.086% | -0.54 | [-0.397%, +0.224%] | 46 |
| baseline | uncontrolled | -0.097% | -0.48 | [-0.491%, +0.297%] | 57 |
| no_bj | controls | -0.088% | -0.61 | [-0.375%, +0.198%] | 46 |
| no_bj | uncontrolled | -0.119% | -0.61 | [-0.500%, +0.263%] | 57 |
| no_bj_no_bottom20cap | controls | -0.097% | -0.65 | [-0.388%, +0.194%] | 46 |
| no_bj_no_bottom20cap | uncontrolled | -0.141% | -0.69 | [-0.542%, +0.261%] | 57 |

Regression outcomes use observed-return complete cases, with coverage reported by the script. No liquidity control, factor alpha, causal identification, or out-of-sample validation is claimed.

## Missing-return sensitivity

| Missing-return treatment | Weighting | Mean | HAC t | 95% CI | Months |
|---|---|---|---|---|---|
| complete | equal | +0.156% | 0.10 | [-2.909%, +3.221%] | 36 |
| complete | value | +1.227% | 0.80 | [-1.794%, +4.248%] | 36 |
| observed_only_selected_sample | equal | +0.423% | 0.39 | [-1.691%, +2.538%] | 57 |
| observed_only_selected_sample | value | +0.917% | 0.72 | [-1.593%, +3.427%] | 57 |
| unknown_return_loss100_scenario | equal | -0.432% | -0.41 | [-2.502%, +1.639%] | 57 |
| unknown_return_loss100_scenario | value | +0.890% | 0.70 | [-1.616%, +3.397%] | 57 |
| unknown_return_zero_scenario | equal | +0.395% | 0.37 | [-1.717%, +2.507%] | 57 |
| unknown_return_zero_scenario | value | +0.916% | 0.72 | [-1.593%, +3.426%] | 57 |

Only `complete` is the primary portfolio treatment. Observed-only weights are renormalized over a selected sample. Assigning 0% or −100% to unknown holdings is an explicit scenario; neither assignment recovers actual delisting payouts, and these are not sharp bounds for a long-minus-short contrast.

## Historical subperiods

| Holding period | Weighting | Mean | HAC t | 95% CI | Months |
|---|---|---|---|---|---|
| full | equal | +0.156% | 0.10 | [-2.909%, +3.221%] | 36 |
| early_2021_2022 | equal | +1.554% | 0.53 | [-4.194%, +7.303%] | 17 |
| middle_2023 | equal | -2.123% | -1.59 | [-4.734%, +0.487%] | 7 |
| late_2024_2025 | equal | -0.495% | -0.32 | [-3.551%, +2.561%] | 12 |
| full | value | +1.227% | 0.80 | [-1.794%, +4.248%] | 36 |
| early_2021_2022 | value | +1.968% | 0.83 | [-2.690%, +6.626%] | 17 |
| middle_2023 | value | -0.814% | -0.63 | [-3.358%, +1.729%] | 7 |
| late_2024_2025 | value | +1.367% | 0.46 | [-4.414%, +7.148%] | 12 |

These subperiods were not held out from the earlier exploratory work. Their short samples and changing coverage limit the interpretation of differences.

## Targeted interest-rate enrichment

The official FRED/OECD China three-month Treasury yield series supplies formation-month proxies through November 2023, allowing holding returns through December 2023. Annual percentage yield /100/12 approximates monthly carry. It is not a realized bill return or a verified point-in-time vintage. No absent months are filled. The names `rf_proxy_matched` and `zero_rf_matched` denote the same formation window but have 25 and 24 usable contrast months respectively. Compare `rf_on_common`, `zero_on_common`, and `rf_minus_zero` for the identical 24 holding months.

| Comparison | Weighting | Mean | HAC t | 95% CI | Months |
|---|---|---|---|---|---|
| rf_minus_zero | equal | -0.164% | -0.72 | [-0.615%, +0.286%] | 24 |
| rf_minus_zero | value | -0.130% | -0.32 | [-0.939%, +0.679%] | 24 |
| rf_on_common | equal | +0.317% | 0.15 | [-3.778%, +4.412%] | 24 |
| rf_on_common | value | +1.026% | 0.65 | [-2.086%, +4.138%] | 24 |
| rf_proxy_matched | equal | +0.470% | 0.24 | [-3.446%, +4.386%] | 25 |
| rf_proxy_matched | value | +1.014% | 0.67 | [-1.974%, +4.001%] | 25 |
| zero_on_common | equal | +0.482% | 0.22 | [-3.821%, +4.784%] | 24 |
| zero_on_common | value | +1.156% | 0.65 | [-2.320%, +4.633%] | 24 |
| zero_rf_matched | equal | +0.482% | 0.22 | [-3.821%, +4.784%] | 24 |
| zero_rf_matched | value | +1.156% | 0.65 | [-2.320%, +4.633%] | 24 |

## Interpretation and remaining limits

The study produces inconclusive estimates with explicit sensitivity checks. Provider price adjustments, dated identifier histories, delisting consideration and execution constraints require further evidence. Public issuer/exchange checks and the added interest-rate data are documented in [Data sources and quality](data_sources.md).

The original research inspiration is Chen, Wang and Yu, [Salience and Short-term Momentum and Reversals](https://ssrn.com/abstract=4649393). Its published U.S. findings are not results of this A-share study.

## Reproduce and inspect

Read the [fixed evaluation protocol](research_protocol.md) and [reproduction instructions](reproduce.md). Complete aggregate estimates include the [portfolio grid](tables/full/spread_summary.csv), [all regression coefficients](tables/full/regression_summary.csv), and [rate-proxy comparisons](tables/full/rf_spread_summary.csv), including six-lag HAC and all subperiods. These are correlated exploratory estimates, not independent confirmatory tests. Tables contain only aggregate estimates. Raw vendor data, stock-level derived records and local file-path manifests are excluded from this public report.
