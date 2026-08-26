# Phase31-F2A — 2022-12-16 Fresh Long-Horizon Submit HALT Actual-Artifact Root-Cause Audit

## PRIMARY_JUDGMENT

PHASE31_F2A_FRESH_PATH_BUY_ITEM_SCOPED_REVIEW_PLUS_TERMINAL_NOT_EXECUTABLE_ZERO_SUBMISSION_AGGREGATE_GAP

## Scope

This is a READ-ONLY actual-artifact root-cause audit. No implementation, fresh-run, resume, replay, or long Historical execution was performed.

Target run:

```text
runtime-test-historical-extended-smoke-20260821T123424251236Z
```

Evidence root:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T123424251236Z
```

Halt boundary:

```text
2022-12-16:submit
```

## Exact Submit Result

Submit artifact:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T123424251236Z/daily/2022-12-16/submit/runtime_manifest.json
```

Observed top-level submit result:

```text
SUBMIT_STATUS = REVIEW_REQUIRED
SUBMIT_REASON = submit blocked before broker boundary; manual review required
SUBMIT_EXIT_CODE = 20
BLOCKED_COUNT = 0
REVIEWED_COUNT = 1
REJECTED_COUNT = 0
SUBMITTED_COUNT = 0
SUBMIT_ACTION = NO_SUBMIT_ATTEMPTED
broker_write = false
external_delivery = false
raw_request_saved = false
raw_response_saved = false
```

The run-level wrapper halted with:

```text
fresh_run_summary.status = HALT
fresh_run_summary.exit_code = 30
run_state.status = HALT
run_state.next_job = 2022-12-16:submit
```

## Pending Composition

The exact Pending presented to Submit:

```text
PENDING_PLAN_ID = pending-strategy-plan-historical-2022-12-16-00c221725547446d
PENDING_PLAN_STATE = REVIEW_REQUIRED
PENDING_ITEM_COUNT = 2
BUY_ITEM_COUNT = 1
SELL_ITEM_COUNT = 1
review_scope = BUY_ITEM_SCOPED_REVIEW
review_scope_reason = corporate_action_event_not_resolved
```

Per-item evidence:

| item_id | symbol | side | qty | state | approved | decision | feasibility | review reason | current / quantity authority | existing order identity |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| `strategy-b6cc92107e94543df99d` | 76920 | BUY | 200 | REVIEW_REQUIRED | false | BUY_NEW | REVIEW_REQUIRED | corporate_action_event_not_resolved | quantity RESOLVED_EXECUTABLE; cash authority PASS | none |
| `strategy-411fa4d0435aaa88ef89` | 41020 | SELL | 100 | APPROVED at Pending input; terminal NOT_EXECUTABLE at Submit item result | true at Pending input | SELL_EXIT | PASS at Pending input; NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE at Submit item result | EXECUTION_AUTHORITY_UNAVAILABLE at Submit item result | current authority PASS; current quantity 100; broker available quantity 100; sell quantity guard PASS | none |

