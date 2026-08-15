# Phase30-A Candidate — Market Regime Performance Attribution Audit

## Task

Phase30-A candidate

Mode: READ-ONLY audit.

Strategy, Runtime, Config, Model, and Threshold were not changed. No fresh-run, resume, replay, or recovery was executed. Historical-only strategy logic was not introduced.

## Scope

Requested scope: 4-year Historical run.

Local artifact reality: no completed 4-year Historical run artifact was found in `reports/runtime_tests/runs`. The longest available local run was used:

- Target run: `runtime-test-historical-extended-smoke-20260814T131647480030Z`
- Audited dates: `2022-08-10` to `2023-07-25`
- Audited business days: `235`

This report is therefore a partial long-run attribution, not a full 4-year judgment.

## Inputs

Regime authority:

- `daily/<date>/strategy/market_context.json`
- Source field: `trend_regime`

Mapping:

- `BULL` -> `BULL`
- `BEAR` -> `BEAR`
- `RANGE` -> `RANGE`
- any other `trend_regime` -> `UNKNOWN`

Raw trend regime counts:

| Raw Regime | Business Days |
| --- | ---: |
| `BULL` | 104 |
| `RANGE` | 45 |
| `BEAR` | 33 |
| `RECOVERY` | 40 |
| `CORRECTION` | 13 |

Because the user requested only `BULL / BEAR / RANGE / UNKNOWN`, `RECOVERY` and `CORRECTION` were grouped under `UNKNOWN`.

## Method

Daily portfolio state was read from:

- `daily/<date>/current_valuation_refresh/current_valuation_manifest.json`

Action counts were read from:

- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/strategy/position_management.json`

Entry forward returns were calculated from BUY fills and future PIT close prices in each daily market refresh artifact:

- `daily/<date>/execution/fills.json`
- `daily/<date>/market_refresh/inputs/historical_asof/<date>/raw_normalized/jquants/equities_bars_daily/data.parquet`

Limitations:

- Exact realized PnL contribution is `NOT_AVAILABLE`; fill observability has cash flow and notional but not exact realized PnL.
- Unrealized contribution uses `current_valuation_refresh` position `unrealized_pnl`.
- Average holding days is inferred from first position appearance inside this audited run because `acquired_at` is blank in current-position adapter rows.
- Profit giveback is inferred as symbol-level peak unrealized PnL minus current unrealized PnL inside this audited run.

## Regime Summary

| Regime | Days | Return | Daily Mean | Win Rate | Max DD | Avg Cash | Avg Exposure | BUY_NEW | ADD | HOLD | REDUCE | EXIT | Avg Hold Days | Profit Giveback | Entry 5BD | Entry 10BD | Entry 20BD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL | 104 | -7.14% | -0.064% | 48.54% | -18.64% | 384,392 | 61.01% | 109 | 212 | 364 | 122 | 65 | 76.66 | 4,561,336 | 0.00% | 0.81% | -1.61% |
| RANGE | 45 | +7.19% | +0.179% | 48.89% | -17.04% | 410,634 | 57.20% | 48 | 65 | 151 | 37 | 29 | 66.81 | 1,651,370 | -3.40% | -1.61% | -5.74% |
| BEAR | 33 | +6.07% | +0.197% | 54.55% | -7.18% | 514,974 | 46.51% | 23 | 57 | 64 | 16 | 24 | 56.03 | 795,650 | -3.44% | +0.27% | +11.30% |
| UNKNOWN | 53 | -2.81% | -0.021% | 43.40% | -20.16% | 413,029 | 57.85% | 55 | 68 | 186 | 42 | 42 | 75.41 | 2,485,190 | -4.79% | -3.84% | -5.86% |

## Interpretation

In the available partial run, the portfolio did not make its profits in `BULL`. The largest regime-level loss was in `BULL`, despite the highest average exposure and the highest BUY/ADD activity.

`RANGE` and `BEAR` were positive at the portfolio level. However, `RANGE` entries had weak forward returns, especially 20BD forward. This suggests RANGE profit was not necessarily driven by new entry quality; it may have come from existing holdings, timing, or unrealized contribution already present in the portfolio.

`BEAR` had the lowest exposure and best max drawdown. Its entry 20BD forward return was positive, but sample size was small (`20` entries), so this is evidence for review rather than a stable conclusion.

`UNKNOWN` was negative and had the worst max drawdown. Because `UNKNOWN` includes both `RECOVERY` and `CORRECTION`, it should be split in a follow-up if Phase30 uses this result for design.

## Transition Summary

| Transition | Count | Avg Pre 20BD Return | Avg Post 20BD Return | Pre BUY | Post BUY | Pre HOLD | Post HOLD | Pre EXIT | Post EXIT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL -> RANGE | 10 | -2.84% | +1.40% | 50.3 | 48.4 | 51.2 | 65.1 | 13.2 | 13.8 |
| BULL -> BEAR | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| RANGE -> BULL | 2 | -7.83% | -0.05% | 40.0 | 47.0 | 26.0 | 67.5 | 14.5 | 16.5 |
| RANGE -> BEAR | 2 | +6.49% | -0.51% | 46.0 | 49.0 | 61.5 | 44.5 | 13.5 | 13.0 |
| BEAR -> RANGE | 3 | -0.28% | -0.09% | 45.0 | 59.3 | 47.7 | 60.7 | 18.0 | 11.7 |
| BEAR -> BULL | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

Transition observations:

- `RANGE -> BEAR` is the clearest loss-of-profit transition in this sample: pre-window was positive and post-window turned negative.
- `BULL -> RANGE` is mixed; average post-window was positive, but individual events vary widely.
- Direct `BULL -> BEAR` and `BEAR -> BULL` did not occur under the requested exact transition set.

## Artifacts

Generated reports:

- `reports/phase30_a_candidate_market_regime_performance_attribution_audit/summary.json`
- `reports/phase30_a_candidate_market_regime_performance_attribution_audit/regime_summary.csv`
- `reports/phase30_a_candidate_market_regime_performance_attribution_audit/transition_summary.csv`
- `reports/phase30_a_candidate_market_regime_performance_attribution_audit/daily_regime_attribution.csv`
- `reports/phase30_a_candidate_market_regime_performance_attribution_audit/entry_forward_returns.csv`

## Primary Finding

For the available local long-run artifact, profits were made mainly in `RANGE` and `BEAR`, while losses were concentrated in `BULL` and `UNKNOWN`.

The most suspicious transition is `RANGE -> BEAR`, where the pre-transition 20BD return was positive and the post-transition 20BD return turned negative. The most suspicious regime-level behavior is high BUY/ADD activity and high exposure during `BULL` while portfolio return was negative.

## Validation

- `summary.json` parse: PASS
- `git diff --check`: PASS
- Runtime mutation: NO
- Strategy change: NO
- Threshold tuning: NO
- Historical-only logic: NO

## Next Step

Before making any Phase30 strategy design decision, rerun this attribution against the true completed 4-year Historical artifact, or provide the target run ID if it exists outside the current workspace.

Recommended next audit:

`Phase30-A1 — RECOVERY / CORRECTION Split Attribution and BULL Entry Loss Concentration Audit`
