# Runtime Test Command Guide

This guide defines the fixed operator command for AI Fund Lab v2 Runtime Tests.
The formal execution authority is [Runtime Test Specification](../02_architecture/runtime_test_specification.md), especially section 26. This guide is an operational companion and must not override the specification.

Formal entrypoint:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py <subcommand> [options]
```

The runner is a thin lifecycle orchestrator. It calls the normal Runtime v2 CLI and does not implement AI decisions, Feature production, Pending generation, Fill generation, Ledger updates, or Current updates.

## Prerequisites

- Use only accepted profiles under `config/runtime_tests/`.
- Historical manual validation must use an isolated runtime root prepared for the run, for example `.runtime/runtime_tests/<run_id>/.runtime`. Shared `.runtime` remains the source for immutable accepted AI/data references, but shared Trading State is not Day1 authority.
- Production use is blocked by the runner.
- Mutating commands require both:

```bash
--confirm --yes-i-understand-this-mutates-trading-state
```

- Use `--dry-run` before any mutating command.

## Quick Command Selection

| What You Need To Know | Command |
|---|---|
| Runtime Test runner current state | `run-status` |
| Whether the system is safe or ready for an operating context | `system-status` |
| Detailed AI artifact / Accepted Generation authority | `ai-status` |
| Run overview | `summarize --run-id <RUN_ID> --scope overview` |
| Performance metrics | `summarize --run-id <RUN_ID> --scope performance` |
| Symbol-level Position Campaign results | `summarize --run-id <RUN_ID> --scope positions` |
| BUY -> HOLD -> ADD -> REDUCE -> EXIT lifecycle | `summarize --run-id <RUN_ID> --scope lifecycle` |
| Complete run analysis | `summarize --run-id <RUN_ID> --scope full` |

## Run Status

`run-status` is the canonical Runtime Test runner state command.

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status
PYTHONPATH=src python3 scripts/runtime_test.py run-status --json
```

It shows Runtime root, environment, active run, Current/Ledger/Pending/Runtime State summaries, Registry checkpoint, accepted artifact hash, latest backup, and external effect policy. `run-status` is read-only and writes no evidence.

`status` remains a compatibility alias for `run-status`:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py status
PYTHONPATH=src python3 scripts/runtime_test.py status --json
```

`status` and `run-status` use the same handler, payload, human output, authority, and exit code. No unconditional deprecation warning is printed, so JSON and script consumers are not broken.

Use `system-status` instead when the question is whole-system readiness, component health, data freshness, AI scoped overview, Broker boundary status, or production/demo readiness.

Use `ai-status` instead when the question is detailed AI artifact authority, Accepted Generation, model/scaler/calibration health, or AI runtime readiness.

## Summarize

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID>
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope overview
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope performance
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope positions
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope lifecycle
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope full
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --write-evidence
```

Summarize is a read-only post-run inspection command. It reads `reports/runtime_tests/runs/<run_id>/` evidence and, when no run-specific Trading State snapshot exists, uses the current Runtime root only if `final_summary.final_state_hashes` exactly match the current Runtime root hashes. It does not run Runtime jobs, refresh data, submit orders, generate fills, close/resume/rollback/abandon runs, call Broker APIs, or mutate Current / Ledger / Pending / Runtime State / Registry / Accepted Generation evidence.

Scope options:

| Scope | Operator Question | Main Output |
|---|---|---|
| `overview` | What happened in this run overall? | Run identity, business dates, Runtime judgment, external effects, equity, return, BUY/SELL counts, PM counts, lifecycle consistency, current positions summary, findings |
| `performance` | How did this run perform? | Contract-style metrics, daily equity curve summary when available, maximum drawdown, exposure, cash utilization, turnover, execution notional, metric status/confidence/warnings |
| `positions` | What happened to each symbol-level Position Campaign? | Symbol-level BUY, scores, confidence, open/closed status, final quantity/price, available PnL, MFE/MAE, evidence status, limitations |
| `lifecycle` | How did BUY -> HOLD -> ADD -> REDUCE -> EXIT evolve? | Position-level event timeline with decision-time evidence, execution evidence, end-of-day valuation, missing evidence, and post-hoc attribution labels |
| `full` | Show all analysis scopes | `overview`, `performance`, `positions`, and `lifecycle` sections |

When `--scope` is omitted, `summarize` uses a legacy-compatible full default. Existing top-level JSON fields are retained. New scope sections are additive, and non-selected explicit scopes are `null` in JSON.

The human output for the legacy-compatible default includes Run Summary, External Effect Summary, Performance Summary, PM Decision Summary, BUY / SELL Summary, REDUCE / EXIT Summary, Trade Attribution, Current Positions, Lifecycle Consistency, Review / Block Summary, and Operator Judgment. Explicit scopes render focused human summaries. `--write-evidence` writes only to `reports/runtime_tests/summaries/<summary_id>/` and records `summary_id`, `run_id`, `scope`, `generated_at`, contract versions, source evidence, authority, warnings, and selected scope sections.

Performance scope follows the Phase20 performance metric contract. Benchmark, Sector, and lot-level metrics are reported as `MISSING`, `DERIVABLE_PARTIAL`, or `NOT_AVAILABLE` when evidence is absent. Missing values are not zero-filled.

Positions and lifecycle scopes are symbol-level / Position Campaign observability. They must not be interpreted as stable lot-level analysis unless stable lot evidence exists. MFE, MAE, post-decision returns, loss avoided, profit missed, and counterfactual returns are marked `POST_HOC_ATTRIBUTION_ONLY` and must not be used as Runtime, Training, Calibration, Validation, or Accepted Generation authority.

Lifecycle consistency follows the REDUCE execution feasibility contract. A PM `REDUCE` is consistent when it resolves to exactly one executable partial SELL plan or exactly one approved non-executable terminal outcome with `execution_feasibility_status=NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY`, `reason=REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY`, no pending order, unchanged position quantity, and Runtime continuation `PASS`. Missing outcomes, conflicting plan plus terminal evidence, invalid terminal reasons, and position mutation remain `REVIEW_REQUIRED`.

