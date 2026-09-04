# Phase32-EA — Canonical Same-Run Source Transition / Resume Continuation Implementation

## Summary

Implemented a canonical `runtime_test.py transition-source-baseline` command that records an explicit source-generation transition for a halted Historical Runtime Test run without replaying completed business days or bypassing the normal resume baseline guard.

This is a control/provenance repair only. No Strategy, PM, PC, PS, BUY, SELL, BQ, DQ, cash, threshold, weight, ranking, or trading semantic logic was changed.

## Implementation

- Command added: `transition-source-baseline`.
- Required inputs:
  - `--run-id`
  - `--reason`
  - `--operator`
  - `--confirm`
  - `--yes-i-understand-this-mutates-trading-state` for actual mutation
  - optional `--audit-id`
  - optional repeated `--repair-report`
  - optional `--expected-old-source-commit`
  - optional `--expected-new-source-commit`
  - optional `--performance-continuity-classification`
- Dry-run support:
  - compares old and current baselines
  - reports changed baseline keys
  - reports registry and accepted-artifact hash continuity
  - reports completed-day preservation proof
  - reports failed-job retry point
  - reports target-day side-effect safety
  - proposes the immutable source-transition artifact path
  - performs no mutation
- Actual command behavior:
  - materializes an immutable `runtime_test_source_transition_v1` artifact under `source_transitions/`
  - appends one entry to `run_state.source_transitions[]`
  - updates only `run_state.source_baseline` and transition/performance-purity metadata
  - preserves `next_job` so the failed job is retried
  - verifies completed-day artifact proof after writing

## Files Changed

- `scripts/runtime_test.py`
  - Added `SOURCE_TRANSITION_SCHEMA_VERSION`.
  - Added CLI parser and dispatch for `transition-source-baseline`.
  - Added source-transition planning, artifact, authority, side-effect, and idempotency helpers.
- `tests/runtime_v2/test_phase32_ea_source_transition_baseline.py`
  - Added focused command/guard regression coverage.

## Contract

`resume` still rejects unrecorded source baseline mismatch. The new canonical continuation path is:

1. Dry-run the explicit transition.
2. Apply the explicit transition with operator confirmation.
3. Run normal `resume`.

The transition command does not infer Strategy semantic equivalence from git diff. It records `performance_continuity_classification` separately from resume permission.

Registry and accepted-artifact authority remain separate. If `registry_hash` or `accepted_artifact_hash` changes, the source transition rejects with `PRECONDITION_FAILURE`; a separate canonical authority update is required.

## Target Dry-Run

Target run:

`runtime-test-historical-extended-smoke-20260902T060955933565Z`

Dry-run result:

- status: `DRY_RUN`
- exit_code: `0`
- target run mutated: `NO`
- source transition artifact created: `NO`
- `source_transitions/` directory exists after dry-run: `NO`
- run_state baseline after dry-run remains: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- next_job after dry-run remains: `2023-12-11:morning`
- completed_business_days after dry-run remains: `293`

Baseline diff:

- old `source_commit`: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- new `source_commit`: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
- changed baseline keys: `source_commit`
- old/new `source_dirty`: `true` / `true`
- registry hash unchanged: `YES`
- accepted artifact hash unchanged: `YES`
- registry hash: `4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`
- accepted artifact hash: `5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`

Completed-day proof:

- completed business days: `293`
- first completed business day: `2022-10-03`
- last completed business day: `2023-12-08`
- missing completed-day artifact dirs: `[]`
- completed day artifact inventory hash: `766d93149992e2fb19ed68eeeca21ecefa9cad6dc0c540fdeaea0f56f58c7c8a`

Retry boundary:

- restart point: `2023-12-11:morning`
- later job evidence on `2023-12-11`: absent for `sell_planning`, `submit`, `execution`, `current_valuation_refresh`, `runtime_state_refresh`
- target-date ledger side effects on `2023-12-11`: `0` orders, `0` executions, `0` positions, `0` cash, `0` events
- target retry boundary safe: `PASS`

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ea python3 -m py_compile scripts/runtime_test.py tests/runtime_v2/test_phase32_ea_source_transition_baseline.py
```

Result: `PASS`

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ea python3 -m pytest -q tests/runtime_v2/test_phase32_ea_source_transition_baseline.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase17_k_resume_rejects_changed_source_baseline tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase17_k_resume_uses_fixed_plan_without_skipping_failed_job
```

