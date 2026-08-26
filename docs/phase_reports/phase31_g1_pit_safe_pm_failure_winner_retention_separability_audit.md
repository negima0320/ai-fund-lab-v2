# Phase31-G1 — PIT-Safe PM Failure / Winner Retention Separability Audit

## Scope

Task type: READ-ONLY PERFORMANCE CHARACTERIZATION / SEPARABILITY AUDIT.

Target run:

`runtime-test-historical-extended-smoke-20260821T095536206137Z`

Evidence root:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T095536206137Z`

Primary prior report:

`docs/phase_reports/phase31_g0_clean_100bd_strategy_performance_causal_decomposition_audit.md`

No Strategy mutation, PM mutation, SELL rule change, threshold tuning, weight tuning, feature addition, model retraining, Runtime mutation, config mutation, fresh-run, resume, replay, or Historical rerun was performed.

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G1_PIT_SEPARABILITY_PARTIAL_PM_SEMANTIC_SIGNAL_EXISTS_BUT_WINNER_COLLATERAL_RISK_HIGH`

Existing PIT evidence can detect most short 2-5BD losing campaigns before or by exit, and it also contains explicit winner profit-protection context. However, the same canonical non-healthy SELL states also fire frequently on short 2-5BD winners. Therefore the current evidence is useful but not sufficient for a naive faster SELL rule. The best next design focus is PM action timing and severity semantics, especially `nonhealthy_state + negative current campaign return` and regime-conditioned escalation, not adding new indicators or tuning thresholds on this 100BD window.

## PIT Feature Inventory

| Evidence family | Artifact | Producer / authority | Field examples | PIT binding | Production PM today |
| --- | --- | --- | --- | --- | --- |
| Canonical SELL semantic | `daily/<date>/strategy/position_management.json` | `strategy.sell_semantic_state`, contract `phase31_f1f_pm_canonical_sell_semantic_integration_v1` | `canonical_sell_state`, `canonical_state_reasons`, `final_pm_action`, `pm_deterioration_reasons`, `recovery_state` | `pit_proof.feature_dates` same-day / prior position state, `future_information_used=false` | YES |
| Campaign state | `daily/<date>/strategy/position_management.json` | strategy intelligence connected to PM | `strategy_intelligence_current_campaign_relative_return`, `strategy_intelligence_observed_campaign_mfe`, `strategy_intelligence_observed_giveback`, `campaign_age_business_days` | same-day PM evidence; MFE/giveback observed to date, not future peak | YES |
| Hold/add evidence | `daily/<date>/strategy/position_management.json` | strategy intelligence | `continuation_quality_status`, `downside_risk_status`, `hold_worthiness_evidence`, `profit_protection_status` | same-day PM evidence | YES |
| PM action / reason | `daily/<date>/strategy/position_management.json`; `daily/<date>/position_management/pm_decisions.json` | existing PM authority | `action`, `reason_codes`, `confidence`, `intensity` | same-day PM artifact | YES |
| Technical momentum | `daily/<date>/strategy/technical_features.json` | runtime PM feature input, J-Quants OHLCV derived | `price_momentum_return_1d/3d/5d/10d/20d`, `momentum_1d_vs_5d_delta`, `momentum_5d_vs_20d_delta` | `feature_date`, `data_until`, `temporal_validation_status=PASS` | YES |
| Trend relationship | `daily/<date>/strategy/technical_features.json` | runtime PM feature input | `trend_close_over_ma_20d`, `trend_ma_5_20_ratio` | same as above | YES |
| Volatility / downside proxy | `daily/<date>/strategy/technical_features.json`; `price_volatility.json` | runtime PM feature input | `recent_move_volatility_z_1d`, `recent_move_volatility_z_3d`, `volatility_return_std_20d`, `volatility_value` | same as above | YES |
| Volume / liquidity | `daily/<date>/strategy/technical_features.json` | runtime PM feature input | `volume_momentum_ratio_5d`, `rolling_median_traded_value_20` | same as above | YES |
| Market Context | `daily/<date>/strategy/market_context.json` | Market Context authority | `regime_state`, `trend_regime`, `breadth_state`, `volatility_state`, `trend_strength` | `feature_date` / same business date | YES |

No new feature family was introduced in this audit.

## Cohorts

Symbol-level campaign economics reconcile to G0 canonical PnL authority. The G1 cohort split is:

