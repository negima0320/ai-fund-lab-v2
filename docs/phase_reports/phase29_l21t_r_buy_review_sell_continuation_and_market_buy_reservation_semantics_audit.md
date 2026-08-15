# Phase29-L21T-R BUY Review / SELL Continuation & MARKET BUY Reservation Semantics Audit

## Scope

READ-ONLY AUDIT / DESIGN VERIFICATION.

Codex did not implement source changes, mutate runtime state, execute recovery,
rollback, resume, fresh-run, or long Historical validation.  This report is the
only intended artifact change for L21T-R.

Target run:

```text
runtime-test-historical-smoke-20260812T083943290963Z
```

Target halt:

```text
business_date = 2023-06-12
job = sell_planning
exit_code = 20
reason = ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
```

## Primary Judgment

`PHASE29_L21T_R_NO_SELL_CONTINUATION_DEFECT_RESERVATION_SEMANTIC_DEFECT_CONFIRMED_AUDIT_COMPLETE`

Required judgments:

```text
SELL_CONTINUATION_DEFECT_CONFIRMED = NO
SELL_CONTINUATION_REGRESSION_CONFIRMED = NO
SELL_CONTINUATION_CLASSIFICATION = INTENDED_NO_SIGNAL_BUY_REVIEW_PRESERVATION
Q1B_RESERVATION_AUTHORITY_VALID = YES
RESERVED_NOTIONAL_SELECTED_POSITION_AMOUNT_COMPARISON_VALID = NO
RESERVATION_SEMANTIC_DEFECT_CONFIRMED = YES
Q1B_PERFORMANCE_SIDE_EFFECT_CONFIRMED = YES
NEGATIVE_CASH_PROTECTION_STILL_REQUIRED = YES
Q2_TRANSACTIONALITY_MUST_BE_PRESERVED = YES
IMPLEMENTATION_REQUIRED = YES
RESUME_SAFE_NOW = NO
```

`IMPLEMENTATION_REQUIRED=YES` is for the MARKET BUY reservation semantic defect,
not for BUY/SELL continuation composition.

## Read-Only Evidence

### Run State

`reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/run_state.json`
shows:

```text
status = HALT
next_job = 2023-06-12:sell_planning
halted_at.business_date = 2023-06-12
halted_at.job = sell_planning
halted_at.exit_code = 20
completed last business day = 2023-06-09
```

The run had already passed the Q3B scoped replay for 2023-06-08 and then
continued through 2023-06-09.  No resume was executed by this audit.

### Current Pending Before SELL Planning

`.runtime/pending_order_plan/pending_order_plan.json` and
`reports/.../daily/2023-06-12/sell_planning/pre_sell_pending_snapshot_evidence.json`
show one same-day BUY pending:

```text
pending_plan_id = pending-strategy-plan-historical-2023-06-12-c5095866647c8ae8
state = REVIEW_REQUIRED
plan_created_date = 2023-06-12
target_session_date = 2023-06-12
read_classification = VALID
consume.consumed = false
review_scope = BUY_ITEM_SCOPED_REVIEW
sell_continuation_allowed = true
approved_item_ids = []
approved_buy_item_ids = []
approved_sell_item_ids = []
review_required_buy_item_ids = [strategy-333b4929b4bedbe3e52d]
```

The BUY item:

```text
pending_item_id = strategy-333b4929b4bedbe3e52d
symbol = 59550
side = BUY
source_decision_type = BUY_NEW
quantity = 1000
state = REVIEW_REQUIRED
approved = false
capital_allocation_status = APPROVED
quantity_status = RESOLVED_EXECUTABLE
feasibility_status = REVIEW_REQUIRED
batch_submit_status = ITEM_REVIEW_REQUIRED
item_review_reason = reserved notional exceeds selected_position_amount
reservation_price_type = market_buy_stop_high_cash_reservation
reservation_price = 152.0
reserved_notional = 152000.0
estimated_price = 108.0
estimated_amount = 108000.0
selected_position_amount = 115253.75
```

The payload-level reason for `active_buy_missing` is therefore precise:
`read_active_buy_pending()` requires a positive BUY item whose item id is present
in top-level `approved_item_ids`.  The only BUY item is valid as a same-day
pending record, but it is deliberately item-scoped review and unapproved.  It is
not an active approved BUY.

### SELL Planning Signal

SELL Planning did not produce an executable SELL/REDUCE/EXIT on 2023-06-12.

`.runtime/runtime_state/sell_pipeline/2023-06-12/order_plan.json`:

```text
status = NO_ACTION
reason = NO_SIGNAL:exit_ai_no_sell_signal
items = []
```

`.runtime/runtime_state/sell_pipeline/2023-06-12/approval_artifact.json`:

```text
status = NO_SIGNAL
reason = NO_SIGNAL:exit_ai_no_sell_signal
```

Position management evidence:

```text
pm_review_required = false
decisions = ADD: 1, HOLD: 2, REDUCE: 0, EXIT: 0
ADD symbol = 94320
HOLD symbols = 21340, 76470
```

The sell runtime manifest also recorded:

```text
final_safety_status = READY
safety_block_buy = false
safety_block_sell = false
safety_block_submit = false
safety_halt_runtime = false
pm_review_required = false
runtime_state_safety_state = BUY_REVIEW_REQUIRED
```

## BUY Review / SELL Continuation Finding

The 2023-06-12 halt is not a SELL continuation composition defect.

