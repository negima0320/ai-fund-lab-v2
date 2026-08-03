# Phase25-A1 Performance Evaluation Work Design and Daily Evidence Contract

## 1. Executive Summary

Phase25-A1 defines the official work design for Phase25 Performance Evaluation. It does not implement producers, schemas, CLI commands, Runtime changes, Strategy changes, benchmark fetching, or metric calculations.

Primary outcome:

```text
Performance Evaluation can proceed only after daily capital, equity, exposure, benchmark status, and missing-evidence authority are materialized as immutable post-hoc evidence.
```

The design preserves the Phase24 closure rule: Runtime correctness and Performance Evaluation are separate axes. Performance evidence remains post-hoc diagnostic and must not become Runtime, learning, calibration, validation, accepted generation, or automatic promotion authority.

## 2. Primary Judgment

```text
PHASE25_A1_PERFORMANCE_EVALUATION_DESIGN_COMPLETE_USER_DECISION_REQUIRED
```

Phase25-A status:

```text
READY_WITH_USER_DECISIONS
```

The design is ready for implementation, but benchmark source authority and risk-free/cash baseline policy require user decisions before benchmark-relative and official Sharpe-style metrics can be complete.

## 3. Scope

In scope:

- Performance Evaluation workflow.
- Run eligibility contract.
- Official metric classification and definitions.
- Daily Evaluation Evidence Artifact Contract.
- Run-level Performance Summary Artifact Contract.
- Missing, interrupted, abandoned, and review-stop handling.
- Capital efficiency daily evidence.
- Compound reinvestment trace.
- Cash ratio attribution evidence.
- Benchmark missing contract.
- Baseline and experiment comparison workflow.
- Follow-on implementation and user-run test tasks.

Out of scope:

- Runtime implementation changes.
- Strategy improvement.
- Position sizing, capital deployment, threshold, PM, ADD, REDUCE, EXIT, or cash policy change.
- Benchmark data fetching or vendor approval.
- Corporate Action Manual Review implementation.
- Operator CLI implementation.
- Long Historical Runtime execution by Codex.

## 4. Existing Contract Reuse

Phase25-A1 reuses these established contracts.

| Contract | Reuse decision |
|---|---|
| Phase20-B Performance Metric Contract | Reuse metric taxonomy, authority fields, missing-data policy, equity/return/drawdown/turnover definitions. |
| Phase20-B Benchmark Contract | Reuse benchmark missing rule: missing benchmark is `MISSING`, never zero, cash, or proxy. |
| Phase20-B Experiment Comparison Contract | Reuse baseline/variant identity, evidence hashes, same-window comparability, one hypothesis/one change. |
| Phase24-A Performance Evaluation Contract | Reuse post-hoc-only rule, +50% horizon rule, short-period warnings, benchmark missing behavior. |
| Phase24 final handoff | Reuse Phase24 closed Runtime status and Phase25 entry gates. |
| Phase25-AA investigation | Reuse confirmed gaps: missing daily metric artifact, missing benchmark source, ambiguous compound reinvestment, non-decomposed cash ratio. |
| Runtime Architecture v2 | Reuse Current, Ledger, Pending, Planning, Submit, Safety, and Corporate Action authority boundaries. |
| Strategy Architecture v1 | Reuse prohibition against feeding Runtime outcomes back into Strategy learning or acceptance. |
| Strategy Experiment Contract | Reuse single-change principle, regression-first, risk metrics, rollback, and overfitting prevention. |

## 5. Performance Evaluation Workflow

Official workflow:

| Step | Name | Input | Output | Gate |
|---:|---|---|---|---|
| 1 | Select run | Run id, run directory, summary id if available | `selected_run_ref` | Run path exists and identity fields are readable. |
| 2 | Check eligibility | `run_state.json`, final summary, halt/review state, lifecycle evidence | `run_eligibility` | Official, diagnostic, partial, or rejected classification. |
| 3 | Inventory evidence | Daily Current, valuation, executions, realized slices, position campaigns, strategy artifacts, benchmark snapshots | `evidence_completeness` | Missing fields are explicit and typed. |
| 4 | Materialize daily evidence | Immutable run-scoped evidence only | Daily evaluation evidence v1 | No interpolation, no latest-path fallback, no zero-fill. |
| 5 | Aggregate run summary | Valid daily evidence series | Run-level performance summary v1 | Uses daily evidence, not ad hoc scans. |
| 6 | Evaluate capital efficiency | Daily capital fields and policy targets | Capital efficiency block | Cash/exposure/idle-cash buckets are visible. |
| 7 | Trace compound reinvestment | Position sizing, planning, submit, capital config, Current equity | Compound reinvestment block | Fixed-cap constraints and dynamic-equity use are separated. |
| 8 | Attribute cash ratio | Daily policy, candidates, orders, reservations, fills | Cash attribution block | Yen buckets are not double-counted. |
| 9 | Evaluate benchmark | Approved benchmark evidence if present | Benchmark block | Missing benchmark remains `MISSING`. |
| 10 | Compare experiment | Baseline and variant summaries | Comparison record | One hypothesis, one change, regression first. |

