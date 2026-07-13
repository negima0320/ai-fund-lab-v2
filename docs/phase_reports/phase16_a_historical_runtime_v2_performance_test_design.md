# Phase16-A Historical Runtime v2 Performance Test Design

作成日: 2026-07-13

## Initial Design Only / Superseded by Phase16-H and Phase16-I

Phase16-A is initial design evidence only.

Current official positioning:

```text
Phase16:
Operational Data Foundation

Phase17:
Historical Runtime v2 Performance Test
```

Phase16-I clarifies that Phase16 is not a Historical-only, Backtest-only, Replay-only, or Phase16-only foundation. Phase16 builds the common operational data foundation used by Production, Demo, Paper, and Historical modes.

Phase16-A is preserved as the initial Historical Runtime Test design and as evidence for the Phase16-A to Phase16-G readiness investigation.

Phase16-H revises the official Phase16 objective:

```text
Old Phase16 objective:
Historical Runtime v2 Performance Test

New Phase16 objective:
Canonical Data Foundation and Historical Runtime Readiness
```

Phase16-I revises the official Phase16 name and objective again:

```text
Official Phase16 name:
Operational Data Foundation

Official Phase16 purpose:
Production、Demo、Paper、Historicalが同一のCanonical Data Contract、Feature Producer、Feature Schema、AI Artifact、AI Decision Contract、Runtime v2 Mainlineを利用できる恒久的な運用データ基盤を完成させる。
```

Phase16 does not run the Historical Performance Test.

Phase16 completes:

- Canonical Data Foundation
- Historical Runtime Readiness
- Model / Config Freeze prerequisites
- Backup / Reset / Restore prerequisites
- Historical Broker boundary prerequisites
- Point-in-time data and feature readiness

Phase17 runs the Historical Runtime v2 Performance Test.

Phase16-A to Phase16-G are reclassified as prerequisite investigation phases:

| Phase | Revised position |
|---|---|
| Phase16-A | Initial Historical Runtime Test Design |
| Phase16-B | Prerequisite Audit |
| Phase16-C | Temporal Bug Audit |
| Phase16-D | Temporal Bug Fix |
| Phase16-E | Prerequisite Re-Audit |
| Phase16-F | AI State and Data Lineage Audit |
| Phase16-G | Canonical Historical Data Audit |

Performance-test steps originally described in this document are moved to Phase17 and must not be executed during Phase16.

## Final Judgment

```text
PHASE16_A_HISTORICAL_RUNTIME_V2_TEST_DESIGN_ACCEPTED_WITH_PREREQUISITES
```

Phase16-A defines the design for long-term historical performance testing using accepted Runtime v2 as the fixed engine.

No `.runtime` reset, Current mutation, Ledger mutation, Pending mutation, broker API call, 5BD run, 20BD run, 1Y run, full-period run, AI retraining, model change, or trading logic optimization was performed.

## Original Purpose Before Phase16-H Amendment

Before Phase16-H, this document proposed that Phase16 evaluate:

- long-term Runtime v2 operational performance
- whole AI trading system performance
- state continuity
- long-term Contract consistency
- return and drawdown
- failures, inconsistencies, and bugs

This is not a simple AI-model backtest.

After Phase16-H, these performance-test activities are deferred to Phase17. Phase16 uses this document only as readiness-investigation evidence and does not execute the performance-test portions.

## Runtime Fixed Engine

Runtime v2 remains fixed.

Do not change Runtime for:

- low return
- low annualized return
- low win rate
- high drawdown
- low trade count
- high cash ratio
- long holding period

Investigate these first:

- Candidate AI
- Opportunity AI
- Position Management AI
- Feature
- Policy
- Safety
- Capital Allocation
- Execution assumptions
- market regime

Runtime bug fixes are allowed only with evidence of Runtime Core defects such as double submit, double ledger, Current/Cash/Quantity inconsistency, Pending lifecycle inconsistency, Temporal/Authority violation, nondeterminism, normal mainline bypass, restore failure, or no-fill update error.

## Normal Runtime Root Policy

Phase16 uses the normal Runtime root:

```text
.runtime
```

