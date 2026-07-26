# Phase21 Performance Improvement Entry Plan

## Phase21 Name

`Phase21 - Strategy and Performance Improvement`

## Objective

Maintain the current Runtime Contract, Safety Contract, and PIT Authority while improving the Japanese equities AI operation toward the annual `+50%` target through evidence-first diagnosis, controlled experiments, and cross-regime validation.

## Starting Judgment

Phase20 post-fix Bull and Range runs passed Runtime/Lifecycle but both produced negative returns:

- Bull 20BD: `-2.672%`
- Range 20BD: `-1.069%`

Therefore, Phase21 starts from:

```text
CURRENT_STRATEGY_PERFORMANCE_INSUFFICIENT
RUNTIME_CONTRACT_MUST_BE_PRESERVED
```

## Workstream Order

1. Phase21-A 245BD Long-run Finalization and Diagnostic Dataset Certification
2. Phase21-B Performance Authority and Metric Completion
3. Phase21-C PM Attribution
4. Phase21-D Position Holding Attribution
5. Phase21-E Capital Deployment Audit
6. Phase21-F Candidate / Opportunity Ranking Quality
7. Phase21-G Improvement Experiment Contract
8. Phase21-H+ Evidence-based strategy experiments

## Phase21-A 245BD Long-run Finalization and Diagnostic Dataset Certification

Active run:

```text
runtime-test-historical-extended-smoke-20260726T053732539035Z
```

Current handoff status:

- status: `RUNNING`
- completed_business_days: `188`
- latest_completed_business_date: `2023-06-08`
- next_job: `2023-06-09:market_refresh`

User executes or resumes long-running Historical work. Codex only reads final evidence after completion.

Phase21-A must certify the completed run not only as final long-run performance evidence but also as the primary run-scoped diagnostic dataset for Phase21.

Certification targets:

- run identity
- start/end dates
- completed business days
- final state hash
- daily evidence completeness
- position campaigns
- PM decision snapshots
- BUY / SELL plans
- pending lifecycle
- submit evidence
- execution evidence
- realized slices
- current valuation
- cash
- market value
- positions
- benchmark snapshots
- sector evidence
- review / block findings

Minimum diagnostic extracts:

- daily portfolio state
- position campaign attribution
- PM decision attribution
- capital deployment timeline
- execution and realized slice attribution
- missing metric inventory
- diagnostic dataset certification

Planned Phase21-A deliverables:

- `docs/phase_reports/phase21_a_245bd_long_run_diagnostic_dataset_certification.md`
- `reports/phase_reports/phase21_a_245bd_long_run_diagnostic_dataset_certification.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/dataset_inventory.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/daily_portfolio_state.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/position_campaign_attribution.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/pm_decision_attribution.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/capital_deployment_timeline.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/execution_and_realized_slice_attribution.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/missing_metric_inventory.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/diagnostic_dataset_certification.json`

## Phase21-B Minimum Metrics

- Daily Equity Curve
- Maximum Drawdown
- Cash Ratio
- Invested Ratio
- Cash Utilization
- Gross Exposure
- Position Count
- Turnover
- Single-name Concentration
- Sector Concentration
- Benchmark Return
- Excess Return
- Trade Win Rate
- Profit Factor
- Average Win
- Average Loss
- Holding Period

## Experiment Guardrails

Each experiment must define:

- Experiment ID
- Hypothesis
- Single Changed Variable
- Control
- Treatment
- Training-independent evaluation
- Bull / Range / Long-run comparison
- Benchmark comparison
- Acceptance Criteria
- Rollback Criteria

No experiment may use future returns as Runtime decision-time input.

The 245BD run is the primary diagnostic period, not the sole acceptance period. Phase21 experiments must separate:

- Diagnostic period: this 245BD run
- Development / counterfactual period: explicitly separated period
- Validation period: unused period
- Regime checks: Bull, Bear or downtrend, Range
- Final holdout: period not used for improvement selection

The 245BD data may be used for post-run diagnosis, counterfactual analysis, attribution, hypothesis generation, experiment design, and holdout evaluation planning. It must not be used for future leakage, Runtime feature contamination, direct performance imitation, or backtest-result memorization.

## Initial Candidate Areas

- PM HOLD / EXIT / REDUCE / ADD logic
- profit retention
- loss cutting
- holding period
- max_positions and dynamic position count
- position weight
- cash reserve and reinvestment
- Candidate ranking
- Opportunity ranking
- BUY timing
- market regime adaptation
- sector diversification
- single-name concentration

Priority must be set from Phase21 evidence, not from intuition or one-off examples.

## Entry Status

`PHASE21_ENTRY_READY_AFTER_PHASE20_CLOSURE`
