# Phase31-G98 - G97 Authoritative Reconsideration Actual Propagation Audit

## PRIMARY_JUDGMENT

`G97_PROPAGATION_DEFECT_CONFIRMED_REPAIR_REQUIRED`

G97 authoritative residual reconsideration binding is present in the fresh-run actual Portfolio Construction artifacts and the positive rows are merged into the final `canonical_multi_allocation_deployment_set.security_allocations[]`.

However, every G97 positive row in the completed fresh-run is terminally zeroed before Position Sizing can produce quantity:

```text
G97 positive authoritative rows in completed run: 141
G97 rows entering final canonical security_allocations[]: 141
G97 rows with G61 state LOT_EXECUTABLE_COMPATIBLE: 0
G97 rows with G61 state INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED: 141
G97 rows with PS positive quantity: 0
G97 rows with Runtime positive BUY/ADD plan: 0
```

The behavior is therefore materially identical to the G90 baseline because G97 rows are added to PC evidence but carry no executable lot context into the G61 -> PS boundary.

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260824T121719329586Z`

Baseline run:

`runtime-test-historical-extended-smoke-20260824T055234719725Z`

Representative anchors inspected:

| Date | Symbol(s) |
|---|---|
| 2023-03-22 | 94320 |
| 2023-04-07 | 83060, 77760, 44440 |
| 2023-04-14 | 94320 |
| 2023-04-18 | 59350 |

No code/config/threshold/weight changes were made. No fresh-run/resume/replay/Historical was executed by Codex.

## Artifact Presence

For each representative date, the fresh-run emitted:

| Date | G95 shadow present | G97 authoritative binding evidence present | Positive authoritative rows | Final marked security rows |
|---|---:|---:|---:|---:|
| 2023-03-22 | YES | YES | 1 | 1 |
| 2023-04-07 | YES | YES | 3 | 3 |
| 2023-04-14 | YES | YES | 1 | 1 |
| 2023-04-18 | YES | YES | 5 | 5 |

The G97 authority is stored inside:

```text
strategy/portfolio_construction.json
  capital_competition
    canonical_multi_allocation_deployment_set
      residual_reconsideration_authoritative_binding_evidence
