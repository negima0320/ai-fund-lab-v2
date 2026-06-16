# Phase9 Daily Paper Trading Design

## 1. Objective

Phase9 validates daily paper trading operation without broker order APIs.

The system should run every business day, produce OrderPlans, update an internal Paper Ledger, and generate reports that humans can review.

Phase9 is not a live trading phase.

## 2. Boundary

Allowed:

```text
internal Paper Ledger virtual trades
historical / same-day market data based virtual fills
REAL read-only Broker Snapshot reference
Broker snapshot reconciliation
Human Review
Safety Report
moomoo SIMULATE support investigation
Tachibana adapter re-evaluation as design-only work
```

Prohibited:

```text
live order
auto order
REAL order
Broker API order submit / cancel / modify
unlock_trade
trade unlock
OpenD automatic startup
automatic login/logout
secret persistence
raw moomoo response persistence
plain account id persistence
```

## 3. Existing Phase8 Components Reused

Phase9 reuses:

```text
Broker snapshot loader
Paper Ledger
Reconciliation
Safety Reconciliation
OrderPlan schema
Order Plan Generator
dependency validator
OrderPlan store and history reader
approval record
Human Review report writer
Paper ledger dry-run update
dry-run orchestrator
review queue
paper ledger diff
safety report links
```

Phase9 should add daily operation and performance layers around these components.

## 4. Runtime Paths

Recommended paths:

```text
.runtime/order_manager/paper/ledgers/
.runtime/order_manager/plans/
.runtime/order_manager/review/
.runtime/order_manager/audit/
.runtime/phase9/daily_runs/
.runtime/phase9/reports/
.runtime/phase9/performance/
reports/phase_reports/
reports/phase9/daily/
```

Broker snapshots remain under:

```text
.runtime/broker/snapshots/
.runtime/broker/sync_results/
```

Paper Ledger and Broker snapshots must not be mixed.

## 5. Daily Run Manifest

Each daily run should write a manifest.

Required fields:

```text
run_id
run_date
business_date
created_at
schema_version
source = phase9_daily_paper_trading
mode = paper_only
market_data_status
candidate_ai_status
opportunity_ai_status
position_ai_status
capital_allocation_status
order_manager_status
paper_ledger_status
human_review_status
safety_status
performance_status
external_broker_order_api_called = false
```

The manifest should link:

```text
market data artifact
AI artifacts
Capital Allocation artifact
OrderPlan
Paper Ledger before / after
Human Review report
Safety report
Daily Summary report
Performance metrics JSON
```

## 6. Daily Pipeline

Daily pipeline:

```text
1. Resolve business date
2. Validate market data availability
3. Run Candidate AI
4. Run Opportunity AI
5. Run Position Management AI
6. Run Capital Allocation
7. Load latest Paper Ledger
8. Load latest normalized Broker Snapshot if available
9. Run reconciliation
10. Read Safety lock state
11. Generate OrderPlan
12. Store OrderPlan
13. Generate Human Review report
14. Apply paper-only virtual execution
15. Write new Paper Ledger
16. Calculate performance metrics
17. Generate Safety report
18. Generate Daily Summary report
19. Update 30 business day tracker
```

Default failure policy:

```text
fail closed
write diagnostic report
do not mutate Paper Ledger unless inputs and plan are valid
do not call broker order APIs
```

## 7. Paper Ledger Model

Current Phase8 model:

```text
cash
buying_power
positions
pending_orders
executions
as_of
ledger_id
schema_version
source = paper
```

Phase9 additions should be additive:

```text
daily_mark_to_market
realized_pnl
unrealized_pnl
trade_cost
slippage
run_id
business_date
valuation_source
```

If model expansion is risky, keep Phase8 schema stable and store Phase9 metrics in a separate performance record.

## 8. Virtual Fill Policy

Phase9 must define a deterministic virtual fill policy before using daily paper results.

Initial conservative policy:

```text
BUY uses next available close or next open, depending on available data
SELL uses next available close or next open with the same convention
100-share unit enforced
cash buffer enforced
max position weight enforced
T+2 conservative cash unavailable enforced
SELL_FIRST_BUY_AFTER_FILL enforced
blocked BUY remains unfilled
missing price means no fill and warning
```

The fill policy must be printed in every daily report.

## 9. Report Design

Daily markdown report sections:

```text
Run Summary
Safety Status
Market Data Status
AI Recommendations
OrderPlan
BUY Candidates
SELL Candidates
HOLD Candidates
Dependency / Blocked Items
Paper Fill Simulation
Paper Portfolio
PnL and Performance
Human Review Checklist
Tomorrow Checklist
```

Daily JSON report should mirror the markdown with stable IDs.

Human-friendly requirements:

```text
show symbol and issue name where available
explain why BUY / SELL / HOLD was proposed
show cash and position effect
show warnings plainly
make review-required items explicit
never imply real execution occurred
```

## 10. Performance Tracking

Daily metrics:

```text
paper_total_equity
paper_cash
paper_buying_power
gross_exposure
position_count
realized_pnl
unrealized_pnl
daily_return
cumulative_return
win_rate
average_win
average_loss
profit_factor
max_drawdown
trade_count
turnover
average_holding_days
blocked_buy_count
review_only_count
safety_warning_count
```

Aggregate windows:

```text
1 business day
5 business days
10 business days
20 business days
30 business days
```

## 11. Human Review

Every daily run requires Human Review.

Review decisions:

```text
approved
rejected
needs_change
```

Approval still means:

```text
approval_does_not_allow_live_order = true
```

Human Review should check:

```text
AI recommendation plausibility
SELL_FIRST_BUY_AFTER_FILL dependencies
paper fill assumptions
cash and exposure constraints
safety warnings
unexpected turnover
large drawdown
missing data warnings
```

## 12. Safety Report

Safety Report should include:

```text
lock state
reconciliation status
broker snapshot availability
paper ledger integrity
daily run warnings
review-only status
halt candidates
no-live-order confirmation
```

Locked behavior:

```text
no normal OrderPlan
review-only diagnostic report
no Paper Ledger mutation unless explicitly safe and diagnostic-only
```

## 13. 30 Business Day Validation

Plan:

```text
Days 1-5: setup and report calibration
Days 6-15: daily operational stability
Days 16-25: performance and safety pattern review
Days 26-30: final validation and next-phase readiness decision
```

Completion criteria:

```text
all 30 runs have manifests
Paper Ledger remains internally consistent
daily reports are usable by a human reviewer
Safety warnings are explainable
OrderPlans remain non-executable
no broker order API path is introduced
performance metrics are reproducible
```

## 14. Phase9-A Scope

Implement first:

```text
initial Paper Ledger creation CLI
daily run manifest schema
daily pipeline runner skeleton
Paper Ledger daily snapshot writer
virtual fill policy stub
daily report writer markdown/json
performance metrics schema
30 business day tracker
Phase9 audit script
pytest coverage for default no-external-connection behavior
```

Do not implement:

```text
broker order APIs
OpenD startup
trade unlock
automatic login/logout
live order path
```

## 15. Broker API Test Readiness

Broker API connection tests may be considered only after:

```text
30 business day validation completes
Phase9 audit passes
Human Review process is accepted
Safety Report process is accepted
Paper Ledger accounting is stable
SIMULATE availability is resolved or alternative broker strategy is approved
explicit user approval is given for a new phase
new broker test design is written
new no-live-order audit is written
```

Broker API tests must begin as a separate phase and must not imply automatic live trading.
