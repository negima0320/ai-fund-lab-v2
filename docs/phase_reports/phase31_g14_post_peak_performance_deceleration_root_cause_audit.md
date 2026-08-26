# Phase31-G14 — Post-Peak Performance Deceleration Root Cause Audit

## Scope

Task type: READ-ONLY PERFORMANCE CAUSAL DECOMPOSITION.

Target run:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z`

Runtime state observed during this audit:

- `run_state.status`: `RUNNING`
- `run_state.next_job`: `2023-06-09:market_refresh`
- latest fully completed date used for this report: `2023-06-08`
- completed business days at read time: `168`

Reference peak:

- `2023-03-23`
- equity: `1,295,660`
- return from initial capital: `+29.57%`

This report did not execute fresh-run, resume, replay, or Historical runtime. The target run was not interfered with.

## Evidence Sources

Primary artifacts:

- `run_state.json`
- `daily/<date>/current_valuation_refresh/valuation_projection.json`
- `daily/<date>/execution/fills.json`
- `daily/<date>/execution/realized_slices.json`
- `daily/<date>/strategy/market_context.json`
- `daily/<date>/strategy/buy_quality_decisions.json`
- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/2023-06-08/positions/position_campaigns.json`

Market regime was read from canonical per-day Runtime strategy market context evidence. No future labeling, later outcome classification, parameter tuning, or alternate split point was used.

## Window Definition

| Window | Dates | Business days | Start equity | End equity | Absolute PnL | Return |
|---|---:|---:|---:|---:|---:|---:|
| PRE_PEAK | 2022-10-03 -> 2023-03-23 | 116 | 1,000,000 | 1,295,660 | +295,660 | +29.57% |
| POST_PEAK | 2023-03-24 -> 2023-06-08 | 52 | 1,295,660 | 1,161,160 | -134,500 | -10.38% |

## Core Realized Campaign Performance

| Metric | PRE_PEAK | POST_PEAK |
|---|---:|---:|
| Closed / realized campaign count | 195 | 82 |
| Winners | 87 | 34 |
| Losers | 94 | 44 |
| Breakeven | 14 | 4 |
| Gross profit | +593,450 | +210,170 |
| Gross loss | -333,510 | -337,330 |
| Profit factor | 1.779 | 0.623 |
| Win rate | 44.62% | 41.46% |
| Payoff ratio | 1.923 | 0.806 |
| Expectancy | +1,333 | -1,551 |
| Average winner | +6,821 | +6,181 |
| Average loser | -3,548 | -7,667 |
| Median winner | +2,400 | +2,450 |
| Median loser | -1,335 | -2,600 |
| Largest winner | 44440 +84,000 on 2023-03-22 | 49370 +41,200 on 2023-05-10 |
| Largest loser | 59350 -61,200 on 2023-03-06 | 60220 -45,500 on 2023-04-13 |

Primary realized-performance deterioration is `AVG_LOSER_WORSENING`. Win rate fell modestly, and average winner declined mildly, but average loser more than doubled in magnitude from `-3,548` to `-7,667`. This collapsed payoff from `1.923` to `0.806` and moved expectancy from positive to negative.

Top POST loser concentration:

| Symbol | Date | PnL |
|---|---:|---:|
| 60220 | 2023-04-13 | -45,500 |
| 78780 | 2023-03-30 | -44,500 |
| 30410 | 2023-06-02 | -38,900 |
| 41660 | 2023-04-12 | -38,400 |
| 62310 | 2023-05-15 | -32,700 |

The top five POST realized losers explain about `59.2%` of POST gross realized loss.

## Daily Loss Distribution

| Metric | PRE_PEAK | POST_PEAK |
|---|---:|---:|
| Mean daily return | +0.224% | -0.183% |
| Median daily return | +0.309% | -0.054% |
| Daily volatility | 1.380% | 2.335% |
| Downside deviation | 0.950% | 1.708% |
| Positive day rate | 60.00% | 48.08% |
| Negative day rate | 40.00% | 51.92% |
| Days <= -1% | 17 | 13 |
| Days <= -2% | 10 | 8 |
| Days <= -3% | 2 | 4 |
| Days <= -5% | 0 | 1 |