## 6. Run Eligibility Contract

| Run state | Official use |
|---|---|
| `COMPLETE` with complete daily evidence | Official baseline/evaluation eligible. |
| `COMPLETE_WITH_NON_BLOCKING_GAPS` | Eligible for metrics whose authorities are complete; missing metrics remain missing. |
| `ABANDONED` due to Corporate Action Manual Review | Diagnostic only until review is resolved; not official baseline. |
| `REVIEW_REQUIRED` | Diagnostic only; no official before/after decision. |
| `CRASHED` | Runtime defect evidence; not performance baseline. |
| `PARTIAL` or interrupted | Partial-period diagnostic only; no annual target judgment. |
| `INSUFFICIENT_EVIDENCE` | No official metrics except listed readable facts. |

Minimum horizon policy:

| Use | Minimum |
|---|---:|
| Display period return | 1 valid completed business day. |
| Display annualized return with warning | 20 valid completed business days. |
| Risk metric review without short-period warning | 60 valid completed business days. |
| First +50% annual target judgment | 252 valid completed business days. |

Dirty tree handling:

- Direct baseline/variant comparison requires identical source identity except the declared change.
- Dirty working tree is allowed only if dirty status and diff hash are captured.
- If dirty status differs and the changed component is not declared, comparison status is `INCOMPARABLE`.

## 7. Metric Classification

| Class | Metrics |
|---|---|
| Core return | Total Return, Return Rate, CAGR, Annualized Return, Monthly Return, Quarterly Return. |
| Risk | Max Drawdown, Volatility, Sharpe, Sortino, Calmar, downside volatility, drawdown duration. |
| Trade/outcome | Profit Factor, Win Rate, Loss Rate, Trade Count, Holding Period, turnover, average trade notional. |
| Capital efficiency | runtime_evaluation_capital, buying power, cash, market value, total equity, cash ratio, exposure ratio, idle cash, position count, compound reinvestment. |
| Benchmark | benchmark return, relative return, excess return, beta/alpha only after benchmark source approval. |
| Attribution | symbol, position, campaign, action, cash drag, exposure drag, candidate/opportunity, market context. |
| Experiment | before/after deltas, guardrails, regression status, comparability status, decision. |

Each metric output must include:

```text
metric_id
metric_name
value
unit
status
confidence_class
definition
calculation_formula
authority
producer
source_artifacts
missing_data_policy
temporal_safety
limitations
warnings
contract_version
```

## 8. Metric Definition Contract

