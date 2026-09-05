# Phase32-GR — Post-GN 20BD BUY Selection Current-PIT Opportunity Quality / Pre-GN Causal Comparison Audit

Date: 2026-09-05 JST

Scope: READ-ONLY audit of completed 20BD Historical artifacts for:

- Post-GN: `runtime-test-historical-extended-smoke-20260904T231555544129Z`
- Pre-GN: `runtime-test-historical-extended-smoke-20260904T204012180628Z`
- Window: 2023-06-01 through 2023-06-28, 20 business days
- Initial cash: 1,000,000 JPY

No source/config/schema/runtime state mutation was performed. No fresh-run/resume/replay/recover was performed. Future return, realized PnL, MFE/MAE, and final campaign outcome were excluded from BUY-quality attribution.

## Executive Judgment

GN changed actual BUY selection in 14 symbol-date observations. The first direct split occurred on 2023-06-16: pre-GN bought `50250` at Current Opportunity rank 23 because pre-GN MCV still elevated `ELIGIBLE_STRONG` ahead of the pure rank order; post-GN did not buy `50250` and instead preserved rank-first capital ordering among the same-day accepted BUY set.

Across the full 20BD window, post-GN purchased rank quality improved modestly in aggregate:

- weighted average purchased rank: pre-GN `16.7465`, GN `16.2812`
- median purchased rank: pre-GN `17`, GN `16`
- Top20 capitalization: pre-GN `35/400 = 8.75%`, GN `37/400 = 9.25%`

The post-6/16 differences are path-dependent after the first BUY split, so same-day output differences after that point are not automatically direct GN priority effects.

## Actual BUY Divergence

Runtime evidence source: `execution/fills.json` BUY fills, keyed by `business_date` and `symbol`.

- BOTH_BUY_COUNT: `53`
- PRE_GN_ONLY_BUY_COUNT: `7`
- GN_ONLY_BUY_COUNT: `7`
- ACTUAL_BUY_OVERLAP_RATE: `79.10%` (`53 / 67` unique symbol-date BUY observations)

Pre-GN-only BUYs:

| date | symbol | type | qty | notional | Current rank | MCV priority |
|---|---:|---|---:|---:|---:|---:|
| 2023-06-16 | 50250 | BUY_NEW | 100 | 75,900 | 23 | 2 |
| 2023-06-20 | 89180 | BUY_NEW | 3,600 | 32,400 | 23 | 6 |
| 2023-06-22 | 33230 | BUY_NEW | 500 | 46,500 | 22 | 4 |
| 2023-06-26 | 54010 | BUY_NEW | 100 | 58,470 | 33 | 3 |
| 2023-06-27 | 92410 | BUY_NEW | 100 | 143,100 | 14 | 2 |
| 2023-06-28 | 50250 | BUY_NEW | 100 | 84,700 | 25 | 7 |
| 2023-06-28 | 77090 | BUY_NEW | 100 | 30,000 | 13 | 3 |

GN-only BUYs:

| date | symbol | type | qty | notional | Current rank | MCV priority |
|---|---:|---|---:|---:|---:|---:|
| 2023-06-19 | 89180 | BUY_NEW | 3,400 | 30,600 | 16 | 6 |
| 2023-06-21 | 33230 | BUY_NEW | 300 | 29,700 | 21 | 8 |
| 2023-06-21 | 48910 | BUY_NEW | 100 | 33,100 | 14 | 5 |
| 2023-06-26 | 92410 | BUY_NEW | 100 | 145,000 | 14 | 3 |
| 2023-06-27 | 37470 | BUY_NEW | 100 | 44,900 | 27 | 7 |
| 2023-06-27 | 77090 | BUY_NEW | 100 | 27,300 | 15 | 4 |
| 2023-06-28 | 70420 | BUY_NEW | 100 | 52,450 | 29 | 12 |

## First Actual BUY Divergence

- FIRST_ACTUAL_BUY_DIVERGENCE_DATE: `2023-06-16`
- FIRST_ACTUAL_BUY_DIVERGENCE_SYMBOL: `50250`
- FIRST_ACTUAL_BUY_DIVERGENCE_CAUSE: `DIRECT_GN_PRIORITY_EFFECT: pre-GN quality-class-first priority lifted rank-23 50250 to MCV priority 2; GN rank-first priority placed 50250 at priority 12, leaving it with zero runtime quantity.`

