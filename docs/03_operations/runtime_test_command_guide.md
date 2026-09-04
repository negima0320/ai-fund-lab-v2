# Runtime Test Command Guide

This guide defines the fixed operator command for AI Fund Lab v2 Runtime Tests.
The formal execution authority is [Runtime Test Specification](../02_architecture/runtime_test_specification.md), especially section 26. This guide is an operational companion and must not override the specification.

Formal entrypoint:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py <subcommand> [options]
```

The runner is a thin lifecycle orchestrator. It calls the normal Runtime v2 CLI and does not implement AI decisions, Feature production, Pending generation, Fill generation, Ledger updates, or Current updates.

Phase22 Strategy shadow generation is orchestration only. The runner calls the production-common Phase22 Strategy producers after each completed daily Runtime job sequence and stores their draft, non-production-consumable artifacts as run evidence; it does not reimplement Strategy judgment logic.

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
| Phase22 Strategy shadow evidence | `summarize --run-id <RUN_ID> --scope strategy` |
| Phase22 Strategy shadow readiness | `system-status --scope strategy` |
| Phase22 Strategy artifact inspection | `show --run-id <RUN_ID> --artifact strategy [--business-date <DATE>]` |

## Read-Only Audit Scripts

Some Phase29 attribution tasks add standalone read-only audit scripts outside
the Runtime Test runner.  These scripts must not mutate Runtime state, Pending,
Ledger, Current, Registry, Accepted Generation, Broker state, credentials, or
notifications.

Phase29-L21T-AO Buy Quality x Relative Opportunity Score forward-outcome audit:

```bash
python3 scripts/audits/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_audit.py
```

Optional explicit inputs:

```bash
python3 scripts/audits/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_audit.py \
  --run-dir reports/runtime_tests/runs/<RUN_ID> \
  --price-path .runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw/jquants/equities_bars_daily/data.parquet \
  --output-dir reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit \
  --anchor-date 2022-08-10
```

Outputs:

```text
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/summary.json
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/per_entry.csv
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/group_summary.csv
reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit/anchor_2022_08_10.csv
```

Forward returns from this script are post-hoc audit evidence only and must not
be fed back into Runtime decisions.

Phase29-L21T-AW Post-AV short fresh validation:

Use this operator-run command to validate AV Momentum Trajectory BUY_WAIT
semantics over a short window near earlier observed 78780 / 53800 examples.
The deleted old-run runtime artifacts are not required, and artifact-level
comparison against `runtime-test-historical-extended-smoke-20260814T054658313415Z`
is not an AW pass condition. Codex must not run this command, and `--json` must
not be added to the fresh-run command.

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-08-10 \
  --business-days 20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

After the operator captures `<NEW_RUN_ID>`, use read-only inspection:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope overview
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope performance
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope positions
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id <NEW_RUN_ID> --scope lifecycle
```

Required review points are BUY_NEW count, BUY_WAIT count, trajectory class
counts, Cash, Gross Exposure, Positions, Pending state, Runtime Judgment, SELL
continuation, AV feature/classification materialization, and at least one
HEALTHY_CONTINUATION candidate remaining BUY-eligible when other authorities
pass. Check 78780 / 53800 fading-to-wait behavior only if comparable cases
naturally appear; absence of those symbols/cases in the short window is not a
failure.

## Phase22 Strategy Shadow

Runtime Test commands include a shadow-only Phase22 Strategy job. It is visible in `plan`, runs after each normal daily Runtime job sequence in `run`, `fresh-run`, and `resume`, and writes to:

```text
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/strategy/
reports/runtime_tests/runs/<RUN_ID>/strategy_shadow_manifest.json
reports/runtime_tests/runs/<RUN_ID>/strategy_shadow_summary.json
```

Daily evidence includes `input_manifest.json`, `source_manifest.json`, Strategy producer artifacts, `strategy_decision_trace.json`, `legacy_shadow_comparison.json`, and `strategy_shadow_summary.json`.

The Strategy shadow job is read-only for active Runtime authority. It must not write Pending, Submit, Approval, Execution, Ledger, Current, Registry, Accepted Generation, Broker, credentials, or notifications. Evidence records Runtime mutation and Broker/external delivery flags separately from the active Runtime result.

The input manifest binds Strategy shadow evidence to the COMMITTED Accepted Generation resolver, Candidate and Opportunity output artifacts, feature schema hashes, model/scaler/calibration hashes where available from the Accepted Generation manifest, Runtime snapshots, Strategy configs, Safety config, source hashes, and config hashes. Latest fallback, previous-day Strategy copy, and future-row consumption are forbidden. The input manifest also references `source_manifest.json` and its SHA-256 hash.

