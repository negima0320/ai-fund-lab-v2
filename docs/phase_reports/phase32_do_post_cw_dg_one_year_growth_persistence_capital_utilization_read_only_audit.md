# Phase32-DO — Post-CW/DG One-Year Growth Persistence / Capital Utilization READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Usable completed window: `2022-10-03` through `2023-10-26`
- Completed business days in window: 264
- Run state at audit time: `RUNNING`, next job observed during read-only inspection: `2023-10-31:market_refresh`
- Current source identity: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- Evidence used: target-run daily artifacts, current source/SoT references, Phase32-CW/CX/CY/CZ/DG reports.
- Historical PnL use: diagnostic only for growth, drawdown, materiality, and campaign behavior characterization. It was not used to choose thresholds, weights, features, ranking formulas, or parameters.
- Production change executed: NO
- Target run mutated: NO

## Reference Baseline

Phase32-CX found the legacy long-horizon failure mode as time-accumulating prior-owned/REENTRY suppression after April, with zero canonical REENTRY fills in the inspected legacy window and a growing flat prior-owned burden. Phase32-CW removed the broad REENTRY-only rank penalty, portfolio rank hurdle, and duplicate BQ gate while preserving cooldown, unresolved-churn protection, prior-cause recovery, and fail-closed semantics. Phase32-DG then promoted tick-normalized trend/momentum evidence without adding a low-price blacklist or PnL-derived threshold.

The current one-year run therefore tests whether the repaired baseline still decays over time, and where compounding remains structurally constrained.

## Growth Persistence

Monthly equity and exposure:

| Month | End equity | Monthly return | Avg exposure | Median exposure | Avg cash | Avg positions | Days <60% exp | Days >90% exp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-10 | 1,066,780 | 6.68% | 72.8% | 75.4% | 284,498 | 9.6 | 4 | 1 |
| 2022-11 | 1,191,220 | 11.67% | 87.4% | 88.3% | 141,808 | 12.0 | 0 | 8 |
| 2022-12 | 1,158,100 | -2.78% | 74.8% | 76.9% | 293,633 | 10.6 | 5 | 6 |
| 2023-01 | 1,229,680 | 6.18% | 72.3% | 68.8% | 324,134 | 11.7 | 4 | 3 |
| 2023-02 | 1,203,900 | -2.10% | 87.3% | 90.5% | 156,127 | 13.9 | 0 | 10 |
| 2023-03 | 1,418,920 | 17.86% | 81.4% | 86.2% | 231,952 | 11.1 | 1 | 7 |
| 2023-04 | 1,612,250 | 13.63% | 74.2% | 74.9% | 389,979 | 8.7 | 2 | 1 |
| 2023-05 | 1,675,240 | 3.91% | 81.7% | 84.7% | 294,098 | 11.8 | 2 | 6 |
| 2023-06 | 1,752,810 | 4.63% | 86.0% | 88.1% | 239,936 | 13.7 | 0 | 9 |
| 2023-07 | 1,767,660 | 0.85% | 86.2% | 87.5% | 240,526 | 15.4 | 0 | 8 |
| 2023-08 | 1,785,420 | 1.00% | 78.5% | 80.4% | 375,433 | 14.2 | 3 | 4 |
| 2023-09 | 1,848,850 | 3.55% | 80.5% | 85.1% | 358,837 | 16.5 | 3 | 5 |
| 2023-10 | 1,800,480 | -2.62% | 52.0% | 54.1% | 878,184 | 10.2 | 13 | 0 |

Equity rose from the 1,000,000 initial cash baseline to 1,800,480 by `2023-10-26` (+80.05%). The rolling high-water mark reached 1,868,050 on `2023-09-27`. There were 54 new-high days in the usable window. The longest no-new-high stretch was 33 business days. The maximum drawdown from rolling HWM was -9.49% on `2023-04-20`.

Major windows:

| Window | Dates | Return | In-window max drawdown | Avg exposure |
|---|---|---:|---:|---:|
| Dec 2022 correction | `2022-12-01` to `2022-12-30` | -2.78% | -4.78% | 74.8% |
| Feb-Mar 2023 | `2023-02-01` to `2023-03-31` | 15.39% | -6.30% | 84.1% |
| May 2023 | `2023-05-01` to `2023-05-31` | 3.91% | -8.62% | 81.7% |
| Jul-Aug 2023 | `2023-07-03` to `2023-08-31` | 1.86% | -2.94% | 82.1% |
| Late Sep-Oct 2023 | `2023-09-15` to `2023-10-26` | -2.22% | -4.77% | 59.1% |
| Post-April | `2023-04-03` to `2023-10-26` | 26.89% | -9.49% | 77.5% |

Classification:

- `TIME_ACCUMULATING_GROWTH_DECAY_REPRODUCED = NO`
- `POST_APRIL_GROWTH_PERSISTENCE = PRESENT_WITH_LATE_SEP_OCT_DEFENSIVE_SOFT_PATCH`

The old post-April plateau is not reproduced: April, May, June, July, August, and September all closed above the prior month, and the run made new highs as late as `2023-09-27`. October-to-date is weaker and cash-heavy, but it is a correction/defensive utilization episode rather than evidence of monotonic time-accumulating opportunity decay.

## REENTRY Health

Portfolio Construction evidence in the window:

- `semantic_buy_type=REENTRY` rows: 5,196
- `REENTRY_ELIGIBLE`: 207
- `REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE`: 2,286
- `REENTRY_INSUFFICIENT_EVIDENCE`: 1,341
- `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION`: 791
- `REENTRY_NOT_ELIGIBLE_PRIOR_EXIT_CONTEXT`: 571
- Recovery status counts: `PASS=510`, `REVIEW_REQUIRED=1,486`, `FAIL_CLOSED=3,200`
- Business days since prior exit: average 47.7, median 18, max 276
- Top recurring REENTRY symbols include `76470`, `89180`, `94340`, `67310`, `91070`, `54010`, `83060`, `77760`, `65730`, and `31330`.

Important execution-label nuance:

- Ledger/fill `source_decision_type` counts show no literal `REENTRY` fill label.
- Matching fills back to same-day PC semantics shows 80 funded semantic REENTRY buys, 67 symbols, notional 5,879,710.
- These fills are persisted as `source_decision_type=BUY_NEW` while PC carries `semantic_buy_type=REENTRY`; this is a characterization note, not evidence of renewed universe erosion in this audit.

REENTRY blocker profile:

- Current-evidence not satisfied is the largest explicit block.
- Insufficient-evidence/review cases remain material: 1,341 rows, led by `reentry_unknown_prior_context_independence_not_established` and `recoverable_prior_exit_context_defect`.
- Churn protection remains active early after exits and does not accumulate into a permanent same-symbol ban by itself.

Classification:

- `REENTRY_UNIVERSE_EROSION_REPRODUCED = NO`
- `CW_REENTRY_LONG_HORIZON_EFFECTIVE = YES_WITH_REMAINING_REVIEW_FRICTION`

CW eliminated the Phase32-CX-style broad time-accumulating suppression. The remaining REENTRY limits are evidence-specific: current recovery quality, prior-context sufficiency, and repeated unresolved churn, rather than a flat prior-owned universe penalty.

## BUY_NEW / REENTRY / BUY_ADD

Execution/fill view:

| Type | Fill count | Notional | Symbols | Campaigns |
|---|---:|---:|---:|---:|
| BUY_NEW ledger label | 456 | 35,572,930 | 376 | 456 |
| BUY_ADD | 11 | 211,930 | 4 | 5 |
| SELL_EXIT | 446 | 35,495,320 | 370 | 446 |
| SELL_REDUCE | 50 | 491,730 | 24 | 27 |

Semantic buy view after matching PC to fills:

| Semantic type | Fill count | Notional | Symbols |
|---|---:|---:|---:|
| BUY_NEW | 376 | 29,693,220 | 376 |
| REENTRY | 80 | 5,879,710 | 67 |
| BUY_ADD | 11 | 211,930 | 4 |

PM and PC ADD evidence:

- PM decisions: `ADD=301`, `HOLD=1,994`, `REDUCE=675`, `EXIT=262`
- PC ADD candidates detected: 152
- Positive accepted incremental weight: 22
- Positive lot-aware accepted incremental weight: 15
- BUY_ADD fills: 11
- BUY_ADD campaigns: 5
- Campaigns with 2+ ADD fills: 2
- Campaigns with 3+ ADD fills: 2
- Top BUY_ADD campaign: `94320 / pc-7c5bd9294d48b016-94320-0001`, 5 ADD fills, still open on `2023-10-26` with 700 shares and 6.75% weight.

Open campaigns on `2023-10-26`:

| Symbol | Campaign | Market value | Weight | Quantity | Opened |
|---|---|---:|---:|---:|---|
| 94320 | `pc-7c5bd9294d48b016-94320-0001` | 121,450 | 6.75% | 700 | 2023-01-23 |
| 71800 | `pc-2593f6268c506145-71800-0001` | 88,880 | 4.94% | 100 | 2023-10-16 |
| 23510 | `pc-93db22a1482d44a8-23510-0001` | 58,400 | 3.24% | 100 | 2023-10-24 |
| 80950 | `pc-9d46cb70d234169e-80950-0001` | 52,500 | 2.92% | 100 | 2023-10-20 |
| 94340 | `pc-8d0b3d71adb1e835-94340-0001` | 50,460 | 2.80% | 300 | 2023-06-13 |
| 47660 | `pc-95c84fbd811e0890-47660-0001` | 44,800 | 2.49% | 200 | 2023-10-12 |
| 92630 | `pc-681ebb7f24f91f46-92630-0001` | 39,800 | 2.21% | 200 | 2023-10-12 |
| 98760 | `pc-25fa7d36ebf95168-98760-0001` | 27,100 | 1.51% | 100 | 2023-10-23 |

Classification:

- `WINNER_CAPITALIZATION_STATUS = MATERIAL_BOTTLENECK`

The system can retain and add to winners, but it does so rarely relative to PM ADD intent and relative to BUY_NEW turnover. One campaign graduated meaningfully (`94320` to 700 shares / 6.75%), but most funded capital still flows through many fresh 100-share campaigns instead of repeated incremental capitalization of strongest continuing positions.

## ADD Suppression Root-Cause Profile

Observed ADD suppression is not caused by absence of PM ADD signal. PM produced 301 ADD decisions. The largest loss of ADD materialization occurs downstream in PC/Entry/BQ/capital competition/lot feasibility:

- PC ADD candidates: 152
- PC accepted incremental weight: 22
- Lot-aware positive ADD: 15
- Actual BUY_ADD fills: 11

Blocked ADD profile from PC evidence:

| Cause class | Count |
|---|---:|
| BUY Quality / Entry / continuation caution | 129 |
| Position cap / capacity | 1 |

Additional capital-competition/cash artifacts:

- `final_winner_type` occurrences include `CASH_OPTIONALITY`, `NEW_BUY`, `PC_FINAL_DISCRETE_AUTHORITY`, and `ADD`.
- Cash reason evidence includes `UNAVOIDABLE_LOT_RESIDUAL`, `VALID_POLICY_RESERVE`, `NO_VALID_COMPETITOR`, and `CONCENTRATION_BLOCK`.

Classification:

- `ADD_SUPPRESSION_ROOT_CAUSE_PROFILE = DOWNSTREAM_PC_ENTRY_BQ_AND_MARGINAL_CAPITAL_COMPETITION_DOMINANT; PM_SIGNAL_PRESENT; LOT_AND_CAP_SECONDARY`

This is consistent with Phase32-CY's architecture finding: the system has BUY_NEW/BUY_ADD/Cash competition, but ADD still lacks a high-resolution marginal-JPY value unit strong enough to repeatedly beat NEW/Cash for the best continuing campaigns.

## Capital Utilization

Full-window exposure:

- Average exposure: 78.3%
- Median exposure: 82.6%
- Days exposure <60%: 37
- Days exposure >90%: 68

Capital utilization by phase:

- Oct-Nov 2022 and Feb-Jun 2023 show high deployment, often near or above 85% exposure.
- Post-April average exposure remains 77.5%, so there is no broad permanent cash drag.
- October 2023-to-date drops to 52.0% average exposure, 878,184 average cash, and 13 days below 60% exposure.

Classification:

- `CAPITAL_UTILIZATION_STATUS = GENERALLY_ACTIVE_WITH_LATE_WINDOW_DEFENSIVE_CASH_AND_OPPORTUNITY_ALLOCATION_FRICTION`

The October cash build appears partly healthy defensive cash after a September HWM, but it is also linked to low deployable security competition and limited ADD capitalization. It should not be treated as pure risk-control success or pure defect without a narrower follow-up.

## Portfolio Breadth vs Concentration

The run funds broad BUY_NEW flow:

- 456 BUY_NEW-labeled fills across 376 symbols.
- Final open book has 8 open campaigns, but the full window includes substantial turnover and many short-lived 100-share starts.
- Concentration in final open book is moderate: top open campaign is 6.75%; top 3 open campaigns sum approximately 14.93% of equity.

Classification:

- `PORTFOLIO_FRAGMENTATION_STATUS = BROAD_STARTER_TURNOVER_WITH_LIMITED_WINNER_CONCENTRATION`

The issue is not simply "too many positions" at the final date. The structural pattern is high starter turnover plus low repeated ADD conversion, which limits concentration into the few campaigns that prove durable.

## Winner Retention

Winner retention has improved compared with earlier plateau analyses:

- The run retains long-lived winners: `94320` remains open from `2023-01-23` through `2023-10-26`, reaches 700 shares, and carries the largest final open weight.
- `94340` remains open from `2023-06-13` at 300 shares.
- Full-window drawdown remained controlled: max rolling drawdown -9.49%; late Sep-Oct drawdown -4.77%.

Remaining limitation:

- Many winners are retained but not repeatedly capitalized.
- SELL/REDUCE activity remains active enough to control downside, but the capital released often returns to BUY_NEW/Cash rather than compounding existing strongest campaigns.

Classification:

- `WINNER_RETENTION_STATUS = FUNCTIONAL_AND_IMPROVED; CAPITALIZATION_LAG_REMAINS`
- `DOWNSIDE_CONTROL_STATUS = EFFECTIVE_WITH_MODERATE_DRAWDOWNS`

## Opportunity Flow Over Time

Monthly PC/fill flow:

| Month | BUY_NEW candidates | REENTRY candidates | REENTRY eligible | ADD candidates | BUY_NEW fills | Semantic REENTRY fills | BUY_ADD fills |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2022-10 | 687 | 152 | 8 | 17 | 41 | 3 | 3 |
| 2022-11 | 590 | 242 | 17 | 29 | 30 | 8 | 1 |
| 2022-12 | 671 | 314 | 8 | 3 | 33 | 1 | 0 |
| 2023-01 | 496 | 358 | 13 | 13 | 36 | 6 | 1 |
| 2023-02 | 523 | 307 | 21 | 28 | 26 | 7 | 4 |
| 2023-03 | 514 | 392 | 19 | 24 | 29 | 7 | 1 |
| 2023-04 | 400 | 458 | 20 | 4 | 31 | 7 | 0 |
| 2023-05 | 271 | 558 | 19 | 1 | 34 | 8 | 1 |
| 2023-06 | 368 | 516 | 20 | 16 | 39 | 6 | 0 |
| 2023-07 | 427 | 399 | 20 | 0 | 36 | 5 | 0 |
| 2023-08 | 436 | 454 | 18 | 0 | 39 | 6 | 0 |
| 2023-09 | 261 | 504 | 12 | 4 | 43 | 10 | 0 |
| 2023-10 | 212 | 542 | 12 | 13 | 39 | 6 | 0 |

Classification:

- `OPPORTUNITY_FLOW_DECAY_OVER_TIME = NOT_BROADLY_REPRODUCED; BUY_NEW_SUPPLY_SOFTENS_LATE, REENTRY_SUPPLY_PERSISTS, ADD_FLOW_REMAINS_THIN`

There is no evidence that opportunity flow disappears after April. REENTRY candidates actually rise into May/June and remain high in September/October. The late-window weakness is a combination of lower BUY_NEW candidate supply, more cash optionality, and still-limited ADD conversion.