| Cohort | Count | PnL / loss |
| --- | ---: | ---: |
| A1: 2-5BD losers | 57 | -183,480 |
| A2: 2-5BD winners | 40 | +75,690 |
| 2-5BD flat | 8 | 0 |
| C: 11BD+ winners | 22 | +199,700 |
| Other | 34 | mixed |

The G0 duration bucket had 105 completed 2-5BD campaigns; G1 separates that into 57 losing, 40 winning, and 8 flat campaigns.

## Feature Separability Table

Diagnostic separability only. AUC is post-hoc rank separability where `0.5` means no separation and values below `0.5` mean the feature tends to be lower in 2-5BD losers than in 11BD+ winners. This is not a production model and not parameter selection.

Early row = first available PM row at offset +1BD to +5BD.

| Feature | A1 2-5BD loser median | C 11BD+ winner median | AUC loser higher | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `current_campaign_relative_return` | 0.0000 | 0.0233 | 0.223 | Strong direction: losers lower. |
| `observed_campaign_mfe` | 0.0000 | 0.0233 | 0.223 | Same as current return in early window. |
| `trend_close_over_ma_20d` | 0.0000 | 1.1138 | 0.290 | Long winners show clearer trend support. |
| `price_momentum_return_20d` | 0.0000 | 0.3062 | 0.302 | Long winners have stronger medium momentum. |
| `price_momentum_return_3d` | 0.0000 | 0.0281 | 0.309 | Modest direction. |
| `trend_ma_5_20_ratio` | 0.0000 | 1.0678 | 0.367 | Modest direction. |
| `confidence` | 0.0000 | 0.4669 | 0.359 | PM confidence is higher for long winners. |
| `price_momentum_return_5d` | 0.0000 | 0.0276 | 0.411 | Weak/moderate direction. |
| `volume_momentum_ratio_5d` | 0.0000 | 1.0517 | 0.497 | No useful standalone separation. |
| `volatility_return_std_20d` | 0.0000 | 0.0753 | 0.520 | No useful standalone separation. |

Raw technical fields alone are weaker than existing PM semantic fields. The strongest current evidence is semantic/contextual: canonical SELL state, campaign return, and whether recovery reasons remain present.

## Canonical SELL State Separability

First available early PM row:

| Cohort | N | Non-healthy state count | Non-healthy rate | State distribution | Action distribution |
| --- | ---: | ---: | ---: | --- | --- |
| A1 2-5BD losers | 57 | 41 | 71.9% | EXIT_GRADE 19; WEAKENING_BUT_INTACT 22; HEALTHY_OR_RECOVERING 16 | EXIT 19; REDUCE 22; HOLD 16 |
| A2 2-5BD winners | 40 | 33 | 82.5% | EXIT_GRADE 19; WEAKENING_BUT_INTACT 14; HEALTHY_OR_RECOVERING 7 | EXIT 19; REDUCE 14; HOLD 7 |
| C 11BD+ winners | 22 | 5 | 22.7% | WEAKENING_BUT_INTACT 5; HEALTHY_OR_RECOVERING 17 | REDUCE 5; HOLD 17 |

All PM rows:

| Canonical state | Rows | Loss-outcome rows | Winner-outcome rows | Actions |
| --- | ---: | ---: | ---: | --- |
| HEALTHY_OR_RECOVERING | 616 | 189 | 422 | HOLD 542; ADD 74 |
| WEAKENING_BUT_INTACT | 131 | 55 | 69 | REDUCE 131 |
| PERSISTENT_DETERIORATION | 61 | 36 | 19 | EXIT 61 |
| EXIT_GRADE | 97 | 42 | 52 | EXIT 96; HOLD 1 |

Conclusion: canonical SELL state is useful for separating long healthy winners from churn, but it does not cleanly separate 2-5BD losers from 2-5BD winners. A naive "non-healthy means exit faster" policy has high premature-exit risk.

`CANONICAL_SELL_STATE_SEPARABILITY = PARTIAL_HIGH_COLLATERAL_RISK`

## Existing Multi-Feature Separability

Pre-declared combinations:

| Combination | A1 hit rate | A2 hit rate | C hit rate | Read |
| --- | ---: | ---: | ---: | --- |
| non-healthy canonical state | 41/57 = 71.9% | 33/40 = 82.5% | 5/22 = 22.7% | Detects churn but damages short winners. |
| non-healthy + current return < 0 | 28/57 = 49.1% | 2/40 = 5.0% | 1/22 = 4.5% | Best PIT-safe separability found. |
| non-healthy + adverse/non-expansion regime | 26/57 = 45.6% | 14/40 = 35.0% | 2/22 = 9.1% | Helpful mostly against long winners; still overlaps short winners. |
| EXIT_GRADE only | 19/57 = 33.3% | 19/40 = 47.5% | 0/22 = 0.0% | Too much short-winner overlap. |
| WEAKENING_BUT_INTACT only | 22/57 = 38.6% | 14/40 = 35.0% | 5/22 = 22.7% | Weak standalone signal. |

