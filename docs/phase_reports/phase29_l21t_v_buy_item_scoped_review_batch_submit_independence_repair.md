# Phase29-L21T-V BUY Item-Scoped Review / Batch Submit Independence Repair

## Primary Judgment

`PHASE29_L21T_V_BUY_ITEM_SCOPED_REVIEW_SUBMIT_SCOPE_INCOMPLETE_MIGRATION_CONFIRMED_AND_REPAIRED_FOCUSED_REGRESSION_PASS`

## Root Cause

The 2022-10-12 target run stopped at `2022-10-12:submit` because Submit used the pre-Phase24 generic Pending guard:

```text
dangerous pending state blocked: REVIEW_REQUIRED
```

That guard only inspected top-level `pending.state` and did not apply the Phase24-HV/IE structured review scope contract.

The target Pending was structurally valid:

- `state=REVIEW_REQUIRED`
- `review_scope=BUY_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed=true`
- `approved_item_ids=[]`
- `approved_buy_item_ids=[]`
- `approved_sell_item_ids=[]`
- `review_required_buy_item_ids=[strategy-9a17b799ca59b1896fce]`
- `review_required_sell_item_ids=[]`

## 2022-10-12 Item Evidence

`65500`:

- `quantity=700`
- `estimated_amount=136500.0`
- `reserved_notional=170800.0`
- `feasibility_status=PASS`
- final item state `REVIEW_REQUIRED`
- `batch_submit_status=BLOCKED_BY_BATCH_REVIEW`

`76920`:

- `quantity=1200`
- `estimated_amount=136680.0`
- `reserved_notional=219960.0`
- `feasibility_status=REVIEW_REQUIRED`
- `item_review_reason=reserved notional exceeds dynamic cash capacity`
- `violated_policy=dynamic_cash`
- `violated_policy_source=policy_context`

The aggregate reservation sequence is valid evidence:

```text
170800 + 219960 = 390760
dynamic cash capacity = 361311
excess = 29449
```

Therefore `76920` review is valid. This repair does not weaken MARKET BUY stop-high reservation, dynamic cash capacity, buying-power, exposure, or Q2 transactionality.

## Batch Atomicity Judgment

Phase24-IE explicitly preserves BUY batch submit atomicity for reviewed Pending plans:

```text
Aggregate batch REVIEW_REQUIRED
  -> approved_item_ids = []
  -> approved_buy_item_ids = []
  -> approved_sell_item_ids = []
  -> no Submit boundary crossing from that Pending plan
```

So `65500` must not be submitted from this Pending plan, even though it has `feasibility_status=PASS`. `BLOCKED_BY_BATCH_REVIEW` is expected under the current contract.

The defect was not `65500` being blocked from BUY submit. The defect was promoting a valid BUY-only item-scoped review into Runtime-wide Submit `BLOCKED` / run HALT.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`
- `docs/phase_reports/phase29_l21t_v_buy_item_scoped_review_batch_submit_independence_repair.md`

No new command was added, so `docs/03_operations/runtime_test_command_guide.md` required no L21T-V update.

## Authority Before / After

Before:

```text
BUY_ITEM_SCOPED_REVIEW Pending
  -> Submit guard sees state=REVIEW_REQUIRED
  -> BLOCKED
  -> Runtime Test HALT
```

After:

```text
valid BUY_ITEM_SCOPED_REVIEW Pending
  -> Submit materializes BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION
  -> submitted_count=0
  -> partial_buy_submit_allowed=false
  -> BUY batch atomicity preserved
  -> Execution accepts no-submitted-order authority
  -> no Broker ReadOnly orderlist required
```

Invalid/unscoped/malformed REVIEW_REQUIRED Pending still falls through to the existing dangerous-state fail-closed guard.

## Regression Classification

`INCOMPLETE_MIGRATION_CONFIRMED`

The generic Submit guard predates Phase24-IE. Phase24-IE introduced structured `BUY_ITEM_SCOPED_REVIEW` semantics, but Submit and Execution no-action authority were not migrated to consume the new scope. The 2022-10-12 multi-BUY batch exposed that incomplete migration.

READ-only search over the target run detected `BUY_ITEM_SCOPED_REVIEW`, `BLOCKED_BY_BATCH_REVIEW`, and `dangerous pending state blocked: REVIEW_REQUIRED` only on 2022-10-12 among the completed/halted daily evidence, so this appears to be first exposure in this 41BD run, not proof that partial BUY submit previously worked.

## Recovery / Resume Judgment

`recover-stale-pending` dry-run was attempted read-only:

```text
status = PRECONDITION_FAILURE
errors =
  persistent state is not at last completed coherent boundary
  run_state next_job is not stale pending sell_planning boundary
  halted_at job is not sell_planning
```

This is expected because the existing recovery command is scoped to stale Pending regeneration from a sell_planning boundary.

For this case, the Pending producer semantics are valid and no 2022-10-12 orders/ledger/current mutations occurred. The repaired component is the Submit/Execution consumer of that existing Pending. Therefore:

- `SCOPED_RECOVERY_REQUIRED = NO`
- `FRESH_RUN_REQUIRED = NO`
- `DIRECT_RESUME_SAFE_AFTER_REPAIR = YES`
- Codex did not resume the target run.

## Final Judgments

- `BUY_76920_REVIEW_VALID = YES`
- `BUY_65500_FEASIBILITY_PASS_VALID = YES`
- `BUY_65500_PARTIAL_SUBMIT_ALLOWED = NO`
- `BUY_BATCH_ATOMICITY_VALID = YES`
- `SUBMIT_HALTING_ON_VALID_BUY_ITEM_SCOPED_REVIEW_EXPECTED = NO`
- `RUNTIME_WIDE_SCOPE_ESCALATION_DEFECT_CONFIRMED = YES`
- `SUBMIT_SCOPE_AWARE_REPAIR_IMPLEMENTED = YES`
- `EXECUTION_NO_ACTION_AUTHORITY_REPAIR_IMPLEMENTED = YES`
- `BUY_FAIL_CLOSED_PRESERVED = YES`
- `SELL_INDEPENDENCE_PRESERVED = YES`
- `GLOBAL_SAFETY_FAIL_CLOSED_PRESERVED = YES`
- `CAPITAL_GUARD_PRESERVED = YES`
- `REVIEWED_BUY_UNAUTHORIZED_SUBMIT = NO`
- `RUNTIME_MUTATION_PERFORMED = NO`
- `LONG_HISTORICAL_RUN_PERFORMED = NO`
- `PHASE = Phase29`

## Regression Results

Passed:

```text
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -k 'l21t_v'
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py
python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py
git diff --check
```

Existing warning observed:

```text
DeprecationWarning in position_management/producer.py for empty ndarray truth value
```

This warning is pre-existing and unrelated to L21T-V.

## User Next Action

Run a resume dry-run for the target run from its current `2022-10-12:submit` boundary. If the dry-run confirms the repaired Submit no-submission authority and subsequent Execution no-action path, then apply the normal resume.