`source_manifest.json` is the PIT source-resolution artifact for Strategy shadow. It records portfolio state, pending state, market quotes, benchmark, sector, corporate-event, Candidate, Opportunity, bootstrap, PIT validation, source hashes, direct blockers, propagated blockers, root blocker components, and root reason codes. It is read-only evidence and is not a production consumer input.

PIT source resolution is fail-closed. Rows later than the business date may exist in a source file, but they must not be selected. If D-or-earlier rows are available, Strategy shadow records the future-row rejection count and selects the latest PIT row/window. If only future rows are available, the source resolves to `BLOCK` / `SOURCE_UNAVAILABLE` / `BOOTSTRAP_REQUIRED` as applicable. Corporate-event empty output means `NO_EVENT_CONFIRMED` only when source coverage is available and the producer passes; missing or partial coverage remains `SOURCE_UNAVAILABLE`, `SOURCE_PARTIAL`, or `REVIEW_REQUIRED`.

The single approved exception is J-Quants `earnings_calendar` scheduled-date avoidance. Historical validation may use the latest materialized current snapshot only for `earnings_scheduled_date_only`, labeled as `CURRENT_SNAPSHOT_CALENDAR_ONLY`. This is not a general latest fallback: market data, financial statements, listed issues, corporate actions, candidates, opportunity outputs, PM, portfolio state, broker snapshots, and every other Runtime input remain PIT-bound.

Historical Strategy source coverage is checked before long Runtime Test execution through the Strategy shadow source preflight embedded in `plan`:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 5 \
  --json
