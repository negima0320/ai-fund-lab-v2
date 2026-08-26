# Phase31-G12 - Long-Horizon Interim System Performance Scorecard Audit

## Scope

Task type: READ-ONLY PERFORMANCE CHARACTERIZATION / SYSTEM SCORECARD.

No implementation, Strategy mutation, PM mutation, BUY/SELL tuning, threshold tuning, parameter tuning, config change, feature addition, model retraining, fresh-run, resume, replay, or Historical rerun was performed.

Target run:

`runtime-test-historical-extended-smoke-20260822T174358377089Z`

Profile:

`historical-extended-smoke`

Requested:

- start-date = `2022-10-01`
- business-days = `480`
- initial-cash = `1,000,000`

All metrics in this report are `INTERIM`.

## Evidence Eligibility

`RUN_START_DATE = 2022-10-03`

The requested start date `2022-10-01` was not a completed business day in the run evidence. The first completed business date is `2022-10-03`.

`LATEST_FULLY_COMPLETED_DATE = 2023-03-27`

`COMPLETED_BUSINESS_DAY_COUNT = 118`

`REQUESTED_BUSINESS_DAY_COUNT = 480`

`RUN_COMPLETE = NO`

`FUTURE_UNCOMPLETED_EVIDENCE_USED = NO`

