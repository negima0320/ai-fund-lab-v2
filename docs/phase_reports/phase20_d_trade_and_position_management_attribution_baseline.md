# Phase20-D Trade and Position Management Attribution Baseline

## Executive Summary

Phase20-D reconstructed the trade and Position Management attribution baseline for the 20BD Baseline Run:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

Final judgment:

```text
PHASE20_D_TRADE_AND_PM_ATTRIBUTION_COMPLETE_WITH_DERIVABLE_GAPS
```

Runtime judgment remains:

```text
PASS
```

Performance remains:

```text
-4.49%
```

This phase did not perform cause analysis and did not propose improvements. It only links available decisions and post-hoc outcomes to evidence.

## Required Documents Read

Read and applied:

- `docs/phase_reports/phase20_c_read_only_performance_baseline_extraction.md`
- `docs/phase_reports/phase20_b_performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase20_a_performance_baseline_and_attribution_evidence_inventory.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`

Contract version:

```text
phase20_b_performance_metric_contract.v1
```

## Generated Artifacts

Generated attribution artifacts:

```text
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/trade_lifecycle.json
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/trade_lifecycle.csv
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/buy_attribution.json
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/buy_attribution.csv
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/pm_attribution.json
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/pm_attribution.csv
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/reduce_exit_attribution.json
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/reduce_exit_attribution.csv
```

Generated phase report JSON:

```text
reports/phase_reports/phase20_d_trade_and_position_management_attribution_baseline.json
```

## Authority and Scope

Primary authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T213848054826Z-20260721T221640818568Z/summary.json
```

BUY score detail authority:

```text
.runtime/runtime_state/buy_ai/2026-06-17/candidate_decisions.json
.runtime/runtime_state/buy_ai/2026-06-17/opportunity_rankings.json
```

The BUY score artifacts are generation-bound and business-date specific. They are used only for detail fields, not for run event counts.

PM count authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/daily/<DATE>/sell_planning/position_management_evidence.json
```

REDUCE/EXIT linkage authority:

```text
summary.reduce_exit.items
```

