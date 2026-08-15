# Phase29-L21T-M BUY Item-Scoped Review SELL Continuation Composition Repair

Task ID: `Phase29-L21T-M`

## Primary Judgment

`PHASE29_L21T_M_BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_COMPOSITION_REPAIRED_FOCUSED_REGRESSION_PASS`

BUY_BATCH_ATOMICITY_PRESERVED = YES  
PARTIAL_BUY_APPROVAL_IMPLEMENTED = NO  
BUY_REVIEW_EVIDENCE_PRESERVED = YES  
SELL_CONTINUATION_UNDER_BUY_ITEM_SCOPED_REVIEW = PASS  
REDUCE_CONTINUATION = PASS  
EXIT_CONTINUATION = PASS  
GLOBAL_SAFETY_FAIL_CLOSED_PRESERVED = YES  
CURRENT_QUANTITY_FAIL_CLOSED_PRESERVED = YES  
L21T_F_BEHAVIOR_CHANGED = NO  
L21T_K_BEHAVIOR_CHANGED = NO  
SHARED_PENDING_MODEL_PRESERVED = YES  
SUBMIT_SIDE_MIGRATION_GAP_FOUND = NO  
FRESH_VALIDATION_READY = YES

## Root Cause

L21T-L confirmed that `read_active_buy_pending()` intentionally requires a BUY item to be present in top-level `approved_item_ids`. Under Phase24-ID/IE whole-BUY-batch atomicity, a `BUY_ITEM_SCOPED_REVIEW` pending has `approved_buy_item_ids=()` and `approved_item_ids=()`, even when one BUY item independently passed and is recorded as `BLOCKED_BY_BATCH_REVIEW`.

The sell pipeline then treated the reviewed BUY pending as `active_buy_missing`, preserved the original BUY review pending, and dropped an independently valid SELL/REDUCE/EXIT. That coupled BUY review authority to the SELL lane at the final Pending composition boundary.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`

## Repair

Added `compose_with_buy_item_scoped_review_pending()` as a Production/Demo/Historical-common shared Pending composition path.

Eligibility is fail-closed and requires:

- same `plan_created_date` and `target_session_date`
- unconsumed active current Pending
- `state=REVIEW_REQUIRED`
- `review_scope=BUY_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed=true`
- no approved BUY ids
- no review-required SELL ids
- at least one review-required BUY id
- independently generated positive SELL items

The repaired composition writes one shared current Pending with `state=APPROVED`, `approved_item_ids` and `approved_sell_item_ids` containing only SELL ids, `approved_buy_item_ids=()`, and preserved BUY review fields/items. Reviewed BUY items keep `approved=false`, `ITEM_REVIEW_REQUIRED`, and `BLOCKED_BY_BATCH_REVIEW` evidence.

Normal approved BUY + approved SELL `COMPOSITE_PENDING_PLAN` behavior remains unchanged.

## Proof

BUY batch atomicity unchanged:

- Focused L21T-M fixture preserves `buy-review-30410` as `ITEM_REVIEW_REQUIRED`.
- `buy-pass-24350` remains `BLOCKED_BY_BATCH_REVIEW`.
- `approved_buy_item_ids=[]`.
- No partial BUY approval was added.
- Phase24 aggregate feasibility regression passed.

SELL independence:

- REDUCE under BUY item-scoped review composes into shared Pending with one approved SELL id.
- EXIT under BUY item-scoped review composes and Submit sends only the SELL item.
- no-SELL signal preserves the reviewed BUY pending and does not write EMPTY.
- unscoped/invalid BUY review with `sell_continuation_allowed=false` remains fail-closed under the existing invalid BUY preservation guard.

Submit behavior:

- Submit already iterates `pending.approved_item_ids`.
- The repaired Pending is top-level `APPROVED`, with only SELL item ids approved.
- Focused Submit regression submitted the EXIT SELL item only and did not consume reviewed BUY items.
- No downstream Submit migration gap was found.

Runtime judgment behavior:

- Valid SELL-continuation composition returns `sell_planning status=PASS`.
- BUY review remains represented in current Pending side/item fields.
- Runtime does not need a global `REVIEW_REQUIRED -> PASS` conversion.

## Regression Results

PASS:

```bash
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -k l21t_m
```

Result: `4 passed, 17 deselected`

PASS:

```bash
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
```

Result: `21 passed`

PASS:

```bash
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py
```

Result: `55 passed`

PASS:

```bash
python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -k l21t_k tests/runtime_v2/test_phase26_step4_position_sizing_authority.py -k 'l21t_h or one_lot' tests/strategy/test_phase22_j_position_sizing.py -k 'l21t_b or l21t_c'
```

Result: `11 passed, 110 deselected`

PASS:

```bash
python3 -m pytest tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'block_sell or current_position_missing or BUY_ITEM_SCOPED_REVIEW or sell_continuation'
```

Result: `2 passed, 23 deselected`

PASS:

```bash
python3 -m pytest tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py
```

Result: `5 passed`

PASS:

```bash
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/composition.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
```

PASS:

```bash
git diff --check
```

## Fresh Validation Readiness

Codex did not run fresh-run, resume-run, 100BD Historical, long Historical, broker mutation, manual Runtime/Pending mutation, config change, threshold tuning, or Accepted Generation change.

User-run focused Historical command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --start-date 2022-08-23 --end-date 2022-09-16 --confirm --yes-i-understand-this-mutates-trading-state
```

## Remaining Gaps

No L21T-M downstream migration gap was found in focused regression. Fresh Historical validation is still required to verify the repaired path against the full 2022-08-23 through 2022-09-16 runtime sequence and later 100BD resumption/restart.