## Plan

5BD plan:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06
```

Date range:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --date-from 2026-07-06 \
  --date-to 2026-07-10
```

Plan is read-only. It lists business dates, feature dates, carryover dates, job sequence, evaluation times, Runtime CLI commands, reset/exclusion scope, expected evidence paths, external effects, fill model, and rollback policy.

## Backup

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py backup \
  --profile historical-smoke \
  --dry-run
```

Actual backup:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py backup \
  --profile historical-smoke \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Backups include resettable Trading State only. Registry, Accepted Artifacts, Canonical Data, Raw Data, Feature Schema, AI Artifacts, Policy, Safety, Configs, and Evidence are excluded.

## Reset

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py reset \
  --profile historical-smoke \
  --dry-run
```

Actual reset:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py reset \
  --profile historical-smoke \
  --backup-id <BACKUP_ID> \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Reset requires a valid backup. It initializes Historical smoke state to 1,000,000 JPY cash/buying power, zero positions, zero pending, zero open orders, zero executions, and zero PnL. Partial reset is prohibited.

## Fresh Run

Fresh Run is the one-command operator for restarting a Historical Runtime Test from a clean state. It runs the formal sequence:

```text
Status -> Backup -> Clean Reset -> Plan -> Run -> Validate -> Close -> Final Summary
```

It preserves existing evidence under `reports/runtime_tests/runs/` and creates a new `run_id`. It does not purge old run evidence.

Identifier ownership is explicit:

- `fresh_run_id` identifies the orchestration attempt and its fresh-run summary before a Runtime Test plan exists.
- `backup_id` identifies the backup bundle created before reset.
- Runtime Test `run_id` is generated by the Plan step and is the only identifier passed to Run, Validate, Close, and run evidence paths.

`fresh-run` must construct the same Plan request contract as `plan`; internal subcommand namespaces must include every Plan-required attribute. Dry run validates Plan request construction and Runtime Test `run_id` generation without writing plan evidence or mutating Runtime state.

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --date-from 2026-06-29 \
  --date-to 2026-07-10 \
  --business-days 10 \
  --initial-cash 1000000 \
  --dry-run
```

Actual 10BD run:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src

python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --date-from 2026-06-29 \
  --date-to 2026-07-10 \
  --business-days 10 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Equivalent start/count form:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2026-06-29 \
  --business-days 10 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Fresh Run uses the normal Runtime v2 CLI for runtime execution:

```text
market_refresh
data_readiness
morning
sell_planning
submit
execution
current_valuation_refresh
runtime_state_refresh
```

The operator does not implement AI decisions, Pending generation, Fill generation, Ledger update, or Current update by itself.

Backup / Reset scope:

- Backup includes resettable Trading State only: Current, Ledger, Pending, Runtime operational state, orders, executions, positions, cash / buying power, and PnL.
- Backup excludes Registry, Accepted Artifacts, Canonical Data, Raw Data, AI Artifacts, Feature Schema, Config, Policy, Safety, Phase Reports, and Lifecycle Evidence.
- Reset requires the internally created `backup_id`; partial reset is prohibited.

Failure behavior:

- If any step is non-PASS, later steps are `NOT_EXECUTED`.
- The summary includes `failed_step`, `exit_code`, `error`, `backup_id`, `run_id`, last completed day/job, resume possibility, rollback possibility, and a recommended command.
- `Run` HALT does not execute `Validate` or `Close`.
- `Validate` failure does not execute `Close`.

Evidence:

```text
reports/runtime_tests/runs/<run_id>/plan.json
reports/runtime_tests/runs/<run_id>/run_state.json
reports/runtime_tests/runs/<run_id>/fresh_run_summary.json
reports/runtime_tests/runs/<run_id>/final_summary.json
reports/runtime_tests/backups/<backup_id>/
```

Exit codes are the same runner exit codes listed below.

Resume / Rollback guidance:

- Use `resume --run-id <RUN_ID> --dry-run` first when the summary says `resume_possible=true`.
- Use `rollback --backup-id <BACKUP_ID> --dry-run` first when the summary says `rollback_possible=true`.
- Use `abandon --run-id <RUN_ID> --dry-run` when a HALT run will not be resumed and a new `fresh-run` must start without deleting evidence.
- Actual rollback remains a separate explicit command with confirmation flags.

## PM Cross-Regime Campaign

Use this sequence when validating Position Management behavior across the three Phase20-Y market regimes. The campaign is three independent `fresh-run` executions followed by one read-only comparison command.

Primary campaign windows:

| Regime | Meaning | Start Date | Business Days | Selection |
|---|---|---:|---:|---|
| BULL | Up market | `2026-03-24` | 20 | Primary BULL |
| BEAR | Down market | `2026-03-02` | 20 | Primary BEAR |
| RANGE | Sideways market | `2026-04-10` | 20 | RANGE fallback with sufficient outcome coverage |

Run independence contract:

- Execute each regime as a separate `fresh-run`.
- Do not carry Runtime State, Ledger, Current, Pending, positions, or cash between regimes.
- Do not start the next regime if the previous run is `HALT`, `REVIEW_REQUIRED`, `BLOCKED`, non-zero exit, or completed days are fewer than 20.
- Record the emitted Runtime Test `run_id` from each successful run; those ids become `<BULL_RUN_ID>`, `<BEAR_RUN_ID>`, and `<RANGE_RUN_ID>`.

### BULL

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2026-03-24 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

### BEAR

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2026-03-02 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

### RANGE

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2026-04-10 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

### Cross-Regime Analysis

After all three runs complete successfully, replace the placeholders with the three emitted run ids:

```bash
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \
  --run-id <BULL_RUN_ID> \
  --run-id <BEAR_RUN_ID> \
  --run-id <RANGE_RUN_ID> \
  --output-json reports/phase_reports/phase20_y_pm_cross_regime_campaign_analysis.json
