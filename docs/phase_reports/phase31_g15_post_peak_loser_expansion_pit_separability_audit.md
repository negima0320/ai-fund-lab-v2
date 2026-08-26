# Phase31-G15 — Post-Peak Loser Expansion Root Cause / PIT Separability Audit

## Scope

Task type: READ-ONLY ROOT-CAUSE + PIT SEPARABILITY AUDIT.

Target run:

- `runtime-test-historical-extended-smoke-20260822T174358377089Z`

Audit snapshot:

- run status at first read: `RUNNING`
- fixed latest completed date used for this report: `2023-06-13`
- PRE window: `2022-10-03 -> 2023-03-23`, 116 business days
- POST window: `2023-03-24 -> 2023-06-13`, 55 business days

No implementation, Strategy/PM/BUY/SELL change, threshold tuning, config change, fresh-run, resume, replay, or Historical rerun was performed.

## Evidence Sources

Primary evidence:

- `docs/phase_reports/phase31_g14_post_peak_performance_deceleration_root_cause_audit.md`
- `docs/phase_reports/phase31_g13_2023_05_19_extreme_daily_loss_valuation_integrity_audit.md`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z/run_state.json`
- `daily/<date>/current_valuation_refresh/valuation_projection.json`
- `daily/<date>/execution/fills.json`
- `daily/<date>/execution/realized_slices.json`
- `daily/<date>/strategy/market_context.json`
- `daily/<date>/strategy/buy_quality_decisions.json`
- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/position_management.json`
- `daily/<date>/sell_planning/position_management_evidence.json`
- `daily/2023-06-13/positions/position_campaigns.json`

Post-hoc realized outcome is used only for audit cohort construction and diagnostic accounting. It is not used as a proposed production input or threshold.

## G15-1 Input Evidence Availability Drift

All audited primary artifacts were present for every PRE and POST business day.

| Evidence area | PRE | POST | Drift assessment |
|---|---:|---:|---|
| Market Context artifacts present | 116/116 | 55/55 | NO |
| BUY quality artifacts present | 116/116 | 55/55 | NO |
| Runtime planning artifacts present | 116/116 | 55/55 | NO |
| Portfolio construction artifacts present | 116/116 | 55/55 | NO |
| Strategy PM artifacts present | 116/116 | 55/55 | NO |
| SELL PM evidence artifacts present | 116/116 | 55/55 | NO |
| Data Readiness artifacts present | 116/116 | 55/55 | NO |
| Corporate-event artifacts present | 116/116 | 55/55 | NO |

Coverage and availability:

| Metric | PRE | POST |
|---|---:|---:|
| BUY quality `missing_evidence_count` | 0 | 0 |
| SELL PM `pm_missing_fields + pm_missing_symbols` | 0 | 0 |
| Runtime planning non-RESOLVED artifacts | 10/116 | 8/55 |
| SELL PM non-PASS artifacts | 1/116 | 0/55 |
| Market Context coverage mean | 0.7687 | 0.7698 |
| Market Context coverage min | 0.7000 | 0.7000 |
| Active stale-status occurrences | 44 | 0 |

Active fallback-true occurrences were lower POST than PRE on a per-day basis. These counts include internal resolver evidence, not production threshold proposals:

| Area | PRE count | POST count |
|---|---:|---:|
| Runtime planning | 174 | 73 |
| Portfolio construction | 2,417 | 290 |
| Data Readiness | 1,038 | 368 |

Interpretation:

- No J-Quants/Market Context coverage collapse is visible.
- No BUY quality missing-evidence drift is visible.
- No SELL PM missing-symbol or missing-field drift is visible.
- Runtime planning unresolved-artifact rate is modestly higher POST, but this does not align with the loser expansion mechanism, and no downstream evidence shows it created the large POST losers.

`INPUT_EVIDENCE_AVAILABILITY_DRIFT = PARTIAL`

`JQUANTS_SOURCE_COVERAGE_DRIFT = NO`

`MARKET_CONTEXT_INPUT_COVERAGE_DRIFT = NO`

`CANDIDATE_INPUT_COVERAGE_DRIFT = NO`

`PM_INPUT_COVERAGE_DRIFT = NO`

`SELL_INPUT_COVERAGE_DRIFT = NO`

