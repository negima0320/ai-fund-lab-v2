# Phase20-G: Runtime Test CLI Responsibility Audit and Performance Observability Integration Design

## Executive Summary

Phase20-G audited the implemented `scripts/runtime_test.py` command surface and the existing operator documentation in `docs/03_operations/runtime_test_command_guide.md`.

No Runtime, AI, Opportunity, Position Management, Risk, Capital Allocation, Accepted Generation, Broker, Training, Calibration, Validation, or Historical Smoke behavior was changed.

Main decisions:

- `status` currently means Runtime Test runner status, not whole-system status.
- Future consolidation should use `run-status` as the canonical runner-state command and retain `status` as a deprecated compatibility alias.
- `system-status` should remain the canonical whole-system inspection command.
- `ai-status` should remain a specialist AI artifact and authority audit; `system-status --scope ai` should remain a system-scoped AI overview.
- Performance observability and position lifecycle analysis should be integrated into the existing `summarize` command through a future `--scope overview|performance|positions|lifecycle|full` option.
- A new `diagnose` command is not recommended unless a later phase defines distinct authority, output contract, or exit semantics.

Final judgment:

```text
PHASE20_G_CLI_RESPONSIBILITY_AUDIT_COMPLETE_INTEGRATION_DESIGN_READY
```

## Scope / Non-goals

Scope:

- Inventory all implemented Runtime Test CLI subcommands.
- Map each command to the operator question it answers.
- Audit naming overlap between `status`, `system-status`, and `ai-status`.
- Decide where Phase20 performance and position lifecycle observability should integrate.
- Update the formal operator command guide without adding duplicate documentation trees.

Non-goals:

- No command implementation.
- No alias implementation.
- No parser changes.
- No Runtime state mutation.
- No AI, PM, Opportunity, Risk, or Capital Allocation change.
- No Broker access.
- No long Historical Smoke, Full Backtest, Training, Calibration, or Validation.

## Reviewed Docs

- `docs/03_operations/runtime_test_command_guide.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase20_f_performance_improvement_candidate_identification.md`
- `docs/phase_reports/phase20_e_performance_diagnosis_and_attribution_report.md`
- `docs/phase_reports/phase20_d_trade_and_position_management_attribution_baseline.md`
- `docs/phase_reports/phase20_c_read_only_performance_baseline_extraction.md`
- `docs/phase_reports/phase20_b_performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase19_bv_runtime_test_summarize_and_trade_attribution_command.md`
- `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`
- `docs/phase_reports/phase19_ax_system_status_command.md`
- `docs/phase_reports/phase19_av_ai_authority_audit_command_and_runtime_readiness.md`

