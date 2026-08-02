# Phase24-IN Phase25 Performance Evaluation and Improvement Plan

## Phase25 Objective

`Phase25 - Performance Evaluation, Attribution and Strategy Improvement`

The objective is to measure baseline performance correctly, attribute the causes of return and risk, and then improve Strategy behavior through controlled experiments.

Annual return `+50%` is the user target. It is not guaranteed, not achieved, and must not be inferred from the 2024 10BD `+6.766%` run.

## Entry Gate

Phase25 may begin with gates:

1. Baseline run evidence is reproducible.
2. Metrics contract is fixed.
3. Benchmark contract is fixed.
4. Experiment contract is fixed.
5. Prohibited learning inputs are explicit.
6. Runtime vs Strategy change boundary is explicit.
7. Safety and Submit Guard remain unchanged.
8. Long tests are user/operator-owned.
9. One hypothesis / one change.
10. Regression and historical comparison are available.

## Workstream 1: Baseline Performance Evaluation

Required metrics:

- Total Return, Annualized Return, CAGR
- Max Drawdown, Drawdown Duration
- Volatility, Sharpe, Sortino, Calmar
- Profit Factor, Win Rate, Average Win, Average Loss, Payoff Ratio, Expectancy
- Turnover, Trade Count
- Average and Median Holding Period
- Exposure-adjusted and Cash-adjusted Return
- Monthly / Quarterly Return
- Regime / Market Context / Position Count / Cash Ratio returns
- BUY / ADD / REDUCE / EXIT attribution

## Workstream 2: Benchmark Evaluation

Benchmark candidates:

- TOPIX
- Nikkei 225
- JPX Prime 150
- market-cap weighted Japanese equity benchmark
- equal-weight universe benchmark

Compare:

- absolute return, excess return, alpha, beta
- drawdown, volatility
- up capture, down capture
- hit rate and regime differences

Benchmark construction must be PIT-safe.

## Workstream 3: Capital Efficiency and Compound Reinvestment

Priority questions:

- What is `runtime_evaluation_capital` authority?
- Is any initial-capital fixed reference still used?
- Does Position Sizing use total_equity / buying_power correctly?
- How are realized and unrealized PnL reflected?
- Does cash buffer / max exposure / position count scale with equity?
- Is the 2024 `36.3421%` cash ratio caused by Market Context, Opportunity shortage, Sizing constraints, or policy?

Required time series:

- Cash, Market Value, Total Equity, Buying Power
- Cash Ratio, Exposure Ratio
- Position Count
- Reserved and Deployable Capital
- Idle Cash
- Strategy Target Exposure and Actual Exposure

## Workstream 4: Attribution

Decompose returns into:

- Candidate Selection
- Opportunity Ranking
- Market Context
- Portfolio Policy
- Position Count
- Position Sizing
- Entry Timing
- ADD / REDUCE / EXIT
- Holding Period
- Sector / Market Regime
- Corporate Event
- Cash Drag
- Missed Opportunity
- Slippage / Transaction Cost
- Constraint Cost
- Review / Block Cost

## Workstream 5: Strategy Improvement

Candidate hypotheses:

- Candidate quality
- Opportunity ranking calibration
- Entry threshold
- Market Context sensitivity
- Dynamic Position Count
- Dynamic Cash / Exposure
- Position Sizing concentration
- ADD / REDUCE / EXIT conditions
- Holding Period
- Sector concentration
- Cash Drag
- Reinvestment
- Volatility scaling
- Drawdown control
- Regime transition response

Experiment rule:

```text
1 hypothesis
1 change
before/after evidence
regression first
no guard weakening
```

## Workstream 6: Runtime Performance

Measure:

- job and stage duration
- Market Refresh
- Feature Generation
- Candidate / Opportunity
- PM
- Strategy artifacts
- Planning / Submit / Fill / Ledger
- Snapshot / Evidence copy
- Resume overhead
- repeated artifact generation
- redundant file I/O
- Parquet load cost
- model load cost

Classify optimizations that do not change Production Runtime behavior.

## Workstream 7: Operator Operations

Backlog commands:

- review list / show / resolve
- corporate action approve / reject
- sell all / partial
- hold / defer
- dry-run / confirm
- resume after review
- audit history
- reason entry
- authority artifact binding

Manual operations must not bypass Submit Guard, Safety Guard, Planning Authority, or Corporate Action Guard.

## Prohibited Approaches

- Do not claim annual `+50%` achieved.
- Do not annualize 10BD return as acceptance.
- Do not optimize to one period.
- Do not use future data.
- Do not use Runtime/Paper Ledger outcomes as learning input.
- Do not force fixed BUY counts.
- Do not weaken Safety, Submit, or Corporate Action guards.
- Do not bundle multiple Strategy changes in one experiment.

## Acceptance Criteria

Phase25-A should complete only when baseline metrics, benchmark contract, capital efficiency evidence, attribution scope, and experiment protocol are all materialized in machine-readable evidence.