Worst POST days:

| Date | Regime | PnL | Return | Exposure | Positions |
|---|---|---:|---:|---:|---:|
| 2023-05-19 | RECOVERY | -94,200 | -8.173% | 44.51% | 5 |
| 2023-04-11 | CORRECTION | -45,340 | -3.638% | 65.95% | 7 |
| 2023-06-01 | CORRECTION | -39,430 | -3.311% | 71.55% | 8 |
| 2023-05-12 | BULL | -38,850 | -3.213% | 95.29% | 10 |
| 2023-04-18 | BULL | -35,400 | -2.968% | 48.13% | 6 |

`LARGE_LOSS_DAY_FREQUENCY_INCREASED = YES`.

The POST window has fewer days than PRE, but larger-loss frequency worsened materially on a rate basis: `<= -3%` days moved from `2/116 = 1.7%` to `4/52 = 7.7%`, and `<= -5%` appeared only POST.

## Drawdown / Giveback Structure

Peak-to-current POST drawdown:

- peak: `2023-03-23`, equity `1,295,660`
- trough so far: `2023-05-19`, equity `1,058,430`
- latest audited equity: `2023-06-08`, equity `1,161,160`
- worst drawdown depth: `-18.31%`
- underwater duration through latest audited date: `52` business days
- recovered to prior peak: `NO`

Failed recovery attempts, using descriptive recovery followed by another material downswing without reclaiming the 2023-03-23 peak:

| Trough | Rebound | Rebound % | Next downswing | Drop from rebound |
|---|---|---:|---|---:|
| 2023-03-30 1,212,520 | 2023-03-31 1,246,230 | +2.78% | 2023-04-12 1,168,900 | -6.21% |
| 2023-04-12 1,168,900 | 2023-04-17 1,192,880 | +2.05% | 2023-04-21 1,140,140 | -4.42% |
| 2023-04-21 1,140,140 | 2023-05-10 1,221,930 | +7.17% | 2023-05-19 1,058,430 | -13.38% |
| 2023-05-19 1,058,430 | 2023-05-30 1,204,090 | +13.76% | 2023-06-01 1,151,360 | -4.38% |

`RECOVERY_ATTEMPT_COUNT = 4`

`RECOVERY_ATTEMPTS_THAT_FAILED = 4`

`FAILED_RECOVERY_DEFINITION = equity recovered materially from a local trough but failed to reclaim the 2023-03-23 peak before another material downswing`

## Re-Risking / False Recovery

Representative POST episodes:

| Episode | Low / reduced exposure | Re-risked exposure | Loss within 1-3BD |
|---|---|---|---|
| Early April | 2023-04-05, BEAR, 14.98% exposure | 2023-04-06, BEAR, 40.84%; then 2023-04-11, CORRECTION, 65.95% | 2023-04-11 -45,340, 2023-04-12 -31,960 |
| April bounce | 2023-04-10, CORRECTION, 19.25% | 2023-04-11, CORRECTION, 65.95% | 2023-04-11 -45,340; 2023-04-12 -31,960 |
| May bounce | 2023-05-10, BULL, 68.53% | 2023-05-12, BULL, 95.29% | 2023-05-12 -38,850; 2023-05-15 -34,700 |
| 67310 shock / reversal | 2023-05-18, BULL, 49.04% | 2023-05-19, RECOVERY, 44.51% | 2023-05-19 -94,200; G13 classified this as valid mark-to-market with execution reversal on 2023-05-22 |

`FALSE_RECOVERY_RERISK_PATTERN_SUPPORTED = YES`

This is not a claim that every POST loss came from re-risking. It is supported as a material recurring pattern: exposure rose after local stabilization/rebound, then the next 1-3 business days contained large losses.

## Exposure Timing