Causal trace for `50250` on 2023-06-16:

| stage | pre-GN | post-GN |
|---|---|---|
| Candidate / Current Opportunity | BUY_NEW candidate | BUY_NEW candidate |
| Current rank | `23` | `23` |
| BQ / Entry | `REDUCED_ALLOCATION_ONLY`, `BUY_NEW_ALLOWED`, score `0.649785` | same |
| Momentum / trend | `BUY_ELIGIBLE`, `HEALTHY_CONTINUATION` | same |
| MCV class | `ELIGIBLE_STRONG` | `ELIGIBLE_STRONG` |
| MCV canonical priority | `2` | `12` |
| PC requested / accepted | requested `0.070985`, accepted `0.070985` | requested trace `0.0`, accepted weight diagnostic `0.030303`, but no executable quantity |
| Lot-aware quantity | `100` | `0` |
| PS / Runtime BUY | BUY fill: 100 shares, 75,900 JPY | no BUY order; runtime reason `no_order_zero_quantity_delta;portfolio_add_candidate_maps_to_buy_new` |

Same-day rank context: post-GN bought `94320` rank 1 ADD, `40520` rank 5 NEW, `37820` rank 9 NEW, `23150` rank 19 NEW, and `68360` rank 29 NEW. The first divergence is therefore not a SELL, PM, runtime, or sizing-authority redecision; it is the intended replacement of quality-class-first MCV ordering with Current Opportunity rank-first ordering.

## Paired Replacement Analysis

Paired same-day replacements, matched only where both sides had same-day exclusive BUYs:

| date | pre-GN symbol/rank | GN symbol/rank | PIT priority judgment |
|---|---|---|---|
| 2023-06-26 | 54010 / rank 33 | 92410 / rank 14 | GN better |
| 2023-06-27 | 92410 / rank 14 | 77090 / rank 15 | pre-GN slightly better |
| 2023-06-28 | 77090 / rank 13 | 70420 / rank 29 | pre-GN better |

- PAIRED_REPLACEMENT_COUNT: `3`
- GN_ACTUAL_BUY_RANK_IMPROVEMENT_RATE: `33.33%` (`1 / 3`)
- GN_CURRENT_PIT_PRIORITY_IMPROVEMENT_COUNT: `1`
- PRE_GN_CURRENT_PIT_PRIORITY_BETTER_COUNT: `2`
- INCOMPARABLE_COUNT: `0`

Interpretation: paired replacements after 2023-06-16 include downstream portfolio/cash path effects. They do not overturn the aggregate rank-quality improvement, and they do not show old ownership/history/accepted-increment priority returning in post-GN artifacts.

## Root Causes

PRE_GN_LOWER_PRIORITY_BUY_ROOT_CAUSES:

- QUALITY_CLASS_FIRST: `1` directly evidenced by the 2023-06-16 `50250` split.
- CURRENT_POSITION_RELATIONSHIP: `0` directly evidenced.
- ACCEPTED_INCREMENT_FILTER: `0` directly evidenced.
- CONSTRUCTION_PRIORITY_FALLBACK: `0` directly evidenced.
- HISTORY/CAMPAIGN: `0` directly evidenced.
- LOT/CAP/LIQUIDITY: `0` direct first-cause evidence.
- OTHER / downstream path: remaining later divergences are path-dependent.

GN_ONLY_BUY_ROOT_CAUSES:

- rank-first Current PIT priority reached capital: `7`
- old ownership/history/campaign cause: `0`
- accepted-increment dependency cause: `0`

PRE_GN_ONLY_BUY_GN_SKIP_REASONS:

- no requested increment: `3`
- higher priority consumed capital or residual cash: `2`
- lot infeasible / zero runtime quantity: `2`
- ADD safety: `0`
- recent EXIT guard: `0`
- no longer eligible: `0` directly evidenced

## NEW / ADD Distribution

| metric | pre-GN | post-GN |
|---|---:|---:|
| BUY_NEW count | 52 | 52 |
| BUY_NEW notional | 2,885,000 JPY | 2,776,980 JPY |
| BUY_ADD count | 8 | 8 |
| BUY_ADD notional | 222,200 JPY | 222,200 JPY |

GN did not change NEW/ADD action-type counts and did not favor ADD over NEW by count or ADD notional.

