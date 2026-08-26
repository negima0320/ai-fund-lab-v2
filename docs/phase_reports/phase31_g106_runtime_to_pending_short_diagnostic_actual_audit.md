# Phase31-G106 - Runtime-to-Pending Short Diagnostic Actual Audit

## PRIMARY_JUDGMENT

`G106_RUNTIME_PENDING_BEHAVIOR_CORRECT_NO_REPAIR`

The short diagnostic run:

```text
runtime-test-historical-extended-smoke-20260825T045610960730Z
```

contains the required primary anchor:

```text
2022-11-11 / 76470
```

Actual artifacts prove that 76470 did not disappear because of a Runtime-to-Pending consumer defect. The row satisfied Runtime planning, entered Strategy Authority, generated a PendingOrderItem candidate, and was then explicitly pruned by `_cash_feasible_buy_batch()` because same-day cash was insufficient after higher-priority BUY reservations.

No code/config/run-state changes were made. No fresh-run/resume/replay/long Historical was executed by Codex.

## Target Run

```text
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260825T045610960730Z
AUDIT_MODE = READ_ONLY_ACTUAL_ARTIFACTS
PRIMARY_ANCHOR = 2022-11-11 / 76470
RUN_STATE_AT_AUDIT = RUNNING
COMPLETED_DAILY_ARTIFACTS_AUDITED = 2022-10-03 through 2022-11-17
```

The run was not stopped or modified.

## Primary Anchor Trace

### PC / G97 / G99 / G102 Provenance

The primary anchor is present in residual reconsideration authoritative binding evidence inside:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T045610960730Z/daily/2022-11-11/strategy/position_sizing.json
```

Actual values:

```text
residual_reconsideration_authoritative_binding = true
positive_authoritative_count = 1
symbol = 76470
allocation_authority_status = AUTHORITATIVE_PC_RESIDUAL_RECONSIDERATION_BOUND
interaction_result = DEPLOY_ELIGIBLE
g102_item_scoped_pc_discrete_quantity_authority_propagated = true
pc_positive_executable_quantity_authority.status = PASS
pc_positive_executable_quantity_authority.final_allocated_quantity = 300
pc_positive_executable_quantity_authority.ps_must_consume_canonical_quantity = true
phase29_l19_lot_resolution.g102_item_scoped_pc_discrete_quantity_authority = true
phase29_l19_lot_resolution.lot_overshoot_reason =
  G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY
```

G61 / lot-aware compatibility:

```text
compatibility_state = LOT_EXECUTABLE_COMPATIBLE
projected_quantity_delta_evidence_only = 300
reference_price = 26.0
trading_unit = 100
portfolio_value = 1,115,160
```

### Position Sizing

Actual values from `strategy/position_sizing.json`:

```text
security_code = 76470
current_quantity = 0
quantity_delta_candidate = 300
final_quantity_delta = 300
target_weight = 0.007832
incremental_buy_notional = 8,733.93
pc_discrete_quantity_authority_consumed = false at top-level row
```

The residual reconsideration binding evidence still carries the item-scoped PC authority `PASS / final_allocated_quantity=300`.

### Runtime Planning

Actual values from `strategy/runtime_planning.json`:

```text
security_code = 76470
planning_id = rp-2022-11-11-76470-buy_new-4bdf36eb19f86836
planning_intent = BUY_NEW
order_side_intent = BUY
planned_quantity = 300
quantity_delta_candidate = 300
target_quantity_candidate = 300
quantity_status = RESOLVED_EXECUTABLE
pending_eligibility = CANDIDATE_ONLY
reference_price = 26.0
reference_price_date = 2022-11-11
reference_price_type = planning_reference_close
reason_codes =
  - position_sizing_positive_quantity_delta_maps_to_buy_new
  - position_sizing_quantity_candidate_resolved
```

### Strategy Authority

Actual Strategy Authority evidence:

```text
order_plan_artifact_path =
  .runtime/runtime_state/strategy_planning/2022-11-11/order_plan.json

