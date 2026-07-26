# Phase20-E Performance Diagnosis and Attribution Report

## Executive Summary

Phase20-E diagnoses the 20BD Baseline Run performance using the Phase20-C Performance Baseline and Phase20-D Trade / PM Attribution Baseline.

Target run:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

Runtime judgment:

```text
PASS
```

Final judgment:

```text
PHASE20_E_PERFORMANCE_DIAGNOSIS_COMPLETE_WITH_DERIVABLE_GAPS
```

This is a Strategy Performance diagnosis only. It is not a Runtime failure diagnosis. This report does not propose improvements or prescribe changes.

## Required Documents Read

Read and applied:

- `docs/phase_reports/phase20_d_trade_and_position_management_attribution_baseline.md`
- `docs/phase_reports/phase20_c_read_only_performance_baseline_extraction.md`
- `docs/phase_reports/phase20_b_performance_metric_benchmark_experiment_contract.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`

Contract version:

```text
phase20_b_performance_metric_contract.v1
```

All MFE, MAE, post-decision return, post-sale return, loss avoided, and profit missed fields are:

```text
POST_HOC_ATTRIBUTION_ONLY
```

They are not Runtime, Training, Calibration, Validation, Accepted Generation, AI, PM, or Risk authority.

## Generated Artifacts

Generated diagnosis artifacts:

```text
reports/phase_reports/phase20_e_performance_diagnosis_and_attribution_report.json
reports/performance_diagnosis/runtime-test-historical-smoke-20260721T213848054826Z/performance_diagnosis.json
reports/performance_diagnosis/runtime-test-historical-smoke-20260721T213848054826Z/buy_performance_diagnosis.json
reports/performance_diagnosis/runtime-test-historical-smoke-20260721T213848054826Z/buy_performance_diagnosis.csv
reports/performance_diagnosis/runtime-test-historical-smoke-20260721T213848054826Z/pm_performance_diagnosis.json
reports/performance_diagnosis/runtime-test-historical-smoke-20260721T213848054826Z/drawdown_diagnosis.json
```

## Performance Summary

| Metric | Value | Status |
|---|---:|---|
| Initial Equity | 1,000,000 | `AVAILABLE` |
| Final Equity | 955,100 | `AVAILABLE` |
| Total Return | -44,900 | `AVAILABLE` |
| Return Rate | -4.49% | `AVAILABLE` |
| Maximum Drawdown | -86,300 / -8.470749901845308% | `DERIVABLE_EXACT` |
| Turnover | 1.3485887835785726 | `DERIVABLE_EXACT` |
| Execution Count | 12 | `AVAILABLE` |
| BUY Count | 5 | `AVAILABLE` |
| SELL Count | 7 | `AVAILABLE` |
| Final Position Count | 2 | `DERIVABLE_EXACT` |
| Average Position Count | 2.4 | `DERIVABLE_EXACT` |
| Final Cash Utilization | 0.2146372107632709 | `DERIVABLE_EXACT` |
| Average Cash Utilization | 0.32177290456454166 | `DERIVABLE_EXACT` |

Performance decomposition:

| Component | Value | Status |
|---|---:|---|
| Closed realized PnL | -51,300 | `AVAILABLE` aggregate |
| Open unrealized PnL | +6,400 | `AVAILABLE` |
| Total PnL | -44,900 | `AVAILABLE` |

## BUY Performance Diagnosis

BUY rows are reconstructed from Phase20-D BUY attribution and run-scoped valuation evidence. Final return for closed symbols uses the last available valuation before or at exit. Exact per-symbol realized PnL remains partial for closed symbols where multi-symbol SELL days occurred.

| Symbol | Opp Rank | Candidate Score | Opportunity Score | Confidence | Capital | Open/Closed | Final Return | MFE | MAE | Status |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| 89180 | 2 | 0.99904408 | 0.55725565 | 0.98 | 154,000 | OPEN | 0.00% | 10.00% | 0.00% | `DERIVABLE_EXACT` |
| 45640 | 3 | 0.99109192 | 0.40360326 | 0.96 | 161,500 | OPEN | 5.263157894736842% | 10.526315789473683% | -5.263157894736842% | `DERIVABLE_EXACT` |
| 81050 | 5 | 0.96535396 | 0.23910165 | 0.92 | 164,800 | CLOSED | -17.475728155339805% | -7.281553398058252% | -17.475728155339805% | `DERIVABLE_PARTIAL` |
| 66590 | 6 | 0.95588506 | 0.1926104 | 0.90 | 159,500 | CLOSED | -7.2727272727272725% | 5.454545454545454% | -7.2727272727272725% | `DERIVABLE_PARTIAL` |
| 43780 | 7 | 0.94898282 | 0.12884552 | 0.88 | 129,000 | CLOSED | -12.558139534883722% | -0.6201550387596899% | -12.558139534883722% | `DERIVABLE_PARTIAL` |