## Higher-Rank Capitalization

Characterization only, not a production cutoff:

| cutoff | pre-GN actual BUY reach | post-GN actual BUY reach |
|---|---:|---:|
| Top5 | 14 / 100 = 14.00% | 14 / 100 = 14.00% |
| Top10 | 20 / 200 = 10.00% | 20 / 200 = 10.00% |
| Top20 | 35 / 400 = 8.75% | 37 / 400 = 9.25% |
| Top50 | 60 / 1000 = 6.00% | 60 / 1000 = 6.00% |

Capital Reach Quality:

- PRE_GN_WEIGHTED_AVG_PURCHASED_RANK: `16.7465`
- GN_WEIGHTED_AVG_PURCHASED_RANK: `16.2812`
- PRE_GN_MEDIAN_PURCHASED_RANK: `17`
- GN_MEDIAN_PURCHASED_RANK: `16`
- deepest purchased rank: pre-GN `36`, GN `36`

## Direct vs Downstream Path Separation

Divergence classification over all exclusive BUY symbol-date observations:

- DIRECT_GN_PRIORITY_EFFECT_COUNT: `1`
- DOWNSTREAM_PATH_EFFECT_COUNT: `13`

By date:

| date | divergence count | classification | pre-GN-only | GN-only |
|---|---:|---|---|---|
| 2023-06-16 | 1 | DIRECT_GN_PRIORITY_EFFECT | 50250 | none |
| 2023-06-19 | 1 | DOWNSTREAM_PATH_EFFECT | none | 89180 |
| 2023-06-20 | 1 | DOWNSTREAM_PATH_EFFECT | 89180 | none |
| 2023-06-21 | 2 | DOWNSTREAM_PATH_EFFECT | none | 33230, 48910 |
| 2023-06-22 | 1 | DOWNSTREAM_PATH_EFFECT | 33230 | none |
| 2023-06-26 | 2 | DOWNSTREAM_PATH_EFFECT | 54010 | 92410 |
| 2023-06-27 | 3 | DOWNSTREAM_PATH_EFFECT | 92410 | 37470, 77090 |
| 2023-06-28 | 3 | DOWNSTREAM_PATH_EFFECT | 50250, 77090 | 70420 |

## 50250 Trace

50250_TRACE_COMPLETE: `YES`

Key observations:

- 2023-06-14: no BUY in either run; rank 32; BQ `BUY_WAIT`; no priority.
- 2023-06-15: no BUY in either run; rank 31; momentum `TEMPORARY_BUY_INELIGIBLE`; no runtime BUY.
- 2023-06-16: pre-GN BUY_NEW 100 shares; GN no BUY. This is the first direct GN priority effect.
- 2023-06-19: pre-GN already holds `50250`; GN treats it as BUY_NEW candidate at rank 22 / priority 9 and buys no additional runtime quantity.
- 2023-06-20: pre-GN has PM EXIT path for `50250`; GN has BUY_NEW evidence at rank 21 / priority 9 but zero runtime quantity.
- 2023-06-28: pre-GN buys `50250` again as path-dependent PRE_GN_ONLY; not used as future-return evidence.

No 50250 attribution used post-decision return.

## 89180 Quantity Divergence

89180_DIVERGENCE_TRACE_COMPLETE: `YES`

First divergence: 2023-06-19, GN BUY_NEW `89180` 3,400 shares / 30,600 JPY while pre-GN had no fill. This is downstream of the 2023-06-16 portfolio split, not a SELL regression.

Subsequent differences:

- 2023-06-20: pre-GN buys 3,600 shares; GN has PM REDUCE / no BUY and sells 800 shares.
- 2023-06-21: GN sells 600 shares; pre-GN no 89180 fill.
- 2023-06-22: both have PM REDUCE sells, quantity differs because holdings differ: pre-GN sells 900, GN sells 500.
- 2023-06-23: both have PM REDUCE sells, quantity differs because holdings differ: pre-GN sells 600, GN sells 300.
- 2023-06-26: both have PM REDUCE sells, quantity differs because holdings differ: pre-GN sells 1,000, GN sells 600.

The observed 89180 quantity differences are path/holding-size effects. Runtime plans retain PM REDUCE semantics such as `pm_reduce_zero_delta_maps_to_intentional_no_order` / `reduce_execution_semantic`, so this is not classified as SELL semantic regression.