For executable SELL, L21T-M added the item-scoped review composition path:
`compose_with_buy_item_scoped_review_pending()` preserves the reviewed BUY,
approves only the SELL item ids, and emits a shared pending plan.  That path is
only relevant when SELL Planning has executable SELL items.

For no-signal SELL, `_write_no_signal_pending()` preserves the current active
pending and returns REVIEW_REQUIRED with
`PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL` semantics when the current pending is not
an approved active BUY but must not be overwritten.  This behavior is covered by
the L21T-M focused regression
`test_phase29_l21t_m_buy_item_scoped_review_no_signal_preserves_review_pending`.

The observed 2023-06-12 shape matches that expected no-signal preservation:

```text
SELL has no executable item
BUY pending remains current
BUY item remains REVIEW_REQUIRED
Submit is not reached because BUY review remains unresolved
```

`sell_continuation_allowed=true` means SELL may continue past a BUY item-scoped
review if a valid SELL exists.  It does not mean SELL Planning should convert a
no-signal day with an unresolved BUY review into PASS.

## MARKET BUY Reservation Semantics Finding

Q1B's MARKET BUY reservation authority is valid and must be preserved.

The Q1B repair correctly moved MARKET BUY cash reservation to a stop-high
buying-power authority so that pre-commit feasibility can reserve enough cash
for execution-price uncertainty.  This protects Production/Demo/Historical
common runtime from the 2023-06-08 negative-cash class.  Q2 transactional
commit must also remain intact so failed execution projections do not leave
Ledger and Current partially diverged.

The defect is narrower: Planning Submit feasibility currently compares the
broker cash reservation amount directly against Strategy
`selected_position_amount` and raises:

```text
reserved notional exceeds selected_position_amount
```

For 2023-06-12:

```text
Strategy selected_position_amount = 115253.75
lot/reference notional = 108000.0
reserved_notional = 152000.0
cash / buying_power = 609670.0
available_cash_after_target = 609670.0
```

The Strategy-sized trade fits the Strategy selected notional:

```text
108000.0 <= 115253.75
```

The Q1B reservation also fits cash authority:

```text
152000.0 <= 609670.0
```

The only observed blocker is the cross-authority comparison:

```text
152000.0 > 115253.75
```

That comparison conflates two different semantics:

| Field | Authority | Meaning |
| --- | --- | --- |
| `selected_position_amount` | Strategy / position sizing | desired or authorized position notional at the planning/reference basis |
| `reserved_notional` | Broker reservation / pre-commit cash safety | worst-case MARKET BUY cash hold using stop-high reservation price |

`reserved_notional` is valid for cash, buying power, exposure, and aggregate
pre-commit affordability.  It is not valid as a direct substitute for Strategy
selected position notional unless Strategy explicitly emits a
reservation-inclusive cap.

## Performance Side Effect

The read-only scan of the target run artifacts from 2023-04-03 through
2023-06-12 found:

```text
MARKET_BUY_ORDER_PLAN_COUNT = 29
MARKET_BUY_WITH_RESERVED_NOTIONAL = 7
BUY_EXECUTIONS_COUNT = 19
```

The Q1B-era evidence contains repeated `reserved notional exceeds
selected_position_amount` review reasons on 2023-06-08 and 2023-06-12
manifests.  The 2023-06-12 item is the current decisive halt item.  Earlier
manifest occurrences include replayed or preserved pending payloads, so they
should not be counted as independent executions blocked without item-level
deduplication.

Performance interpretation:

```text
47BD performance observation = valid observation
Strategy improvement = not proven by this audit
Reservation semantic side effect = confirmed
```

The side effect is that Q1B's conservative stop-high reservation can turn
otherwise Strategy-feasible MARKET BUYs into BUY_ITEM_SCOPED_REVIEW when the
reference/lot notional fits Strategy sizing but the temporary reservation hold
exceeds Strategy sizing.  This can suppress capital deployment without being a
Strategy quality improvement.

This finding does not justify weakening negative-cash protection.

## Design Repair Recommendation

Repair should be production-common and minimal:

1. Keep Q1B stop-high `reserved_notional` for cash, buying power,
   available-cash-after-target, exposure, and execution pre-commit checks.
2. Stop using `reserved_notional > selected_position_amount` as the Strategy
   position-sizing violation.
3. Compare Strategy sizing against the Strategy/reference executable notional
   already represented by `estimated_amount`, `lot_adjusted_notional`, or the
   resolved position sizing authority notional.
4. If a worst-case spend cap is desired, add an explicit authority field such as
   `reservation_inclusive_position_cap`; do not overload
   `selected_position_amount`.
5. Preserve BUY_ITEM_SCOPED_REVIEW fail-closed behavior for genuinely
   unapproved, stale, consumed, date-mismatched, cash-insufficient, or
   buying-power-insufficient pending plans.

Regression shape to add in the implementation phase:

```text
2023-06-12 semantic fixture:
  selected_position_amount = 115253.75
  reference/lot notional = 108000.0
  reserved_notional = 152000.0
  cash = 609670.0

Expected:
  position sizing PASS
  reservation cash feasibility PASS
  no BUY_ITEM_SCOPED_REVIEW solely from reserved_notional > selected_position_amount
```

Additional regression must keep a cash-insufficient MARKET BUY fixture
REVIEW_REQUIRED under the same Q1B reservation authority.

## Resume Decision

`RESUME_SAFE_NOW = NO`.

The run is halted at 2023-06-12 sell_planning and the halt reflects an unresolved
BUY review caused by the reservation semantic defect.  Resuming before the
semantic repair would preserve the same unresolved pending state or require
manual/operator intervention outside the verified authority chain.

