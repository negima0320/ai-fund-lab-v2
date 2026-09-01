# Phase32-BZ — Recurrent BQ INSUFFICIENT/HOLD Later-Loss PIT Separability READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Audit mode: READ-ONLY
- Quantitative snapshot: completed evidence through `2023-04-18`
- Reference preserved: `docs/phase_reports/phase32_by_post_bq_long_run_profit_retention_large_loss_mechanism_read_only_audit.md`

No source, config, runtime state, Pending, Ledger, recovery, replay, resume, or fresh-run mutation was performed. The running Historical validation was not interrupted.

This audit deliberately excludes the separate `59350`-style Winner Profit Retention / PM HOLD confirmation-lag mechanism except as an explicit non-BZ mechanism. BZ is limited to:

```text
PM REDUCE
-> REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
-> BQ SHADOW_INSUFFICIENT_EVIDENCE or SHADOW_HOLD
-> NO_ORDER
-> later material loss label
```

Later outcomes are used only after PIT event grouping to label harmful/beneficial/neutral outcomes. They are not used as Production decision input.

## Evidence Sources

- `docs/phase_reports/phase32_by_post_bq_long_run_profit_retention_large_loss_mechanism_read_only_audit.md`
- `.runtime/runtime_state/sell_pipeline/<business_date>/order_plan.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<business_date>/current_valuation_refresh/current_valuation_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/daily/<business_date>/execution/fills.json`
- `src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py`
- `docs/phase_reports/phase32_bq_lot_blocked_reduce_reconsidered_full_exit_production_implementation.md`
- `docs/phase_reports/phase32_bp_bo_full_exit_production_promotion_acceptance_read_only_audit.md`

The run had advanced beyond the BY window when inspected, but this report fixes the audit boundary at `2023-04-18` to keep the comparison aligned with Phase32-BY and avoid chasing a moving long-run state.

## Population

Population rule:

- `lot_blocked_reduce_reconsiderations.status = NOT_PROMOTED`
- `bo_shadow_binary_decision in {SHADOW_INSUFFICIENT_EVIDENCE, SHADOW_HOLD}`
- matching non-executable REDUCE quantity contract has `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`

Counts through `2023-04-18`:

| Scope | Count |
|---|---:|
| raw non-promoted BQ rows | 219 |
| unique campaign/symbol first episodes | 113 |
| raw `SHADOW_INSUFFICIENT_EVIDENCE` | 201 |
| raw `SHADOW_HOLD` | 18 |
| campaign-level `SHADOW_INSUFFICIENT_EVIDENCE` first episodes | 103 |
| campaign-level `SHADOW_HOLD` first episodes | 10 |

The count differs from BY's 220 non-promoted lot-blocked cases because BY included one unpaired/blank BO outcome. BZ requires `SHADOW_INSUFFICIENT_EVIDENCE` or `SHADOW_HOLD`, so the BZ population is 219 raw rows.

## Outcome Labeling

For each event, the PIT snapshot is frozen first. The later label then uses only subsequent same-run valuation or sell-fill evidence within the next five completed business days.

Label rule:

- `HARMFUL_NON_PROMOTION`: worst observed position value or sell-fill value within +5BD is at least `10,000` below the event-date position value.
- `BENEFICIAL_NON_PROMOTION`: best observed value within +5BD is at least `10,000` above the event-date value and no material loss occurred first in the window.
- `NEUTRAL`: neither harmful nor beneficial by the above materiality.
- `INSUFFICIENT_OUTCOME`: no adequate +5BD valuation/fill evidence in the fixed snapshot.

Campaign-level first episode labels:

| Label | Campaign count |
|---|---:|
| `HARMFUL_NON_PROMOTION` | 5 |
| `BENEFICIAL_NON_PROMOTION` | 3 |
| `NEUTRAL` | 104 |
| `INSUFFICIENT_OUTCOME` | 1 |

Raw-event labels:

| Label | Raw count |
|---|---:|
| `HARMFUL_NON_PROMOTION` | 6 |
| `BENEFICIAL_NON_PROMOTION` | 5 |
| `NEUTRAL` | 155 |
| `INSUFFICIENT_OUTCOME` | 53 |

The raw harmful count includes a repeated warning for `14000` on the same campaign. Campaign-level economic counting avoids treating that as a fully separate loss pool.

## Harmful Non-Promotion Cases