`EXISTING_MULTI_FEATURE_SEPARABILITY = MODERATE_FOR_NONHEALTHY_PLUS_NEGATIVE_RETURN; WEAK_FOR_NONHEALTHY_STATE_ALONE`

## Failure Detectability

Earliest detectable state for A1 2-5BD losers, using canonical non-healthy SELL state, PM deterioration reasons, or REDUCE/EXIT action:

| Earliest bucket | Campaigns | Loss yen | Example symbols |
| --- | ---: | ---: | --- |
| DETECTABLE_+1BD | 41 | 130,680 | 13840, 72110, 73560, 41990, 82540, 33500, 37790, 73680 |
| DETECTABLE_+2BD | 9 | 24,700 | 68360, 95010, 23530, 70140, 39410, 44220, 89440, 73590 |
| DETECTABLE_+3_TO_5BD | 7 | 28,100 | 92420, 36790, 80780, 27780, 65790, 35280, 60540 |
| NOT_SEPARABLE | 0 | 0 | none under canonical semantic/action definition |
| INSUFFICIENT_EVIDENCE | 0 | 0 | none |

This does not mean all 183,480 yen was avoidable. It means contemporaneous PM/SELL evidence did identify the failing positions by +5BD. Winner-control overlap remains the gating constraint.

`PIT_DETECTABLE_2_5BD_LOSS_YEN = 183,480`

`EARLIEST_FAILURE_DETECTABILITY_TABLE = +1BD 41 / 130,680; +2BD 9 / 24,700; +3_TO_5BD 7 / 28,100`

## Healthy Pullback False Exit Risk

Healthy long winners with early non-healthy / pullback-like signals:

| Symbol | Date | Current return | State | Action | Final campaign PnL |
| --- | --- | ---: | --- | --- | ---: |
| 76470 | 2022-08-16 | -3.70% | WEAKENING_BUT_INTACT | REDUCE | +1,200 |
| 27670 | 2022-08-29 | +3.18% | WEAKENING_BUT_INTACT | REDUCE | +17,800 |
| 26660 | 2022-11-09 | +0.73% | WEAKENING_BUT_INTACT | REDUCE | +5,000 |
| 97310 | 2022-11-17 | +0.12% | WEAKENING_BUT_INTACT | REDUCE | +10,200 |
| 32050 | 2022-12-07 | +2.04% | WEAKENING_BUT_INTACT | REDUCE | +600 |

False-exit risk is not low. It is moderate to high if using canonical non-healthy state alone. It becomes lower when requiring both non-healthy state and negative campaign return, but that also detects only about half of short losers.

`HEALTHY_PULLBACK_FALSE_EXIT_RISK = HIGH_FOR_STATE_ONLY; MODERATE_FOR_STATE_PLUS_NEGATIVE_RETURN`

## Winner Deterioration Timeline Summary

G0 winner giveback reference recomputed from metadata-covered winners:

`TOTAL_WINNER_GIVEBACK_YEN = 199,240`

Top winner-giveback cases:

| Symbol | Giveback | Final profit | Approx peak profit | First non-healthy PIT date | First state/action | Actual close |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 97310 | 30,200 | 10,200 | 40,400 | 2022-11-17 | WEAKENING_BUT_INTACT / REDUCE | 2022-12-20 |
| 78780 | 24,000 | 14,500 | 38,500 | 2022-09-14 | WEAKENING_BUT_INTACT / REDUCE | 2022-09-15 |
| 78860 | 18,400 | 23,900 | 42,300 | 2022-12-02 | WEAKENING_BUT_INTACT / REDUCE | 2022-12-07 |
| 70640 | 17,750 | 18,000 | 35,750 | 2022-10-13 | EXIT_GRADE / EXIT | 2022-10-13 |
| 88910 | 15,000 | 17,200 | 32,200 | 2022-09-01 | WEAKENING_BUT_INTACT / REDUCE | 2022-09-28 |
| 69730 | 11,600 | 28,500 | 40,100 | 2022-11-04 | WEAKENING_BUT_INTACT / REDUCE | 2022-12-05 |
| 93600 | 11,500 | 16,700 | 28,200 | 2022-10-20 | EXIT_GRADE / EXIT | 2022-10-20 |
| 62490 | 7,200 | 43,200 | 50,400 | 2022-11-01 | WEAKENING_BUT_INTACT / REDUCE | 2022-12-12 |