```

Read `strategy_shadow.source_preflight` before running 1BD or 5BD validation. Important fields are:

- `requested_start_date`: the operator-requested start date; the runner must not silently shift it.
- `required_warmup_start`: earliest quote date required for the Market Context lookback window.
- `market_coverage`, `listed_coverage`, `sector_coverage`, `corporate_event_coverage`: PIT source readiness and coverage dates.
- `candidate_generation_readiness`, `opportunity_generation_readiness`: date-by-date Runtime lifecycle producer readiness. Candidate/Opportunity artifacts are generated by the production-common `morning` job; Plan must not require preexisting daily outputs. Latest, shared-state, default-generation, and future-artifact fallback remain forbidden.
- `portfolio_state_readiness`, `pending_state_readiness`: mutable state readiness; actual Historical fresh-run state must come from isolated/reset run state, not active production Current.
- `eligible_dates`, `blocked_dates`, `first_eligible_start_date`, `root_blockers`, `operator_ready`.

Do not run 5BD when `operator_ready=false`. Use `first_eligible_start_date` only as an operator-visible recommendation; the requested start date remains unchanged in the failed preflight. Corporate Event `overall_event_coverage=PARTIAL` and Sector PIT review fields are review conditions, not permission to backfill current data.

Before any 10BD/20BD Runtime Test, complete the permanent J-Quants Corporate Event materialization procedure and validation gate in [J-Quants Data Operations Runbook](jquants_data_operations_runbook.md#corporate-event-validation-gate). Runtime Test commands must not be used as a substitute for J-Quants source materialization. A source file that exists is not automatically PIT coverage for a historical business date, except for the approved `earnings_calendar` schedule-only exception. The gate must expose `earnings_calendar_authority_type=CURRENT_SNAPSHOT_CALENDAR_ONLY`, `earnings_calendar_historical_pit_compliant=false`, `earnings_calendar_exception_scope=earnings_scheduled_date_only`, `non_calendar_future_leakage_used=false`, and `non_calendar_latest_fallback_used=false` before operator rerun review.

For the 10BD operator entry review, generate Corporate Event artifacts for every business date in the requested window and inspect `status`, `known_event_count`, `known_no_event_count`, `unknown_count`, source-scoped coverage, earnings-calendar authority metadata, and non-calendar PIT flags. Do not run the 10BD Runtime Test until the calendar-only validation evidence has passed review.

Status semantics are separated: `runtime_judgment` is the active Runtime result, `strategy_shadow_judgment` is the Phase22 Strategy result, and `overall_test_judgment` exposes both without promoting shadow artifacts to active consumers. `REVIEW_REQUIRED` in Strategy shadow does not automatically fail active legacy Runtime execution. Strategy shadow Runtime mutation detection is a HALT condition.

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
| `strategy` / `strategy-trace` / `strategy-attribution` / `strategy-readiness` / `strategy-shadow` | What did Phase22 Strategy shadow produce? | Run-scoped Strategy artifacts, trace, readiness, reasons, and legacy comparison |

When `--scope` is omitted, `summarize` uses a legacy-compatible full default. Existing top-level JSON fields are retained. New scope sections are additive, and non-selected explicit scopes are `null` in JSON.

The human output for the legacy-compatible default includes Run Summary, External Effect Summary, Performance Summary, PM Decision Summary, BUY / SELL Summary, REDUCE / EXIT Summary, Trade Attribution, Current Positions, Lifecycle Consistency, Review / Block Summary, and Operator Judgment. Explicit scopes render focused human summaries. `--write-evidence` writes only to `reports/runtime_tests/summaries/<summary_id>/` and records `summary_id`, `run_id`, `scope`, `generated_at`, contract versions, source evidence, authority, warnings, and selected scope sections.

Performance scope follows the Phase20 performance metric contract. Benchmark, Sector, and lot-level metrics are reported as `MISSING`, `DERIVABLE_PARTIAL`, or `NOT_AVAILABLE` when evidence is absent. Missing values are not zero-filled.

Positions and lifecycle scopes are symbol-level / Position Campaign observability. They must not be interpreted as stable lot-level analysis unless stable lot evidence exists. MFE, MAE, post-decision returns, loss avoided, profit missed, and counterfactual returns are marked `POST_HOC_ATTRIBUTION_ONLY` and must not be used as Runtime, Training, Calibration, Validation, or Accepted Generation authority.

Lifecycle consistency follows the REDUCE execution feasibility contract. A PM `REDUCE` is consistent when it resolves to exactly one executable partial SELL plan or exactly one approved non-executable terminal outcome with `execution_feasibility_status=NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY`, `reason=REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY`, no pending order, unchanged position quantity, and Runtime continuation `PASS`. Missing outcomes, conflicting plan plus terminal evidence, invalid terminal reasons, and position mutation remain `REVIEW_REQUIRED`.

Strategy scopes read run-scoped daily Strategy evidence. They do not generate Strategy artifacts, call Broker APIs, mutate Runtime state, or promote consumer eligibility.

For Strategy scope, `summarize --scope strategy --json` includes source-resolution rollups from `strategy_shadow_summary.json`: `pit_valid_dates`, `pit_blocked_dates`, `source_unavailable_dates`, `bootstrap_required_dates`, `root_blocker_counts`, `future_row_rejection_count`, `latest_fallback_used`, `current_state_leakage_detected`, `sector_pit_status`, and `corporate_event_coverage_status`.

`show --artifact strategy --business-date <DATE> --json` returns the daily Strategy shadow summary and embeds the same day's `source_manifest` when present. Without `--business-date`, it returns the run-level Strategy shadow summary.

## Marginal Capital SHADOW Backfill

```bash
PYTHONPATH=src python3 scripts/runtime_test.py shadow-backfill-marginal-capital \
  --source-run-id <RUN_ID> \
  --start-date <YYYY-MM-DD> \
  --end-date <YYYY-MM-DD> \
  --output-root reports/runtime_tests/analysis/<BACKFILL_ID> \
  --dry-run \
  --json

PYTHONPATH=src python3 scripts/runtime_test.py shadow-backfill-marginal-capital \
  --source-run-id <RUN_ID> \
  --start-date <YYYY-MM-DD> \
  --end-date <YYYY-MM-DD> \
  --output-root reports/runtime_tests/analysis/<BACKFILL_ID> \
  --confirm \
  --json
```

`shadow-backfill-marginal-capital` is a non-Runtime-mutating analysis command for applying the current `unified_marginal_capital_shadow.v1` evaluator to immutable historical Portfolio Construction PIT artifacts. It reads only `reports/runtime_tests/runs/<RUN_ID>/daily/<date>/strategy/portfolio_construction.json` for each requested date, does not invoke full Portfolio Construction, does not recompute Candidate / Opportunity / BQ / Entry / SI / PM, does not read live `.runtime` state, and writes only isolated analysis output under `reports/runtime_tests/analysis/<BACKFILL_ID>/`.

The command records dual provenance: original Production run/source/artifact identity and current DQ evaluator/source identity. It fails closed on missing daily PC artifacts, missing required DQ inputs, date mismatch, non-analysis output roots, or attempts to write inside the source run or `.runtime`. It must not be used as Production allocation authority; it is SHADOW analysis only.

For the current canonical source inventory, the first 5BD operator-ready Strategy source window is `2026-07-06` through `2026-07-10`. The user-operated command is:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 5 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Codex must not run this long validation. After the user runs it, inspect:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --scope strategy --json
PYTHONPATH=src python3 scripts/runtime_test.py validate --profile historical-smoke --json
```

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

