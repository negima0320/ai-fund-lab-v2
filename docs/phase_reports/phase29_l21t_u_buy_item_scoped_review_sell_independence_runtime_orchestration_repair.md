# Phase29-L21T-U BUY Item-Scoped Review / SELL Independence Runtime Orchestration Repair

## Primary Judgment

`PHASE29_L21T_U_BUY_ITEM_SCOPED_REVIEW_SELL_NO_SIGNAL_RUNTIME_ORCHESTRATION_REPAIRED_FOCUSED_REGRESSION_PASS`

## Root Cause

The 2023-06-14 target run stopped at `2023-06-14:sell_planning` with exit code 20 because SELL Planning treated a valid BUY-only item-scoped review Pending as a runtime-wide active Pending conflict in the SELL no-signal path.

Evidence from `runtime-test-historical-smoke-20260812T083943290963Z`:

- Current Pending: `state=REVIEW_REQUIRED`, `review_scope=BUY_ITEM_SCOPED_REVIEW`, `sell_continuation_allowed=true`
- BUY item: `99840`, `quantity=100`, `state=REVIEW_REQUIRED`, `reserved_notional=197750.0`, reason `reserved notional exceeds Current cash`
- Top-level approvals: `approved_item_ids=[]`, `approved_buy_item_ids=[]`, `approved_sell_item_ids=[]`
- SELL order plan: `status=NO_ACTION`, reason `NO_SIGNAL:exit_ai_no_sell_signal`
- Pre-SELL snapshot: `active_buy_pending_reason=active_buy_missing`
- Pending continuity: `ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`
- Final manifest: `sell planning pipeline review required`, `final_state=REVIEW_REQUIRED`, exit code 20

The BUY review itself is valid and remains fail-closed. The defect was that SELL no-signal preservation returned `REVIEW_REQUIRED` even when the Pending was structurally eligible for `BUY_ITEM_SCOPED_REVIEW` SELL continuation.

## Lineage

Phase24-HV and Phase24-IE established that `BUY_ITEM_SCOPED_REVIEW` blocks BUY submission but must not automatically invalidate independent Position Management, SELL Planning, or approved SELL submission when same-date safety and authority checks pass.

L21T-M repaired executable SELL composition under BUY item-scoped review, but the no-signal path still preserved the reviewed BUY Pending by returning runtime-wide `REVIEW_REQUIRED`. That made no-signal days halt even though no SELL action was requested and no fake SELL should be created.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`
- `tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py`

No new runtime-test command was added, so `docs/03_operations/runtime_test_command_guide.md` did not require a new L21T-U command entry.

## Authority Before / After

Before:

```text
BUY_ITEM_SCOPED_REVIEW Pending
  -> read_active_buy_pending = active_buy_missing
  -> SELL no-signal
  -> original Pending preserved
  -> SELL Planning result REVIEW_REQUIRED
  -> runtime HALT
```

After:

```text
BUY_ITEM_SCOPED_REVIEW Pending
  -> structural sell-continuation eligibility check
  -> SELL no-signal
  -> original BUY review Pending preserved
  -> SELL Planning result NO_SIGNAL
  -> no fake SELL, no BUY approval, no SELL-side HALT
```

Invalid/stale/consumed/date-mismatched/unscoped/global safety blocked Pending still falls through to the existing fail-closed preservation path.

## 2023-06-14 Fixture Result

Focused fixture:

`test_phase29_l21t_m_buy_item_scoped_review_no_signal_preserves_review_pending`

Result:

- SELL Planning `status=NO_SIGNAL`
- `reason=NO_SIGNAL:exit_ai_no_sell_signal`
- `pending_composition_model=BUY_ITEM_SCOPED_REVIEW_SELL_NO_SIGNAL_PRESERVATION`
- current Pending remains `state=REVIEW_REQUIRED`
- `review_scope=BUY_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed=true`
- BUY items remain preserved and non-approved
- continuity evidence includes `BUY_ITEM_SCOPED_REVIEW_PRESERVED_ON_SELL_NO_SIGNAL`

## Negative Fixtures

- Invalid/unscoped BUY review remains `REVIEW_REQUIRED` via `PRESERVE_ACTIVE_PENDING_ON_INVALID_BUY`.
- SELL-side invalidity/global safety blocks remain under existing fail-closed tests.
- Q1B MARKET BUY reservation and Q2 transactionality regressions remain passing.

## Recovery Readiness

Dry-run only command executed:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending --run-id runtime-test-historical-smoke-20260812T083943290963Z --business-date 2023-06-14 --expected-pending-plan-id pending-strategy-plan-historical-2023-06-14-9f2a59c132e5c5b9 --dry-run --json
```

Result:

- `status=DRY_RUN`
- `dry_run_no_mutation=true`
- `recovery_classification=STALE_REVIEW_REQUIRED_PENDING_REPLAY`
- `rewind_to_job=morning`
- `manual_file_edit_required=false`
- `ledger_current_recovery_required=false`
- `production_common_recovery=true`

## Final Judgments

- `BUY_99840_REVIEW_VALID = YES`
- `BUY_ITEM_SCOPED_REVIEW_VALID = YES`
- `SELL_CONTINUATION_AUTHORITY_VALID = YES`
- `SELL_SIGNAL_ON_2023_06_14 = NO_SIGNAL`
- `SELL_PLANNING_HALT_EXPECTED = NO`
- `RUNTIME_ORCHESTRATION_DEFECT_CONFIRMED = YES`
- `PENDING_COMPOSITION_DEFECT_CONFIRMED = YES`
- `REGRESSION_CONFIRMED = YES`
- `REGRESSION_INTRODUCING_CHANGE = Phase29-L21T-M no-signal preservation path encoded REVIEW_REQUIRED instead of NO_SIGNAL under valid BUY item-scoped review`
- `PRODUCTION_COMMON_REPAIR_IMPLEMENTED = YES`
- `BUY_FAIL_CLOSED_PRESERVED = YES`
- `SELL_INDEPENDENCE_PRESERVED = YES`
- `GLOBAL_SAFETY_FAIL_CLOSED_PRESERVED = YES`
- `TARGET_PENDING_STALE_AFTER_REPAIR = YES`
- `SCOPED_RECOVERY_REQUIRED = YES`
- `DIRECT_RESUME_SAFE = NO`
- `RESUME_SAFE_NOW = NO`

## Regression Results

Passed:

```text
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -k 'l21t_m_buy_item_scoped_review or l21t_m_unscoped_invalid_buy or l21t_f_sell_order_preserves_invalid_active_buy_fail_closed'
python3 -m pytest tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k 'BUY_ITEM_SCOPED_REVIEW or sell_continuation or block_sell or current_position_missing'
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py
python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py
python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/composition.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
git diff --check
```

One initial `py_compile` attempt failed because the default Apple Python bytecode cache path was outside the sandbox. Re-running with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache` passed.

## Next Step

Do not directly resume `runtime-test-historical-smoke-20260812T083943290963Z`. The current 2023-06-14 Pending was generated before this repair and must be superseded through scoped stale Pending recovery from the `2023-06-14:morning` boundary before replaying the day.