```

with:

```text
schema_version = canonical_residual_reconsideration_authoritative_binding.v1
```

This is not absent evidence. The defect is downstream of final PC merge.

## Row-Level Propagation

| Date | Symbol | PC G97 binding | Final canonical allocation | G61 compatibility | PS quantity delta | Runtime plan | Fill | Propagation status |
|---|---|---|---|---|---:|---:|---:|---|
| 2023-03-22 | 94320 | YES | YES | INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED | 0 | 0 | 0 | STOPPED_AT_LOT |
| 2023-04-07 | 83060 | YES | YES | INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED | 0 | 0 | 0 | STOPPED_AT_LOT |
| 2023-04-07 | 77760 | YES | YES | INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED | 0 | 0 | 0 | STOPPED_AT_LOT |
| 2023-04-07 | 44440 | YES | YES | INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED | 0 | 0 | 0 | STOPPED_AT_LOT |
| 2023-04-14 | 94320 | YES | YES | INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED | 0 | 0 | 0 | STOPPED_AT_LOT |
| 2023-04-18 | 59350 | YES | YES | INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED | 0 | 0 | 0 | STOPPED_AT_LOT |

In PS artifacts, each representative row appears as a zero target:

```text
target_weight = 0.0
canonical_sizing_evidence.quantity_delta = 0
phase29_l19_lot_resolution.requested_incremental_weight = 0.0
```

Runtime planning then carries only no-action lineage for the anchor symbols, not an executable BUY/ADD.

## Population Funnel

Completed dates inspected in target run: 214

```text
canonical_residual_reconsideration_shadow.v1 present: 213 dates
canonical_residual_reconsideration_authoritative_binding.v1 present: 213 dates
G97 positive authoritative rows: 141
Final canonical marked G97 rows: 141
G61 LOT_EXECUTABLE_COMPATIBLE marked G97 rows: 0
G61 INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED marked G97 rows: 141
PS nonzero marked G97 rows: 0
Runtime BUY/ADD marked G97 rows: 0
Holding-effect marked G97 rows: 0
```

Population funnel:

```text
RECONSIDERABLE
-> G97 POSITIVE: 141
-> FINAL PC POSITIVE: 141
-> PS NONZERO: 0
-> RUNTIME BUY: 0
-> HOLDING EFFECT: 0
```

## Baseline Comparison

For dates where both the target and baseline runs contain `execution/fills.json`, the fill signatures match exactly:

```text
Comparable fill days: 182
Range: 2022-10-03 through 2023-06-28
Fill differences: 0
```

This explains why the G97 fresh-run can look materially identical to G90 despite additional PC evidence: no G97 row reaches a positive PS quantity or Runtime order.

## Canonical Merge / Overwrite Audit

G97 positive rows do enter the final canonical allocation.

Relevant producer behavior:

- `portfolio_construction._canonical_multi_allocation_deployment_set()` extends `security_allocations` with `reconsideration_binding["security_allocations"]`.
- The final payload persists both `security_allocations[]` and `residual_reconsideration_authoritative_binding_evidence`.
- Immediately after the merge, the same function computes `_lot_aware_allocation_to_sizing_compatibility(...)` over the expanded `security_allocations`.

Evidence:

```text
G97_POSITIVE_ROWS_ENTER_FINAL_CANONICAL_ALLOCATION = YES
POST_G97_CANONICAL_OVERWRITE_EXISTS = NO
```

No later actual artifact was found that rebuilds the final canonical allocation and drops the G97 rows. The rows survive into final PC, but not as lot-executable PS inputs.

## First Divergence Boundary

First actual behavior divergence from intended G97 propagation:

```text
Boundary: Portfolio Construction final canonical allocation -> G61 lot-aware compatibility -> Position Sizing selection
```

Mechanism:

1. G97 rows are appended to `canonical_multi_allocation_deployment_set.security_allocations[]`.
2. `_lot_aware_allocation_to_sizing_compatibility()` tries to resolve lot context for each row.
3. For all G97 rows, `_one_lot_weight_from_context(...)` cannot resolve a usable one-lot weight.
4. Each row becomes `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED`.
5. Position Sizing only selects rows whose compatibility state is `LOT_EXECUTABLE_COMPATIBLE`.
6. Therefore every G97 row becomes PS target/quantity zero and Runtime no-action.

Code boundaries observed:

- PC computes compatibility after G97 merge: `src/ai_fund_lab_v2/strategy/portfolio_construction.py:3380`
- PC assigns `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED` when lot context is missing: `src/ai_fund_lab_v2/strategy/portfolio_construction.py:4941`
- PS only selects `LOT_EXECUTABLE_COMPATIBLE` rows: `src/ai_fund_lab_v2/strategy/position_sizing.py:875`

## Required Conclusions

```text
G97_AUTHORITATIVE_ARTIFACT_PRESENT_IN_FRESH_RUN = YES
G97_POSITIVE_ROWS_ENTER_FINAL_CANONICAL_ALLOCATION = YES
POST_G97_CANONICAL_OVERWRITE_EXISTS = NO
PS_CONSUMES_G97_ALLOCATIONS = NO
RUNTIME_CONSUMES_G97_PS_OUTPUT = NO
G97_REGRESSION_ANCHORS_REPRODUCE_IN_ACTUAL_RUN = PARTIAL
G97_POSITIVE_ROWS_DUPLICATE_EXISTING_DESTINATION_COUNT = 0
G97_POSITIVE_ROWS_NET_NEW_DESTINATION_COUNT = 141
FIRST_ACTUAL_BEHAVIOR_DIVERGENCE_DATE = 2022-10-31
FIRST_ACTUAL_BEHAVIOR_DIVERGENCE_BOUNDARY = PC_FINAL_CANONICAL_ALLOCATION_TO_G61_LOT_COMPATIBILITY_TO_PS_SELECTION
IDENTICAL_BEHAVIOR_PRIMARY_EXPLANATION = B_ROWS_ZEROED_AT_LOT_PS_CAP
G97_ACTUAL_PROPAGATION_DEFECT_CONFIRMED = YES
REPAIR_REQUIRED = YES
```

`G97_REGRESSION_ANCHORS_REPRODUCE_IN_ACTUAL_RUN = PARTIAL` because the G97 PC positive anchors reproduce in actual artifacts, but their intended PS/Runtime propagation does not.

`G97_POSITIVE_ROWS_NET_NEW_DESTINATION_COUNT = 141` means G97 created 141 final canonical allocation destinations relative to the G97 marker, but none produced a net executable position effect.

## Safety / Integrity

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
THRESHOLD_WEIGHT_TUNING = NO
FRESH_RUN_EXECUTED_BY_CODEX = NO
RESUME_EXECUTED_BY_CODEX = NO
REPLAY_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_STRATEGY_INPUT_COUNT = 0
```

## Recommended Next Boundary

Repair only the actual G97-to-G61 lot context propagation boundary.

The next task should not redesign G90/G81/G86/G97 semantics and should not change Market Quality, Risk Pacing, thresholds, candidate ranking, or PS quantity ownership. The narrow repair target is to ensure G97 reconsidered rows carry the existing canonical lot sizing context needed by `_lot_aware_allocation_to_sizing_compatibility()` so that genuinely executable rows can become `LOT_EXECUTABLE_COMPATIBLE` and then be consumed by PS.