Plan also lists `strategy_shadow_job` for each business date, including execution order, input authority, expected output path, mutation policy, failure policy, and active consumer eligibility. Strategy shadow must be visible in plan before it is run.

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

## Stop RUNNING Run

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py stop \
  --run-id <RUN_ID> \
  --dry-run
```

Actual stop:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py stop \
  --run-id <RUN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

`stop` is the formal operator command for a `RUNNING` Runtime Test run that
should not continue immediately.  It is evidence-only and does not roll back or
delete Ledger, Current, Pending, broker snapshots, daily artifacts, execution
evidence, position campaigns, completed business days, or performance evidence.

The command uses the existing HALT state model:

```text
RUNNING -> HALT
halted_at.runtime_test_job_status = OPERATOR_STOPPED
```

No separate top-level `STOPPED` run_state status is introduced.  A stopped run
is resume-compatible (`resume --dry-run` may be used if source baselines still
match) and abandon-compatible (`abandon --dry-run` then confirmed `abandon` when
the operator chooses not to resume).

Allowed source states:

- `RUNNING`: transitions to operator-stopped `HALT`;
- `HALT`: returns `ALREADY_STOPPED` without rewriting evidence.

Invalid transition behavior:

- unknown run id: rejected fail-closed;
- `COMPLETED`, closed, or `ABANDONED`: rejected fail-closed;
- corrupted or schema-invalid `run_state.json`: rejected fail-closed by run-state loading.

Dry-run reports the current run-scoped status, whether stop is eligible, the
target transition, files that would be modified, and `dry_run_no_mutation=true`.
Double stop is idempotent.  `run-status` reads the active profile-scoped
RUNNING/HALT run, while `show --run-id <RUN_ID>` reads the requested run's
run-scoped `run_state.json`.

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

## Resolve Corporate Action Adjustment Authority

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resolve-ca-adjustment-authority \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --symbol <CODE> \
  --event-type <OPERATOR_REVIEWED_EVENT_TYPE> \
  --effective-date <YYYY-MM-DD> \
  --adjustment-factor <FACTOR> \
  --pre-adjustment-quantity <QTY_BEFORE> \
  --post-adjustment-quantity <QTY_AFTER> \
  --current-quantity <QTY_AFTER> \
  --broker-available-quantity <QTY_AFTER> \
  --pending-quantity <PENDING_SELL_QTY> \
  --submit-quantity <SUBMIT_SELL_QTY> \
  --price-series-adjusted true \
  --quantity-adjusted true \
  --adjustment-already-applied true \
  --reviewer <OPERATOR_ID> \
  --audit-id <AUDIT_ID> \
  --resolution-reason <REASON> \
  --evidence-source <PATH> \
  --dry-run
```

Actual resolution:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resolve-ca-adjustment-authority \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --symbol <CODE> \
  --event-type <OPERATOR_REVIEWED_EVENT_TYPE> \
  --effective-date <YYYY-MM-DD> \
  --adjustment-factor <FACTOR> \
  --pre-adjustment-quantity <QTY_BEFORE> \
  --post-adjustment-quantity <QTY_AFTER> \
  --current-quantity <QTY_AFTER> \
  --broker-available-quantity <QTY_AFTER> \
  --pending-quantity <PENDING_SELL_QTY> \
  --submit-quantity <SUBMIT_SELL_QTY> \
  --price-series-adjusted true \
  --quantity-adjusted true \
  --adjustment-already-applied true \
  --reviewer <OPERATOR_ID> \
  --audit-id <AUDIT_ID> \
  --resolution-reason <REASON> \
  --evidence-source <PATH> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

`resolve-ca-adjustment-authority` is the canonical operator path for resolving one run/date/symbol Corporate Action Adjustment Authority after PIT evidence proves impact but not event type, adjusted quantity, or already-applied state. It writes only `.runtime/runtime_state/corporate_action_adjustments/<business_date>/<symbol>.json`, preserves the original unresolved artifact hash in the audit trail, and never submits orders, regenerates Pending, mutates Ledger/Current, or resumes a run.

The command rejects plan-expectation-only evidence, unknown event types, source hash/run-binding mismatches, future data, missing reviewer/audit id, unconfirmed already-applied status, unresolved price or quantity basis, double-adjustment risk, and stale Pending/Submit quantities that exceed the adjusted owned or broker-available quantity. `AdjFactor` remains an impact signal only; the operator supplies the event type and quantity reconciliation explicitly.

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

