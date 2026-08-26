# Phase31-G100 - G99 Lot-Compatible Reconsideration Actual PS / Runtime Propagation Audit

## PRIMARY_JUDGMENT

`G99_ACTUAL_PROPAGATION_DEFECT_CONFIRMED_REPAIR_REQUIRED`

G99 lot-context repair is active in the actual fresh-run and propagates G97 rows through:

```text
PC G97 authoritative positive
-> G61 LOT_EXECUTABLE_COMPATIBLE
-> Position Sizing positive quantity
-> Runtime BUY plan
```

However, G97-derived Runtime BUYs do not reach submitted orders/fills/holdings. The confirmed first post-Runtime stopping boundary is Submit item-scoped BUY feasibility:

```text
pc_discrete_quantity_authority_not_pass
```

Primary classification:

`OTHER_CONFIRMED`

Specific confirmed cause:

`SUBMIT_DISCRETE_QUANTITY_AUTHORITY_GAP_AFTER_G99_RUNTIME_BUY`

## Target

Actual G99 fresh-run:

`runtime-test-historical-extended-smoke-20260824T203644021876Z`

Baseline:

`runtime-test-historical-extended-smoke-20260824T055234719725Z`

Run state at audit time:

```text
status = RUNNING
completed business dates = 118
completed range = 2022-10-03 through 2023-03-27
next_job = 2023-03-28:market_refresh
```

No code/config/threshold/weight changes were made. No fresh-run/resume/replay/Historical was executed by Codex.

## Primary Anchor: 2023-03-22 94320

Actual lineage:

```text
source competitor = NEW_BUY / COMPETITOR_REJECTED_RECONSIDERABLE
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION = YES
G95 shadow outcome = SHADOW_SECURITY_PARTICIPATION_VALID
G95 interaction_result = CASH_PREFERRED
G95 participation_deferral_resolution = CASH_PREFERRED_PARTICIPATION_VALID
G97 authoritative binding = YES
final canonical security allocation = YES
authorized_allocation_weight = 0.030303
lot_sizing_context propagated = YES
reference_price = 161.8
portfolio_value = 1,369,320
one_lot_weight = 0.011816
safety_hard_cap_weight = 0.25
G61 compatibility = LOT_EXECUTABLE_COMPATIBLE
G61 projected quantity = 200
PS selected row = YES
PS target_weight = 0.024382
PS current_quantity = 0
PS quantity_delta = 200
Runtime BUY_NEW plan = YES
Runtime planned_quantity = 200
Submit/fill = NO
Submit reason = pc_discrete_quantity_authority_not_pass
```

Required values:

```text
ACTUAL_20230322_94320_G97_POSITIVE = YES
ACTUAL_20230322_94320_G61_STATE = LOT_EXECUTABLE_COMPATIBLE
ACTUAL_20230322_94320_PS_TARGET_WEIGHT = 0.024382
ACTUAL_20230322_94320_PS_QUANTITY_DELTA = 200
ACTUAL_20230322_94320_RUNTIME_BUY = YES
ACTUAL_20230322_94320_FILL = NO
```

## Producer-Equivalent vs Actual

G99 producer-equivalent expected for 2023-03-22 / 94320:

```text
G97 positive = YES
G61 LOT_EXECUTABLE_COMPATIBLE = YES
theoretical quantity = 200
```

Actual fresh-run matches this through Runtime:

```text
G97 positive = YES
G61 LOT_EXECUTABLE_COMPATIBLE = YES
PS quantity_delta = 200
Runtime BUY_NEW = YES
```

The divergence is after Runtime Planning:

```text
PRODUCER_EQUIVALENT_ACTUAL_DIVERGENCE_BOUNDARY =
Runtime Planning -> Submit item-scoped BUY feasibility
```

This is not a G99 lot-context serialization gap.

## G61 Actual Consumer Surface

The final persisted PC artifact contains the G99 context on the exact row PS consumes:

```text
G99_LOT_CONTEXT_PRESENT_IN_ACTUAL_FINAL_PC_ARTIFACT = YES
G99_LOT_CONTEXT_PRESENT_ON_PS_CONSUMED_ROW = YES
```

For 2023-03-22 / 94320, the persisted `strategy/portfolio_construction.json` has:

```text
capital_competition.canonical_multi_allocation_deployment_set.security_allocations[4]
  residual_reconsideration_authoritative_binding = true
  lot_materialization_status = LOT_EXECUTABLE_COMPATIBLE
  lot_aware_allocation_to_sizing_compatibility.compatibility_state = LOT_EXECUTABLE_COMPATIBLE
  reference_price = 161.8
  portfolio_value = 1,369,320
  minimum_executable_weight = 0.011816
  projected_quantity_delta_evidence_only = 200
```

`strategy/position_sizing.json` preserves the upstream PC row and produces:

```text
lot_feasibility_preflight[94320].canonical_sizing_evidence.quantity_delta = 200
positions[94320].canonical_sizing_evidence.quantity_delta = 200
```