## Top Remaining Structural Bottlenecks

Ranked bottlenecks:

1. Winner capitalization / ADD marginal capital resolution. PM ADD signal exists, but only 11 BUY_ADD fills materialize from 301 PM ADD decisions and 152 PC ADD candidates. This is the largest compounding bottleneck.
2. High-resolution NEW vs REENTRY vs ADD vs Cash marginal value. Existing architecture recognizes the limitation; current evidence shows capital often chooses NEW/Cash while strongest continuing campaigns receive few increments.
3. Residual REENTRY review friction. CW removed broad time-accumulating erosion, but `REENTRY_INSUFFICIENT_EVIDENCE` and prior-context review still consume 1,341 rows.
4. Late-window cash deployment selectivity. October 2023 exposure drops to 52.0%; this is partly defensive but also reflects `NO_VALID_COMPETITOR`, `CONCENTRATION_BLOCK`, and lot residual evidence.
5. Starter turnover and limited campaign graduation. Many campaigns start, fewer graduate to multi-add/large allocations.

## Required Final Answers

- `TIME_ACCUMULATING_GROWTH_DECAY_REPRODUCED = NO`
- `POST_APRIL_GROWTH_PERSISTENCE = PRESENT_WITH_LATE_SEP_OCT_DEFENSIVE_SOFT_PATCH`
- `REENTRY_UNIVERSE_EROSION_REPRODUCED = NO`
- `CW_REENTRY_LONG_HORIZON_EFFECTIVE = YES_WITH_REMAINING_REVIEW_FRICTION`
- `WINNER_CAPITALIZATION_STATUS = MATERIAL_BOTTLENECK`
- `ADD_SUPPRESSION_ROOT_CAUSE_PROFILE = DOWNSTREAM_PC_ENTRY_BQ_AND_MARGINAL_CAPITAL_COMPETITION_DOMINANT; PM_SIGNAL_PRESENT; LOT_AND_CAP_SECONDARY`
- `CAPITAL_UTILIZATION_STATUS = GENERALLY_ACTIVE_WITH_LATE_WINDOW_DEFENSIVE_CASH_AND_OPPORTUNITY_ALLOCATION_FRICTION`
- `PORTFOLIO_FRAGMENTATION_STATUS = BROAD_STARTER_TURNOVER_WITH_LIMITED_WINNER_CONCENTRATION`
- `WINNER_RETENTION_STATUS = FUNCTIONAL_AND_IMPROVED; CAPITALIZATION_LAG_REMAINS`
- `DOWNSIDE_CONTROL_STATUS = EFFECTIVE_WITH_MODERATE_DRAWDOWNS`
- `OPPORTUNITY_FLOW_DECAY_OVER_TIME = NOT_BROADLY_REPRODUCED; BUY_NEW_SUPPLY_SOFTENS_LATE, REENTRY_SUPPLY_PERSISTS, ADD_FLOW_REMAINS_THIN`
- `TOP_REMAINING_STRUCTURAL_BOTTLENECKS = WINNER_CAPITALIZATION_AND_HIGH_RESOLUTION_MARGINAL_CAPITAL_ALLOCATION`
- `HISTORICAL_PNL_USED_FOR_PRODUCTION_TUNING = NO`
- `PHASE32_PERFORMANCE_CLOSURE_READINESS = READY_FOR_NEXT_PERFORMANCE_DESIGN_STEP_WITH_ADD_CAPITALIZATION_AS_PRIMARY_TOPIC`
- `PRODUCTION_CHANGE_EXECUTED = NO`
- `TARGET_RUN_MUTATED = NO`
- `NEXT_RECOMMENDED_STEP = Design the next READ-ONLY/SHADOW phase around winner ADD marginal capital value and campaign graduation, not REENTRY erosion or broad growth-decay repair.`

## Final Judgment

`PHASE32_DO_POST_CW_DG_ONE_YEAR_GROWTH_PERSISTENCE_CONFIRMED_PRIMARY_BOTTLENECK_WINNER_CAPITALIZATION`