pending_item_count = 2
selected_symbols = 45840,35280
status = PASS
```

`strategy_item_lineage[]` for 76470 proves `_pending_item_from_strategy_plan()` generated a candidate:

```text
security_code = 76470
planning_id = rp-2022-11-11-76470-buy_new-4bdf36eb19f86836
planning_intent = BUY_NEW
order_side_intent = BUY
pending_item_generated = true
reason = pending_item_generated
opportunity_buy_rank = 4
```

Therefore:

```text
_pending_item_from_strategy_plan invoked = YES
Pending candidate generated = YES
generated pending_item_id = strategy-78c58fe80c0b766fb58d
```

### Cash Feasible Buy Batch

Actual `cash_feasible_buy_batch.items[]` row for 76470:

```text
symbol = 76470
pending_item_id = strategy-78c58fe80c0b766fb58d
canonical_priority_index = 5
executable_quantity = 300
reservation_price = 56.0
reserved_notional = 16,800
cash_before_item = 9,290
remaining_cash_before_item = 9,290
reserved_cash_before_item = 68,700
decision = PRUNE
reason = DEFERRED_INSUFFICIENT_RESERVED_CASH
source_submit_feasibility_status = REVIEW_REQUIRED
source_violated_policy = cash
reserved_cash_after_item = 9,290
```

Batch summary:

```text
included_buy_count = 2
cash_pruned_count = 3
final_reserved_notional_total = 68,700
remaining_reserved_cash = 9,290
priority_order_preservation = PASS
```

Same-day batch order:

| Priority | Symbol | Decision | Reserved Notional | Remaining Cash Before | Violated Policy |
|---:|---:|---|---:|---:|---|
| 1 | 45840 | INCLUDE | 36,300 | 77,990 |  |
| 2 | 35280 | INCLUDE | 32,400 | 41,690 |  |
| 3 | 76920 | PRUNE | 35,920 | 9,290 | cash |
| 4 | 60480 | PRUNE | 28,400 | 9,290 | cash |
| 5 | 76470 | PRUNE | 16,800 | 9,290 | cash |

76470 required 16,800 reserved notional, but only 9,290 cash remained after included higher-priority reservations.

### Final Order Plan / Persisted Pending / Submit

Final order-plan items on 2022-11-11:

```text
45840 BUY 100
35280 BUY 100
```

Submit manifest persisted Pending payload:

```text
pending_state = APPROVED
pending_item_count = 2
approved_item_ids =
  strategy-fed1502003be290c057b
  strategy-3ef56addb9e95e2ae5ae

items =
  45840 BUY 100
  35280 BUY 100
```

76470 is absent from final order plan, persisted Pending, and Submit item results because it was pruned before final Pending persistence.

```text
final order-plan contains 76470 = NO
persisted Pending contains 76470 = NO
Submit contains 76470 = NO
```

## Primary Classification

```text
20221111_76470_CLASSIFICATION = LEGITIMATE_CASH_PRUNE
```

The exact causal boundary is:

```text
PendingOrderItem candidate generated
-> _cash_feasible_buy_batch()
-> PRUNE / DEFERRED_INSUFFICIENT_RESERVED_CASH
-> not included in final pending_items
-> not persisted to Pending
```

This is not a Runtime-to-Pending consumer gap.

## Cash Feasibility Causality

```text
CASH_FEASIBLE_BUY_BATCH_CAUSAL = YES
CASH_PRUNE_CONFIRMED = YES
BUYING_POWER_PRUNE_CONFIRMED = NO
```

Exact evidence path:

```text
.runtime/runtime_state/strategy_planning/2022-11-11/order_plan.json
  .cash_feasible_buy_batch.items[]
  select(.symbol == "76470")
