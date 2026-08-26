# Phase31-F1T — Canonical SELL Authority / Same-Day BUY+SELL Composite Pending Continuation Repair

## PRIMARY_JUDGMENT

PHASE31_F1T_CANONICAL_SELL_AUTHORITY_BUY_SELL_COMPOSITE_CONTINUATION_REPAIR_PASS

ROOT_CAUSE =

BUY_SELL_COMPOSITE_PENDING_CONTINUATION_GAP

+

SELL_AUTHORITY_PRODUCER_CONSUMER_MISMATCH

IMPLEMENTATION_STATUS = COMPLETE

CANONICAL_FINAL_SELL_AUTHORITY = `runtime_state/strategy_planning/<business_date>/order_plan.json` produced by Strategy Runtime Planning / strategy planning authority. For F1T continuation, sell_planning consumes only finalized `planning_intent = SELL_EXIT` rows with positive planned quantity from this artifact.

DUPLICATE_FINAL_SELL_AUTHORITY_COUNT = 0

60540_CANONICAL_SELL_AUTHORITY_REGRESSION = PASS

99840_NO_ORDER_EXCLUDED = PASS

70140_NO_ORDER_EXCLUDED = PASS

20220823_BUY_SELL_COMPOSITE_CONTINUATION_REGRESSION = PASS

BUY_ITEMS_PRESERVED = YES

COMPOSITE_GENUINE_CONFLICT_FAIL_CLOSED = PASS

MISSING_CANONICAL_SELL_AUTHORITY_FAIL_CLOSED = PASS

93600_SINGLE_SELL_REGRESSION = PASS

20221012_MULTI_SELL_REGRESSION = PASS

ORIGINAL_PENDING_PRESERVED = YES

DUPLICATE_PENDING_CREATED = NO

F1F_ESCALATION_SEMANTICS_CHANGED = NO

F1I_HISTORY_BRIDGE_CHANGED = NO

CANONICAL_SELL_STATES_CHANGED = NO

BUY_LOGIC_CHANGED = NO

ADD_LOGIC_CHANGED = NO

MARKET_CONTEXT_CHANGED = NO

FUTURE_INFORMATION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Implementation Summary

Changed:

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py`

The repair adds a distinct same-day canonical BUY+SELL composite pending continuation path. It runs only after the existing F1L/F1R SELL-only equivalence path does not match.

The continuation path:

- reads finalized SELL authority from Strategy Runtime Planning order_plan
- never falls back to raw PM REDUCE when canonical authority is missing
- requires same-day APPROVED unconsumed pending
- preserves BUY items unchanged
- requires pending SELL set to exactly match canonical SELL_EXIT set
- requires per-symbol pending quantity to match canonical SELL_EXIT quantity
- requires EXIT lineage and current full-position quantity
- fail-closes on stale, partial/submitted, consumed, duplicate SELL, missing current position, missing authority, set mismatch, and quantity mismatch

## Canonical Authority

CANONICAL_FINAL_SELL_AUTHORITY details:

- Producer: Strategy Runtime Planning / strategy planning authority
- Artifact: `.runtime/runtime_state/strategy_planning/<business_date>/order_plan.json`
- Consumer: sell_planning same-day composite pending continuation only
- Canonical field: `items[].planning_intent == SELL_EXIT`
- Canonical quantity: `items[].planned_quantity` or `items[].quantity`
- Temporal binding: same business date as sell_planning and target session date

Raw PM action remains semantic input upstream. It is not used as an independent final SELL authority when Strategy Runtime Planning finalized SELL authority exists.

## 2022-08-23 Regression

Production-shaped test:

- Existing Pending BUY:
  - 94320 BUY_ADD 200
  - 38150 BUY_NEW 100
  - 72980 BUY_NEW 100
  - 44410 BUY_NEW 100
  - 71730 BUY_NEW 100
- Existing Pending SELL:
  - 60540 SELL_EXIT 100
- Canonical final SELL set:
  - 60540 SELL_EXIT 100
- Canonical NO_ORDER rows:
  - 99840 NO_ORDER
  - 70140 NO_ORDER

Result:

- status PASS
- pending_composition_model = SAME_DAY_CANONICAL_BUY_SELL_COMPOSITE_PENDING_CONTINUATION
- BUY item count before = 5
- BUY item count after = 5
- SELL item set after = 60540 only
- original pending preserved
- duplicate pending not created
- 99840 and 70140 not inserted

## Evidence Materialized

New evidence artifact for the continuation path:

`same_day_buy_sell_composite_pending_continuation_evidence.json`

It includes:

- canonical_sell_authority_source
- canonical_sell_authority_producer
- canonical_sell_symbol_set
- pending_sell_symbol_set
- per_symbol_canonical_sell
- canonical quantity
- pending quantity
- current position quantity
- BUY item count
- SELL item count
- buy_items_preserved
- original_pending_preserved
- duplicate_pending_created
- continuation_decision
- future_information_used

## Focused Test Results

FOCUSED_TEST_RESULTS = PASS

- `python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py -q` = 20 passed
- `python3 -m pytest tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q` = 38 passed
- `python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q` = 22 passed
- `python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py -q` = 14 passed

PY_COMPILE = PASS

- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py`

GIT_DIFF_CHECK = PASS

- `git diff --check`

## Resume Safety

Target run:

runtime-test-historical-extended-smoke-20260821T041825673015Z

READ-ONLY recheck:

- still halted at 2022-08-23:sell_planning
- sell_planning cli exit code = 20
- top-level fresh_run_summary exit_code = 30
- pending_plan_id = pending-strategy-plan-historical-2022-08-23-9fa776fa8db6a019
- no 2022-08-23 submit directory
- no 2022-08-23 execution directory

RESUME_AFTER_F1T = SAFE

Reason: F1T does not require mutating the existing pending. The repaired path can reuse the exact same same-day approved composite pending, preserve BUY items, reuse SELL_EXIT 60540, and continue without creating duplicate pending or adding 99840/70140.

## NEXT_TASK_RECOMMENDATION

Run focused acceptance, then resume the clean 100BD run from the existing 2022-08-23 halt state. Do not run resume inside F1T.
