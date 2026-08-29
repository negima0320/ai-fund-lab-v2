# Phase32-CT Old vs Post-CS 5BD Capital Lifecycle Delta Audit

## Executive Summary

This was a READ-ONLY audit. No Production code, config, threshold, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

Post-CS repaired one-lot representability enough to increase 2022-10-03 BUY_NEW breadth versus Post-CJ: Day-0 now has 8 BUY fills, including CS-restored one-lot names `82540` and `96100`. The remaining five-day low-exposure problem is no longer primarily a Day-0 one-lot materialization failure. It is a capital lifecycle problem:

- OLD averaged about 77.4% exposure over 2022-10-03 through 2022-10-07.
- Post-CS averaged about 14.61% exposure.
- Post-CS deployed only 16.83% notional on Day-0 versus OLD's about 50.45% BUY notional / 51.1% exposure.
- Of the eight Post-CS Day-0 campaigns, seven were fully or effectively gone by 2022-10-06; only `94340` survived and grew.
- The first major lifecycle divergence is PM on 2022-10-04: `89180`, `67860`, `37820`, `96100`, and `76470` EXIT, while `33500`/`82540` enter REDUCE. That returned about 101,500 notional to cash immediately after a low initial deployment.
- By 2022-10-07, a valid BF NEW target for `76920` existed but did not fill because morning planning/submit feasibility marked the BUY `REVIEW_REQUIRED` with `corporate_action_event_not_resolved`.

Primary diagnosis: MIXED. Low exposure is caused by both smaller NEW deployment than OLD and early REDUCE/EXIT, with early capital exit the dominant lifecycle cause after CS. PM appears semantically misaligned with cautionary entry semantics for several Day-0 positions: the same `CONTINUATION_WITH_CAUTION` / reduced-quality entry class is accepted on Day-0, then multiple rows are sold T+1 as `trend_and_opportunity_broken`, `weak_hold_score`, or `hard_stop_current_return`. `94340` is the survivor control because it has rank 3, FULL allocation quality, PM HOLD on T+1, then repeated ADD intent on strong continuation evidence.

## Run Identity

| Role | Run | Coverage | Artifact status |
| --- | --- | --- | --- |
| OLD baseline | `runtime-test-historical-extended-smoke-20260828T000823285458Z` | 2022-10-03 to 2022-10-07 | Run directory absent locally; OLD daily facts are taken from `phase32_cg_pre_phase32_vs_current_final_investment_decision_semantic_delta_audit.md` |
| Post-CS | `runtime-test-historical-extended-smoke-20260829T060203037185Z` | 2022-10-03 to 2022-10-07 | Daily artifacts present and read directly |

Important limitation: OLD symbol-level campaign/PM artifacts are not present under `reports/runtime_tests/runs`. Therefore OLD symbol-level survival is inferential from CG daily snapshots, while Post-CS symbol-level findings are direct artifact observations.

## Daily Capital Flow

### OLD Baseline

OLD daily values are from CG. Sell notional is inferred from cash movement:

```text
sell_notional ~= cash_t - cash_t-1 + buy_notional
```

| Date | Opening security value | BUY notional | Implied sell/return-to-cash | Closing security value | Cash | Exposure | Positions | Price / residual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10-03 | 0 | 504,470 | 0 | ~517,824 | 495,530 | 51.1% | 7 | ~13,354 |
| 2022-10-04 | ~517,824 | 329,150 | ~130,320 | ~751,710 | 296,700 | 71.7% | 7 | ~35,056 |
| 2022-10-05 | ~751,710 | 163,880 | ~89,800 | ~847,668 | 222,620 | 79.2% | 7 | ~21,879 |
| 2022-10-06 | ~847,668 | 141,780 | ~0 | ~997,027 | 80,840 | 92.5% | 10 | ~7,578 |
| 2022-10-07 | ~997,027 | 35,100 | ~33,700 | ~979,760 | 79,440 | 92.5% | 10 | ~-18,667 |

OLD repeatedly redeployed capital and reached high exposure by 2022-10-06. Even with some early selling, BUY notional remained large enough to keep portfolio capital inside securities.

### Post-CS

Post-CS values are read directly from `current_valuation_refresh/valuation_projection.json` and `execution/fills.json`.

