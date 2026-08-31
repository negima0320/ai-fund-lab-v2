# Phase32-BC - Mixed Review Pending Day-Rollover Lifecycle Repair

## Objective

Repair the Phase32-BB defect where a prior-day `MIXED_SELL_ITEM_SCOPED_REVIEW` residual Pending could not canonically expire at next-day pre-data-readiness.

Target run:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

Current halt before repair:

`2023-10-12:data_readiness`

## Root Cause Repaired

The Pending lifecycle runner had next-day expiration contracts for:

- terminal-only prior-day Pending,
- stale residual `BUY_ITEM_SCOPED_REVIEW`,
- mixed BUY-review / SELL-continuation residual with no reviewed SELL,
- same-day historical corporate-action quarantine.

It did not have a contract for the actual Phase32-AX/BA shape:

- prior-day `REVIEW_REQUIRED` Pending,
- `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`,
- approved executable SELL already terminal/`CONSUMED`,
- reviewed SELL and BUY items still non-approved/non-submittable,
- matching submit and execution evidence preserved.

Because that shape remained `REVIEW_REQUIRED`, 2023-10-12 pre-data-readiness failed with:

`pending_state_review_required_requires_operator_review`

## Repair

Added a narrow Pending lifecycle authority:

`mixed_sell_review_residual_rollover_authority`

Terminal transition:

`MIXED_SELL_REVIEW_RESIDUAL_PRIOR_DAY_AUTHORITY_EXPIRED`

The authority expires the prior-day review authority only when all required checks pass:

- `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`
- `target_session_date < current business_date`
- executable BUY items are absent
- executable SELL items are present
- reviewed BUY/SELL items are present and remain `REVIEW_REQUIRED`
- reviewed items are not approved, submitted, filled, or otherwise side-effected
- all executable items are terminal/`CONSUMED`
- submit manifest exists, passed, matches the Pending plan, and submitted exactly the executable SELL count
- execution manifest exists, passed, reconciled, and filled exactly the executable SELL count
- submit/execution runtime-test bindings do not conflict when present
- no broker-write uncertainty or post-send unknown state exists

The repair preserves prior-day audit evidence in Pending history, empties the active Pending slot, and records that fresh current-day authority is required for any reconsidered BUY/SELL.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py`
- `tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py`
- `tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py`

No Strategy, PM, PC, PS, threshold, ranking, cash policy, G129, KI-004, KI-006, or Winner Retention semantics were changed.

## Focused Validation

Passed:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py -q
60 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py -q
83 passed
```

Focused tests prove:

- valid prior-day mixed-review residual expires;
- reviewed items do not carry executable authority;
- new-day BUY/SELL requires fresh authority;
- unconsumed executable SELL blocks;
- missing execution evidence blocks;
- duplicate execution/fill count blocks;
- reviewed item with submit evidence blocks;
- mismatched submit/execution runtime-test run binding blocks;
- existing BUY-only rollover remains PASS;
- AX/BA current valuation and partial-submit adjacent behavior remains PASS;
- G129 BUY_ADD focused behavior remains PASS.

## Actual Boundary Reproduction

To avoid mutating the target run while validating the repaired boundary, `.runtime` was copied to `/private/tmp` and only `2023-10-12:data_readiness` was executed against the copy.

Result:

- return code: `0`
- copied Pending after: `EMPTY`
- `last_pending_plan_id`: `pending-strategy-plan-historical-2023-10-11-84b153a169af27d4`
- `last_terminal_state`: `EXPIRED`
- copied data readiness manifest:
  - `exit_code=0`
  - `final_state=CURRENT_STATE_LOADED`
  - `pending_lifecycle_status=EXPIRED`
  - `transition_reason=MIXED_SELL_REVIEW_RESIDUAL_PRIOR_DAY_AUTHORITY_EXPIRED`
  - `data_readiness_status=READY`
- `mixed_sell_review_residual_rollover.status=PASS`
- key checks:
  - `submit_submitted_sell_count_exact=true`
  - `execution_fill_count_exact=true`
  - `runtime_test_binding_not_mismatched=true`
  - `reviewed_items_not_submitted_or_filled=true`

This confirms the Phase32-BB data-readiness halt root cause is removed by the new lifecycle contract.

## Target Run Re-Audit

Before resume:

- run status: `HALT`
- next job: `2023-10-12:data_readiness`
- `2023-10-11` completed: YES
- `2023-10-12` completed: NO
- active Pending: prior-day `MIXED_SELL_ITEM_SCOPED_REVIEW`
- `2023-10-12/submit`: absent
- `2023-10-12/execution`: absent

92460 preservation:

- 2023-10-11 submit count: `1`
- execution submitted order count: `1`
- 92460 fill count: `1`
- ledger append evidence: `ledger_orders_appended=1`, `ledger_executions_appended=1`, `ledger_cash_appended=1`, `status=PASS`