Result: `11 passed`

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/pycache-phase32-ea python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase17_k_run_dry_run_never_executes_runtime_cli
```

Result: `1 passed`

Focused coverage:

- source mismatch rejection before transition: `PASS`
- dry-run no mutation: `PASS`
- successful fixture transition: `PASS`
- append-only transition history: `PASS`
- idempotency for already-current baseline: `PASS`
- stale expected old-baseline rejection: `PASS`
- registry/accepted authority mismatch rejection: `PASS`
- completed-day immutability: `PASS`
- failed-job retry preservation: `PASS`
- unsafe submit/execution boundary rejection: `PASS`
- resume dry-run acceptance after transition: `PASS`
- normal run dry-run path remains unchanged: `PASS`

## Required Answers

- `SOURCE_TRANSITION_COMMAND_IMPLEMENTED`: `YES`
- `OLD_NEW_BASELINE_DIFF_EXPLICIT`: `PASS`
- `SOURCE_TRANSITION_PROVENANCE_ARTIFACT`: `PASS`
- `COMPLETED_DAY_ARTIFACTS_REWRITTEN`: `NO`
- `FAILED_JOB_RETRY_PRESERVED`: `YES`
- `TARGET_RETRY_BOUNDARY_SAFE`: `PASS`
- `AUTHORITY_BASELINE_SEPARATE_FROM_SOURCE_TRANSITION`: `PASS`
- `SOURCE_TRANSITION_HISTORY_APPEND_ONLY`: `PASS`
- `POST_TRANSITION_SOURCE_AUTHORITY`: `CURRENT_ACCEPTED_TRANSITION_BASELINE`
- `PERFORMANCE_PURITY_SEPARATE_FROM_RESUME_PERMISSION`: `PASS`
- `SOURCE_DIFF_AUTO_SEMANTIC_APPROVAL`: `NO`
- `ITERATIVE_HISTORICAL_REPAIR_WORKFLOW_SUPPORTED`: `YES`
- `UNRECORDED_SOURCE_MISMATCH_STILL_REJECTED`: `YES`
- `SOURCE_TRANSITION_DRY_RUN`: `PASS`
- `SOURCE_TRANSITION_IDEMPOTENCY`: `PASS`
- `SOURCE_TRANSITION_FAIL_CLOSED_GATES`: `PASS`
- `TARGET_SOURCE_TRANSITION_DRY_RUN`: `PASS`
- `TARGET_SOURCE_TRANSITION_EXECUTED_BY_CODEX`: `NO`
- `POST_TRANSITION_RESUME_PATH_DEFINED`: `PASS`
- `FRESH_RUN_REQUIRED`: `NO`, provided the source transition succeeds
- `TRADING_SEMANTICS_CHANGED`: `NO`
- `PRODUCTION_CHANGE_EXECUTED`: `NO`
- `TARGET_RUN_MUTATED`: `NO`
- `LONG_RUNTIME_EXECUTED`: `NO`

## User Commands

Recommended dry-run:

```bash
NEW_COMMIT="$(git rev-parse HEAD)"
PYTHONPATH=src python3 scripts/runtime_test.py transition-source-baseline \
  --profile historical-extended-smoke \
  --run-id runtime-test-historical-extended-smoke-20260902T060955933565Z \
  --reason "Phase32-DY non-authoritative DW shadow builder isolation accepted; record explicit source transition before retrying 2023-12-11 morning" \
  --operator negishi \
  --audit-id phase32-ea-source-transition \
  --repair-report docs/phase_reports/phase32_dx_20231211_morning_halt_post_dw_root_cause_read_only_audit.md \
  --repair-report docs/phase_reports/phase32_dy_dw_shadow_failure_isolation_morning_continuation_production_repair.md \
  --expected-old-source-commit a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd \
  --expected-new-source-commit "$NEW_COMMIT" \
  --dry-run
```

If the dry-run returns `DRY_RUN` / exit `0`, apply the transition:

```bash
NEW_COMMIT="$(git rev-parse HEAD)"
PYTHONPATH=src python3 scripts/runtime_test.py transition-source-baseline \
  --profile historical-extended-smoke \
  --run-id runtime-test-historical-extended-smoke-20260902T060955933565Z \
  --reason "Phase32-DY non-authoritative DW shadow builder isolation accepted; record explicit source transition before retrying 2023-12-11 morning" \
  --operator negishi \
  --audit-id phase32-ea-source-transition \
  --repair-report docs/phase_reports/phase32_dx_20231211_morning_halt_post_dw_root_cause_read_only_audit.md \
  --repair-report docs/phase_reports/phase32_dy_dw_shadow_failure_isolation_morning_continuation_production_repair.md \
  --expected-old-source-commit a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd \
  --expected-new-source-commit "$NEW_COMMIT" \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Then resume normally:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --run-id runtime-test-historical-extended-smoke-20260902T060955933565Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Next Recommended Step

User should execute the dry-run command first, then the confirmed transition command only if the dry-run remains `DRY_RUN` / exit `0`, then normal resume.

## Final Judgment

`PHASE32_EA_CANONICAL_SAME_RUN_SOURCE_TRANSITION_IMPLEMENTED_TARGET_DRY_RUN_PASS_READY_FOR_USER_APPLIED_TRANSITION`