## Scoped Recovery / Replay

Scoped recovery commands are for halted Historical Runtime Test runs where a
specific day must be formally rewound before replay. Always create a backup
before applying an actual scoped recovery. Dry-run first.

### Failed Execution Recovery

Use `recover-failed-execution` only for failed execution or submit-only
precommit halt shapes. It requires the halted run to be at
`<business-date>:execution`, the current Pending to be a consumed failed-attempt
state, and target-date Ledger rows matching the failed execution or submit-only
precommit pattern.

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-failed-execution \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --rewind-to-job morning \
  --dry-run \
  --json
```

Actual recovery:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-failed-execution \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --rewind-to-job morning \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

### Partial Submit Recovery

Use `recover-partial-submit` only for submit-stage HALT runs where Submit
accepted at least one item before a later approved item was blocked, and no
target-date execution/current external effect has been written yet. This path
preserves accepted order and historical broker evidence, retires the mixed
Pending slot to `EMPTY`, records the accepted item as replay-excluded, and
rewinds the run for scoped replay.

Required shape:

```text
run_state.status = HALT
run_state.next_job = <business-date>:submit
current Pending state = REVIEW_REQUIRED
at least one Pending item = CONSUMED with matching ACCEPTED order evidence
at least one Pending item = APPROVED with canonical Submit guard block evidence
target-date Ledger orders >= 1
target-date Ledger executions/positions/cash/events = none
historical broker accepted evidence reconciles to preserved order rows
```

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-partial-submit \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --rewind-to-job morning \
  --expected-pending-plan-id <PENDING_PLAN_ID> \
  --dry-run \
  --json
```

Actual recovery:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-partial-submit \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --rewind-to-job morning \
  --expected-pending-plan-id <PENDING_PLAN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Do not use this command if target-date executions, positions, cash, or event
rows exist. Do not delete the accepted target-date order rows; replay Submit
must reconcile them through the existing pending-item submission reconciliation
contract.

### Stale Pending Recovery

Use `recover-stale-pending` when a halted run contains a same-day
`REVIEW_REQUIRED` Pending generated under stale semantics and the day must be
regenerated from the Pending producer boundary. It does not edit Ledger or
Current. It preserves the stale Pending and daily evidence, retires the current
Pending slot to `EMPTY`, removes target-day replay jobs from `completed_jobs`,
and rewinds `run_state.next_job` to the requested replay boundary.

Required shape:

```text
run_state.status = HALT
run_state.next_job = <business-date>:sell_planning
current Pending state = REVIEW_REQUIRED
current Pending target_session_date = <business-date>
target-date Ledger rows = none
```

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --rewind-to-job morning \
  --expected-pending-plan-id <PENDING_PLAN_ID> \
  --dry-run \
  --json
```

Actual recovery:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --rewind-to-job morning \
  --expected-pending-plan-id <PENDING_PLAN_ID> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Do not use `recover-stale-pending` if the target date already has Ledger rows;
audit the state and use the failed-execution recovery path if applicable.

### Replay Recovered Day

After an actual scoped recovery rewinds the run, use `replay-recovered-day` to
re-execute the allowed day jobs.

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py replay-recovered-day \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --jobs morning,sell_planning,submit,execution \
  --dry-run \
  --json
```

Actual replay:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py replay-recovered-day \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --jobs morning,sell_planning,submit,execution \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

After replay, inspect the regenerated Pending, Submit, Execution, and run_state
evidence before considering `resume --dry-run`.

### Partial Submit Day Finalization

Use `finalize-partial-submit-day` only after `recover-partial-submit` has been
applied and scoped replay has proven that the unresolved regenerated items are
same-day `REVIEW_REQUIRED` before any new Submit. This command finalizes the day
from preserved accepted order evidence only. It never resubmits the accepted
item, never executes reviewed regenerated items, and does not rerun Strategy,
Planning, or Submit.

Required shape:

```text
run_state.status = HALT
scoped_partial_submit_recovery.status = RECOVERY_APPLIED
current Pending target_session_date = <business-date>
current Pending state = REVIEW_REQUIRED
no unexpected approved item ids in current Pending
preserved accepted order rows exist
historical broker accepted evidence reconciles to preserved order rows
target-date Ledger executions = none
same-day Historical safety temporal authority = READY
```

Dry run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py finalize-partial-submit-day \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --dry-run \
  --json
