# Phase31-F1X - Post-F1W Actual Resume Submit Terminalization Audit

## PRIMARY_JUDGMENT

PHASE31_F1X_F1W_ACTUAL_REPAIR_PARTIAL_INTEGRATION_DEFECT_REMAINS

## TARGET_RUN_ID

runtime-test-historical-extended-smoke-20260821T050423121340Z

## LATEST_SUBMIT_REASON

`submit completed with rejected/unknown/blocked items`

## LATEST_SUBMIT_STATUS

REVIEW_REQUIRED

Latest submit artifact:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/submit/runtime_manifest.json`

Latest submit counters:

- LATEST_BLOCKED_COUNT = 4
- LATEST_SUBMITTED_COUNT = 1
- LATEST_ACCEPTED_COUNT = 1
- LATEST_EXIT_CODE = 20

The final REVIEW_REQUIRED is not caused only by 76920. Additional defects are present:

- 34940 SELL: adapter preflight HALT, `missing or non-unique target session OHLCV row`
- 82560 SELL: BLOCKED, `sell quantity exceeds broker available quantity`
- 37790 SELL: BLOCKED, `sell quantity exceeds broker available quantity`
- 45910 SELL: BLOCKED, `sell quantity exceeds broker available quantity`
- 76920 BUY: valid item-scoped review, `corporate_action_event_not_resolved`, not submitted

## FOUR_EXISTING_ORDER_RECONCILIATION

FAIL

| symbol | preexisting_order_found | reconciled | new_adapter_submit_called | duplicate_created |
|---|---|---|---|---|
| 61440 | YES | YES | NO | NO |
| 82560 | YES | NO | NO | NO |
| 37790 | YES | NO | NO | NO |
| 45910 | YES | NO | NO | NO |

All four preexisting accepted orders still exist in `.runtime/persistent_ledger/orders.jsonl` and `.runtime/runtime_state/historical_broker/2022-12-08/`. F1W recognized only 61440. The three preexisting SELL side effects were not reconciled before sell-available-quantity guard evaluation.

## 34940_ACTUAL_DISPOSITION

STILL_MISSING_DEFECT

34940 evidence:

- 34940_EXISTING_SIDE_EFFECT_BEFORE_RETRY = NO
- 34940_SUBMIT_ATTEMPTED = PREFLIGHT_ONLY
- 34940_ORDER_MATERIALIZED = NO
- 34940_LEDGER_ORDER_ID = NOT_AVAILABLE
- 34940_PENDING_ITEM_TERMINAL_STATE = APPROVED
- 34940_LATEST_PREFLIGHT_STATUS = HALT
- 34940_LATEST_REASON = `missing or non-unique target session OHLCV row`

The item did not duplicate, but it also did not submit exactly once and did not become terminal. It remains an approved/submittable Pending item with no accepted side effect.

## 76920_REVIEW_PRESERVED

YES

76920 BUY remains `REVIEW_REQUIRED`, `NOT_SUBMITTED`, with reason `corporate_action_event_not_resolved`.

## SUBMITTED_IDS_NOW_PERSISTED

PARTIAL

Active Pending:

- `pending.state` = REVIEW_REQUIRED
- `pending.consume.consumed` = false
- `pending.consume.submitted_order_ids` = [`5b3e3b80c7cbbadb83008b168ee1917f4e83f4daaa347bf7cc30e39c928404bc`]

Only 61440 is persisted. Existing accepted orders for 82560, 37790, and 45910 are absent from the Pending consume IDs.

## LEDGER_IDS_NOW_PERSISTED

PARTIAL

Active Pending:

- `pending.consume.ledger_order_record_ids` = [`ledger-order-submit-9118df439e89f7b4`]

Only 61440 is persisted. Existing accepted ledger rows for 82560, 37790, and 45910 are absent from the Pending consume IDs.

## PENDING_ITEM_STATES

| symbol | side | quantity | pending_item_id | state | approved | latest disposition |
|---|---|---:|---|---|---|---|
| 61440 | BUY | 100 | strategy-9242cb1dda97a6433677 | APPROVED | true | reconciled existing order, ID persisted |
| 76920 | BUY | 200 | strategy-dae988dcba6a12b37f97 | REVIEW_REQUIRED | false | preserved review, not submitted |
| 34940 | SELL | 100 | strategy-5c7d2975b463ced32e60 | APPROVED | true | preflight HALT, still no order |
| 82560 | SELL | 300 | strategy-8f700934de4464ffa4d5 | APPROVED | true | existing order not reconciled, blocked by available quantity |
| 37790 | SELL | 100 | strategy-d869e35933dcd6215538 | APPROVED | true | existing order not reconciled, blocked by available quantity |
| 45910 | SELL | 100 | strategy-72c08989f99bb27f815a | APPROVED | true | existing order not reconciled, blocked by available quantity |

## ACTUAL_ACCEPTED_ORDER_SYMBOL_SET

[`37790`, `45910`, `61440`, `82560`]

## EXPECTED_ACCEPTED_ORDER_SYMBOL_SET

[`34940`, `37790`, `45910`, `61440`, `82560`]

## SET_EQUALITY

FAIL

34940 is still missing from accepted order side effects.

## DUPLICATE_ORDER_COUNT

0

## DUPLICATE_PENDING_ITEM_SUBMISSION_COUNT

0

No duplicate accepted order IDs or duplicate accepted pending-item submissions were found for the 2022-12-08 Pending plan.

## F1W_ACTUAL_REPAIR_ACTIVATED

PARTIAL

Evidence of activation:

- 61440 item result: `preflight_status = RECONCILED`
- 61440 reason: `existing_item_submission_reconciled`
- 61440 idempotency status: `PASS_RECONCILED_EXISTING_SUBMISSION`
- Pending consume IDs now include the 61440 order/ledger IDs.

Evidence repair did not fully activate:

- 82560, 37790, 45910 existing accepted orders were not reconciled.
- 34940 remains missing and non-terminal.
- Pending consume IDs are partial, not equal to the accepted executable side-effect set.

## ITEM_SCOPED_REVIEW_RUNTIME_CONTINUATION_CONTRACT

CONTINUE

Current Submit contract indicates that item-scoped reviewed BUY does not by itself halt when approved executable items are successfully submitted/reconciled and no other item is blocked/rejected/unknown:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` sets `status = PASS` and reason `submitted_with_reviewed_buy_items_not_submitted` when `unsubmitted_review_present` exists without blocked/rejected/unknown items.
- Existing regression tests assert this PASS behavior for BUY_ITEM_SCOPED_REVIEW partial submit with approved BUY/SELL continuation.