`MISSING_EVIDENCE_RATE_PRE = 0.00%`

`MISSING_EVIDENCE_RATE_POST = 0.00%`

`UNRESOLVED_EVIDENCE_RATE_PRE = 10/116 runtime_planning artifacts = 8.62%`

`UNRESOLVED_EVIDENCE_RATE_POST = 8/55 runtime_planning artifacts = 14.55%`

`STALE_EVIDENCE_RATE_PRE = active stale-status occurrences present, not POST-increased`

`STALE_EVIDENCE_RATE_POST = 0 active stale-status occurrences`

`FALLBACK_USAGE_PRE = 3,629 active fallback-true occurrences across audited artifacts`

`FALLBACK_USAGE_POST = 731 active fallback-true occurrences across audited artifacts`

`DATA_AVAILABILITY_CHANGE_CAN_EXPLAIN_DECELERATION = NO`

`FIRST_DRIFT_DATE = NOT_APPLICABLE`

## G15-2 POST Loser Cohort

Canonical POST closed-loser campaigns:

- count: `48`
- gross realized loss: `-350,130`
- average loser: `-7,294`

Holding-duration buckets:

| Holding bucket | Count | Gross loss | Avg loss | Median loss | Worst loss | Share of POST gross loss | Avg entry rank | Avg BUY quality | Avg entry exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1BD | 13 | -109,380 | -8,414 | -1,300 | -44,500 | 31.24% | 34.08 | 0.556 | 60.97% |
| 2-5BD | 27 | -159,050 | -5,891 | -2,600 | -45,500 | 45.43% | 28.52 | 0.597 | 64.15% |
| 6-10BD | 8 | -81,700 | -10,213 | -2,250 | -38,900 | 23.33% | 25.13 | 0.620 | 50.02% |

No same-day loser bucket was observed in the closed-loser cohort.

The dominant gross-loss bucket is `2-5BD`, but the mechanism is broader short-horizon failure: `1BD + 2-5BD = 76.67%` of POST gross loss.

`POST_LOSER_EXPANSION_DOMINANT_HOLD_BUCKET = 2-5BD`

## G15-3 / G15-4 Loss Path and Failure Class

Largest POST realized losers:

| Symbol | Open | Close | Bucket | PnL | Entry regime | Entry rank | Entry quality | Entry edge | Entry exposure | First actionable PM evidence |
|---|---|---|---|---:|---|---:|---:|---:|---:|---|
| 60220 | 2023-04-11 | 2023-04-13 | 2-5BD | -45,500 | CORRECTION | 21 | 0.608 | -0.352 | 65.95% | 2023-04-12 REDUCE / WEAKENING_BUT_INTACT / DEFENSIVE |
| 78780 | 2023-03-29 | 2023-03-30 | 1BD | -44,500 | RECOVERY | 23 | 0.631 | -0.382 | 79.26% | 2023-03-30 EXIT / EXIT_GRADE |
| 30410 | 2023-05-25 | 2023-06-02 | 6-10BD | -38,900 | RANGE | 2 | 0.797 | +0.374 | 63.69% | 2023-06-02 EXIT / EXIT_GRADE |
| 41660 | 2023-04-11 | 2023-04-12 | 1BD | -38,400 | CORRECTION | 25 | 0.601 | -0.384 | 65.95% | 2023-04-12 EXIT / EXIT_GRADE |
| 62310 | 2023-04-28 | 2023-05-15 | 6-10BD | -32,700 | RECOVERY | 33 | 0.557 | -0.430 | 70.35% | 2023-05-01 REDUCE / WEAKENING_BUT_INTACT / CAUTION |

Non-exclusive failure class gross-loss contribution:

| Class | Campaign count | Gross loss |
|---|---:|---:|
| PRE_EXISTING_WEAK_ENTRY | 46 | -311,030 |
| EARLY_FAILURE | 40 | -268,430 |
| PERSISTENT_DOWNTREND | 31 | -179,550 |
| WINNER_TO_LOSER_GIVEBACK | 8 | -54,900 |
| OTHER | 1 | -38,900 |

`PRIMARY_POST_LOSER_FAILURE_CLASS = EARLY_FAILURE_WITH_PRE_EXISTING_WEAK_ENTRY_EVIDENCE`

