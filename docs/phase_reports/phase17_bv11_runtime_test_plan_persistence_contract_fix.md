# Phase17-BV11 Runtime Test Plan Persistence Contract Fix

## Executive Summary

Phase17-BV11 fixed a Runtime Test Runner contract gap where `plan --json` could return `PASS` with a run_id and an expected run-scoped `plan.json` path while no persisted plan artifact existed for that exact run_id.

The root cause was in `scripts/runtime_test.py`: `plan_command()` only wrote `reports/runtime_tests/runs/<run_id>/plan.json` when `--write-evidence` was provided. The `historical-extended-smoke` operator command did not include that flag, so stdout succeeded but the exact-run plan artifact required by `run --run-id` was missing.

Final judgment:

```text
PHASE17_BV11_RUNTIME_TEST_PLAN_PERSISTENCE_CONTRACT_ACCEPTED
FRESH_RUN_SAFE
```

This judgment only means a fresh plan can now be persisted and used by a later exact-run `run --run-id` invocation. Runtime Test `run`, `resume`, `reset`, `rollback`, and `close` were not executed in this phase.

## Root Cause

The previous plan success path mixed two separate responsibilities:

- Building and printing a valid plan payload to stdout.
- Persisting the same plan under the exact run directory for later execution.

Only the stdout path was unconditional. File persistence was guarded by:

```python
if args.write_evidence:
    write_json_atomic(run_dir / "plan.json", plan_payload)
```

As a result, `plan --profile historical-extended-smoke --json` could report `status=PASS` while `reports/runtime_tests/runs/<run_id>/plan.json` did not exist. A following exact-run execution correctly failed closed with:

```text
runtime test plan not found for exact run_id
PRECONDITION_FAILURE
exit_code=70
```

## Affected Code Path

Before fix:

```text
plan_command
  -> build_plan
  -> validate_plan_entry_gate
  -> stdout JSON
  -> optional plan.json only when --write-evidence
```

After fix:

```text
plan_command
  -> build_plan
  -> validate_plan_entry_gate
  -> persist_runtime_test_plan
      -> write_json_atomic
      -> load_plan read-back
      -> validate_persisted_plan
      -> write validated persistence evidence
      -> final read-back validation
  -> stdout JSON
```

`status=PASS` and `exit_code=0` are now returned only after the run-scoped plan artifact exists and passes read-back validation.

## Contract Fix

The Runtime Test plan contract is now:

- Every successful `plan` invocation persists `reports/runtime_tests/runs/<run_id>/plan.json`.
- Persistence no longer depends on `--write-evidence`.
- The persisted path uses the exact run_id returned in stdout.
- `run --run-id` continues to load only `reports/runtime_tests/runs/<exact_run_id>/plan.json`.
- No latest-run fallback or profile-based guessing was introduced.
- Persistence failure is fail-closed as `PRECONDITION_FAILURE`, exit code `70`.

## Atomic Write Contract

`write_json_atomic()` now writes JSON using:

1. parent directory creation
2. temporary file write
3. flush
4. `fsync`
5. atomic replace

This shared writer is used by the new plan persistence path.

## Read-Back Validation

`persist_runtime_test_plan()` validates the saved artifact immediately after writing. The validation checks:

- file exists
- JSON read-back succeeds
- run_id matches stdout run_id
- profile_id matches requested profile
- schema_version matches
- source_commit matches
- business_dates match
- job_sequence matches
- canonical artifact hash matches

The final persisted `plan.json` also contains `plan_persistence` evidence.

## Profile Impact

This was a common Runtime Test Runner bug, not a Historical-only or Extended-only business rule. `historical-smoke` often avoided the failure because existing operator sequences used `--write-evidence`; `historical-extended-smoke` exposed the bug because the operator command omitted that flag.

No Production, Demo, broker, ledger, pending, or trading-state contract was changed.

## Start Date Verification

The current profile definition in `config/runtime_tests/historical_extended_smoke_10bd.json` has:

```json
{
  "window": {
    "date_from": "2026-07-06",
    "date_to": ""
  },
  "business_days": 10
}
```

The verified plan used:

```text
requested_start_date=2026-07-06
requested_end_date=2026-07-15
requested_business_days=8
```

The plan persistence defect is independent from the previous 2026-06-29 extended-smoke expectation. BV11 did not change the profile start date.

## Acceptance Plan Evidence

Command executed:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-extended-smoke \
  --json
```

Result:

```text
status=PASS
run_id=runtime-test-historical-extended-smoke-20260716T093412171794Z
plan_path=reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260716T093412171794Z/plan.json
```

Persisted plan validation:

```text
json.tool=PASS
plan_persistence.status=PASS
exists=true
read_back_valid=true
run_id_matches=true
profile_id_matches=true
schema_version_matches=true
source_commit_matches=true
business_dates_match=true
job_sequence_matches=true
artifact_hash=sha256:d5dfee27b48d7f0c1e16303b9deaea1f5d8c0b7167012e9e7c3ee8699b4229f4
```

## Tests

Targeted:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py
5 passed
```

Lifecycle and related regression:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py::test_phase17_ad_runner_requires_exact_existing_plan_run_id \
  tests/runtime_v2/test_phase17_bv6_historical_replay_operator_range.py \
  tests/runtime_v2/test_phase17_bv7_runtime_test_active_run_lifecycle_cleanup.py \
  tests/runtime_v2/test_phase17_bp_clean_reset_plan_feature_date_entry_gate.py \
  tests/runtime_v2/test_phase17_bq_run_feature_date_authority_boundary.py

30 passed
```

Full Runtime v2 regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2
932 passed
```

Static checks:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_bv11_pycache PYTHONPATH=src python3 -m py_compile \
  scripts/runtime_test.py \
  tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py

git diff --check
```

Both passed.

## Prohibited Operations Audit

The following were not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run edits
- `.runtime` manual edits
- Ledger/Pending manual edits
- broker write
- J-Quants fetch
- external notification

## Fresh Rerun Safety

Fresh run safety status:

```text
FRESH_RUN_SAFE
```

Reason:

- A fresh `historical-extended-smoke` plan now persists exact-run `plan.json`.
- The saved plan is valid JSON and read-back validated.
- The exact run_id lookup contract used by `run --run-id` is preserved.
- No fallback latest-plan behavior was added.

Operator may proceed in the next phase with the validated run_id or create a new fresh plan, subject to the normal operation sequence and user approval for actual Runtime Test execution.