All 199,240 yen of winner giveback had some PIT semantic deterioration or profit-protection evidence, but it is not all safely recoverable. The same states appear in healthy pullback and short-winner controls.

| Bucket | Yen |
| --- | ---: |
| PIT_DETECTABLE_WITH_STRONG_SEPARABILITY | 0 |
| PIT_DETECTABLE_WITH_MODERATE_SEPARABILITY | 199,240 |
| PIT_DETECTABLE_WITH_HIGH_WINNER_COLLATERAL_RISK | included in above, especially state-only usage |
| NOT_PIT_DETECTABLE | 0 |
| INSUFFICIENT_EVIDENCE | 0 |

`PIT_DETECTABLE_WINNER_GIVEBACK_YEN = 199,240_WITH_MODERATE_SEPARABILITY_NOT_FULLY_RECOVERABLE`

## Regime Conditional Separability

First early PM row non-healthy rate by regime:

| Cohort | BULL | RANGE | RECOVERY | CORRECTION | BEAR |
| --- | ---: | ---: | ---: | ---: | ---: |
| A1 2-5BD losers | 8/12 = 66.7% | 12/15 = 80.0% | 7/13 = 53.8% | 3/4 = 75.0% | 11/13 = 84.6% |
| A2 2-5BD winners | 13/17 = 76.5% | 7/7 = 100.0% | 6/6 = 100.0% | 3/3 = 100.0% | 4/7 = 57.1% |
| C 11BD+ winners | 3/9 = 33.3% | 2/6 = 33.3% | 0/4 = 0.0% | n/a | 0/3 = 0.0% |

Regime helps protect long winners from false positives: long winners in RECOVERY/BEAR had no early non-healthy signal in this sample. But regime does not cleanly separate short losers from short winners. The useful design direction is regime-conditioned severity / persistence, not regime as a standalone switch.

`REGIME_CONDITIONAL_SEPARABILITY = PARTIAL; IMPROVES_LONG_WINNER_COLLATERAL_CONTROL_BUT_NOT_SHORT_WINNER_SEPARATION`

## PM Failure Mode Table

For A1 2-5BD losers:

| Failure mode | Campaigns | Loss yen | Interpretation |
| --- | ---: | ---: | --- |
| PM_ACTION_ESCALATED_BUT_LOSS_REALIZED | 57 | 183,480 | PM/SELL did escalate via REDUCE/EXIT within 2-5BD; remaining loss is mostly execution of a necessary stop, one-lot/minimum-notional constraints, or delayed severity rather than absent evidence. |
| EVIDENCE_AVAILABLE_BUT_SEMANTIC_STATE_DID_NOT_ESCALATE | 0 | 0 | Not observed for A1 under current canonical semantic. |
| SEMANTIC_ESCALATED_PM_ACTION_LAGGED | 0 | 0 | Not observed in A1 first-detectable rows; actions were already REDUCE/EXIT when non-healthy. |
| EVIDENCE_INSUFFICIENT | 0 | 0 | Not observed. |

For winner giveback, the failure mode differs: evidence frequently existed as `WEAKENING_BUT_INTACT` or `EXIT_GRADE`, but collateral-risk against winners makes direct escalation unsafe without better severity semantics.

`PM_FAILURE_MODE_TABLE = A1 losses: action escalated but loss realized; winner giveback: evidence present but safe severity/persistence distinction incomplete`

## Economic Scope

| Scope | Yen | Confidence | Collateral risk |
| --- | ---: | --- | --- |
| Potential avoided 2-5BD loss with PIT detection | 183,480 | High detection, low recoverability certainty | High if state-only; moderate if state+negative return |
| Potential preserved winner profit | 199,240 | Moderate | High if state-only |
| Premature-exit winner damage, state-only proxy | At least 75,690 from A2 short winners, plus long-winner risk | High | High |
| Safer candidate: non-healthy + negative current return | 28/57 A1 losers, only 2/40 A2 winners and 1/22 long winners | Moderate | Moderate/low |

