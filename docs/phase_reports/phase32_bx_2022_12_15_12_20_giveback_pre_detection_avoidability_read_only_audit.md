# Phase32-BX — 2022-12-15→12-20 Giveback Pre-Detection & Avoidability READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: READ-ONLY
- Audited window: `2022-12-14` through `2022-12-20`
- Run status when inspected: `RUNNING`
- Run continuation point when inspected: `2022-12-21:submit`

No code, config, model, threshold, weight, PM/SELL/HOLD semantics, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run mutation was performed. The running Historical validation was not interrupted.

Future outcomes were used only after PIT classification to describe economic consequence.

## Giveback Confirmation

The episode is confirmed from target run valuation artifacts.

| Date | Cash | Market value | Equity | Exposure |
|---|---:|---:|---:|---:|
| 2022-12-15 | 307,320 | 845,920 | 1,153,240 | 73.35% |
| 2022-12-16 | 110,220 | 1,024,580 | 1,134,800 | 90.29% |
| 2022-12-19 | 136,250 | 965,000 | 1,101,250 | 87.63% |
| 2022-12-20 | 624,900 | 466,100 | 1,091,000 | 42.72% |

- Peak equity: `1,153,240` on `2022-12-15`
- Trough equity in episode: `1,091,000` on `2022-12-20`
- Total giveback: `-62,240`

## Loss Attribution

Daily equity changes:

- `2022-12-16`: `-18,440`
- `2022-12-19`: `-33,550`
- `2022-12-20`: `-10,250`

Dominant valuation/realization contributors by day:

| Period | Symbol | Mechanism | Approx contribution | Share of daily loss |
|---|---:|---|---:|---:|
| 12/15→12/16 | 97310 | held, price 2114→2031 | -8,300 | 45.0% |
| 12/15→12/16 | 99840 | held, price 1572.8→1513.0 | -5,980 | 32.4% |
| 12/15→12/16 | 23350 | held, price 1113→1072 | -4,100 | 22.2% |
| 12/16→12/19 | 97310 | held, price 2031→1830 | -20,100 | 59.9% |
| 12/16→12/19 | 31500 | held, price 2036→1961 | -7,500 | 22.4% |
| 12/16→12/19 | 14910 | held, price 600→580 | -2,000 | 6.0% |
| 12/16→12/19 | 72730 | held, price 172.9→156.2 | -1,670 | 5.0% |
| 12/16→12/19 | 45410 | held, price 121→114, qty 200 | -1,400 | 4.2% |
| 12/19→12/20 | 31500 | held, price 1961→1908 | -5,300 | 51.7% |
| 12/19→12/20 | 61440 | held, price 1542→1510 | -3,200 | 31.2% |
| 12/19→12/20 | 23350 | held, price 1084→1054 | -3,000 | 29.3% |
| 12/19→12/20 | 97310 | sold, prior close 1830 vs sell 1812 | -1,800 | 17.6% |

The dominant full-episode contributor is `97310`, with about `-30,200` from the 12/15 close through 12/20 sell execution. Secondary contributors are `31500`, `99840`, `23350`, `61440`, `14910`, `72730`, and `45410`.

## Position-Level PIT Timeline

The following table uses decision-time artifacts only for the decision classification.

