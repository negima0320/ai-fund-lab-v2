# Phase31-G2 — PIT-Safe PM Severity / Persistence / HOLD-Regret Separability Audit

## Scope

Task type: READ-ONLY PERFORMANCE CHARACTERIZATION / SEVERITY-PERSISTENCE AUDIT.

Target run:

`runtime-test-historical-extended-smoke-20260821T095536206137Z`

Evidence root:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T095536206137Z`

Prior reports read:

- `docs/phase_reports/phase31_g0_clean_100bd_strategy_performance_causal_decomposition_audit.md`
- `docs/phase_reports/phase31_g1_pit_safe_pm_failure_winner_retention_separability_audit.md`

No Strategy mutation, PM mutation, SELL rule change, threshold tuning, weight tuning, config tuning, feature addition, model retraining, Runtime mutation, fresh-run, resume, replay, or Historical rerun was performed.

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G2_READY_FOR_PM_SEVERITY_DESIGN_EXISTING_PIT_FEATURES_PARTIALLY_SUFFICIENT`

G2 confirms the G1 direction: non-healthy canonical state alone is unsafe, but severity/persistence materially improves separability. The most promising PIT-safe semantics are:

1. `nonhealthy + negative current campaign return`
2. `nonhealthy + negative current campaign return + adverse regime`
3. `2 consecutive nonhealthy + negative current campaign return`

The first has the largest diagnostic scope but some winner collateral. The third is safest for winner preservation but misses more losses. None should be converted into production thresholds in G2.

## Severity Feature Inventory

| Field | Artifact | Producer | PIT binding | Missingness in PM rows | Production consumer |
| --- | --- | --- | --- | ---: | --- |
| `canonical_sell_state` | `daily/<date>/strategy/position_management.json` | `strategy.sell_semantic_state` | `pit_proof.feature_dates`, `future_information_used=false` | 0 / 905 | YES |
| `current_campaign_relative_return` | same | strategy intelligence PM bridge | current PM business date; position state may be prior close | 0 / 905 | YES |
| `observed_campaign_mfe` / `observed_giveback` | same | strategy intelligence PM bridge | observed-to-date only; not future peak | 0 / 905 | YES |
| `continuation_quality_status` | same | canonical SELL semantic / strategy intelligence | same PM date | 0 / 905 | YES |
| `downside_risk_status` | same | canonical SELL semantic / strategy intelligence | same PM date | 0 / 905 | YES |
| `pm_deterioration_reasons` | same | canonical SELL semantic | same PM date | 0 / 905 | YES |
| `recovery_state` | same | canonical SELL semantic | same PM date | 0 / 905 | YES |
| `confidence`, `intensity` | same | existing PM authority | same PM date | 0 / 905 | YES |
| `price_momentum_return_1d/3d/5d` | `daily/<date>/strategy/technical_features.json` | runtime PM feature input | `feature_date`, `data_until`, `temporal_validation_status=PASS` | 0 / 905 joined PM rows | YES |
| `trend_close_over_ma_20d`, `trend_ma_5_20_ratio` | same | runtime PM feature input | same | 0 / 905 | YES |
| `recent_move_volatility_z_1d/3d` | same | runtime PM feature input | same | 0 / 905 | YES |
| `regime_state` | `daily/<date>/strategy/market_context.json` | Market Context authority | same business date | 0 / 905 | YES |

`SEVERITY_FEATURE_INVENTORY = EXISTING_PIT_FIELDS_AVAILABLE_NO_NEW_FEATURE`

## Persistence Evidence

The current artifacts are sufficient to measure PIT-safe persistence descriptively:

- consecutive non-healthy PM rows
- consecutive non-healthy + negative current campaign return rows
- repeated REDUCE decisions
- state sequence progression, including `HEALTHY_OR_RECOVERING -> WEAKENING_BUT_INTACT -> PERSISTENT_DETERIORATION / EXIT_GRADE`
- recovery back to `HEALTHY_OR_RECOVERING`
- repeated weakening within 3-5BD

These are measured as fixed natural buckets, not optimized windows.

`PERSISTENCE_EVIDENCE_AVAILABLE = YES`

## Canonical State Sequence Table

Compressed state legend: `H = HEALTHY_OR_RECOVERING`, `W = WEAKENING_BUT_INTACT`, `P = PERSISTENT_DETERIORATION`, `E = EXIT_GRADE`.

