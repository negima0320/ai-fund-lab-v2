# Phase25-AA Baseline Metrics, Benchmark and Capital Efficiency Investigation

## 1. Executive Summary

Phase25-AA is complete as an investigation. No Production, Runtime, Strategy, schema, CLI, or benchmark-fetcher code was changed.

The repo already has strong Performance Evaluation contracts and useful run-scoped observability for executions, realized slices, position campaigns, lifecycle consistency, PM decisions, Strategy artifacts, and benchmark placeholder snapshots. However, Phase25-A cannot yet treat the current evaluation foundation as complete. The biggest gaps are:

- benchmark-relative evaluation is blocked because TOPIX/Nikkei/JPX approved PIT-safe sources are not present;
- official daily equity/cash/exposure series are not fully materialized as canonical metrics for the inspected 2024 10BD run;
- compound reinvestment is plausible but not confirmed, because `runtime_evaluation_capital` remains fixed at 1,000,000 while Position Sizing uses `portfolio_total_equity`;
- the 2024 final Cash Ratio can be measured, but its cause cannot be fully decomposed without a dedicated capital efficiency artifact.

Phase25-A should proceed, but only as contract/design/materialization work, not Strategy improvement.

## 2. Primary Judgment

`PHASE25_AA_BASELINE_INVESTIGATION_COMPLETE_EVIDENCE_REQUIRED`

Phase25-A Entry:

`READY_WITH_GATES`

Gate results:

| Gate | Result |
|---|---|
| Metrics | `DESIGN_REQUIRED` |
| Benchmark | `DESIGN_REQUIRED` |
| Capital Authority | `EVIDENCE_REQUIRED` |
| Compound Reinvestment | `EVIDENCE_REQUIRED` |
| Cash Ratio Observability | `EVIDENCE_REQUIRED` |
| Attribution | `PASS_WITH_NON_BLOCKING_GAPS` |
| Experiment Contract | `PASS_WITH_NON_BLOCKING_GAPS` |

## 3. Scope and Method

The investigation followed the requested order:

1. Mandatory reading.
2. Architecture and contract review.
3. Schema, artifact, and CLI inventory.
4. Producer and consumer tracing.
5. Capital authority chain tracing.
6. Existing test and implementation review.
7. Runtime evidence comparison against the 2024 10BD run.
8. Gap classification.
9. Phase25-A entry gate decision.

Short validation performed:

```text
PYTHONPATH=src python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-extended-smoke-20260802T113114833349Z --scope performance --json
```

Result: exit code 0 in about 2.8 seconds. This was read-only and inspected existing run evidence.

## 4. Documents Reviewed

Mandatory handoff:

- `docs/phase_reports/phase24_to_phase25_chatgpt_handoff.md`
- `docs/phase_reports/phase24_final_summary_and_phase25_handoff.md`
- `docs/phase_reports/phase24_in_phase21_to_phase24_cross_phase_review.md`
- `docs/phase_reports/phase24_in_phase24_runtime_test_findings_and_remaining_gaps.md`
- `docs/phase_reports/phase24_in_phase25_performance_evaluation_and_improvement_plan.md`

Architecture and roadmap:

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/01_requirements/phase_roadmap.md`

Additional contracts:

- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase24_a_performance_evaluation_contract.md`
- `docs/01_requirements/strategy_experiment_contract.md`
- `docs/03_operations/runtime_test_command_guide.md`

## 5. Metrics Inventory