| Date | Opening security value | BUY_NEW notional | BUY_ADD notional | SELL notional | Closing security value | Cash | Exposure | Positions | Price movement / residual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10-03 | 0 | 168,320 | 0 | 0 | 169,540 | 831,680 | 16.93% | 8 | 1,220 |
| 2022-10-04 | 169,540 | 95,200 | 0 | 101,500 | 169,020 | 837,980 | 16.78% | 6 | 5,780 |
| 2022-10-05 | 169,020 | 35,380 | 0 | 59,100 | 139,880 | 861,700 | 13.97% | 6 | -5,420 |
| 2022-10-06 | 139,880 | 55,100 | 44,340 | 93,420 | 145,170 | 855,680 | 14.50% | 4 | -730 |
| 2022-10-07 | 145,170 | 0 | 0 | 33,700 | 108,470 | 889,380 | 10.87% | 3 | -3,000 |

Post-CS does put some capital in, but sells/reduces nearly as much as it buys from 2022-10-04 onward. Over the five days, Post-CS BUY notional is about 398,340, while sell notional is about 287,720. Because Day-0 starts much lower than OLD and subsequent BUY replenishment is modest, cash rises to about 89%.

## Exposure Change Decomposition

| Driver | OLD | Post-CS | Delta interpretation |
| --- | ---: | ---: | --- |
| Day-0 initial deployment | 504,470 BUY / 51.1% exposure | 168,320 BUY / 16.93% exposure | NEW deployment deficit remains material even after CS |
| 10/04 sell pressure | ~130,320 implied | 101,500 direct | Similar absolute scale, but much larger relative to Post-CS opening exposure |
| 10/04 BUY replenishment | 329,150 | 95,200 | OLD redeploys more aggressively |
| 10/05 BUY replenishment | 163,880 | 35,380 | Post-CS does not refill sold capital |
| 10/06 ADD / growth | included in 141,780 BUY | 44,340 ADD to `94340`; 55,100 NEW | Post-CS ADD exists but only one survivor absorbs capital |
| 10/07 BUY suppression | 35,100 BUY | 76920 BF target exists, but 0 fill | Post-CS blocked after BF by submit feasibility review |
| Price movement | supportive through 10/06 | small / mixed | Not primary |

The exposure delta is not explained by price movement. It is explained by initial NEW notional being far lower, followed by early PM exits/reduces and weaker redeployment.

## Post-CS Day-0 Campaign Survival

| Symbol | Entry qty / notional | T+1 qty | T+2 qty | T+3 qty | T+4 qty | First PM action | Exact PM reason | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| `33500` | 400 / 16,800 | 300 | 300 | 0 | 0 | REDUCE on 10/04 | `risk_increased_but_trend_not_broken` | REDUCE then full sell through sell-planning path |
| `37820` | 300 / 19,800 | 0 | 0 | 0 | 0 | EXIT on 10/04 | `trend_and_opportunity_broken` | T+1 EXIT |
| `67860` | 200 / 15,000 | 0 | 0 | 0 | 0 | EXIT on 10/04 | `trend_and_opportunity_broken` | T+1 EXIT |
| `76470` | 700 / 18,900 | 0 | 0 | 0 | 0 | EXIT on 10/04 | `weak_hold_score` | T+1 EXIT |
| `82540` | 100 / 29,900 | 100 | 0 | 0 | 0 | REDUCE on 10/04 | `risk_increased_but_trend_not_broken` | T+2 sell |
| `89180` | 2,100 / 21,000 | 0 | 0 | 0 | 0 | EXIT on 10/04 | `hard_stop_current_return` | T+1 hard stop |
| `94340` | 200 / 28,920 | 200 | 200 | 500 | 500 | HOLD on 10/04 | `positive_expected_edge|downside_risk_contained`; then ADD intent | Survivor / ADD control |
| `96100` | 100 / 18,000 | 0 | 0 | 0 | 0 | EXIT on 10/04 | `trend_and_opportunity_broken` | T+1 EXIT |

Day-0 capital that disappeared by 2022-10-07:

| Bucket | Symbols | Approx proceeds / capital returned |
| --- | --- | ---: |
| `trend_and_opportunity_broken` EXIT | `37820`, `67860`, `96100` | 56,700 |
| `weak_hold_score` EXIT | `76470` | 19,600 |
| `hard_stop_current_return` EXIT | `89180` | 21,000 |
| REDUCE / sell-planning liquidation | `33500`, `82540` | 47,040 |
| Survivor capital | `94340` | initial 28,920 remains and grows to 500 shares |

