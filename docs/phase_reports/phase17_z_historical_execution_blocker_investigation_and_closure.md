# Phase17-Z Historical Execution Blocker Investigation and Closure

Final judgment: `PHASE17_Z_HISTORICAL_EXECUTION_ACCEPTED`

## Scope

This closure investigated the frozen failed run:

```text
runtime-test-historical-smoke-20260715T001218345482Z
```

The current clean plan was not run. No reset, rollback, restore, submit job, execution job, Demo broker write, Production access, J-Quants fetch, canonical update, feature artifact edit, or Registry update was executed during this investigation.

## Evidence Read

Read-only target evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T001218345482Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T001218345482Z/plan.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T001218345482Z/final_summary.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T001218345482Z/daily/2026-07-06/`

Relevant backups were inspected read-only:

- `reports/runtime_tests/backups/backup-historical-smoke-20260715T001152110893Z/`
- `reports/runtime_tests/backups/backup-historical-smoke-20260715T002718431720Z/`

`docs/phase_reports/runtime_test_specification.md` was requested but does not exist. The accepted contract exists at `docs/02_architecture/runtime_test_specification.md` and was read.

## Direct Failure

The target run completed:

1. `market_refresh`
2. `data_readiness`
3. `morning`
4. `sell_planning`
5. `submit`

It stopped at:

```text
business_date=2026-07-06
job=execution
runtime_cli_exit_code=20
runner_status=HALT
```

The direct Runner reason is:

```text
Runtime CLI stopped at 2026-07-06:execution with exit code 20
```

The target run does not contain `daily/2026-07-06/execution/`. Therefore the frozen evidence proves the non-zero boundary but does not contain the execution stage details needed to fully reconstruct the internal `REVIEW_REQUIRED` fields. That absence is itself an evidence completeness bug.

## Root Cause

Classification:

- `Case B: Execution common processing implementation gap`
- `Case C: Evidence/Runner judgment inconsistency`
- `Case E: Runtime Test orchestration/reset-scope inconsistency`
- `Case G: composite`

Closed causes:

- Execution Current/Reconcile ordering: accepted Runtime-owned fills must project/apply Current before post-execution reconciliation decides success for non-demo modes.
- Historical cash authority: Historical execution snapshot cash/buying_power must derive from starting Current cash plus accepted fill `cash_effect`, not a fixed zero value.
- Reset scope: `runtime_state/historical_broker` is mutable Historical broker execution evidence and must be reset/backup scoped.
- Run-scoped evidence: Execution jobs must write run-scoped execution evidence just like Morning and Sell Planning.

This is not a simple path-string mismatch. The important mismatches were evidence identity/scope and execution state authority.

## Fixes

Updated:

- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`

The changes are production-common Runtime contract fixes. They do not add a Historical-only PASS, skip reconciliation by mode, or convert `exit_code=20` to success.

## Evidence Added

Created:

- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/read_audit.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/target_run_execution_trace.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/execution_failure_classification.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/submitted_order_identity.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/historical_fill_authority.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/ledger_current_apply_trace.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/pending_terminalization_trace.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/runner_exit_code_analysis.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/external_effect_audit.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/test_summary.json`
- `reports/phase17_z_historical_execution_blocker_investigation_and_closure/authority_decision.json`
- `reports/phase_reports/phase17_z_historical_execution_blocker_investigation_and_closure.json`

## Validation

Limited fixture/regression tests only:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py
```

Result:

```text
22 passed
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pytest_cache/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py
```

Result: `PASS`

## Operations Not Performed

- No `scripts/runtime_test.py run`
- No `scripts/runtime_test.py resume`
- No new 5BD execution
- No reset / restore / rollback
- No Submit job execution
- No Execution job execution
- No target failed run mutation
- No clean plan execution
- No Demo broker write
- No Production broker access
- No J-Quants API fetch
- No Registry update

## Recommended Next Prefix

Use the clean lifecycle from the terminal. The user should run it explicitly; Codex should not run it for this phase:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run --profile historical-smoke --run-id runtime-test-historical-smoke-20260715T003301564910Z --confirm --yes-i-understand-this-mutates-trading-state --json
```
