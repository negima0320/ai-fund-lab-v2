# Phase30-AK3R2A - Post-AK3R1 Fresh 1BD Zero-BUY Root-Cause Audit

Task ID: `Phase30-AK3R2A`

Type: `READ_ONLY_REGRESSION_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T222751947653Z
```

Audit date:

```text
2022-08-10
```

Boundary:

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK3R2A
NO_REPLAY_RESUME_FRESH_RUN_BY_CODEX
NO_RUNTIME_MUTATION
NO_THRESHOLD_CAP_CANDIDATE_MODEL_SAFETY_CHANGE
```

## Primary Judgment

```text
POST_AK3R1_ZERO_BUY_CLASSIFICATION = B_NEW_SUBMIT_OR_EXECUTION_GAP
```

AK3R1 was action-effective in fresh runtime. The previous selected-position
overshoot review did not recur.

The new zero-BUY root cause is:

```text
SUBMIT_FEASIBILITY_AGGREGATE_CASH_REVIEW_TO_ATOMIC_PENDING_NO_SUBMISSION
```

Runtime Planning/Pending generated 13 BUY items. Submit feasibility passed 12
items, including all 5 AK3R1-authorized one-lot items, but one legacy BUY
item, `93180`, failed cash feasibility because reserved notional exceeded
remaining current cash at its sequence point:

```text
symbol = 93180
estimated_amount = 49,800
reserved_notional = 290,500
cash_at_check = 271,880
reason = reserved notional exceeds Current cash
```

Because Pending uses item-scoped review with atomic BUY batch protection, this
single cash review item produced zero submitted orders and zero fills.

## Required Counts

```text
FIRST_ZERO_BUY_LAYER = SUBMIT_FEASIBILITY_AGGREGATE_CASH_REVIEW_TO_ATOMIC_PENDING_NO_SUBMISSION
CANDIDATE_COUNT = 50
PC_POSITIVE_COUNT = 16
AK2_ONE_LOT_AUTHORITY_COUNT = 5
PS_POSITIVE_COUNT = 13
RUNTIME_BUY_PLAN_COUNT = 13
PENDING_BUY_ITEM_COUNT = 13
SUBMIT_FEASIBILITY_PASS_COUNT = 12
SUBMIT_FEASIBILITY_REVIEW_COUNT = 1
SUBMITTED_ORDER_COUNT = 0
BUY_FILL_COUNT = 0
```

## AK3R1 Authority Consumption

```text
AK3R1_AUTHORITY_RUNTIME_MATERIALIZED = YES
AK3R1_AUTHORITY_RUNTIME_CONSUMED = YES
AUTHORIZED_ONE_LOT_SUBMIT_PASS_COUNT = 5
AUTHORIZED_ONE_LOT_SUBMIT_REVIEW_COUNT = 0
SELECTED_AMOUNT_OVERSHOOT_REVIEW_RECURRENCE = NO
POSITION_SIZING_AUTHORITY_RESOLUTION = PASS
```

Authorized one-lot items:

| Symbol | Original PC Notional | Executable Notional | Reserved Notional | Authority | Submit |
| --- | ---: | ---: | ---: | --- | --- |
| 38410 | 52,632 | 80,800 | 96,700 | `ADMIT` | `PASS` |
| 39950 | 52,632 | 52,800 | 61,500 | `ADMIT` | `PASS` |
| 47770 | 52,632 | 68,400 | 78,000 | `ADMIT` | `PASS` |
| 83060 | 52,632 | 71,350 | 85,920 | `ADMIT` | `PASS` |
| 99840 | 52,632 | 132,880 | 162,380 | `ADMIT` | `PASS` |

All five consumed:

```text
authority_type = PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION
authority_decision = ADMIT
one_lot_submit_authority_status = PASS
submit_feasibility_status = PASS
```

## Submit / Atomic Batch

```text
ATOMIC_BATCH_BLOCK_RECURRENCE = YES_DIFFERENT_TRIGGER_CASH_REVIEW
BLOCKED_BY_BATCH_REVIEW_COUNT = 12
ITEM_SCOPED_REVIEW_COUNT = 1
```

The previous AK3R0 trigger:

```text
estimated amount exceeds selected_position_amount
```

did not recur.

The new trigger:

```text
reserved notional exceeds Current cash
```

Batch totals:

```text
strategy_executable_notional_total = 715,650
reserved_notional_total = 1,260,860
cash = 1,000,000
ending_reserved_cash_after_nonblocked_items = 29,640
```

## Normal Preexisting BUY Preservation

Pre-AK2 normal 2022-08-10 BUY symbols:

```text
23700, 94320, 89180, 93180, 23880, 66590, 94340, 76470
```

Post-AK3R1 disappearance distribution:

```text
NORMAL_PREEXISTING_BUY_DISAPPEARANCE_REASON_DISTRIBUTION = {
  "batch_submit_blocked_by_other_review": 7,
  "reserved notional exceeds Current cash": 1
}
```

`93180` is the direct cash-review item. The other seven normal BUYs passed
item feasibility but were not submitted because the atomic BUY batch ended in
review.

## Fresh State Integrity

```text
FRESH_STATE_INTEGRITY = PASS
```

Evidence:

```text
plan.initial_state.cash = 1,000,000
plan.initial_state.positions = 0
plan.initial_state.pending = 0
morning.pending_slot_status = EMPTY
morning.pm_status = NO_POSITION
morning.safety_status = PASS
positions.position_campaigns count = 0
execution.fills = []
```

The target run was still running at read time:

```text
run_state.status = RUNNING
completed_business_days = [2022-08-10, 2022-08-12]
next_job = 2022-08-15:market_refresh
```

## Defect Boundary

```text
KNOWN_RUNTIME_DEFECT = NO_SUBMIT_FAIL_CLOSED_AS_DESIGNED
KNOWN_AUTHORITY_DEFECT = YES_PLANNING_PENDING_BATCH_RESERVED_NOTIONAL_CASH_FEASIBILITY_GAP
```

Submit did not fail open. The defect boundary is upstream authority / planning:
the BUY batch was allowed to reach Pending with aggregate market-order reserved
notional above cash, so Submit correctly refused the atomic batch.

## Evidence

Primary evidence:

```text
reports/phase_reports/phase30_ak3r2a_post_ak3r1_fresh_1bd_zero_buy_root_cause_audit.json
reports/phase_reports/phase30_ak3r2a/buy_chain_comparison_2022_08_10.json
```

Runtime artifacts inspected:

```text
daily/2022-08-10/strategy/buy_quality_decisions.json
daily/2022-08-10/strategy/portfolio_construction.json
daily/2022-08-10/strategy/position_sizing.json
daily/2022-08-10/strategy/runtime_planning.json
daily/2022-08-10/morning/planning_evidence.json
daily/2022-08-10/submit/runtime_manifest.json
daily/2022-08-10/execution/submitted_order_authority.json
daily/2022-08-10/execution/historical_fill_authority.json
daily/2022-08-10/execution/fills.json
.runtime/pending_order_plan/history/2022-08-10/pending-strategy-plan-historical-2022-08-10-6f8eb6bfbef7908e.json
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK3R2A
```

## Recommended Next Task

```text
Phase30-AK3R2B - Reserved-Notional-Aware BUY Batch Construction / Cash Feasibility Repair
```