## Reviewed Implementation

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/ai_status.py`
- `src/ai_fund_lab_v2/runtime_v2/system_status.py`
- `schemas/runtime_test/ai_status_report.schema.json`
- `schemas/runtime_test/system_status_report.schema.json`
- Targeted tests under `tests/runtime_v2/`, especially Runtime Test runner, summarize, AI status, system status, fresh-run, abandon, isolated-root, and post-run context coverage.

## Complete Subcommand Inventory

Implemented subcommands:

```text
status
summarize
ai-status
system-status
prepare-isolated
plan
backup
reset
run
fresh-run
validate
resume
abandon
rollback
close
show
list-runs
list-backups
```

Implemented aliases / deprecated parser options:

| Item | Current State | Phase20-G Result |
|---|---|---|
| `system-status --full` | Alias for `--scope full` | Keep |
| `run --auto-prepare` | Parser accepts it, implementation rejects it as deprecated and incomplete | Keep rejected; `fresh-run` is canonical |
| `run-status` | Not implemented | Recommend future canonical alias for current `status` behavior |
| `status` as deprecated alias | Not implemented as deprecated | Recommend only in a later implementation phase |

The complete per-command inventory has been consolidated into `docs/03_operations/runtime_test_command_guide.md` under "Phase20-G Command Responsibility Audit".

## Operator Question Mapping

| Operator Question | Current Command |
|---|---|
| Is a Runtime Test active, halted, completed, or idle? | `status` |
| Is the system healthy for the selected operational scope? | `system-status` |
| Are Accepted Generation and AI artifacts healthy? | `ai-status` |
| Is AI healthy as part of the whole system? | `system-status --scope ai` |
| What would the runner execute for a date window? | `plan` |
| Can Day1 historical isolation be prepared? | `prepare-isolated` |
| Can resettable state be backed up? | `backup` |
| Can historical state be reset cleanly? | `reset` |
| Can the planned Runtime jobs execute? | `run` |
| Can a clean Historical Runtime Test be orchestrated end to end? | `fresh-run` |
| Is a run valid enough to close or review? | `validate` |
| Can a halted compatible run continue? | `resume` |
| Can a halted run be abandoned without trading mutation? | `abandon` |
| Can resettable state be restored from backup? | `rollback` |
| Can the run be finalized with summary evidence? | `close` |
| What raw run or backup evidence exists? | `show`, `list-runs`, `list-backups` |
| What happened in the run, including performance and lifecycle summary? | `summarize` |

## Naming Audit

`status` is too broad as a long-term canonical name because it answers only Runtime Test runner state. It does not answer system readiness, AI artifact health, Broker boundary health, or performance diagnosis.

`system-status` is well named for whole-system inspection and already supports scope selection.

`ai-status` is well named for specialist AI artifact inspection. Its overlap with `system-status --scope ai` is acceptable because the operator question is different.

`summarize` is the natural name for read-only post-run analysis. It already contains performance, trade attribution, current position, and lifecycle consistency sections.

## Responsibility Boundary Audit

| Boundary | Result |
|---|---|
| Runtime execution | Owned by `run`, `resume`, and `fresh-run`; `summarize`, `status`, `ai-status`, and `system-status` are read-only |
| Trading state mutation | Owned by `backup`, `reset`, `run`, `resume`, `rollback`, and `fresh-run` actual modes; mutation flags are required where implemented |
| Evidence finalization | Owned by `close`, `abandon`, and optional `--write-evidence` inspection commands |
| AI artifact authority | Owned by `ai-status`; summarized in `system-status --scope ai` |
| Whole-system readiness | Owned by `system-status` |
| Run-scoped post-run analysis | Owned by `summarize` |
| Performance diagnosis | Not currently a separate CLI command; future integration should be `summarize --scope performance` |
| Position lifecycle analysis | Not currently a separate CLI command; future integration should be `summarize --scope lifecycle` or `--scope positions` |

## status / system-status Decision

Decision: recommend Option B for a future implementation.

```text
Canonical future command: run-status
Compatibility alias: status
Whole-system command: system-status
```

Rationale:

- `status` currently returns active run, run status, current business date, summaries, registry checkpoint, accepted artifact hash, latest backup, and external effect policy.
- `system-status` returns whole-system inspection context, data, AI, runtime, broker, readiness, lineage, component, and full scopes.
- Folding `status` into `system-status --scope runtime-test` would mix runner lifecycle state with whole-system inspection semantics and exit-code expectations.

Phase20-G implementation status: documentation only. No alias was added.

## ai-status / system-status Decision

Decision: recommend Option A.

```text
Keep ai-status as specialist AI artifact inspection.
Keep system-status --scope ai as whole-system scoped AI overview.
```

Rationale:

- `ai-status` writes a detailed AI evidence bundle under `reports/runtime_tests/ai_status/<run_id>/`.
- `system-status --scope ai` is a scoped view of the system report and is appropriate for daily operator overview.
- Deprecating `ai-status` would remove a clear specialist question and force detailed AI audit semantics into the whole-system command.

Phase20-G implementation status: documentation only. No deprecation was added.

## summarize / Position Lifecycle Integration Decision

Decision: recommend Option A.

```text
Future command shape:
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope overview
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope performance
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope positions
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope lifecycle
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope full
```

Rationale:

- `summarize` already reads run-scoped evidence.
- It already guards runtime-root reads through final-state hash matching.
- It already produces performance, PM decision summary, BUY/SELL summary, REDUCE/EXIT summary, trade attribution, current positions, and lifecycle consistency.
- Position lifecycle and performance observability are post-run questions, not Runtime execution questions.

`diagnose` is not recommended in Phase20-G because no distinct authority boundary, mutation model, or exit-code model has been established.

## Command Taxonomy

| Family | Commands |
|---|---|
| Runner State Inspection | `status`, future `run-status` |
| Whole-System Inspection | `system-status` |
| Specialist AI Inspection | `ai-status` |
| Planning / Preparation | `plan`, `prepare-isolated` |
| Execution / Orchestration | `run`, `resume`, `fresh-run` |
| Backup / Reset / Recovery | `backup`, `reset`, `rollback` |
| Validation / Finalization | `validate`, `close`, `abandon` |
| Artifact Discovery | `show`, `list-runs`, `list-backups` |
| Post-run Analysis | `summarize` |

## Deprecation / Compatibility Plan

No deprecation is implemented in Phase20-G.

Recommended future sequence:

1. Add `run-status` as an exact alias of current `status`.
2. Keep `status` as a deprecated compatibility alias with unchanged payload and exit-code semantics.
3. Keep `system-status` unchanged.
4. Keep `ai-status` unchanged.
5. Add `summarize --scope` only after defining the summary scope schema.
6. Retain current `summarize` behavior as default `overview` or compatible full summary, depending on the implementation contract.
7. Do not add `diagnose` unless a later phase defines a distinct command authority.

## Documentation Consolidation Result

The formal operator command document is:

```text
docs/03_operations/runtime_test_command_guide.md
```

No duplicate `docs/operations/` command guide was created.

The guide now contains the Phase20-G command responsibility audit, operator question mapping, naming decisions, command taxonomy, deprecation plan, compatibility plan, and runtime/strategy/authority impact statement.

No architecture contract update was required because Phase20-G did not change command authority or schemas.

## Recommended Implementation Sequence

1. In a later implementation phase, add `run-status` as an alias with tests proving identical payload and exit-code behavior.
2. Mark `status` as a compatibility alias in help and docs without breaking existing automation.
3. Define `summarize --scope` schema and formatter behavior.
4. Add `summarize --scope performance` using existing run-scoped performance evidence.
5. Add `summarize --scope positions` and `--scope lifecycle` using existing lifecycle and PM evidence.
6. Add focused tests for `show`, `list-runs`, and `list-backups` if these remain operator-facing commands.
7. Reconsider a separate `diagnose` command only after a distinct authority contract exists.

## Runtime Impact

```text
NONE
```

Phase20-G did not change Runtime execution, Runtime state, Broker behavior, or Runtime CLI parser behavior.

## Strategy Impact

```text
NONE
```

Phase20-G did not change AI selection, Opportunity ranking, BUY policy, HOLD policy, ADD policy, REDUCE policy, EXIT policy, Risk, Position Management, Capital Allocation, or Accepted Generation.

## Authority Impact

```text
NONE
```

Phase20-G only documented command responsibility and future integration design. It did not change artifact authority, schema authority, evidence authority, or runtime judgment authority.

## Validation

Allowed short read-only checks performed:

```text
PYTHONPATH=src python3 scripts/runtime_test.py --help
PYTHONPATH=src python3 scripts/runtime_test.py <subcommand> --help
```

File validation:

```text
python3 -m json.tool reports/phase_reports/phase20_g_runtime_test_cli_responsibility_and_observability_integration_audit.json
git diff --check
```

Disallowed actions not performed:

```text
Historical Smoke
Full Backtest
Broker connection
Training
Calibration
Validation rerun
Runtime State mutation
Accepted Generation mutation
```

## Final Judgment

```text
PHASE20_G_CLI_RESPONSIBILITY_AUDIT_COMPLETE_INTEGRATION_DESIGN_READY
```
