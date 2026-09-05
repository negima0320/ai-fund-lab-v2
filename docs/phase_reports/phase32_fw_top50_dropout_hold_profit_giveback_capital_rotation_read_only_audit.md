# Phase32-FW — Top50 Dropout HOLD / Profit Giveback / Capital Rotation READ-ONLY Audit

## Scope

- Primary long run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Evidence window: completed business days only, `2022-10-03` through `2023-08-04`
- Completed business days: `208`
- Period split follows Phase32-FU:
  - EARLY: `2022-10-03` through `2023-02-28`
  - MIDDLE: `2023-03-01` through `2023-05-31`
  - LATE: `2023-06-01` through `2023-08-04`

READ-ONLY confirmation:

- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Runtime/Pending/Ledger state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- Historical outcome used only for actual economics characterization: YES
- Historical outcome used for SELL threshold/Top-N/parameter selection: NO

## Top50 Membership Authority

`TOP50_MEMBERSHIP_AUTHORITY_CONFIRMED = YES`

Canonical rank authority:

- Producer: Runtime BUY AI Opportunity Ranking Producer.
- Canonical field: `opportunity_buy_rank`.
- Source semantic field: `buy_rank` in `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json`.
- Portfolio Construction materialization: `input_opportunity_rank`.
- Runtime lineage: `opportunity_buy_rank -> Portfolio Construction input_opportunity_rank -> Position Sizing opportunity_buy_rank -> Runtime Planning opportunity_buy_rank`.

The primary run does not retain a separate raw `opportunity_rankings.json` under the run evidence tree. Therefore this audit uses same-day `strategy/portfolio_construction.json` as the canonical consumer-materialized authority for Top50 membership.

Classification:

- `IN_TOP50`: held current position has `input_opportunity_rank <= 50`.
- `OUTSIDE_TOP50`: same-day PC artifact is present, held current position is represented, but no valid Top50 rank is materialized.
- `NO_VALID_CANDIDATE_EVIDENCE`: PC/candidate authority unavailable for that held row.

Observed PC evidence had no full-day artifact outage:

- Held position daily rows: `2,656`
- `IN_TOP50`: `2,025`
- `OUTSIDE_TOP50`: `631`
- `NO_VALID_CANDIDATE_EVIDENCE`: `0`

## Dropout Definition

`TOP50_DROPOUT` is defined campaign-locally as:

```text
previous held row = IN_TOP50
current held row = OUTSIDE_TOP50
same symbol/campaign_id
```

The audit does not count repeated daily outside rows as new dropout events, and it does not treat Top50 dropout as a Production sell rule.

## Headline Counts

- `TOTAL_HELD_CAMPAIGNS = 379`
- `TOP50_DROPOUT_EPISODE_COUNT = 52`
- `UNIQUE_DROPOUT_CAMPAIGN_COUNT = 49`
- `DROPOUT_REENTRY_RATE = 5 / 52 = 9.6%`
- `MEDIAN_DROPOUT_DURATION_BD = 2.5`
- `PERSISTENT_DROPOUT_EPISODE_COUNT = 29` using duration `> 1BD`

Duration distribution:

| Duration bucket | Episodes |
|---|---:|
| 1BD | 23 |
| 2BD | 3 |
| 3-5BD | 9 |
| 6-10BD | 9 |
| 11+BD | 8 |

Episode end reason:

| End reason | Episodes |
|---|---:|
| SELL / EXIT | 45 |
| Top50 re-entry | 5 |
| Run end / still held | 2 |

SELL timing from dropout to episode end:

- Median: `2.5BD`
- p75: `7.25BD`
- p90: `14BD`
- Max: `68BD`

## PM Action After Dropout

Action-days inside dropout episodes:

| PM action | Days |
|---|---:|
| HOLD | 252 |
| REDUCE | 26 |
| EXIT / SELL_EXIT | 45 |