Post-hoc valuation authority:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/daily/<DATE>/current_valuation_refresh/current_valuation_manifest.json
```

All post-hoc fields are classified as:

```text
POST_HOC_ATTRIBUTION_ONLY
```

They are not Runtime, AI, PM, Risk, Training, Calibration, Validation, or Accepted Generation authority.

## BUY Decision Table

| Symbol | Date | BUY price | Quantity | Capital allocated | Opportunity rank | Candidate score | Opportunity score | Confidence | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 89180 | 2026-06-17 | 10 | 15,400 | 154,000 | 2 | 0.99904408 | 0.55725565 | 0.98 | `DERIVABLE_EXACT` |
| 45640 | 2026-06-17 | 19 | 8,500 | 161,500 | 3 | 0.99109192 | 0.40360326 | 0.96 | `DERIVABLE_EXACT` |
| 81050 | 2026-06-17 | 206 | 800 | 164,800 | 5 | 0.96535396 | 0.23910165 | 0.92 | `DERIVABLE_EXACT` |
| 66590 | 2026-06-17 | 55 | 2,900 | 159,500 | 6 | 0.95588506 | 0.1926104 | 0.90 | `DERIVABLE_EXACT` |
| 43780 | 2026-06-17 | 645 | 200 | 129,000 | 7 | 0.94898282 | 0.12884552 | 0.88 | `DERIVABLE_EXACT` |

Generation:

```text
phase19_aq_accepted_generation_641e6e313543f013
```

BUY reason is available in `buy_attribution.json` and `buy_attribution.csv`. BUY execution price uses post-execution Current `average_price`; estimated planning price is preserved separately.

## PM Decision Table

PM decision rows were emitted to:

```text
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/pm_attribution.json
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/pm_attribution.csv
```

The table includes:

- decision date
- decision type
- symbol where derivable
- candidate symbols where symbol assignment is partial
- position size
- average cost
- unrealized PnL
- decision reason
- return after decision
- MFE
- MAE
- evidence status
- post-hoc classification

Important gap:

```text
Per-symbol PM decision bodies for the 20BD dates were not copied into run evidence, and the current shared .runtime only retains 2026-07-14 PM detail.
```

Therefore:

- REDUCE/EXIT symbol rows are reconstructed from `summary.reduce_exit.items`.
- HOLD rows are exact only when all remaining positions map to HOLD.
- Mixed HOLD/ADD days are emitted as `DERIVABLE_PARTIAL` aggregate rows with `symbol = MISSING` and `candidate_symbols` populated.
- PM `decision_reason` is `MISSING` where the PM decision body row is unavailable.

## REDUCE / EXIT Decision Table

| Date | Symbol | Decision | Quantity | Remaining quantity | Execution price | Realized PnL | Status |
|---|---|---|---:|---:|---:|---:|---|
| 2026-06-18 | 81050 | REDUCE | 200 | 600 | 183 | -4,600 | `DERIVABLE_EXACT` |
| 2026-06-19 | 81050 | EXIT | 600 | 0 | `MISSING` | `MISSING` | `DERIVABLE_PARTIAL` |
| 2026-06-19 | 66590 | REDUCE | 700 | 2,200 | `MISSING` | `MISSING` | `DERIVABLE_PARTIAL` |
| 2026-06-22 | 43780 | EXIT | 200 | 0 | `MISSING` | `MISSING` | `DERIVABLE_PARTIAL` |
| 2026-06-22 | 66590 | EXIT | 2,200 | 0 | `MISSING` | `MISSING` | `DERIVABLE_PARTIAL` |
| 2026-06-30 | 89180 | REDUCE | 7,700 | 7,700 | `MISSING` | `MISSING` | `DERIVABLE_PARTIAL` |
| 2026-06-30 | 45640 | REDUCE | 2,100 | 6,400 | `MISSING` | `MISSING` | `DERIVABLE_PARTIAL` |

Execution price and realized PnL are exact only for the single-symbol execution day. Multi-symbol execution days preserve daily group cash effect and realized PnL but do not guess a per-symbol split.

Post-sale return, loss avoided, and profit missed are emitted as post-hoc fields. Where post-sale symbol price evidence is unavailable after a full exit, the value is `MISSING`.

## Trade Lifecycle Table

Lifecycle rows were emitted to:

```text
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/trade_lifecycle.json
reports/performance_attribution/runtime-test-historical-smoke-20260721T213848054826Z/trade_lifecycle.csv
```

Reconstructed symbols:

| Symbol | BUY date | Final status | Main reconstructed lifecycle |
|---|---:|---|---|
| 89180 | 2026-06-17 | OPEN | Candidate -> Opportunity -> BUY -> HOLD/REDUCE/HOLD evidence -> Final Position |
| 45640 | 2026-06-17 | OPEN | Candidate -> Opportunity -> BUY -> HOLD/REDUCE/HOLD evidence -> Final Position |
| 81050 | 2026-06-17 | CLOSED | Candidate -> Opportunity -> BUY -> REDUCE -> EXIT -> Final Position |
| 66590 | 2026-06-17 | CLOSED | Candidate -> Opportunity -> BUY -> REDUCE -> EXIT -> Final Position |
| 43780 | 2026-06-17 | CLOSED | Candidate -> Opportunity -> BUY -> EXIT -> Final Position |

The lifecycle is evidence-linked but not complete at the per-symbol HOLD/ADD level for mixed HOLD/ADD dates.

## Position Management Summary

PM decision counts:

| Decision | Count |
|---|---:|
| HOLD | 30 |
| ADD | 9 |
| REDUCE | 4 |
| EXIT | 3 |

These counts match Phase20-A and are derived from run-scoped `position_management_evidence.json` files.

## Missing Evidence Summary

| Evidence | Status | Handling |
|---|---|---|
| PM per-symbol decision body before 2026-07-14 | `MISSING` | Do not assign mixed HOLD/ADD decisions to symbols. |
| PM decision reason rows | `MISSING` | Emit `decision_reason = MISSING`. |
| Mixed HOLD/ADD symbol assignment | `DERIVABLE_PARTIAL` | Emit aggregate rows with `candidate_symbols`. |
| Multi-symbol SELL execution price | `DERIVABLE_PARTIAL` | Preserve group notional; per-symbol price `MISSING`. |
| Multi-symbol realized PnL split | `DERIVABLE_PARTIAL` | Preserve group realized PnL; per-symbol realized PnL `MISSING`. |
| Lot-level realized PnL | `MISSING` | No lot-level attribution emitted. |
| Post-exit market price for closed symbols | `MISSING` | Post-sale return/loss avoided/profit missed remain `MISSING`. |

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

## Validation

Validation performed:

```text
json validation
git diff --check
```

No Historical Smoke, Broker connection, Training, Calibration, Validation, full backtest, Runtime mutation, or code change was performed.

## Final Judgment

```text
PHASE20_D_TRADE_AND_PM_ATTRIBUTION_COMPLETE_WITH_DERIVABLE_GAPS
```