| Metric | Current Status | Definition / Formula | Source Data | Producer / Authority | Materialization | PIT Safety | Known Gap |
|---|---|---|---|---|---|---|---|
| Total Return | `PARTIAL` | `final_equity - initial_equity` | final Current, fresh summary | Runtime Test summarizer / final Current | `final_summary.json`, final state, `summarize --scope performance` | `SAFE` | Final-period only unless daily equity curve is canonicalized. |
| CAGR | `NOT_IMPLEMENTED` | Contract defines CAGR-style compounding | daily equity curve | Contract only | none found for Runtime Test summary | `UNKNOWN` | Needs >=252BD official horizon and daily equity. |
| Annualized Return | `PARTIAL` | `(final/initial) ** (252 / completed_bd) - 1` | equity and completed BD | Contract / some legacy scripts | not emitted for inspected 2024 summary | `UNKNOWN` | Needs official short-period warning and metric record. |
| Max Drawdown | `PARTIAL` | min running peak drawdown | daily equity curve | Contract / summarize fallback | `NOT_AVAILABLE` for inspected run | `SAFE` if daily equity exists | Daily equity artifact not canonical for inspected run. |
| Volatility | `NOT_IMPLEMENTED` | std daily returns, annualized | daily returns | Contract only | none found | `SAFE` if EOD returns | Needs daily return series. |
| Sharpe Ratio | `NOT_IMPLEMENTED` | mean excess daily return / std * sqrt(252) | daily returns, cash diagnostic baseline | Contract only | none found | `UNKNOWN` | Needs risk-free/cash baseline rule. |
| Sortino Ratio | `NOT_IMPLEMENTED` | mean excess return / downside std * sqrt(252) | daily returns | Contract only | none found | `UNKNOWN` | Needs downside sample policy. |
| Calmar Ratio | `NOT_IMPLEMENTED` | annualized return or CAGR / abs(MDD) | annualized return, MDD | not found as Runtime metric | none found | `UNKNOWN` | Needs formula and metric record. |
| Profit Factor | `PARTIAL` | gross wins / abs(gross losses) | realized slices | Contract / realized slice evidence | derivable, not summarized | `SAFE` | Approximate without stable lot IDs. |
| Win Rate | `PARTIAL` | winning realized slices / realized slices | realized slices | Contract / realized slice evidence | derivable, not summarized | `SAFE` | Approximate without stable lot IDs. |
| Average Win | `PARTIAL` | avg positive realized slice PnL | realized slices | realized slice evidence | derivable | `SAFE` | Not official summary metric. |
| Average Loss | `PARTIAL` | avg negative realized slice PnL | realized slices | realized slice evidence | derivable | `SAFE` | Not official summary metric. |
| Payoff Ratio | `PARTIAL` | avg win / abs(avg loss) | realized slices | Contract / realized slice evidence | derivable | `SAFE` | Approximate without stable lot IDs. |
| Holding Period | `PARTIAL` | campaign/lifecycle business-day duration | executions, campaigns | position campaign observability | `position_campaigns.json`, lifecycle scope | `SAFE` | Exact lot holding period missing. |
| Turnover | `PARTIAL` | abs executed notional / average equity | fills and equity | Contract / summarize | execution notional emitted; turnover `NOT_AVAILABLE` | `SAFE` | Needs average daily equity. |
| Trade Count | `IMPLEMENTED` | canonical execution count | fills/executions | run-scoped execution evidence | `summarize.trading.execution_count` | `SAFE` | Keep order/fill/action separation explicit. |
| Monthly Return | `NOT_IMPLEMENTED` | month end / start equity - 1 | daily equity | legacy capital_allocation backtests only | not Runtime authority | `UNSAFE` for Phase25 | Needs Runtime EOD aggregation. |
| Quarterly Return | `NOT_IMPLEMENTED` | quarter end / start equity - 1 | daily equity | none found | none | `UNKNOWN` | Needs Runtime EOD aggregation. |
| Exposure-adjusted Return | `NOT_IMPLEMENTED` | not fixed | return and exposure series | none found | none | `UNKNOWN` | Needs formula and daily exposure. |
| Cash-adjusted Return | `NOT_IMPLEMENTED` | not fixed | return and cash series | none found | none | `UNKNOWN` | Needs formula and daily cash. |
| Attribution | `PARTIAL` | post-hoc component attribution | campaigns, fills, PM, Strategy artifacts | summarize, run artifacts | lifecycle/positions/strategy scopes | `SAFE` for decision-time joins | Benchmark, sector, cash drag, and exact-lot attribution incomplete. |

