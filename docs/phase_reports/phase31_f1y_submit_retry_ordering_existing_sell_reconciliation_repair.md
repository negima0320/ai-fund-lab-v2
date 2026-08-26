# Phase31-F1Y - Actual-Artifact Submit Retry Ordering / Existing SELL Reconciliation Repair

## PRIMARY_JUDGMENT

PHASE31_F1Y_SUBMIT_RETRY_RECONCILIATION_ORDERING_REPAIRED_34940_FAIL_CLOSED

## ROOT_CAUSE

SUBMIT_RETRY_RECONCILIATION_ORDERING_GAP

## IMPLEMENTATION_STATUS

IMPLEMENTED

## RECONCILIATION_PRECEDES_REVALIDATION

YES

Submit now checks exact accepted side-effect evidence before sell available-quantity guard, corporate-action materialization, broker preflight, and adapter submit. Exact identity requires matching:

- pending_plan_id
- pending_item_id
- business_date/session
- symbol
- side
- quantity
- accepted status

If matched, the item is classified as `RECONCILED_EXISTING_SUBMISSION`, no fresh submit is attempted, and the order/ledger IDs are persisted.

## 61440_RECONCILIATION_REGRESSION

PASS

## 82560_RECONCILIATION_REGRESSION

PASS

## 37790_RECONCILIATION_REGRESSION

PASS

## 45910_RECONCILIATION_REGRESSION

PASS

## RECONCILED_SUBMITTED_SYMBOL_SET

{61440, 82560, 37790, 45910}

## SUBMITTED_ORDER_IDS_COMPLETE_FOR_RECONCILED_SET

YES

## LEDGER_ORDER_IDS_COMPLETE_FOR_RECONCILED_SET

YES

## 34940_OHLCV_ROW_COUNT

0 canonical normalized rows

Additional raw-source diagnostic:

- raw rows for 2022-12-08 / 34940 = 1
- raw `O/H/L/C` values = NaN
- run-scoped normalized source rows for 2022-12-08 / 34940 = 0

## 34940_OHLCV_AUTHORITY_STATUS

HALT

## 34940_OHLCV_ROOT_CAUSE

The canonical run-scoped normalized OHLCV source used by `HistoricalSubmitAdapter` has no valid 2022-12-08 row for 34940. The run-scoped raw J-Quants source contains one 34940 row for 2022-12-08, but the price fields are NaN, so no PIT target-session Open can be resolved without fabricating a price.

Source inspected:

- normalized: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/market_refresh/inputs/historical_asof/2022-12-08/raw_normalized/jquants/equities_bars_daily/data.parquet`
- raw: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/market_refresh/inputs/historical_asof/2022-12-08/raw/jquants/equities_bars_daily/data.parquet`

## 34940_HANDLING

TERMINAL_FAIL_CLOSED

No submit is authorized for 34940 unless a canonical PIT OHLCV authority with a unique valid Open exists. F1Y does not fabricate prices and does not use future rows.

## 76920_REVIEW_PRESERVED

YES

76920 remains item-scoped `REVIEW_REQUIRED`, not submitted, with reason `corporate_action_event_not_resolved`.

## ITEM_SCOPED_REVIEW_CONTINUATION_PRESERVED

YES

Existing continuation semantics remain: reviewed BUY alone does not block successful submitted/reconciled executable items. If all executable approved items are submitted/reconciled and no blocked/rejected/unknown item remains, Submit returns PASS with `submitted_with_reviewed_buy_items_not_submitted`.

## RETRY_DUPLICATE_ORDER_COUNT

0

## SIDE_EFFECT_IDENTITY_MISMATCH_FAIL_CLOSED

PASS

Regression mutates an existing 82560 ledger side effect to a mismatched quantity. The item is not reconciled and fails closed through the existing sell available-quantity guard instead of being treated as equivalent.

## 20221208_RETRY_ORDERING_REGRESSION

PASS

Production-shaped regression covers:

- preexisting accepted 61440 BUY
- preexisting accepted 82560 SELL
- preexisting accepted 37790 SELL
- preexisting accepted 45910 SELL
- missing 34940 SELL with preflight HALT
- reviewed 76920 BUY

Expected behavior is verified:

- all four existing side effects reconcile before revalidation
- no false available-quantity blockers on already submitted SELLs
- all four reconciled order/ledger IDs persist to Pending consume evidence
- 34940 remains unsubmitted/fail-closed
- 76920 remains reviewed/not submitted
- retry duplicate count remains zero

## CORPORATE_ACTION_SAFETY_CHANGED

NO

## BUY_LOGIC_CHANGED

NO

## F1F_ESCALATION_SEMANTICS_CHANGED

NO

## F1I_HISTORY_BRIDGE_CHANGED

NO

## SELL_STRATEGY_CHANGED

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

- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py -q` = 3 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15bo_isolated_submit_simulation.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py -q` = 10 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q` = 41 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q` = 42 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q` = 28 passed
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase30_ak9r10_full_day1_day2_pending_lifecycle.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py -q` = 10 passed, 4 warnings

Warnings were pre-existing deprecation warnings in `position_management/producer.py` around empty array truthiness; no F1Y failure.

## PY_COMPILE

PASS

- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py`

## GIT_DIFF_CHECK

PASS

- `git diff --check`

## RECOVERY_PATH_RECOMMENDATION

SCOPED_RECOVERY_REQUIRED

F1Y makes retry ordering safe for existing 61440/82560/37790/45910 side effects. However, the actual run still contains a missing 34940 order whose canonical target-session Open cannot be resolved from PIT OHLCV authority. Do not classify the target run as normal-resume-safe until an acceptance audit confirms how the 34940 fail-closed item should be terminalized for recovery.

## NEXT_TASK_RECOMMENDATION

Acceptance + exact recovery procedure.

Recommended next step: Phase31-F1Z acceptance/readiness audit over the repaired code and actual artifact state, without running resume. It should decide the precise scoped recovery procedure for 34940 fail-closed terminalization while preserving 76920 review and the four reconciled accepted side effects.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py`

No Strategy, PM SELL semantics, BUY ranking, corporate-action safety, F1F, or F1I behavior was changed.