BUY aggregate:

| Metric | Value |
|---|---:|
| BUY count | 5 |
| Open count | 2 |
| Closed count | 3 |
| Average final return | -6.408687413642791% |
| Average MFE | 3.615830561440239% |
| Average MAE | -8.513950571537529% |

Opportunity rank distribution among executed BUYs:

| Opportunity Rank | Count | Symbols | Avg Final Return | Avg MFE | Avg MAE |
|---:|---:|---|---:|---:|---:|
| 2 | 1 | 89180 | 0.00% | 10.00% | 0.00% |
| 3 | 1 | 45640 | 5.263157894736842% | 10.526315789473683% | -5.263157894736842% |
| 5 | 1 | 81050 | -17.475728155339805% | -7.281553398058252% | -17.475728155339805% |
| 6 | 1 | 66590 | -7.2727272727272725% | 5.454545454545454% | -7.2727272727272725% |
| 7 | 1 | 43780 | -12.558139534883722% | -0.6201550387596899% | -12.558139534883722% |

No Rank 1 BUY execution exists in the 20BD run evidence.

## HOLD / ADD Diagnosis

PM counts:

| Decision | Count | Exact symbol rows | Partial rows | Avg Return After Decision | Avg MFE | Avg MAE |
|---|---:|---:|---:|---:|---:|---:|
| HOLD | 30 | 20 | 8 | 2.134502923976608% | 7.228070175438597% | -1.8026315789473686% |
| ADD | 9 | 0 | 8 | `MISSING` | `MISSING` | `MISSING` |

HOLD post-hoc values are available only where symbol-level HOLD assignment is derivable. ADD post-hoc values remain `MISSING` because mixed HOLD/ADD days lack per-symbol PM decision body evidence.

All fields in this section are:

```text
POST_HOC_ATTRIBUTION_ONLY
```

## REDUCE / EXIT Diagnosis

| Metric | Value |
|---|---:|
| REDUCE count | 4 |
| EXIT count | 3 |
| Exact rows | 1 |
| Partial rows | 6 |
| Average post-sale return | `MISSING` |
| Loss avoided available count | 0 |
| Profit missed available count | 0 |

REDUCE / EXIT detail:

| Date | Symbol | Decision | Quantity | Remaining | Execution Price | Realized PnL | Group Realized PnL | Status |
|---|---|---|---:|---:|---:|---:|---:|---|
| 2026-06-18 | 81050 | REDUCE | 200 | 600 | 183 | -4,600 | -4,600 | `DERIVABLE_EXACT` |
| 2026-06-19 | 81050 | EXIT | 600 | 0 | `MISSING` | `MISSING` | -27,000 | `DERIVABLE_PARTIAL` |
| 2026-06-19 | 66590 | REDUCE | 700 | 2,200 | `MISSING` | `MISSING` | -27,000 | `DERIVABLE_PARTIAL` |
| 2026-06-22 | 43780 | EXIT | 200 | 0 | `MISSING` | `MISSING` | -27,400 | `DERIVABLE_PARTIAL` |
| 2026-06-22 | 66590 | EXIT | 2,200 | 0 | `MISSING` | `MISSING` | -27,400 | `DERIVABLE_PARTIAL` |
| 2026-06-30 | 89180 | REDUCE | 7,700 | 7,700 | `MISSING` | `MISSING` | +7,700 | `DERIVABLE_PARTIAL` |
| 2026-06-30 | 45640 | REDUCE | 2,100 | 6,400 | `MISSING` | `MISSING` | +7,700 | `DERIVABLE_PARTIAL` |

Loss avoided and profit missed were not calculated where the required post-sale per-symbol price/lot evidence is missing.

## Position Contribution

Position contribution is `DERIVABLE_PARTIAL` because exact per-symbol realized PnL for multi-symbol SELL days is unavailable.

Open positions:

| Symbol | Quantity | Average Price | Current Price | Market Value | Unrealized PnL |
|---|---:|---:|---:|---:|---:|
| 89180 | 7,700 | 10 | 10 | 77,000 | 0 |
| 45640 | 6,400 | 19 | 20 | 128,000 | +6,400 |

Closed realized groups:

| Date | Symbols | Realized PnL Group | Status |
|---|---|---:|---|
| 2026-06-18 | 81050 | -4,600 | `DERIVABLE_PARTIAL` |
| 2026-06-19 | 66590, 81050 | -27,000 | `DERIVABLE_PARTIAL` |
| 2026-06-22 | 43780, 66590 | -27,400 | `DERIVABLE_PARTIAL` |
| 2026-06-30 | 45640, 89180 | +7,700 | `DERIVABLE_PARTIAL` |