## PS Selection Audit

```text
PS_G97_ROW_SELECTION = PASS
```

PS identifies the G97 row via the canonical multi-allocation/G61 surface and emits a positive quantity. The row is not excluded by G97 provenance.

Observed for 2023-03-22 / 94320:

```text
PC authorized_allocation_weight = 0.030303
G61 projected_quantity_delta_evidence_only = 200
PS target_weight = 0.024382
PS quantity_delta = 200
```

The lower PS target weight is lot conversion output, not loss of G97 selection.

## Duplicate Symbol / Merge Audit

Across actual completed dates, no duplicate final security-allocation symbol row was found that affected G97-positive rows.

```text
DUPLICATE_SYMBOL_MERGE_AFFECTS_G97 = NO
```

## Additional Anchors

`2023-04-14 / 94320` was not completed in the actual target run at the time of audit, so it was skipped without waiting.

Earliest actual lot-executable G97 row:

```text
FIRST_ACTUAL_G99_LOT_EXECUTABLE_DATE = 2022-11-11
FIRST_ACTUAL_G99_LOT_EXECUTABLE_SYMBOL = 76470
```

## Completed-Date Population Funnel

Completed actual dates only:

```text
G97 positive = 39
final PC positive = 39
G61 LOT_EXECUTABLE_COMPATIBLE = 27
G61 LOT_INFEASIBLE_RESIDUAL_REQUIRED = 12
PS selected = 39
PS quantity_delta > 0 = 27
Runtime BUY_NEW/BUY_ADD = 26
Fill = 0
Holding effect = 0
```

One PS-positive row did not produce a Runtime BUY:

```text
2023-02-09 / 45940 / PS quantity_delta = 100
```

For Runtime-visible G97 BUY rows:

```text
Runtime G97 BUY rows = 26
Submit item_results with pc_discrete_quantity_authority_not_pass = 7
G97 fills = 0
```

Many Runtime-visible G97 rows do not appear as submitted item results; none materialize as fills.

## Baseline Comparison

Compared against baseline through overlapping completed target dates:

```text
FIRST_G99_ACTUAL_PC_DIVERGENCE_DATE = 2022-10-31
FIRST_G99_ACTUAL_G61_DIVERGENCE_DATE = 2022-10-31
FIRST_G99_ACTUAL_PS_DIVERGENCE_DATE = 2022-11-11
FIRST_G99_ACTUAL_RUNTIME_DIVERGENCE_DATE = 2022-11-11
FIRST_G99_ACTUAL_HOLDING_DIVERGENCE_DATE = NONE
```

This matches the funnel: G99 changes actual PC/G61/PS/Runtime surfaces, but no G97-derived holding effect exists yet.

## G99 Activation Judgments

```text
G99_CODE_ACTIVE_IN_FRESH_RUN = YES
G99_LOT_CONTEXT_ACTUAL_PROPAGATION = PASS
G61_ACTUAL_COMPATIBILITY_PROPAGATION = PASS
PS_ACTUAL_CONSUMPTION = PASS
RUNTIME_ACTUAL_CONSUMPTION = PARTIAL
```

Runtime consumption is `PARTIAL` because 26 of 27 PS-positive G97 rows became Runtime BUY plans, with one observed PS-positive/no-Runtime case.

## Root Cause Classification

Required primary classification:

`OTHER_CONFIRMED`

Explanation:

The confirmed gap is not producer-equivalent vs actual PC, not lot-context serialization, not G61-to-PS, not duplicate merge, and not PS-to-Runtime for the primary anchor. The first complete-anchor failure occurs after Runtime Planning at Submit item-scoped BUY feasibility:

```text
pc_discrete_quantity_authority_not_pass
```

This suggests the next repair boundary is Submit's consumption of PS/G61-derived quantity authority for G97 reconsideration rows, not the G99 lot-context propagation boundary.

## Required Final Judgment

```text
G99_ACTUAL_PROPAGATION_CONFIRMED = PARTIAL
G99_ACTUAL_PROPAGATION_DEFECT_CONFIRMED = YES
REPAIR_REQUIRED = YES
FINAL_DECISION = G99_ACTUAL_PROPAGATION_DEFECT_CONFIRMED_REPAIR_REQUIRED
```

## Safety

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
THRESHOLD_WEIGHT_TUNING = NO
FRESH_RUN_EXECUTED_BY_CODEX = NO
RESUME_EXECUTED_BY_CODEX = NO
REPLAY_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
RUN_MUTATED_BY_CODEX = NO
FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_STRATEGY_INPUT_COUNT = 0
```

## Recommended Next Boundary

Audit and repair only the Submit item-scoped BUY feasibility / discrete quantity authority boundary for G99/G97 reconsideration-derived Runtime BUY rows.

Do not revisit G99 lot context, G90/G97 participation semantics, Market Quality, Risk Pacing, ranking, ADD semantics, Safety, PS quantity ownership, or Runtime priority unless new evidence contradicts this boundary.
