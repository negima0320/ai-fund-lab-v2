# Phase19-BJ Runtime Test HALT Run Abandon / Clear Contract

## Final Judgment

```text
PHASE19_BJ_RUNTIME_TEST_HALT_RUN_ABANDON_CONTRACT_COMPLETE
```

## Root Cause

`active_run_for_profile()` treated `RUNNING` and `HALT` runs as active unless
`final_summary.json` contained `closed_at`. A HALT run that had been rolled back
or reset therefore remained active forever when the operator did not intend to
resume it.

## Implementation

Added the formal operator command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id <RUN_ID> \
  --dry-run
```

Actual:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id <RUN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Actual abandon preserves `run_state.json` as the original HALT evidence and
writes:

```text
abandonment.json
final_summary.json
```

with `status=ABANDONED`, `final_judgment=ABANDONED`,
`resume_disabled=true`, `evidence_preserved=true`, and
`trading_state_mutated=false`.

## Active Run

Active detection now excludes:

```text
closed_at exists
abandoned_at exists
status = ABANDONED
valid abandonment.json
```

`RUNNING` and non-abandoned `HALT` runs remain active. `RUNNING` abandon is
rejected. Re-abandon is idempotent.

## Target Run Dry-run

Verified read-only:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id runtime-test-historical-smoke-20260721T012456836804Z \
  --dry-run --json
```

Result:

```text
status = DRY_RUN
active_run = true
abandonment_possible = true
trading_state_mutation = false
files_to_modify = []
```

Codex did not execute Actual abandon for the shared target run.

## Regression

```text
py_compile = PASS
pytest = 36 passed
```

## Non-mutation

No shared Runtime Trading State mutation, Broker access, Broker write, external
delivery, Accepted Generation change, Registry change, or evidence deletion was
performed. Actual tests used isolated pytest Runtime Roots.

## Evidence

```text
reports/phase19_bj_runtime_test_halt_run_abandon_contract/root_cause_analysis.json
reports/phase19_bj_runtime_test_halt_run_abandon_contract/abandon_contract.json
reports/phase19_bj_runtime_test_halt_run_abandon_contract/active_run_detection_contract.json
reports/phase19_bj_runtime_test_halt_run_abandon_contract/dry_run_result.json
reports/phase19_bj_runtime_test_halt_run_abandon_contract/non_mutation.json
reports/phase19_bj_runtime_test_halt_run_abandon_contract/regression_results.json
reports/phase19_bj_runtime_test_halt_run_abandon_contract/final_judgment.json
```