| Symbol | 12/14 | 12/15 | 12/16 | 12/19 | 12/20 | Classification |
|---:|---|---|---|---|---|---|
| 97310 | PM `REDUCE`, `peak_drawdown_warning`; lot-blocked raw 33→0; BQ `SHADOW_INSUFFICIENT_EVIDENCE`; NO_ORDER | HOLD, `trend_continuation` | HOLD, `trend_continuation` | HOLD, `hold_score_above_exit_threshold` after large same-day drawdown | native EXIT, `trend_and_opportunity_broken` | `PREDETECTED_BUT_UNDER_MATERIALIZED` |
| 99840 | HOLD, `downside_risk_contained` | HOLD, `downside_risk_contained` | HOLD, `downside_risk_contained` | HOLD, `downside_risk_contained` | native EXIT, `trend_and_opportunity_broken` | `HOLD_SEMANTIC_CONFLICT` / partly new deterioration |
| 23350 | HOLD, `trend_continuation` | HOLD, `trend_continuation` | HOLD, `hold_score_above_exit_threshold` | HOLD, `trend_continuation` | HOLD, `hold_score_above_exit_threshold` | `HOLD_SEMANTIC_CONFLICT` |
| 31500 | not held | not held | BUY_NEW, 100 shares | HOLD, `trend_continuation`, `downside_risk_contained` | REDUCE, `risk_increased_but_trend_not_broken`; lot-blocked raw 25→0; BQ `SHADOW_INSUFFICIENT_EVIDENCE`; NO_ORDER | `NOT_PREDETECTABLE_BEFORE_ENTRY`; later `LOT_GRANULARITY_RELATED` |
| 61440 | HOLD, `trend_continuation` | HOLD, `trend_continuation` | HOLD, `trend_continuation` | HOLD, `trend_continuation` | HOLD, `hold_score_above_exit_threshold` | `HOLD_SEMANTIC_CONFLICT` |
| 14910 | BUY_NEW, 100 shares | HOLD, `trend_continuation`, `downside_risk_contained` | HOLD, `hold_score_above_exit_threshold` | PM REDUCE, `risk_increased_but_trend_not_broken`; BQ `SHADOW_FULL_EXIT` in order-plan evidence, but actual submit reused existing 58010 pending | BQ/SELL_EXIT submitted and filled | `PREDETECTED_AND_MANAGED_WITH_ONE_DAY_MATERIALIZATION_LAG` |
| 72730 | HOLD, `positive_expected_edge`, `downside_risk_contained` | HOLD, same | HOLD, same | HOLD, same, despite price drop | native EXIT, `hard_stop_current_return`, `profit_retention_break` | `HOLD_SEMANTIC_CONFLICT` / new hard-stop confirmation |
| 45410 | not held | not held | BUY_NEW, 200 shares | HOLD, `trend_continuation`, `positive_expected_edge`, `downside_risk_contained` | native EXIT, `hard_stop_current_return` | `MIXED`; early HOLD authority existed, then hard-stop |
| 58030 | not held | BUY_NEW, 100 shares | HOLD, `hold_score_above_exit_threshold` | REDUCE, `risk_increased_but_trend_not_broken`; lot-blocked raw 25→0; BQ `SHADOW_INSUFFICIENT_EVIDENCE`; NO_ORDER | native EXIT, `trend_and_opportunity_broken` | `PREDETECTED_BUT_UNDER_MATERIALIZED`, small loss |
| 58010 | HOLD, `trend_continuation` | HOLD, `trend_continuation` | REDUCE, `risk_increased_but_trend_not_broken`; lot-blocked raw 25→0; BQ `SHADOW_INSUFFICIENT_EVIDENCE`; NO_ORDER | REDUCE again; BQ `SHADOW_HOLD`; submitted as sell via existing pending path and filled | not held | `PREDETECTED_AND_MANAGED`, small effect |

## Earliest Warning Dates

- Earliest material PIT deterioration: `2022-12-14` for `97310` via PM `REDUCE` / `peak_drawdown_warning`.
- Earliest PM sell-side action in the episode: `2022-12-14` for `97310`.
- Earliest native PM EXIT affecting dominant contributors: `2022-12-20`.
- PM REDUCE before the major 12/19 loss: YES, specifically `97310` on `2022-12-14` and `58010` on `2022-12-16`.
- PM EXIT before the major 12/19 loss for dominant contributors: NO. The material 12/20 exits arrived after the largest daily giveback.

## REDUCE Materialization and BQ

Observed REDUCE / lot-block / BQ cases in the episode:

| Date | Symbol | PM reason | Desired REDUCE | Executable | BQ decision | Production result | Later loss relevance |
|---|---:|---|---:|---:|---|---|---|
| 2022-12-14 | 97310 | `peak_drawdown_warning` | 33 | 0 | `SHADOW_INSUFFICIENT_EVIDENCE` | NO_ORDER | high |
| 2022-12-15 | 39850 | `risk_increased_but_trend_not_broken` | 25 | 0 | `SHADOW_INSUFFICIENT_EVIDENCE` | NO_ORDER; native EXIT next day | low |
| 2022-12-16 | 58010 | `risk_increased_but_trend_not_broken` | 25 | 0 | `SHADOW_INSUFFICIENT_EVIDENCE` | NO_ORDER; sold 12/19 | low |
| 2022-12-19 | 58010 | `risk_increased_but_trend_not_broken` | 25 | 0 | `SHADOW_HOLD` | existing pending sell submitted/fill | low |
| 2022-12-19 | 58030 | `risk_increased_but_trend_not_broken` | 25 | 0 | `SHADOW_INSUFFICIENT_EVIDENCE` | NO_ORDER; native EXIT 12/20 | low |
| 2022-12-19 | 14910 | `risk_increased_but_trend_not_broken` | 25 | 0 | `SHADOW_FULL_EXIT` | BQ order-plan evidence exists, but actual submit used existing 58010 pending | low/moderate |
| 2022-12-20 | 14910 | `risk_increased_but_trend_not_broken` | 25 | 0 | `SHADOW_FULL_EXIT` | SELL_EXIT submitted/fill | after most loss |
| 2022-12-20 | 31500 | `risk_increased_but_trend_not_broken` | 25 | 0 | `SHADOW_INSUFFICIENT_EVIDENCE` | NO_ORDER | remaining held loss |