Evidence source:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z/run_state.json`
- `run_state.status = RUNNING`
- `run_state.next_job = 2023-03-28:market_refresh`

The run advanced beyond the operator-visible `2023-03-22` while this audit was requested. This report uses only completed business dates listed in `run_state.completed_business_days` and does not inspect `2023-03-28` or later uncompleted dates.

## Metric Authorities

Daily equity authority:

`daily/<date>/current_valuation_refresh/valuation_projection.json`

Daily equity definition:

`equity = cash + new_total_market_value`

Daily PnL definition:

`daily_pnl(T) = equity(T) - equity(previous completed business day)`, with the first completed day measured against initial capital `1,000,000`.

Regime authority:

`daily/<date>/strategy/market_context.json / regime_state`

Realized campaign/trade PnL authority:

`daily/<date>/execution/realized_slices.json / gross_realized_pnl`, aggregated by `position_campaign_id`.

Campaign lifecycle authority:

`daily/2023-03-27/positions/position_campaigns.json`

Important limitation:

The latest `position_campaigns` campaign ids and `realized_slices` campaign ids do not intersect in this run artifact snapshot. Therefore this report does not join realized PnL to latest campaign lifecycle rows. Realized PnL, Profit Factor, Win/Loss quality, and concentration are calculated from `realized_slices` only. Holding period and PM lifecycle counts are calculated from `position_campaigns` only.

## Capital / Return Summary

`RETURN_METRICS_STATUS = INTERIM`

| Metric | Value |
|---|---:|
| INITIAL_CAPITAL | 1,000,000 |
| CURRENT_EQUITY | 1,262,240 |
| ABSOLUTE_PNL | +262,240 |
| TOTAL_RETURN_PCT | +26.22% |
| PEAK_EQUITY | 1,295,660 |
| PEAK_DATE | 2023-03-23 |
| PEAK_RETURN_PCT | +29.57% |
| CURRENT_DISTANCE_FROM_PEAK | -33,420 |
| CURRENT_DRAWDOWN_PCT | -2.58% |
| INTERIM_ANNUALIZED_RETURN_NOT_FINAL_CAGR | +64.44% |

The annualized figure is an interim descriptive estimate over 118 completed business days. It is not a final CAGR and should not be treated as long-run Production performance.

## Maximum Drawdown

| Metric | Value |
|---|---:|
| MAX_DRAWDOWN_PCT | -12.21% |
| MAX_DRAWDOWN_YEN | -157,850 |
| MDD_PEAK_DATE | 2023-02-08 |
| MDD_TROUGH_DATE | 2023-03-14 |
| CURRENT_DRAWDOWN_PCT | -2.58% |

Material drawdowns observed:

| Peak | Trough | Drawdown | Yen | Peak->Trough BD | Recovery | Trough->Recovery BD | Underwater BD |
|---|---|---:|---:|---:|---|---:|---:|
| 2022-10-06 | 2022-10-13 | -4.09% | -43,740 | 4 | 2022-11-01 | 13 | 17 |
| 2022-11-08 | 2022-11-14 | -3.91% | -43,850 | 4 | 2022-11-21 | 5 | 9 |
| 2022-11-25 | 2022-12-07 | -3.17% | -36,950 | 8 | 2022-12-15 | 6 | 14 |
| 2022-12-15 | 2022-12-20 | -4.85% | -56,590 | 3 | 2023-01-17 | 17 | 20 |
| 2023-02-08 | 2023-03-14 | -12.21% | -157,850 | 23 | 2023-03-23 | 6 | 29 |
| 2023-03-23 | 2023-03-27 | -2.58% | -33,420 | 2 | OPEN_DRAWDOWN | n/a | 2 |

`RECOVERY_METRICS_STATUS = INTERIM`

## Return / Drawdown Efficiency

`RETURN_TO_MDD_RATIO = 2.15`

Definition:

`total_return_pct / abs(max_drawdown_pct) = 26.22 / 12.21`

`INTERIM_CALMAR_LIKE_RATIO = 5.28`

Definition:

`interim annualized return estimate / abs(max_drawdown_pct) = 64.44 / 12.21`

This is a descriptive zero-RF, interim annualized-return-to-MDD estimate, not a final Production Calmar ratio.

## Daily Return Statistics

| Metric | Value |
|---|---:|
| Mean daily return | +0.207% |
| Median daily return | +0.306% |
| Daily return standard deviation | 1.386% |
| Downside deviation | 0.906% |
| Positive day rate | 59.32% |
| Negative day rate | 40.68% |
| Flat day rate | 0.00% |
| Best day | 2023-03-01 / +3.934% / +48,340 |
| Worst day | 2023-03-13 / -3.775% / -44,720 |
| Annualized Sharpe-like estimate | 2.37 |

Sharpe-like estimate uses zero risk-free rate as a descriptive assumption because no risk-free-rate authority was identified in the run evidence.

Best 5 daily returns:

| Date | Regime | PnL | Return | Exposure | Positions |
|---|---|---:|---:|---:|---:|
| 2023-03-01 | BULL | +48,340 | +3.934% | 49.55% | 11 |
| 2023-03-22 | RANGE | +47,330 | +3.827% | 73.79% | 10 |
| 2022-10-04 | RANGE | +36,730 | +3.628% | 71.72% | 7 |
| 2023-03-15 | RANGE | +34,750 | +3.061% | 74.24% | 10 |
| 2023-03-20 | CORRECTION | +26,250 | +2.168% | 71.54% | 9 |

Worst 5 daily returns:

| Date | Regime | PnL | Return | Exposure | Positions |
|---|---|---:|---:|---:|---:|
| 2023-03-13 | BULL | -44,720 | -3.775% | 34.72% | 5 |
| 2023-03-03 | BULL | -43,690 | -3.403% | 91.59% | 13 |
| 2022-11-14 | RECOVERY | -32,750 | -2.953% | 85.18% | 11 |
| 2022-12-07 | RANGE | -28,260 | -2.443% | 84.76% | 12 |
| 2022-12-19 | CORRECTION | -27,640 | -2.422% | 66.17% | 10 |

## Profit Factor

Authority:

`execution/realized_slices.json / gross_realized_pnl`, aggregated by `position_campaign_id`.

| Metric | Value |
|---|---:|
| GROSS_PROFIT | +608,350 |
| GROSS_LOSS | -350,310 |
| NET_REALIZED_PNL | +258,040 |
| PROFIT_FACTOR | 1.74 |

`NET_REALIZED_PNL` differs from portfolio `ABSOLUTE_PNL` by +4,200 because portfolio equity includes current open-market valuation and cash state, while realized slices are closed realized PnL only.

## Win / Loss Quality

Definitions:

- Winner: realized campaign aggregate PnL > 0
- Loser: realized campaign aggregate PnL < 0
- Break-even: realized campaign aggregate PnL = 0
- Payoff Ratio: average winner / abs(average loser)
- Expectancy: average realized PnL per realized campaign

| Metric | Value |
|---|---:|
| CLOSED_CAMPAIGN_COUNT | 199 |
| Winner count | 89 |
| Loser count | 96 |
| Break-even count | 14 |
| WIN_RATE | 44.72% |
| Loss rate | 48.24% |
| AVERAGE_WINNER | +6,835 |
| AVERAGE_LOSER | -3,649 |
| Median winner | +2,500 |
| Median loser | -1,385 |
| LARGEST_WINNER | +84,000 / 44440 |
| LARGEST_LOSER | -61,200 / 59350 |
| PAYOFF_RATIO | 1.87 |
| EXPECTANCY_PER_CAMPAIGN | +1,297 |

## Winner / Loser Concentration

| Metric | Value |
|---|---:|
| Top 1 Winner contribution to gross profit | 13.81% |
| Top 3 Winner contribution to gross profit | 24.97% |
| Top 5 Winner contribution to gross profit | 33.65% |
| Top 10 Winner contribution to gross profit | 50.53% |
| Largest loser contribution to gross loss | 17.47% |
| Gross Profit excluding Top 1 Winner | +524,350 |
| Gross Profit excluding Top 3 Winners | +456,450 |
| Net PnL excluding Top 1 Winner | +174,040 |
| Net PnL excluding Top 3 Winners | +106,140 |

This is concentration characterization only, not a diversification or rule recommendation.

## Holding Period Statistics

Authority:

`daily/2023-03-27/positions/position_campaigns.json`

| Metric | Value |
|---|---:|
| Closed position campaigns in latest lifecycle artifact | 160 |
| Average holding BD | 7.23 |
| Median holding BD | 4.00 |

Holding bucket distribution:

| Bucket | Campaign Count |
|---|---:|
| Same-day | 0 |
| 1BD | 0 |
| 2-5BD | 101 |
| 6-10BD | 29 |
| 11-20BD | 19 |
| 21BD+ | 11 |

PnL by holding bucket is unavailable without an unsafe join between `position_campaigns` and `realized_slices` campaign ids.

## Regime Performance

`REGIME_METRICS_ARE_DESCRIPTIVE = YES`

Regime authority:

`strategy/market_context.json / regime_state`

| Regime | Days | PnL | Return Contribution | Avg Daily Return | Positive Day Rate | Avg Exposure | Avg Cash | Worst Day | Best Day |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| BULL | 53 | +22,490 | +2.25% | +0.061% | 54.72% | 82.43% | 212,726 | 2023-03-13 / -44,720 | 2023-03-01 / +48,340 |
| RECOVERY | 14 | +200 | +0.02% | +0.012% | 64.29% | 81.28% | 214,487 | 2022-11-14 / -32,750 | 2022-12-15 / +18,710 |
| RANGE | 23 | +174,440 | +17.44% | +0.669% | 69.57% | 75.66% | 277,015 | 2022-12-07 / -28,260 | 2023-03-22 / +47,330 |
| CORRECTION | 3 | +3,240 | +0.32% | +0.057% | 66.67% | 71.80% | 324,363 | 2022-12-19 / -27,640 | 2023-03-20 / +26,250 |
| BEAR | 25 | +61,870 | +6.19% | +0.220% | 56.00% | 56.95% | 476,785 | 2022-10-11 / -22,410 | 2023-01-17 / +20,800 |

Do not infer causality from these associations.

## Exposure / Cash Characterization

| Metric | Value |
|---|---:|
| AVERAGE_EXPOSURE | 75.31% |
| MEDIAN_EXPOSURE | 76.82% |
| Min exposure | 26.82% |
| Max exposure | 98.25% |
| AVERAGE_CASH | 284,249 |
| Median cash | 263,745 |

Exposure bucket distribution:

| Bucket | Days | Avg Daily Return | Descriptive PnL |
|---|---:|---:|---:|
| <40% | 5 | -1.063% | -61,730 |
| 40-60% | 13 | +0.660% | +93,860 |
| 60-80% | 49 | +0.407% | +226,710 |
| 80-90% | 29 | -0.068% | -19,930 |
| 90%+ | 22 | +0.145% | +23,330 |

This is descriptive only and must not be used as exposure tuning in G12.

## Position Count

| Metric | Value |
|---|---:|
| AVERAGE_POSITION_COUNT | 10.94 |
| Median position count | 11 |
| Min position count | 5 |
| Max position count | 16 |

No optimal position count is inferred.

## Trading Activity

Authority:

`daily/<date>/execution/fills.json`

| Metric | Value |
|---|---:|
| Total fills | 430 |
| BUY fills | 214 |
| Total SELL fills | 216 |
| EXIT fills | 101 |
| REDUCE fills | 17 |
| SELL fills with missing source_decision_type | 98 |
| ADD fills | UNAVAILABLE_FROM_CANONICAL_FILL_SOURCE |
| Average trades per BD | 3.64 |
| No-trade days | 1 |

ADD fill count is not inferred from holdings diffs. The fill source does not expose a reliable ADD classification for BUY fills in this evidence window.

## Campaign Lifecycle Quality

Authority:

`daily/2023-03-27/positions/position_campaigns.json / pm_decision_evidence_events`

| Event | Events | Campaigns With Event | Repeated Campaigns |
|---|---:|---:|---:|
| HOLD | 841 | 112 | 92 |
| ADD | 54 | 5 | 5 |
| REDUCE | 159 | 134 | 21 |
| EXIT | 99 | 97 | 1 |

Realized performance by lifecycle group is unavailable without an unsafe campaign-id join.

## Winner Retention Scorecard

Authority:

Latest `position_campaigns` observed-to-date diagnostic fields.

| Metric | Value |
|---|---:|
| Winner campaign count from lifecycle relative return | 71 |
| Average observed MFE for winners | 14.18% |
| Average observed giveback for winners | 5.44% |
| Approx. realized profit retention | 61.63% |

Approximate realized profit retention is computed as:

`1 - average_giveback / average_observed_mfe`

`FUTURE_OUTCOME_USED_AS_PRODUCTION_INPUT = NO`

These are post-hoc Historical diagnostics only and are not Production inputs.

## Churn / Short-Lived Campaigns

Lifecycle bucket counts:

| Bucket | Campaign Count |
|---|---:|
| Same-day | 0 |
| Next-day | 0 |
| 2-5BD | 101 |

Gross profit, gross loss, net PnL, PF, and win rate by churn bucket are unavailable because realized PnL and latest lifecycle campaign ids are not join-compatible in this evidence snapshot.

## Rolling Performance

Rolling windows use every fully contained window in the completed evidence. No starting date is cherry-picked.

| Window | Completed Windows | Best Return | Median Return | Worst Return | Positive Window Rate | Worst MDD Inside Window |
|---|---:|---:|---:|---:|---:|---:|
| 20BD | 99 | +13.18% | +3.13% | -9.61% | 72.73% | -11.59% |
| 50BD | 69 | +16.87% | +10.00% | -0.53% | 97.10% | -12.21% |
| 100BD | 19 | +26.16% | +16.63% | +9.62% | 100.00% | -12.21% |

`ROLLING_20BD_SUMMARY = 99 windows / best +13.18% / median +3.13% / worst -9.61% / positive 72.73% / worst window MDD -11.59%`

`ROLLING_50BD_SUMMARY = 69 windows / best +16.87% / median +10.00% / worst -0.53% / positive 97.10% / worst window MDD -12.21%`

`ROLLING_100BD_SUMMARY = 19 windows / best +26.16% / median +16.63% / worst +9.62% / positive 100.00% / worst window MDD -12.21%`

## Start-Date Sensitivity Context

Prior runs are separate contextual observations and are not merged into one portfolio.

| Run | Start | Latest/Valid Through | Completed BD | Return |
|---|---|---|---:|---:|
| runtime-test-historical-extended-smoke-20260821T095536206137Z | 2022-08-15 | 2023-01-11 | 100 | +17.16% |
| runtime-test-historical-extended-smoke-20260822T104434934314Z | 2022-08-22 | 2022-12-15 | 79 | +9.24% |
| runtime-test-historical-extended-smoke-20260822T174358377089Z | 2022-10-03 | 2023-03-27 | 118 | +26.22% |

Comparable through `2022-12-15`:

| Run | Return Through 2022-12-15 |
|---|---:|
| runtime-test-historical-extended-smoke-20260821T095536206137Z | +19.90% |
| runtime-test-historical-extended-smoke-20260822T104434934314Z | +9.24% |
| runtime-test-historical-extended-smoke-20260822T174358377089Z | +16.59% |

`START_DATE_SENSITIVITY_OBSERVED = YES`

This is context only and not a start-date optimization recommendation.

## Risk Event Table

Top 10 negative daily PnL days:

| Date | Regime | Daily PnL | Return | Exposure | Positions | Next-Day PnL | Equity Later Recovered Prior Level |
|---|---|---:|---:|---:|---:|---:|---|
| 2023-03-13 | BULL | -44,720 | -3.775% | 34.72% | 5 | -4,820 | YES |
| 2023-03-03 | BULL | -43,690 | -3.403% | 91.59% | 13 | -1,060 | YES |
| 2022-11-14 | RECOVERY | -32,750 | -2.953% | 85.18% | 11 | +21,130 | YES |
| 2022-12-07 | RANGE | -28,260 | -2.443% | 84.76% | 12 | +11,170 | YES |
| 2022-12-19 | CORRECTION | -27,640 | -2.422% | 66.17% | 10 | -4,110 | YES |
| 2023-02-10 | BULL | -26,530 | -2.060% | 91.71% | 14 | -24,020 | YES |
| 2023-02-14 | BULL | -26,110 | -2.110% | 87.56% | 14 | +20,230 | YES |
| 2023-02-27 | BULL | -24,910 | -1.987% | 76.56% | 14 | +20 | YES |
| 2022-12-16 | RANGE | -24,840 | -2.131% | 81.76% | 15 | -27,640 | YES |
| 2023-02-13 | BULL | -24,020 | -1.904% | 67.98% | 13 | -26,110 | YES |

## Recovery Event Table

| Event | Start | End | PnL | Return |
|---|---|---|---:|---:|
| Largest 1BD gain | 2023-03-01 | 2023-03-01 | +48,340 | +3.934% |
| Largest 3BD recovery | 2023-03-17 | 2023-03-22 | +93,070 | +7.813% |
| Largest 5BD recovery | 2023-03-15 | 2023-03-22 | +149,060 | +13.131% |
| Fastest recovery from >5% drawdown | 2023-03-14 | 2023-03-23 | n/a | 6BD trough-to-recovery |

## Runtime Integrity Context

`STRATEGY_PERFORMANCE` is separated from `RUNTIME_RELIABILITY`.

| Metric | Value |
|---|---:|
| Runtime HALT count in target run so far | 0 |
| Completed runtime jobs | 1,062 |
| Submit REVIEW_REQUIRED/HALT days | 0 |
| Execution no-action continuation events | 1 |
| Known repaired boundary events exercised | 2022-11-30 Submit/Execution NO_ACTION continuation |
| Performance evidence quarantine required | NO |

`PERFORMANCE_EVIDENCE_QUARANTINE_REQUIRED = NO`

No HALT, rejected submit batch, duplicate side-effect, or performance-contaminating runtime defect was observed in the target run evidence through `2023-03-27`.

## Official Scorecard Proposal

`OFFICIAL_SCORECARD_SCHEMA_PROPOSED = YES`

Use the same metric definitions after the 480BD run completes:

Performance:

- Total Return
- CAGR
- Gross Profit
- Gross Loss
- Profit Factor
- Win Rate
- Payoff Ratio
- Expectancy

Risk:

- MDD
- Calmar
- Daily volatility
- Worst day
- Underwater duration

Consistency:

- Rolling 20BD / 50BD / 100BD returns
- Positive rolling-window rate
- Worst rolling-window MDD

Capital:

- Average exposure
- Median exposure
- Average cash
- Average positions
- Exposure bucket return characterization

Campaign:

- Holding period
- Winner / Loser stats
- Concentration
- Churn
- Winner retention

Runtime:

- HALTs
- REVIEW_REQUIRED
- No-action continuation events
- Reconciliation failures
- Duplicate side effects
- Performance evidence quarantine status

## No Performance Recommendation

`PERFORMANCE_TUNING_RECOMMENDED = NO`

This report does not recommend filters, thresholds, weights, SELL rules, BUY rules, exposure changes, position caps, ADD changes, regime changes, or any other tuning.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G12_INTERIM_SCORECARD_PROFITABLE_WITH_MATERIAL_BUT_RECOVERED_DRAWDOWN_RUN_STILL_INCOMPLETE`