Aggregate contribution:

| Component | PnL |
|---|---:|
| Open unrealized PnL | +6,400 |
| Closed realized PnL | -51,300 |
| Total PnL | -44,900 |

## Drawdown Diagnosis

Drawdown contract uses mark-to-market equity, including open positions.

| Metric | Value |
|---|---:|
| Peak Date | 2026-06-17 |
| Bottom Date | 2026-06-29 |
| Recovery | `MISSING` |
| Unrecovered within 20BD | true |
| Drawdown period business days | 9 |
| Equity at peak | 1,018,800 |
| Equity at bottom | 932,500 |
| Cash at peak | 231,200 |
| Cash at bottom | 625,500 |
| Market value at peak | 787,600 |
| Market value at bottom | 307,000 |
| Average cash ratio during drawdown | 0.5450411324629922 |
| Average cash utilization during drawdown | 0.45495886753700776 |
| Average gross exposure during drawdown | 0.45495886753700776 |
| Max position count during drawdown | 5 |
| Min position count during drawdown | 2 |

Positions at peak:

```text
89180, 45640, 81050, 66590, 43780
```

Positions at bottom:

```text
89180, 45640
```

This section describes what happened during the drawdown window. It does not assign causal blame and does not propose any action.

## Performance Distribution

| Distribution | Value | Status |
|---|---:|---|
| Profit symbols by final / last observed return | 1 | `DERIVABLE_PARTIAL` |
| Loss symbols by final / last observed return | 3 | `DERIVABLE_PARTIAL` |
| Neutral symbols by final / last observed return | 1 | `DERIVABLE_PARTIAL` |
| Open PnL | +6,400 | `AVAILABLE` |
| Closed PnL | -51,300 | `AVAILABLE` aggregate |

Execution day distribution:

| Date | Side | Execution Count | Execution Notional |
|---|---|---:|---:|
| 2026-06-17 | BUY | 5 | 768,800 |
| 2026-06-18 | SELL | 1 | 36,600 |
| 2026-06-19 | SELL | 2 | 135,100 |
| 2026-06-22 | SELL | 2 | 222,600 |
| 2026-06-30 | SELL | 2 | 124,600 |

PM distribution:

| Decision | Count |
|---|---:|
| HOLD | 30 |
| ADD | 9 |
| REDUCE | 4 |
| EXIT | 3 |

BUY rank distribution:

| Opportunity Rank | Count |
|---:|---:|
| 2 | 1 |
| 3 | 1 |
| 5 | 1 |
| 6 | 1 |
| 7 | 1 |

## Diagnosis Summary

Confirmed facts:

- Runtime judgment is PASS while Strategy Performance is negative over the 20BD baseline.
- Total return is -44,900 (-4.49%).
- Aggregate realized PnL is -51,300 and open unrealized PnL is +6,400.
- Maximum drawdown is -86,300 from the 2026-06-17 peak to the 2026-06-29 bottom.
- The drawdown was not recovered within the 20BD window.
- BUY executions are 5 and SELL executions are 7.
- PM counts are HOLD 30 / ADD 9 / REDUCE 4 / EXIT 3.
- Open positions contribute +6,400 unrealized PnL; closed realized PnL is -51,300 at aggregate level.

Evidence gaps:

- Lot-level realized PnL is missing.
- Benchmark return evidence is missing.
- Sector mapping and sector return evidence are missing.
- PM per-symbol decision body is missing for most 20BD dates.
- Multi-symbol SELL per-symbol execution price and realized PnL splits are missing.
- Fees, tax, and slippage evidence is not available.

Additional evidence needed for more granular diagnosis:

- Stable lot IDs and fill-level realized PnL.
- Per-symbol PM decision body snapshots copied into run evidence.
- Approved benchmark index return evidence.
- Sector mapping and sector return evidence.
- Fee, tax, and slippage fields in execution evidence.

## Prohibited Actions Check

Not performed:

- AI change
- Opportunity change
- PM change
- Risk change
- Runtime change
- Training
- Calibration
- Validation
- Accepted Generation change
- Broker connection
- Runtime State mutation
- Long Historical
- Full Backtest

This report contains no recommendation to change EXIT, ADD, AI, Opportunity, Risk, PM, or Runtime behavior.

## Validation

Validation performed:

```text
json validation
git diff --check
```

No Historical Smoke, Broker connection, Training, Calibration, Validation, full backtest, Runtime mutation, or code change was performed.

## Final Judgment

```text
PHASE20_E_PERFORMANCE_DIAGNOSIS_COMPLETE_WITH_DERIVABLE_GAPS
```