Old repeated pattern reproduced for `97310`:

PM detects weakness -> REDUCE -> 100-share lot makes REDUCE non-executable -> BQ returns `SHADOW_INSUFFICIENT_EVIDENCE` -> position remains -> subsequent material loss.

This is the cleanest avoidability evidence in the episode.

## HOLD Authority Consistency

Positive continuation authority existed for several positions before loss:

- `97310`: `trend_continuation` on 12/15 and 12/16.
- `23350`: `trend_continuation` on 12/14, 12/15, and 12/19.
- `61440`: `trend_continuation` through 12/19.
- `72730`: `positive_expected_edge` and `downside_risk_contained` through 12/19.
- `45410`: `trend_continuation`, `positive_expected_edge`, and `downside_risk_contained` on 12/19.

However, several HOLDs look semantically fragile rather than strongly protective:

- `99840` remained HOLD on repeated `downside_risk_contained` despite price deterioration, then native EXIT on 12/20.
- `23350` and `61440` continued under trend/hold-score reasons while contributing to 12/20 losses.
- `72730` remained HOLD under positive expected edge/downside containment through 12/19, then hard-stop/profit-retention break appeared on 12/20.
- `97310` reverted from 12/14 REDUCE to 12/15-12/16 HOLD, then suffered the largest loss before 12/20 EXIT.

`HOLD_AUTHORITY_SEMANTIC_CONFLICT_FOUND = YES`

This is not a threshold recommendation. It is a characterization that HOLD authority sometimes appears to require terminal break confirmation rather than acting on earlier deterioration.

`PROFIT_CUSHION_HOLD_REGRESSION_FOUND = NO_CONCRETE_PROFIT_CUSHION_HOLD_REGRESSION`

`TREND_NOT_BROKEN_INERTIA_FOUND = YES`

## BQ Effectiveness During Episode

BQ helped or attempted to help:

- `14910`: BQ `SHADOW_FULL_EXIT` appeared on 12/19 and again on 12/20; actual sell occurred on 12/20.

BQ did not capture material contributors where it mattered most:

- `97310`: BQ returned `SHADOW_INSUFFICIENT_EVIDENCE` on 12/14, then the position became the dominant giveback contributor.
- `58030`: BQ returned `SHADOW_INSUFFICIENT_EVIDENCE` on 12/19, then native EXIT occurred on 12/20; economic effect was small.
- `31500`: BQ returned `SHADOW_INSUFFICIENT_EVIDENCE` on 12/20; this was contemporaneous with, not prior to, the episode loss.

Therefore the remaining giveback is not only a BQ ambiguity problem. It is mixed:

- a BQ insufficient-evidence / lot-block materialization gap for `97310`;
- a separate PM/HOLD/SELL confirmation-lag gap for several held names;
- exposure timing amplified by new buys on 12/16.

## Exposure Timing

Exposure path:

- 12/15: `73.35%`
- 12/16: `90.29%`
- 12/19: `87.63%`
- 12/20: `42.72%`

12/16 exposure increase was driven by:

- BUY 31500: 100 shares at `2014.0`, about `201,400` cash outflow.
- BUY 45410: 200 shares at `125.0`, about `25,000` cash outflow.
- SELL 39850: about `29,300` cash inflow.

Net cash fell by `197,100`, increasing exposure before the 12/19 loss. `31500` then contributed `-7,500` on 12/19 and `-5,300` on 12/20.

12/20 exposure collapse was caused by seven SELLs:

- 66320, 45410, 99840, 72730, 58030, 97310, 14910.

The evidence that caused the 12/20 wave was mixed:

- Already present earlier: `97310` REDUCE warning on 12/14; `58030` and `14910` REDUCE warnings on 12/19.
- Not clearly present as sell authority earlier: `99840`, `66320`, `72730`, `45410` native EXIT evidence appears on 12/20.
- Still not sold: `31500` was REDUCE/lot-blocked on 12/20, BQ insufficient, and remained held.

`12_20_RISK_REDUCTION_EVIDENCE_ALREADY_PRESENT_EARLIER = PARTIAL`

## Avoidability Classification