```

Key values:

```text
decision = PRUNE
reason = DEFERRED_INSUFFICIENT_RESERVED_CASH
source_submit_feasibility_status = REVIEW_REQUIRED
source_violated_policy = cash
reserved_notional = 16,800
remaining_cash_before_item = 9,290
```

## Candidate Creation vs Persistence

```text
PENDING_CANDIDATE_GENERATED = YES
PENDING_CANDIDATE_SURVIVED_CASH_BATCH = NO
PENDING_PERSISTENCE_EXPECTED_AFTER_BATCH = NO
```

The candidate was created, but after an explicit cash prune it was not supposed to persist.

## Normal Same-Day Comparison

Same-day successful BUY rows:

| Symbol | Planned Qty | Reserved Notional | Batch Decision | Submit |
|---:|---:|---:|---|---|
| 45840 | 100 | 36,300 | INCLUDE | submitted |
| 35280 | 100 | 32,400 | INCLUDE | submitted |

Same-day pruned rows:

| Symbol | Planned Qty | Reserved Notional | Batch Decision | Reason |
|---:|---:|---:|---|---|
| 76920 | 200 | 35,920 | PRUNE | DEFERRED_INSUFFICIENT_RESERVED_CASH |
| 60480 | 100 | 28,400 | PRUNE | DEFERRED_INSUFFICIENT_RESERVED_CASH |
| 76470 | 300 | 16,800 | PRUNE | DEFERRED_INSUFFICIENT_RESERVED_CASH |

76470 did not vanish independently. It was the fifth BUY in the cash-feasible ordering, after 68,700 of same-day cash had already been reserved by the two included rows.

```text
76470_LOST_LEGITIMATE_CAPITAL_COMPETITION = YES
```

## Short-Window Residual Funnel

Using available date-specific order-plan artifacts from:

```text
.runtime/runtime_state/strategy_planning/YYYY-MM-DD/order_plan.json
```

for completed daily artifacts through 2022-11-17:

```text
SHORT_WINDOW_RUNTIME_BUY_COUNT = 93
SHORT_WINDOW_INCLUDED_BUY_COUNT = 51
SHORT_WINDOW_INCLUDE_REVIEW_REQUIRED_COUNT = 22
SHORT_WINDOW_CASH_PRUNE_COUNT = 20
SHORT_WINDOW_BUYING_POWER_PRUNE_COUNT = 0
SHORT_WINDOW_TRUE_PENDING_GAP_COUNT = 0
SHORT_WINDOW_OTHER_COUNT = 0
```

Decision distribution:

```text
INCLUDE = 51
INCLUDE_REVIEW_REQUIRED = 22
PRUNE = 20
```

Policy distribution:

```text
cash = 20
historical_corporate_action_symbol_quarantine = 13
dynamic_cash = 8
position_sizing = 1
blank/PASS = 51
```

Critical invariant:

```text
INCLUDE or INCLUDE_REVIEW_REQUIRED rows missing from final order-plan items = 0
PRUNE rows missing from final order-plan items = 20
```

This supports the G105 hypothesis that the residual non-materialized rows can be legitimate cash pruning, not necessarily a true Pending consumer defect.

## Additional Observable Anchors

Observable pruned anchors in and after the requested 2022-11-11 boundary include:

| Date | Symbol | Qty | Decision | Violated Policy | Final Pending |
|---|---:|---:|---|---|---|
| 2022-11-11 | 76920 | 200 | PRUNE | cash | NO |
| 2022-11-11 | 60480 | 100 | PRUNE | cash | NO |
| 2022-11-11 | 76470 | 300 | PRUNE | cash | NO |
| 2022-11-14 | 78860 | 100 | PRUNE | cash | NO |
| 2022-11-14 | 76920 | 300 | PRUNE | cash | NO |
| 2022-11-14 | 46890 | 100 | PRUNE | cash | NO |
| 2022-11-15 | 80290 | 100 | PRUNE | cash | NO |
| 2022-11-15 | 72110 | 100 | PRUNE | cash | NO |
| 2022-11-17 | 67210 | 200 | PRUNE | cash | NO |
| 2022-11-17 | 87890 | 600 | PRUNE | cash | NO |

No `decision=INCLUDE` or `decision=INCLUDE_REVIEW_REQUIRED` row was found missing from final order-plan items in the audited short window.

## G104 Actual Activation Check

Submit artifacts in the short window show canonical PC discrete quantity submit authority recognition is active for ordinary BUY rows:

```text
canonical_discrete_quantity_submit_authority.status = PASS
canonical_discrete_quantity_submit_authority.reason = pc_discrete_quantity_authority_verified
authority_type = PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
```

Examples:

```text
2022-10-03 / 94340 / PASS / pc_discrete_quantity_authority_verified
2022-10-03 / 37820 / PASS / pc_discrete_quantity_authority_verified
2022-10-03 / 93600 / PASS / pc_discrete_quantity_authority_verified
2022-11-11 / 45840 / PASS / pc_discrete_quantity_authority_verified
2022-11-11 / 35280 / PASS / pc_discrete_quantity_authority_verified
```

The specific 2022-11-11 / 76470 G102 item-scoped authority did not reach Submit because it was cash-pruned first.

```text
G104_ACTUAL_SUBMIT_RECOGNITION_ACTIVE = YES
```

## Short E2E Holding Gate

The primary reconsideration-derived anchor 2022-11-11 / 76470 did not survive cash feasibility. No qualifying reconsideration-derived BUY was proven to survive all gates in this short window.

```text
SHORT_E2E_HOLDING_GATE = NOT_REACHED
```

Normal same-day BUYs 45840 and 35280 did submit and fill, but they are not used to satisfy the reconsideration-derived E2E gate.

## Architecture Judgment

The observed behavior conforms to the intended architecture:

```text
Runtime Planning may expose BUY candidate quantities.
Strategy Authority may generate PendingOrderItem candidates.
Strategy Authority then applies canonical same-day cash feasibility before final Pending persistence.
Cash/buying-power pruned rows do not persist as Pending items.
```

```text
RUNTIME_TO_PENDING_ARCHITECTURE_CONFORMANCE = PASS
```

## Repair Decision

No repair is justified for the primary anchor.

Do not weaken:

```text
cash feasibility
buying power feasibility
Pending admission
Submit
Safety
PS quantity ownership
Runtime priority
```

## Required Final Judgments

```text
20221111_76470_CLASSIFICATION = LEGITIMATE_CASH_PRUNE

