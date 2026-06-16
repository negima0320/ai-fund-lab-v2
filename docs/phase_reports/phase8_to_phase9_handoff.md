# Phase8 to Phase9 Handoff

## 1. Purpose

This document hands off AI Fund Lab vNext from Phase8 Order Manager to Phase9 Daily Paper Trading Validation.

Phase9 does not perform broker API order tests.

Phase9 starts daily operation validation with AI Fund Lab's internal Paper Ledger while continuing to use moomoo REAL read-only Broker Snapshot only as a reference and reconciliation input.

## 2. Inputs Reviewed

Documents:

```text
docs/phase_reports/phase8h_completion_audit.md
reports/phase_reports/phase8h_completion_audit.json
docs/phase_reports/phase8g_order_manager_end_to_end_dry_run.md
docs/phase_reports/phase8f_order_manager_dry_run_workflow.md
docs/phase_reports/phase8e_order_plan_generator.md
docs/phase_reports/phase8d_order_manager_reconciliation.md
docs/phase_reports/phase8c7_moomoo_simulate_account_investigation.md
docs/phase_reports/phase8c_moomoo_readonly_smoke.md
docs/phase_reports/phase7_final_summary_and_phase8_handoff.md
docs/01_requirements/phase_roadmap.md
```

Source areas:

```text
src/ai_fund_lab_v2/order_manager/
src/ai_fund_lab_v2/broker/
src/ai_fund_lab_v2/safety/
```

## 3. Phase8 Completion Judgment

Final Phase8-H judgment:

```text
Phase8 Order Manager: PASS
moomoo REAL read-only Broker Sync: PASS
moomoo SIMULATE Broker Sync: NOT_READY
no-live-order safety: PASS
Phase8 Overall: COMPLETE_WITH_SIMULATE_PENDING
```

Phase8-H did not run any external connection or live broker operation.

## 4. What Phase8 Built

Phase8 completed:

```text
moomoo Broker Integration Design
read-only snapshot schema
moomoo mock fixture and normalizer
REAL read-only Broker Sync
Broker snapshot loader
Paper Ledger
Broker snapshot vs Paper Ledger reconciliation
Safety lock integration
OrderPlan / OrderPlanItem schema
Order Plan Generator
SELL_FIRST_BUY_AFTER_FILL dependency
Human Review report
Approval record
Paper ledger dry-run update
OrderPlan persistence and history
Review queue
End-to-end dry-run orchestration
no-live-order audits
```

Phase8 safety invariants:

```text
OrderPlan.executable = false
OrderPlan.live_order_allowed = false
OrderPlan.requires_human_review = true
Approval does not allow live order
Broker snapshot and Paper Ledger are stored separately
locked state allows review-only diagnostics only
reconciliation halt prevents normal plan generation
```

## 5. Phase8 Remaining Issues

moomoo SIMULATE Broker Sync remains unresolved.

Known facts:

```text
SDK exposes TrdEnv.SIMULATE
get_acc_list under SIMULATE smoke succeeds but returns only trd_env=REAL
selected_candidate_count = 0
AI Fund Lab correctly fails closed with NO_MATCHING_ACCOUNT
Official OpenAPI table marks JP stocks / ETFs / REITs Paper Trading as X
moomoo support confirmation is still needed
```

Tachibana remains a fallback option if moomoo constraints block the long-term workflow.

## 6. Phase9 Goal

Phase9 goal:

```text
Validate daily AI-driven paper trading operation without broker order APIs.
```

Phase9 should answer:

```text
Can the system run every business day?
Can AI recommendations produce reviewable OrderPlans?
Can the Paper Ledger simulate buy/sell/hold outcomes clearly?
Can humans understand daily decisions, risk, and performance?
Can Safety reports detect halt/review conditions before any live order path exists?
```

## 7. Phase9 Prohibited Scope

Phase9 prohibits:

```text
live order
auto order
REAL order
Broker API order submit
Broker API order cancel
Broker API order modify
unlock_trade
trade unlock
OpenD automatic startup
automatic login/logout
secret persistence
raw moomoo response persistence
plain account id persistence
```

Phase9 permits:

```text
internal Paper Ledger virtual trades
virtual fills from historical or same-day market data
REAL read-only Broker Snapshot reference
Broker snapshot reconciliation
Human Review
Safety Report
moomoo SIMULATE investigation
Tachibana re-evaluation
```

## 8. Daily Operation Flow

Every business day, Phase9 should run:

```text
1. Update market data
2. Run Candidate AI
3. Run Opportunity AI
4. Run Position Management AI
5. Run Capital Allocation
6. Run Order Manager dry-run orchestration
7. Store OrderPlan
8. Update Paper Ledger
9. Apply buy-if-executed / sell-if-executed virtual fills
10. Generate Human Review report
11. Generate Safety report
12. Generate Daily Summary report
13. Update performance metrics
```

Failure handling:

```text
missing market data -> fail closed
missing Phase7/AI artifact -> INVALID_INPUT
broken Paper Ledger -> fail closed
reconciliation halt -> review-only report
safety locked -> REVIEW_ONLY_LOCKED report
unknown fill price -> skip fill and warn
```

## 9. AI Execution Flow

Phase9 should preserve the Phase7 policy relationship:

```text
Candidate AI -> Opportunity AI -> Position Management AI -> Capital Allocation -> Order Manager
```

Primary policy:

```text
CAP5
```

Shadow policies:

```text
CAP4
POLICY_Y_CAP4_EDGE08_CONF5
```

Execution constraints:

```text
100-share unit
cash buffer 5%
max position weight 20%
T+2 conservative cash unavailable
SELL_FIRST_BUY_AFTER_FILL
```