Thus approximately 145,340 of 168,320 Day-0 entry notional was sold by 2022-10-07, excluding the surviving `94340` exposure.

## Entry Evidence vs PM Evidence

Day-0 Post-CS entry evidence:

| Symbol | Rank | Opportunity score | Buy Quality action | Quality score | Entry state | Quality target | Fill qty | T+1/T+2 PM outcome |
| --- | ---: | ---: | --- | ---: | --- | ---: | ---: | --- |
| `94340` | 3 | 0.2403 | `FULL_ALLOCATION_ELIGIBLE` | 0.765860 | `CONTINUATION_WITH_CAUTION` | 3.3636% | 200 | HOLD then ADD |
| `37820` | 6 | n/a in extracted table | `REDUCED_ALLOCATION_ONLY` | 0.716582 | `CONTINUATION_WITH_CAUTION` | 2.4103% | 300 | EXIT T+1 |
| `89180` | 25 | -0.3390 | `REDUCED_ALLOCATION_ONLY` | 0.585257 | `CONTINUATION_WITH_CAUTION` | 1.9686% | 2,100 | hard-stop EXIT T+1 |
| `76470` | 26 | n/a in extracted table | `REDUCED_ALLOCATION_ONLY` | 0.576307 | `CONTINUATION_WITH_CAUTION` | 1.9385% | 700 | weak-hold EXIT T+1 |
| `33500` | 29 | n/a in extracted table | `REDUCED_ALLOCATION_ONLY` | 0.557743 | `CONTINUATION_WITH_CAUTION` | 1.8760% | 400 | REDUCE T+1 |
| `82540` | 35 | n/a in extracted table | `REDUCED_ALLOCATION_ONLY` | 0.513128 | `CONTINUATION_WITH_CAUTION` | 0% final PC, one-lot authority admitted | 100 | REDUCE T+1/T+2 |
| `67860` | 37 | n/a in extracted table | `REDUCED_ALLOCATION_ONLY` | 0.482751 | `CONTINUATION_WITH_CAUTION` | 1.6238% | 200 | EXIT T+1 |
| `96100` | 41 | n/a in extracted table | `REDUCED_ALLOCATION_ONLY` | 0.471220 | `CONTINUATION_WITH_CAUTION` | 0% final PC, one-lot authority admitted | 100 | EXIT T+1 |

The survivor control, `94340`, differs clearly:

- rank 3 versus rank 25/26/29/35/37/41 for most early exits,
- FULL allocation quality versus reduced allocation,
- PM says HOLD on T+1 with positive expected edge / contained downside,
- PM produces ADD intent on 10/05, 10/06, and 10/07 with `strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging`.

## OLD vs Post-CS PM Decision

OLD campaign-level PM artifacts are not available locally, so exact same-symbol PM reason comparison cannot be completed for OLD. The daily-level evidence still shows materially stronger OLD capital retention:

- OLD positions remain 7, 7, 7, 10, 10 from 10/03 to 10/07.
- Post-CS positions move 8, 6, 6, 4, 3.
- OLD exposure rises from 51.1% to 92.5%.
- Post-CS exposure falls from 16.93% to 10.87%.
- OLD has larger BUY replenishment on 10/04, 10/05, and 10/06; Post-CS lets sell proceeds accumulate as Cash.

Therefore OLD's stronger path was MIXED:

- higher initial deployment,
- stronger or more persistent redeployment,
- longer portfolio capital retention,
- and likely less immediate PM liquidation relative to invested capital.

Because OLD symbol PM artifacts are missing, it is not possible to assert whether OLD would have HOLD/ADD for the exact Post-CS early-exit symbols.

## 2022-10-07 BF Target With No Fill

Post-CS had one BF aggregated NEW target on 2022-10-07:

| Symbol | BF target | Semantic type | Planning status | Submit / fill result |
| --- | ---: | --- | --- | --- |
| `76920` | +200 | `NEW_FIRST_LOT` | Pending item generated | BUY not included; `source_submit_feasibility_status = REVIEW_REQUIRED`, reason `corporate_action_event_not_resolved` |