POST exposure bucket outcomes:

| Exposure bucket | Days | PnL | Avg return | Positive day rate | Worst |
|---|---:|---:|---:|---:|---:|
| <40% | 11 | +121,910 | +1.030% | 63.64% | -0.987% |
| 40-60% | 17 | -181,840 | -0.904% | 41.18% | -8.173% |
| 60-80% | 19 | -40,290 | -0.142% | 42.11% | -3.638% |
| 80-90% | 2 | -11,840 | -0.499% | 50.00% | -1.791% |
| 90%+ | 3 | -22,440 | -0.603% | 66.67% | -3.213% |

`EXPOSURE_FAILURE_CLASS = OVEREXPOSED_ON_BAD_DAYS`

The evidence does not support a simple "always too much exposure" story. The largest POST damage came from being exposed during bad 40-80% and 90%+ days. The `<40%` bucket is positive, but that includes the 2023-05-22 execution-driven recovery described in G13, so it should not be read as missed profitable opportunity.

## Regime / Transition

POST static regime outcomes:

| Regime | Days | PnL | Avg return | Positive day rate | Avg exposure |
|---|---:|---:|---:|---:|---:|
| BEAR | 3 | -10,310 | -0.276% | 33.33% | 32.02% |
| BULL | 20 | +69,690 | +0.359% | 55.00% | 53.34% |
| CORRECTION | 3 | -66,270 | -1.814% | 33.33% | 52.25% |
| RANGE | 8 | -3,590 | -0.014% | 50.00% | 57.05% |
| RECOVERY | 18 | -124,020 | -0.574% | 44.44% | 59.99% |

`STATIC_REGIME_EXPLAINS_DECELERATION = PARTIAL`

RECOVERY and CORRECTION days explain most static-regime POST loss, while BULL days remained profitable in aggregate. This supports regime interaction as a contributor, not as a complete standalone explanation.

Notable adverse transition evidence:

- `CORRECTION -> CORRECTION`, 2023-04-10: next1 `-3.638%`, next3 `-6.257%`
- `RANGE -> CORRECTION`, 2023-05-31: next1 `-3.311%`, next3 `-3.238%`
- `CORRECTION -> BULL`, 2023-04-11: next1 `-2.661%`
- `BULL -> RECOVERY`, 4 observed POST transitions: average next1 `-2.361%`; includes the 2023-05-19 shock sequence

`REGIME_TRANSITION_LOSS_CONCENTRATION = PARTIAL`

## Entry / Opportunity Availability

BUY quality and planning comparison:

| Metric | PRE_PEAK | POST_PEAK |
|---|---:|---:|
| BUY quality decisions | 5,800 | 2,600 |
| Runtime plans | 3,931 | 1,450 |
| BUY plans | 444 | 108 |
| BUY plans / day | 3.83 | 2.08 |
| Mean BUY opportunity rank | 25.95 | 29.28 |
| Median BUY opportunity rank | 27 | 32 |
| Mean BUY quality score | 0.608 | 0.589 |
| Median BUY quality score | 0.599 | 0.563 |
| Mean portfolio member count | 54.20 | 51.52 |
| Mean available incremental budget | 0.320 | 0.592 |

Action distribution:

| Action | PRE_PEAK | POST_PEAK |
|---|---:|---:|
| FULL_ALLOCATION_ELIGIBLE | 506 | 226 |
| REDUCED_ALLOCATION_ONLY | 3,214 | 1,249 |
| BUY_WAIT | 1,123 | 642 |
| REJECT | 957 | 483 |

`ENTRY_QUALITY_DROPPED = PARTIAL`

POST BUY plans were fewer, lower-ranked on average, and lower quality-score on average. However, the realized deterioration is much larger in loser severity than in entry score/rank drift, so entry quality is contributory rather than primary.

`OPPORTUNITY_AVAILABILITY_DROPPED = YES`

BUY plans per day fell from `3.83` to `2.08`, and POST portfolio member count also fell. Available incremental budget rose, which suggests fewer acceptable deployments rather than purely cash exhaustion.

