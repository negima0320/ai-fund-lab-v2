# Phase30-AK9R25 - Submit Data Readiness BUY_ITEM_SCOPED_REVIEW Temporal Authority Repair

## Primary Judgment

`SUBMIT_DATA_READINESS_BUY_ITEM_SCOPED_REVIEW_TEMPORAL_AUTHORITY_REPAIRED`

Phase30-AK9R25 repaired the AK9R24 authority gap where a valid same-day `BUY_ITEM_SCOPED_REVIEW` pending plan was accepted by Sell Planning but rejected by Submit Data Readiness as a batch-level Historical Safety mismatch.

The repair preserves the core meaning:

```text
BUY_ITEM_SCOPED_REVIEW_IS_NOT_BATCH_FAILURE = YES
```

Reviewed BUY items remain fail-closed and are not submitted. Approved executable BUY/SELL items can proceed when their own feasibility and safety evidence pass.

## Repair Summary

Implemented focused Production-common changes in:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
src/ai_fund_lab_v2/runtime_v2/submit/guards.py
src/ai_fund_lab_v2/runtime_v2/pending/consume.py
```

Data Readiness now permits the AK9R24 shape at `readiness_scope=submit`:

```text
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
sell_continuation_allowed = true
approved BUY present
approved SELL may be present
reviewed BUY present
reviewed SELL absent
approved items have PASS submit feasibility
reviewed BUY is the only non-PASS item
```

The existing canonical Historical Safety temporal authority is reused. No Submit-only Historical authority was introduced.

Submit preflight and pending consume were aligned to the same item-scoped predicate so the real Submit pipeline can submit the approved executable subset after Data Readiness passes. This is not a Strategy, PC, PS, Cash, Safety, or cap change.

## AK9R24 Reproduction / Positive Sentinel

`AK9R24_SUBMIT_DATA_READINESS_FAILURE_REPRODUCED = YES`

The pre-repair failure class was reproduced by the AK9R24 evidence and encoded as focused sentinels:

- approved BUY `PASS`
- approved SELL `PASS`
- reviewed BUY `REVIEW_REQUIRED`
- reviewed SELL count `0`
- `review_scope = BUY_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed = true`

Post-repair:

```text
SUBMIT_DATA_READINESS_ITEM_SCOPED_REVIEW_SUPPORTED = YES
APPROVED_BUY_NOT_BLOCKED_BY_REVIEWED_BUY = YES
APPROVED_SELL_NOT_BLOCKED_BY_REVIEWED_BUY = YES
REVIEWED_BUY_REMAINS_FAIL_CLOSED = YES
AK9R24_EQUIVALENT_PARTIAL_SUBMIT_PASS = YES
```

The real Submit sentinel submits the approved BUY and SELL while leaving the reviewed BUY unsubmitted:

```text
submitted_symbols = 24350, 43760
reviewed_buy_symbol = 30410
reviewed_buy_not_submitted_reason = item_scoped_review_required
```

## Fail-Closed Preservation

The repair does not turn item-scoped review into a broad bypass.

Preserved fail-closed cases:

- reviewed SELL exists
- aggregate cash failure
- stale or malformed pending
- temporal authority mismatch
- Historical Safety mismatch
- quantity inconsistency
- invalid approval/review id overlap
- `sell_continuation_allowed=false`

Cash-specific boundary:

```text
CASH_FEASIBILITY_FAIL_CLOSED_PRESERVED = YES
AK3R2B_CASH_AUTHORITY_PRESERVED = YES
```

The AK9R24-style reviewed BUY may have a cash-like item review reason such as `reserved_cash`, but aggregate cash failure remains batch-level fail-closed.

## Cross-Repair Preservation

```text
AK9R21_SUBMIT_AUTHORITY_PRESERVED = YES
AK9R21_SYSTEM_REVIEW_REASON_RECURRENCE = NO
AK9R1_ITEM_SCOPED_PARTIAL_SUBMISSION_ACTION_EFFECTIVE = YES
AK8R_BUY_SELL_INDEPENDENCE_PRESERVED = YES
VALID_BUY_NOT_DROPPED_BY_SELL = YES
VALID_SELL_NOT_DROPPED_BY_BUY_REVIEW = YES
AK9R23_SELL_PLANNING_REPAIR_PRESERVED = YES
CROSS_REPAIR_INTERACTION_STATUS = PASS
```

## No Performance Tuning

```text
NEW_BUY_FILTER_CREATED = NO
NEW_SELL_FILTER_CREATED = NO
FORCED_BUY_CREATED = NO
FORCED_SELL_CREATED = NO
STRATEGY_CHANGED = NO
PC_CHANGED = NO
PS_CHANGED = NO
CAP_VALUES_CHANGED = NO
```

No Candidate, PM, Strategy, Portfolio Construction, Position Sizing, cap, threshold, or model behavior was changed.

## Tests

```text
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/submit/guards.py src/ai_fund_lab_v2/runtime_v2/pending/consume.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
PASS

