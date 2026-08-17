# Phase30-AK9R0 - Post-AK9 Fresh Zero-BUY Regression Root-Cause Audit

Task ID: `Phase30-AK9R0`

Type: `READ_ONLY_FRESH_RUNTIME_REGRESSION_ROOT_CAUSE_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260817T040435873521Z
```

Primary comparison run:

```text
runtime-test-historical-extended-smoke-20260817T014925194738Z
```

## Primary Judgment

```text
POST_AK9_ZERO_BUY_REGRESSION_CLASSIFICATION =
  SUBMIT_BUY_ITEM_SCOPED_REVIEW_ATOMIC_BATCH_NO_SUBMISSION_REGRESSION

FIRST_ZERO_BUY_LAYER = Submit
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
```

The fresh zero-BUY result is not caused by missing Candidates, zero PC target,
zero PS quantity, AK2 one-lot admission, cash infeasibility, Sell Planning
overwrite, or valuation refresh.

On 2022-08-10 the pipeline produced 50 Candidates, 16 positive PC BUY_NEW
members, 16 PC executable quantity authorities, 16 positive PS BUY_NEW
quantities, 16 Runtime BUY_NEW plans, and 16 Morning Pending BUY items. Submit
then read a valid pending plan with 16 BUY items, but classified it as:

```text
BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION
no_action_reason = buy_item_scoped_review_no_approved_items
submit_action = NO_SUBMISSION_REQUIRED
submitted_count = 0
```

Root cause: AK7R made larger discrete executable quantities materialize through
PC -> PS as intended. AK3R2B then kept non-cash authority failures inside the
active pending BUY batch as `INCLUDE_REVIEW_REQUIRED`. Submit preserves atomic
BUY batch protection, so the reviewed BUY items block the otherwise PASS BUY
items, leaving zero approved BUY items and zero submitted orders.

## 2022-08-10 BUY Chain

```text
CANDIDATE_COUNT = 50
PC_POSITIVE_BUY_NEW_COUNT = 16
PC_POSITIVE_EXECUTABLE_QUANTITY_AUTHORITY_COUNT = 16
AK2_ONE_LOT_AUTHORITY_COUNT = 0
PS_POSITIVE_BUY_NEW_COUNT = 16
RUNTIME_BUY_NEW_COUNT = 16
CASH_FEASIBLE_BUY_INCLUDED_COUNT = 8
CASH_PRUNED_COUNT = 0
PENDING_BUY_COUNT = 16
SUBMIT_BUY_PASS_COUNT = 0
SUBMITTED_BUY_ORDER_COUNT = 0
BUY_FILL_COUNT = 0
```

Evidence:

- `strategy/buy_quality_decisions.json`: 50 decisions.
- `strategy/portfolio_construction.json`: 16 positive BUY_NEW members, all with
  `pc_positive_executable_quantity_authority.status = PASS`.
- `strategy/position_sizing.json`: 16 positive BUY_NEW `final_quantity_delta`.
- `morning/planning_evidence.json`: `plan_count = 19`,
  `pending_item_count = 16`, `pending_commit_status = COMMITTED_CURRENT`.
- `submit/runtime_manifest.json`: `submit_action = NO_SUBMISSION_REQUIRED`,
  `pending_item_count = 16`, `submitted_count = 0`.
- `execution/fills.json`: zero fills.

## Cash-Feasible Batch

2022-08-10 cash batch:

```text
starting_cash = 1000000.0
candidate_buy_count = 16
included_buy_count = 8
cash_pruned_count = 0
final_reserved_notional_total = 922400.0
remaining_reserved_cash = 77600.0
```

The cash-pruning repair is action-effective for cash. The active PASS subset
fits inside available cash, and there is no `DEFERRED_INSUFFICIENT_RESERVED_CASH`
on 2022-08-10.

The reviewed items are non-cash position-sizing reviews:

```text
23880  quantity=300   reason=estimated amount exceeds selected_position_amount
47840  quantity=100   reason=estimated amount exceeds selected_position_amount
61980  quantity=100   reason=estimated amount exceeds selected_position_amount
76470  quantity=2000  reason=estimated amount exceeds selected_position_amount
89180  quantity=5000  reason=estimated amount exceeds selected_position_amount
94320  quantity=300   reason=estimated amount exceeds selected_position_amount
94340  quantity=300   reason=estimated amount exceeds selected_position_amount
95010  quantity=100   reason=estimated amount exceeds selected_position_amount
```

Submit then applies atomic BUY batch protection:

```text
review_required_count = 8
blocked_by_batch_count = 8
partial_buy_submit_allowed = false
submitted_count = 0
```

## Before / After Divergence

`runtime-test-historical-extended-smoke-20260817T014925194738Z` on 2022-08-10:

```text
candidate_buy_count = 13
included_buy_count = 12
cash_pruned_count = 1
review_decision_count = 0
pending_item_count = 12
submit_action = SUBMIT
submitted_count = 12
BUY_FILL_COUNT = 12
```

`runtime-test-historical-extended-smoke-20260817T040435873521Z` on 2022-08-10:

```text
candidate_buy_count = 16
included_buy_count = 8
cash_pruned_count = 0
review_decision_count = 8
pending_item_count = 16
submit_action = NO_SUBMISSION_REQUIRED
submitted_count = 0
BUY_FILL_COUNT = 0
```

```text
FIRST_BEFORE_AFTER_BEHAVIORAL_DIVERGENCE =
  Runtime Planning / cash-feasible batch composition began retaining
  non-cash position_sizing REVIEW_REQUIRED BUY items in the active BUY batch.
  The first layer where BUY becomes zero is Submit, via
  BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION.
```