| Metric | Metric id | Formula / definition | Authority | Missing policy |
|---|---|---|---|---|
| Total Return | `core.total_return` | `final_equity - initial_equity` | Run-level summary derived from daily evidence | Missing if either endpoint missing. |
| Return Rate | `core.return_rate` | `total_return / initial_equity` | Initial/final equity authority | Missing if denominator absent or zero. |
| CAGR | `core.cagr` | `(final_equity / initial_equity) ** (252 / valid_business_days) - 1` | Daily equity curve | Official only at >=252BD; warning below. |
| Annualized Return | `core.annualized_return` | Same 252BD compounding formula for display | Daily equity curve | Warning below 60BD; no +50% judgment below 252BD. |
| Max Drawdown | `risk.max_drawdown` | `min((equity - running_peak) / running_peak)` | Daily equity evidence | Missing if equity curve incomplete. |
| Volatility | `risk.volatility` | Std dev daily returns times `sqrt(252)` | Daily returns | Missing if insufficient observations. |
| Sharpe | `risk.sharpe` | Annualized excess daily return / annualized volatility | Daily returns plus approved baseline | Missing until risk-free/cash baseline policy fixed. |
| Sortino | `risk.sortino` | Annualized excess return / downside volatility | Daily returns plus approved baseline | Missing if downside sample/baseline insufficient. |
| Calmar | `risk.calmar` | CAGR / absolute max drawdown | CAGR and MDD | Missing if either component missing. |
| Profit Factor | `outcome.profit_factor` | Gross realized gains / absolute gross realized losses | Realized slices | Approximate without stable lot ids. |
| Win Rate | `outcome.win_rate` | Winning realized slices / realized slices | Realized slices | Approximate without stable lot ids. |
| Holding Period | `activity.holding_period` | Business days by position campaign or realized slice | Position campaigns and executions | Partial without tax-lot linkage. |
| Turnover | `activity.turnover` | Sum absolute executed notional / average equity | Canonical executions and daily equity | Missing if either side missing. |
| Trade Count | `activity.trade_count` | Count canonical execution events by action/side | Execution-equivalent events | Missing if execution evidence absent. |
| Monthly Return | `period.monthly_return` | Month-end equity / previous month-end equity - 1 | Daily equity curve | Partial for incomplete month. |
| Quarterly Return | `period.quarterly_return` | Quarter-end equity / previous quarter-end equity - 1 | Daily equity curve | Partial for incomplete quarter. |
| Exposure-adjusted Return | `capital.exposure_adjusted_return` | Period return / average gross exposure | Daily return and exposure | Missing if exposure missing; not infinite at zero exposure. |
| Cash-adjusted Return | `capital.cash_adjusted_return` | Return relative to deployed capital or cash-utilized denominator, explicitly labeled | Daily capital evidence | Requires denominator policy in artifact. |
| Attribution | `attribution.*` | Contribution by declared dimension | Daily evidence and canonical artifacts | Missing/partial by dimension. |

## 9. Horizon and Annualization Contract

Annualization uses 252 Japanese business-day convention for Phase25 reporting unless a later calendar contract supersedes it.

Rules:

- Period return is always the primary fact.
- Annualized return for short runs is display-only.
- Under 20 valid business days, annualized return is `NOT_AVAILABLE` unless explicitly requested as diagnostic.
- From 20 to 59 valid business days, annualized return is `AVAILABLE_WITH_SHORT_PERIOD_WARNING`.
- From 60 to 251 valid business days, annualized/risk metrics are diagnostic but cannot decide the +50% target.
- At 252 or more valid business days, CAGR/Annualized Return may be used for the +50% target judgment if run eligibility is official.

## 10. Daily Evaluation Evidence Contract

Artifact:

```text
artifact_name = phase25_daily_evaluation_evidence
schema_version = phase25_daily_evaluation_evidence.v1
producer = phase25_daily_evaluation_evidence_producer
materialization_path = reports/performance_evaluations/<RUN_ID>/daily/<YYYY-MM-DD>/daily_evaluation_evidence.json
```

The producer must be read-only with respect to Runtime evidence and must not mutate Strategy, Runtime, ledger, accepted generation, source data, or benchmark data.

Required top-level fields:

| Field | Requirement |
|---|---|
| `schema_version` | Required. |
| `run_id` | Required. |
| `business_date` | Required. |
| `source_revision` | Required if available; otherwise `MISSING`. |
| `runtime_mode` | Required. |
| `run_eligibility_status` | Required. |
| `metric_contract_version` | Required. |
| `source_artifact_refs` | Required list of input artifacts and hashes when available. |
| `evidence_status` | Required summary status. |
| `capital` | Required block. |
| `returns` | Required block if previous equity exists; otherwise status fields required. |
| `risk` | Required block for running peak/drawdown status. |
| `activity` | Required block for trade/order/fill counts and notional status. |
| `benchmark` | Required block; may be `MISSING`. |
| `attribution_inputs` | Required block with available/missing flags. |
| `missing_fields` | Required list. |
| `warnings` | Required list. |

Required `capital` fields:

```text
runtime_evaluation_capital
buying_power
cash
market_value
total_equity
cash_ratio
gross_exposure_ratio
net_exposure_ratio
position_count
idle_cash
target_gross_exposure_ratio
target_cash_reserve_ratio
policy_cash_buffer
pending_reserved_cash
actual_deployed_notional
executed_buy_notional
executed_sell_notional
```

Conditional fields:

- `benchmark.daily_return`, `benchmark.cumulative_return`, `benchmark.relative_return`: required only when approved benchmark evidence exists.
- `candidate_count`, `eligible_candidate_count`, `opportunity_count`, `rejected_candidate_count`: required when candidate/opportunity artifacts exist.
- `planned_buy_notional`, `submitted_buy_notional`, `filled_buy_notional`: required when planning/submit/execution evidence exists.
- `unexplained_idle_cash`: required when cash remains after all explainable cash buckets.