```

The comparison command is read-only. It reads run evidence under `reports/runtime_tests/runs/<RUN_ID>/` and writes the cross-regime analysis JSON. It does not mutate Runtime State, Accepted Generation, Registry, Broker state, or strategy logic.

## Abandon HALT Run

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id <RUN_ID> \
  --dry-run
```

Actual abandon:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon \
  --run-id <RUN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

`abandon` is the formal operator command for a HALT Runtime Test that will not be resumed. It does not delete or rewrite `run_state.json`, daily evidence, `plan.json`, or `fresh_run_summary.json`. It writes `abandonment.json` and a final summary with `status=ABANDONED`, `final_judgment=ABANDONED`, `abandoned_at`, `resume_disabled=true`, `evidence_preserved=true`, and `trading_state_mutated=false`.

After abandon, `status` no longer reports the run as active and `resume` is rejected for that `run_id`. `RUNNING` runs cannot be abandoned; they must first stop or HALT. Re-running `abandon` for an already abandoned run is idempotent and does not mutate Trading State.

Production prohibition:

- Production profiles are rejected.
- Broker write, external delivery, Tachibana API calls, and J-Quants fetch are disabled by accepted Historical profiles.
- Fresh Run does not switch Runtime accepted models and does not mutate Registry accepted state.

`run --auto-prepare` is deprecated. It is not a formal alias and now fails with guidance to use `fresh-run`, because Backup / Reset / Validate / Close orchestration must not be an ambiguous no-op.

## 5BD Run

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06 \
  --dry-run
```

Actual run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

The runner calls:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

with Historical mode, `historical_simulated` broker environment, `.runtime`, payload-only notifications, API fetch disabled, and stop-on-review/block flags.

## 10BD Run

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run \
  --profile historical-extended-smoke \
  --business-days 10 \
  --start-date 2026-07-06 \
  --dry-run
```

The 10BD profile is a Historical Extended Smoke / Pre-Continuity Test. It is not the formal 20BD continuity test and does not claim performance acceptance.

## Validate

```bash
PYTHONPATH=src python3 scripts/runtime_test.py validate --run-id <RUN_ID>
PYTHONPATH=src python3 scripts/runtime_test.py validate --run-id <RUN_ID> --business-date 2026-07-08
```

Validation checks Runtime root, Current, Pending, Runtime State, external effect policy, run state presence, and state hashes. It never repairs state.

## Resume

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --run-id <RUN_ID> \
  --dry-run
```

Resume validates source baseline, Registry hash, and accepted artifact hash. If any baseline changed, resume is rejected. Failed jobs are never skipped.

## Rollback

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py rollback \
  --backup-id <BACKUP_ID> \
  --dry-run
```

Actual rollback:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py rollback \
  --backup-id <BACKUP_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Rollback restores the full resettable Trading State bundle. Partial restore and Operational Foundation restore are prohibited.

## Close

```bash
PYTHONPATH=src python3 scripts/runtime_test.py close --run-id <RUN_ID>
```

## Phase20-G Command Responsibility Audit

This section records the implemented Runtime Test CLI surface as of Phase20-G. It is a responsibility and observability integration guide only. It does not add commands, aliases, scopes, Runtime behavior, AI behavior, Position Management behavior, Risk behavior, Opportunity behavior, or Broker behavior.

Phase20-H implemented the Phase20-G recommendations for `run-status` and `summarize --scope`. The table below is retained as audit history; the canonical operational instructions are the `Run Status` and `Summarize` sections above.

### Current Subcommand Inventory