| Symbol | Classification | Avoidability note |
|---:|---|---|
| 97310 | `PREDETECTED_BUT_UNDER_MATERIALIZED` and `LOT_GRANULARITY_RELATED` | strongest avoidability support; REDUCE warning existed 12/14 before large losses |
| 99840 | `HOLD_SEMANTIC_CONFLICT` | deterioration before native EXIT, but no earlier explicit sell-side action observed |
| 23350 | `HOLD_SEMANTIC_CONFLICT` | remained HOLD; not clearly actionable under current contract |
| 31500 | `NOT_PREDETECTABLE_BEFORE_ENTRY`; later `LOT_GRANULARITY_RELATED` | 12/16 buy raised exposure; first REDUCE was 12/20 |
| 61440 | `HOLD_SEMANTIC_CONFLICT` | remained HOLD through episode |
| 14910 | `PREDETECTED_AND_MANAGED_WITH_ONE_DAY_MATERIALIZATION_LAG` | BQ FULL_EXIT evidence existed 12/19; actual sell 12/20 |
| 72730 | `HOLD_SEMANTIC_CONFLICT` | positive expected edge/downside containment persisted until 12/20 hard-stop |
| 45410 | `MIXED` | bought 12/16; held 12/19; hard-stop 12/20 |
| 58030 | `PREDETECTED_BUT_UNDER_MATERIALIZED`, small | 12/19 REDUCE/BQ insufficient, 12/20 native EXIT |
| 58010 | `PREDETECTED_AND_MANAGED`, small | 12/16 REDUCE/BQ insufficient, sold 12/19 |

Estimated avoidable giveback:

- Strongly supported: about `30,200` for `97310` from 12/15 close to 12/20 sell execution, because an authoritative PM REDUCE warning already existed on 12/14 but was not materially executable and BQ did not promote.
- Weak/small additions: `58030` about `50`; not material.
- Not counted as avoidable: positions whose first explicit sell authority appeared only on 12/20, and cases where HOLD authority was still positive under current contract.

`AVOIDABLE_GIVEBACK_SUPPORTED = PARTIAL`

`ESTIMATED_AVOIDABLE_GIVEBACK_AMOUNT = ABOUT_30,200_STRONGLY_SUPPORTED_BY_97310_ONLY`

## Required Final Answers

1. `GIVEBACK_EPISODE_CONFIRMED = YES`
2. `PEAK_EQUITY = 1,153,240_ON_2022_12_15`
3. `TROUGH_EQUITY = 1,091,000_ON_2022_12_20`
4. `TOTAL_GIVEBACK = -62,240`
5. `DOMINANT_LOSS_CONTRIBUTORS = 97310, 31500, 99840, 23350, 61440, 14910, 72730, 45410`
6. `EARLIEST_MATERIAL_PIT_WARNING_DATE = 2022-12-14_FOR_97310`
7. `EARLIEST_PM_SELL_SIDE_ACTION_DATE = 2022-12-14_FOR_97310_REDUCE`
8. `PRE_LOSS_WARNING_EXISTED = YES`
9. `PM_REDUCE_BEFORE_MAJOR_LOSS = YES`
10. `PM_EXIT_BEFORE_MAJOR_LOSS = NO_FOR_DOMINANT_CONTRIBUTORS`
11. `LOT_BLOCKED_REDUCE_INVOLVED = YES`
12. `BQ_FULL_EXIT_INVOLVED = YES_FOR_14910; NO_FOR_DOMINANT_97310`
13. `BQ_HOLD_OR_INSUFFICIENT_LATER_LOSS_CASES = YES_97310_AND_SMALLER_58030`
14. `HOLD_AUTHORITY_SEMANTIC_CONFLICT_FOUND = YES`
15. `PROFIT_CUSHION_HOLD_REGRESSION_FOUND = NO_CONCRETE_PROFIT_CUSHION_HOLD_REGRESSION`
16. `TREND_NOT_BROKEN_INERTIA_FOUND = YES`
17. `12_20_RISK_REDUCTION_EVIDENCE_ALREADY_PRESENT_EARLIER = PARTIAL`
18. `AVOIDABLE_GIVEBACK_SUPPORTED = PARTIAL`
19. `ESTIMATED_AVOIDABLE_GIVEBACK_AMOUNT = ABOUT_30,200_STRONGLY_SUPPORTED`
20. `PRIMARY_GIVEBACK_MECHANISM = MIXED_PREDETECTED_LOT_BLOCKED_97310_PLUS_HOLD_CONFIRMATION_LAG_PLUS_12_16_EXPOSURE_REEXPANSION`
21. `BQ_REMAINING_GAP = YES_FOR_INSUFFICIENT_EVIDENCE_ON_MATERIAL_LOT_BLOCKED_97310`
22. `SEPARATE_PM_HOLD_SELL_GAP = YES`
23. `PRODUCTION_CHANGE_JUSTIFIED_NOW = NO_READ_ONLY_CHARACTERIZATION_ONLY`
24. `NEXT_RECOMMENDED_STEP = Design a focused PIT-only follow-up around 97310-style pre-detected lot-blocked REDUCE and separate HOLD authority confirmation-lag cases; do not tune directly from this single outcome episode.`
25. `FINAL_JUDGMENT = PHASE32_BX_GIVEBACK_MIXED_PREDETECTED_UNDER_MATERIALIZED_AND_HOLD_SEMANTIC_GAP_CHARACTERIZED_READ_ONLY`