Execution filled only the `44220` SELL on 2022-10-07. This is not a Cash/common-frontier preference; it is a post-BF planning/submit feasibility review boundary.

## Answers To Most Important Questions

1. Post-CS low exposure is caused by both NEW deployment deficit and early REDUCE/EXIT. After CS, early REDUCE/EXIT plus weak redeployment is the dominant lifecycle cause; Day-0 is improved to 8 BUYs but starts from only 16.93% exposure.

2. OLD capital appears to remain in the portfolio longer at the daily aggregate level. OLD exposure climbs to 92.5% by 10/06, while Post-CS falls to 10.87% by 10/07.

3. PM only partially matches Post-CS entry semantics. It correctly distinguishes `94340` as HOLD/ADD, but many `CONTINUATION_WITH_CAUTION` reduced entries become T+1 EXIT/REDUCE. That looks like an entry/PM semantic scale mismatch, not merely a sizing issue.

4. Yes, there is evidence consistent with caution-at-entry becoming sell/exit evidence immediately after entry. Examples: `37820`, `67860`, `96100` enter as caution/reduced and exit T+1 for `trend_and_opportunity_broken`; `76470` exits for `weak_hold_score`; `33500`/`82540` reduce for increased risk.

5. OLD's rightward exposure path was MIXED: materially higher initial deployment, larger daily redeployment, and stronger aggregate retention. ADD cannot be isolated in OLD from available artifacts.

6. `94340` survives because it has strong relative rank, FULL allocation quality, PM positive expected edge / contained downside on T+1, then explicit ADD reasons. Early disappearing campaigns are mostly reduced-quality/caution entries with weaker rank/opportunity and immediate PM deterioration.

## Defect / Repair Judgment

CS itself is not the primary defect: it restored two one-lot Day-0 BUYs (`82540`, `96100`) and the authority/BF path is active.

The next production repair is justified, but should not be a threshold/PnL tuning change. The repair boundary should be semantic:

- align NEW/REENTRY entry admission with PM next-day management so cautionary entries are not immediately treated as broken unless fresh deterioration is explicit;
- separate expected-entry caution from post-entry deterioration;
- preserve PM hard stops and true breakdown exits;
- investigate submit-feasibility `corporate_action_event_not_resolved` for valid BF targets like 2022-10-07 `76920`.

## Final Judgments

PHASE32_CT_OLD_AVG_EXPOSURE = 77.40%

PHASE32_CT_POST_CS_AVG_EXPOSURE = 14.61%

PHASE32_CT_PRIMARY_LOW_EXPOSURE_CAUSE = MIXED: lower initial NEW deployment plus material early REDUCE/EXIT and weak redeployment; after CS, early capital exit / retention failure is dominant

PHASE32_CT_NEW_DEPLOYMENT_DEFICIT = YES

PHASE32_CT_EARLY_CAPITAL_EXIT_MATERIAL = YES

PHASE32_CT_ENTRY_PM_SEMANTIC_MISMATCH = PARTIAL

PHASE32_CT_OLD_CAPITAL_RETENTION_STRONGER = YES

PHASE32_CT_ADD_DIFFERENCE_MATERIAL = PARTIAL

PHASE32_CT_94340_SURVIVOR_DIFFERENCE = rank 3, FULL allocation quality, PM HOLD with positive expected edge/downside contained, then ADD intent from strong trend continuation and opportunity rank still high; most exited peers were reduced-quality CONTINUATION_WITH_CAUTION rows with weaker rank/opportunity and T+1 deterioration reasons

PHASE32_CT_PRIMARY_DIVERGENCE_BOUNDARY = PM post-entry management on 2022-10-04, after a secondary Day-0 NEW deployment deficit; 2022-10-07 also has a post-BF submit-feasibility REVIEW_REQUIRED blocker for 76920

PHASE32_CT_PRODUCTION_REPAIR_JUSTIFIED = PARTIAL

PHASE32_CT_NEXT_STEP = Design a narrow Entry-to-PM semantic consistency repair/audit: distinguish expected caution at entry from fresh post-entry deterioration, preserve true hard-stop/trend-break exits, and separately audit the 2022-10-07 corporate-action submit-feasibility review boundary for valid BF BUY targets.