- `DROPOUT_HOLD_COUNT = 252 action-days`
- `DROPOUT_REDUCE_COUNT = 26 action-days`
- `DROPOUT_EXIT_COUNT = 45 action-days`
- `DROPOUT_HOLD_SHARE = 78.0%`

Top50 dropout episodes are therefore mostly held while outside Top50. The current PM path eventually exits most episodes, but often after several HOLD days.

## Dropout Economics

Metric is actual mark/proceeds delta from first dropout value to episode end value, campaign-deduped. This is diagnostic economics only, not parameter-selection evidence.

| Metric | Value |
|---|---:|
| `POST_DROPOUT_GROSS_PROFIT` | `55,710` |
| `POST_DROPOUT_GROSS_LOSS` | `-97,190` |
| `POST_DROPOUT_NET_PNL` | `-41,480` |
| Mean episode PnL | `-797.69` |
| Median episode PnL | `0` |
| `POST_DROPOUT_NEGATIVE_EPISODE_SHARE` | `50.0%` |

Loss/giveback cohort split:

| Cohort | Episodes |
|---|---:|
| A. Already loss at dropout, then worsened | 2 |
| B. Profit at dropout, giveback and post-dropout loss | 15 |
| C. Post-dropout PnL positive | 21 |
| D. Top50 re-entry | 5 |

Interpretation:

- Dropout HOLD is not uniformly harmful.
- There are material giveback cases, but also many cases where post-dropout HOLD was economically positive or the symbol recovered into Top50.
- A hard `Top50 dropout -> immediate EXIT` rule is not justified from this evidence.

## Profit Giveback

- Episodes with profit at dropout: `43`
- Episodes with positive giveback: `25`
- `TOP50_DROPOUT_PROFIT_GIVEBACK_TOTAL = 139,750`
- `TOP50_DROPOUT_PROFIT_GIVEBACK_SHARE = 32.46% of the post-dropout peak profit pool`

Largest giveback cases:

| Dropout date | Symbol | Duration | End | PnL | Giveback | Notional-days | PM actions |
|---|---:|---:|---|---:|---:|---:|---|
| 2023-05-08 | 66560 | 20 | SELL/EXIT | 7,600 | 23,600 | 3,923,500 | HOLD 17 / REDUCE 2 / EXIT 1 |
| 2023-07-05 | 40520 | 8 | SELL/EXIT | -300 | 18,800 | 1,116,300 | HOLD 5 / REDUCE 2 / EXIT 1 |
| 2022-12-01 | 78860 | 5 | SELL/EXIT | -4,000 | 16,600 | 687,900 | HOLD 3 / REDUCE 1 / EXIT 1 |
| 2023-06-06 | 88900 | 14 | SELL/EXIT | -1,000 | 15,000 | 4,240,800 | HOLD 13 / EXIT 1 |
| 2023-01-20 | 70680 | 22 | SELL/EXIT | 9,400 | 11,300 | 1,210,600 | HOLD 18 / REDUCE 3 / EXIT 1 |

## Profit Retention / Deterioration Interaction

- `OUTSIDE_TOP50_PLUS_PROFIT_RETENTION_BREAK_HOLD_COUNT = 0 action-days observed by explicit reason-code search`
- `OUTSIDE_TOP50_PLUS_DETERIORATION_HOLD_COUNT = 252 action-days by canonical sell/deterioration text evidence`

The explicit `profit_retention_break` token was not observed in dropout HOLD action-days. However, the PM evidence often contained deterioration dimensions such as weakening, elevated risk, deceleration, or deterioration state while preserving HOLD due to recovery/continuation evidence.

This points to a SELL design interaction rather than a correctness defect:

- Top50 dropout and deterioration evidence can coexist with HOLD.
- The system can still exit later.
- The gap is whether outside-Top50 status should become soft sell/rotation evidence in combination with PM deterioration and capital opportunity context.

## Capital Lock

