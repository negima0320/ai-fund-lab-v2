# Phase31-F1W - Item-Scoped Review Partial Submit Terminalization / Idempotent Reconciliation Repair

## PRIMARY_JUDGMENT

PHASE31_F1W_ITEM_SCOPED_PARTIAL_SUBMIT_TERMINALIZATION_REPAIRED

## ROOT_CAUSE

ITEM_SCOPED_BUY_REVIEW_PARTIAL_SUBMIT_TERMINALIZATION_AND_IDEMPOTENCY_GAP

## IMPLEMENTATION_STATUS

IMPLEMENTED

## PER_ITEM_SUBMIT_TERMINAL_AUTHORITY

PASS

Submit now treats existing accepted side effects as item-scoped terminal evidence only when `pending_plan_id`, `pending_item_id`, `business_date`, `status`, side, symbol, and quantity match the active Pending item.

## ALREADY_SUBMITTED_ITEM_RECONCILIATION

PASS

Existing accepted `persistent_ledger/orders.jsonl` records are reconciled before adapter submit. Historical broker evidence is also recognized as a fallback side-effect source, but ledger evidence remains preferred when both exist.

## 34940_MISSING_ORDER_HANDLING

PASS

If no accepted side effect exists for the approved 34940 SELL item, Submit may submit that item exactly once after normal guard/preflight validation. A retry then reconciles the resulting ledger order and does not call the adapter again.

## 76920_REVIEW_PRESERVED

PASS

The reviewed 76920 BUY item remains `REVIEW_REQUIRED`, is not submitted, and is not converted to SAFE/APPROVED.

## PENDING_PARTIAL_SUBMIT_TERMINALIZATION

PASS

For item-scoped BUY review partial submit, accepted executable items are marked `CONSUMED`, the Pending plan remains `REVIEW_REQUIRED`, and the residual reviewed BUY item remains visible for review/lifecycle terminalization.

## SUBMITTED_ORDER_IDS_PERSISTED

PASS

`consume.submitted_order_ids` is populated even when the Pending plan is not fully consumed.

## LEDGER_ORDER_RECORD_IDS_PERSISTED

PASS

`consume.ledger_order_record_ids` is populated for reconciled/new accepted ledger order records.

## RETRY_DUPLICATE_ORDER_COUNT

0

Covered by `tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py`.

## 20221208_ACTUAL_PATH_REGRESSION

PASS

The regression fixture mirrors the F1V 2022-12-08 shape: four already materialized approved items, one missing approved 34940 SELL, and one reviewed 76920 BUY.

## ITEM_SCOPED_REVIEW_PARTIAL_SUBMIT_REGRESSION

PASS

## NORMAL_FULL_SUBMIT_REGRESSION

PASS

Existing normal submit regression remained green.

## SELL_CONTINUATION_PRESERVED

PASS

Approved SELL items remain independently executable/reconcilable under BUY item-scoped review.

## PARTIAL_SIDE_EFFECT_CRASH_RECOVERY_CONTRACT

PASS

Recovery authority is item-scoped accepted side-effect reconciliation. Already materialized approved items are not resubmitted; missing approved items can proceed through normal guard validation exactly once; reviewed BUY remains deferred.

## DUPLICATE_SUBMIT_AUTHORITY_COUNT

0

## CORPORATE_ACTION_SAFETY_CHANGED

NO

## BUY_LOGIC_CHANGED

NO

## F1F_ESCALATION_SEMANTICS_CHANGED

NO

## FUTURE_INFORMATION_USED

NO

## FRESH_RUN_EXECUTED

NO

## RESUME_EXECUTED

NO

## REPLAY_EXECUTED

NO

## LONG_HISTORICAL_EXECUTED

NO

## FOCUSED_TEST_RESULTS

PASS

- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py -q` = 1 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15bo_isolated_submit_simulation.py -q` = 6 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py -q` = 4 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q` = 41 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py -q` = 20 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q` = 22 passed

## PY_COMPILE

PASS

- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py`

## GIT_DIFF_CHECK

PASS

- `git diff --check`

## RECOVERY_PATH_RECOMMENDATION

Resume may be attempted only after operator acceptance of this repair. On the F1V actual halted state, expected behavior is: reconcile 61440 BUY, 82560 SELL, 37790 SELL, and 45910 SELL; submit 34940 SELL if still guard-valid and not already materialized; preserve 76920 BUY as REVIEW_REQUIRED.

## NEXT_TASK_RECOMMENDATION

Run the existing actual resume path from the F1V halted run and audit the produced Submit/Pending artifacts before any new long Historical run.

## Scope Notes

Modified:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py`

Not modified:

- Strategy
- Position Management SELL semantics
- BUY ranking
- corporate-action safety/quarantine semantics
- F1F/F1I escalation semantics
- fixtures or artifacts from the actual halted run

No fresh-run, resume, replay, or long Historical execution was performed.