```

Actual finalization:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py finalize-partial-submit-day \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id <RUN_ID> \
  --business-date <YYYY-MM-DD> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

After a `PASS`, run `resume --dry-run` for the same run before actual resume.

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

## Phase22-PR Strategy Shadow Checks

Phase22 Strategy shadow remains read-only. It must not write Pending, Submit, Execution, Fill, Ledger, Current, Broker state, or production Runtime switch state.

`summarize --scope strategy --json` exposes asset-proportional Strategy fields:

```text
portfolio_total_equity
current_cash
current_market_value
pending_reserved_cash
net_available_cash
target_cash_ratio
target_cash_amount
target_invested_ratio
target_invested_notional
current_invested_ratio
incremental_deployment_capacity
eligible_opportunity_count
meaningful_allocation_position_count
actual_target_position_count
legacy_max_positions
legacy_max_exposure
legacy_authority_active
strategy_fixed_position_cap_used
strategy_fixed_jpy_exposure_cap_used
safety_constraints_applied
```

Expected fixed-cap flags:

```text
strategy_fixed_position_cap_used = false
strategy_fixed_jpy_exposure_cap_used = false
```

`validate --run-id <RUN_ID> --json` checks strategy shadow structure plus ratio-to-notional consistency, fixed cap non-use, legacy isolation, Pending single deduction, and target weight sum. Historical probes that mix old business dates with current `.runtime` authority and therefore produce PIT `BLOCK` must not be treated as successful validation.

Operator 5BD validation command, not run by Codex:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 5 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Post-run checks:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --scope strategy --json
PYTHONPATH=src python3 scripts/runtime_test.py validate --profile historical-smoke --json
```

## Phase20-G Command Responsibility Audit

This section records the implemented Runtime Test CLI surface as of Phase20-G. It is a responsibility and observability integration guide only. It does not add commands, aliases, scopes, Runtime behavior, AI behavior, Position Management behavior, Risk behavior, Opportunity behavior, or Broker behavior.

Phase20-H implemented the Phase20-G recommendations for `run-status` and `summarize --scope`. The table below is retained as audit history; the canonical operational instructions are the `Run Status` and `Summarize` sections above.

### Current Subcommand Inventory