| Date | Symbol | Campaign | BQ | PM reason | Raw reduce | Base value | Worst +5BD loss | Worst evidence | PIT features |
|---|---:|---|---|---|---:|---:|---:|---|---|
| 2022-12-02 | 78860 | `pc-4abc6670738d0096-78860-0001` | `SHADOW_INSUFFICIENT_EVIDENCE` | `peak_drawdown_warning` | 50 | 146,600 | -18,400 | 2022-12-07 sell fill | age 17; return +31.3%; participation WEAK; risk votes 2; profit `PROFIT_AT_RISK` |
| 2022-12-14 | 97310 | `pc-b0d08c20d01781e0-97310-0001` | `SHADOW_INSUFFICIENT_EVIDENCE` | `peak_drawdown_warning` | 33 | 205,700 | -24,500 | 2022-12-20 sell fill | age 26; return +5.2%; participation WEAK; risk votes 2; strong structure true; profit `PROFIT_AT_RISK` |
| 2023-02-24 | 14000 | `pc-aa5f669b8e6cec24-14000-0001` | `SHADOW_INSUFFICIENT_EVIDENCE` | `risk_increased_but_trend_not_broken` | 66 | 32,400 | -17,400 | 2023-03-02 valuation | age 2; return -5.4%; risk votes 0; no profit cushion |
| 2023-04-05 | 52470 | `pc-85bf06340b720569-52470-0001` | `SHADOW_INSUFFICIENT_EVIDENCE` | `risk_increased_but_trend_not_broken` | 25 | 271,000 | -10,000 | 2023-04-06 sell fill | age 2; return +6.8%; trend MIXED; participation WEAK; risk votes 4; reversal ELEVATED_RISK |
| 2023-04-13 | 41660 | `pc-5915e6229ecf467b-41660-0001` | `SHADOW_HOLD` | `peak_drawdown_warning` | 50 | 168,500 | -32,100 | 2023-04-18 valuation | age 1; return +8.1%; supportive trend/participation; risk votes 0; profit `CONTEXTUAL_HOLD_SUPPORT` |

Repeated raw warning:

- `14000` also warned on `2023-03-01`, same campaign, `SHADOW_INSUFFICIENT_EVIDENCE`, raw reduce 66, base value 30,800, worst +5BD loss -15,800 by `2023-03-02`.

The supported campaign-level loss pool from this audit's direct +5BD labeling is approximately `102,400`. Phase32-BY's broader supported pool remains approximately `108,000` because it used the Phase32-BX framing for `97310` at about `30,200` instead of this audit's strict +5BD sell-fill delta of `24,500`.

## Beneficial And Neutral Controls

Campaign-level beneficial first episodes:

| Date | Symbol | Campaign | BQ | PM reason | Base value | Best +5BD gain | Worst +5BD change | PIT notes |
|---|---:|---|---|---|---:|---:|---:|---|
| 2022-10-04 | 92420 | `pc-987b8a65c3a66940-92420-0001` | `SHADOW_INSUFFICIENT_EVIDENCE` | `risk_increased_but_trend_not_broken` | 136,200 | +15,800 | +1,000 | weak trend/participation, elevated risk |
| 2022-10-31 | 99840 | `pc-d6cacadc60246e75-99840-0001` | `SHADOW_HOLD` | `peak_drawdown_warning` | 160,000 | +13,230 | +3,930 | supportive structure, profit `CONTEXTUAL_HOLD_SUPPORT` |
| 2023-03-23 | 43880 | `pc-d6a6356c6cfd8db1-43880-0001` | `SHADOW_INSUFFICIENT_EVIDENCE` | `peak_drawdown_warning` | 127,900 | +19,400 | -7,400 | profit `PROFIT_AT_RISK`, but no material +5BD loss |

This control set matters: several PIT dimensions that appear in harmful cases also appear in beneficial or neutral cases.

## PIT Separability

Separability judgment:

```text
PARTIALLY_SEPARABLE
```

Most informative existing PIT dimensions:

- Event notional / base position value: harmful median `168,500`, neutral median `47,160`.
- Profit-at-risk or peak-drawdown context: 3 of 5 harmful campaigns, but also 2 beneficial and 16 neutral campaign first episodes.
- Weak participation plus elevated risk: present in `78860`, `97310`, and `52470`, but common in neutral rows.
- High risk-vote count and elevated reversal: `52470` is close to the current FULL_EXIT semantic neighborhood.
- Lack of recovery: all 5 harmful campaign first episodes have `NO_RECOVERY`, but this is also true for nearly all neutral rows.

Not sufficient as standalone splitters:

- `risk_increased_but_trend_not_broken`: 2 harmful, 1 beneficial, 88 neutral campaign first episodes.
- `peak_drawdown_warning`: 3 harmful, 2 beneficial, 16 neutral campaign first episodes.
- BQ result alone: `SHADOW_INSUFFICIENT_EVIDENCE` contains most harmful cases but also most neutral cases; `SHADOW_HOLD` has one harmful and one beneficial campaign first episode.
- Repeated REDUCE persistence: 72 of 113 campaigns have multiple raw non-promoted warnings, but the five harmful first episodes all have `reduce_history_summary.event_count = 0` at their first warning. Repetition is useful as an observation pattern, not as a first-warning decisive PIT feature in the current artifact shape.

The harmful subset is not random, but it is not strongly separable using one existing field. It appears to require a composite PIT-only shadow feature that distinguishes:

```text
profit cushion / peak drawdown + capital at risk + deterioration or weak participation + no recovery + lot-blocked unrepresentability
```

from ordinary one-lot noise and legitimate continuation.

## SHADOW_HOLD vs INSUFFICIENT

Campaign-level harmful split:

- `SHADOW_INSUFFICIENT_EVIDENCE`: 4 campaign first episodes; 5 raw harmful rows
- `SHADOW_HOLD`: 1 campaign first episode; 1 raw harmful row

The `41660` `SHADOW_HOLD` case is the important exception. Its PIT evidence had supportive trend/participation and contextual profit-cushion HOLD support, so current BO logic had a coherent reason to hold. The later -32,100 label exposes a performance limitation, not proof that the current HOLD semantics are invalid under PIT.

For `SHADOW_INSUFFICIENT_EVIDENCE`, the larger issue is under-materialization of mixed evidence. Some cases are close to current FULL_EXIT (`52470`), while others contain structural support or insufficient deterioration confirmation (`97310`, first `14000`).

## Current FULL_EXIT Neighborhood

Current BQ FULL_EXIT promotions through the same snapshot:

- promotions: 31
- reason family: 30 `risk_increased_but_trend_not_broken`, 1 profit-retention/peak-drawdown
- trend: all `MIXED` or `WEAK`
- strong medium-term structure: false for all 31
- reversal risk: all `MIXED` or `ELEVATED_RISK`
- recovery: all `NO_RECOVERY`

Overlap with harmful non-promotions:

- `52470` is nearest: trend MIXED, participation WEAK, risk votes 4, reversal ELEVATED_RISK.
- `14000` repeated warning on `2023-03-01` moves closer than its first warning: participation WEAK, risk votes 3, reversal ELEVATED_RISK.
- `78860` has weak participation/elevated risk but trend remains SUPPORTIVE and reversal MIXED.
- `97310` and `41660` retain supportive structure that current BQ reasonably treats as mixed or HOLD-supportive.

Therefore the current FULL_EXIT semantic neighborhood overlaps with part of the harmful non-promoted population, but not enough to justify broad Production promotion.

## False-Exit Risk

False-exit risk if BQ is broadened mechanically:

```text
HIGH
```

Reasons:

- 104 of 113 campaign first episodes are neutral under the +5BD materiality rule.
- 3 campaign first episodes are beneficial non-promotions.
- Many neutral/beneficial rows share broad warning features such as `risk_increased_but_trend_not_broken`, `peak_drawdown_warning`, weak participation, elevated risk, and profit-at-risk context.
- Current BO/BQ FULL_EXIT was accepted because it is narrow: no structural HOLD evidence, multiple deterioration dimensions, no recovery, and explicit PIT authority.

A Production change that simply promotes more `SHADOW_INSUFFICIENT_EVIDENCE` or `SHADOW_HOLD` cases would likely convert legitimate holds into unnecessary exits.

## BY Relationship

Phase32-BY conclusions remain valid:

- upside capture is strong
- BQ FULL EXIT promotions are active and not shown to impair winner capture
- the recurrent non-promoted later-loss population exists
- the supported avoidable-loss pool is material but partial
- `59350`-style HOLD confirmation lag is a separate mechanism

BZ refines the BY non-promoted population: the concrete later-loss pool is reproducible, but current PIT evidence supports only partial separability, not immediate broad Production promotion.

## Repair / Design Implications

Production change justified now:

```text
NO
```

New threshold justified now:

```text
NO
```

New model required:

```text
NO_CONCRETE_EVIDENCE
```

New feature or shadow refinement justified:

```text
YES
```