## Cash Difference Attribution

GN cash differences after 2023-06-16 are path-dependent. The 2023-06-16 direct split left `50250` without executable quantity after rank-first ordering; later cash/exposure differences follow from holdings, lot granularity, and PM reductions. Cash was not judged as good or bad by level alone.

- CASH_SEMANTIC_REGRESSION_FOUND: `NO`
- Evidence: no runtime cash-winner redecision, no PS recomputation of capital priority, and residual cash remains explicit through PC/PS/runtime compatibility artifacts.

## Regime Characterization

The auditable dynamic policy state in this run window is `BALANCED` for all 20 dates; requested CORRECTION/RECOVERY/BULL buckets were not present as discrete labels in the inspected production artifacts. Therefore the report records one observed regime bucket and does not derive thresholds.

| regime | run | days | BUY count | BUY notional | median rank | avg exposure | avg cash |
|---|---|---:|---:|---:|---:|---:|---:|
| BALANCED | pre-GN | 20 | 60 | 3,107,200 | 17 | 0.860286 | 0.139714 |
| BALANCED | GN | 20 | 60 | 2,999,180 | 16 | 0.861839 | 0.138161 |

- REGIME_BUY_CHARACTERIZATION_COMPLETE: `YES, using observed BALANCED artifact state; CORRECTION/RECOVERY/BULL labels were not materialized in this 20BD artifact set.`

## Churn / Recent Exit Guard

Churn metrics from 20BD fill sequences:

- PRE_GN_BUY_EXIT_BUY_CYCLE_COUNT: `10`
- GN_BUY_EXIT_BUY_CYCLE_COUNT: `10`
- pre-GN EXIT->BUY count: `12`
- GN EXIT->BUY count: `12`
- repeated same-symbol cycle count: pre-GN `12`, GN `13`
- GN_NEW_CHURN_RISK_COUNT: `1`
- GN_MEANINGFUL_REQUALIFICATION_COUNT: `1`

The one extra repeated same-symbol cycle is tied to path-dependent timing/holding differences and the later `50250`/`89180` path, with contemporaneous BQ/Entry/rank evidence present. No recent-exit bypass was observed.

Recent Exit Guard:

- activation/block/release artifacts and PC reason-code materialization inspected over 20BD.
- guard block evidence observed in both runs.
- RECENT_EXIT_GUARD_BYPASS_COUNT: `0`

## SELL / Winner / Sizing / Safety Regression Search

- SELL_SEMANTIC_REGRESSION_FOUND: `NO`
- WINNER_AUTHORITY_REGRESSION_FOUND: `NO`
- SIZING_SEMANTIC_REGRESSION_FOUND: `NO`
- CASH_SEMANTIC_REGRESSION_FOUND: `NO`
- ADD_SAFETY_BYPASS_COUNT: `0`
- G129_REGRESSION_COUNT: `0`

Evidence basis:

- Runtime planning keeps `runtime_capital_priority_redecision = false`.
- PS keeps `position_sizing_recomputes_capital_priority = false`.
- G61/G63 compatibility remains PASS and prohibits implicit lower-priority promotion.
- Fresh target shadow zero-tolerance diagnostics report `add_safety_bypass_count = 0`.
- `recent_exit_guard_buy_new_bypass_blocked` appears as block evidence, not bypass permission.
- SELL/REDUCE quantity differences are explained by different prior holdings after BUY path divergence.

## PnL Separation

Final 20BD return is recorded only as run outcome context:

- POST_GN_20BD_RETURN: `14.38%` (`final_equity = 1,143,800`, `equity_delta = 143,800`)
- PRE_GN_20BD_RETURN: `15.406%` (`final_equity = 1,154,060`, `equity_delta = 154,060`)
- PNL_USED_FOR_DESIGN_JUDGMENT: `NO`

The acceptance decision is based on Current PIT BUY quality and semantic regression evidence, not final return.

## Required Answers

