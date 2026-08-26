# Phase31-F1R — Strict Multi-SELL Same-Day Pending Set-Equivalence Repair

## PRIMARY_JUDGMENT

PHASE31_F1R_STRICT_MULTI_SELL_SAME_DAY_PENDING_SET_EQUIVALENCE_REPAIR_PASS

ROOT_CAUSE = MULTI_SELL_COMPOSITION_GAP

IMPLEMENTATION_STATUS = COMPLETE

TARGET_ACTUAL_CASE = 2022-10-12 SELL Planning HALT

TARGET_PENDING_PLAN_ID = pending-strategy-plan-historical-2022-10-12-6837dc958968615c

TARGET_PENDING_SYMBOL_SET = 28130, 70690, 70780, 82540

## MULTI_SELL_SET_EQUIVALENCE_CONTRACT

The F1L same-day SELL pending idempotency authority was extended from single SELL_EXIT reuse to strict multi-SELL_EXIT set reuse.

Reuse is allowed only when all of the following are true:

- existing pending plan state is APPROVED
- plan_created_date equals the sell planning business date
- target_session_date equals the sell planning target session date
- pending plan is unconsumed
- pending plan contains no BUY items
- every pending item is an approved SELL item with positive quantity
- every item state is CREATED, READY, or APPROVED
- no partial/fill evidence is present
- no duplicate symbol exists
- every pending symbol has a canonical current position
- every pending quantity equals that symbol's current full position quantity
- every item is EXIT lineage by canonical pending item/source planning fields
- every authoritative embedded SELL_EXIT quantity equals the current full position quantity
- pending symbol set equals authoritative SELL_EXIT symbol set
- equivalence is symbol-keyed and order-independent

Single SELL_EXIT behavior remains F1L-compatible.

## Required Output

20221012_MULTI_SELL_EQUIVALENCE_REGRESSION = PASS

93600_SINGLE_SELL_REGRESSION = PASS

SET_CARDINALITY_MISMATCH_FAIL_CLOSED = PASS

PER_SYMBOL_QUANTITY_MISMATCH_FAIL_CLOSED = PASS

MIXED_BUY_SELL_FAIL_CLOSED = PASS

DUPLICATE_SYMBOL_FAIL_CLOSED = PASS

EXECUTION_ADVANCED_PENDING_FAIL_CLOSED = PASS

ORIGINAL_PENDING_PRESERVED = YES

DUPLICATE_PENDING_CREATED = NO

ACTIVE_PENDING_SAFETY_GUARD_WEAKENED = NO

F1F_ESCALATION_SEMANTICS_CHANGED = NO

F1I_HISTORY_BRIDGE_CHANGED = NO

CANONICAL_SELL_STATES_CHANGED = NO

FUTURE_INFORMATION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Focused Test Results

FOCUSED_TEST_RESULTS = PASS

- `python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py -q` = 15 passed
- `python3 -m pytest tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q` = 38 passed
- `python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q` = 22 passed
- `python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py -q` = 14 passed

PY_COMPILE = PASS

- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py`

GIT_DIFF_CHECK = PASS

- `git diff --check`

## Implementation Notes

Changed:

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py`

The repair only changes no-signal/non-executable SELL pending idempotency handling. It does not alter Strategy, PM SELL semantics, F1F escalation, F1I bridge history materialization, thresholds, submit, execution, lifecycle state definitions, or canonical SELL state semantics.

BUY-only active pending preservation remains unchanged. Mixed BUY+SELL active pending is not treated as BUY-only preservation; it is routed through active-pending preservation and fail-closed review semantics.

## Actual Artifact Safety

The existing 2022-10-12 artifact still shows the four pending SELL_EXIT items and no fresh submit/execution artifacts were created by this task.

READ_ONLY_ACTUAL_ARTIFACT_CHECK = PASS

CANONICAL_RUN_ARTIFACT_MUTATED = NO

## Resume Assessment

RESUME_AFTER_F1R = SAFE

Reason: the F1Q root cause was the multi-SELL composition gap after F1L/F1O had already supplied current-position evidence. F1R now accepts only the strict 4-symbol full EXIT set represented by the existing approved same-day unconsumed pending. Duplicate pending creation remains prevented and original pending identity is preserved.

## NEXT_TASK_RECOMMENDATION

Resume from the existing 2022-10-12 pending state using the normal resume path, then verify SELL Planning progresses past the prior `EQUIVALENT_SELL_PENDING_AMBIGUOUS_ITEM_SET` branch.