The canonical Pending review scope authority inside Submit reported:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
structural_validity = PASS
batch_blocked = false
reviewed_buy_item_ids = [strategy-b6cc92107e94543df99d]
reviewed_sell_item_ids = []
executable_sell_item_ids = [strategy-411fa4d0435aaa88ef89]
partial_submit_allowed = true
sell_continuation_allowed = true
```

## Side-Effect Audit

No 2022-12-16 order side effect was created before HALT.

Submit stage details:

```text
submitted_order_ids = []
ledger_order_record_ids = []
submitted_symbols = []
accepted_count = 0
submitted_count = 0
unknown_count = 0
pending_consumed = false
```

The 2022-12-16 run directory has no execution directory and no current valuation refresh directory, consistent with Submit stopping before broker/order/fill mutation.

```text
PREEXISTING_ACCEPTED_ORDER_COUNT = 0
NEW_ACCEPTED_ORDER_COUNT_BEFORE_HALT = 0
DUPLICATE_ORDER_COUNT = 0
```

## Reconciliation / Idempotency

There was no preexisting accepted 2022-12-16 side effect to reconcile, and no new side effect was created. F1W/F1Y duplicate prevention was therefore not exercised by this actual halt.

```text
EXISTING_SIDE_EFFECT_RECONCILIATION = NOT_APPLICABLE
RETRY_DUPLICATE_RISK = NO
```

## NOT_EXECUTABLE Handling

41020 SELL became a Submit item-level terminal non-executable outcome:

```text
symbol = 41020
side = SELL
quantity = 100
preflight_status = NOT_EXECUTABLE
adapter_preflight_status = HALT
adapter_preflight_reason = missing or non-unique target session OHLCV row
guard_decision = NOT_EXECUTABLE
guard_reason = EXECUTION_AUTHORITY_UNAVAILABLE
execution_feasibility_status = NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE
authority_type = ITEM_EXECUTION_AUTHORITY_UNAVAILABLE_TERMINAL
adapter_submit_called = false
order_created = false
ledger_order_created = false
broker_side_effect_created = false
cash_mutated = false
position_mutated = false
retry_eligible_same_day = false
next_day_re_evaluation_required = true
```

Item-level safety is correct: no broker, order, ledger, cash, or position side effect occurred.

The contract gap is at the aggregate Submit disposition: with 76920 correctly deferred as BUY item-scoped review and 41020 safely terminalized as NOT_EXECUTABLE, there was no blocked, rejected, unknown, or ambiguous side effect item remaining. Existing F1Z2/F1Z3 contract language expects continuation PASS when only reviewed/deferred and terminal non-executable items remain. This actual fresh-run path instead returned `REVIEW_REQUIRED`.

```text
NOT_EXECUTABLE_CONTRACT_STATUS = FAIL
```

## Genuine Review Scope

76920 BUY is a genuine item-scoped review:

```text
symbol = 76920
side = BUY
quantity = 200
preflight_status = REVIEW_REQUIRED
authority_type = BUY_ITEM_SCOPED_REVIEW_ITEM_NOT_SUBMITTED
review_scope = BUY_ITEM_SCOPED_REVIEW
review_reason = corporate_action_event_not_resolved
blocked_other_items = false
```

This is not a batch-level review, not reviewed SELL, and not malformed/unknown side-effect evidence. The no-order authority explicitly reported:

```text
status = PASS
authority_type = BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION
item_review_does_not_escalate_to_batch_failure = true
true_batch_failure_atomicity_preserved = true
reviewed_buy_submitted = false
```

Expected runtime disposition under the existing continuation contract is to defer the reviewed BUY and continue if the remaining item is terminal or safely submitted. The actual run halted because the remaining approved SELL became safely terminal NOT_EXECUTABLE and there were zero accepted submissions.

```text
REVIEW_SCOPE_CLASSIFICATION = BUY_ITEM_SCOPED_REVIEW_WITH_TERMINAL_NOT_EXECUTABLE_SELL
REVIEW_RUNTIME_DISPOSITION = CONTINUE_ALLOWED
```

## Quantity / Cash / Position Authority

BUY 76920:

```text
planning_status = PASS
planning_intent = BUY_NEW
quantity_status = RESOLVED_EXECUTABLE
selected_quantity = 200
estimated_amount = 29260
cash_exposure_authority_status = PASS
position_count_authority_status = PASS
item review reason = corporate_action_event_not_resolved
```

SELL 41020:

```text
planning_status = PASS
planning_intent = SELL_EXIT
quantity_status = RESOLVED_EXECUTABLE
selected_quantity = 100
current_authority_status = PASS
current_authority_winner = persistent_ledger_state
current_quantity = 100
broker_available_quantity = 100
sell_quantity_guard_status = PASS
estimated_amount = 130500
```

Aggregate submit feasibility for the executable SELL item:

```text
status = PASS
reason = planning_submit_feasibility_pass
current_total_equity = 1092400
cash = 102860
current_exposure = 989540
source_selection_reason = explicit_persistent_ledger_state_current_authority
```

Therefore quantity, cash, and position authority are not the root cause.

```text
BUY_QUANTITY_STATUS = PASS
SELL_QUANTITY_STATUS = PASS
CASH_AUTHORITY_STATUS = PASS
POSITION_AUTHORITY_STATUS = PASS
```

## Corporate Action

Corporate-action safety is involved for 76920 only:

```text
symbol = 76920
reason = corporate_action_event_not_resolved
guard_class = DATA_INTEGRITY_SAFETY
guard_code = CORPORATE_ACTION_UNRESOLVED
precomputable_executable_membership_guard_status = REVIEW_REQUIRED
violated_policy = historical_corporate_action_symbol_quarantine
```

This behavior is expected as a BUY item-scoped quarantine. It should not submit 76920 and should not escalate to batch failure when the scope authority remains structurally valid and no reviewed SELL exists.

41020 SELL had corporate-action adjustment authority PASS at Submit.

```text
CORPORATE_ACTION_INVOLVED = YES
```

## Execution Price Authority

One item lacks canonical same-day execution authority:

```text
EXECUTION_AUTHORITY_UNAVAILABLE_COUNT = 1
symbol = 41020
```

The F1Z2 item-level safety shape is present:

```text
NOT_EXECUTABLE
no order
no fill
no cash mutation
no position mutation
retry_eligible_same_day = false
next_day_re_evaluation_required = true
```

The missing piece is aggregate Submit continuation for the zero-submission terminal/deferred batch.

## Relation To Prior F1 Repairs

This is not a recurrence of the earlier resume-only stale Pending lifecycle defect. It occurred on a clean fresh long-horizon run with current code.

It is also not an existing-order reconciliation/idempotency problem: there were no 2022-12-16 accepted side effects.

The closest prior contract is F1Z2/F1Z3:

```text
reviewed BUY not submitted
+ terminal NOT_EXECUTABLE item not submitted
-> Submit continuation PASS when no blocked / rejected / unknown execution item remains
```

F2A exposes a new generic gap in the aggregate Submit finalization path when the only executable candidate becomes terminal NOT_EXECUTABLE, leaving `submitted_count = 0`.

```text
RELATION_TO_PRIOR_F1_REPAIRS = NEWLY_EXPOSED_GENERIC_GAP
FRESH_PATH_DEFECT_CONFIRMED = YES
```

## Performance Evidence Safety

The run completed through 2022-12-15. The 2022-12-15 day has:

```text
day_completion.status = PASS
2022-12-15 current_valuation_refresh exit_code = 0
2022-12-15 runtime_state_refresh exit_code = 0
```

The 2022-12-16 day has market refresh, data readiness, morning, and sell planning completed, but stopped at Submit. It has no 2022-12-16 execution or current valuation refresh artifact.

```text
PERFORMANCE_EVIDENCE_VALID_THROUGH = 2022-12-15
PERFORMANCE_EVIDENCE_QUARANTINE_REQUIRED = NO
```

Use performance evidence through 2022-12-15 only; do not include 2022-12-16 as a completed performance day.

## Repair Gate

The defect is generic and repairable without symbol/date/reason-specific branching.

Candidate repair direction:

```text
When Submit item outcomes consist only of:
- reviewed BUY item-scoped deferred items that must not submit
- safely terminal NOT_EXECUTABLE items with no side effects
- no blocked / rejected / unknown / ambiguous item