## 11. Daily Evidence Authority

| Field group | Official authority |
|---|---|
| Cash / buying power / market value / total equity | End-of-business-date Current after execution and valuation refresh. |
| Daily return | Current day total equity vs previous valid daily evaluation evidence total equity. |
| Position count | Current open Runtime-owned positions after execution and valuation refresh. |
| Execution notional | Canonical execution-equivalent performance events. |
| Realized PnL | Realized slices or canonical runtime performance events, with approximate status if lot ids are missing. |
| Target exposure / target cash | Strategy portfolio policy and position sizing evidence for the same business date. |
| Pending reserved cash | Pending / planning authority for the same date. |
| Benchmark | Approved PIT-safe benchmark artifact only. |
| Candidate/opportunity counts | Run-scoped candidate and opportunity artifacts only. |
| Market context | Run-scoped market context artifact only; post-hoc attribution, never learning authority. |

Forbidden authorities:

- Shared latest `.runtime` scans.
- Manual latest path or mtime fallback.
- Missing benchmark interpreted as zero.
- Missing position interpreted as zero.
- Broker snapshot without reconciliation.
- Runtime Test/Paper Ledger/PnL/selected/bought/cash/portfolio value as learning input.

## 12. Missing and Failure Contract

Status taxonomy:

| Status | Meaning |
|---|---|
| `AVAILABLE` | Value is present from official authority. |
| `DERIVED` | Value is computed from official authority. |
| `PARTIAL` | Value covers only an explicitly stated subset. |
| `MISSING` | Required artifact or field is absent. |
| `NOT_APPLICABLE` | Metric does not apply. |
| `NOT_AVAILABLE` | Intentionally unavailable in this profile. |
| `INVALID` | Artifact exists but fails schema or temporal safety checks. |
| `CONFLICT` | Multiple authorities disagree. |
| `REVIEW_REQUIRED` | Manual review or Corporate Action state blocks official use. |

Rules:

- Missing data is never zero-filled.
- Missing benchmark blocks benchmark-relative metrics only.
- Missing daily equity blocks MDD, volatility, Sharpe, Sortino, Calmar, monthly/quarterly return, and turnover.
- Corporate Action Manual Review stop makes the run diagnostic until resolved.
- Interrupted runs may produce partial daily evidence, but run-level official judgment is blocked.
- If an input artifact is invalid, dependent metrics are `INVALID` or `CONFLICT`, not derived.

## 13. Capital Efficiency Evaluation Design

Capital efficiency is evaluated daily and run-level.

Core daily formulas:

```text
cash_ratio = cash / total_equity
gross_exposure_ratio = gross_market_value / total_equity
net_exposure_ratio = net_market_value / total_equity
cash_utilization = 1 - cash_ratio
idle_cash = max(0, cash - policy_cash_buffer - pending_reserved_cash)
```

Required evaluation fields:

- `runtime_evaluation_capital`
- `buying_power`
- `cash`
- `market_value`
- `total_equity`
- `cash_ratio`
- `gross_exposure_ratio`
- `position_count`
- `idle_cash`
- `compound_reinvestment_status`
- `capital_base_used_by_position_sizing`
- `capital_base_used_by_planning`
- `capital_limit_used_by_submit_or_deployment`

Run-level rollups:

- Average cash ratio.
- Final cash ratio.
- Average gross exposure.
- Maximum gross exposure.
- Average idle cash.
- Days with idle cash above threshold.
- Days where target exposure exceeded actual exposure.
- Days where candidate/opportunity shortage is observed.

## 14. Compound Reinvestment Trace Contract

Purpose:

```text
Confirm whether profits are redeployed from increased total equity instead of staying anchored to initial 1,000,000 JPY.
```

Daily trace fields:

| Field | Meaning |
|---|---|
| `initial_capital` | Run start equity/cash authority. |
| `runtime_evaluation_capital` | Current runtime evaluation field. |
| `current_total_equity` | Current total equity authority. |
| `position_sizing_capital_base` | Equity base consumed by position sizing. |
| `planning_capital_base` | Capital base consumed by planning/capital deployment. |
| `submit_capital_limit` | Any max exposure or submit/deployment cap. |
| `target_notional_before_caps` | Desired notional from sizing before caps. |
| `target_notional_after_caps` | Desired notional after caps. |
| `filled_notional` | Executed notional. |
| `fixed_cap_binding` | Whether fixed evaluation capital/max exposure constrained deployment. |

