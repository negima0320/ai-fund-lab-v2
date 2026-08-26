# Phase31-G126 — Early Post-Entry Failure Decision Consumption Audit

## Judgment

FINAL_DECISION =
`G126_EARLY_FAILURE_CONSUMPTION_DESIGN_CONFORMANT_RETURN_TO_WINNER_SCALING_AUDIT`

PRIMARY_JUDGMENT:

Early post-entry failure evidence is being produced and consumed through the existing PM -> Runtime Planning -> Execution path for the audited population. The dominant +1BD PM `REDUCE` signal is not an executable sell authority for most one-lot / minimum-notional positions; Runtime correctly maps it to intentional `NO_ORDER` with `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT` or `REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL`. When PM reaches +2BD `EXIT`, Runtime and Execution materialize it for all 33 +2BD EXIT cases.

No mandatory downstream consumption defect was found in G126. The remaining material open track remains BUY_ADD / Winner Scaling.

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260825T135619843503Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T135619843503Z`
- Primary campaign authority: `daily/2023-09-04/positions/position_campaigns.json`
- PM evidence: `daily/<date>/strategy/position_management.json`
- Runtime evidence: `daily/<date>/strategy/runtime_planning.json`
- Execution evidence: `daily/<date>/execution/fills.json`
- Cohort definition: same as G125, using inclusive business-day duration from `opened_business_date` through `closed_business_date` or latest observed date.

READ_ONLY = YES  
CODE_CHANGED = NO  
RUN_MODIFIED = NO  
FRESH_RUN_EXECUTED = NO  
RESUME_EXECUTED = NO  
REPLAY_EXECUTED = NO  
LONG_HISTORICAL_EXECUTED = NO

## Cohort Reconstruction

| Cohort | Count |
| --- | ---: |
| EARLY_FAILURE | 60 |
| DURABLE_WINNER | 37 |
| SHORT_LIVED_WINNER | 40 |
| ORDINARY | 33 |
| Total March-August BUY_NEW campaigns | 170 |

EARLY_FAILURE_CAMPAIGNS_RECONSTRUCTED = `60/60`

DURABLE_WINNER_CONTROLS_RECONSTRUCTED = `37/37`

## PM State Transition Check

| Offset | Durable Winner PM states | Early Failure PM states |
| --- | --- | --- |
| +1BD | HELD_SUPPORTIVE 33; REDUCE 2; ADD 2 | REDUCE 33; HELD_SUPPORTIVE 27 |
| +2BD | HELD_SUPPORTIVE 33; ADD 2; REDUCE 2 | EXIT 33; HELD_SUPPORTIVE 16; REDUCE 11 |
| +3BD | HELD_SUPPORTIVE 30; ADD 3; REDUCE 4 | MISSING 33; REDUCE 11; EXIT 13; HELD_SUPPORTIVE 3 |
| +5BD | HELD_SUPPORTIVE 31; ADD 1; REDUCE 4; EXIT 1 | MISSING 60 |

This reproduces G125's key separation: early failures often emit PM `REDUCE` at +1BD and PM `EXIT` at +2BD, while durable winners are mostly held.

## +1BD REDUCE Consumption

PLUS1_PM_REDUCE_COUNT = `33`

PLUS1_RUNTIME_REDUCE_COUNT = `0`

PLUS1_EXECUTED_REDUCE_COUNT = `1`

PLUS1_REDUCE_AUTHORITY_LEAK_COUNT = `0`

Reason distribution for the 33 PM `REDUCE` cases:

| Runtime disposition | Count |
| --- | ---: |
| `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT` | 32 |
| `REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL` | 1 |

Interpretation:

PM did emit REDUCE, but canonical Runtime evidence explicitly classified the partial REDUCE as unexecutable. This is not a hidden downstream leak. It is the existing discrete-lot / minimum-notional REDUCE representability contract. The later +2BD EXIT path is the actionable liquidation path.

## +2BD EXIT Consumption

PLUS2_PM_EXIT_COUNT = `33`

PLUS2_RUNTIME_EXIT_COUNT = `33`

PLUS2_EXECUTED_EXIT_COUNT = `33`

PLUS2_EXIT_AUTHORITY_LEAK_COUNT = `0`

Note: only 8 fills preserve `source_decision_type = EXIT`; however all 33 have same-date SELL fills for the relevant symbol. Therefore the execution effect exists even when the observability field is `MISSING`.

## HELD_SUPPORTIVE Cases

EARLY_FAILURE_HELD_WITHOUT_DOWNSIDE_EVIDENCE = `43`

EARLY_FAILURE_HELD_DESPITE_CANONICAL_DOWNSIDE_EVIDENCE = `0`

Breakdown:

| Observation window | HELD_SUPPORTIVE count |
| --- | ---: |
| +1BD | 27 |
| +2BD | 16 |

The held early-failure cases were held under `HEALTHY_OR_RECOVERING` / supportive PM evidence, not despite canonical downside evidence. This argues against a PM consumer defect.

## Latency

For the 60 Early Failure campaigns:

| Boundary | Campaigns with evidence | Business-day latency distribution from BUY |
| --- | ---: | --- |
| First canonical downside evidence | 60 | +1: 33; +2: 12; +3: 12; +4: 3 |
| First PM REDUCE/EXIT | 60 | +1: 33; +2: 12; +3: 12; +4: 3 |
| First Runtime SELL | 59 | +2: 33; +3: 13; +4: 13 |
| First executed SELL | 59 | +1: 1; +2: 33; +3: 13; +4: 12 |

The one non-executed case is `2023-08-29 / 72560`, still OPEN at the latest artifact date `2023-09-04`. PM REDUCE appeared at the evidence horizon, Runtime mapped it to `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`, and no later business date is available in this run artifact. This is an evidence-horizon tail case, not a confirmed implementation defect.

## Post-Warning Loss

EARLY_FAILURE_POST_WARNING_LOSS_SHARE = `about 51.5% of normalized campaign relative loss occurred after the first downside/PM warning`

This is descriptive only. It is not used to select a production threshold.

The result is consistent with the REDUCE representability constraint: first warning often appears as REDUCE, but partial de-risking cannot be executed for one-lot/minimum-notional positions, so loss can still accumulate until EXIT-grade evidence.

## Durable Winner Control

DURABLE_WINNER_EARLY_REDUCE_COUNT = `11`

DURABLE_WINNER_EARLY_EXIT_COUNT = `1`

DURABLE_WINNER_RETENTION_AT_RISK = `PARTIAL`

Some durable winners also show early `WEAKENING_BUT_INTACT / REDUCE` evidence. Therefore an aggressive automatic escalation from early REDUCE to EXIT would create material winner-retention risk. Current design often lets these recover back to `HEALTHY_OR_RECOVERING`.

## Re-entry Interaction

EARLY_EXIT_REENTRY_DISTRIBUTION:

| Re-entry gap after observed early failure | Count |
| --- | ---: |
| same-day | 0 |
| next-day | 0 |
| 2-5BD | 1 |
| 6-10BD | 0 |
| 11BD+ | 0 |
| none in observed horizon | 59 |

No broad same-symbol churn / immediate re-entry pattern was found in this specific Early Failure population.

## Regime Interaction

Early Failure entry-regime distribution:

| Regime | Count |
| --- | ---: |
| BULL | 29 |
| RANGE | 12 |
| RECOVERY | 13 |
| BEAR | 1 |
| CORRECTION | 5 |

EARLY_FAILURE_CONSUMPTION_REGIME_DEPENDENT = `NO`

The evidence consumption path is not broken in a specific regime. Early failures occur across regimes, but PM/RUNTIME/Execution consumption of EXIT-grade evidence is intact.

## Monthly Pattern

| Entry month | Early failures | +1BD PM REDUCE | +2BD PM EXIT | Authority leak |
| --- | ---: | ---: | ---: | ---: |
| 2023-03 | 8 | 6 | 6 | 0 |
| 2023-04 | 12 | 8 | 8 | 0 |
| 2023-05 | 8 | 4 | 4 | 0 |
| 2023-06 | 11 | 8 | 9 | 0 |
| 2023-07 | 12 | 3 | 3 | 0 |
| 2023-08 | 9 | 4 | 3 | 0 confirmed; 1 evidence-horizon tail case |

POST_APRIL_EARLY_FAILURE_CONSUMPTION_SHIFT = `NO`

There is a shift in signal incidence, especially July/August having more held-supportive early losers, but there is no confirmed failure to consume canonical REDUCE/EXIT evidence.

## Existing Evidence Ignored Test

Classification of Early Failure campaigns:

| Class | Count |
| --- | ---: |
| PM REDUCE/EXIT consumed through Runtime/Execution | 59 |
| PM REDUCE at final evidence horizon, Runtime intentional no-order, no later evidence | 1 |
| Canonical downside evidence but PM failed to act | 0 |
| Runtime SELL plan not executed | 0 confirmed |

EARLY_FAILURE_PRIMARY_DECISION_BOUNDARY = `NO_DEFECT`

The primary boundary is not Strategy Intelligence, PM, or downstream execution. For confirmed evidence, the existing contracts are followed. The residual pain point is a known representability/economic limitation: early REDUCE can be non-executable for one-lot positions before EXIT evidence appears.

## SELL Philosophy Conformance

EARLY_FAILURE_SELL_PHILOSOPHY_CONFORMANCE = `PARTIAL`

Conformance evidence:

- The system does not require perfect entry.
- It allows post-entry confirmation.
- It cuts EXIT-grade failures promptly: +2BD PM EXIT -> Runtime SELL_EXIT -> SELL fill is 33/33.
- It preserves many durable winners despite transient REDUCE evidence.
- It does not impose a fixed holding period.
- Re-entry remains allowed.

Partial limitation:

- REDUCE-before-EXIT is semantically present but often physically unrepresentable for one-lot/minimum-notional positions, so early-warning loss can continue until EXIT.

This limitation is not a G126 mandatory repair because the current SoT preserves PM-owned REDUCE semantics and explicitly permits review/no-order when REDUCE is unrepresentable.

## Required Judgments

EARLY_FAILURE_CAMPAIGNS_RECONSTRUCTED = `60/60`

DURABLE_WINNER_CONTROLS_RECONSTRUCTED = `37/37`

PLUS1_REDUCE_AUTHORITY_LEAK_COUNT = `0`

PLUS2_EXIT_AUTHORITY_LEAK_COUNT = `0`

EARLY_FAILURE_HELD_WITHOUT_DOWNSIDE_EVIDENCE = `43`

EARLY_FAILURE_HELD_DESPITE_CANONICAL_DOWNSIDE_EVIDENCE = `0`

EARLY_FAILURE_PRIMARY_DECISION_BOUNDARY = `NO_DEFECT`

EARLY_FAILURE_POST_WARNING_LOSS_SHARE = `about 51.5% normalized relative-loss share after first warning`

DURABLE_WINNER_RETENTION_AT_RISK = `PARTIAL`

EARLY_FAILURE_CONSUMPTION_REGIME_DEPENDENT = `NO`

POST_APRIL_EARLY_FAILURE_CONSUMPTION_SHIFT = `NO`

EARLY_FAILURE_SELL_PHILOSOPHY_CONFORMANCE = `PARTIAL`

MANDATORY_REPAIR_FOUND = `NO`

BUY_ADD_WINNER_SCALING_ISSUE_CLOSED = `NO`

NEXT_BUY_ADD_AUDIT_REQUIRED = `YES`

FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = `NO`

PERFORMANCE_USED_TO_SELECT_PRODUCTION_PARAMETER = `NO`

## Next Task

Recommended exactly one next task:

`PHASE31_G127_BUY_ADD_WINNER_SCALING_ACTUAL_FUNNEL_RETURN_AUDIT`

Purpose: return to the unresolved BUY_ADD / Winner Scaling actual funnel, using the current post-G122/G115/G119 lineage and actual campaign evidence, without changing early-failure SELL semantics.