then aggregate Submit should produce a terminal continuation PASS/no-op outcome rather than REVIEW_REQUIRED, and persist canonical item terminal/deferred state so downstream lifecycle consumers do not re-open stale executable authority.
```

Do not implement this in F2A.

```text
INTEGRATION_DEFECT_CONFIRMED = YES
REPAIR_CANDIDATE = YES
GENERIC_REPAIR_POSSIBLE = YES
```

## Required Output

PRIMARY_JUDGMENT = PHASE31_F2A_FRESH_PATH_BUY_ITEM_SCOPED_REVIEW_PLUS_TERMINAL_NOT_EXECUTABLE_ZERO_SUBMISSION_AGGREGATE_GAP

TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260821T123424251236Z

HALT_DATE = 2022-12-16

SUBMIT_STATUS = REVIEW_REQUIRED

SUBMIT_REASON = submit blocked before broker boundary; manual review required

HALT_SYMBOLS = 76920, 41020

FIRST_FAILED_GUARD = 41020 SELL submit_adapter_preflight -> NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE / EXECUTION_AUTHORITY_UNAVAILABLE

PENDING_PLAN_ID = pending-strategy-plan-historical-2022-12-16-00c221725547446d

PENDING_PLAN_STATE = REVIEW_REQUIRED

PENDING_ITEM_COUNT = 2

BUY_ITEM_COUNT = 1

SELL_ITEM_COUNT = 1

PREEXISTING_ACCEPTED_ORDER_COUNT = 0

NEW_ACCEPTED_ORDER_COUNT_BEFORE_HALT = 0

DUPLICATE_ORDER_COUNT = 0

EXISTING_SIDE_EFFECT_RECONCILIATION = NOT_APPLICABLE

RETRY_DUPLICATE_RISK = NO

NOT_EXECUTABLE_CONTRACT_STATUS = FAIL

REVIEW_SCOPE_CLASSIFICATION = BUY_ITEM_SCOPED_REVIEW_WITH_TERMINAL_NOT_EXECUTABLE_SELL

REVIEW_RUNTIME_DISPOSITION = CONTINUE_ALLOWED

BUY_QUANTITY_STATUS = PASS

SELL_QUANTITY_STATUS = PASS

CASH_AUTHORITY_STATUS = PASS

POSITION_AUTHORITY_STATUS = PASS

CORPORATE_ACTION_INVOLVED = YES

EXECUTION_AUTHORITY_UNAVAILABLE_COUNT = 1

RELATION_TO_PRIOR_F1_REPAIRS = NEWLY_EXPOSED_GENERIC_GAP

FRESH_PATH_DEFECT_CONFIRMED = YES

PERFORMANCE_EVIDENCE_VALID_THROUGH = 2022-12-15

PERFORMANCE_EVIDENCE_QUARANTINE_REQUIRED = NO

INTEGRATION_DEFECT_CONFIRMED = YES

REPAIR_CANDIDATE = YES

GENERIC_REPAIR_POSSIBLE = YES

IMPLEMENTATION_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION = Do not resume before F2A is resolved. Implement a generic aggregate Submit terminal/no-op continuation repair for BUY-item-scoped reviewed deferred items plus safely terminal NOT_EXECUTABLE items with zero accepted submissions, then run focused production acceptance.