Status policy:

| Status | Definition |
|---|---|
| `CONFIRMED` | Sizing, planning, and cap application are proven to reference current equity or explicitly compound-compatible capital; no fixed initial-cap binding is active. |
| `PARTIAL` | Position sizing uses current equity, but downstream planning/submit/capital caps are not fully proven. |
| `NOT_ESTABLISHED` | A fixed initial-cap or max-exposure cap prevents profit deployment without policy justification. |
| `AMBIGUOUS` | Required trace evidence is missing or conflicting. |

Phase25-AA current status remains:

```text
COMPOUND_REINVESTMENT_AMBIGUOUS
```

## 15. Cash Ratio Attribution Design

Cash attribution is a waterfall. Yen amount is assigned once; cause flags may be multiple but monetary attribution must not double-count.

Waterfall order:

| Order | Bucket |
|---:|---|
| 1 | Required policy cash buffer. |
| 2 | Safety reserved cash. |
| 3 | Pending reserved cash. |
| 4 | Price constraint cash. |
| 5 | Lot-size residual cash. |
| 6 | Position sizing residual cash. |
| 7 | Position count limit cash. |
| 8 | Candidate/opportunity shortage cash. |
| 9 | No-action or ADD-not-established cash. |
| 10 | Unexplained idle cash. |

For the inspected 2024 10BD final state, Phase25-AA established:

```text
cash_ratio = 36.3421%
target_cash_reserve_ratio = 21%
unattributed_cash_ratio_after_policy_buffer = about 15.3421 percentage points
```

The remaining amount requires daily evidence across candidates, sizing, planning, pending reservations, and fills. Final state alone is not sufficient for cause attribution.

## 16. Run-level Performance Summary Contract

Artifact:

```text
artifact_name = phase25_performance_evaluation_summary
schema_version = phase25_performance_evaluation_summary.v1
producer = phase25_performance_summary_producer
materialization_path = reports/performance_evaluations/<RUN_ID>/performance_evaluation_summary.json
```

Relationship to existing summaries:

- Supplements `reports/runtime_tests/summaries/<SUMMARY_ID>/summary.json`.
- Does not replace Runtime final summary.
- Consumes daily evaluation evidence v1.
- Must not rescan mutable latest state.

Required blocks:

- `run_identity`
- `run_eligibility`
- `metric_contract_versions`
- `evidence_completeness`
- `core_returns`
- `risk_metrics`
- `capital_efficiency`
- `trade_activity`
- `attribution`
- `benchmark`
- `experiment_comparability`
- `missing_metrics`
- `warnings`
- `decision_support`

## 17. Benchmark Missing Contract

Benchmark source status:

```text
benchmark_source_status = USER_DECISION_REQUIRED
```

Rules:

- TOPIX/Nikkei225/PIT-safe benchmark metrics remain `MISSING` until source authority is approved.
- Missing benchmark does not block absolute return, capital efficiency, drawdown, volatility, or cash attribution.
- Missing benchmark blocks relative return, alpha, beta, tracking error, information ratio, and benchmark-relative experiment decisions.
- Cash may be used only as an explicitly labeled diagnostic baseline, not as TOPIX or market benchmark.
- When a benchmark source is later approved, benchmark blocks can be rematerialized from immutable daily strategy evidence without rerunning Runtime, provided the benchmark artifact is PIT-safe and versioned.

## 18. Experiment Comparison Workflow

Experiment comparison requires:

- 1 hypothesis.
- 1 declared change.
- Regression gates before performance judgment.
- Baseline and variant identity hashes.
- Same date window for direct A/B comparison.
- Same initial cash/initial position policy.
- Same Runtime/Safety/Submit/Corporate Action guard contracts.
- Before/after evidence from run-level performance summaries.

Comparison statuses:

| Status | Meaning |
|---|---|
| `IMPROVED` | Primary metric improves and guardrails do not regress beyond thresholds. |
| `DEGRADED` | Primary metric or guardrails materially worsen. |
| `NO_MEANINGFUL_CHANGE` | Difference is within tolerance. |
| `INCOMPARABLE` | Identity, date, source, config, or run eligibility differs outside declared change. |
| `INSUFFICIENT_EVIDENCE` | Required metrics or horizon are missing. |
| `REVIEW_REQUIRED` | Mixed outcome or authority concern. |