Confirmed normal fixed paths:

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
.runtime/pending_order_plan/pending_order_plan.json
.runtime/runtime_state/current_state.json
.runtime/runtime_state/run_manifest/
.runtime/runtime_state/logs/
```

Phase16-specific Runtime root/path/mainline/backtest engine is prohibited.

Backup/evidence directories may be used for preservation only. They are not active Runtime roots.

## Current Runtime State Investigation

Current `.runtime` contains:

- active persistent ledger files
- active pending plan
- active runtime state
- runtime manifests/logs for Phase15 acceptance dates
- broker readonly evidence
- safety evidence
- market evidence
- current valuation/current migration evidence
- historical Phase artifacts

Phase15 evidence and reports must not be deleted.

## Reset Policy

Phase16-B must reset normal Runtime state to:

```text
initial_cash=1,000,000 JPY
initial_positions=0
initial_pending_orders=0
initial_open_orders=0
initial_executions=0
initial_realized_pnl=0
initial_unrealized_pnl=0
```

Reset scope:

- Current
- Runtime State
- Persistent Ledger
- Pending
- Approval state
- Execution state
- Historical Simulated Broker state
- Idempotency state
- Runtime operational report state

Forbidden:

- manual JSON editing
- partial file deletion
- Current-only reset
- Ledger-only reset
- Current/Ledger mismatch
- Phase16-specific path switching
- initialization that bypasses normal mainline contracts

## Current Reset Mechanism

Existing helper found:

```text
src/ai_fund_lab_v2/runtime_v2/asset/initializer.py
initialize_demo_operation_current_sot
```

It initializes demo operation Current with JPY 1,000,000 and backs up persistent ledger files, but it is Phase14e8/demo-specific and does not reset all Phase16 required state.

Current conclusion:

```text
FORMAL_PHASE16_RESET_CLI_NOT_FOUND
```

Phase16-B prerequisite:

```text
NORMAL_RUNTIME_BACKUP_RESET_RESTORE_CONTRACT_REQUIRED
```

## Backup / Restore Policy

Before reset, preserve:

- Current
- Runtime State
- Persistent Ledger
- Pending
- Approval
- Executions
- Manifest
- Hashes
- Reports
- Git commit
- Runtime version

Backup manifest must include:

```text
backup_id
source_paths
file_hashes
file_counts
git_commit
runtime_version
created_at
restore_command_or_procedure
validation_hashes
```

Restore must be all-or-nothing.

Phase16 final results must be preserved, then normal Runtime must be clean-reset again before production preparation.

## Historical Period

Requested:

```text
requested_start_date=2021-07-01
end_date=latest_available_trading_date
```

Effective start date must be the first business day after 2021-07-01 where all required lookback/data/model inputs are valid.

Manifest fields:

```text
requested_start_date
effective_start_date
latest_available_date
business_day_count
excluded_dates
exclusion_reasons
```

## AI Retraining Status

```text
AI_RETRAINING=PROHIBITED
```

The accepted model artifacts present at Phase16 start must be frozen and used across the run. Manifest must include model name, artifact path, version, hash, training period, feature schema version, accepted status, and generated time.

## Backtest Feedback Policy

Historical results must not feed the same run.

PnL, win rate, drawdown, successful symbols, failed trades, future prices, future Current, future Safety, and future PM decisions cannot influence Feature, AI, Policy, Safety, Capital Allocation, Submit, or Execution in the same run.

Phase16-E/F may use results for analysis and improvement design only. Improved evaluation must use separate version/run/manifest/result.

## Historical Clock

Existing CLI findings:

- `run_daily_operation` supports `--business-date`.
- `run_daily_operation` supports `--evaluation-time`.
- Many freshness-producing jobs accept the historical evaluation time.
- `business_date` falls back to `date.today()` if omitted.
- `started_at`, `finished_at`, and `run_id` use real UTC time.

Phase16 must always pass explicit `--business-date` and `--evaluation-time`.

Classification:

| Finding | Classification |
|---|---|
| omitted `--business-date` uses today | `CLOCK_CONFIGURATION_GAP` |
| actual timestamps in run_id/started_at/finished_at | `EXPECTED_NON_DETERMINISM` unless used in state hash |
| missing historical clock support in any required component | `HISTORICAL_ADAPTER_REQUIREMENT` or `TEMPORAL_CONTRACT_BUG` after evidence |

## Historical Simulated Broker

The Historical Simulated Broker replaces only the broker boundary.

Runtime Submit, Execution, Ledger, Current, and Report paths must remain normal.

Contract must define:

```text
order submit date
target session
fill date
fill price source
BUY fill rule
SELL fill rule
market order rule
limit order rule
lot size
trading unit
tick size
daily price limit
suspension
no quote
missing data
unfilled order
partial fill
insufficient cash
insufficient quantity
fees
tax
slippage
corporate actions
stock split
reverse split
delisting
duplicate submit
execution idempotency
```

Evidence classification:

```text
simulation=true
historical_replay=true
broker_write=false
production_equivalent=false
acceptance_only=false
```

## Normal Mainline

Required mainline:

```text
Market
↓
Feature
↓
Candidate AI
↓
Opportunity AI
↓
Policy
↓
Safety
↓
Capital Allocation / Planning
↓
Authoritative Pending
↓
Submit Guard
↓
Historical Simulated Broker
↓
Execution Processor
↓
Ledger Writer
↓
Current Projector
↓
Current Apply
↓
Runtime State
↓
Runtime Report / Audit
```

No profit-only backtest engine.

## Disabled Components

Out of scope / prohibited:

- Tachibana API ReadOnly
- Tachibana Demo Write
- Tachibana Production Write
- Demo trading
- Production Broker Write
- Discord send
- LINE send
- Blog publish
- Public Blog Markdown as required output
- Notification Delivery

Required:

- Runtime internal report
- Audit report
- Performance report

Current CLI gap:

`run_daily_operation` currently generates public report and notification payload artifacts unconditionally after job execution. Delivery is false, but Phase16 should either disable optional public/blog/payload artifacts by configuration or classify this as:

```text
OPTIONAL_COMPONENT_CONFIGURATION_GAP
```

If this dependency blocks historical operation, reclassify as:

```text
RUNTIME_CORE_DEPENDENCY_BUG
```

## Look-Ahead Prevention

Design requirements:

- Point-in-time Universe
- Point-in-time listed status
- Point-in-time financial availability
- Corporate action handling
- Feature cutoff
- Decision cutoff
- Fill cutoff

Audit must catch:

- same-day close used before decision time
- next-day price in features
- future label leakage
- full-period normalization leakage
- future delisting/listed status leakage
- future financial disclosure leakage
- future corporate action misuse
- historical result feedback

## Runtime Integrity Metrics

- Runtime failure count
- Retry count
- State inconsistency count
- Idempotency conflict count
- Temporal error count
- Safety halt count
- Review required count
- Pending lifecycle error count
- Execution classification error count
- Current restore error count
- Current consistency
- Ledger consistency
- Runtime State consistency
- Authority correctness
- Determinism
- Normal Mainline use

## Performance Metrics

- Total Return
- Annualized Return
- Maximum Drawdown
- Profit Factor
- Win Rate
- Average Return per Trade
- Median Return per Trade
- Average Gain
- Average Loss
- Payoff Ratio
- Exposure
- Cash Utilization
- Turnover
- Trade Count
- Average Holding Period
- Unfilled Count
- Safety Block Count

Runtime Integrity failure periods are excluded from official performance.

## Attribution

Phase16-E classifies findings into:

```text
Candidate AI
Opportunity AI
Position Management AI
Feature
Policy
Safety
Capital Allocation
Execution assumption
Market regime
Data defect
Runtime defect
Unknown
```

Do not confuse performance issue, Runtime bug, data issue, model limitation, policy limitation, or execution simulation bias.

## Determinism

Same inputs must produce same daily decisions, Pending, Executions, Ledger, Current, cash, positions, PnL, Runtime reports, and final hashes.

Frozen inputs:

```text
Git commit
Runtime version
Model version/hash
Feature schema/hash
Policy version/hash
Safety version/hash
Capital Allocation version/hash
Initial Current/hash
Market data/hash
Calendar version/hash
Historical Broker config/hash
```

Divergence classification:

```text
CLOCK_DEPENDENCY
UNSTABLE_INPUT
CONFIGURATION_DRIFT
DATA_DRIFT
RUNTIME_BUG
EXPECTED_NON_DETERMINISM
UNKNOWN_DIVERGENCE
```

## Phase16-B To I Gates

| Phase | Gate |
|---|---|
| Phase16-B | Formal reset plus 5BD Historical Smoke using normal `.runtime`; validate Current/Ledger/Pending/Runtime State hashes, no broker write, no notification send, no Phase16-specific path. |
| Phase16-C | 20BD continuity; verify carryover, BUY/SELL/HOLD/no-trade/no-fill, valuation-only update, Pending consume, rerun, recovery, reports, hash continuity, append-only Ledger. |
| Phase16-D | 1Y Runtime performance and integrity metrics. |
| Phase16-E | Performance/failure/runtime attribution. |
| Phase16-F | Improvement design outside Runtime Core unless Runtime bug evidence exists. |
| Phase16-G | Improved version 1Y revalidation with separate version/run/manifest. |
| Phase16-H | Full 2021-07 to latest historical test. |
| Phase16-I | Final performance and Production readiness review. |

## Required Before Phase16-B

```text
NORMAL_RUNTIME_BACKUP_RESET_RESTORE_CONTRACT_REQUIRED
HISTORICAL_SIMULATED_BROKER_CONTRACT_REQUIRED
HISTORICAL_CLOCK_JOB_AUDIT_REQUIRED
MODEL_ARTIFACT_FREEZE_MANIFEST_REQUIRED
HISTORICAL_PERIOD_READINESS_AUDIT_REQUIRED
OPTIONAL_PUBLIC_REPORT_NOTIFICATION_CONFIGURATION_DECISION_REQUIRED
```

## Acceptance Criteria Result

| Criterion | Status |
|---|---|
| Phase16 purpose defined | PASS |
| Runtime fixed policy defined | PASS |
| normal Runtime root defined | PASS |
| normal fixed paths defined | PASS |
| Phase16-specific Runtime root prohibited | PASS |
| normal mainline use defined | PASS |
| start reset policy defined | PASS |
| final reset policy defined | PASS |
| Backup / Restore policy defined | PASS |
| 2021-07 onward period defined | PASS |
| AI retraining prohibited | PASS |
| backtest feedback prohibited | PASS |
| Historical Broker defined | PASS |
| Historical Clock defined | PASS_WITH_GAPS |
| Tachibana API excluded | PASS |
| Blog / LINE / Discord excluded | PASS_WITH_OPTIONAL_COMPONENT_GAP |
| Look-ahead prevention defined | PASS |
| Runtime Integrity and Performance separated | PASS |
| Runtime bug and Performance issue separated | PASS |
| Phase16-B to I Gates defined | PASS |
| Roadmap aligned | PASS |

## Next Prefix

```text
Phase16-B
```
