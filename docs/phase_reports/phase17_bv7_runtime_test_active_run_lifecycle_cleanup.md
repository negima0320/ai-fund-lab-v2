# Phase17-BV7 Runtime Test Active Run Lifecycle Cleanup

## Executive Summary

Final judgment: `PHASE17_BV7_ACTIVE_RUN_LIFECYCLE_ACCEPTED`

Runtime Test `status` was resolving the active run from the newest `reports/runtime_tests/runs/*/run_state.json` by mtime. It did not filter by profile and did not consult the close marker `final_summary.json`. Therefore a closed `historical-smoke` HALT run was still shown as the active run for `historical-extended-smoke`.

This was classified as:

- `STATUS_OBSERVABILITY_DEFECT`
- `PROFILE_ISOLATION_DEFECT`
- `ACTIVE_RUN_LIFECYCLE_DEFECT`

No Frozen Run evidence, existing run directory, or `.runtime` state was edited.

## Root Cause

`scripts/runtime_test.py::status()` used `latest_run(evidence_root)`.

`latest_run()` sorts all `run_state.json` files by mtime and returns the first payload. The resolver is history-oriented, not active-lifecycle-oriented. It ignores:

- `profile_id`
- `final_summary.json`
- `closed_at`
- whether the run is still resumable

The old run had:

- `run_state.json.status = HALT`
- `run_state.json.profile_id = historical-smoke`
- `run_state.json.next_job = 2026-06-29:market_refresh`
- `final_summary.json.status = PASS`
- `final_summary.json.closed_at = 2026-07-16T06:18:10.346563Z`

Thus the run was closed, but status still selected its HALT `run_state.json`.

## Close Contract

Close preserves historical run evidence and writes `final_summary.json`. It does not rewrite `run_state.json` from `HALT` to a closed status. This is acceptable if consumers treat `final_summary.json.closed_at` as the lifecycle close marker.

The defect was in the status/resume consumers, not in the closed run evidence.

## Reset Contract

Reset restores clean runtime state but does not delete historical run evidence. After a clean reset, status should report no active run unless an unclosed run for the same profile is present.

After the fix, `status --profile historical-extended-smoke --json` reports:

- `active_test_run = ""`
- `run_status = IDLE`
- `next_job = ""`

## Fix Boundary

Implemented:

- Added profile-scoped active run resolver.
- Added closed-run detection using `final_summary.json.closed_at`.
- Updated `status()` to use the active resolver and report `IDLE` when no active run exists.
- Added `resume_command()` preflight rejection for closed runs.
- Added fixture-only tests for closed HALT exclusion, profile isolation, unclosed same-profile HALT visibility, and closed resume rejection.

Not changed:

- Existing run evidence.
- `.runtime` state.
- Ledger/current/pending.
- Runtime Test run/resume/reset/rollback/close execution.

## Resume Safety

An explicitly requested closed run is now rejected before baseline checks or any mutation path:

`resume rejected; run is closed: <run_id>`

There is no automatic resume target selection in this runner path, and closed runs are no longer exposed by status as active candidates.

## Verification

Commands executed:

- `PYTHONPATH=src python3 scripts/runtime_test.py status --profile historical-extended-smoke --json`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv7_runtime_test_active_run_lifecycle_cleanup.py`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv7_runtime_test_active_run_lifecycle_cleanup.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase17_al_runtime_test_clean_baseline_guard.py tests/runtime_v2/test_phase17_bp_clean_reset_plan_feature_date_entry_gate.py tests/runtime_v2/test_phase17_bv6_historical_replay_operator_range.py`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase17_bv7_pycache PYTHONPATH=src python3 -m py_compile scripts/runtime_test.py`
- `git diff --check`

Results:

- BV7 targeted tests: `4 passed`
- Related Runtime Test regression: `38 passed`
- Full `tests/runtime_v2`: `910 passed`
- `py_compile`: PASS
- `git diff --check`: PASS

## Prohibited Operations Confirmation

Not executed:

- Runtime Test `run`
- Runtime Test `resume`
- Runtime Test `reset`
- Runtime Test `rollback`
- Runtime Test `close`
- Frozen Run evidence edit
- Past run directory deletion
- `.runtime` manual edit
- Ledger manual edit
- Registry refresh
- J-Quants fetch
- Broker write
- Order submit
- External notification