Most POST losers already had weak or negative expected-edge evidence at entry, but this field is not sufficient by itself because many POST winners had similar weak entry evidence.

## G15-5 False Recovery / Re-Risk Failure Cohort

Evidence-defined failure episodes:

| Episode | Re-risk / recovery evidence | Loss evidence |
|---|---|---|
| 2023-03-31 rebound failed | 2023-03-31 equity rebound to 1,246,230 after 2023-03-30 trough | 41660 -38,400 and 60220 -45,500 in the following sequence |
| 2023-05-10 re-risk failed | 2023-05-10 BULL, exposure 68.53%, then 2023-05-12 exposure 95.29% | 62310 -32,700 and 44380 -14,900 |
| 2023-05-30 re-risk failed | 2023-05-30 BULL, exposure 66.82% after recovery | 30410 -38,900 by 2023-06-02 |
| 2023-05-18 / 2023-05-19 shock sequence | 2023-05-18 BULL exposure 49.04%, then 2023-05-19 RECOVERY shock | G13: 67310 mark-to-market shock; realized-loss cohort effect counted separately |

`FALSE_RECOVERY_FAILURE_EPISODE_COUNT = 4`

`FALSE_RECOVERY_FAILURE_GROSS_LOSS = -170,400`

The gross-loss figure includes realized loser symbols tied to those episodes: 60220, 78780, 41660, 62310, 44380, and 30410. The 67310 2023-05-19 mark-to-market shock is valid daily-performance evidence per G13 but is not counted as a closed realized loser here.

## G15-6 Successful Re-Risk Control Cohort

Successful comparable controls were present, so PIT separability is not left unresolved for lack of controls.

Examples of successful controls:

| Symbol | Open | Close | PnL | Entry regime | Entry rank | Entry quality | Entry edge | Entry exposure |
|---|---|---:|---:|---|---:|---:|---:|---:|
| 49370 | 2023-05-08 | 2023-05-10 | +41,200 | BULL | 29 | 0.494 | -0.444 | 41.50% |
| 51360 | 2023-03-31 | 2023-04-05 | +10,000 | RECOVERY | 37 | 0.534 | -0.490 | 41.08% |
| 52460 | 2023-03-28 | 2023-03-30 | +9,900 | RANGE | 40 | 0.509 | -0.553 | 60.46% |
| 79970 | 2023-04-06 | 2023-04-10 | +6,600 | BEAR | 38 | 0.486 | -0.444 | 40.84% |
| 52470 | 2023-03-28 | 2023-03-31 | +6,500 | RANGE | 15 | 0.692 | -0.241 | 60.46% |

`SUCCESSFUL_RERISK_CONTROL_COUNT = 7`

## G15-7 Failure vs Success PIT Feature Comparison

Failure cohort used here: material false-recovery-linked losers. Success cohort: profitable POST re-risk controls.

| PIT feature | Failure distribution | Success distribution | Overlap | Directional separability |
|---|---|---|---|---|
| Entry rank | n=5, mean 21.8, median 25, min 2, max 33 | n=7, mean 30.9, median 34, min 15, max 40 | High | NONE |
| BUY quality | n=5, mean 0.633, median 0.601, min 0.557, max 0.797 | n=7, mean 0.571, median 0.553, min 0.486, max 0.692 | High | NONE |
| Expected edge | n=5, mean -0.251, median -0.384, min -0.464, max +0.374 | n=7, mean -0.423, median -0.475, min -0.553, max -0.218 | High | WEAK |
| Entry exposure | n=5, mean 70.52%, median 65.95%, min 63.69%, max 86.64% | n=7, mean 54.06%, median 60.46%, min 40.84%, max 73.54% | Moderate | MODERATE |
| Entry regime | Failure concentrated in CORRECTION/RECOVERY/RANGE | Success includes RECOVERY/RANGE/BEAR/BULL | High | WEAK |

`BEST_EXISTING_PIT_DISCRIMINATORS = ENTRY_EXPOSURE_STATE, RECOVERY_OR_CORRECTION_CONTEXT, NON_POSITIVE_EXPECTED_EDGE_AS_SECONDARY_CONTEXT`

The best existing discriminator is not rank or quality. The failure cases often looked better than success controls by rank and quality. The only directional separation with useful signal is higher portfolio exposure around recovery/re-risk contexts.