- BOTH_BUY_COUNT: `53`
- PRE_GN_ONLY_BUY_COUNT: `7`
- GN_ONLY_BUY_COUNT: `7`
- ACTUAL_BUY_OVERLAP_RATE: `79.10%`
- FIRST_ACTUAL_BUY_DIVERGENCE_DATE: `2023-06-16`
- FIRST_ACTUAL_BUY_DIVERGENCE_SYMBOL: `50250`
- FIRST_ACTUAL_BUY_DIVERGENCE_CAUSE: `DIRECT_GN_PRIORITY_EFFECT / quality-class-first removed; Current rank-first priority preserved`
- PAIRED_REPLACEMENT_COUNT: `3`
- GN_ACTUAL_BUY_RANK_IMPROVEMENT_RATE: `33.33%`
- GN_CURRENT_PIT_PRIORITY_IMPROVEMENT_COUNT: `1`
- PRE_GN_CURRENT_PIT_PRIORITY_BETTER_COUNT: `2`
- INCOMPARABLE_COUNT: `0`
- PRE_GN_LOWER_PRIORITY_BUY_ROOT_CAUSES: `QUALITY_CLASS_FIRST=1; later path-dependent=13 exclusive observations; no direct history/relationship/accepted-increment cause found`
- GN_ONLY_BUY_ROOT_CAUSES: `rank-first Current PIT priority reached capital=7; history/ownership/campaign=0`
- PRE_GN_ONLY_BUY_GN_SKIP_REASONS: `no requested increment=3; higher priority/residual capital=2; lot/zero quantity=2`
- PRE_GN_BUY_NEW_COUNT: `52`
- GN_BUY_NEW_COUNT: `52`
- PRE_GN_BUY_ADD_COUNT: `8`
- GN_BUY_ADD_COUNT: `8`
- PRE_GN_WEIGHTED_AVG_PURCHASED_RANK: `16.7465`
- GN_WEIGHTED_AVG_PURCHASED_RANK: `16.2812`
- PRE_GN_MEDIAN_PURCHASED_RANK: `17`
- GN_MEDIAN_PURCHASED_RANK: `16`
- DIRECT_GN_PRIORITY_EFFECT_COUNT: `1`
- DOWNSTREAM_PATH_EFFECT_COUNT: `13`
- 50250_TRACE_COMPLETE: `YES`
- 89180_DIVERGENCE_TRACE_COMPLETE: `YES`
- REGIME_BUY_CHARACTERIZATION_COMPLETE: `YES`
- PRE_GN_BUY_EXIT_BUY_CYCLE_COUNT: `10`
- GN_BUY_EXIT_BUY_CYCLE_COUNT: `10`
- GN_NEW_CHURN_RISK_COUNT: `1`
- GN_MEANINGFUL_REQUALIFICATION_COUNT: `1`
- RECENT_EXIT_GUARD_BYPASS_COUNT: `0`
- SELL_SEMANTIC_REGRESSION_FOUND: `NO`
- WINNER_AUTHORITY_REGRESSION_FOUND: `NO`
- SIZING_SEMANTIC_REGRESSION_FOUND: `NO`
- CASH_SEMANTIC_REGRESSION_FOUND: `NO`
- ADD_SAFETY_BYPASS_COUNT: `0`
- G129_REGRESSION_COUNT: `0`
- POST_GN_20BD_RETURN: `14.38%`
- PRE_GN_20BD_RETURN: `15.406%`
- PNL_USED_FOR_DESIGN_JUDGMENT: `NO`
- GN_ACTUAL_BUY_CURRENT_PIT_PRIORITY_ACCEPTED: `YES`
- GN_BUY_SELECTION_DIRECTION_ACCEPTED: `YES`
- CHURN_NO_REGRESSION_ACCEPTED: `YES`
- SHORT_DYNAMIC_VALIDATION_ACCEPTED: `YES`
- LONG_HORIZON_VALIDATION_READY: `YES`
- DIRECT_PRODUCTION_PROMOTION_READY: `NO`
- NEXT_STEP: `Run long-horizon validation with the fixed churn contract from Phase32-GQ1/GR, continue excluding future PnL from BUY-quality threshold decisions, and require zero recent-exit bypass plus unchanged SELL/Winner/Sizing/Cash authority before production promotion.`

Final Judgment: GNのhistory-neutral BUY priorityは20BD actual pathでもCurrent PIT rank-first方向へBUY selectionを寄せ、history/relationship/accepted-increment依存を再導入せず、SELL・Winner・Sizing・Cash・ADD Safety・G129・Recent Exit Guardの新規semantic regressionは確認されない。ただしdirect production promotionはlong-horizon validation完了まで保留。
