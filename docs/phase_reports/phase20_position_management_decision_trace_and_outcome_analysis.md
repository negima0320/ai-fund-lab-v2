# Phase20-R Position Management Decision Trace and Outcome Analysis

## Status

PHASE20_R_POSITION_MANAGEMENT_DECISION_TRACE_AND_OUTCOME_ANALYSIS_COMPLETE

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260722T082906704807Z`
- Runtime judgment: PASS
- Work type: read-only post-hoc analysis
- No implementation change, threshold change, Runtime change, training, calibration, broker access, or full historical smoke was executed.
- Decision-time evidence and post-decision outcome are separated. Future prices are used only as `POST_HOC_ANALYSIS_ONLY`.

## Evidence Sources

- Run evidence: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260722T082906704807Z/`
- PM decisions: `.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json`
- PM inference scores: `.runtime/runtime_state/position_management/<business_date>/position_management_inference.parquet`
- Holding snapshot: `.runtime/runtime_state/position_management/<business_date>/current_holdings_snapshot.csv`
- Opportunity context: `.runtime/runtime_state/position_management/<business_date>/position_management_opportunity_context.csv`
- Decision-time feature input: `.runtime/operations/feature_artifacts/<business_date>/position_feature_input.parquet`
- Post-hoc close price source: `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`

Detailed per-symbol/per-date traces are written to:

`reports/phase_reports/phase20_position_management_decision_trace_and_outcome_analysis.json`

## Decision Reconstruction

All PM decisions in the 20BD run were reconstructed.

| Action | Count |
|---|---:|
| HOLD | 23 |
| REDUCE | 10 |
| EXIT | 9 |
| ADD | 2 |

Dominant cause reconstruction follows the implementation decision order:

1. EXIT rules
2. REDUCE rules
3. ADD rules
4. HOLD rules

| Dominant Cause | Count |
|---|---:|
| EXIT_BY_HARD_STOP | 7 |
| EXIT_BY_TREND_AND_EDGE_BREAK | 2 |
| REDUCE_BY_WEAK_HOLD_SCORE | 7 |
| REDUCE_BY_DRAWDOWN_WARNING | 3 |
| ADD_BY_STRONG_TREND_AND_RANK | 2 |
| HOLD_BY_STRONG_CONTINUATION | 5 |
| HOLD_BY_PARTIAL_CONTINUATION | 18 |
| HOLD_BY_FALLBACK | 0 |

## Decision Trace Fields

For each `symbol` / `business_date`, the JSON report contains:

- `current_return`
- `peak_return`
- `drawdown_from_peak`
- `holding_days`
- `expected_edge_score`
- `buy_rank`
- `downside_risk_score`
- `risk_guard_status`
- `price_momentum_return_5d`
- `price_momentum_return_20d`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `volume_momentum_ratio_5d`
- `volatility_return_std_20d`

The score components are also included per decision:

- `trend_score`
- `opportunity_score`
- `profit_score`
- `risk_penalty`
- `hold_score`
- `exit_score`
- `reduce_score`
- `add_score`

Trigger booleans are recorded for EXIT / REDUCE / ADD / HOLD using the Phase20-Q confirmed deterministic PM rule order.

## Post-decision Outcome

Post-decision returns are calculated from the close on the decision date to the next 1 / 2 / 3 / 5 trading days. This is strictly post-hoc and was not mixed into decision-time evidence.

### By Action

| Action | Count | 1BD Mean | 2BD Mean | 3BD Mean | 5BD Mean |
|---|---:|---:|---:|---:|---:|
| ADD | 2 | -4.76% | 0.25% | -2.13% | -9.52% |
| EXIT | 9 | 2.95% | 0.74% | 3.75% | 0.09% |
| HOLD | 23 | -1.05% | -1.77% | -1.44% | -1.94% |
| REDUCE | 10 | 0.61% | 0.30% | -1.62% | 3.07% |

### By Dominant Cause

| Dominant Cause | Count | 1BD Mean | 2BD Mean | 3BD Mean | 5BD Mean |
|---|---:|---:|---:|---:|---:|
| EXIT_BY_HARD_STOP | 7 | 4.27% | 2.47% | 6.11% | 1.43% |
| EXIT_BY_TREND_AND_EDGE_BREAK | 2 | -1.68% | -5.33% | -3.36% | -3.92% |
| REDUCE_BY_WEAK_HOLD_SCORE | 7 | 0.56% | 1.10% | -1.22% | 5.61% |
| REDUCE_BY_DRAWDOWN_WARNING | 3 | 0.73% | -1.57% | -2.57% | -5.81% |
| HOLD_BY_STRONG_CONTINUATION | 5 | -2.71% | -7.62% | -8.29% | -6.95% |
| HOLD_BY_PARTIAL_CONTINUATION | 18 | -0.58% | -0.14% | 0.57% | -0.26% |
| ADD_BY_STRONG_TREND_AND_RANK | 2 | -4.76% | 0.25% | -2.13% | -9.52% |