## G15-8 Matched Loser / Winner Controls

POST loser vs POST winner distributions:

| Feature | POST losers | POST winners | Separability |
|---|---:|---:|---|
| Entry rank mean | 29.46 | 31.94 | Weak; losers looked slightly better |
| Entry rank median | 31.5 | 34 | Weak |
| BUY quality mean | 0.590 | 0.570 | Weak; losers looked slightly better |
| BUY quality median | 0.566 | 0.557 | Weak |
| Expected edge mean | -0.386 | -0.418 | Weak |
| Expected edge median | -0.430 | -0.445 | Weak |

`MATCHED_CONTROL_COVERAGE = PARTIAL`

`LOSER_WINNER_PIT_SEPARABILITY = WEAK`

The observed loser/winner overlap is substantial. Rejecting by single PIT fields would remove many winners.

## G15-9 Hold-Regret / Winner Destruction Test

Diagnostic-only accounting for possible existing discriminators:

| Diagnostic discriminator | Loser loss captured | Winner profit at risk | Net diagnostic value | Interpretation |
|---|---:|---:|---:|---|
| Non-positive expected edge | 311,030 | 237,270 | +73,760 | Many winners also affected |
| Rank > 20 | 292,130 | 190,740 | +101,390 | Losers and winners heavily overlap |
| RECOVERY/CORRECTION entry | 203,650 | 82,440 | +121,210 | More useful, but incomplete |
| Entry exposure >= 60% | 295,350 | 129,640 | +165,710 | Best diagnostic balance in this audit |
| BUY quality < 0.60 | 133,430 | 167,400 | -33,970 | Reject as discriminator |

These are diagnostic bins observed in the audit, not proposed production thresholds.

`WINNER_CAMPAIGNS_AFFECTED = 17 for the best diagnostic exposure bin`

`WINNER_GROSS_PROFIT_AT_RISK = 129,640`

`LOSER_GROSS_LOSS_POTENTIALLY_AVOIDABLE = 295,350`

`NET_DIAGNOSTIC_VALUE = +165,710`

## G15-10 PM Severity / G8 Effectiveness

Large POST losers inspected: 9 campaigns with realized PnL <= `-10,000`.

| Metric | Count |
|---|---:|
| Large losers inspected | 9 |
| Actionable PM evidence before exit | 5 |
| First actionable evidence on exit day or too late | 4 |
| REDUCE before exit | 5 |
| EXIT-grade first evidence | 4 |

Examples:

- 60220: DEFENSIVE / REDUCE appeared on 2023-04-12, one business day before 2023-04-13 exit, after the campaign was already `-7.83%`.
- 78780: first actionable evidence was EXIT_GRADE on 2023-03-30, the exit day, after `-19.59%`.
- 41660: first actionable evidence was EXIT_GRADE on 2023-04-12, the exit day, after `-18.22%`.
- 62310: CAUTION / REDUCE appeared early on 2023-05-01, but the campaign still realized `-32,700` on 2023-05-15.
- 30410: first actionable evidence was EXIT_GRADE on 2023-06-02, the exit day, after `-14.42%`.

`PM_SEVERITY_EARLY_WARNING_EFFECTIVE = PARTIAL`

`PM_SEVERITY_TOO_LATE_FOR_LARGE_LOSER = PARTIAL`

`G8_ACTION_MAPPING_MATERIAL_POST = PARTIAL`

G8-style severity evidence existed and sometimes arrived before final exit, but for the largest fast losers it was often too late to prevent most of the damage.

## G15-11 Shock vs Gradual Deterioration

Gross realized POST loser loss: `-350,130`.

Descriptive attribution:

| Category | Approx gross loss | Share | Notes |
|---|---:|---:|---|
| Overnight / sudden early shock | -109,380 | 31.24% | 1BD loser bucket; PM can rarely react before damage is visible |
| Multi-day gradual deterioration | -159,050 | 45.43% | 2-5BD bucket; partly actionable, but still short |
| Failed recovery / re-risk sequence | -170,400 | 48.67% | Non-exclusive with holding buckets |
| Longer 6-10BD deterioration | -81,700 | 23.33% | Includes 30410 and 62310 |