## 6. Evaluation and Reporting Surface

Primary Runtime Test surface:

- `scripts/runtime_test.py summarize`
- scopes: `overview`, `performance`, `positions`, `lifecycle`, `strategy`, and related strategy aliases.
- `docs/03_operations/runtime_test_command_guide.md` documents that summarize is read-only and writes evidence only under `reports/runtime_tests/summaries/<summary_id>/` when requested.

Other status surfaces:

- `run-status` / `status`: runner and current Runtime Test state.
- `system-status`: whole-system readiness and scoped health.
- `ai-status`: AI artifact / accepted generation authority.

Performance-related non-authoritative surfaces:

- Paper Trading reports and ledgers under `src/ai_fund_lab_v2/paper_trading/`.
- Legacy or experimental capital allocation backtests under `src/ai_fund_lab_v2/capital_allocation_ai/`.

Conflict / duplication finding:

- Runtime Test performance uses final Current, run-scoped fills, realized slices, and position campaigns.
- Paper Trading and capital allocation backtest metrics compute similar names such as annualized return, win rate, profit factor, monthly return, and drawdown, but they are not Phase25 Runtime Test authority.
- Phase25-A must explicitly prevent these legacy/backtest metrics from becoming official baseline authority unless re-bound through the Phase25 contract.

## 7. Benchmark Inventory and PIT-Safe Assessment

| Benchmark | Existing Source | Data Provider | Date Binding | Constituents | Corporate Action Adjustment | Return Type | PIT Safety | Runtime Dependency | Suitability |
|---|---|---|---|---|---|---|---|---|---|
| TOPIX | Placeholder snapshots only | `NOT_CONFIRMED` | `business_date` in snapshot | Missing | Unknown | Unknown | `UNKNOWN` | none, read-only | `NOT_READY` |
| Nikkei 225 | none found | `NOT_CONFIRMED` | none | Missing | Unknown | Unknown | `UNKNOWN` | none | `NOT_READY` |
| JPX-related index | none found | `NOT_CONFIRMED` | none | Missing | Unknown | Unknown | `UNKNOWN` | none | `NOT_READY` |
| Equal-weight market proxy | Market Context / Phase22-L design | J-Quants listed/common universe quote proxy | business-date/as-of artifacts | repository universe proxy | source-dependent | price proxy | `SAFE` when generated by Market Context | Strategy context, not benchmark authority | `REFERENCE` |
| Sector benchmark | Phase22-L sector proxy design | J-Quants listed info and quotes | business-date/as-of artifacts | sector membership where covered | source-dependent | equal-weight sector proxy | `SAFE` when coverage valid | Strategy context/attribution | `REFERENCE` |

The inspected 2024 run has daily `benchmark_snapshot.json` artifacts, but they all state:

```text
status = MISSING
benchmark_source = NOT_CONFIRMED
benchmark_implementation = NOT_PERFORMED
```

Therefore benchmark-relative metrics are blocked until Phase25-A selects and binds an approved PIT-safe source.

## 8. Capital Authority Chain

Observed chain:

```text
Historical isolated state / Broker read-only evidence
  -> persistent_ledger/state.json
  -> cash, buying_power, market_value, total_equity
  -> runtime_evaluation_capital retained in Current
  -> Portfolio Policy / Portfolio Construction
  -> Position Sizing
  -> Runtime Planning
  -> Strategy Planning Authority / Pending
  -> Submit Guard
```

Key implementation observations:

- `runtime_owned_fill_projection.py` computes projected cash from `before.runtime_evaluation_capital or before.cash`, then applies runtime-owned execution cash effects.
- `position_sizing.py` requires `portfolio_total_equity` and writes it into `strategy/position_sizing.json`.
- `dynamic_cash_exposure.py` computes `portfolio_total_equity = current_cash + current_market_value`.
- `configs/runtime_v2/capital_deployment.json` still includes `evaluation_capital=1000000` and `max_exposure=850000`.
- `src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py` validates `max_exposure <= evaluation_capital`, preserving a fixed-capital-style policy surface.

