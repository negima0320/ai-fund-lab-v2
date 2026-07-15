# Phase17-AL Runtime Test Clean Baseline / Cross-Run Contamination Guard

## Final Judgment

`PHASE17_AL_RUNTIME_TEST_CLEAN_BASELINE_GUARD_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T071246088595Z` was left unchanged. I did not run `runtime_test.py run/resume/reset/rollback/backup/close`, did not edit Pending/Ledger/Current manually, and did not execute broker, submit, execution, notification, J-Quants, or retraining flows.

## Root Cause

Confirmed failure:

- New run: `runtime-test-historical-smoke-20260715T071246088595Z`
- Requested start date: `2026-07-06`
- Existing Pending origin run: `runtime-test-historical-smoke-20260715T063047874126Z`
- Existing Pending target date: `2026-07-07`
- Existing safety business date: `2026-07-07`
- Data Readiness reason: `historical_safety_temporal_authority_missing`
- Pending authority reason: `historical_pending_safety_authority_mismatch`

Classification:

- A. Operator lifecycle misuse: a new plan/run was attempted without reset/rollback to a compatible baseline.
- B. Runner validation gap: `run` checked only for backup existence and required files.
- C. Backup semantics gap: backups did not expose whether they were clean baselines or mid-run states.
- D. Plan semantics gap: `plan` built a future run plan without surfacing current Runtime state incompatibility.

This is not an AK PM leakage issue. It is cross-run contamination in Runtime Test lifecycle state.

## Implemented Guard

`scripts/runtime_test.py` now has a shared baseline compatibility contract:

- `build_baseline_compatibility(...)`
- `inspect_runtime_test_state(...)`
- `baseline_mismatch_reasons(...)`
- `classify_backup_for_clean_baseline(...)`

`runtime_test.py run` now validates the baseline after confirmation but before creating `run_state.json` or executing the first Runtime CLI job. On mismatch it fail-closes:

```text
status: HALT
reason: runtime_test_clean_baseline_mismatch
next_operator_action: reset_or_rollback_to_compatible_backup
```

Guard checks:

- Current/runtime_state business date is not after requested start date.
- Ledger business date is not after requested start date.
- Pending target date is not after requested start date.
- Pending is not active.
- Pending does not contain a foreign runtime-test run id.
- Pending safety business date is not after requested start date.
- Safety artifact business date/run id is not future/foreign.
- Required Current/Ledger/Pending/Runtime State files exist.

No Historical-only bypass was added. The same compatibility helper classifies Production, Demo, and Historical state.

## Plan-Time Evidence

`runtime_test.py plan` now embeds `baseline_compatibility` in the plan payload.

If baseline state is incompatible, plan returns:

```text
PLAN_REVIEW_REQUIRED
```

The evidence includes:

- `baseline_compatibility_status`
- `requested_start_date`
- `current_state_date`
- `ledger_date`
- `pending_target_date`
- `pending_active`
- `pending_origin_run_id`
- `safety_authority_date`
- `compatible_backup_required`
- `recommended_backup_id`

`plan` remains read-only for Runtime trading state.

## Backup Inventory

Evidence inventory:

- `reports/phase17_al_runtime_test_clean_baseline_guard/backup_inventory.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/clean_baseline_candidate.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/rejected_backups.json`

Result:

- Total historical-smoke backups inspected: 22
- Clean candidate count for `2026-07-06` start: 1
- Recommended clean candidate: `backup-historical-smoke-20260715T031700494429Z`

Explicit requested backups:

- `backup-historical-smoke-20260715T055933965598Z`: rejected because it contains future current/runtime_state date and future Pending target date.
- `backup-historical-smoke-20260715T062952991771Z`: rejected because it contains future current/runtime_state date, future Pending target/safety dates, and a foreign run id.

The latest backup `backup-historical-smoke-20260715T071237940864Z` is also rejected because it contains Day2/future Pending state from `runtime-test-historical-smoke-20260715T063047874126Z`.

## Fail-Closed Examples

Regression coverage confirms fail-closed behavior for:

- terminal EMPTY Pending with future target date
- terminal EMPTY Pending with foreign run id
- active Pending
- future Current/runtime_state date
- future Ledger business date
- future Safety authority date
- foreign Safety run id
- Production/Demo/Historical mode with foreign runtime-test identity
- pre-run HALT before any Runtime CLI job executes
- backup classification rejecting mid-run states
- no-action terminal Pending distinguished from active Pending

## User Next Step

Do not resume or rerun frozen run `runtime-test-historical-smoke-20260715T071246088595Z`.

Suggested operator sequence after approval:

1. Restore/reset to a compatible baseline. Evidence currently recommends `backup-historical-smoke-20260715T031700494429Z` if rollback is preferred; otherwise use reset.
2. Run `runtime_test.py plan --write-evidence` and confirm `baseline_compatibility_status=PASS`.
3. Run `runtime_test.py run` only after the plan is PASS.

No reset or rollback was executed during Phase17-AL.

## Verification

Focused:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_al_runtime_test_clean_baseline_guard.py
16 passed
```

Related regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_al_runtime_test_clean_baseline_guard.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_ak_pm_leakage_audit_runtime_contract.py tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_w_historical_morning_capability.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py
117 passed
```

Final checks:

- `py_compile`: PASS
- `git diff --check`: PASS
- JSON validation: PASS

## Evidence

- `reports/phase17_al_runtime_test_clean_baseline_guard/frozen_run_root_cause.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/mismatched_state_matrix.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/backup_inventory.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/clean_baseline_candidate.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/rejected_backups.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/pre_run_guard_contract.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/plan_time_compatibility_contract.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/fail_closed_examples.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/common_runtime_contract.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/external_effect_audit.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/regression_test_results.json`
- `reports/phase17_al_runtime_test_clean_baseline_guard/next_operator_steps.json`