| Command | Operator Question | Primary Responsibility | Scope | Mutation | Confirmation | Input Authority | Output Authority | Evidence Path | Exit Codes | Implementation | Formatter / Schema | Tests / Coverage | Documentation | Overlap Candidates | Recommended Future State |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `status` | Is a Runtime Test runner active and what is the local runner state? | Runner state summary | Active run, current root summaries, latest backup | Read-only | No | Profile, runtime root, evidence root | `runtime_test_runner_v1` payload | None | `0`, error codes | `status` | default emit / runner schema | `test_phase17_k_runtime_test_runner.py`, `test_phase19_bj_runtime_test_abandon.py` | Documented | `system-status` naming | Future canonical `run-status`; keep `status` compatibility alias after implementation phase |
| `summarize` | What happened in this completed or closed run? | Run-scoped post-run summary | Run evidence, performance summary, PM counts, trading, reduce/exit, attribution, lifecycle | Read-only, optional evidence write | No | `reports/runtime_tests/runs/<run_id>/`, final-state hash match for current root reads | `runtime_test_summary_v1` | `reports/runtime_tests/summaries/<summary_id>/` with `--write-evidence` | `0`, `10`, `20`, error codes | `summarize_command` | `_format_runtime_test_summary` / inline schema | `test_phase19_bv_runtime_test_summarize.py`, Phase19-BY authority correction tests | Documented | Future performance / position lifecycle views | Extend with future `--scope overview|performance|positions|lifecycle|full`; do not create `diagnose` yet |
| `ai-status` | Are AI artifacts, Accepted Generation, and AI Runtime authority healthy? | Focused AI artifact inspection | Candidate AI, Opportunity AI, calibration, lineage, freshness, readiness option | Read-only, optional evidence write | No | Accepted Generation resolver, AI artifacts, runtime root | `runtime_test_ai_status_report.v1` | `reports/runtime_tests/ai_status/<run_id>/` | `0`, `10`, `20`, `30` | `ai_status_command`, `build_ai_status_report` | AI human summary / `schemas/runtime_test/ai_status_report.schema.json` | `test_phase19_av_ai_status.py` | Documented | `system-status --scope ai` | Keep as specialist command; `system-status --scope ai` remains overview |
| `system-status` | Is the whole system ready or healthy for the selected inspection scope? | Whole-system operational inspection | `overview`, `data`, `ai`, `runtime`, `broker`, `readiness`, `lineage`, `components`, `full` | Read-only, optional evidence write | No | Profile, runtime root, latest compatible closed run context | `runtime_test_system_status_v2` plus legacy full report | `reports/runtime_tests/system_status/<run_id>/` | `0`, `10`, `20` | `system_status_command`, `build_system_status_report` | scoped human summary / `schemas/runtime_test/system_status_report.schema.json` | `test_phase19_ax_system_status.py`, `test_phase19_bw_system_status_scoped_output.py`, `test_phase19_bo_post_run_system_status_context.py` | Documented | `status`, `ai-status` | Keep canonical system inspection command |
| `prepare-isolated` | Can a historical isolated root be materialized for Day1? | Isolated historical runtime root preparation | Historical pre-run root materialization and temporal preflight | Mutates isolated test root and optional evidence only; shared runtime read-only | No special mutation flag in current CLI | Historical profile, shared runtime root, Accepted Generation references | runner payload plus prepare isolated evidence | `reports/runtime_tests/prepare_isolated/<run_id>/` with `--write-evidence` | `0`, `20`, `60` | `prepare_isolated_command` | default emit / prepare isolated result files | `test_phase19_bb_isolated_runtime_root.py` | Now documented here | `fresh-run` preparation | Keep separate pre-run preparation command |
| `plan` | What jobs and dates would this Runtime Test execute? | Runtime Test plan creation and persistence | Schedule, feature dates, job commands, rollback policy | Evidence write only | No | Profile, window args, runtime root, evidence root | `runtime_test_plan_v1` | `reports/runtime_tests/plans/` and run plan path when persisted | `0`, `10`, error codes | `plan_command` | default emit / plan schema | `test_phase17_k_runtime_test_runner.py`, `test_phase17_bv11_runtime_test_plan_persistence.py` | Documented | `fresh-run` internal plan | Keep |
| `backup` | Can resettable trading state be backed up before reset? | Backup resettable state | Trading state only, excludes foundation data and AI artifacts | Mutating unless `--dry-run` | Yes for actual | Runtime root, profile reset scope | `runtime_test_backup_manifest_v1` | `reports/runtime_tests/backups/<backup_id>/` | `0`, `30`, `50`, `60`, `70`, `90` | `backup_command` | default emit / backup manifest schema | `test_phase17_k_runtime_test_runner.py`, `test_phase17_ae_reset_scope_plan_gate.py` | Documented | `fresh-run` internal backup | Keep |
| `reset` | Can historical trading state be reset cleanly? | Clean historical state reset | Resettable trading state and clean-state invariant | Mutating unless `--dry-run` | Yes for actual | Backup manifest, profile initial state | `runtime_test_reset_manifest_v1` | Runtime state plus runner payload | `0`, `50`, `60`, `70`, `90` | `reset_command` | default emit / reset manifest schema | `test_phase17_k_runtime_test_runner.py`, `test_phase17_ae_reset_scope_plan_gate.py` | Documented | `fresh-run` internal reset | Keep |
| `run` | Execute the planned Historical Runtime Test jobs? | Runtime job execution loop | Normal Runtime v2 CLI job sequence | Mutating unless `--dry-run` | Yes for actual | Plan or window args, runtime root | `runtime_test_run_state_v1` | `reports/runtime_tests/runs/<run_id>/` | `0`, `30`, `60`, `70`, `80`, `90` | `run_command` | default emit / run state schema | `test_phase17_k_runtime_test_runner.py`, `test_phase17_m_consumer_wiring_and_feature_temporal_authority.py`, `test_phase18w_historical_scoped_block.py` | Documented | `fresh-run` orchestration | Keep; `--auto-prepare` remains deprecated and rejected |
| `fresh-run` | Start a complete clean Historical Runtime Test from one command? | Orchestrate status, backup, reset, plan, run, validate, close | Full historical lifecycle | Mutating unless `--dry-run` | Yes for actual | Profile, runtime root, evidence root, window args | `runtime_test_fresh_run_summary_v1` | `reports/runtime_tests/runs/<run_id>/fresh_run_summary.json` | `0`, `30`, `40`, `50`, `60`, `70`, `80`, `90` | `fresh_run_command` | default emit / fresh run summary schema | `test_phase18v_runtime_test_fresh_run.py`, `test_phase19_bh_fresh_run_namespace.py` | Documented | `run --auto-prepare` | Keep canonical full restart command |
| `validate` | Is the current run state and evidence consistent enough to accept? | Read-only validation | Current state, pending, runtime state, external effects, run state presence | Read-only | No | Runtime root, optional run state | runner payload | None | `0`, `40` | `validate_command` | default emit / runner schema | `test_phase17_k_runtime_test_runner.py`, `test_phase18v_runtime_test_fresh_run.py` | Documented | `close` internal validation | Keep |
| `resume` | Can a halted compatible run continue from remaining jobs? | Resume incomplete job sequence | Original plan, run state, baseline consistency | Mutating unless `--dry-run` | Yes for actual | Existing run state, original plan, current baseline | `runtime_test_run_state_v1` updates | `reports/runtime_tests/runs/<run_id>/` | `0`, `30`, `60`, `70`, `80`, `90` | `resume_command` | default emit / run state schema | `test_phase17_k_runtime_test_runner.py`, `test_phase19_bj_runtime_test_abandon.py` | Documented | `run` execution loop | Keep |
| `abandon` | Should a halted run be finalized as abandoned without touching trading state? | Abandon halted run | Run evidence finalization | Evidence mutation only, no trading mutation | Yes for actual except idempotent existing abandon | Existing halted run state | `runtime_test_abandonment_v1`, final summary | `reports/runtime_tests/runs/<run_id>/` | `0`, `60`, `70` | `abandon_command` | default emit / abandonment and final summary schemas | `test_phase19_bj_runtime_test_abandon.py` | Documented | `close`, `resume` | Keep |
| `rollback` | Restore resettable state from a backup? | Restore backup | Resettable trading state only | Mutating unless `--dry-run` | Yes for actual | Backup manifest | runner payload | Runtime root restored from backup | `0`, `50`, `60`, `70`, `90` | `rollback_command` | default emit / runner schema | `test_phase17_k_runtime_test_runner.py`, `test_phase17_ae_reset_scope_plan_gate.py` | Documented | `reset` backup dependency | Keep |
| `close` | Can this run be formally closed with final summary? | Finalize run evidence | Final summary and validation result | Evidence write only | No | Run state, validation result, current hashes | `runtime_test_final_summary_v1` | `reports/runtime_tests/runs/<run_id>/final_summary.json` | `0`, `10`, `70` | `close_command` | default emit / final summary schema | `test_phase17_k_runtime_test_runner.py`, `test_phase18v_runtime_test_fresh_run.py` | Documented | `abandon`, `summarize` | Keep |
| `show` | Show a raw run or backup artifact? | Artifact display | `run_state.json` or `backup_manifest.json` | Read-only | No | Default `reports/runtime_tests` constants, `--run-id` or `--backup-id` | Source artifact wrapped by runner response | None | `0`, `60`, error codes | `show` | default emit / source artifact schema | Covered indirectly by runner tests; no focused test identified | Now documented here | `list-runs`, `list-backups` | Keep as low-level inspection; add focused parser tests in later phase |
| `list-runs` | What Runtime Test run ids exist? | List run ids and statuses | Default `reports/runtime_tests/runs` | Read-only | No | Default constants only | runner payload | None | `0` | `list_runs` | default emit / runner schema | Covered indirectly; no focused test identified | Now documented here | `show` | Keep; future common `--evidence-root` could be considered |
| `list-backups` | What backup ids exist? | List backup ids | Default `reports/runtime_tests/backups` | Read-only | No | Default constants only | runner payload | None | `0` | `list_backups` | default emit / runner schema | Covered indirectly; no focused test identified | Now documented here | `show` | Keep; future common `--evidence-root` could be considered |