| Cohort / sequence | Count | Net PnL | Median current return | Dominant actions |
| --- | ---: | ---: | ---: | --- |
| A1 loser: `E` | 19 | -73,640 | -2.60% | EXIT |
| A1 loser: `W>E` | 7 | -34,480 | -3.22% | REDUCE then EXIT |
| A1 loser: `W>P` | 15 | -22,560 | -1.99% | REDUCE then EXIT |
| A1 loser: `H>W>P` | 9 | -20,500 | -0.40% | HOLD, REDUCE, EXIT |
| A1 loser: `H>W>E` | 4 | -21,900 | +0.26% | HOLD, REDUCE, EXIT |
| A2 short winner: `E` | 19 | +18,400 | +1.52% | EXIT |
| A2 short winner: `W>P` | 9 | +12,430 | +0.64% | REDUCE then EXIT |
| A2 short winner: `H>W>P` | 3 | +21,300 | +3.62% | HOLD, REDUCE, EXIT |
| C long winner: `H` | 11 | +71,100 | +5.71% | mostly HOLD |
| C long winner: `H>W>H` | 5 | +93,500 | +16.27% | HOLD with intermittent REDUCE |
| C long winner: `W>H` | 3 | +29,200 | +9.30% | REDUCE then HOLD recovery |

`CANONICAL_STATE_SEQUENCE_TABLE = losers progress to E/P with negative returns; long winners often recover H after W and retain positive returns`

## Healthy Recovery Control Cases

Healthy recovery control = positive final campaign where canonical state became non-healthy and PM did not fully exit immediately.

Observed: 37 cases, +244,090 final profit.

Representative cases:

| Symbol | Final PnL | Weakness date | State/action | Current return | Giveback | Continuation/downside | Recovery state | Regime |
| --- | ---: | --- | --- | ---: | ---: | --- | --- | --- |
| 62490 | +43,200 | 2022-11-01 | W / REDUCE | +16.16% | 0.00% | PASS / PASS | NO_RECOVERY | BULL |
| 92270 | +31,300 | 2022-11-01 | W / REDUCE | +13.58% | 2.45% | PASS / PASS | NO_RECOVERY | BULL |
| 69730 | +28,500 | 2022-11-04 | W / REDUCE | +5.73% | 3.00% | PASS / PASS | NO_RECOVERY | CORRECTION |
| 40800 | +20,400 | 2022-08-19 | W / REDUCE | +3.24% | 0.85% | PASS / PASS | NO_RECOVERY | BULL |
| 27670 | +17,800 | 2022-08-29 | W / REDUCE | +3.18% | 0.00% | PASS / PASS | NO_RECOVERY | RANGE |
| 88910 | +17,200 | 2022-09-01 | W / REDUCE | +3.87% | 0.00% | PASS / PASS | NO_RECOVERY | RANGE |
| 78780 | +14,500 | 2022-09-14 | W / REDUCE | +8.69% | 9.88% | PASS / PASS | NO_RECOVERY | RANGE |
| 97310 | +10,200 | 2022-11-17 | W / REDUCE | +0.12% | 0.00% | PASS / PASS | NO_RECOVERY | BULL |

These cases are the main HOLD-regret warning. Weakening while current campaign return is still positive often belongs to eventual winners.

`HEALTHY_RECOVERY_CONTROL_CASES = 37 cases / +244,090 final profit`

## Failed Persistence Cases

Representative A1 2-5BD losers:

| Symbol | Loss | First non-healthy | First negative return | Max consecutive non-healthy | First P/E | Exit | Regime |
| --- | ---: | --- | --- | ---: | --- | --- | --- |
| 21950 | -18,670 | 2022-09-01 | 2022-09-01 | 1 | 2022-09-01 | 2022-09-01 | RANGE |
| 21380 | -12,700 | 2022-10-05 | 2022-10-05 | 2 | 2022-10-06 | 2022-10-06 | RANGE |
| 65790 | -9,700 | 2022-11-01 | 2022-10-31 | 2 | 2022-11-02 | 2022-11-02 | BULL |
| 44220 | -9,100 | 2022-09-28 | 2022-09-28 | 2 | 2022-09-29 | 2022-09-29 | BEAR |
| 96100 | -9,000 | 2022-09-01 | 2022-09-01 | 1 | 2022-09-01 | 2022-09-01 | RANGE |
| 92420 | -7,800 | 2022-10-12 | 2022-10-13 | 2 | 2022-10-13 | 2022-10-13 | BEAR |
| 37790 | -6,700 | 2022-12-08 | 2022-12-08 | 1 | 2022-12-08 | 2022-12-08 | RANGE |