G13 67310 remains a valid mark-to-market shock in daily equity but is not counted in realized gross loser loss here because the subsequent 2023-05-22 exit reversed the mark-to-market loss through execution.

`UNAVOIDABLE_SHOCK_LOSS_SHARE = 31.24%`

`POTENTIALLY_ACTIONABLE_DERIORATION_LOSS_SHARE = 68.76%`

This is not a preventability claim. It only separates losses whose damage was visible immediately from losses with at least some PIT deterioration path.

## G15-12 Concentration and Position Sizing Interaction

Top five POST losers:

| Symbol | Loss | Peak quantity | ADD count | Entry exposure | Loss mechanism |
|---|---:|---:|---:|---:|---|
| 60220 | -45,500 | 100 | 0 | 65.95% | 2-5BD early deterioration |
| 78780 | -44,500 | 100 | 0 | 79.26% | 1BD shock / fast failure |
| 30410 | -38,900 | 200 | 1 | 63.69% | ADD amplified 6-10BD deterioration |
| 41660 | -38,400 | 100 | 0 | 65.95% | 1BD shock / fast failure |
| 62310 | -32,700 | 100 | 0 | 70.35% | 6-10BD deterioration after early CAUTION |

`POSITION_SIZE_AMPLIFIED_LOSER_SEVERITY = PARTIAL`

`BAD_ADD_CONTRIBUTION = PARTIAL`

Position sizing did not explain most top losers because four of the top five peaked at 100 shares with no ADD. It did materially amplify 30410, which had peak quantity 200 and one ADD.

## G15-13 Opportunity Scarcity Interaction

G14 established:

- BUY plans/day fell from `3.83` to about `2.08`
- mean rank worsened from `25.95` to `29.28`
- mean BUY quality declined from `0.608` to `0.589`
- available incremental budget increased

G15 adds that many POST losers and winners both came from weak expected-edge/rank regions:

- POST loser expected-edge mean: `-0.386`
- POST winner expected-edge mean: `-0.418`
- POST loser rank mean: `29.46`
- POST winner rank mean: `31.94`

`OPPORTUNITY_SCARCITY_CHANGED_BEHAVIOR = PARTIAL`

`WEAKER_OPPORTUNITY_ACCEPTANCE_SUPPORTED = PARTIAL`

Scarcity appears to have made the system operate in weaker opportunity territory, but weak opportunity evidence alone cannot separate losers from winners.

## G15-14 Change-Point Timing

Rolling realized-campaign diagnostics:

- first rolling PF below 1 after 2023-01-01: `2023-02-13`
- first rolling average loser below about `-7,000`: `2023-03-06`
- large loss frequency became visible before the 2023-03-23 equity peak through the 2023-03-06 and 2023-03-13 loss events
- false-recovery/re-risk sequences became prominent after the peak, especially from late March through early June

`EARLIEST_BEHAVIORAL_CHANGE_DATE_RANGE = 2023-02-13 -> 2023-03-06`

`CHANGE_POINT_PRECEDES_EQUITY_PEAK = YES`

The equity peak is the visible split point, not the first causal degradation point.

## G15-15 Root Cause Hierarchy

| Cause | Rank | Evidence |
|---|---|---|
| DATA_EVIDENCE_DRIFT | NOT_SUPPORTED | all primary artifacts present; missing evidence rate 0; Market Context coverage stable |
| MARKET_SHOCK | SECONDARY | 1BD losses and G13 67310 show real fast shocks |
| FALSE_RECOVERY_RERISK | PRIMARY | 4 episodes, `-170,400` realized loss tied to failure cohort |
| LOSER_CONTAINMENT_DELAY | PRIMARY | PM evidence often arrived after large early damage or did not stop loss expansion |
| ENTRY_QUALITY | CONTRIBUTORY | weak entry evidence common, but not separable from winners |
| WINNER_GIVEBACK | CONTRIBUTORY | 8 loser campaigns, `-54,900`; retention worsened but not dominant |
| OPPORTUNITY_SCARCITY | CONTRIBUTORY | lower BUY plans/day, weaker opportunity region, higher cash |
| POSITION_CONCENTRATION | CONTRIBUTORY | top-five concentration high; sizing/ADD mattered for 30410 only |
| OTHER | UNRESOLVED | single campaign 30410 had strong PIT entry rank/quality yet became a large loser |