| Command | Operator Question | Primary Responsibility | Scope | Mutation | Confirmation | Input Authority | Output Authority | Evidence Path | Exit Codes | Implementation | Formatter / Schema | Tests / Coverage | Documentation | Overlap Candidates | Recommended Future State |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `status` | Is a Runtime Test runner active and what is the local runner state? | Runner state summary | Active run, current root summaries, latest backup | Read-only | No | Profile, runtime root, evidence root | `runtime_test_runner_v1` payload | None | `0`, error codes | `status` | default emit / runner schema | `test_phase17_k_runtime_test_runner.py`, `test_phase19_bj_runtime_test_abandon.py` | Documented | `system-status` naming | Future canonical `run-status`; keep `status` compatibility alias after implementation phase |
| `summarize` | What happened in this completed or closed run? | Run-scoped post-run summary | Run evidence, performance summary, PM counts, trading, reduce/exit, attribution, lifecycle | Read-only, optional evidence write | No | `reports/runtime_tests/runs/<run_id>/`, final-state hash match for current root reads | `runtime_test_summary_v1` | `reports/runtime_tests/summaries/<summary_id>/` with `--write-evidence` | `0`, `10`, `20`, error codes | `summarize_command` | `_format_runtime_test_summary` / inline schema | `test_phase19_bv_runtime_test_summarize.py`, Phase19-BY authority correction tests | Documented | Future performance / position lifecycle views | Extend with future `--scope overview|performance|positions|lifecycle|full`; do not create `diagnose` yet |
| `shadow-backfill-marginal-capital` | Can current DQ marginal-capital SHADOW be applied to immutable historical PC PIT artifacts? | Isolated marginal-capital SHADOW analysis backfill | Source run daily PC artifacts only, date window, dual provenance, summary | Analysis artifact write only; no Runtime state mutation | `--confirm` for actual artifact creation; no trading mutation flag | `reports/runtime_tests/runs/<run_id>/daily/<date>/strategy/portfolio_construction.json` | `runtime_test_marginal_capital_shadow_backfill_*` | `reports/runtime_tests/analysis/<backfill_id>/` | `0`, `60`, `70`, `90` | `shadow_backfill_marginal_capital_command` | default emit / backfill manifest, daily shadow, summary schemas | `test_phase32_dt_shadow_backfill_marginal_capital.py` | Documented | `summarize --scope strategy` | Keep as specialist non-mutating analysis generator; never promote to Production authority directly |
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
| `stop` | Should a RUNNING run be formally stopped before resume or abandon? | Operator stop lifecycle transition | Run-scoped `run_state.json` only | Evidence mutation only; no Trading State mutation | Yes for actual | Existing RUNNING/HALT run state | `runtime_test_run_state_v1` operator stop HALT record | `reports/runtime_tests/runs/<run_id>/run_state.json` | `0`, `60`, `70` | `stop_command` | default emit / run state schema | `test_phase17_k_runtime_test_runner.py` Phase29-L21T-AE tests | Documented | `resume`, `abandon`, `run-status`, `show` | Keep; no separate STOPPED top-level status |
| `resolve-ca-adjustment-authority` | Can an operator-reviewed PIT Corporate Action adjustment become canonical authority? | Per-symbol Corporate Action Adjustment Authority resolution | One run/date/symbol adjustment authority artifact | Mutates only `.runtime/runtime_state/corporate_action_adjustments/<date>/<symbol>.json` unless `--dry-run` | Yes for actual | Existing unresolved CA authority, PIT source hash, run/date/symbol binding, reviewer/audit id, quantity/price/idempotency proof | `runtime_v2_corporate_action_adjustment_authority_v1` plus `runtime_v2_corporate_action_operator_resolution_v1` audit trail | Runtime state authority artifact only | `0`, `60`, `70` | `resolve_ca_adjustment_authority_command` | default emit / operator resolution payload | `test_phase32_dl_ca_operator_resolution_and_sell_campaign_identity.py` | Documented | `resume`, `sell_planning`, `submit` | Keep; no order submit, Pending regeneration, Ledger/Current mutation, or AdjFactor event-type inference |
| `recover-failed-execution` | Can a failed execution or submit-only precommit halt be rewound for scoped replay? | Scoped failed execution recovery | Target-day failed Ledger/Pending/Broker evidence and run_state rewind | Mutating unless `--dry-run` | Yes for actual | HALT run at `<date>:execution`, consumed failed-attempt Pending, target-date failed rows | `runtime_test_scoped_failed_execution_recovery_plan_v1` | `reports/runtime_tests/runs/<run_id>/recovery/<recovery_id>/` | `0`, `60`, `70` | `recover_failed_execution_command` | default emit / recovery evidence schema | `test_phase17_k_runtime_test_runner.py` Q3B/Q1B recovery tests | Documented | `rollback`, `resume`, `recover-stale-pending` | Keep; do not use for stale REVIEW_REQUIRED Pending |
| `recover-partial-submit` | Can a partial submit HALT preserve accepted orders and rewind unresolved items for scoped replay? | Scoped partial submit recovery | Mixed Pending, accepted target-date orders, broker evidence, run_state rewind | Mutating unless `--dry-run` | Yes for actual | HALT run at `<date>:submit`, REVIEW_REQUIRED mixed Pending, accepted order rows, no execution/current rows | `runtime_test_scoped_partial_submit_recovery_plan_v1` | `reports/runtime_tests/runs/<run_id>/recovery/<recovery_id>/` | `0`, `60`, `70` | `recover_partial_submit_command` | default emit / recovery evidence schema | `test_phase17_k_runtime_test_runner.py` Phase32-AC tests | Documented | `recover-failed-execution`, `recover-stale-pending`, `resume` | Keep separate; preserves accepted order evidence and relies on Submit reconciliation during replay |
| `finalize-partial-submit-day` | Can an already recovered partial-submit day be finalized from preserved accepted orders only? | Accepted-items-only partial submit finalization | Preserved accepted order rows, historical broker evidence, execution/current projection, Pending terminalization, day completion | Mutating unless `--dry-run` | Yes for actual | Applied scoped partial submit recovery, regenerated same-day REVIEW_REQUIRED Pending, preserved accepted order rows, no target-date execution rows | `runtime_test_partial_submit_day_finalization_plan_v1` | `reports/runtime_tests/runs/<run_id>/recovery/<finalization_id>/` | `0`, `30`, `60`, `70` | `finalize_partial_submit_day_command` | default emit / finalization evidence schema | `test_phase17_k_runtime_test_runner.py` Phase32-AE tests | Documented | `recover-partial-submit`, `replay-recovered-day`, `resume` | Dedicated path for replay gap; never resubmits accepted items or executes reviewed regenerated items |
| `recover-stale-pending` | Can a same-day stale REVIEW_REQUIRED Pending be superseded so the day can be regenerated? | Scoped stale Pending recovery | Current Pending slot and target-day run_state replay records only | Mutating unless `--dry-run` | Yes for actual | HALT run at `<date>:sell_planning`, same-day REVIEW_REQUIRED Pending, no target-date Ledger rows | `runtime_test_scoped_stale_pending_recovery_plan_v1` | `reports/runtime_tests/runs/<run_id>/recovery/<recovery_id>/` | `0`, `60`, `70` | `recover_stale_pending_command` | default emit / recovery evidence schema | `test_phase17_k_runtime_test_runner.py` stale pending tests | Documented | `recover-failed-execution`, `resume` | Keep; do not use when target-date Ledger rows exist |
| `replay-recovered-day` | Can the officially rewound day be replayed from selected jobs? | Scoped day replay | Planned jobs subset: morning, sell_planning, submit, execution | Mutating unless `--dry-run` | Yes for actual | Existing run plan, run_state after scoped recovery | `runtime_test_run_state_v1` updates plus replay payload | `reports/runtime_tests/runs/<run_id>/daily/<date>/` | `0`, `70` | `replay_recovered_day_command` | default emit / replay payload | `test_phase17_k_runtime_test_runner.py` recovery coverage | Documented | `resume`, `run` | Keep scoped to recovered day jobs |
| `abandon` | Should a halted run be finalized as abandoned without touching trading state? | Abandon halted run | Run evidence finalization | Evidence mutation only, no trading mutation | Yes for actual except idempotent existing abandon | Existing halted run state | `runtime_test_abandonment_v1`, final summary | `reports/runtime_tests/runs/<run_id>/` | `0`, `60`, `70` | `abandon_command` | default emit / abandonment and final summary schemas | `test_phase19_bj_runtime_test_abandon.py` | Documented | `close`, `resume` | Keep |
| `rollback` | Restore resettable state from a backup? | Restore backup | Resettable trading state only | Mutating unless `--dry-run` | Yes for actual | Backup manifest | runner payload | Runtime root restored from backup | `0`, `50`, `60`, `70`, `90` | `rollback_command` | default emit / runner schema | `test_phase17_k_runtime_test_runner.py`, `test_phase17_ae_reset_scope_plan_gate.py` | Documented | `reset` backup dependency | Keep |
| `close` | Can this run be formally closed with final summary? | Finalize run evidence | Final summary and validation result | Evidence write only | No | Run state, validation result, current hashes | `runtime_test_final_summary_v1` | `reports/runtime_tests/runs/<run_id>/final_summary.json` | `0`, `10`, `70` | `close_command` | default emit / final summary schema | `test_phase17_k_runtime_test_runner.py`, `test_phase18v_runtime_test_fresh_run.py` | Documented | `abandon`, `summarize` | Keep |
| `show` | Show a raw run or backup artifact? | Artifact display | `run_state.json` or `backup_manifest.json` | Read-only | No | `--evidence-root`, `--run-id` or `--backup-id` | Source artifact wrapped by runner response | None | `0`, `60`, error codes | `show` | default emit / source artifact schema | `test_phase17_k_runtime_test_runner.py` Phase29-L21T-AE observability test | Documented | `list-runs`, `list-backups` | Keep as low-level inspection |
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
| Can I rewind a failed execution day for scoped replay? | `recover-failed-execution --dry-run`, then `recover-failed-execution --confirm ...`, then `replay-recovered-day` |
| Can I preserve accepted submit rows while regenerating unresolved same-day items? | `recover-partial-submit --dry-run`, then `recover-partial-submit --confirm ...`, then `replay-recovered-day` |
| Can I supersede a stale same-day REVIEW_REQUIRED Pending and regenerate the day? | `recover-stale-pending --dry-run`, then `recover-stale-pending --confirm ...`, then `replay-recovered-day` |
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
| Safety / Recovery | `backup`, `reset`, `rollback`, `abandon`, `close`, `validate`, `recover-failed-execution`, `recover-partial-submit`, `finalize-partial-submit-day`, `recover-stale-pending`, `replay-recovered-day` | Resettable state, evidence finalization, validation, scoped recovery and replay |
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

Authorized no-order submit days are also formal Runtime outcomes. Submit may continue with zero submissions only when Pending is an active `EMPTY` no-order plan bound to same-date Strategy Planning evidence, the order plan and approval artifact both say `NO_ORDER_AUTHORIZED`, source hashes match, Runtime Planning is `PASS`, `quantity_unresolved_count=0`, `review_required_quantity_count=0`, and pending items are empty. `EMPTY` pending by itself is not approval, missing approval evidence is not no-order authority, and rejected/review/block states remain fail-closed. On authorized no-order days, Submit writes no broker request, performs no external delivery, records `submit_action=NO_SUBMISSION_REQUIRED`, and Execution may continue with zero orders/fills as `NO_ACTION`.

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