`FAILED_PERSISTENCE_CASES = A1 failures usually show non-healthy state plus negative return before/at exit; deeper persistence exists but many failures are short-lived`

## Severity / Persistence Separability

Candidate semantics are diagnostic only. They are not production thresholds.

| Candidate | A1 2-5BD loser hit | A2 2-5BD winner hit | C 11BD+ winner hit | A1 loss captured | A2/C winner profit exposed | Read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| non-healthy state only | 57/57 | 40/40 | 8/22 | 183,480 | 128,090 | Detects everything but unsafe. |
| non-healthy + negative current return | 52/57 | 6/40 | 3/22 | 170,160 | 8,710 | Strongest broad diagnostic scope. |
| non-healthy + negative return + adverse regime | 35/57 | 4/40 | 0/22 | 128,390 | 5,700 | Safer for long winners; misses more loss. |
| 2 consecutive non-healthy | 35/57 | 16/40 | 1/22 | 99,440 | 47,840 | Persistence alone still hits winners. |
| 2 consecutive non-healthy + negative return | 22/57 | 0/40 | 0/22 | 68,320 | 0 | Best winner-preservation profile, lower coverage. |
| worsening to PERSISTENT/EXIT | 57/57 | 40/40 | 0/22 | 183,480 | 75,690 | Protects long winners but damages short winners. |
| profit-protection giveback + non-healthy | 1/57 | 6/40 | 1/22 | 7,800 | 33,300 | Not a loss-control signal. |

`SEVERITY_PERSISTENCE_SEPARABILITY_TABLE = nonhealthy+negative return strongest; 2-consecutive nonhealthy+negative safest`

## Hold Regret / Error Costs

Full-exit diagnostic across all completed campaigns:

| Candidate | Gross avoided loss | Full-exit hold regret / false winner damage | Missed early-exit loss | Net diagnostic full-exit value |
| --- | ---: | ---: | ---: | ---: |
| non-healthy state only | 204,130 | 138,980 | 1,770 | +65,150 |
| non-healthy + negative current return | 186,410 | 8,710 | 19,490 | +177,700 |
| non-healthy + negative return + adverse regime | 141,040 | 5,700 | 64,860 | +135,340 |
| 2 consecutive non-healthy + negative return | 77,070 | 0 | 128,830 | +77,070 |
| 2 consecutive non-healthy | 113,230 | 49,940 | 92,670 | +63,290 |

`HOLD_REGRET_YEN = candidate-dependent; best broad candidate 8,710 full-exit regret; safest persistence candidate 0 full-exit regret`

`FULL_EXIT_HOLD_REGRET_YEN = nonhealthy+negative return 8,710; 2-consecutive nonhealthy+negative return 0`

`REDUCE_HOLD_REGRET_YEN = PARTIAL_UNRESOLVED`

Exact REDUCE counterfactual slice economics were not reconstructed because actual REDUCE quantity may be unrepresentable, rounded to zero, or path-dependent. G2 therefore reports full-exit diagnostic damage and keeps REDUCE regret unresolved rather than inventing a counterfactual.

`FALSE_EXIT_DAMAGE_YEN = 8,710 for nonhealthy+negative return; 0 for 2-consecutive nonhealthy+negative return`

`MISSED_EARLY_EXIT_DAMAGE_YEN = 19,490 for nonhealthy+negative return; 128,830 for 2-consecutive nonhealthy+negative return`

`NET_DIAGNOSTIC_PM_VALUE_YEN = +177,700 for nonhealthy+negative return full-exit diagnostic; +77,070 for 2-consecutive nonhealthy+negative return full-exit diagnostic`

These are diagnostic only, not expected PnL.

## Winner Giveback Severity Decomposition

G0/G1 winner giveback reference: 199,240 yen.

| Bucket | Yen | Rationale |
| --- | ---: | --- |
| SAFE_TO_CONTINUE_HOLD | 0 asserted | Future recovery/peak information cannot be used as production input. |
| POSSIBLE_PROFIT_PROTECTION | 151,790 | Winners with non-healthy state while campaign return remained positive; signal exists but collateral risk is real. |
| STRONG_PROFIT_PROTECTION_CANDIDATE | 0 asserted | No strong PIT-only rule clears winner-preservation gate in G2. |
| HIGH_COLLATERAL_RISK | 47,450 | Giveback cases where the same state/persistence pattern appears in healthy recovery controls. |
| UNRESOLVED | 0 | Metadata-covered giveback cases had PIT semantic evidence. |