## Exit / PM / Winner Retention

PM evidence from canonical position campaign lifecycle:

| Metric | PRE_PEAK | POST_PEAK |
|---|---:|---:|
| HOLD events | 835 | 176 |
| REDUCE events | 157 | 58 |
| EXIT events | 98 | 36 |
| ADD events | 54 | 3 |
| Closed campaigns | 159 | 66 |
| Average holding duration | 8.24 BD | 6.33 BD |
| Median holding duration | 5 BD | 4 BD |
| 1-5BD closed campaign share | 55.35% | 63.64% |
| Mean observed MFE | 6.31% | 4.94% |
| Mean observed giveback | 4.35% | 5.77% |
| Median retention ratio | 0.467 | 0.333 |
| Large giveback count | 55 | 25 |

`WINNER_RETENTION_DETERIORATED = YES`

Winner retention deteriorated on campaign evidence: lower MFE, higher giveback, lower final returns, and lower median retention ratio. It is a secondary cause because POST gross profit did not collapse as sharply as gross loss quality did.

`SHORT_HOLD_LOSS_SHARE_INCREASED = YES`

Short-hold closed campaign share increased from `55.35%` to `63.64%`, while POST realized expectancy and average loser worsened. The precise PnL-by-holding-bucket join is not treated as canonical here, but the count distribution and realized-loss severity jointly support short-hold/churn loss as contributory.

`CHURN_LOSS_INCREASED = PARTIAL`

Trading fills per day decreased from `3.65` to `3.25`, so deterioration is not explained by more total trading activity. The churn-like evidence is instead shorter closed holding duration plus worse realized loss severity.

## Activity Shift

| Metric | PRE_PEAK | POST_PEAK |
|---|---:|---:|
| Total fills | 423 | 169 |
| Fills / day | 3.65 | 3.25 |
| BUY fills | 211 | 82 |
| SELL fills | 212 | 87 |
| No-trade days | 1 | 2 |

`TRADING_ACTIVITY_SHIFT = DECREASED`

The post-peak deceleration is not caused by higher aggregate turnover. It is caused by worse timing, larger losses, and weaker realized payoff per closed campaign.

## G13 2023-05-19 Bridge

The largest daily loss, `2023-05-19 -94,200`, should not be quarantined as a measurement defect. G13 found:

- 67310 contributed about `-100,000` from valid canonical valuation price movement
- no one-day adjustment-factor defect
- no corporate-action effective-date defect
- no stale fallback / price authority measurement regression
- 2023-05-22 recovery was largely an execution reversal, not a price-basis correction

Therefore `2023-05-19` remains valid performance evidence in this decomposition.

## Causal Decomposition

Primary cause:

- `LARGER_LOSER_SEVERITY`

Secondary causes:

- `FALSE_RECOVERY_RERISKING`
- `REGIME_MISMATCH_OR_TRANSITION_ADVERSENESS`
- `WINNER_RETENTION_DETERIORATION`
- `REDUCED_PROFITABLE_OPPORTUNITY_AVAILABILITY`

Rejected as primary:

- pure win-rate collapse: win rate declined only from `44.62%` to `41.46%`
- pure average-winner decline: average winner declined only from `+6,821` to `+6,181`
- pure excessive churn: fills per day decreased
- pure market-wide adverse condition: BULL days remained profitable, while losses concentrated in RECOVERY/CORRECTION and specific adverse sequences
- pure valuation defect: G13 cleared the largest loss as valid mark-to-market evidence

## Required Output

`PRIMARY_JUDGMENT = POST_PEAK_DECELERATION_MULTI_CAUSAL`

`TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260822T174358377089Z`

`LATEST_COMPLETED_DATE = 2023-06-08`

`PRE_PEAK_BUSINESS_DAYS = 116`

`POST_PEAK_BUSINESS_DAYS = 52`

`PRE_PEAK_RETURN = +29.57%`

