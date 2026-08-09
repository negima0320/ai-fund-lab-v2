# Phase28-D67 Fresh 100BD 2023-05-09 Morning HALT Root Cause Audit

## Judgment

Primary Judgment:

```text
PHASE28_D67_PC_PS_ADD_TARGET_WEIGHT_CHANGE_CONTRACT_MISMATCH_CONFIRMED
```

The 2023-05-09 morning halt is confirmed as a production-common Strategy contract defect between Portfolio Construction and Position Sizing for an existing-position `ADD` row whose current weight is already above the single-name cap. It is not a Pending Safety D63 regression, not a D3 pending reconciliation regression, and not a cash-capacity halt.

## Direct HALT Producer

Target run:

```text
runtime-test-historical-smoke-20260809T065457596902Z
```

Direct Runtime CLI exit producer:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:713
```

`EXIT_REVIEW_REQUIRED` is `20`, and the morning job maps `StrategyPlanningAuthorityResult.status == REVIEW_REQUIRED` to exit code 20. Evidence:

- `daily/2023-05-09/morning/cli_result.json`: `exit_code = 20`
- `daily/2023-05-09/morning/runtime_manifest.json`: `reason = morning pipeline review required: strategy_planning_authority_unresolved`

Direct authority producer:

```text
Strategy Planning Authority
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:365
```

Direct reason:

```text
strategy_planning_authority_unresolved
strategy_plan_quantity_unresolved:76470
```

The direct fail-closed is legitimate: Strategy Planning Authority must not commit a BUY_ADD pending item when planned quantity is unresolved.

## Root Cause Chain

The first bad state is earlier than Strategy Planning Authority.

```text
Portfolio Construction
76470 PM ADD
current_weight = 0.182409
single_name_weight_cap = 0.18
post_add_target_weight = 0.18
target_weight_change = -0.002409

Position Sizing
ADD branch reads target_weight_change through _ratio(...)
_ratio requires 0 <= value <= 1
negative signed delta raises "ratio out of range"

Runtime Planning
BUY_ADD survives as intent but quantity authority is unresolved

Strategy Planning Authority
strategy_plan_quantity_unresolved:76470

run_daily_operation
exit code 20
```

Code evidence:

- Portfolio Construction emits `target_weight_change`: `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1961`
- Position Sizing consumes it as a ratio: `src/ai_fund_lab_v2/strategy/position_sizing.py:855`
- `_ratio` rejects negative values: `src/ai_fund_lab_v2/strategy/position_sizing.py:1915`
- Strategy Planning Authority rejects non-positive planned quantity: `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:448`

## State Boundary

2023-05-08 is a useful control case:

```text
76470
pm_action = ADD
current_weight = 0.173457
post_add_target_weight = 0.18
target_weight_change = +0.006543
Position Sizing = PASS
Runtime Planning = NO_ACTION, zero delta
fills = []
current_apply = NOT_REQUIRED
```

2023-05-09 is the first observed failure:

```text
76470
pm_action = ADD
current_weight = 0.182409
post_add_target_weight = 0.18
target_weight_change = -0.002409
Position Sizing = BLOCK
error = ratio out of range
Runtime Planning = BUY_ADD, quantity unresolved
```

This is not a bad fill or state mutation from 2023-05-08. The current weight moved above cap because valuation changed while quantity stayed `6900`.

## Regression Checks

D61 causality:

```text
CONTRIBUTING
```

D61 made the valid PM ADD path reach the ADD allocation/PC/PS path. The root defect is not D61's ADD evidence semantics; it is the PC/PS field contract when ADD has no executable positive increment because current weight is already over the cap.

D63 causality:

```text
UNRELATED
```

2023-05-09 Data Readiness passed. Pending and safety component reasons are empty. The previous pending plan is 2023-05-08 empty/no-order and inactive.

D3 pending reconciliation regression:

```text
NO
```

No `existing_pending_conflict` reason was observed, no active stale pending blocked the run, and submit/execution were not reached.

BUY / SELL independence:

```text
NO VIOLATION
```

2023-05-09 PM actions are `76010=HOLD`, `76470=ADD`, `94320=HOLD`; no SELL/REDUCE/EXIT intent existed to be independently allowed.

Cash capacity:

```text
UNRELATED
```

Cash was ready (`506220.0`), pending reservation was zero, no requested notional reached submit feasibility, and the first block was Position Sizing `ratio out of range`.

## Runtime Contract Legitimacy

Classification:

```text
PARTIAL LEGITIMATE_FAIL_CLOSED
PLANNING_DEFECT
CAPITAL_CONVERSION_CONTRACT_DEFECT
```

The final fail-closed is correct: unresolved BUY_ADD quantity cannot become Pending. The upstream producer/consumer mismatch is a production runtime defect and requires repair.

## Resume / Fresh Decision

Resume after repair:

```text
YES
```

Fresh run required after repair:

```text
NO
```

The halt happened before pending commit, submit, broker simulation, execution, fills, and current-state mutation for 2023-05-09. D67 did not resume or run fresh.

## D66 Status

```text
WAITING
```

D66 final attribution must remain blocked until a repaired 100BD run completes. The partial run through 2023-05-08 must not be used as final D66 effect evidence.

## Next Phase

```text
Phase28-D68 PC/PS ADD target_weight_change signed-delta contract repair design
```

Minimal D68 scope: design one production-common repair for ADD rows where current weight is above cap and executable ADD increment is zero. The repair should preserve D61 ADD evidence, D63 Pending Safety protection, and fail-closed behavior. It should not loosen Submit Guard, broker, thresholds, config, schema, or Accepted Generation.

## Deliverables

- `docs/phase_reports/phase28_d67_fresh_100bd_20230509_morning_halt_root_cause_audit.md`
- `reports/phase_reports/phase28_d67_fresh_100bd_20230509_morning_halt_root_cause_audit.json`
- `reports/phase28_d67_fresh_100bd_20230509_morning_halt_root_cause_audit/`

## Non-Actions

No implementation, config, schema, threshold, model, Accepted Generation, Runtime artifact, Pending artifact, Runtime state, fresh run, resume, long historical, or 100BD rerun was performed by Codex in D67.