python3 -m pytest tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'ak9r25 or ak9r23 or phase24_hv or phase17_x_pending_safety_authority_mismatch or phase23_ax'
13 passed, 9 deselected

python3 -m pytest tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'ak9r25 or ak9r23 or phase24_hv or phase17_x_pending_safety_authority_mismatch or phase23_ax or historical'
33 passed

python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
28 passed

python3 -m pytest tests/runtime_v2/test_phase30_ak9r10_full_day1_day2_pending_lifecycle.py tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -k 'ak9r21 or ak9r1b or one_lot or selected_position_amount or lifecycle or orchestration'
17 passed, 15 deselected

python3 -m pytest tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase13_p_pending_consume.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py -k 'submit or guard or one_lot or review or dedup'
20 passed, 2 deselected

python3 -m pytest tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py
7 passed
```

The attempted AK9R14 standalone file lookup found no `tests/runtime_v2/*ak9r14*` file in this checkout, so AK9R14 lifecycle coverage was exercised through the available pending lifecycle/orchestration suites.

## Final Judgments

```text
AK9R24_SUBMIT_DATA_READINESS_FAILURE_REPRODUCED = YES
CANONICAL_SUBMIT_HISTORICAL_SAFETY_AUTHORITY_REUSED = YES
BUY_ITEM_SCOPED_REVIEW_IS_NOT_BATCH_FAILURE = YES
SUBMIT_DATA_READINESS_ITEM_SCOPED_REVIEW_SUPPORTED = YES
APPROVED_BUY_NOT_BLOCKED_BY_REVIEWED_BUY = YES
APPROVED_SELL_NOT_BLOCKED_BY_REVIEWED_BUY = YES
REVIEWED_BUY_REMAINS_FAIL_CLOSED = YES
REVIEWED_SELL_FAIL_CLOSED_PRESERVED = YES
TRUE_BATCH_FAILURE_FAIL_CLOSED_PRESERVED = YES
CASH_FEASIBILITY_FAIL_CLOSED_PRESERVED = YES
AK3R2B_CASH_AUTHORITY_PRESERVED = YES
AK9R21_SUBMIT_AUTHORITY_PRESERVED = YES
AK9R21_SYSTEM_REVIEW_REASON_RECURRENCE = NO
AK9R1_ITEM_SCOPED_PARTIAL_SUBMISSION_ACTION_EFFECTIVE = YES
AK8R_BUY_SELL_INDEPENDENCE_PRESERVED = YES
VALID_BUY_NOT_DROPPED_BY_SELL = YES
VALID_SELL_NOT_DROPPED_BY_BUY_REVIEW = YES
AK9R23_SELL_PLANNING_REPAIR_PRESERVED = YES
REAL_SUBMIT_ORCHESTRATION_SENTINEL = YES
ORCHESTRATION_FIDELITY = FULL
AK9R24_EQUIVALENT_PARTIAL_SUBMIT_PASS = YES
CROSS_REPAIR_INTERACTION_STATUS = PASS

NEW_BUY_FILTER_CREATED = NO
NEW_SELL_FILTER_CREATED = NO
FORCED_BUY_CREATED = NO
FORCED_SELL_CREATED = NO
STRATEGY_CHANGED = NO
PC_CHANGED = NO
PS_CHANGED = NO
CAP_VALUES_CHANGED = NO

KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
FRESH_VALIDATION_BLOCKERS = []
FRESH_20BD_VALIDATION_READY = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

`Phase30-AK9R26 - User-Operated Fresh 20BD Validation`
