# Phase17-AC Runtime Artifact Schema Identity Cleanup

## Judgment

`PHASE17_AC_RUNTIME_ARTIFACT_SCHEMA_IDENTITY_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T015929082437Z` was not modified and was not rerun or resumed.

## Root Cause

Runtime Test Runner and Historical Runtime support artifacts were promoted from Phase work into ongoing Runtime usage while retaining Phase-number schema identities. This was not a runtime execution bug, but it made permanent Runtime contracts look like temporary Phase artifacts.

## Renamed Runtime Schemas

- `phase17_k_runtime_test_runner_v1` -> `runtime_test_runner_v1`
- `phase17_k_run_state_v1` -> `runtime_test_run_state_v1`
- `phase17_k_runtime_test_plan_v1` -> `runtime_test_plan_v1`
- `phase17_k_backup_manifest_v1` -> `runtime_test_backup_manifest_v1`
- `phase17_k_reset_manifest_v1` -> `runtime_test_reset_manifest_v1`
- `phase17_k_final_summary_v1` -> `runtime_test_final_summary_v1`
- `phase17_l_historical_asof_view_v1` -> `runtime_historical_asof_view_v1`
- `phase17_m_historical_logical_input_v1` -> `runtime_historical_logical_input_v1`
- `phase17_m_historical_logical_input_manifest_v1` -> `runtime_historical_logical_input_manifest_v1`
- `phase17_b1_regression_baseline.v1` -> `runtime_historical_regression_baseline_v1`
- `phase17_b1_trading_state_reset_plan.v1` -> `runtime_historical_trading_state_reset_plan_v1`
- `phase17_b1_reset_plan_validation.v1` -> `runtime_historical_reset_plan_validation_v1`
- `phase17_b1_entry_gate_evaluation.v1` -> `runtime_historical_entry_gate_evaluation_v1`
- `phase17_g_historical_submission_evidence_v1` -> `runtime_historical_submission_evidence_v1`

The Runtime Test CLI response now stays `runtime_test_runner_v1`; embedded artifacts keep their own schema via explicit fields such as `runtime_test_plan_schema_version`.

## Legacy Compatibility

Read-only legacy aliases were added for existing Frozen Evidence:

- `phase17_k_run_state_v1`
- `phase17_k_runtime_test_plan_v1`
- `phase17_k_backup_manifest_v1`
- `phase17_l_historical_asof_view_v1`

Unknown schemas fail closed. There is no wildcard `phase*` acceptance and no `startswith("phase17")` logic.

## Residual Scan

Runtime writer Phase schema count: `0`

Runtime current contract Phase identifier count: `0`

Legacy read alias count: `4`

Remaining Phase identifiers are limited to test names/fixtures and explicit legacy aliases. Phase reports and Phase scripts are intentionally out of Runtime writer scope.

## Verification

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ac_schema_identity_cleanup.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py
```

Result: `20 passed`

Extended regression passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ac_schema_identity_cleanup.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_b1_historical_support.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
```

Result: `31 passed`

Passed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase17ac_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py src/ai_fund_lab_v2/runtime_v2/historical_support/baseline.py src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py src/ai_fund_lab_v2/runtime_v2/historical_support/gates.py src/ai_fund_lab_v2/runtime_v2/historical_support/__init__.py src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py tests/runtime_v2/test_phase17_ac_schema_identity_cleanup.py
```

## Evidence

Evidence directory:

`reports/phase17_ac_runtime_artifact_schema_identity_cleanup/`

Files:

- `schema_inventory.json`
- `schema_classification.json`
- `schema_rename_map.json`
- `legacy_compatibility_matrix.json`
- `unknown_schema_fail_closed_test.json`
- `runtime_phase_identifier_residual_scan.json`
- `test_results.json`
- `external_effect_audit.json`

Machine-readable summary:

`reports/phase_reports/phase17_ac_runtime_artifact_schema_identity_cleanup.json`

## External Effects

- Frozen Evidence modified: no
- Runtime Test run/resume/reset/rollback/backup/close on real state: no
- Runtime state mutation: no
- Pending mutation: no
- Persistent Ledger mutation: no
- J-Quants fetch: no
- Broker write: no
- Demo write: no
- Production access: no
- Submit/execution: no
- External notification: no

The next Runtime Test may be rerun only after this static schema cleanup is reviewed; this phase itself did not unblock or fix the frozen `2026-07-07:market_refresh` blocker.