Aliases and deprecated aliases:

| Item | Current State | Phase20-G Decision |
|---|---|---|
| `system-status --full` | Implemented alias for `--scope full` | Keep |
| `run --auto-prepare` | Parser accepts it, implementation rejects it as deprecated and incomplete | Keep rejected; use `fresh-run` |
| `status` as `run-status` | `run-status` is not implemented | Recommend future `run-status` canonical command, with `status` retained as deprecated compatibility alias |
| `ai-status` aliasing into `system-status` | Not implemented | Do not deprecate `ai-status` |

### Operator Question Mapping

| Operator Question | Current Command |
|---|---|
| What is the current Runtime Test runner state? | `status` |
| Is the whole system ready or healthy for an operation context? | `system-status` |
| Are AI artifacts, Accepted Generation, freshness, and runtime AI authority healthy? | `ai-status` or `system-status --scope ai` |
| What would run for this date window? | `plan` |
| Can I safely restart from clean historical state? | `fresh-run --dry-run`, then `fresh-run --confirm ...` |
| Can I inspect a completed run? | `summarize --run-id <RUN_ID>` |
| Can I inspect raw run or backup evidence? | `show`, `list-runs`, `list-backups` |
| Can I continue a halted compatible run? | `resume --dry-run`, then `resume --confirm ...` |
| Can I finalize a halted run as abandoned? | `abandon --dry-run`, then `abandon --confirm ...` |
| Can I restore the previous resettable state? | `rollback --dry-run`, then `rollback --confirm ...` |

### Naming and Responsibility Decisions

`status` versus `system-status`: future Option B is recommended. `status` currently answers a Runtime Test runner-state question, while `system-status` answers system inspection and readiness questions. The future canonical spelling should be `run-status`, with `status` retained as a deprecated compatibility alias. Phase20-G does not implement this alias.

`ai-status` versus `system-status --scope ai`: Option A is recommended. Keep `ai-status` as the specialist AI artifact and authority audit. Keep `system-status --scope ai` as the daily operator overview of AI within whole-system context. The two commands overlap by design because `system-status` reuses AI status inspection, but they have different operator questions and output depth.

Performance observability and position lifecycle analysis: Option A is recommended. Extend `summarize` in a later phase with `--scope overview|performance|positions|lifecycle|full`. This is the natural integration point because `summarize` already owns run-scoped post-run evidence, performance summaries, PM decision counts, trading evidence, reduce/exit attribution, current positions, lifecycle consistency, and evidence writing. A new `diagnose` command is not justified unless a later phase defines a distinct authority, non-summary exit contract, or separate evidence schema.

### Command Taxonomy

| Family | Commands | Boundary |
|---|---|---|
| Runner State Inspection | `status` future `run-status` | Active run and local Runtime Test state only |
| Whole-System Inspection | `system-status` | Operational readiness and component health |
| Specialist Inspection | `ai-status` | AI artifact authority and readiness |
| Planning | `plan`, `prepare-isolated` | Read-only plan creation and historical root preparation |
| Lifecycle Execution | `run`, `fresh-run`, `resume` | Runtime job execution via normal Runtime v2 CLI |
| Safety / Recovery | `backup`, `reset`, `rollback`, `abandon`, `close`, `validate` | Resettable state, evidence finalization, validation, recovery |
| Artifact Inspection | `show`, `list-runs`, `list-backups` | Low-level evidence discovery |
| Post-run Analysis | `summarize` | Run-scoped summaries, future performance and lifecycle scopes |

### Deprecation and Compatibility Plan

No deprecation is implemented in Phase20-G. Future implementation should follow this order:

1. Add `run-status` as a canonical alias of current `status`.
2. Keep `status` as a compatibility alias with documentation and tests.
3. Keep `system-status` unchanged.
4. Keep `ai-status` unchanged.
5. Add `summarize --scope` only after a schema and evidence contract is defined.
6. Do not add `diagnose` unless a later authority contract proves a separate command is required.

Compatibility guarantees for a future implementation:

- Existing `status`, `summarize`, `ai-status`, and `system-status` invocations must keep working.
- Existing JSON fields should remain available during any transition.
- Deprecated aliases must not silently change exit-code semantics.
- Performance and position lifecycle observability must remain read-only and run-scoped.