No Strategy improvement task should begin until baseline daily evidence and run-level summary implementation exist.

## 19. Design Decision Records

| DDR | Decision |
|---|---|
| DDR-001 Daily Equity Authority | Use EOD Current after execution and valuation refresh as daily equity authority. |
| DDR-002 Summary Relationship | Phase25 summary supplements Runtime summary and is produced from daily evaluation evidence. |
| DDR-003 Benchmark Missing | Benchmark-relative metrics remain `MISSING`; no zero/proxy substitution. |
| DDR-004 Annualization | 252BD compounding convention; +50% judgment only at >=252BD official runs. |
| DDR-005 Abandoned Runs | Corporate Action review-stop runs are diagnostic until review resolution. |
| DDR-006 Cash Attribution | Waterfall amounts are mutually exclusive. |
| DDR-007 Compound Reinvestment | Must trace sizing, planning, caps, and fills before declaring confirmed. |
| DDR-008 Experiment Comparison | One hypothesis and one change remain mandatory. |

## 20. Blocking Design Gaps

No blocking gap remains for design completion.

Blocking before full official Phase25 performance evaluation:

- Approved benchmark source is missing.
- Sharpe/Sortino excess-return baseline policy is not fixed.
- Daily evaluation evidence producer is not implemented.
- Run-level performance summary producer is not implemented.

## 21. Non-Blocking Design Gaps

- Stable tax-lot ids are unavailable; win rate and profit factor may remain approximate.
- Fees, tax, and slippage are unavailable unless evidence later supplies them.
- Sector attribution is partial until sector source coverage is approved.
- 2023 Corporate Action stop run remains diagnostic.
- Runtime speed is not addressed by this design.

## 22. Required User Decisions

| Decision | Required for |
|---|---|
| Approved benchmark source: TOPIX, Nikkei225, or other PIT-safe source | Benchmark-relative metrics and experiment relative judgment. |
| Risk-free/cash diagnostic baseline policy | Sharpe/Sortino excess-return calculation. |
| First official baseline run id after implementation | Official Phase25 baseline materialization. |
| Whether benchmark source absence is accepted temporarily | Absolute-only Phase25-A implementation sequencing. |

## 23. Required Implementation Tasks

Recommended sequence:

1. `Phase25-A2 Daily Evaluation Evidence Schema and Producer`
2. `Phase25-A3 Run-level Performance Summary Aggregator`
3. `Phase25-A4 Capital Efficiency and Compound Reinvestment Trace`
4. `Phase25-A5 Cash Ratio Attribution Materialization`
5. `Phase25-A6 Benchmark Source Decision and Benchmark Evidence Adapter`
6. `Phase25-A7 Experiment Comparison Evidence Template`
7. `Phase25-A8 Baseline Materialization on User-selected Run`

## 24. Required User-Run Tests

Codex must not run long Historical Runtime tests. After implementation, user/operator should run:

| Test | Purpose |
|---|---|
| Existing 2024 10BD evidence materialization | Validate producer on known PASS run without rerunning Runtime. |
| 20BD fresh run | Validate annualized display and short-period warning. |
| 60BD fresh run | Validate risk metric sample and cash attribution. |
| 200BD long diagnostic | Validate durability before annual target run. |
| 252BD official baseline | First +50% annual target evaluation. |

## 25. Acceptance Criteria

Phase25-A implementation is acceptable when:

- Daily evaluation evidence exists for every valid completed business day.
- Missing fields are explicit and typed.
- Run-level summary is produced only from daily evidence.
- Total return, CAGR/annualized return, MDD, volatility, Sharpe/Sortino/Calmar status, turnover, trade count, monthly/quarterly return, exposure-adjusted return, cash-adjusted return, and attribution status are present.
- Capital fields include runtime_evaluation_capital, buying power, cash, market value, total equity, cash ratio, exposure ratio, position count, idle cash, and compound reinvestment trace.
- Benchmark-relative metrics remain missing when source is not approved.
- Experiment comparison refuses incomparable runs.
- Runtime/Strategy/Safety/Submit/Corporate Action guards are not changed.

## 26. Recommended Next Task

```text
Phase25-A2 Daily Evaluation Evidence Schema and Producer
```

Phase25-A2 should implement only the read-only daily evidence schema/producer and validate it against an existing short Runtime run. It should not improve Strategy or alter Runtime behavior.