## 10. Paper Ledger Operation

Phase9 Paper Ledger is the source of virtual trading state.

It must remain separate from Broker snapshots.

State:

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

Phase9 should add daily ledger runs:

```text
initial ledger creation
daily ledger snapshot
virtual execution record
daily mark-to-market
realized PnL
unrealized PnL
ledger diff
performance summary
```

Virtual fill policy should be explicit:

```text
BUY fill price source
SELL fill price source
slippage assumption
commission assumption
partial fill policy
cash availability policy
failed fill policy
```

Default Phase9 recommendation:

```text
Use conservative close-price or next-open approximation until a more precise fill model is designed.
Never call Broker order APIs.
```

## 11. Daily Report Specification

Daily human-readable report should include:

```text
run date
market data status
safety status
broker snapshot reference status
paper ledger id
OrderPlan id
Human Review status
today's AI recommended symbols
BUY candidates
SELL candidates
HOLD candidates
decision rationale
SELL_FIRST_BUY_AFTER_FILL dependencies
blocked / waiting items
buy-if-executed outcome
sell-if-executed outcome
paper cash
paper buying power
paper holdings
unrealized PnL
realized PnL
win rate
average win
average loss
max drawdown
trade count
holding days
turnover
Safety warnings
Human Review required items
tomorrow checklist
```

Machine-readable companion JSON should include the same identifiers and metrics.

## 12. Performance Metrics

Track daily:

```text
paper total equity
cash
buying power
gross exposure
position count
realized PnL
unrealized PnL
daily return
cumulative return
win rate
average profit
average loss
profit factor
max drawdown
trade count
turnover
average holding days
sell-first dependency count
blocked buy count
review-only count
safety warning count
```

Compare:

```text
CAP5 primary vs CAP4 shadow
CAP5 primary vs POLICY_Y_CAP4_EDGE08_CONF5 shadow
paper results vs Phase7 expectations
paper ledger vs REAL read-only Broker Snapshot exposure
```

## 13. 30 Business Day Validation Plan

Days 1-5:

```text
Create initial Paper Ledger
Run daily pipeline manually
Validate report readability
Validate ledger diff and performance calculations
Tune failure handling
```

Days 6-15:

```text
Run daily operation with consistent cut-off time
Review BUY/SELL/HOLD rationale
Track blocked and waiting orders
Validate SELL_FIRST_BUY_AFTER_FILL behavior
Compare primary and shadow policies
```

Days 16-25:

```text
Stabilize daily review process
Measure turnover, holding period, and drawdown
Review Safety warnings and reconciliation results
Identify repeated false positives or unclear reports
```

Days 26-30:

```text
Summarize performance
Compare against Phase7 assumptions
Decide whether Phase10/11 prerequisites are satisfied
Decide whether broker API connection tests can be considered
```

Exit criteria:

```text
30 business days completed
no unreviewed safety-critical failure
daily reports are understandable
paper ledger state remains internally consistent
order plans remain non-executable
human review process is practical
broker API order path is still absent
```

## 14. What Can Be Validated Without Broker Order APIs

Can validate:

```text
daily AI orchestration reliability
candidate / opportunity / position / capital allocation flow
OrderPlan quality
paper cash and position accounting
virtual PnL
turnover
holding period
win/loss behavior
human review usability
safety report usability
reconciliation reporting against REAL read-only snapshots
SELL_FIRST_BUY_AFTER_FILL logic
blocked/waiting behavior
```

Cannot validate:

```text
real order acceptance
real cancel / modify behavior
real execution latency
real partial fills
real rejection codes
real buying-power timing
broker-side settlement details
trade unlock process
production order routing
```

## 15. moomoo / Tachibana Handling

moomoo:

```text
Use REAL read-only Broker Sync only as reference.
Do not use moomoo order APIs in Phase9.
Keep SIMULATE support inquiry open.
If support confirms JP SIMULATE is unavailable, keep JP validation on internal Paper Ledger.
Optionally investigate non-JP SIMULATE as a separate read-only task.
```

Tachibana:

```text
Do not reintroduce Tachibana CLMID/API names into common Order Manager interfaces.
Re-evaluate Tachibana only if moomoo cannot support the eventual required broker workflow.
Treat Tachibana as a separate broker adapter decision, not a Phase9 dependency.
```

## 16. Conditions to Proceed to Broker API Connection Tests

Do not proceed to broker API order testing until all are true:

```text
30 business day Paper Trading validation completed
Paper Ledger and daily reports are stable
Safety reports are reviewed and operational
Human Review process is practical
OrderPlan safety flags remain fixed
Reconciliation behavior is understood
moomoo SIMULATE support is resolved or an approved broker test path is selected
explicit user approval exists for a new phase
new design document exists for broker API connection tests
new audit denies live order by default
secret handling and account-id masking are re-reviewed
```

Even then, first broker tests must be separately scoped and should not imply automatic live trading.

## 17. Phase9-A First Implementation Items

Phase9-A should implement:

```text
Phase9 Daily Paper Trading design finalization
initial Paper Ledger creation CLI
daily run manifest schema
daily AI pipeline runner skeleton
daily Paper Ledger snapshot writer
daily report writer markdown/json
performance metrics schema
30 business day validation tracker
Phase9 audit script
tests for no broker order API and no external connection by default
```

Recommended first command shape:

```text
scripts/run_phase9a_daily_paper_trading.py --date YYYY-MM-DD --dry-run
```

Default behavior:

```text
no broker API order call
no OpenD startup
no login/logout
no live order
fail closed on missing inputs
produce reviewable reports
```