### Runtime, Strategy, and Authority Impact

Phase20-G has no Runtime impact, no Strategy impact, no AI impact, no PM impact, no Risk impact, no Opportunity impact, no Capital Allocation impact, no Accepted Generation impact, and no Broker impact. It documents command responsibility and future integration design only.

Close performs final validation, final state freeze, final summary generation, test validity judgment, acceptance gate judgment, and post-close lifecycle recommendation. It does not reset state.

## System Status

`system-status` is the recommended daily pre-operation read-only health command for AI Fund Lab v2.

Use it before starting daily operation to answer:

```text
Can this system be operated safely today?
```

It inspects:

```text
Data: J-Quants, Raw, Normalized, Feature, Dataset, Split
AI: Candidate, Opportunity, Calibration, Runtime Baseline, Freshness, Accepted Generation
Runtime: Resolver, COMMITTED authority, Runtime Consumer, Lifecycle, Threshold, BUY Planning, SELL Continuity
Runtime State: Current, Pending, Ledger, PM, Safety
Broker Layer: Approval, Submit Guard, Execution, Broker Connection, Notification, Reporting
Overall: PASS / REVIEW_REQUIRED / BLOCK
```

Default overview:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py system-status
```

The default output is a compact operator overview. It shows Inspection Context, separated status judgments, key data freshness dates, Runtime completion/current state, Accepted Generation age with explicit units, important findings, and the final system-status judgment. It intentionally omits hashes, full lineage, complete inventories, and dependency matrices.

Scope options:

| Scope | Purpose | Main Checks |
|---|---|---|
| `overview` | Normal daily check | Key statuses, latest dates, Runtime state |
| `data` | Data status check | J-Quants, Feature, Freshness, Temporal |
| `ai` | AI status check | Accepted Generation, Model, Scaler, Health |
| `runtime` | Runtime state check | Stage, Current, Pending, Ledger, Execution |
| `broker` | Broker boundary check | Config, Connectivity, Write readiness |
| `readiness` | Environment readiness | Historical, Demo, Production readiness |
| `lineage` | Detailed lineage audit | Dataset, Hash, Split, Source |
| `components` | Component audit | Inventory, Dependency, Authority |
| `full` | Full inspection | All sections |

Examples:

```bash
# Normal overview
PYTHONPATH=src python3 scripts/runtime_test.py system-status

# Data status
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope data

# AI status
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope ai

# Runtime status
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope runtime

# Broker boundary status
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope broker

# Production readiness / environment readiness
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope readiness

# Full inspection
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope full
```

JSON output follows the selected scope:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope data --json
```

Full JSON is intentionally large; save it to a file when reviewing all details:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py system-status --scope full --json > /tmp/system_status_full.json
```

For backward compatibility, `system-status --json` still includes the deprecated top-level `system_status_report` full legacy report. New consumers should use the v2 fields: `scope`, `inspection_context`, `status_summary`, `findings`, and `sections`.

Full scope includes Active Component Inventory, Active Component Count Summary, Complete Component Inventory, Component Dependency Matrix, Runtime Chain Inspection, J-Quants Dependency Matrix, Runtime State Coverage, Inspection Coverage, Data Sources, Complete Data Source Inventory, Datasets, Runtime Features, AI Models, AI Data Window Summary, AI Input Lineage, Runtime Input Lineage, Runtime Baseline Traceability, Freshness Policy Traceability, Decision Subsystems, Accepted Generation / Authority, Runtime State, Broker Layer, Freshness Matrix, Findings, Non-mutation Guarantee, and Exit Code. Candidate evaluated symbol count is reported separately from Candidate output count; Opportunity input candidate count, ranking count, and Top20 count are also reported separately.

Candidate and Opportunity input lineage are first-class operator output, not JSON-only diagnostics. The human report and JSON report both show training dataset revision, dataset artifact/manifest path, source authority, source earliest/latest date, source row/symbol count, schema/content hash, Training/Calibration/Validation/Test/Recent Holdout split window statistics, recent holdout non-use, and calibration/validation independence. Runtime input lineage remains a planned pre-run contract until target-date features and inference are materialized, and must display explicit values such as `NOT_YET_MATERIALIZED` instead of empty placeholders.

Operational component inspection is complete only when every Runtime operation component has a contract row with Component Name, Component Type, Active/Inactive status, Authority, Implementation, Input Artifact, Output Artifact, Input Components, Input Business Date, Output Business Date, Configuration Status, Runtime Status, Inspection Status, and J-Quants dependency. Repository operation components that are not inspected must be reported as `COMPONENT_NOT_INSPECTED` / `REVIEW_REQUIRED`; they must not be silently skipped.

Status semantics are intentionally split. `inspection_status = PASS` means the component was inspected successfully; it does not mean the target-date Runtime step was executed. Operators must read `target_date_execution_status` and `runtime_result_status` for target-date execution meaning. In PRE_RUN, model loadability may PASS while Candidate/Opportunity inference remains `NOT_YET_MATERIALIZED`; Submit/Execution/Reporting/Notification may be configured but `NOT_PERFORMED`.

J-Quants dependency is classified as `DIRECT`, `INDIRECT`, or `NONE`. The compatibility field `JQUANTS_DEPENDENT` may still appear, but the formal interpretation is `jquants_dependency_type`, `jquants_dependency_path`, `jquants_direct_input_artifacts`, and `jquants_dependency_reason`.

Historical source coverage and Runtime consumer cutoff are separate. A historical source may be available beyond the target business date, but `consumer_cutoff_date` remains the target business date and `future_rows_consumed` must be zero or `NOT_YET_MATERIALIZED`; future-row consumption is a temporal contract violation.

The header includes Runtime Stage, Pre-run Readiness, and Day1 Start Permission. For a clean isolated Historical Day1 root before the Runtime route starts, target-date Runtime Features, Candidate/Opportunity Inference, AI Lifecycle Gate, Safety Decision, and BUY Planning are reported as `NOT_YET_APPLICABLE` with `PRE_RUN_NOT_MATERIALIZED`; this is not a false BLOCK. Model authority, model/scaler/calibration hashes, and read-only model loadability are inspected separately.

`system-status` PASS is valid only within the displayed inspection context. A Historical isolated pre-run PASS does not mean Demo readiness, Production readiness, Broker connectivity readiness, BUY readiness, or autonomous operation readiness. The command prints Environment Readiness separately:

```text
Historical Pre-run Readiness
Single-day Runtime Readiness
Multi-day Continuity Readiness
Demo Current-data Readiness
Production Current-data Readiness
Broker Connectivity Readiness
Broker Write Readiness
```

After a Historical Runtime Test is formally closed with `Run=PASS`, `Validate=PASS`, and `Close=PASS`, `system-status` resolves the latest compatible closed run as `HISTORICAL_POST_RUN` when no active run exists and the inspected runtime root matches the run root. In that context, the target business date is the final completed business date, not the profile start date. Temporal isolation is evaluated against that final date, and Historical Safety authority is read from the closed run's Data Readiness / Submit evidence rather than requiring `.runtime/runtime_state/safety/latest_safety_decision.json`.

`NOT_PERFORMED` is not rendered as connectivity PASS. Broker Configuration and Submit Guard configuration may be PASS while Broker Connectivity, Credential Access, and Broker Write remain `NOT_PERFORMED` or `PROHIBITED`.

Evidence output:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py system-status --write-evidence
```

