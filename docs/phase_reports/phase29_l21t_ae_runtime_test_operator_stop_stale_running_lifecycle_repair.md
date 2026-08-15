# Phase29-L21T-AE - Runtime Test Operator Stop / Stale RUNNING Lifecycle Repair

Task ID: `Phase29-L21T-AE`

Primary Judgment:

```text
PHASE29_L21T_AE_RUNTIME_TEST_OPERATOR_STOP_LIFECYCLE_REPAIRED_FOCUSED_REGRESSION_PASS
```

Current Phase:

```text
Phase29
```

Phase30 entered:

```text
NO
```

## Scope

This task repairs Runtime Test operator lifecycle only. It does not change Strategy, Portfolio Construction, Position Sizing, BUY Planning, Sell Planning, Pending trading lifecycle, Submit, Execution, Broker adapter, Safety, Market Context, Candidate Selection, or Performance logic.

Target run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Codex did not mutate the target run and did not run resume, replay, recovery, fresh-run, long Historical, or 100BD validation.

## Task ID Check

`Phase29-L21T-AE`, `L21T-AE`, and `PHASE29_L21T_AE` were not found in repo docs/src/tests/scripts before implementation.

## Root Cause Audit

State authority findings:

- `run-status` / `status` reads profile-scoped active state via `active_run_for_profile(...)`.
- `active_run_for_profile(...)` scans run-scoped `run_state.json` files and returns the newest non-closed `RUNNING` or `HALT` run for the profile.
- `show --run-id` reads the requested run-scoped `run_state.json`.
- `abandon` reads the requested run-scoped `run_state.json` and rejects direct `RUNNING` abandon unless an internal stale-running override is used.
- No public `stop` CLI existed before AE.

RUNNING definition:

```text
Persisted run lifecycle has not reached HALT, COMPLETED, CLOSED, or ABANDONED.
```

The Runtime Test runner executes normal Runtime v2 jobs as foreground subprocesses. No background worker registry, active execution owner pointer, or daemon stop channel exists in the current architecture. A stale `RUNNING` can therefore remain after external interruption.

Existing stop/halt path:

- Runtime job failure and explicit runner failures materialize `HALT`.
- `abandon --allow-stale-running` had an internal conversion path to HALT, but normal operator abandon still rejected RUNNING.
- No `stop`, `pause`, `cancel`, `operator-abort`, or equivalent public lifecycle command was available.

Abandon preconditions:

- Direct `HALT` can be abandoned.
- Already abandoned is idempotent.
- Direct `RUNNING` remains rejected.
- Closed / completed / unrelated states are rejected.

## Root Cause Classification

```text
E_MULTI_CAUSAL
  A: Missing Operator Stop CLI
  B: State Authority Divergence
  C: Stale RUNNING Persistence
  D: Documentation / CLI Contract Mismatch
```

Regression confirmed:

```text
YES
```

The contract said `RUNNING` must be halted or stopped before abandon, but no public `stop` command existed.

## Repair

Added:

```text
PYTHONPATH=src python3 scripts/runtime_test.py stop --run-id <RUN_ID> --dry-run
PYTHONPATH=src python3 scripts/runtime_test.py stop --run-id <RUN_ID> --confirm --yes-i-understand-this-mutates-trading-state
```

State model selected:

```text
No new top-level STOPPED status.
RUNNING -> HALT
halted_at.runtime_test_job_status = OPERATOR_STOPPED
halted_at.operator_stop = true
```

Why:

- Existing architecture already treats `HALT` as resume-compatible and abandon-compatible.
- Adding a new top-level state would require broader state-machine changes.
- Operator stop is a lifecycle explanation, not a new trading outcome.

Resume semantics:

```text
Option A selected.
Stopped HALT is resume-capable if normal resume baseline gates pass.
```

Abandon semantics:

```text
RUNNING -> stop -> HALT(OPERATOR_STOPPED) -> abandon
```

Direct `RUNNING -> abandon` remains rejected.

## Safety

Operator stop does not:

- roll back Ledger;
- roll back Current;
- delete Pending;
- delete Execution evidence;
- delete daily evidence;
- rewrite completed business days;
- alter performance evidence;
- access Broker;
- write Broker;
- change accepted generation;
- change Strategy / Trading logic.

It only updates run-scoped lifecycle evidence in `run_state.json`.

## Changed Files

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md`
- `docs/phase_reports/phase29_l21t_ae_runtime_test_operator_stop_stale_running_lifecycle_repair.md`

## Regression Results

Focused AE + status/auto-abandon regression:

```text
8 passed
```

Coverage:

- R1 RUNNING -> stop -> HALT(OPERATOR_STOPPED)
- R2 stop dry-run no mutation
- R3 stopped run -> abandon allowed
- R4 direct RUNNING abandon remains rejected
- R5 double stop idempotent
- R6 ABANDONED run stop rejected
- R7 unknown run stop rejected
- R8 daily evidence preserved
- R9 resume dry-run compatible
- R10 run-status / show observability consistent and explainable

Runtime Test runner regression:

```text
44 passed
```

Abandon regression:

```text
6 passed
```

Changed Python `py_compile`:

```text
PASS
```

`git diff --check`:

```text
PASS
```

## Documentation

Updated Runtime Test Command Guide:

```text
docs/03_operations/runtime_test_command_guide.md
```

Updated Common Runtime Test lifecycle SoT:

```text
docs/02_architecture/runtime_test_specification.md
```

Updated roadmap and Phase30 entry evidence note:

```text
docs/01_requirements/phase_roadmap.md
docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md
```

## Operator Commands For Target Run

Codex did not run these commands. Operator may use them after reviewing this repair:

Dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py stop \
  --run-id runtime-test-historical-smoke-20260812T212155604711Z \
  --dry-run
```

Actual stop:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py stop \
  --run-id runtime-test-historical-smoke-20260812T212155604711Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Then abandon dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id runtime-test-historical-smoke-20260812T212155604711Z \
  --dry-run
```

Actual abandon, if operator chooses not to resume:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id runtime-test-historical-smoke-20260812T212155604711Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Final Judgment

```text
PHASE29_L21T_AE_RUNTIME_TEST_OPERATOR_STOP_LIFECYCLE_REPAIRED_FOCUSED_REGRESSION_PASS
```
