# Phase20-C Read-only Performance Baseline Extraction

## Executive Summary

Phase20-C extracted the official read-only Performance Baseline for the 20BD Baseline Run:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

Final judgment:

```text
PHASE20_C_BASELINE_EXTRACTION_COMPLETE_WITH_DERIVABLE_GAPS
```

Runtime judgment remains:

```text
PASS
```

Baseline performance remains:

```text
Initial equity = 1,000,000
Final equity = 955,100
Total return = -44,900 (-4.49%)
Realized PnL = -51,300
Unrealized PnL = +6,400
```

This phase did not change Runtime, AI, Opportunity, Strategy, PM, Risk, Training, Calibration, Validation, Accepted Generation, Broker state, or Runtime State.

## Required Documents Read

Read and applied:

- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase20_b_performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase20_a_performance_baseline_and_attribution_evidence_inventory.md`

Contract version used:

```text
phase20_b_performance_metric_contract.v1
```

## Evidence Scope

Primary run evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/
```

Summary evidence:

```text
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T213848054826Z-20260721T221640818568Z/summary.json
```

Daily equity authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/daily/<DATE>/current_valuation_refresh/current_valuation_manifest.json
```

Execution count and cash-effect notional authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/daily/<DATE>/execution/historical_fill_authority.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/daily/<DATE>/current_valuation_refresh/current_valuation_manifest.json
```

The older shared `.runtime/runtime_state/run_manifest/<DATE>/...` source manifests referenced by copied run manifests were not used as primary authority. They are mutable shared detail and old per-date files are not stable after later runtime-test activity. Counts remain anchored to run-scoped evidence and summary.

## Generated Artifacts

Generated baseline artifacts:

```text
reports/performance_baselines/runtime-test-historical-smoke-20260721T213848054826Z/baseline_metrics.json
reports/performance_baselines/runtime-test-historical-smoke-20260721T213848054826Z/performance_metrics.json
reports/performance_baselines/runtime-test-historical-smoke-20260721T213848054826Z/daily_equity_curve.csv
reports/performance_baselines/runtime-test-historical-smoke-20260721T213848054826Z/daily_equity_curve.json
```

Generated phase report JSON:

```text
reports/phase_reports/phase20_c_read_only_performance_baseline_extraction.json
```

## Extracted Metric Summary

| Metric | Value / scope | Status | Confidence |
|---|---:|---|---|
| Daily Equity Curve | 20 daily snapshots | `DERIVABLE_EXACT` | `HIGH` |
| Daily Return | 20 daily values | `DERIVABLE_EXACT` | `HIGH` |
| Cumulative Return | 20 daily values | `DERIVABLE_EXACT` | `HIGH` |
| Maximum Drawdown | -8.470749901845308% / -86,300 | `DERIVABLE_EXACT` | `HIGH` |
| Gross Exposure | daily series | `DERIVABLE_EXACT` | `HIGH` |
| Net Exposure | daily series | `DERIVABLE_EXACT` | `HIGH` |
| Cash Ratio | daily series | `DERIVABLE_EXACT` | `HIGH` |
| Cash Utilization | daily series | `DERIVABLE_EXACT` | `HIGH` |
| Turnover | 1.3485887835785726 | `DERIVABLE_EXACT` | `HIGH` |
| BUY Count | 5 | `AVAILABLE` | `HIGH` |
| SELL Count | 7 | `AVAILABLE` | `HIGH` |
| Execution Notional | 1,287,700 aggregate daily cash-effect notional | `DERIVABLE_EXACT` | `HIGH` |
| Position Count | daily series | `DERIVABLE_EXACT` | `HIGH` |
| Single-name Concentration | daily series | `DERIVABLE_EXACT` | `HIGH` |
| Usable Symbol-level PnL | open unrealized exact; realized grouped partial | `DERIVABLE_PARTIAL` | `HIGH` |
| TOPIX Benchmark Return | missing | `MISSING` | `HIGH` |
| Sector Concentration | missing | `MISSING` | `HIGH` |
| Lot-level Realized PnL | missing | `MISSING` | `HIGH` |

Every emitted metric record includes:

```text
value
status
authority
confidence_class
limitations
warnings
contract_version
```

The JSON metric records also include the contract-required descriptive fields such as metric ID, formula, numerator, denominator, time basis, aggregation level, source artifacts, join keys, open position handling, partial execution handling, ADD/REDUCE/EXIT handling, missing data policy, precision, rounding, temporal safety, and known limitations.

