# Historical Runtime Test Contract

作成日: 2026-07-13

## Phase16-H Amendment

This contract remains the permanent Historical Runtime Test contract. Phase16-H changes the implementation and execution phase assignment, not the contract's meaning.

## Phase16-I Amendment

Phase16-I clarifies that Phase16 is:

```text
Operational Data Foundation and readiness prerequisites
```

Phase17 is:

```text
Historical Runtime Test execution
```

This contract is retained as the Phase17 Performance Test Contract.

Phase16 prepares the common Operational Data Foundation used by Production, Demo, Paper, and Historical modes. This contract must not require a Historical-only, Backtest-only, Replay-only, or Phase16-only Canonical Data Source, Feature Store, Runtime root, Current, Ledger, Pending, or mainline.

Historical Runtime execution must consume the same accepted Canonical Data Contract, Feature Producer, Feature Schema, AI Artifact, AI Decision Contract, and Runtime v2 Mainline that Production, Demo, and Paper are expected to use.

Contract implementation phase:

```text
Phase16 readiness
```

Contract execution phase:

```text
Phase17 execution
```

Phase16 completes the common Operational Data Foundation and prerequisites needed to run this contract correctly:

- Operational Data Foundation prerequisites
- Runtime operational prerequisites
- Model / Config Freeze prerequisites
- Backup / Reset / Restore prerequisites
- Historical Broker boundary prerequisites
- Point-in-time data and feature guard prerequisites

Operational lifecycle and environment transition boundaries are defined in:

```text
docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md
```

Historical Runtime Test output is evidence. Historical Trading State, Ledger, Pending, Current, PnL, Feature Artifacts, and Decision Artifacts must not become Tachibana Demo or Production trading authority.

Phase17 executes the Historical Runtime Performance Test defined by this contract.

Phase16 must not run 5BD, 20BD, 1-Year, or full-period Historical Runtime Performance Tests.

## Purpose

Phase17 evaluates long-term operation of the accepted Runtime v2 control system with historical data from July 2021 onward. Phase16 prepares the Operational Data Foundation and readiness prerequisites required for that execution.

This is not a standalone AI backtest. It is a Runtime v2 performance and integrity test that runs the normal Runtime root, normal fixed paths, normal CLI, and normal mainline as close as possible to production operation, while replacing external broker writes with a Historical Simulated Broker adapter.

## Fixed Engine Policy

Runtime v2 is fixed.

Do not change these for performance improvement:

- Runtime State Machine
- Current authority
- Persistent Ledger
- Pending authority
- Submit Pipeline and Submit Guard
- Execution Processor
- Ledger Writer
- Current Projector and Current Apply
- Runtime Report
- Idempotency control
- Authority Contract
- Temporal Contract

Poor return, low win rate, high drawdown, low turnover, high cash, or long holding period are not Runtime change reasons.

Runtime changes are allowed only when evidence shows a Runtime Core bug, such as double submit, double execution, double ledger write, double PnL, Current/Cash/Quantity inconsistency, Pending lifecycle inconsistency, Temporal/Authority violation, nondeterministic state transition for identical inputs, bypass of normal mainline, failed state restore, or incorrect no-fill update.

## Normal Runtime Root Policy

Phase16 readiness and Phase17 execution use the normal Runtime root and normal fixed paths:

```text
.runtime/
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

Phase16-specific or Phase17-specific Runtime roots, Current paths, Ledger paths, Pending paths, State Machines, Submit paths, Current Apply paths, or standalone backtest engines are prohibited.

Evidence backup paths may be created for preservation, but they are not Runtime roots and must not be used as the active Runtime input.

## Phase17-B1I-A Historical Environment Composition Amendment

Historical Runtime execution is a formal Runtime environment composition, not an alternate mainline and not the standalone simulation harness.

Formal identity:

```text
run_type=HISTORICAL
runtime_mode=historical
broker_environment=historical_simulated
runtime_root=.runtime
external_delivery=false
broker_write=false
```

The official CLI mode is:

```text
--mode historical
```

`--mode simulation` is not a formal Runtime environment. If retained for older fixtures, it must remain a compatibility-only alias or test fixture label and must fail closed in operational Runtime composition.

Historical mode requires explicit temporal identity:

```text
--business-date
--evaluation-time
```

Fallback to wall-clock current date or current time is prohibited for historical execution.

Historical composition selects only:

- `HistoricalSubmitAdapter`
- `HistoricalExecutionSnapshotProvider`

Historical composition must not instantiate Tachibana Demo submit adapters, Tachibana Production submit adapters, or Tachibana Broker ReadOnly snapshot providers. Submit Guard and Execution Processor remain the normal Runtime v2 guard/processor boundaries and must not be bypassed.

External effects are disabled:

```text
tachibana_readonly=false
tachibana_demo_write=false
tachibana_production_write=false
notification_delivery=false
discord_send=false
line_send=false
blog_publish=false
external_delivery=false
broker_write=false
```

Historical manifests must include:

```text
run_type
runtime_mode
broker_environment
simulation=true
historical_replay=true
broker_write=false
production_equivalent=false
acceptance_only=false
external_delivery=false
runtime_root
environment_id
run_id
business_date
evaluation_time
```

Until the Historical Broker fill model is separately accepted, Historical Submit and Historical Execution must fail closed with `NOT_IMPLEMENTED_BLOCKING` and must not create accepted fills, mutate Current, consume Pending, or write broker-equivalent external effects.

## Phase17-G Historical Submit Guard And Fill Model Amendment

Phase17-G accepts a limited Historical Submit Guard and Historical Fill Model for the 5BD Historical Runtime Smoke Test only.

This amendment does not create a Historical-only Runtime, Feature Producer, Current, Ledger, Pending, Runtime State, Submit path, or Execution Processor. Historical execution must still enter through Runtime v2 Mainline and the normal Submit Guard.

Submit Guard Environment Matrix:

| environment | required pending | required adapter | broker write | external delivery | result |
|---|---|---|---:|---:|---|
| Demo | `demo` | Demo submit adapter | true | allowed by Demo policy | normal Demo guard |
| Historical | `historical` | `HistoricalSubmitAdapter` | false | false | allowed only after common Approval / Policy / Safety / Pending / Duplicate / Temporal / Cash / Quantity guards pass |
| Production | `production` | Production submit adapter | explicit acceptance only | production policy | fail closed without production acceptance |

Historical `broker_write=false` means no external broker write, no Tachibana Demo write, no Tachibana Production write, no raw request/response/secret persistence, and no external delivery. It does not mean the Runtime mainline is bypassed or acceptance-only. Accepted Historical evidence may be consumed by the normal Execution Processor as a simulated broker snapshot.

Accepted 5BD smoke fill rule:

- Order type: `MARKET` only.
- Fill date: `target_session_date == business_date`.
- Fill time: session open evidence timestamp, represented as `09:00:00+09:00`.
- Fill price: Canonical normalized OHLCV `Open` for `(business_date, symbol)`.
- Source authority: 5BD PIT manifest source hash plus Canonical OHLCV hash match.
- Universe authority: Listed Issues PIT membership as of business date.
- Corporate action guard: raw OHLCV `AdjFactor == 1.0` for the business date, otherwise halt.
- Lot / trading unit: use explicit `listed_info.trading_unit` when present; otherwise rely on existing Runtime Pending / Approval / Broker Capability quantity authority and record `ACCEPTED_EXISTING_RUNTIME_QUANTITY_AUTHORITY`. The model must not invent an unconditional 100-share rule.
- Duplicate prevention: deterministic historical order and execution identities; existing evidence path blocks resubmit.
- BUY cash and SELL quantity remain normal Runtime Submit Guard responsibilities.

Out of scope for this accepted 5BD smoke model:

- fees
- tax
- slippage
- partial fill
- non-market limit-order execution rule
- full long-term official performance execution model

If any of the required PIT source, universe, Corporate Action no-impact, market price, or environment matrix evidence is missing or inconsistent, Historical Submit must fail closed before accepted fill evidence is created.

## Reset Policy

Before Phase17 execution starts, Phase16 readiness must provide a formal mechanism to reset the normal Runtime state to:

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

Phase16 does not perform Historical Runtime Performance Test reset for execution. It defines, implements, and accepts the reset requirement before Phase17.

Manual JSON editing, partial deletion, Current-only reset, Ledger-only reset, Current/Ledger mismatch, Phase16-specific path switching, and mainline bypass are prohibited.

## Backup And Restore Policy

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

Backup must record source paths, hashes, file counts, generated time, Git commit, Runtime version, and restore instructions.

Restore must be all-or-nothing. Partial restore is prohibited.

Phase16 readiness evidence and Phase17 execution evidence must be preserved. The normal Runtime must be clean-reset again before any production preparation state is generated.

## Historical Period

Requested period:

```text
requested_start_date=2021-07-01
end_date=latest_available_trading_date
```

Effective start date must satisfy:

- Market Data exists.
- Required lookback exists.
- Feature generation is possible.
- Candidate AI input is valid.
- Opportunity AI input is valid.
- Position Management AI input is valid.
- Trading Calendar resolves.
- Point-in-time Universe is valid.

Manifest fields:

```text
requested_start_date
effective_start_date
latest_available_date
business_day_count
excluded_dates
exclusion_reasons
```

## AI Retraining Prohibition

AI retraining is prohibited during Phase16 readiness and Phase17 historical runs.

Prohibited:

- Candidate AI retraining
- Opportunity AI retraining
- Position Management AI retraining
- fine tuning
- rolling retraining
- walk-forward retraining
- additional training during the run
- model selection from historical test results

Manifest must freeze:

```text
model_name
model_artifact_path
model_version
model_hash
training_period
feature_schema_version
accepted_status
generated_at
```

## Backtest Feedback Prohibition

Historical test results must not feed the same run.

Prohibited inputs:

- PnL
- win rate
- Profit Factor
- drawdown
- symbol-level PnL
- selected/bought/sold symbols from future days
- successful/failed trades
- future prices or returns
- future Current
- future Safety
- future PM decisions

Results may be used after Phase17 execution for attribution and improvement design. Improved evaluation must use a separate version, run id, manifest, and result set.

## Historical Clock

Phase16 readiness defines and validates the Historical Clock without changing the normal mainline. Phase17 execution uses the accepted Historical Clock. Existing `--business-date` and `--evaluation-time` are the preferred injection points.

Separate:

```text
runtime_business_date
trading_session_date
latest_expected_trading_date
latest_available_market_date
market_data_as_of
feature_date
position_state_as_of
valuation_as_of
pending_target_session_date
artifact_generated_at
historical_evaluation_time
```

Known implementation findings:

- `run_daily_operation` supports `--business-date`.
- `run_daily_operation` supports `--evaluation-time` and passes it to Safety, Runtime State, Current temporal migration, Current valuation, Broker ReadOnly, Promotion, and Apply.
- CLI `started_at`, `finished_at`, and `run_id` still use actual UTC time.
- `business_date` falls back to `date.today()` when omitted.
- Some freshness and calendar behavior still needs job-by-job audit before Phase17 5BD execution.

Classification:

- Actual run id timestamps: `EXPECTED_NON_DETERMINISM` unless deterministic run id is required.
- Omitted business date fallback: `CLOCK_CONFIGURATION_GAP`; Phase16 readiness and Phase17 execution must always pass `--business-date`.
- Components not accepting historical evaluation time: classify as `HISTORICAL_ADAPTER_REQUIREMENT` or `TEMPORAL_CONTRACT_BUG` after evidence.

## Historical Simulated Broker

Historical Simulated Broker replaces the external broker boundary only. Runtime Submit, Execution, Ledger, Current, and Report paths must remain normal.

The broker contract must define:

- order submit date
- target session
- fill date
- fill price source
- BUY fill rule
- SELL fill rule
- market order rule
- limit order rule
- lot size
- trading unit
- tick size
- daily price limit
- suspension
- no quote
- missing data
- unfilled order
- partial fill
- insufficient cash
- insufficient quantity
- fees
- tax
- slippage
- corporate actions
- stock split
- reverse split
- delisting
- duplicate submit
- execution idempotency

Execution evidence must be transformed into the existing Execution Processor schema.

Required classification:

```text
simulation=true
historical_replay=true
broker_write=false
production_equivalent=false
acceptance_only=false
```

## Normal Mainline

Required Phase17 execution mainline, prepared by Phase16 readiness:

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

Do not add a profit-only backtest engine.

## Disabled External Components

Do not execute:

- Tachibana API ReadOnly
- Tachibana Demo Write
- Tachibana Production Write
- Demo trading
- Production Broker Write
- Discord send
- LINE send
- Blog publish
- Public blog generation unless current CLI cannot disable it
- Notification delivery

Required:

- Runtime internal report
- Audit report
- Performance report

Current CLI finding:

`run_daily_operation` always calls public report and payload artifact generation after the job block. This is acceptable for payload-only evidence but conflicts with Phase16 public blog not-required policy. If it cannot be disabled by configuration, classify as `OPTIONAL_COMPONENT_CONFIGURATION_GAP` unless it blocks historical operation.

## Look-Ahead Prevention

Each business day may use only information available at that day’s decision cutoff.

Audit:

- no same-day close before pre-open decision
- no next-day price in features
- no future label leakage
- no full-period normalization leakage
- no current universe applied to past dates
- no future delisting applied to past dates
- no future financial disclosure
- no future corporate action misuse
- no feedback from historical results

Required design:

- Point-in-time Universe
- Point-in-time listed status
- Point-in-time financial availability
- Corporate action handling
- Feature cutoff
- Decision cutoff
- Fill cutoff

## Metrics

Runtime Integrity:

- Current consistency
- Ledger consistency
- Pending lifecycle
- Runtime State consistency
- Execution lifecycle
- Temporal correctness
- Authority correctness
- Idempotency
- Determinism
- State restoration
- Normal mainline use

Investment Performance:

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

Performance from periods with Runtime Integrity failure must not be accepted as official performance.

## Determinism

Same inputs must produce same results:

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

Compare:

- daily decisions
- Pending
- Executions
- Ledger
- Current
- cash
- positions
- PnL
- Runtime reports
- final hashes

Divergence classification:

- `CLOCK_DEPENDENCY`
- `UNSTABLE_INPUT`
- `CONFIGURATION_DRIFT`
- `DATA_DRIFT`
- `RUNTIME_BUG`
- `EXPECTED_NON_DETERMINISM`
- `UNKNOWN_DIVERGENCE`

## Phase Gates

### Phase16 Readiness Gates

Phase16-H: Scope Revision and Canonical Data Foundation.

Phase16-I: Operational Data Foundation Purpose and Goal Definition.

Phase16-J: Operational Data Architecture Contract.

Phase16-K: AI Artifact Registry and Capital Allocation Contract Design.

Phase16-L: Artifact Physical Path, Registry Integration, and Migration Sequence Design.

Phase16-M: Operational Data Foundation Executive Architecture Review.

Phase16-N: Executive Architecture Review Minor Amendment Closure.

Post Phase16-N: remaining Operational Data Foundation work must be resequenced by review before implementation. Superseded historical labels such as "Canonical Path and Data Lineage Migration Design", "Canonical Market Data Foundation", "Calendar / Listed / Corporate Action Foundation", and "Canonical Feature Producer Connection" are historical plan evidence only and are not current Phase16-K/L/M/N gates.

Phase16-O: Operational Lifecycle, State Reset Boundary, and Environment Transition Contract.

Post Phase16-O: remaining Operational Data Foundation work must be resequenced by review before implementation, including Operational Backup / Reset / Restore, AI Model and Policy Freeze, Historical Broker Boundary, Point-in-time Guard, and Readiness Acceptance.

Phase16 Final: Phase16 Final Review and Phase17 Handoff.

### Phase17 Execution Gates

Phase17-A: Reset normal Runtime and run 5 business days. Primary judgment is normal mainline and state continuity, not performance.

Phase17-B: Run 20 business days and verify daily Current restore, cash/position carryover, BUY/SELL/HOLD/no-trade/no-fill days, valuation-only update, Pending consume, rerun, recovery, report continuity, hash continuity, and append-only Ledger.

Phase17-C: Run 1 year and evaluate Runtime failure counts plus performance metrics.

Phase17-D: Attribute performance/failure to Candidate AI, Opportunity AI, PM AI, Feature, Policy, Safety, Capital Allocation, Execution assumptions, market regime, data defect, Runtime defect, or unknown.

Phase17-E: Design improvements outside Runtime Core unless Runtime bug evidence exists.

Phase17-F: Revalidate improved version for 1 year with separate version/run/manifest.

Phase17-G: Run full 2021-07 to latest historical test.

Phase17 Final: Final performance review and next-phase readiness review.

## Known Limitations And Prerequisites

Required before Phase17-A:

- Formal normal Runtime Backup / Reset / Restore CLI or accepted operational procedure.
- Cross-state reset validation.
- Historical Simulated Broker adapter contract and schema mapping.
- Historical Clock audit for all Phase16 jobs.
- Public report / notification payload optionality decision.
- Accepted model artifact manifest freeze.
- Historical period readiness audit.

## Phase17-M Amendment: As-of Consumer Wiring

Historical as-of resolution is not sufficient as evidence-only output. Historical Market Refresh, Data Readiness, Feature Refresh, and Feature Artifact resolution must consume an accepted logical as-of input for the replay business date.

Allowed implementation forms include a run-scoped verified derived logical input, a data resolver with an explicit `as_of` cutoff, or a formally materialized PIT view. In every case, the logical input must retain physical source path/hash, cutoff, logical max date, future rows excluded count, run identity, and manifest hash. The physical canonical source must not be truncated, deleted, copied back, or overwritten.

Feature artifacts are temporally valid only when the artifact date is not later than the selected Feature Date and not later than the consumer business date. A future artifact existing in the repository is not a failure by itself; using it as consumer input for an earlier historical business date is a temporal contract violation.

Historical Runtime Test run entry requires all target business dates to have `PASS` Feature Date Contracts from the normal contract authority. Profile expected dates are comparison values only and must never act as Feature Date authority.