- `OUTSIDE_TOP50_NOTIONAL_DAYS = 30,540,790`
- Average daily outside-Top50 exposure share versus equity: `21.24%`
- Average daily outside-Top50 share of invested held notional: `26.36%`

Period average outside-Top50 equity share:

| Period | Days | Episodes started | Outside/equity share | Outside/invested share | Median duration | Net post-dropout PnL | Giveback | Re-entry rate | HOLD share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 100 | 29 | 26.24% | 33.31% | 3BD | -21,650 | 52,040 | 10.3% | 78.8% |
| MIDDLE | 62 | 10 | 13.73% | 17.07% | 1BD | -22,840 | 36,140 | 10.0% | 65.6% |
| LATE | 46 | 13 | 20.48% | 23.79% | 3BD | 3,010 | 51,570 | 7.7% | 81.2% |

`EARLY_OUTSIDE_TOP50_EXPOSURE_SHARE = 26.24%`

`MIDDLE_OUTSIDE_TOP50_EXPOSURE_SHARE = 13.73%`

`LATE_OUTSIDE_TOP50_EXPOSURE_SHARE = 20.48%`

`EARLY_POST_DROPOUT_NET_PNL = -21,650`

`MIDDLE_POST_DROPOUT_NET_PNL = -22,840`

`LATE_POST_DROPOUT_NET_PNL = 3,010`

## June Long-Run Snapshot

From `2023-06-01` onward, outside-Top50 holdings become more visible again. The last 10 completed days averaged `33.63%` outside-Top50 equity share.

| Date | Positions | Top50 | Outside | Outside notional | Outside/equity | HOLD | REDUCE | EXIT | Eligible strong candidates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023-06-01 | 9 | 8 | 1 | 207,100 | 15.33% | 1 | 0 | 0 | 0 |
| 2023-06-02 | 9 | 8 | 1 | 196,300 | 14.92% | 0 | 0 | 1 | 1 |
| 2023-06-05 | 9 | 9 | 0 | 0 | 0.00% | 0 | 0 | 0 | 1 |
| 2023-06-06 | 14 | 13 | 1 | 306,500 | 21.75% | 1 | 0 | 0 | 0 |
| 2023-06-07 | 15 | 14 | 1 | 308,000 | 20.77% | 1 | 0 | 0 | 0 |
| 2023-06-08 | 13 | 12 | 1 | 303,500 | 22.12% | 1 | 0 | 0 | 2 |
| 2023-06-09 | 13 | 11 | 2 | 356,410 | 25.35% | 2 | 0 | 0 | 0 |
| 2023-06-12 | 11 | 9 | 2 | 355,600 | 31.63% | 2 | 0 | 0 | 0 |
| 2023-06-13 | 16 | 15 | 1 | 298,300 | 20.70% | 1 | 0 | 0 | 1 |
| 2023-06-14 | 18 | 16 | 2 | 438,000 | 28.71% | 2 | 0 | 0 | 0 |
| 2023-06-15 | 18 | 16 | 2 | 434,900 | 28.49% | 1 | 0 | 1 | 0 |
| 2023-06-19 | 18 | 15 | 3 | 394,000 | 26.12% | 2 | 0 | 1 | 0 |
| 2023-07-10 | 14 | 9 | 5 | 406,600 | 29.59% | 4 | 1 | 0 | 3 |
| 2023-07-11 | 18 | 11 | 7 | 503,300 | 32.20% | 3 | 3 | 1 | 4 |
| 2023-07-12 | 17 | 9 | 8 | 568,710 | 37.67% | 2 | 1 | 5 | 5 |
| 2023-07-14 | 14 | 8 | 6 | 550,300 | 37.26% | 3 | 1 | 2 | 3 |
| 2023-07-26 | 18 | 10 | 8 | 661,840 | 40.70% | 5 | 3 | 0 | 0 |
| 2023-08-02 | 14 | 6 | 8 | 562,740 | 41.26% | 6 | 1 | 1 | 0 |
| 2023-08-04 | 12 | 6 | 6 | 481,380 | 38.17% | 4 | 1 | 1 | 0 |