PENDING_CANDIDATE_GENERATED = YES
PENDING_CANDIDATE_SURVIVED_CASH_BATCH = NO

CASH_FEASIBLE_BUY_BATCH_CAUSAL = YES
CASH_PRUNE_CONFIRMED = YES
BUYING_POWER_PRUNE_CONFIRMED = NO

76470_LOST_LEGITIMATE_CAPITAL_COMPETITION = YES

SHORT_WINDOW_RUNTIME_BUY_COUNT = 93
SHORT_WINDOW_CASH_PRUNE_COUNT = 20
SHORT_WINDOW_BUYING_POWER_PRUNE_COUNT = 0
SHORT_WINDOW_TRUE_PENDING_GAP_COUNT = 0
SHORT_WINDOW_OTHER_COUNT = 0

RUNTIME_TO_PENDING_TRUE_DEFECT_CONFIRMED = NO
LEGITIMATE_PRUNE_CONFIRMED = YES

G104_ACTUAL_SUBMIT_RECOGNITION_ACTIVE = YES

SHORT_E2E_HOLDING_GATE = NOT_REACHED

RUNTIME_TO_PENDING_ARCHITECTURE_CONFORMANCE = PASS

SAFE_NARROW_REPAIR_POSSIBLE = NOT_REQUIRED
REPAIR_REQUIRED = NO
```

## Decision

```text
G106_RUNTIME_PENDING_BEHAVIOR_CORRECT_NO_REPAIR
```

## Constraint Confirmation

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
RUN_MODIFIED = NO
FRESH_RUN_EXECUTED_BY_CODEX = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
FUTURE_PNL_OR_OUTCOME_USED = NO
G90_CHANGED = NO
G97_CHANGED = NO
G99_CHANGED = NO
G102_CHANGED = NO
G104_CHANGED = NO
MARKET_QUALITY_CHANGED = NO
RISK_PACING_CHANGED = NO
CANDIDATE_RANKING_CHANGED = NO
ADD_CHANGED = NO
SAFETY_CHANGED = NO
PS_OWNERSHIP_CHANGED = NO
RUNTIME_PRIORITY_CHANGED = NO
CASH_BUYING_POWER_POLICY_CHANGED = NO
```