`SCORECARD_STATUS = INTERIM`

`TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260822T174358377089Z`

`RUN_START_DATE = 2022-10-03`

`LATEST_FULLY_COMPLETED_DATE = 2023-03-27`

`COMPLETED_BUSINESS_DAY_COUNT = 118`

`RUN_COMPLETE = NO`

`INITIAL_CAPITAL = 1,000,000`

`CURRENT_EQUITY = 1,262,240`

`TOTAL_RETURN_PCT = +26.22%`

`ABSOLUTE_PNL = +262,240`

`PEAK_EQUITY = 1,295,660`

`PEAK_RETURN_PCT = +29.57%`

`MAX_DRAWDOWN_PCT = -12.21%`

`MAX_DRAWDOWN_YEN = -157,850`

`MDD_PEAK_DATE = 2023-02-08`

`MDD_TROUGH_DATE = 2023-03-14`

`CURRENT_DRAWDOWN_PCT = -2.58%`

`RETURN_TO_MDD_RATIO = 2.15`

`GROSS_PROFIT = +608,350`

`GROSS_LOSS = -350,310`

`PROFIT_FACTOR = 1.74`

`CLOSED_CAMPAIGN_COUNT = 199`

`WIN_RATE = 44.72%`

`AVERAGE_WINNER = +6,835`