For the inspected final state:

```text
runtime_evaluation_capital = 1000000.0
cash = 388010.0
market_value = 679650.0
total_equity = 1067660.0
buying_power = 388010.0
```

## 9. Compound Reinvestment Judgment

`COMPOUND_REINVESTMENT_AMBIGUOUS`

Evidence for partial support:

- Position Sizing on 2024-01-18 uses `portfolio_total_equity=1067660.0`, not 1,000,000.
- Dynamic cash/exposure and policy artifacts express ratios against portfolio equity.

Evidence preventing confirmation:

- `runtime_evaluation_capital` remains fixed at 1,000,000 in final Current.
- Runtime-owned cash projection explicitly names `runtime_evaluation_capital_plus_runtime_owned_execution_cash_effect`.
- Capital deployment runtime policy still has fixed `evaluation_capital=1000000` and `max_exposure=850000`.
- A clean trace is needed showing realized or unrealized profit changing later BUY target notional, feasible quantity, and submitted order sizing.

Required Phase25-A evidence:

- daily table of `runtime_evaluation_capital`, `cash`, `buying_power`, `market_value`, `total_equity`, `target_weight`, `target_notional`, `target_quantity_candidate`, `planned_quantity`, and submitted quantity;
- at least one post-profit BUY or ADD decision where sizing can be compared against both initial capital and current equity.

## 10. Capital Efficiency Inventory

| Item | Status | Authority / Materialization | Gap |
|---|---|---|---|
| runtime_evaluation_capital | `AVAILABLE` | Current state | Definition ambiguous: initial capital vs active sizing base. |
| Buying Power | `AVAILABLE` | Current state / asset projection | Unsettled cash not separately represented in inspected state. |
| Cash | `AVAILABLE` | Current state | Idle/reserved/buffer decomposition missing. |
| Market Value | `AVAILABLE` | Current valuation | Needs complete daily valuation for official metrics. |
| Total Equity | `AVAILABLE` | Current state | Daily equity curve not canonical metric for inspected run. |
| Cash Ratio | `DERIVABLE` | `cash / total_equity` | Not official summary metric for inspected run. |
| Exposure Ratio | `DERIVABLE` | `market_value / total_equity` | Not official summary metric for inspected run. |
| Position Count | `AVAILABLE` | Current positions | Needs average/max daily aggregation. |
| Idle Cash | `PARTIAL` | cash minus explicit reserves where available | No canonical decomposition. |
| Reserved Cash | `PARTIAL` | pending/dynamic cash artifacts | Not consistently aggregated. |
| Deployable Cash | `PARTIAL` | dynamic cash exposure `net_available_cash` | Not official summary metric. |
| Target Exposure | `AVAILABLE` | Portfolio Policy / Position Sizing | Eligibility/DRAFT status must be tracked. |
| Actual Exposure | `DERIVABLE` | Current valuation | Needs daily materialization. |
| Unused Exposure Capacity | `DERIVABLE_PARTIAL` | target exposure - actual exposure | Cause decomposition missing. |
| Compound Reinvestment | `AMBIGUOUS` | requires cross-day trace | Not established. |

Phase25-A must distinguish:

- normal cash buffer;
- safety-reserved cash;
- pending-reserved cash;
- opportunity shortage;
- position-count constraint;
- sizing/lot/min-notional residual;
- no-order/no-action Strategy intent;
- true idle cash.

## 11. 2024 10BD Cash Ratio Investigation Readiness

Target result:

```text
Period: 2024-01-04 to 2024-01-18
Business Days: 10
Final Equity: 1067660
Cash: 388010
Cash Ratio: 36.3421%
Exposure Ratio: 63.6579%
Current Positions: 4
```

Observed final-day evidence:

- `portfolio_policy.cash_reserve_ratio = 0.21`
- `position_sizing.target_gross_exposure_ratio = 0.79`
- `position_sizing.portfolio_total_equity = 1067660.0`
- actual exposure = `679650 / 1067660 = 0.636579`
- actual cash = `388010 / 1067660 = 0.363421`