Major giveback cases such as 97310, 78780, 78860, 88910, 69730, and 62490 showed first non-healthy PIT state before/at actual close. The issue is not absent evidence; it is severity calibration without sacrificing healthy winners.

`TOTAL_WINNER_GIVEBACK_YEN = 199,240`

`WINNER_GIVEBACK_SEVERITY_DECOMPOSITION = POSSIBLE_PROFIT_PROTECTION 151,790; HIGH_COLLATERAL_RISK 47,450; STRONG 0; UNRESOLVED 0`

## Negative Campaign Return Interpretation

Negative current campaign return is useful only in combination with semantic state. It is not a standalone production rule.

Evidence:

- `nonhealthy + negative current return` hits 52/57 A1 losers and only 6/40 A2 short winners, 3/22 long winners.
- `2 consecutive nonhealthy + negative current return` hits 22/57 A1 losers and 0 A2/C winners.
- Healthy recovery controls often have non-healthy state with positive current return, e.g. 62490 +16.16%, 92270 +13.58%, 69730 +5.73%, 27670 +3.18%.

Interpretation:

`current_campaign_relative_return < 0` is acting as severity evidence and a drawdown/failed-entry proxy when paired with canonical weakening. It is not merely campaign age, and it is not enough by itself.

`NEGATIVE_CAMPAIGN_RETURN_INTERPRETATION = USEFUL_SEVERITY_MODIFIER_WITH_CANONICAL_STATE_NOT_A_STANDALONE_RULE`

## Recovery Evidence Separability

In the inspected PM rows, many healthy recovery controls still showed `recovery_state = NO_RECOVERY` on the first weakness date while `continuation_quality_status = PASS` and `downside_risk_status = PASS`. That means current `recovery_state` alone is not sufficient to protect healthy pullbacks.

The better protective evidence is the combination of:

- positive current campaign return
- continuation quality `PASS`
- downside risk `PASS`
- return to `HEALTHY_OR_RECOVERING` in later PM rows

`RECOVERY_EVIDENCE_SEPARABILITY = PARTIAL; recovery_state alone weak, recovery sequence and positive current return useful`

## Regime Severity Interaction

Candidate hit counts by first-row regime:

| Candidate / cohort | BULL | RANGE | RECOVERY | CORRECTION | BEAR |
| --- | ---: | ---: | ---: | ---: | ---: |
| nonhealthy+negative, A1 | 10/12 | 15/15 | 13/13 | 4/4 | 10/13 |
| nonhealthy+negative, A2 | 2/17 | 2/7 | 1/6 | 0/3 | 1/7 |
| nonhealthy+negative, C | 1/9 | 1/6 | 1/4 | n/a | 0/3 |
| 2-consecutive nonhealthy+negative, A1 | 3/12 | 5/15 | 6/13 | 2/4 | 6/13 |
| 2-consecutive nonhealthy+negative, A2 | 0/17 | 0/7 | 0/6 | 0/3 | 0/7 |
| 2-consecutive nonhealthy+negative, C | 0/9 | 0/6 | 0/4 | n/a | 0/3 |

Adverse regime improves long-winner protection but is not enough alone. RECOVERY context does not eliminate A1 detection, so regime should modulate severity/persistence confirmation, not replace position evidence.

`REGIME_SEVERITY_INTERACTION_TABLE = adverse regime helps collateral control; RECOVERY requires caution but does not invalidate negative-return deterioration`

## PM Action Severity Alignment

| Family | Observed current PM behavior | Alignment |
| --- | --- | --- |
| A1 2-5BD losers | REDUCE/EXIT generally occurred quickly; 57/57 ultimately escalated. | Evidence/action present; loss remains due short failure, one-lot/minimum-notional, or unavoidable stop economics. |
| Healthy recovery controls | PM often REDUCEd but did not always full-exit immediately; many campaigns recovered or stayed profitable. | Preserving optionality appears valuable. |
| Winner giveback | REDUCE/EXIT evidence existed, but large giveback remained in some winners. | Severity/persistence calibration incomplete. |
| Repeated REDUCE chains | 21 campaigns, net +123,100. Several loser chains had persistent negative return, but many winner chains benefited from optionality. | Do not collapse all repeated REDUCEs to EXIT. |

`PM_ACTION_SEVERITY_ALIGNMENT_TABLE = current PM is directionally responsive; next design should refine severity/persistence, not replace SELL semantics`

## Repeated Reduce Chain Analysis

Repeated REDUCE chains: 21 campaigns, net +123,100.

