# Phase20-B Performance Metric / Benchmark / Experiment Comparison Contract

## Executive Summary

Phase20-B defines the official contracts for Phase20 performance analysis:

- Performance Metric Contract
- Benchmark Contract
- Experiment Comparison Contract

Final judgment:

```text
PHASE20_B_PERFORMANCE_CONTRACT_COMPLETE_BASELINE_EXTRACTION_READY
```

The contract is documented at:

```text
docs/02_architecture/performance_metric_benchmark_experiment_contract.md
```

Phase20-B did not change Runtime, Strategy, AI, PM, Risk, Capital Allocation, Accepted Generation, Training, Calibration, Validation, Broker, or Runtime State.

## Reviewed Evidence

Reviewed Phase20-A artifacts:

- `docs/phase_reports/phase20_a_performance_baseline_and_attribution_evidence_inventory.md`
- `reports/phase_reports/phase20_a_performance_baseline_and_attribution_evidence_inventory.json`

Reviewed Architecture and Phase19 handoff:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/ai_training_and_generation_lifecycle.md`
- `docs/02_architecture/ai_generation_artifact_contract.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase19_bx_final_independent_implementation_review.md`
- `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`
- `docs/phase_reports/phase19_final_summary_and_phase20_handoff.md`
- `docs/phase_reports/phase19_to_phase20_chatgpt_handoff.md`

Reviewed baseline evidence:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/`
- `reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T213848054826Z-20260721T221640818568Z/summary.json`

## Reviewed Implementation

Read-only implementation review covered:

- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/performance_events.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

Implementation facts used by the contract:

- Current `total_equity` is projected as `projected_cash + market_value`.
- Realized PnL is projected from canonical Runtime-owned execution events using average cost.
- Canonical performance fill authority is `execution_equivalent`; raw broker detail is audit evidence unless canonical equivalents exist.
- Current valuation refresh has run-scoped evidence and updates valuation fields without changing position quantity or average price.
- Runtime Test `summarize --run-id` must not use unrelated shared `.runtime` event counts.

## Contract Decisions

| Area | Decision |
|---|---|
| Contract versions | `phase20_b_performance_metric_contract.v1`, `phase20_b_benchmark_contract.v1`, `phase20_b_experiment_comparison_contract.v1` |
| Equity timing | End-of-business-date after execution and current valuation refresh |
| Equity formula | `cash + market_value_of_open_runtime_owned_positions` |
| Drawdown | Mark-to-market equity curve; realized-only drawdown is rejected |
| Turnover primary | `sum(abs(executed_gross_notional)) / average_equity` |
| Win/loss unit | `realized_slice` approximate; exact lot-level metrics are missing until stable lot ID exists |
| Holding period | Position lifecycle and capital-weighted metrics are derivable; exact lot holding period missing |
| Benchmark primary | TOPIX, but status is missing until approved J-Quants-compatible source exists |
| Secondary benchmarks | Cash, Nikkei 225, equal-weighted eligible universe |
| Experiment comparability | `COMPARABLE`, `COMPARABLE_WITH_CAVEATS`, `NOT_COMPARABLE` |
| Missing data | Missing is never zero |
| Post-hoc outcomes | MFE/MAE/loss avoided/profit missed/counterfactuals are post-hoc only |

## Rejected Alternatives

| Alternative | Reason rejected |
|---|---|
| Use realized PnL only for drawdown | Ignores open positions and contradicts mark-to-market performance. |
| Treat missing benchmark as cash | Hides missing evidence. Cash is a separate secondary benchmark. |
| Use BUY/SELL one-to-one trade win rate | Invalid with ADD, REDUCE, partial sell, and open positions. |
| Use shared `.runtime` event scans as run authority | Violates Phase19-BY Run Authority Contract. |
| Annualize 20BD as primary target proof | Short-period annualization is unreliable and cannot prove +50% target. |
| Include pending orders in primary exposure | Primary exposure is executed exposure; committed exposure needs reserved cash evidence. |

## Metric Definition Matrix