Readiness by cause:

| Cause Candidate | Readiness |
|---|---|
| Market Context | `POSSIBLE_CAUSE` |
| Portfolio Policy | `POSSIBLE_CAUSE` |
| Target Exposure | `CONFIRMED_NOT_CAUSE_FOR_FULL_36_PERCENT_CASH` |
| Candidate不足 | `EVIDENCE_REQUIRED` |
| Opportunity不足 | `POSSIBLE_CAUSE` |
| Eligibility脱落 | `EVIDENCE_REQUIRED` |
| Position Count | `POSSIBLE_CAUSE` |
| Position Sizing | `POSSIBLE_CAUSE` |
| Lot Size | `POSSIBLE_CAUSE` |
| Price Constraint | `EVIDENCE_REQUIRED` |
| Capital Deployment | `POSSIBLE_CAUSE` |
| Safety Constraint | `CONFIRMED_NOT_CAUSE_ON_FINAL_DAY` |
| Pending Reservation | `CONFIRMED_NOT_CAUSE_ON_FINAL_DAY` |
| ADD不成立 | `POSSIBLE_CAUSE` |
| Idle Cash | `POSSIBLE_CAUSE` |
| Normal Cash Buffer | `CONFIRMED_CAUSE_PARTIAL_21_PERCENT` |

Important: the final Cash Ratio cannot be fully attributed from final state alone. Phase25-A needs a daily capital efficiency artifact that joins policy target, actual exposure, no-order reason, pending reservation, target notional, target quantity, planned quantity, and fills.

## 12. Attribution Capability Inventory

| Dimension | Current Status | Required Source | Join Key | PIT Safety | Missing Field | Risk |
|---|---|---|---|---|---|---|
| Trade-level | `PARTIAL` | realized slices / trade attribution | symbol, execution_id, date | `SAFE` | stable lot id, fees/tax | Approximate slice unit. |
| Order-level | `IMPLEMENTED` | submitted orders | order_id, pending_item_id | `SAFE` | none for counts | Raw vs canonical confusion. |
| Fill-level | `IMPLEMENTED` | execution equivalent | dedup_key, execution_id | `SAFE` | fees/tax/slippage | Broker detail duplication. |
| Position-level | `PARTIAL` | Current positions | symbol | `SAFE` | lifecycle id in current | Open PnL mixing. |
| Campaign-level | `IMPLEMENTED` | position campaigns | campaign_id | `SAFE` | lot id | Campaign is not tax-lot. |
| Symbol-level | `DERIVABLE` | campaigns/current/slices | symbol | `SAFE` | benchmark/sector | Double counting risk. |
| Day-level | `PARTIAL` | daily current valuation | business_date | `SAFE` | canonical daily metric artifact | Missing valuation interpolation risk. |
| Month-level | `NOT_OBSERVABLE` | daily equity | month | `UNKNOWN` | aggregation | Legacy backtest confusion. |
| Quarter-level | `NOT_OBSERVABLE` | daily equity | quarter | `UNKNOWN` | aggregation | Legacy backtest confusion. |
| Market Regime-level | `PARTIAL` | market_context.json | business_date | `SAFE` | return aggregation | Post-hoc leakage risk if reused. |
| Sector-level | `PARTIAL` | sector/source manifest | symbol/date | `SAFE` when coverage valid | sector PnL aggregation | Unknown coverage. |
| Candidate Source-level | `PARTIAL` | candidate decisions | candidate_ref/date | `SAFE` | full universe exclusions | TopN bias. |
| Ranking-level | `PARTIAL` | opportunity rankings | opportunity_row_id | `SAFE` | complete not-bought reason rollup | Ranking top != BUY. |
| Sizing-level | `PARTIAL` | position_sizing.json | symbol/date | `SAFE` | capacity decomposition | Target vs fill confusion. |
| ADD / REDUCE / EXIT-level | `PARTIAL` | PM, sell planning, executions | pm_decision_id | `SAFE` | exact ADD lot | Counterfactual misuse. |
| Cash Drag | `PARTIAL` | cash/equity/target exposure | date | `SAFE` | cause decomposition | All cash mislabeled idle. |
| Exposure Drag | `PARTIAL` | target and actual exposure | date | `SAFE` | target-vs-actual series | DRAFT eligibility ambiguity. |
| Benchmark-relative | `NOT_OBSERVABLE` | approved benchmark | date | `UNKNOWN` | benchmark source | False relative conclusion. |

