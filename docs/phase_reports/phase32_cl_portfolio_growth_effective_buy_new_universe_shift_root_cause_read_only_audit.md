# Phase32-CL — Portfolio Growth / Effective BUY_NEW Universe Shift Root-Cause READ-ONLY Audit

Target run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

This is a READ-ONLY characterization. No Production code, config, Strategy parameter, threshold, model, feature, runtime state, Pending, Ledger, resume, recover, replay, fresh-run, or long Historical was changed or executed. The Phase32-CK report is treated as repaired-source context only; the old target run remains annotated defect evidence, and CK/CJ REENTRY->BUY_NEW bypass fills are excluded from genuine BUY_NEW characterization.

## Preserved Prior Conclusions

This audit preserves CG/CH/CI/CF/CK:

- post-April BUY_NEW follow-through declined;
- post-April capital increasingly recycled through NEW starter churn;
- effective action ordering was emergent `NEW > ADD > REENTRY`;
- high-notional binary starters are a real separate population;
- REENTRY->BUY_NEW bypass has now been repaired in CK;
- CL does not use the CK correctness defect as the explanation for overall BUY_NEW quality decline.

## Evidence Coverage

Run state completed evidence covers `231` business days from `2022-10-03` through `2023-09-07`.

Primary windows:

| Window | Dates | Completed BD |
|---|---:|---:|
| Growth | `2023-01-18` -> `2023-04-10` | 57 |
| Post-April | `2023-04-11` -> `2023-09-07` | 103 |
| Plateau | `2023-06-19` -> `2023-08-08` | 36 |
| Recovery Control | `2023-08-23` -> `2023-09-07` | 12 |

The recovery control window was derived from completed evidence after the late-August equity recovery had begun: equity rose from about `1.78M` on `2023-08-23` to `1.86M` on `2023-09-07`. It is short, so it is a control, not a final performance regime.

## Method

BUY_NEW fills were read from daily `execution/fills.json`. PC, PS, BQ, technical features, market regime, equity, and cash were read from:

- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/buy_quality_decisions.json`
- `strategy/technical_features.json`
- `strategy/market_context.json`
- `current_valuation_refresh/valuation_projection.json`

For each BUY_NEW fill, the audit captured fill notional, one-lot notional, pre-entry equity, pre-entry cash proxy, one-lot/equity, initial weight, rank, BQ state, runtime opportunity score, momentum/trend evidence, regime, PC accepted/requested weights, and PS lot authority.

Counterfactual 1M executability was classified using the existing 100-share lot and cap landmarks:

- `EXECUTABLE_AT_1M`: one-lot notional <= `180,000`
- `NOT_EXECUTABLE_AT_1M_SOFT_CAP_OR_LOT`: one-lot notional > `180,000` and <= `250,000`
- `NOT_EXECUTABLE_AT_1M_HARD_CAP`: one-lot notional > `250,000`
- `NOT_EXECUTABLE_AT_1M_CASH`: no case where one lot exceeded 1M all-cash capacity

Important nuance: the `SOFT_CAP_OR_LOT` class is a Strategy soft-cap / one-lot pressure class, not proof that the current contract could never admit the trade. CF established that one-lot soft-cap overshoot can be admitted when explicit PC/PS authority proves Safety hard-cap preservation. The strict non-executable-at-1M subset is therefore the hard-cap class.

## BUY_NEW Population

Observed BUY_NEW fills: `361`.

Excluded CK/CJ REENTRY bypass filled cases: `5`.

Genuine BUY_NEW fills used: `356`.

| Window | Genuine BUY_NEW fills | BUY_NEW notional | Median price | Median one-lot notional | Median initial weight | P90 one-lot notional | P90 initial weight |
|---|---:|---:|---:|---:|---:|---:|---:|
| Growth | 78 | 6,205,660 | 518.15 | 52,200 | 4.18% | 180,319 | 14.73% |
| Post-April | 163 | 16,403,440 | 656.00 | 68,600 | 4.18% | 210,490 | 12.08% |
| Plateau | 68 | 7,338,070 | 765.00 | 77,450 | 4.65% | 209,855 | 12.06% |
| Recovery Control | 10 | 745,650 | 416.50 | 41,600 | 2.73% | 145,130 | 8.18% |

Post-April funded BUY_NEW shifted toward higher median one-lot notional than Growth. Initial weight median did not materially increase because portfolio equity was larger.

## 1M Executability

Post-April genuine BUY_NEW:

| 1M classification | Count | Fill notional |
|---|---:|---:|
| `EXECUTABLE_AT_1M` | 135 | 9,757,890 |
| `NOT_EXECUTABLE_AT_1M_SOFT_CAP_OR_LOT` | 19 | 3,879,150 |
| `NOT_EXECUTABLE_AT_1M_HARD_CAP` | 9 | 2,766,400 |

Combined soft/lot + hard-cap pressure population: `28` fills, `6,645,550` notional.

Strict Safety hard-cap newly executable subset: `9` fills, `2,766,400` notional.

At Growth median equity (`1,242,220`), the post-April hard-cap-failing subset falls to `3` fills, with `10` additional soft/lot-pressure fills. This supports a real equity-scale effect, but not a wholesale universe transformation.

## Effective Universe Expansion

Funded BUY_NEW shifted more than the candidate universe:

| Metric | Growth | Post-April | Plateau | Recovery |
|---|---:|---:|---:|---:|
| Candidate rows | 2,850 | 5,150 | 1,800 | 600 |
| Candidate median one-lot notional | 71,900 | 67,050 | 72,950 | 78,050 |
| Candidate P90 one-lot notional | 282,810 | 275,505 | 248,010 | 277,210 |
| Candidate hard-cap-at-1M rows / BD | 6.11 | 5.78 | 4.89 | 6.17 |
| Funded soft/hard pressure fills / BD | 0.14 | 0.27 | 0.36 | 0.08 |

The candidate system was already proposing high-notional names during Growth. Post-April did not show a clear candidate-population high-notional shift. The stronger evidence is that the funded/executable BUY_NEW mix shifted.

`EFFECTIVE_BUY_UNIVERSE_EXPANDED_WITH_EQUITY = YES_MODERATE_FOR_FUNDED_BUY_NEW; NOT_CONFIRMED_FOR_CANDIDATE_SET`

## Price / Lot Structure

`POST_APRIL_NEW_HIGHER_NOTIONAL_SHIFT_SUPPORTED = YES_FOR_FUNDED_BUY_NEW`

Evidence:

- median funded one-lot notional rose from `52,200` to `68,600`;
- P90 funded one-lot notional rose from `180,319` to `210,490`;
- Plateau median funded one-lot notional rose further to `77,450`;
- candidate median one-lot notional did not rise, so this is not primarily a raw candidate proposal shift.

## Newly Executable PIT Quality

Post-April always-executable-at-1M vs newly executable/pressure population:

| Metric | Always executable | Soft/Hard pressure |
|---|---:|---:|
| Count | 135 | 28 |
| Notional | 9,757,890 | 6,645,550 |
| Median one-lot notional | 52,300 | 215,350 |
| Median initial weight | 3.73% | 12.76% |
| Median rank | 33 | 33.5 |
| Median runtime opportunity score | -0.475993 | -0.458848 |
| BQ state | 135 REDUCED | 28 REDUCED |

PIT quality judgment:

`NEWLY_EXECUTABLE_PIT_QUALITY_VS_ALWAYS_EXECUTABLE = MIXED`

The newly executable/pressure population was much larger per lot and not clearly higher quality. But it was not plainly weaker on rank or raw runtime score. All post-April BUY_NEW fills were `REDUCED_ALLOCATION_ONLY`, so BQ does not differentiate the two groups.

## Follow-Through After Population Freeze

Post-April follow-through:

| Group | +1BD pos rate / mean | +3BD pos rate / mean | +5BD pos rate / mean | +10BD pos rate / mean |
|---|---:|---:|---:|---:|
| Always executable | 62.2% / +1,941 | 52.8% / +2,309 | 48.2% / +1,267 | 57.6% / +4,029 |
| Soft pressure | 52.6% / +3,208 | 52.9% / +2,509 | 69.2% / +8,196 | 66.7% / +3,722 |
| Hard-cap-at-1M pressure | 66.7% / +6,867 | 55.6% / -2,400 | 57.1% / +1,014 | 60.0% / -17,610 |
| Combined pressure | 57.1% / +4,384 | 53.8% / +810 | 65.0% / +5,683 | 64.3% / -3,896 |

`NEWLY_EXECUTABLE_FOLLOW_THROUGH = MIXED`

The hard-cap-at-1M subset has material +10BD downside, driven by large-notional names such as `51890` and `65260`. But the soft/lot-pressure subset is not consistently worse than always-executable. This weakens a simple "newly executable equals bad" explanation.

## High-Notional Starter Intersection

Using CF's high-notional starter definition:

- Post-April soft/hard pressure population: `28` fills / `6,645,550` notional.
- High-notional intersection: `5` fills / `1,708,600` notional.
- Therefore high-notional starters explain part of the universe shift, not all of it.

`UNIVERSE_SHIFT_DRIVEN_BY_HIGH_NOTIONAL_STARTERS = PARTIAL`

## Cash vs Equity Expansion

The primary 1M counterfactual blocker is equity/cap/lot scale:

- `9` cases exceed 25% Safety hard cap at 1M;
- `19` cases exceed 18% Strategy soft-cap / one-lot pressure at 1M;
- no case requires >1M all-cash capacity;
- actual pre-entry cash was sufficient for the observed fills, but post-April cash recycling enabled repeated NEW funding.

`PRIMARY_EXECUTABILITY_EXPANSION_DRIVER = EQUITY_WEIGHT_CAP_PRIMARY; CASH_RECYCLING_SECONDARY`

## Candidate Population vs Executability Filter

Candidate population:

- candidate median one-lot notional did not increase from Growth to Post-April;
- candidate P90 one-lot notional was similar/slightly lower;
- candidate hard-cap-at-1M row rate per BD was similar.

Funded/selected population:

- selected rank median moved from `26` in Growth to `33` Post-April and `35` Plateau;
- selected rank >=30 rose from `28 / 78` Growth to `101 / 163` Post-April and `48 / 68` Plateau;
- selected soft/hard pressure fills per BD roughly doubled from Growth to Post-April and rose further in Plateau.

Judgment:

- `CANDIDATE_POPULATION_SHIFT_SUPPORTED = NO_WEAK`
- `EXECUTABILITY_FILTER_SHIFT_SUPPORTED = YES_MODERATE`
- `LOWER_RANK_CANDIDATES_BECAME_EXECUTABLE_WITH_GROWTH = YES`

## Capital Amount Per NEW

Per 10BD:

| Window | BUY_NEW fills / 10BD | BUY_NEW notional / 10BD |
|---|---:|---:|
| Growth | 13.68 | 1,088,712 |
| Post-April | 15.83 | 1,592,567 |
| Plateau | 18.89 | 2,038,353 |
| Recovery Control | 8.33 | 621,375 |

`PORTFOLIO_GROWTH_EFFECT_ON_NEW_CAPITAL = BOTH`

Post-April and Plateau had both more NEW names per 10BD and more NEW capital per 10BD than Growth. Recovery control did not continue that pace despite high equity, which is important evidence against pure equity-size determinism.

## Starter Churn Intersection

Using early same-symbol SELL within 10BD as the starter-churn proxy:

| Class | Churn count | Churn notional |
|---|---:|---:|
| Always executable | 110 | 7,718,140 |
| Soft pressure | 15 | 3,127,650 |
| Hard pressure | 7 | 2,233,700 |

Total post-April churn notional: `13,079,490`.

Soft/hard pressure share of churn capital: `5,361,350 / 13,079,490 = 41.0%`.

`NEWLY_EXECUTABLE_SHARE_OF_STARTER_CHURN_CAPITAL = 41.0%_OF_POST_APRIL_EARLY_SELL_CHURN_NOTIONAL`

This is material, but most churn capital still came from names executable even at 1M.

## Plateau vs Recovery Control

Recovery control has a similar candidate high-notional universe, but funded BUY_NEW was smaller and follow-through improved:

- Recovery candidate hard-cap-at-1M rows / BD: `6.17`, similar to Growth/Post-April.
- Recovery funded pressure fills: `1 / 10` genuine BUY_NEW; no hard-cap-at-1M funded fills.
- Recovery +5BD positive rate was `66.7%`, with no >=10k loss in available evidence.
- Recovery +10BD evidence is only `3` rows, all positive, so it is suggestive but thin.

`RECOVERY_CONTROL_WEAKENS_UNIVERSE_SHIFT_HYPOTHESIS = YES_PARTIAL`

The expanded candidate universe remained visible, but the system did not fund the same high-notional/churn pattern at the same rate, and short follow-through improved. That points toward market follow-through and deployment mix as dominant over static universe expansion.

Within notional buckets:

- Plateau `<=100k` +5BD mean: `+890`, positive rate `61%`.
- Plateau `100-180k` +5BD mean: `-5,242`, positive rate `18%`.
- Plateau `180-250k` +5BD mean: `-430`, positive rate `60%`.
- Recovery evidence is short but better in `<=100k` and one `180-250k` case.

`MARKET_CONDITION_DOMINATES_WITHIN_SAME_NOTIONAL_BUCKET = PARTIAL_YES_SHORT_RECOVERY_SAMPLE`

## Root Cause Decomposition

| Component | Judgment | Evidence |
|---|---|---|
| market follow-through decline | PRIMARY | CG/CH and CL show +3/+5/+10BD follow-through and material-winner rate weakened post-April/Plateau, while recovery control improves despite similar candidate universe |
| action-type bias | SECONDARY | CI showed NEW repeatedly reaches PC/PS/fill while ADD/REENTRY do not; CL sees selected rank moving lower and capital continuing into NEW |
| starter churn | SECONDARY | post-April early-sell churn captures `13.08M` notional; pressure names are `41%`, always-executable names still majority |
| effective-universe expansion | SECONDARY/MINOR_AMPLIFIER | funded soft/hard pressure share grows; not enough to explain always-executable weak follow-through or recovery control |
| high-notional starter admission | MINOR_TO_SECONDARY | 5 high-notional pressure fills contribute material tail, but the 28-name pressure group is broader |
| lower-rank executability | SECONDARY | selected median rank worsens from 26 to 33/35; rank>=30 selected share rises |
| candidate population shift | NOT_SUPPORTED_AS_PRIMARY | candidate median/P90 lot notional did not rise |

`POST_APRIL_BUY_NEW_QUALITY_DECLINE_PRIMARY_CAUSE = MIXED_WITH_PRIMARY_WEAKER_MARKET_FOLLOW_THROUGH`

Secondary causes:

`ACTION_TYPE_BIAS; STARTER_CHURN; LOWER_RANK_EXECUTABILITY; EFFECTIVE_UNIVERSE_EXPANSION_AS_AMPLIFIER; HIGH_NOTIONAL_STARTER_EXPANSION_AS_TAIL_RISK_SUBSET`

## Repairability

No Production change is justified by CL alone. The repairable mechanism should stay inside existing architecture and be evaluated as SHADOW first:

- Candidate/BQ: characterize whether BQ can distinguish one-lot pressure names with weak continuation without adding a hindsight threshold.
- PC/marginal capital: make capital competition compare NEW, ADD, REENTRY, and Cash on a better marginal capital unit, including lot-notional and rank-band pressure as PIT evidence.
- PS: continue enforcing explicit lot/cap authority; do not silently reject all high-notional starters.

No new component or model is required by the evidence.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-09-07`
2. `GROWTH_WINDOW`: `2023-01-18 -> 2023-04-10`
3. `POST_APRIL_WINDOW`: `2023-04-11 -> 2023-09-07`
4. `PLATEAU_WINDOW`: `2023-06-19 -> 2023-08-08`
5. `RECOVERY_CONTROL_WINDOW`: `2023-08-23 -> 2023-09-07`
6. `GENUINE_BUY_NEW_POPULATION_COUNT`: `356 total; 163 post-April used for primary post-April comparison`
7. `POST_APRIL_NEWLY_EXECUTABLE_DUE_TO_PORTFOLIO_GROWTH_COUNT`: `28 soft/hard pressure; 9 strict hard-cap-at-1M`
8. `POST_APRIL_NEWLY_EXECUTABLE_DUE_TO_PORTFOLIO_GROWTH_NOTIONAL`: `6,645,550 soft/hard pressure; 2,766,400 strict hard-cap-at-1M`
9. `EFFECTIVE_BUY_UNIVERSE_EXPANDED_WITH_EQUITY`: `YES_MODERATE_FOR_FUNDED_BUY_NEW; NOT_CONFIRMED_FOR_CANDIDATE_SET`
10. `POST_APRIL_NEW_HIGHER_NOTIONAL_SHIFT_SUPPORTED`: `YES_FOR_FUNDED_BUY_NEW`
11. `GROWTH_MEDIAN_MINIMUM_LOT_NOTIONAL`: `52,200`
12. `POST_APRIL_MEDIAN_MINIMUM_LOT_NOTIONAL`: `68,600`
13. `GROWTH_MEDIAN_INITIAL_WEIGHT`: `4.18%`
14. `POST_APRIL_MEDIAN_INITIAL_WEIGHT`: `4.18%`
15. `NEWLY_EXECUTABLE_PIT_QUALITY_VS_ALWAYS_EXECUTABLE`: `MIXED`
16. `NEWLY_EXECUTABLE_FOLLOW_THROUGH`: `MIXED`
17. `UNIVERSE_SHIFT_DRIVEN_BY_HIGH_NOTIONAL_STARTERS`: `PARTIAL`
18. `PRIMARY_EXECUTABILITY_EXPANSION_DRIVER`: `EQUITY_WEIGHT_CAP_PRIMARY; CASH_RECYCLING_SECONDARY`
19. `CANDIDATE_POPULATION_SHIFT_SUPPORTED`: `NO_WEAK`
20. `EXECUTABILITY_FILTER_SHIFT_SUPPORTED`: `YES_MODERATE`
21. `LOWER_RANK_CANDIDATES_BECAME_EXECUTABLE_WITH_GROWTH`: `YES`
22. `PORTFOLIO_GROWTH_EFFECT_ON_NEW_CAPITAL`: `BOTH`
23. `NEWLY_EXECUTABLE_SHARE_OF_STARTER_CHURN_CAPITAL`: `41.0%`
24. `RECOVERY_CONTROL_WEAKENS_UNIVERSE_SHIFT_HYPOTHESIS`: `YES_PARTIAL`
25. `MARKET_CONDITION_DOMINATES_WITHIN_SAME_NOTIONAL_BUCKET`: `PARTIAL_YES_SHORT_RECOVERY_SAMPLE`
26. `MARKET_FOLLOW_THROUGH_CONTRIBUTION`: `PRIMARY`
27. `ACTION_TYPE_BIAS_CONTRIBUTION`: `SECONDARY`
28. `STARTER_CHURN_CONTRIBUTION`: `SECONDARY`
29. `EFFECTIVE_UNIVERSE_EXPANSION_CONTRIBUTION`: `SECONDARY_TO_MINOR_AMPLIFIER`
30. `PRIMARY_NEW_QUALITY_DECLINE_ROOT_CAUSE`: `MIXED_WITH_PRIMARY_WEAKER_MARKET_FOLLOW_THROUGH`
31. `SECONDARY_NEW_QUALITY_DECLINE_CAUSES`: `ACTION_TYPE_BIAS; STARTER_CHURN; LOWER_RANK_EXECUTABILITY; EFFECTIVE_UNIVERSE_EXPANSION; HIGH_NOTIONAL_STARTER_TAIL_RISK`
32. `SYSTEM_SIDE_REPAIRABLE_MECHANISM_FOUND`: `YES_SHADOW_ONLY`
33. `REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE`: `YES_CANDIDATE_BQ_PC_PS_MARGINAL_CAPITAL`
34. `NEW_COMPONENT_REQUIRED`: `NO`
35. `NEW_MODEL_REQUIRED`: `NO`
36. `PRODUCTION_CHANGE_JUSTIFIED`: `NO`
37. `SHADOW_FOLLOWUP_JUSTIFIED`: `YES`
38. `NEXT_RECOMMENDED_STEP`: design a SHADOW marginal-capital / lot-pressure / rank-band diagnostic inside existing Candidate/BQ/PC/PS architecture; do not promote a Production threshold from this audit.
39. `FINAL_JUDGMENT`: `PHASE32_CL_EFFECTIVE_BUY_NEW_UNIVERSE_EXPANSION_SUPPORTED_AS_SECONDARY_AMPLIFIER_PRIMARY_DECLINE_CAUSE_WEAKER_MARKET_FOLLOW_THROUGH_WITH_NEW_STARTER_CHURN_ACTION_BIAS_SHADOW_FOLLOWUP_JUSTIFIED_NO_PRODUCTION_CHANGE`

## Final Judgment

`PHASE32_CL_EFFECTIVE_BUY_NEW_UNIVERSE_EXPANSION_SUPPORTED_AS_SECONDARY_AMPLIFIER_PRIMARY_DECLINE_CAUSE_WEAKER_MARKET_FOLLOW_THROUGH_WITH_NEW_STARTER_CHURN_ACTION_BIAS_SHADOW_FOLLOWUP_JUSTIFIED_NO_PRODUCTION_CHANGE`