## Three-Day Recurrence

```text
2022-08-10: pending=16, review_required=8, blocked_by_batch=8, submitted=0
2022-08-12: pending=17, review_required=7, blocked_by_batch=10, submitted=0
2022-08-15: pending=16, review_required=9, blocked_by_batch=7, submitted=0
```

All three zero-BUY days recur through the same root cause.

## Recent Repair Causality

```text
AK7R_PC_EXECUTABLE_AUTHORITY_MATERIALIZED = YES
AK7R_PS_CANONICAL_QUANTITY_CONSUMED = YES
AK7R_ZERO_BUY_CAUSALITY = PARTIAL
```

AK7R did not directly zero BUYs. It did make larger executable quantities reach
PS and Runtime Planning, which exposed the later non-cash review / atomic batch
handoff gap.

```text
AK2_RUNTIME_ACTION_EFFECTIVE = NOT_APPLICABLE_NO_AK2_ONE_LOT_AUTHORITY_ON_2022_08_10
```

`AK2_ONE_LOT_AUTHORITY_COUNT = 0`; AK2 did not cause this zero-BUY.

```text
AK8R_NO_SELL_BUY_PENDING_PRESERVED = YES
AK8R_ZERO_BUY_CAUSALITY = NO
```

Sell Planning was `NO_POSITION` on all three dates and did not write pending.
The AK8R sell-overwrite failure mode did not recur.

```text
AK5R2_ZERO_BUY_CAUSALITY = NO
```

The zero-BUY decision occurs at Submit before execution/fill/current valuation
can matter.

```text
CASH_CONSTRAINT_CAUSED_ZERO_BUY = NO
```

Cash was sufficient for the active PASS subset on 2022-08-10, and cash pruning
was not the direct blocker.

## Fresh State Integrity

```text
FRESH_STATE_INTEGRITY = PASS
```

Baseline compatibility was PASS. The initial state had `pending_state = EMPTY`,
`pending_active = false`, `ledger_date = 2022-08-10`, and no mismatch reasons.
The zero-BUY behavior was produced inside the fresh run, not inherited from a
dirty pending/current state.

## Why AK9 Missed This

```text
WHY_AK9_REGRESSION_SUITE_MISSED_THIS =
  The AK9 suite validated isolated cash pruning, one-lot handoff, mixed
  BUY/SELL pending, valuation continuity, and submit fail-closed behavior, but
  did not include a fresh end-to-end BUY_NEW batch containing both PASS BUY
  items and non-cash position_sizing REVIEW_REQUIRED BUY items after AK7R
  larger discrete quantity materialization. The missing sentinel was:
  mixed PASS + non-cash REVIEW_REQUIRED BUY-only batch -> Submit.
```

## Required Final Judgments

```text
FIRST_ZERO_BUY_LAYER = Submit
CANDIDATE_COUNT = 50
PC_POSITIVE_BUY_NEW_COUNT = 16
PC_POSITIVE_EXECUTABLE_QUANTITY_AUTHORITY_COUNT = 16
AK2_ONE_LOT_AUTHORITY_COUNT = 0
PS_POSITIVE_BUY_NEW_COUNT = 16
RUNTIME_BUY_NEW_COUNT = 16
CASH_FEASIBLE_BUY_INCLUDED_COUNT = 8
CASH_PRUNED_COUNT = 0
PENDING_BUY_COUNT = 16
SUBMIT_BUY_PASS_COUNT = 0
SUBMITTED_BUY_ORDER_COUNT = 0
BUY_FILL_COUNT = 0
FIRST_BEFORE_AFTER_BEHAVIORAL_DIVERGENCE =
  AK7R/AK3R2B-era active BUY batch now includes non-cash
  position_sizing REVIEW_REQUIRED items; Submit converts the mixed BUY-only
  batch to BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION.
AK7R_PC_EXECUTABLE_AUTHORITY_MATERIALIZED = YES
AK7R_PS_CANONICAL_QUANTITY_CONSUMED = YES
AK7R_ZERO_BUY_CAUSALITY = PARTIAL
AK2_RUNTIME_ACTION_EFFECTIVE = NOT_APPLICABLE_NO_AK2_ONE_LOT_AUTHORITY_ON_2022_08_10
AK8R_NO_SELL_BUY_PENDING_PRESERVED = YES
AK8R_ZERO_BUY_CAUSALITY = NO
AK5R2_ZERO_BUY_CAUSALITY = NO
CASH_CONSTRAINT_CAUSED_ZERO_BUY = NO
ZERO_BUY_RECURS_SAME_ROOT_CAUSE_ALL_3_DAYS = YES
FRESH_STATE_INTEGRITY = PASS
POST_AK9_ZERO_BUY_REGRESSION_CLASSIFICATION =
  SUBMIT_BUY_ITEM_SCOPED_REVIEW_ATOMIC_BATCH_NO_SUBMISSION_REGRESSION
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R0
```

## Recommended Next Task

```text
Phase30-AK9R1 - Non-Cash BUY Review Batch Submit Boundary Focused Repair
```

Repair target should be limited to the confirmed handoff:

```text
PASS BUY items + non-cash REVIEW_REQUIRED BUY items
-> preserve fail-closed review semantics for reviewed items
-> prevent reviewed items from causing authorized PASS BUY items to disappear
-> preserve cash pruning, atomicity where explicitly required, AK8R SELL
   independence, and Submit final fail-closed guards
```

No implementation was authorized or performed in Phase30-AK9R0.