`JUNE_LONG_RUN_OUTSIDE_TOP50_LEGACY_HOLD_MATERIAL = YES`

## Opportunity Recovery

Top50 re-entry occurred in `5 / 52` episodes.

This is small but non-zero. It matters because it disproves the simplistic interpretation that Top50 dropout always means permanent deterioration. A hard immediate exit rule would have closed some episodes that recovered into Top50 under current PIT evidence.

## Fresh June Comparison Metric Contract

Fresh June comparison run `runtime-test-historical-extended-smoke-20260904T112908488385Z` was not required for this primary audit. For future same-day comparison, use this metric contract:

For each overlapping completed date:

- `long_run_outside_top50_legacy_symbols`
- `fresh_run_held_symbols`
- `long_only_outside_top50_legacy_symbols`
- `long_only_outside_top50_notional`
- `long_only_outside_top50_equity_share`
- `long_only_pm_action_distribution`
- `same_day_eligible_strong_candidate_count`

This distinguishes run-age legacy capital lock from same-calendar opportunity scarcity without mutating either run.

## Does It Accumulate With Run Age?

`OUTSIDE_TOP50_HOLD_ACCUMULATES_WITH_RUN_AGE = PARTIAL`

Reason:

- EARLY has the highest average outside-Top50 equity share, so accumulation is not monotonic from run start.
- MIDDLE improves materially.
- LATE rises again to `20.48%` average and over `33%` in the final 10 completed days.
- LATE has fewer episodes than EARLY but higher HOLD share and visible concentration in several long-held outside-Top50 positions.

The phenomenon is material in LATE, but the evidence does not support a simple monotonic run-age accumulation law over the 208BD completed window.

## Correctness vs Design

`CORRECTNESS_DEFECT_FOUND = NO`

No Architecture/SoT/PIT contract violation was found:

- Top50 rank lineage is materialized through PC.
- Held rows can be classified from same-day evidence.
- PM eventually REDUCE/EXITs most dropout episodes.
- Outcome was used only to characterize actual economics, not to tune a sell rule.

`DESIGN_REFINEMENT_JUSTIFIED = YES`

The material issue is design-level:

- Top50 dropout often coexists with HOLD.
- Some episodes lock capital for many business days.
- Profit giveback is material.
- Current PM/SELL does not appear to use outside-Top50 status as explicit soft evidence for capital rotation or profit-protection review.

## SELL Design Gap Classification

`SELL_DESIGN_GAP_CLASSIFICATION = MIXED`

More specific components:

- `PERSISTENT_OUTSIDE_TOP50_HOLD_MATERIAL = YES`
- `OUTSIDE_TOP50_PLUS_DETERIORATION_HOLD_MATERIAL = YES`
- `PROFIT_RETENTION_INTERACTION_MATERIAL = YES`
- `CAPITAL_ROTATION_GAP_MATERIAL = YES`
- `TEMPORARY_DROPOUT_RECOVERY_DOMINATES = NO`
- `NO_MATERIAL_DROPOUT_HOLD_PROBLEM = NO`

`CAPITAL_ROTATION_GAP_FOUND = YES`

`PROFIT_RETENTION_INTERACTION_FOUND = YES`

## Recommendations

`TOP50_HARD_EXIT_JUSTIFIED = NO`

Top50 dropout alone is too noisy and some episodes recover. It should not be promoted directly into a hard EXIT rule from this audit.

`TOP50_SOFT_SELL_EVIDENCE_REVIEW_JUSTIFIED = YES`

Top50 dropout is useful as current opportunity deterioration evidence, especially when persistent or paired with PM deterioration / giveback.

`CURRENT_OPPORTUNITY_REEVALUATION_REVIEW_JUSTIFIED = YES`

The next design should evaluate existing holdings against current opportunity strength and capital rotation context, not merely against their own trailing campaign state.

Suggested next design direction:

`NEXT_DESIGN_DIRECTION = MULTI_FACTOR`

Candidate components:

- `TOP50_MEMBERSHIP_AS_SOFT_SELL_EVIDENCE`
- `CURRENT_OPPORTUNITY_REEVALUATION_FOR_HOLDINGS`
- `PROFIT_RETENTION_PLUS_OPPORTUNITY_DROPOUT_REVIEW`
- `CAPITAL_ROTATION_REVIEW`

Do not implement fixed immediate Top50 exit.

## Required Final Answers

- `TOP50_MEMBERSHIP_AUTHORITY_CONFIRMED = YES`
- `TOTAL_HELD_CAMPAIGNS = 379`
- `TOP50_DROPOUT_EPISODE_COUNT = 52`
- `UNIQUE_DROPOUT_CAMPAIGN_COUNT = 49`
- `DROPOUT_REENTRY_RATE = 9.6%`
- `MEDIAN_DROPOUT_DURATION_BD = 2.5`
- `PERSISTENT_DROPOUT_EPISODE_COUNT = 29`
- `DROPOUT_HOLD_COUNT = 252 action-days`
- `DROPOUT_REDUCE_COUNT = 26 action-days`
- `DROPOUT_EXIT_COUNT = 45 action-days`
- `DROPOUT_HOLD_SHARE = 78.0%`
- `POST_DROPOUT_GROSS_PROFIT = 55,710`
- `POST_DROPOUT_GROSS_LOSS = -97,190`
- `POST_DROPOUT_NET_PNL = -41,480`
- `POST_DROPOUT_NEGATIVE_EPISODE_SHARE = 50.0%`
- `TOP50_DROPOUT_PROFIT_GIVEBACK_TOTAL = 139,750`
- `TOP50_DROPOUT_PROFIT_GIVEBACK_SHARE = 32.46%`
- `OUTSIDE_TOP50_PLUS_PROFIT_RETENTION_BREAK_HOLD_COUNT = 0 explicit reason-code action-days`
- `OUTSIDE_TOP50_PLUS_DETERIORATION_HOLD_COUNT = 252 action-days`
- `OUTSIDE_TOP50_NOTIONAL_DAYS = 30,540,790`
- `AVG_DAILY_OUTSIDE_TOP50_EXPOSURE_SHARE = 21.24%`
- `EARLY_OUTSIDE_TOP50_EXPOSURE_SHARE = 26.24%`
- `MIDDLE_OUTSIDE_TOP50_EXPOSURE_SHARE = 13.73%`
- `LATE_OUTSIDE_TOP50_EXPOSURE_SHARE = 20.48%`
- `EARLY_POST_DROPOUT_NET_PNL = -21,650`
- `MIDDLE_POST_DROPOUT_NET_PNL = -22,840`
- `LATE_POST_DROPOUT_NET_PNL = 3,010`
- `OUTSIDE_TOP50_HOLD_ACCUMULATES_WITH_RUN_AGE = PARTIAL`
- `JUNE_LONG_RUN_OUTSIDE_TOP50_LEGACY_HOLD_MATERIAL = YES`
- `SELL_DESIGN_GAP_CLASSIFICATION = MIXED`
- `CAPITAL_ROTATION_GAP_FOUND = YES`
- `PROFIT_RETENTION_INTERACTION_FOUND = YES`
- `TOP50_HARD_EXIT_JUSTIFIED = NO`
- `TOP50_SOFT_SELL_EVIDENCE_REVIEW_JUSTIFIED = YES`
- `CURRENT_OPPORTUNITY_REEVALUATION_REVIEW_JUSTIFIED = YES`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `NEXT_DESIGN_DIRECTION = MULTI_FACTOR`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

Final Judgment: `PHASE32_FW_TOP50_DROPOUT_HOLD_CAPITAL_ROTATION_GAP_MATERIAL_DESIGN_REFINEMENT_JUSTIFIED_NO_CORRECTNESS_DEFECT`