`POST_PEAK_RETURN = -10.38%`

`PRE_PEAK_ABSOLUTE_PNL = +295,660`

`POST_PEAK_ABSOLUTE_PNL = -134,500`

`PF_PRE = 1.779`

`PF_POST = 0.623`

`WIN_RATE_PRE = 44.62%`

`WIN_RATE_POST = 41.46%`

`PAYOFF_PRE = 1.923`

`PAYOFF_POST = 0.806`

`EXPECTANCY_PRE = +1,333`

`EXPECTANCY_POST = -1,551`

`PRIMARY_DETERIORATION_COMPONENT = AVG_LOSER_WORSENING`

`LARGE_LOSS_DAY_FREQUENCY_INCREASED = YES`

`WORST_POST_PEAK_DAY = 2023-05-19`

`WORST_POST_PEAK_DAY_PNL = -94,200`

`WORST_POST_PEAK_DAY_RETURN = -8.17%`

`RECOVERY_ATTEMPT_COUNT = 4`

`RECOVERY_ATTEMPTS_THAT_FAILED = 4`

`FALSE_RECOVERY_RERISK_PATTERN_SUPPORTED = YES`

`EXPOSURE_FAILURE_CLASS = OVEREXPOSED_ON_BAD_DAYS`

`STATIC_REGIME_EXPLAINS_DECELERATION = PARTIAL`

`REGIME_TRANSITION_LOSS_CONCENTRATION = PARTIAL`

`ENTRY_QUALITY_DROPPED = PARTIAL`

`EXIT_QUALITY_DROPPED = YES`

`WINNER_RETENTION_DETERIORATED = YES`

`LOSER_DEGRADATION_CLASS = BOTH`

`LOSS_FREQUENCY_INCREASED = YES`

`AVG_LOSER_WORSENED = YES`

`SHORT_HOLD_LOSS_SHARE_INCREASED = YES`

`CHURN_LOSS_INCREASED = PARTIAL`

`OPPORTUNITY_AVAILABILITY_DROPPED = YES`

`TRADING_ACTIVITY_SHIFT = DECREASED`

`LOSS_CONCENTRATION = MODERATE_TO_HIGH`

`POST_PEAK_PRIMARY_CAUSE = LARGER_LOSER_SEVERITY`

`POST_PEAK_SECONDARY_CAUSE = FALSE_RECOVERY_RERISKING_AND_REGIME_INTERACTION`

`POST_PEAK_CONTRIBUTORY_CAUSES = WINNER_RETENTION_DETERIORATION, REDUCED_OPPORTUNITY_AVAILABILITY, SHORTER_HOLD_DURATION`

`FUTURE_INFORMATION_USED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`IMPLEMENTATION_CHANGED = NO`

## Final Questions

1. Peak後の鈍化は何が主因か？

   主因は平均損失の悪化です。PFは `1.779 -> 0.623`、平均損失は `-3,548 -> -7,667` に悪化し、期待値は `+1,333 -> -1,551` へ反転しました。

2. 勝率低下か、損失肥大か、winner givebackか？

   損失肥大が主因です。勝率低下とwinner retention悪化はありますが、規模としては平均損失悪化とpayoff collapseが支配的です。

3. exposure / regime / false recovery のどれが効いているか？

   false recovery後の再リスク化とRECOVERY/CORRECTION局面での損失集中が効いています。exposureは単純な常時過大ではなく、悪い日の40-80%および90%+ exposureが損失を増幅しました。

4. G8/G10後のPM改善余地がどこに残っているか？

   本監査は改善実装を提案しません。証拠上の残課題は、利益保持よりも、回復局面での再リスク後に大きいloserを許している点と、平均損失が拡大している点です。

5. 次に改善すべき対象は BUY / SELL / PM / exposure / regime gating のどれか？

   実装提案は本タスク範囲外です。原因分類としては `PM/exposure/regime interaction` と `SELL/loser containment` 側の寄与がBUY単独より大きいです。