| Metric group | Metrics | Status |
|---|---|---|
| Core return | Initial Equity, Final Equity, Total Return, Return Rate, Realized PnL, Unrealized PnL, Total PnL | `AVAILABLE` |
| Core return derived | Daily Return, Cumulative Return, Annualized Return | `DERIVABLE_EXACT` with short-period warning for annualized |
| Drawdown | Equity curve, peak, drawdown amount/rate, max drawdown, dates, recovery | `DERIVABLE_EXACT` after daily equity extraction |
| Exposure/cash | Gross exposure, net exposure, cash ratio, utilization, single-name concentration | `DERIVABLE_EXACT`; sector concentration `MISSING` |
| Trading activity | BUY/SELL/order/execution count, turnover, trade notional, position count | `AVAILABLE` or `DERIVABLE_EXACT` |
| Outcome | Win rate, profit factor, payoff, average win/loss, largest win/loss | `DERIVABLE_APPROXIMATE` or `DERIVABLE_PARTIAL` |
| PnL contribution | Symbol-level PnL | `DERIVABLE_PARTIAL`; sector-level `MISSING` |
| PM attribution | HOLD/ADD/REDUCE/EXIT counts | `AVAILABLE`; post-decision outcomes `POST_HOC_ATTRIBUTION_ONLY` |

The architecture contract includes the canonical registry for every requested metric ID. Exact value extraction is deferred to Phase20-C; Phase20-B fixes the names, units, formulas, status classes, authorities, missing policies, and temporal safety classes.

## Benchmark Decision

Primary benchmark:

```text
TOPIX
```

Status:

```text
MISSING_UNTIL_JQUANTS_COMPATIBLE_SOURCE_CONFIRMED
```

TOPIX is selected because it is the broadest standard benchmark for Japanese equities among the candidates. It is not yet usable because Phase20-A found benchmark evidence missing and Phase20-B does not fetch external data.

Secondary benchmarks:

- Cash: exact and usable as a no-risk diagnostic.
- Nikkei 225: missing until approved source exists.
- Equal-weighted eligible universe: missing until survivorship-safe eligible-universe returns exist.

## Experiment Comparison Rules

An experiment comparison record must include:

```text
experiment_id
baseline_run_id
candidate_run_id
code_revision
config_revision
accepted_generation_id
dataset_revision_id
test_profile
business_dates
initial_cash
initial_positions
broker_environment
market_data_snapshot
feature_snapshot
random_seed
external_effect_policy
runtime_architecture_version
performance_metric_contract_version
benchmark_contract_version
experiment_comparison_contract_version
changed_component
```

Fixed conditions include business dates, market data, initial cash, initial positions, test profile, broker environment, Runtime Architecture, external-effect policy, metric contract, and benchmark contract.

Only one declared change target is comparable by default. Multi-factor changes are allowed only as explicitly non-causal comparisons.

## Known Gaps

- Benchmark index time series missing.
- Sector mapping and sector return evidence missing.
- Stable lot-level realized PnL evidence missing.
- Fees, tax, slippage, and partial-fill realism not part of the Phase20 baseline contract.
- Full candidate-universe exclusion evidence below persisted Top50 not confirmed.
- PM threshold/confidence metrics not formalized.

## Architecture Impact

No Architecture SoT conflict was introduced.

New architecture contract:

```text
docs/02_architecture/performance_metric_benchmark_experiment_contract.md
```

This is an analysis contract. It does not alter Runtime authority, Accepted Generation authority, AI lifecycle authority, Broker boundary, or Training/Calibration/Validation contracts.

## Runtime Impact

Runtime impact:

```text
NONE
```

No Runtime code, Runtime State, Current, Pending, Ledger, PM, Safety, Broker, or Accepted Generation pointer was changed.

## Strategy Impact

Strategy impact:

```text
NONE
```

This phase defines measurement contracts only. It does not classify the 20BD negative return root cause and does not propose strategy changes.

## Required Follow-up

Recommended next phase:

```text
Phase20-C: Read-only Performance Baseline Extraction
```

Suggested scope:

1. Extract daily equity curve from run-scoped evidence.
2. Compute drawdown, exposure, cash utilization, turnover, and annualized return with short-period warning.
3. Emit metric outputs with `value`, `status`, `confidence_class`, `authority`, `limitations`, and `warnings`.
4. Do not compute benchmark-relative or sector metrics until data exists.

## Validation

Validation performed:

- JSON validation for `reports/phase_reports/phase20_b_performance_metric_benchmark_experiment_contract.json`
- `git diff --check`

Not performed:

- No long Historical Smoke.
- No full backtest.
- No benchmark data fetch.
- No sector data fetch.
- No training, calibration, validation, or Accepted Generation mutation.
- No Broker access.

## Final Judgment

```text
PHASE20_B_PERFORMANCE_CONTRACT_COMPLETE_BASELINE_EXTRACTION_READY
```

Baseline extraction may proceed using this contract. Benchmark-relative, sector, exact lot-level, and PM confidence metrics remain non-blocking gaps for later instrumentation or source approval.