## G15-16 Repairability / Separability Judgment

`REPAIRABILITY_JUDGMENT = FAILURE_MODE_PARTIALLY_PIT_SEPARABLE_MORE_EVIDENCE_REQUIRED`

Rationale:

- Failure cases are not strongly separable using rank, BUY quality, or expected edge alone.
- Higher entry exposure and recovery/correction context provide the best weak-to-moderate PIT signal.
- The winner destruction test shows meaningful winner profit at risk for every simple discriminator.
- A production rule should not be selected from this window.

## Required Summary

`PRIMARY_JUDGMENT = POST_PEAK_LOSER_EXPANSION_PARTIALLY_PIT_SEPARABLE_FALSE_RECOVERY_AND_LOSER_CONTAINMENT_DELAY`

`TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260822T174358377089Z`

`LATEST_COMPLETED_DATE = 2023-06-13`

`INPUT_EVIDENCE_AVAILABILITY_DRIFT = PARTIAL`

`DATA_AVAILABILITY_CHANGE_CAN_EXPLAIN_DECELERATION = NO`

`POST_LOSER_EXPANSION_DOMINANT_HOLD_BUCKET = 2-5BD`

`PRIMARY_POST_LOSER_FAILURE_CLASS = EARLY_FAILURE_WITH_PRE_EXISTING_WEAK_ENTRY_EVIDENCE`

`FALSE_RECOVERY_FAILURE_EPISODE_COUNT = 4`

`FALSE_RECOVERY_FAILURE_GROSS_LOSS = -170,400`

`SUCCESSFUL_RERISK_CONTROL_COUNT = 7`

`LOSER_WINNER_PIT_SEPARABILITY = WEAK`

`BEST_EXISTING_PIT_DISCRIMINATORS = ENTRY_EXPOSURE_STATE, RECOVERY_OR_CORRECTION_CONTEXT, NON_POSITIVE_EXPECTED_EDGE_AS_SECONDARY_CONTEXT`

`WINNER_GROSS_PROFIT_AT_RISK = 129,640`

`LOSER_GROSS_LOSS_POTENTIALLY_AVOIDABLE = 295,350`

`PM_SEVERITY_EARLY_WARNING_EFFECTIVE = PARTIAL`

`PM_SEVERITY_TOO_LATE_FOR_LARGE_LOSER = PARTIAL`

`G8_ACTION_MAPPING_MATERIAL_POST = PARTIAL`

`UNAVOIDABLE_SHOCK_LOSS_SHARE = 31.24%`

`POTENTIALLY_ACTIONABLE_DERIORATION_LOSS_SHARE = 68.76%`

`POSITION_SIZE_AMPLIFIED_LOSER_SEVERITY = PARTIAL`

`BAD_ADD_CONTRIBUTION = PARTIAL`

`OPPORTUNITY_SCARCITY_CHANGED_BEHAVIOR = PARTIAL`

`WEAKER_OPPORTUNITY_ACCEPTANCE_SUPPORTED = PARTIAL`

`EARLIEST_BEHAVIORAL_CHANGE_DATE_RANGE = 2023-02-13 -> 2023-03-06`

`CHANGE_POINT_PRECEDES_EQUITY_PEAK = YES`

`ROOT_CAUSE_HIERARCHY = FALSE_RECOVERY_RERISK: PRIMARY; LOSER_CONTAINMENT_DELAY: PRIMARY; MARKET_SHOCK: SECONDARY; ENTRY_QUALITY: CONTRIBUTORY; WINNER_GIVEBACK: CONTRIBUTORY; OPPORTUNITY_SCARCITY: CONTRIBUTORY; POSITION_CONCENTRATION: CONTRIBUTORY; DATA_EVIDENCE_DRIFT: NOT_SUPPORTED; OTHER: UNRESOLVED`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`HISTORICAL_OUTCOME_USED_TO_SELECT_PRODUCTION_THRESHOLD = NO`

`NEW_FEATURE_CREATED = NO`

`NEW_THRESHOLD_SELECTED = NO`

`PERFORMANCE_TUNING_RECOMMENDED = NO`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = design a PIT-safe research validation for exposure/regime-aware loser containment without choosing production thresholds`