## Daily Equity and Drawdown

Daily equity is extracted from end-of-business-date `candidate_current.total_equity` after execution and current valuation refresh.

Key values:

| Date | Equity | Cash | Market value | Cumulative return | Drawdown |
|---|---:|---:|---:|---:|---:|
| 2026-06-17 | 1,018,800 | 231,200 | 787,600 | +1.88% | 0.00% |
| 2026-06-29 | 932,500 | 625,500 | 307,000 | -6.75% | -8.470749901845308% |
| 2026-07-14 | 955,100 | 750,100 | 205,000 | -4.49% | -6.252453867294856% |

Maximum drawdown:

```text
peak_date = 2026-06-17
bottom_date = 2026-06-29
drawdown_amount = -86,300
drawdown_rate = -0.08470749901845308
recovery_date = MISSING within the 20BD window
```

## Execution Notional and Turnover

Execution counts are taken from the 20BD summary and run-scoped `historical_fill_authority.json` files.

Execution notional is derived from daily cash effects on execution-equivalent days:

| Date | Side | Count | Cash effect | Execution notional |
|---|---:|---:|---:|---:|
| 2026-06-17 | BUY | 5 | -768,800 | 768,800 |
| 2026-06-18 | SELL | 1 | +36,600 | 36,600 |
| 2026-06-19 | SELL | 2 | +135,100 | 135,100 |
| 2026-06-22 | SELL | 2 | +222,600 | 222,600 |
| 2026-06-30 | SELL | 2 | +124,600 | 124,600 |

Aggregate:

```text
total_execution_notional = 1,287,700
average_equity = 954,850
turnover = 1.3485887835785726
```

Warnings:

- `EXECUTION_NOTIONAL_DERIVED_FROM_RUN_SCOPED_CASH_EFFECTS`
- `ORDER_DETAIL_OPTIONAL_MISSING`
- `FEE_TAX_NOT_AVAILABLE`

No per-symbol SELL notional was inferred when multiple symbols executed on the same day.

## Symbol-level PnL

Usable symbol-level PnL is partial:

Open unrealized PnL from final current positions:

| Symbol | Unrealized PnL | Status |
|---|---:|---|
| 89180 | 0 | `DERIVABLE_PARTIAL` |
| 45640 | 6,400 | `DERIVABLE_PARTIAL` |

Realized PnL groups:

| Date | Symbols | Realized PnL group | Status |
|---|---|---:|---|
| 2026-06-18 | 81050 | -4,600 | `DERIVABLE_PARTIAL` |
| 2026-06-19 | 66590, 81050 | -27,000 | `DERIVABLE_PARTIAL` |
| 2026-06-22 | 43780, 66590 | -27,400 | `DERIVABLE_PARTIAL` |
| 2026-06-30 | 45640, 89180 | +7,700 | `DERIVABLE_PARTIAL` |

Exact symbol-level realized PnL is not emitted for multi-symbol SELL days because stable lot/fill-level allocation evidence is absent. The missing data policy is explicit: no guessed split and no zero-fill.

## Missing or Partial Metrics

Benchmark metrics:

```text
MISSING
```

Reason:

```text
No approved run-scoped benchmark index return evidence is present, and Phase20-C does not fetch external benchmark data.
```

Sector metrics:

```text
MISSING
```

Reason:

```text
No sector mapping / sector return evidence is present in the run-scoped evidence.
```

Lot-level realized metrics:

```text
MISSING
```

Reason:

```text
No stable lot ID / fill-level realized slice evidence is present.
```

Symbol-level PnL:

```text
DERIVABLE_PARTIAL
```

Reason:

```text
Final open unrealized PnL is exact, but closed realized PnL cannot be fully allocated by symbol for multi-symbol SELL days.
```

## Prohibited Actions Check

Not performed:

- Runtime change
- AI change
- Opportunity change
- Strategy change
- PM change
- Risk change
- Training
- Calibration
- Validation
- Accepted Generation change
- Broker connection
- Runtime State mutation
- Long Historical Smoke
- Full Backtest
- Benchmark external fetch
- Sector external fetch

## Validation

Validation performed:

```text
json validation
git diff --check
```

No Historical Smoke, Broker connection, Training, Calibration, Validation, or long-running test was executed.

## Final Judgment

```text
PHASE20_C_BASELINE_EXTRACTION_COMPLETE_WITH_DERIVABLE_GAPS
```