`system-status` has no `--detailed` option. Use `--scope full` for the full inspection report.

Exit code:

| Exit code | Meaning |
|---:|---|
| `0` | PASS |
| `10` | REVIEW_REQUIRED |
| `20` | BLOCK / fail-closed precondition |

Status values:

| Status | Meaning |
|---|---|
| `PASS` | Checked and acceptable for the displayed context. |
| `READY` | Materialized and ready. |
| `REVIEW_REQUIRED` | Human review needed, but not necessarily Runtime failure. |
| `BLOCKED` / `BLOCK` | Fail-closed blocker. |
| `NOT_PERFORMED` | Deliberately not executed by this read-only command. |
| `NOT_EVALUATED` | Outside the current inspection context. |
| `NOT_APPLICABLE` | Not applicable for the current context/stage. |
| `NOT_RETAINED` | Artifact not retained after successful run; not automatically a blocker. |

Runtime PASS does not imply Production Ready. Broker Configuration PASS does not imply Broker Connectivity PASS. Model Health REVIEW_REQUIRED does not automatically mean Runtime Execution failed. In Historical Post-run context, transient feature artifacts not retained in shared `.runtime` are not BLOCK when completed run evidence is sufficient.

Safety Artifact timing:

```text
Safety=NOT_YET_APPLICABLE
```

means the expected target-date Safety Decision has not yet been materialized because the target-date Runtime route has not started. This is a normal pre-run state and does not block Day1 start by itself.

```text
Safety=READY
```

means `.runtime/runtime_state/safety/latest_safety_decision.json` exists, matches the expected business date, and is recognized by `system-status`.

```text
Safety=BLOCK
```

means the target-date Safety or Morning route already ran but the expected latest Safety Decision artifact is still missing.

Read-only guarantee:

```text
No training
No calibration
No validation rerun
No generation creation
No authority history append
No runtime pointer write
No trading state mutation
No BUY restart
No Broker access
No Broker write
No notification send
```

When `--write-evidence` is used, evidence is written to:

```text
reports/runtime_tests/system_status/<run_id>/
```

## AI Artifact Inspection

`ai-status` remains available as a narrower AI Artifact Inspection command. Normal daily operation should prefer `system-status`; use `ai-status` when the question is specifically about Candidate AI, Opportunity AI, calibration, Accepted Generation, AI freshness, or AI Runtime authority.

Use it when checking which Accepted Generation is COMMITTED, whether Candidate / Opportunity artifacts are bound and loadable, whether latest J-Quants and BUY feature freshness are connected, and whether runtime lifecycle monitoring reports PASS, REVIEW_REQUIRED, or BLOCK.

Read-only guarantee:

```text
No training
No calibration
No validation rerun
No generation creation
No authority history append
No runtime pointer write
No trading state mutation
No BUY restart
No Broker access
No Broker write
```

Basic summary:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py ai-status
```

Detailed summary:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py ai-status --detailed
```

JSON output:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py ai-status --json
```

Evidence output:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py ai-status --write-evidence
```

Runtime readiness inspection:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py ai-status --check-runtime-readiness
```

Options may be combined:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py ai-status --json --detailed --write-evidence --check-runtime-readiness
```

For `ai-status`, exit code `0` means PASS, `10` means REVIEW_REQUIRED, `20` means BLOCK, and `30` means command/internal error. Statistical drift alone returns REVIEW_REQUIRED and must not be interpreted as a structural BUY block. Schema mismatch, hash mismatch, missing model/scaler/calibration, missing feature columns, NaN/Inf, loader failure, collapse, or missing Candidate dependency are structural BLOCK findings.

When `--write-evidence` is used, evidence is written to:

```text
reports/runtime_tests/ai_status/<run_id>/
```

Review `ai_status_summary.json` first, then `runtime_readiness.json`, `runtime_authority_status.json`, and `legacy_fallback_audit.json`. `Broker Access` must remain `NOT_PERFORMED`.

## Performance Observability Evidence

Phase20-J and later Runtime Test runs write additional run-scoped observability evidence without changing Runtime, AI, PM, Risk, Opportunity, Capital Allocation, Broker behavior, or Accepted Generation.

Daily evidence paths:

```text
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/position_management/pm_decisions.json
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/execution/fills.json
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/execution/realized_slices.json
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/positions/position_campaigns.json
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/benchmark/benchmark_snapshot.json
```

`position_campaign_id` is run-scoped and deterministic. It follows one symbol from initial BUY through ADD/HOLD/REDUCE/EXIT/final open position, and starts a new campaign after full EXIT followed by reBUY. Symbol alone is not campaign identity.