Therefore the latest HALT is not the intended terminal status for a clean item-scoped review continuation. It is caused by unresolved integration defects in the actual side-effect reconciliation / 34940 materialization path.

## ROOT_CAUSE_CLASSIFICATION

F1W_INTEGRATION_STILL_DEFECTIVE

Equivalent F1X-8 choice: A.

The valid 76920 corporate-action review is preserved, but it is not the sole reason Runtime still HALTed. The actual latest Submit result includes four blocked items and only one reconciled submitted item.

## INTEGRATION_DEFECT_REMAINS

YES

Remaining defects:

1. Existing accepted SELL side effects for 82560, 37790, and 45910 are not reconciled before sell available-quantity revalidation, so they become false blockers.
2. 34940 still lacks accepted broker/ledger side effect and remains `APPROVED`, not terminal.
3. Pending consume submitted/ledger IDs are only partial.

## IMPLEMENTATION_CHANGED

NO

## FRESH_RUN_EXECUTED

NO

## RESUME_EXECUTED_BY_CODEX

NO

## REPLAY_EXECUTED

NO

## LONG_HISTORICAL_EXECUTED

NO

## NEXT_ACTION_CLASSIFICATION

SCOPED_RECOVERY_REQUIRED

## NEXT_TASK_RECOMMENDATION

Do not retry resume before F1X is resolved.

Recommended next task: focused F1Y repair/audit for actual-artifact idempotent recovery ordering:

- Reconcile existing accepted item side effects before sell available-quantity and broker preflight checks.
- Persist all reconciled accepted order/ledger IDs for 61440, 82560, 37790, and 45910.
- Resolve 34940 as either `SUBMITTED_EXACTLY_ONCE` if the canonical Historical submit input can be validated, or terminal fail-closed with explicit non-retryable evidence if OHLCV authority remains missing/non-unique.
- Preserve 76920 as item-scoped `REVIEW_REQUIRED` / not submitted.

Do not weaken corporate-action quarantine and do not mark UNKNOWN/REVIEW_REQUIRED as SAFE.