`NET_DIAGNOSTIC_ECONOMIC_SCOPE = POSITIVE_BUT_NOT_QUANTIFIABLE_AS_EXPECTED_PNL_WITHOUT_CROSS_WINDOW_VALIDATION`

Do not treat this as expected future PnL. It is only diagnostic scope.

## No-Hindsight Design Proof

The recommended next design direction may use only:

- `canonical_sell_state`
- `current_campaign_relative_return`
- `observed_giveback` observed to date
- `continuation_quality_status`
- `downside_risk_status`
- `pm_deterioration_reasons`
- `recovery_state`
- same-day `regime_state`
- same-day technical features from `technical_features.json`

It must not use:

- future MFE peak
- final campaign PnL
- future return
- later close date
- this 100BD outcome as a threshold selector

MFE/giveback and final PnL were used here only for post-hoc cohort labeling and diagnostic attribution.

`NO_HINDSIGHT_DESIGN_PROOF = PASS`

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G1_PIT_SEPARABILITY_PARTIAL_PM_SEMANTIC_SIGNAL_EXISTS_BUT_WINNER_COLLATERAL_RISK_HIGH`

`TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260821T095536206137Z`

`PIT_FEATURE_INVENTORY = canonical_sell_state; current_campaign_relative_return; observed_to_date_mfe/giveback; continuation_quality_status; downside_risk_status; PM action/reasons; technical momentum/trend/volatility/volume; market_context.regime_state`

`TOTAL_2_5BD_LOSS_CAMPAIGNS = 57`

`TOTAL_2_5BD_LOSS_YEN = 183,480`

`PIT_DETECTABLE_2_5BD_LOSS_YEN = 183,480`

`TOTAL_WINNER_GIVEBACK_YEN = 199,240`

`PIT_DETECTABLE_WINNER_GIVEBACK_YEN = 199,240_WITH_MODERATE_SEPARABILITY_NOT_FULLY_RECOVERABLE`

`HEALTHY_PULLBACK_FALSE_EXIT_RISK = HIGH_FOR_STATE_ONLY; MODERATE_FOR_STATE_PLUS_NEGATIVE_RETURN`

`FEATURE_SEPARABILITY_TABLE = strongest: current_campaign_relative_return lower in losers, AUC loser-higher 0.223; trend_close_over_ma_20d AUC 0.290; price_momentum_return_20d AUC 0.302; raw volume/volatility weak`

`EXISTING_MULTI_FEATURE_SEPARABILITY = MODERATE_FOR_NONHEALTHY_PLUS_NEGATIVE_RETURN; WEAK_FOR_NONHEALTHY_STATE_ALONE`

`REGIME_CONDITIONAL_SEPARABILITY = PARTIAL; HELPS_LONG_WINNER_COLLATERAL_CONTROL`

`CANONICAL_SELL_STATE_SEPARABILITY = PARTIAL_HIGH_COLLATERAL_RISK`

`PM_FAILURE_MODE_TABLE = A1 losses: PM_ACTION_ESCALATED_BUT_LOSS_REALIZED 57 / 183,480; winner giveback: evidence present but severity/persistence incomplete`

`EARLIEST_FAILURE_DETECTABILITY_TABLE = +1BD 41 / 130,680; +2BD 9 / 24,700; +3_TO_5BD 7 / 28,100`

`WINNER_DETERIORATION_TIMELINE_SUMMARY = top giveback symbols 97310, 78780, 78860, 70640, 88910, 69730, 93600, 62490 all had first non-healthy PIT state before/at actual close`

`NET_DIAGNOSTIC_ECONOMIC_SCOPE = POSITIVE_BUT_NOT_EXPECTED_PNL; state-only collateral risk high`

`EXISTING_FEATURES_SUFFICIENCY = EXISTING_FEATURES_PARTIALLY_SUFFICIENT`

`NEW_FEATURE_REQUIRED_NOW = NO`

`NO_HINDSIGHT_DESIGN_PROOF = PASS`

`PRODUCTION_PARAMETER_CHANGE_AUTHORIZED = NO`

`STRATEGY_MUTATION_AUTHORIZED = NO`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`TOP_NEXT_DESIGN_CANDIDATES = 1. PM severity/persistence contract for nonhealthy+negative-return; 2. winner profit-protection severity semantics using observed-to-date giveback; 3. regime-conditioned PM escalation confirmation`

`NEXT_TASK_RECOMMENDATION = design a PIT-safe PM severity/persistence contract that uses existing canonical SELL semantic plus current campaign return and regime context, with explicit winner-collateral controls`