Worst repeated REDUCE chains:

| Symbol | PnL | REDUCE count | Return pattern | Exit |
| --- | ---: | ---: | --- | --- |
| 69930 | -1,800 | 2 | -4.55%, -7.58% | 2022-10-28 |
| 33580 | -1,400 | 2 | -6.93%, -5.60% | 2022-10-19 |
| 65500 | -900 | 3 | -7.25%, -7.73%, -4.35% | 2022-10-25 |
| 87890 | -600 | 4 | -3.85%, -1.92%, -1.92%, -1.92% | 2022-11-28 |

Best repeated REDUCE chains:

| Symbol | PnL | REDUCE count | Return pattern | Exit |
| --- | ---: | ---: | --- | --- |
| 62490 | +43,200 | 3 | +16.16%, +23.82%, +33.42% | 2022-12-12 |
| 69730 | +28,500 | 3 | +5.73%, +12.67%, +16.20% | 2022-12-05 |
| 27670 | +17,800 | 2 | +3.18%, +16.11% | 2022-10-04 |
| 27880 | +10,400 | 2 | +14.39%, +25.54% | 2022-09-09 |
| 97310 | +10,200 | 2 | +0.12%, +12.75% | 2022-12-20 |

Repeated REDUCEs are not inherently bad. Negative-return repeated chains are the more plausible EXIT escalation candidates.

`REPEATED_REDUCE_CHAIN_ANALYSIS = repeated REDUCE preserves optionality in winners; negative-return persistence is the safer escalation signal`

## Long Winner Protection

| Candidate | 11BD+ winner exposure | Long-winner profit exposed | Gate read |
| --- | ---: | ---: | --- |
| non-healthy state only | 8/22 | 52,400 | FAIL |
| non-healthy + negative current return | 3/22 | 1,600 | PASS_CONDITIONAL |
| non-healthy + negative return + adverse regime | 0/22 | 0 | PASS |
| 2 consecutive non-healthy + negative return | 0/22 | 0 | PASS |
| 2 consecutive non-healthy | 1/22 | 5,000 | PARTIAL |

`LONG_WINNER_PROTECTION_TABLE = state-only fails; negative-return and persistence variants materially protect long winners`

## Candidate Ranking

| Rank | Candidate | Evidence strength | Avoided loss potential | Winner damage | Gate |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | non-healthy + negative current return, with PM severity not automatic full exit | Strongest diagnostic value and broad detection | 186,410 all-loss hit | 8,710 full-exit diagnostic | PASS_CONDITIONAL |
| 2 | 2 consecutive non-healthy + negative current return | Strong winner preservation | 77,070 all-loss hit | 0 | PASS |
| 3 | non-healthy + negative current return + adverse regime context | Good long-winner protection and simple architecture | 141,040 all-loss hit | 5,700 | PASS_CONDITIONAL |

`PM_SEVERITY_CANDIDATE_RANKING = 1. nonhealthy+negative-return severity; 2. 2-day persistence of nonhealthy+negative-return; 3. adverse-regime severity modifier`

## Winner Preservation Gate

| Candidate | Gate | Reason |
| --- | --- | --- |
| non-healthy state only | FAIL | Hits all A2 short winners and 8/22 long winners. |
| non-healthy + negative current return | PASS_CONDITIONAL | Big collateral reduction; still hits 9 completed winners overall. |
| non-healthy + negative return + adverse regime | PASS_CONDITIONAL | Lower collateral; misses more losses. |
| 2 consecutive non-healthy + negative return | PASS | No A2/C or all-winner full-exit damage observed; smaller sample/loss coverage. |
| worsening to PERSISTENT/EXIT | FAIL | Hits all A2 short winners. |

`WINNER_PRESERVATION_GATE_TABLE = state-only FAIL; negative-return variants PASS/PASS_CONDITIONAL`

## Existing Feature Sufficiency

Existing fields are partially sufficient:

- canonical state identifies weakening/deterioration
- current campaign return supplies a strong severity modifier
- persistence over consecutive PM rows substantially improves winner preservation
- regime can reduce collateral but is not enough alone
- recovery evidence is partial and should be sequence-based rather than same-day `recovery_state` only

`EXISTING_FEATURES_SUFFICIENCY = EXISTING_FEATURES_PARTIALLY_SUFFICIENT`

`NEW_FEATURE_REQUIRED_NOW = NO`

## No-Hindsight Proof

Recommended G3 design may use only production-eligible PIT fields:

- `canonical_sell_state`
- `current_campaign_relative_return`
- `observed_giveback` observed to date
- `continuation_quality_status`
- `downside_risk_status`
- `pm_deterioration_reasons`
- `recovery_state`
- PM action history up to the current date
- same-day `regime_state`
- same-day technical features

It must not use:

- future MFE
- final campaign PnL
- future returns
- eventual winner/loser label
- future regime
- optimal duration
- 100BD-derived threshold

Future outcomes were used only for diagnostic cohort/economic accounting.

`NO_HINDSIGHT_DESIGN_PROOF = PASS`

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G2_READY_FOR_PM_SEVERITY_DESIGN_EXISTING_PIT_FEATURES_PARTIALLY_SUFFICIENT`

`TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260821T095536206137Z`

`PERSISTENCE_EVIDENCE_AVAILABLE = YES`

`CANONICAL_STATE_SEQUENCE_TABLE = see table; losers tend E/W>P/W>E with negative returns; long winners often H or W>H recovery`

`HEALTHY_RECOVERY_CONTROL_CASES = 37 cases / +244,090 final profit`

`FAILED_PERSISTENCE_CASES = A1 examples include 21950, 21380, 65790, 44220, 96100, 92420, 37790`

`SEVERITY_PERSISTENCE_SEPARABILITY_TABLE = best broad: nonhealthy+negative return; safest: 2-consecutive nonhealthy+negative return`

`HOLD_REGRET_YEN = 8,710 for nonhealthy+negative return; 0 for 2-consecutive nonhealthy+negative return`

`FULL_EXIT_HOLD_REGRET_YEN = 8,710 / 0 for the same candidates`

`REDUCE_HOLD_REGRET_YEN = PARTIAL_UNRESOLVED`

`FALSE_EXIT_DAMAGE_YEN = 8,710 for nonhealthy+negative return; 0 for 2-consecutive nonhealthy+negative return`

`MISSED_EARLY_EXIT_DAMAGE_YEN = 19,490 for nonhealthy+negative return; 128,830 for 2-consecutive nonhealthy+negative return`

`TOTAL_WINNER_GIVEBACK_YEN = 199,240`

`WINNER_GIVEBACK_SEVERITY_DECOMPOSITION = POSSIBLE_PROFIT_PROTECTION 151,790; HIGH_COLLATERAL_RISK 47,450; STRONG 0; UNRESOLVED 0`

`NEGATIVE_CAMPAIGN_RETURN_INTERPRETATION = useful severity modifier with canonical state, not standalone rule`

`RECOVERY_EVIDENCE_SEPARABILITY = PARTIAL; sequence recovery and positive return useful, same-day recovery_state alone weak`

`REGIME_SEVERITY_INTERACTION_TABLE = adverse regime improves collateral control; not standalone`

`PM_ACTION_SEVERITY_ALIGNMENT_TABLE = PM responsive; severity/persistence calibration incomplete`

`REPEATED_REDUCE_CHAIN_ANALYSIS = 21 chains, net +123,100; winner chains show optionality value; negative-return chains are escalation candidates`

`LONG_WINNER_PROTECTION_TABLE = state-only FAIL; negative-return and persistence variants protect long winners`

`PM_SEVERITY_CANDIDATE_RANKING = 1. nonhealthy+negative-return severity; 2. 2-consecutive nonhealthy+negative-return persistence; 3. adverse-regime severity modifier`

`WINNER_PRESERVATION_GATE_TABLE = state-only FAIL; negative-return variants PASS/PASS_CONDITIONAL`

`NET_DIAGNOSTIC_PM_VALUE_YEN = +177,700 for nonhealthy+negative return full-exit diagnostic; +77,070 for 2-consecutive nonhealthy+negative return full-exit diagnostic; NOT expected PnL`

`EXISTING_FEATURES_SUFFICIENCY = EXISTING_FEATURES_PARTIALLY_SUFFICIENT`

`NEW_FEATURE_REQUIRED_NOW = NO`

`NO_HINDSIGHT_DESIGN_PROOF = PASS`

`PRODUCTION_PARAMETER_CHANGE_AUTHORIZED = NO`

`STRATEGY_MUTATION_AUTHORIZED = NO`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`NEXT_STEP_GATE = READY_FOR_PM_SEVERITY_DESIGN`

`NEXT_TASK_RECOMMENDATION = Phase31-G3 design a PIT-safe PM severity/persistence contract using canonical_sell_state + current_campaign_relative_return + persistence + regime context, with explicit winner-preservation gates and no threshold tuning`

