# Phase17-B1I-A Formal Historical Environment Composition Contract Amendment and Implementation

## Summary

Phase17-B1I-A formalized Historical Runtime as a Runtime environment composition:

```text
run_type=HISTORICAL
runtime_mode=historical
broker_environment=historical_simulated
runtime_root=.runtime
external_delivery=false
broker_write=false
```

The official CLI mode is `--mode historical`. `--mode simulation` is rejected as a non-formal Runtime environment and points operators to `--mode historical`.

## Contract Amendments

- `docs/02_architecture/historical_runtime_test_contract.md`
  - Added Phase17-B1I-A Historical Environment Composition Amendment.
  - Defined formal identity, required explicit `business_date` / `evaluation_time`, external-effect disablement, required manifest fields, and fail-closed behavior.
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
  - Added Historical Runtime Environment Composition section.
  - Defined lifecycle identity, adapter/provider authority, external-effect policy, and Demo/Production non-regression boundary.

## Implementation

- Added `runtime_v2.historical_support.environment`.
  - `resolve_environment_composition(...)`
  - `RuntimeEnvironmentComposition`
  - `HistoricalSubmitAdapter`
  - `HistoricalExecutionSnapshotProvider`
  - `EnvironmentCompositionError`
- CLI:
  - Added `--mode historical`.
  - Added `--broker-environment`.
  - Historical mode requires explicit `--business-date` and `--evaluation-time`.
  - Historical mode requires `--notification-mode payload-only`.
  - Historical mode rejects mode-rooted `.runtime/historical`.
  - Historical manifest fields are emitted only for historical runs.
- Submit:
  - Historical submit requires `HistoricalSubmitAdapter` from composition or returns `HALT`.
  - Tachibana settings/adapter loading is skipped for historical mode.
  - Submit Guard remains in place and is not bypassed.
- Execution:
  - Historical execution requires `HistoricalExecutionSnapshotProvider` from composition or returns `HALT`.
  - Default Tachibana snapshot provider remains Demo/Production only.

## Acceptance Gates

| Gate | Result |
|---|---:|
| `HISTORICAL_ENVIRONMENT_CONTRACT_ACCEPTED` | PASS |
| `HISTORICAL_MODE_FAIL_CLOSED` | PASS |
| `HISTORICAL_ADAPTER_ISOLATED` | PASS |
| `HISTORICAL_SNAPSHOT_PROVIDER_ISOLATED` | PASS |
| `EXTERNAL_EFFECTS_DISABLED` | PASS |
| `DEMO_COMPOSITION_UNCHANGED` | PASS |
| `PRODUCTION_COMPOSITION_UNCHANGED` | PASS |
| `SUBMIT_GUARD_UNCHANGED` | PASS |
| `EXECUTION_PROCESSOR_UNCHANGED` | PASS |
| `NORMAL_RUNTIME_ROOT_CONFIRMED` | PASS |
| `NO_ALTERNATE_MAINLINE` | PASS |
| `NO_RUNTIME_CORE_SEMANTIC_CHANGE` | PASS |

## Validation

Passed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase17_b1_historical_support.py
17 passed

PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py
7 passed
```

Exploratory broader scheduler run:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase14e7_launchd_daily_operation_rehearsal.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py
29 passed, 1 failed
```

The failed exploratory case is `test_phase14e11_cli_runs_all_scheduler_jobs_without_external_writes`; it reached the existing BUY AI producer with missing candidate/opportunity inputs and returned `REVIEW_REQUIRED`. It is not introduced by Historical composition and is not a Phase17-B1I-A acceptance gate.

## Out Of Scope Preserved

- No Trading State reset implementation.
- No Current/Ledger/Pending mutation for historical fills.
- No historical order execution or accepted fill model.
- No feature generation or canonical regeneration.
- No PM Artifact Acceptance or Registry mutation.
- No Tachibana API access, Demo submit, or Production access.
- No AI retraining or optimization.
- No standalone simulation harness promoted to mainline.

## Final Judgment

```text
PHASE17_B1I_A_HISTORICAL_COMPOSITION_ACCEPTED
```

Recommended next prefix:

```text
Phase17-B1I-B PM Adapter Authority Resolution
```
