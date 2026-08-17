# Phase30-AK9R8 - Next-Day Residual BUY Review Pending Expiration Repair

## Scope

Task ID: `Phase30-AK9R8`

Type: `FOCUSED_PRODUCTION_COMMON_PENDING_LIFECYCLE_REPAIR`

Authorized implementation:

```text
next-business-day expiration / terminalization of stale partial-submitted
residual BUY_ITEM_SCOPED_REVIEW Pending
```

No Strategy, Candidate, PC, PS, sizing, ranking, Submit quantity, cash rule,
Safety weakening, fresh Historical, or long Historical change was performed.

## Primary Judgment

```text
NEXT_DAY_RESIDUAL_BUY_REVIEW_EXPIRATION_IMPLEMENTED = YES
RESIDUAL_REVIEW_EXPIRATION_EVIDENCE_COMPLETE = YES
STALE_RESIDUAL_PENDING_TERMINAL_STATE = EXPIRED
STALE_RESIDUAL_PENDING_NO_LONGER_ACTIVE = YES
```

Phase30-AK9R8 repairs the Phase30-AK9R7 confirmed
`NEXT_DAY_RESIDUAL_PENDING_LIFECYCLE_GAP`. A partial-submitted
`BUY_ITEM_SCOPED_REVIEW` pending can remain visible on the same business day,
but once `target_session_date < current business date`, stale residual reviewed
BUY authority is explicitly terminalized as `EXPIRED`.

## Implemented Contract

The new Pending lifecycle authority applies only when all are true:

```text
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
target_session_date < business_date
approved_buy_item_ids exists
review_required_buy_item_ids exists
approved and review ids are disjoint
review_required_sell_item_ids is empty
all items are BUY
approved BUY items are known and state = CONSUMED
reviewed BUY items are known and state = REVIEW_REQUIRED
reviewed BUY items are not approved
reviewed BUY items have no submit/fill evidence
whole pending is not already consumed
```

If valid, Pending lifecycle writes an explicit history record and empties the
active slot:

```text
transition_reason = STALE_NEXT_DAY_RESIDUAL_BUY_REVIEW_EXPIRED
new_state = EXPIRED
active_pending = false
```

The history and manifest carry:

```text
original pending_plan_id
original target_session_date
expiration business date
previous state
terminal state
consumed BUY ids
expired residual review BUY ids
expired residual review BUY symbols
original review reason
stale_residual_buy_review_expiration authority evidence
```

## Preservation

```text
REVIEWED_BUY_NOT_AUTO_APPROVED = YES
REVIEWED_BUY_NOT_AUTO_SUBMITTED = YES
REVIEWED_BUY_HISTORY_PRESERVED = YES
CONSUMED_BUY_AND_CURRENT_STATE_PRESERVED = YES
NEXT_DAY_DATA_READINESS_STALE_PENDING_BLOCK_REMOVED = YES
NEW_DAY_BUY_REQUIRES_FRESH_AUTHORITY = YES
MANDATORY_SELL_INDEPENDENCE_PRESERVED = YES
SAME_DAY_RESIDUAL_REVIEW_VISIBILITY_PRESERVED = YES
NON_TARGET_REVIEW_PENDING_FAIL_CLOSED_PRESERVED = YES
```

Same-day partial residual review remains visible and is not expired by this
repair. Reviewed SELL presence, unconsumed approved BUY, or reviewed BUY submit
evidence all remain fail-closed.

## Lifecycle Documentation

```text
PARTIAL_APPROVED_WITH_REVIEW
-> approved subset SUBMITTED
-> approved subset CONSUMED
-> residual review remains REVIEW_REQUIRED same-day
-> Current Valuation
-> Day Completion
-> next-business-day EXPIRED
```

This is now covered by focused sentinels.

## Regression Sentinels

Added AK9R8 focused sentinels:

```text
next-day partial-submitted residual BUY review expires
Data Readiness becomes ready after residual review expiration
same-day residual review visibility is preserved
reviewed SELL exists -> fail closed
approved BUY not consumed -> fail closed
reviewed BUY submitted -> fail closed
```

Existing sentinels preserve:

```text
normal stale APPROVED expiration
all-reviewed BUY_ITEM_SCOPED_REVIEW no-submission terminalization
generic REVIEW_REQUIRED fail-closed behavior
unknown submit risk fail-closed behavior
normal fully consumed / terminal pending behavior
```

## Production Integrity

```text
AK9R6_CURRENT_VALUATION_CONTINUATION_PRESERVED = YES
AK9R4_SELL_PLANNING_COMPATIBILITY_PRESERVED = YES
AK9R1_PARTIAL_SUBMISSION_PRESERVED = YES
AK9R1B_CANONICAL_QUANTITY_PRECEDENCE_PRESERVED = YES
AK8R_BUY_SELL_INDEPENDENCE_PRESERVED = YES
CURRENT_STATE_CONTINUITY_PRESERVED = YES
POSITION_CAMPAIGN_CONTINUITY_PRESERVED = YES
TEMPORAL_FAIL_CLOSED_FOR_INVALID_PENDING_PRESERVED = YES
```

## Tests

```text
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'ak9r8 or stale_approved_pending_expires or data_readiness_pending_ready_after_expiration or buy_item_scoped_review'
10 passed, 22 deselected

python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
32 passed

python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py
15 passed

python3 -m pytest tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'ak9r4 or buy_item_scoped or mandatory'
3 passed, 14 deselected

python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -k 'ak9r1 or ak8r or buy_item_scoped_review'
7 passed, 19 deselected

python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py -k 'ak9r1b or ak3r2c1 or buy or sell or mandatory'
17 passed, 18 deselected

python3 -m pytest tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py -q
35 passed

python3 -m pytest tests/runtime_v2 -k 'mandatory_sell or buy_sell_independence or ak8r'
1 passed, 1620 deselected

env PYTHONPYCACHEPREFIX=/private/tmp/pycache-ak9r8 python3 -m compileall src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
PASS
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK9R9 - Pending Lifecycle End-to-End Consolidated Regression
```
