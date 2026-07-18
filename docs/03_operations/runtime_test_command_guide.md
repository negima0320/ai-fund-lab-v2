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
- Historical commands must use `--runtime-root .runtime`.
- Production use is blocked by the runner.
- Mutating commands require both:

```bash
--confirm --yes-i-understand-this-mutates-trading-state
```

- Use `--dry-run` before any mutating command.

## Status

```bash
PYTHONPATH=src python3 scripts/runtime_test.py status
PYTHONPATH=src python3 scripts/runtime_test.py status --json
```

Shows Runtime root, environment, active run, Current/Ledger/Pending/Runtime State summaries, Registry checkpoint, accepted artifact hash, latest backup, and external effect policy. Status is read-only.

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
- Actual rollback remains a separate explicit command with confirmation flags.

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

Close performs final validation, final state freeze, final summary generation, test validity judgment, acceptance gate judgment, and post-close lifecycle recommendation. It does not reset state.

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