`realized_slices.json` is the formal realized PnL observability unit when stable lot IDs are not available. Runtime uses average-cost projection for realized PnL; unavailable costs such as fees, tax, and slippage are written as `{ "value": "MISSING", "status": "NOT_AVAILABLE" }`, never zero-filled.

`pm_decisions.json` is a decision-time snapshot only. It must not contain future price movement, MFE/MAE, post-sale return, or other post-hoc attribution fields.

For PM `REDUCE`, `runtime_sell_quantity=0` in PM evidence means Sell Planning owns executable quantity calculation when `runtime_quantity_authority=SELL_PLANNING_REDUCE_QUANTITY_CONTRACT` or the runtime action is `SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING`. It is not a PM request to submit a 0-share order.

If a valid REDUCE rounds below the minimum tradable unit, Sell Planning keeps the original decision as `REDUCE`, records `execution_feasibility_status=NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY`, generates no pending SELL item, leaves the position unchanged, and continues Runtime with reason `REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY`. Review or block behavior remains required for unknown Current quantity, unknown tradable unit, calculation errors, negative sellable quantity, rounded quantity greater than current quantity, contract mismatch, partial sell effectively becoming full EXIT without policy, duplicate conflicting PM decisions, or ambiguous position authority.

An empty portfolio can be a normal authoritative state. When Persistent Ledger Current has `positions=[]`, `current_positions_unknown=false`, `current_position_status=READY`, `no_position=true`, valid `position_state_as_of`, `temporal_status=READY`, and `review_required=false`, Runtime treats Position Authority as `READY_EMPTY`. Position Feature may be a schema-valid 0-row artifact, PM inference is `NOT_REQUIRED`, and Market Refresh can continue. `READY_EMPTY` is different from `UNKNOWN`: missing Ledger, corrupt JSON, missing or non-list `positions`, `current_positions_unknown=true`, stale temporal authority, `review_required=true`, or conflicting metadata remains fail-closed.

Historical Fresh Run Reset separates logical time from wall-clock time. The initial empty Current binds `business_date`, logical `as_of`, and `position_state_as_of` to the first planned business date, while `created_at`, `updated_at`, and `reset_executed_at` remain real execution timestamps. This lets first-day Market Refresh see `READY_EMPTY` without weakening the future-state guard. A reset artifact with `position_state_as_of` after the feature target date is still review-required.

`benchmark_snapshot.json` currently records TOPIX benchmark status as `MISSING` with `benchmark_source=NOT_CONFIRMED` and `benchmark_implementation=NOT_PERFORMED` until a J-Quants-compatible benchmark source is approved. Cash must not be treated as a TOPIX substitute.

The existing summarize scopes consume this evidence additively:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope performance
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope positions
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope lifecycle
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <RUN_ID> --scope full
```

Old runs do not have Phase20-J evidence. Summaries must return `MISSING`, `NOT_RETAINED`, or `DERIVABLE_PARTIAL` for those fields rather than blocking or filling unknown values with zero.

Long historical runs can produce one small JSON payload per day per evidence type. Operators should archive the full run directory for attribution review and avoid copying these files into shared `.runtime` as post-hoc inputs.

Lifecycle and positions summaries count campaigns by `position_campaign_id`. Daily `position_campaigns.json` files are snapshots, not separate lifecycles; five daily snapshots of the same campaign still count as one campaign. When several snapshots exist, `summarize` uses the latest/most complete campaign snapshot.

Closed campaigns remain visible in `summarize --scope positions`. Human output separates:

```text
realized=
unrealized=
total=
```

`total` means `total_campaign_pnl`. Gross realized PnL comes from realized slices. Net realized PnL remains unavailable while fees/tax are missing, and missing fees/tax must not be treated as zero.

## Exit Codes

| Code | Meaning |
|---:|---|
| 0 | PASS |
| 10 | REVIEW_REQUIRED |
| 20 | BLOCKED |
| 30 | HALT |
| 40 | VALIDATION_FAILURE |
| 50 | ROLLBACK_FAILURE |
| 60 | INVALID_ARGUMENT |
| 70 | PRECONDITION_FAILURE |
| 80 | TEST_INVALID |
| 90 | INTERNAL_ERROR |

## Evidence

Evidence root:

```text
reports/runtime_tests/
```

Run evidence:

```text
reports/runtime_tests/runs/<run_id>/
```

Backup evidence:

```text
reports/runtime_tests/backups/<backup_id>/
```

Runner logs are evidence. Trading State, Registry, Canonical Data, Raw Data, Accepted Artifacts, and Feature Schema are authority data, not disposable logs.

## Common Failures

- `PRECONDITION_FAILURE`: backup, reset, run state, or baseline is missing.
- `HALT`: production use, external effect violation, Runtime CLI failure, or path guard rejection.
- `VALIDATION_FAILURE`: state/evidence consistency check failed.
- `REVIEW_REQUIRED`: validated checkpoint exists but human review is required before continuation.

## Production Prohibition

This runner blocks production profiles and production mode. Production Readiness and Production Acceptance require separate authority, credentials, capability, reconciliation, and human release approval.

## Examples

Recommended Phase17-L order:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py status
PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-smoke --business-days 5 --start-date 2026-07-06
PYTHONPATH=src python3 scripts/runtime_test.py backup --profile historical-smoke --confirm --yes-i-understand-this-mutates-trading-state
PYTHONPATH=src python3 scripts/runtime_test.py reset --profile historical-smoke --backup-id <BACKUP_ID> --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
PYTHONPATH=src python3 scripts/runtime_test.py run --profile historical-smoke --business-days 5 --start-date 2026-07-06 --confirm --yes-i-understand-this-mutates-trading-state
PYTHONPATH=src python3 scripts/runtime_test.py validate --run-id <RUN_ID>
PYTHONPATH=src python3 scripts/runtime_test.py close --run-id <RUN_ID>
```