The next safe step is a SHADOW-only refinement, not a direct Production change. The refinement should test a PIT-only composite feature around profit protection / peak drawdown / no-recovery / weak participation / elevated risk / unrepresentable reduce, with explicit false-exit controls from the beneficial and neutral cases.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-04-18_FOR_FIXED_BZ_AUDIT_SNAPSHOT`
2. `NON_PROMOTED_RAW_EVENT_COUNT = 219`
3. `NON_PROMOTED_CAMPAIGN_COUNT = 113`
4. `BQ_INSUFFICIENT_COUNT = 201_RAW / 103_CAMPAIGN_FIRST_EPISODES`
5. `BQ_HOLD_COUNT = 18_RAW / 10_CAMPAIGN_FIRST_EPISODES`
6. `HARMFUL_NON_PROMOTION_COUNT = 6_RAW / 5_CAMPAIGN_LEVEL`
7. `BENEFICIAL_NON_PROMOTION_COUNT = 5_RAW / 3_CAMPAIGN_LEVEL`
8. `NEUTRAL_COUNT = 155_RAW / 104_CAMPAIGN_LEVEL`
9. `ESTIMATED_HARMFUL_NON_PROMOTION_LOSS = APPROX_102,400_STRICT_BZ_5BD_CAMPAIGN_LEVEL; PHASE32_BY_SUPPORTED_POOL_APPROX_108,000_REMAINS_VALID`
10. `78860_REPRODUCED = YES`
11. `97310_REPRODUCED = YES`
12. `14000_REPRODUCED = YES`
13. `52470_REPRODUCED = YES`
14. `41660_REPRODUCED = YES`
15. `HARMFUL_VS_BENEFICIAL_PIT_SEPARABILITY = PARTIALLY_SEPARABLE`
16. `MOST_INFORMATIVE_EXISTING_PIT_DIMENSIONS = POSITION_NOTIONAL, PROFIT_AT_RISK/PEAK_DRAWDOWN_CONTEXT, WEAK_PARTICIPATION, ELEVATED_RISK/REVERSAL, NO_RECOVERY, CURRENT_FULL_EXIT_NEIGHBORHOOD_PROXIMITY`
17. `REPEATED_REDUCE_PERSISTENCE_INFORMATIVE = WEAK_AS_FIRST_WARNING_SIGNAL; USEFUL_AS_OBSERVATION_PATTERN`
18. `PEAK_DRAWDOWN_WARNING_ASSOCIATION = PRESENT_BUT_NOT_STANDALONE_DECISIVE`
19. `RISK_INCREASED_NOT_BROKEN_ASSOCIATION = COMMON_LOW_PRECISION_SIGNAL`
20. `BQ_HOLD_HARMFUL_CASES = 1_CAMPAIGN / 1_RAW; SYMBOL_41660_ON_2023-04-13`
21. `BQ_INSUFFICIENT_HARMFUL_CASES = 4_CAMPAIGN / 5_RAW; SYMBOLS_78860_97310_14000_52470`
22. `CURRENT_FULL_EXIT_SEMANTIC_NEIGHBORHOOD_OVERLAP = PARTIAL; 52470_AND_REPEATED_14000_ARE_NEAREST, 97310_AND_41660_RETAIN_SUPPORTIVE_STRUCTURE`
23. `FALSE_EXIT_RISK_IF_BQ_BROADENED = HIGH`
24. `NEW_FEATURE_REQUIRED = YES_FOR_SHADOW_REFINEMENT_OR_COMPOSITE_PIT_FEATURE`
25. `NEW_MODEL_REQUIRED = NO_CONCRETE_EVIDENCE`
26. `NEW_THRESHOLD_JUSTIFIED = NO_FOR_PRODUCTION; ONLY_SHADOW_EXPLORATION_IF_DONE`
27. `PRODUCTION_CHANGE_JUSTIFIED = NO`
28. `SHADOW_REFINEMENT_JUSTIFIED = YES`
29. `NEXT_RECOMMENDED_STEP = SHADOW-only PIT composite refinement for recurrent lot-blocked REDUCE non-promotions, explicitly benchmarked against beneficial/neutral controls; keep 59350-style HOLD confirmation lag in a separate study.`
30. `FINAL_JUDGMENT = PHASE32_BZ_RECURRENT_BQ_INSUFFICIENT_HOLD_LATER_LOSS_POPULATION_REPRODUCED_PARTIALLY_PIT_SEPARABLE_SHADOW_REFINEMENT_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