## 13. Experiment Contract Inventory

Reusable from existing contracts:

- hypothesis;
- single change;
- baseline and variant;
- changed component;
- unchanged contracts;
- run windows;
- regression gates;
- rollback;
- run comparability;
- before/after evidence requirement.

Still needed for Phase25-A:

- Phase25 experiment record schema;
- primary/secondary/guardrail metric list;
- code/config/source hash binding template;
- regression command matrix;
- dirty-tree treatment;
- comparison result statuses;
- machine-readable acceptance/reject/review criteria;
- benchmark-missing behavior.

## 14. Confirmed Gaps

- No approved benchmark source exists for TOPIX/Nikkei/JPX.
- Daily benchmark snapshots are placeholders with `status=MISSING`.
- `summarize --scope performance` does not provide MDD, turnover, cash utilization, gross exposure, or single-name concentration for the inspected run.
- `runtime_evaluation_capital` remains fixed in Current even when total equity grows.
- Fixed `evaluation_capital` and `max_exposure` remain in Runtime capital deployment policy.
- Cash ratio cause decomposition is not canonical.
- Monthly/quarterly Runtime returns are not implemented.
- Calmar, Sharpe, Sortino, exposure-adjusted return, and cash-adjusted return are not materialized.

## 15. Non-Blocking Gaps

- Realized-slice win/loss and profit factor are approximate without lot IDs.
- Fees/tax/slippage are unavailable.
- Sector and regime attribution are partial.
- Paper Trading and capital allocation backtest metrics overlap by name but are non-authoritative for Runtime evaluation.
- 2023 abandoned run is useful diagnostic evidence, not a clean acceptance baseline.

## 16. Blocking Gaps

Blocking for full Phase25 performance evaluation:

- benchmark source authority missing;
- daily equity/cash/exposure canonical metric artifact missing;
- compound reinvestment not proven;
- cash drag attribution not decomposable by cause.

Not blocking for Phase25-A design entry:

- these gaps are exactly what Phase25-A should design and materialize before Strategy experiments.

## 17. Required User-Provided Evidence

- Approved benchmark source decision, or explicit decision that benchmark metrics remain `MISSING`.
- User/operator selected baseline run directory for Phase25-A.
- Any retained `summarize --write-evidence` output for the selected baseline if already produced.

## 18. User-Run Test Requirements

Codex did not run any long Historical Runtime test.

Future user/operator runs after Phase25-A contract materialization:

- 20BD short baseline;
- 60BD minimum risk/volatility baseline;
- 200BD long diagnostic baseline;
- 252BD first annual-target evaluation.

Each should preserve daily valuation, Strategy artifacts, planning evidence, fills, realized slices, position campaigns, benchmark snapshots, final summary, and source hashes.

## 19. Proposed Phase25-A Task Decomposition

1. `Phase25-A1 Metrics Contract and Daily Metric Artifact Design`
2. `Phase25-A2 Benchmark Source Decision and PIT-Safe Benchmark Evidence Contract`
3. `Phase25-A3 Capital Authority and Compound Reinvestment Trace`
4. `Phase25-A4 Cash Ratio Attribution Observability Contract`
5. `Phase25-A5 Experiment Comparison Evidence Template`

## 20. Final Entry Gate Decision

Phase25-A should begin as:

`READY_WITH_GATES`

Do not begin Strategy improvement yet. The next work should formalize metric materialization, benchmark status, capital efficiency tracing, compound reinvestment evidence, and experiment comparison artifacts.