50280 / 38560 / 76920:

- remain `REVIEW_REQUIRED`
- remain non-approved
- have no submit/execution authority in the active Pending
- are not carried as executable authority by the new rollover contract

## Resume Attempt

The requested same-run resume was attempted with:

```text
PYTHONPATH=src python3 scripts/runtime_test.py resume --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z --confirm --yes-i-understand-this-mutates-trading-state
```

It did not reach the repaired Pending lifecycle boundary. Runtime-test rejected the resume at the plan entry gate with:

`PRECONDITION_FAILURE`

Failed checks:

- `run_scoped_contract_authority_present`
- `run_scoped_contract_source_normal`
- `run_scoped_status_pass`
- `run_scoped_selected_feature_date_present`
- `run_scoped_selected_matches_plan`
- `run_scoped_selected_matches_profile_expected`

Reported feature-date reason:

`feature_date_contract_not_yet_materialized_plan_expectation_only`

After the failed resume attempt, the target run remained:

- `HALT`
- `next_job = 2023-10-12:data_readiness`
- no `2023-10-12` submit artifact
- no `2023-10-12` execution artifact
- 2023-10-11 remains completed

The workspace now has 2023-10-12 market-refresh/feature-date evidence present, but `runtime_test resume` still rejects because the run-scoped feature-date evidence required by the plan entry gate is not materialized in the form it expects. This is a separate runtime-test resume precondition issue, not the Phase32-BB Pending lifecycle defect.

## Same-Run Resume Safety

Lifecycle and side-effect safety: YES.

The repaired lifecycle contract can safely expire the prior-day mixed residual Pending and preserve 2023-10-11/92460 evidence. The target run should continue from:

`2023-10-12:data_readiness`

without replaying 2023-10-11.

Operational resume through current `runtime_test resume`: NOT ACCEPTED YET.

The actual resume command is blocked before reaching data readiness by a separate run-scoped feature-date plan entry gate precondition. A fresh run is not required by the BC evidence, but the existing run cannot currently be advanced via plain `runtime_test resume` until that entry-gate precondition is satisfied or repaired canonically.

## Required Final Answers

- `ROOT_CAUSE_REPAIRED`: YES.
- `MIXED_REVIEW_PENDING_DAY_ROLLOVER_CONTRACT_IMPLEMENTED`: YES.
- `PRIOR_DAY_AUDIT_EVIDENCE_PRESERVED`: YES.
- `REVIEWED_ITEMS_CARRY_EXECUTABLE_AUTHORITY`: NO.
- `CURRENT_DAY_FRESH_AUTHORITY_REQUIRED`: YES.
- `50280_SUBMITTED_FROM_STALE_AUTHORITY`: NO.
- `38560_76920_SUBMITTED_FROM_STALE_AUTHORITY`: NO.
- `92460_STATE_PRESERVED`: YES.
- `FAIL_CLOSED_BEHAVIOR_PRESERVED`: YES.
- `FOCUSED_REGRESSION_RESULT`: PASS, `143 passed` across focused lifecycle, data-readiness orchestration, AX/BA adjacent, safety authority, partial-submit, and G129 suites.
- `2023_10_12_FOCUSED_REPRODUCTION_RESULT`: PASS on copied runtime root; data readiness returned `0`.
- `TARGET_RUN_RESUME_EXECUTED`: ATTEMPTED, but blocked before mutation by runtime-test plan entry gate.
- `2023_10_12_DATA_READINESS_PASS_ON_TARGET_RUN`: NOT YET; plain resume did not reach data readiness.
- `2023_10_12_COMPLETED`: NO.
- `2023_10_13_REACHED`: NO.
- `FRESH_RUN_REQUIRED`: NO by BC lifecycle evidence.
- `SAME_RUN_RESUME_SAFE`: YES at lifecycle/side-effect level after resolving the separate run-scoped feature-date entry-gate precondition; not currently accepted by plain `runtime_test resume`.
- `ANY_STRATEGY_BEHAVIOR_CHANGE`: NO.
- `ANY_PRODUCTION_SEMANTIC_CHANGE`: NO Strategy/decision semantic change; Runtime lifecycle authority is narrowed to an audited prior-day residual shape.

## Final Judgment

`PHASE32_BC_MIXED_REVIEW_PENDING_DAY_ROLLOVER_LIFECYCLE_REPAIRED_RESUME_BLOCKED_BY_RUN_SCOPED_FEATURE_DATE_ENTRY_GATE`

Same-run resume safety is confirmed for the repaired Pending lifecycle boundary: preserve 2023-10-11, preserve 92460 exactly once, and continue from `2023-10-12:data_readiness`.

However, the actual target run has not advanced because `runtime_test resume` currently fails a separate plan entry gate before reaching the repaired boundary. The next canonical work item is to resolve the run-scoped feature-date resume precondition for `2023-10-12` without replaying 2023-10-11 or duplicating 92460.