## Notable Outcome Counts

Significant move threshold: 5%.

- EXIT後2〜5営業日で大幅反発した件数: 2
- REDUCE後に1〜5営業日内で反発した件数: 8
- HOLD後に1〜5営業日内で大幅下落した件数: 16
- fallback HOLD: 0件。strong HOLDとの成績差は比較不能。
- strong HOLD: 5件。5BD平均 -6.95%、positive率 0.00。
- REDUCE_BY_WEAK_HOLD_SCORE: 7件。5BD平均 5.61%、positive率 57.14%。
- Other REDUCE: 3件。5BD平均 -5.81%、positive率 0.00%。

## 66590 Case Study

Decision-time validity and post-hoc outcome are separated below.

| Date | Action | Dominant Cause | Current Return | Drawdown | Hold | Exit | Reduce | 1BD | 2BD | 3BD | 5BD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-06-16 | REDUCE | REDUCE_BY_WEAK_HOLD_SCORE | -1.72% | -1.72% | 0.4128 | 0.5754 | 0.2412 | 5.45% | 0.00% | -7.27% | 16.36% |
| 2026-06-17 | REDUCE | REDUCE_BY_WEAK_HOLD_SCORE | -5.17% | -5.17% | 0.3827 | 0.6779 | 0.3623 | -5.17% | -12.07% | -8.62% | 8.62% |
| 2026-06-18 | HOLD | HOLD_BY_PARTIAL_CONTINUATION | 0.00% | 0.00% | 0.5075 | 0.5521 | 0.3000 | -7.27% | -3.64% | 16.36% | 36.36% |
| 2026-06-19 | REDUCE | REDUCE_BY_WEAK_HOLD_SCORE | -5.17% | -5.17% | 0.2029 | 0.7154 | 0.3875 | 3.92% | 25.49% | 23.53% | 27.45% |
| 2026-06-22 | EXIT | EXIT_BY_HARD_STOP | -12.07% | -12.07% | 0.0322 | 0.9148 | 0.6189 | 20.75% | 18.87% | 41.51% | 20.75% |

Existing normalized J-Quants source prices for 66590:

| Date | Close |
|---|---:|
| 2026-06-16 | 55 |
| 2026-06-17 | 58 |
| 2026-06-18 | 55 |
| 2026-06-19 | 51 |
| 2026-06-22 | 53 |
| 2026-06-23 | 64 |
| 2026-06-24 | 63 |
| 2026-06-25 | 75 |

The request mentioned `2026-06-24 close 75`. The existing normalized source available in this repository shows `2026-06-24 close 63` and `2026-06-25 close 75`. This report does not overwrite evidence by assumption.

Decision-time interpretation:

- 2026-06-16 / 2026-06-17 / 2026-06-19 REDUCE decisions were driven by weak hold score while trend or expected edge remained alive.
- 2026-06-18 HOLD was partial continuation, not fallback HOLD.
- 2026-06-22 EXIT was driven by hard stop first; profit retention break and trend/edge break were secondary triggers.
- The sharp post-EXIT rebound is a post-hoc outcome, not evidence that was available to the PM decision at 2026-06-22 decision time.

## Evidence and Observability Gaps

- `current_holdings_snapshot.csv` and `position_feature_input.parquet` can differ on same-day current price/current return. PM inference is score-consistent with PM feature input artifacts, but authority should be made clearer before any threshold review.
- fallback HOLD did not occur in this run, so fallback HOLD quality cannot be evaluated.
- REDUCE quantity is not decided by PM. PM emits reduce intensity; Sell Planning owns tradable quantity.
- Post-hoc outcomes are close-to-close and do not include intraday MFE/MAE.
- Existing price evidence contradicts the requested 66590 2026-06-24 close value.

## Required Conclusions

- PM_EXIT_RULE_REVIEW_REQUIRED
- PM_REDUCE_RULE_REVIEW_REQUIRED
- PM_HOLD_RULE_ACCEPTABLE
- PM_OBSERVABILITY_IMPROVEMENT_REQUIRED
- THRESHOLD_CHANGE_NOT_READY

Rationale:

- EXIT review is required because 2 EXIT decisions were followed by 2〜5BD rebounds >= 5%, including the 66590 hard-stop EXIT.
- REDUCE review is required because 8 REDUCE decisions rebounded within 1〜5BD and REDUCE_BY_WEAK_HOLD_SCORE had positive 5BD mean outcome.
- HOLD is acceptable for this phase because no fallback HOLD occurred and HOLD weaknesses are observable but not sufficient for threshold change readiness.
- Observability improvement is required because price authority differences and missing fallback cases block clean rule-quality attribution.
- Threshold change is not ready because this phase is diagnostic, the evidence is one run, and identified gaps must be closed before proposing parameter changes.