`AVERAGE_LOSER = -3,649`

`PAYOFF_RATIO = 1.87`

`EXPECTANCY_PER_CAMPAIGN = +1,297`

`LARGEST_WINNER = +84,000 / 44440`

`LARGEST_LOSER = -61,200 / 59350`

`TOP_5_WINNER_CONTRIBUTION = 33.65%`

`AVERAGE_HOLDING_BD = 7.23`

`AVERAGE_EXPOSURE = 75.31%`

`MEDIAN_EXPOSURE = 76.82%`

`AVERAGE_CASH = 284,249`

`AVERAGE_POSITION_COUNT = 10.94`

`BEST_DAILY_RETURN = +3.934% / 2023-03-01`

`WORST_DAILY_RETURN = -3.775% / 2023-03-13`

`DAILY_RETURN_VOLATILITY = 1.386%`

`POSITIVE_DAY_RATE = 59.32%`

`BULL_PNL = +22,490`

`RECOVERY_PNL = +200`

`RANGE_PNL = +174,440`

`CORRECTION_PNL = +3,240`

`BEAR_PNL = +61,870`

`ROLLING_20BD_SUMMARY = 99 windows / best +13.18% / median +3.13% / worst -9.61% / positive 72.73%`

`ROLLING_50BD_SUMMARY = 69 windows / best +16.87% / median +10.00% / worst -0.53% / positive 97.10%`

`ROLLING_100BD_SUMMARY = 19 windows / best +26.16% / median +16.63% / worst +9.62% / positive 100.00%`

`START_DATE_SENSITIVITY_OBSERVED = YES`

`RUNTIME_HALT_COUNT = 0`

`PERFORMANCE_EVIDENCE_QUARANTINE_REQUIRED = NO`

`FUTURE_OUTCOME_USED_AS_PRODUCTION_INPUT = NO`

`PERFORMANCE_TUNING_RECOMMENDED = NO`

`OFFICIAL_SCORECARD_SCHEMA_PROPOSED = YES`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = Continue the existing long-horizon run unchanged. After the run completes, create the FINAL version of this same scorecard using identical metric definitions.`
