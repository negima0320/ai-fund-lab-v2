# Phase32-BJ - PM REDUCE -> Full EXIT Counterfactual READ-ONLY Characterization

## Scope

Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`

Evidence snapshot used for this report:

- completed business days: `388`
- covered window: `2022-10-03` through `2024-05-01`
- run state observed during audit: `RUNNING`
- cutoff fixed to `2024-05-01` to avoid mixing later evidence while the Historical run continues

This is a READ-ONLY characterization. No source, config, runtime state, Pending, Ledger, replay, resume, recover, or fresh-run action was performed. The running Historical validation was not interrupted.

Method:

- PM REDUCE rows were read from daily `position_management/pm_decisions.json`.
- Executable REDUCE was identified by same-day SELL fill with `source_decision_type = REDUCE`.
- Lot-blocked REDUCE was PM REDUCE with no same-day executable partial SELL.
- Counterfactual Full EXIT value used PM decision-time `market_value` / `quantity_before * current_price`.
- Actual subsequent value used same-campaign future fill cash effects from the REDUCE date onward plus final snapshot market value if still open at the cutoff.
- Neutral threshold: absolute effect <= `1,000`.
- Historical outcomes were used only for characterization, not as a decision-time policy selector.

## REDUCE Population

| Population | Count |
|---|---:|
| Total PM REDUCE rows | 904 |
| Lot-blocked REDUCE rows | 847 |
| Executable REDUCE rows | 57 |
| Lot-blocked affected campaigns | 343 |
| Executable REDUCE affected campaigns | 35 |
| Campaigns with any PM REDUCE | 362 |

The PM REDUCE population is overwhelmingly composed of 100-share/minimum-lot cases where PM requested de-risking but no partial lot could be materialized. This confirms the same structural shape found in BH, but BJ evaluates the additional question: whether Full EXIT would dominate REDUCE.

## Policy A - Lot-Blocked REDUCE -> Full EXIT

Policy A converts the first lot-blocked REDUCE in each affected campaign to immediate Full EXIT and leaves executable partial REDUCE unchanged.

| Result | Count / Amount |
|---|---:|
| Counterfactual cases | 343 |
| Full EXIT would have helped | 138 |
| Hold/current path was better | 62 |
| Neutral | 143 |
| Avoided subsequent loss | 863,980 |
| Forfeited recovery/winner gain | 518,140 |
| Net effect | +345,840 |
| Winner false-exit cost | 518,140 |

Major helped cases:

| Symbol | REDUCE date | Start value | Actual subsequent value | Full EXIT benefit | PIT reason |
|---|---:|---:|---:|---:|---|
| 67310 | 2023-04-24 | 300,000 | 200,000 | +100,000 | `risk_increased_but_trend_not_broken` |
| 62310 | 2023-05-01 | 211,600 | 176,000 | +35,600 | `risk_increased_but_trend_not_broken` |
| 74770 | 2023-10-04 | 325,000 | 295,100 | +29,900 | `risk_increased_but_trend_not_broken` |
| 34160 | 2024-03-05 | 132,500 | 107,200 | +25,300 | `peak_drawdown_warning` |
| 36670 | 2023-06-16 | 77,500 | 52,500 | +25,000 | `risk_increased_but_trend_not_broken` |
| 51890 | 2023-04-14 | 273,000 | 248,750 | +24,250 | `peak_drawdown_warning` |

Major false exits / forfeited winners:

| Symbol | REDUCE date | Start value | Actual subsequent value | Full EXIT forfeiture | PIT reason |
|---|---:|---:|---:|---:|---|
| 62280 | 2023-12-22 | 272,670 | 327,330 | -54,660 | `peak_drawdown_warning` |
| 74270 | 2023-08-14 | 116,500 | 157,600 | -41,100 | `risk_increased_but_trend_not_broken` |
| 92270 | 2022-10-24 | 107,300 | 137,300 | -30,000 | `risk_increased_but_trend_not_broken` |
| 72140 | 2023-05-25 | 148,500 | 172,500 | -24,000 | `peak_drawdown_warning` |
| 83040 | 2024-02-21 | 221,500 | 244,550 | -23,050 | `peak_drawdown_warning` |
| 69730 | 2022-11-04 | 158,600 | 178,500 | -19,900 | `peak_drawdown_warning` |

Interpretation: Policy A has positive descriptive economics in the inspected window, but the false-exit cost is large enough that a mechanical unconditional production change is not justified from this audit alone.

## Policy B - All PM REDUCE -> Full EXIT

Policy B converts the first PM REDUCE in each campaign to immediate Full EXIT, including campaigns whose first REDUCE was executable as a partial SELL.

| Result | Count / Amount |
|---|---:|
| Counterfactual cases | 362 |
| Full EXIT would have helped | 150 |
| Partial/Hold/current path was better | 68 |
| Neutral | 144 |
| Avoided subsequent loss | 897,810 |
| Forfeited recovery/winner gain | 584,340 |
| Net effect | +313,470 |
| Winner false-exit cost | 584,340 |

Policy B adds only `33,830` more avoided loss than Policy A, but adds `66,200` more forfeited gain. Its net effect is therefore lower than Policy A by `32,370`.

The executable-first subset in Policy B had:

- cases: `34`
- avoided loss: `38,530`
- forfeited gain: `75,500`
- net: `-36,970`

This is the key result: forcing executable partial REDUCE into Full EXIT would have harmed the inspected evidence set.

## Executable Partial REDUCE Economic Value

First executable REDUCE per campaign:

| Result | Count / Amount |
|---|---:|
| Cases | 35 |
| Full EXIT would have been better | 15 |
| Partial REDUCE preserved later value | 9 |
| Neutral | 11 |
| Avoided loss from Full EXIT | 38,530 |
| Forfeited gain from Full EXIT | 75,500 |
| Net effect of Full EXIT vs partial | -36,970 |

Major cases where Full EXIT would have been better:

| Symbol | REDUCE date | Full EXIT benefit |
|---|---:|---:|
| 76010 | 2023-05-17 | +4,600 |
| 45860 | 2023-02-17 | +3,700 |
| 66590 | 2023-08-10 | +3,700 |
| 33500 | 2024-04-15 | +3,000 |
| 65740 | 2023-12-05 | +2,780 |
| 93180 | 2023-01-27 | +2,600 |

Major cases where partial REDUCE preserved value:

| Symbol | REDUCE date | Full EXIT forfeiture |
|---|---:|---:|
| 66590 | 2024-02-27 | -26,700 |
| 97040 | 2024-03-01 | -19,800 |
| 77090 | 2023-06-30 | -9,900 |
| 26560 | 2023-05-25 | -6,600 |
| 89180 | 2023-12-27 | -4,800 |
| 92630 | 2023-06-16 | -3,300 |

Conclusion: executable partial REDUCE has material economic value relative to immediate Full EXIT. This argues against removing REDUCE globally.

## PIT Evidence Separability

For lot-blocked Policy A cases:

| PIT grouping | Count | Helped | Hurt | Neutral | Avoided | Forfeited | Net |
|---|---:|---:|---:|---:|---:|---:|---:|
| `risk_increased_but_trend_not_broken` | 288 | 122 | 32 | 134 | 680,430 | 209,460 | +470,970 |
| `peak_drawdown_warning` | 55 | 16 | 30 | 9 | 183,550 | 308,680 | -125,130 |
| `action_score < 0.4` | 246 | 100 | 26 | 120 | 557,920 | 138,030 | +419,890 |
| `action_score >= 0.4` | 97 | 38 | 36 | 23 | 306,060 | 380,110 | -74,050 |
| current return `< 0` | 124 | 53 | 15 | 56 | 303,810 | 117,780 | +186,030 |
| current return `>= 5%` | 48 | 18 | 18 | 12 | 225,870 | 210,360 | +15,510 |

Classification: `PARTIALLY_SEPARABLE`.

Reasoning:

- `risk_increased_but_trend_not_broken` and lower action scores skew toward Full EXIT helping.
- `peak_drawdown_warning` and higher action scores skew toward Hold/recovery being better.
- However, overlap remains large. `74270` and `92270` show that even weak-hold style REDUCE can later recover materially; `34160`, `51890`, and `60220` show that peak-drawdown warnings can also precede further loss.
- Therefore existing PIT fields are useful for a shadow conditional design, but not sufficient to accept a hard mechanical rule in this phase.

## Winner False-Exit Risk

Policy A false-exit cost: `518,140`.

Policy B false-exit cost: `584,340`.

Material winners/recoveries that would have been prematurely closed include:

- `62280`: Policy A would forfeit `54,660` after a `2023-12-22` lot-blocked REDUCE. PIT reason was `peak_drawdown_warning`; current return was about `+9.5%`.
- `74270`: Policy A would forfeit `41,100` after a `2023-08-14` lot-blocked REDUCE. PIT reason was `risk_increased_but_trend_not_broken`; current return was about `+2.6%`.
- `66590`: executable partial REDUCE on `2024-02-27`; Policy B Full EXIT would forfeit `26,700`.
- `97040`: executable partial REDUCE on `2024-03-01`; Policy B Full EXIT would forfeit `19,800`.

Winner false-exit risk is therefore HIGH for global REDUCE -> Full EXIT, and MATERIAL even for lot-blocked-only conversion.

## Relationship to BF/BG/BH/BI

BF winner profit retention:

- Policy A would materially improve the most visible late-retention failure in `67310` by avoiding `100,000` of subsequent giveback after the first lot-blocked REDUCE.
- It would not solve all BF winner retention because it also exits genuine recoveries such as `62280`, `74270`, and `83040`.
- Judgment: `PARTIAL_IMPROVEMENT`.

BF weak starter accumulation:

- Policy A improves many weak-starter deterioration cases where the first lot-blocked REDUCE was followed by additional loss.
- It is not a full weak-starter solution because many weak-starter losses occur without a clean REDUCE-to-exit decision point.
- Judgment: `PARTIAL_IMPROVEMENT`.

BG high-notional tail:

- Policy A shrinks some high-notional loss tails, notably `74770`, `51890`, and `60220`.
- It does not justify a blunt entry notional cap because high-notional winners remain material.
- Judgment: `PARTIAL_IMPROVEMENT`.

BH blocked-REDUCE net harm:

- BH reported `-390,380` net blocked-REDUCE consequence on its earlier snapshot.
- BJ Policy A, using the current fixed `2024-05-01` snapshot and full campaign-value accounting, recovers a net `+345,840`.
- This substantially supports BH's finding that lot-blocked REDUCE is economically material.
- Judgment: `SUBSTANTIALLY_RECOVERABLE`, with method/snapshot differences noted.

BI winner rejection problem:

- BI showed strict entry manageability would reject `79.7%` of BUY_NEW campaigns and produce a descriptive `-514,290` net effect.
- BJ avoids that entry-filter problem because it waits until actual post-entry PM deterioration evidence appears.
- However, BJ still has false-exit cost and therefore does not justify immediate production conversion.
- Judgment: `ENTRY_FILTER_PROBLEM_AVOIDED_BY_POST_ENTRY_DESIGN`, but conditional PIT evidence is still required.

## Architecture Judgment

Best-supported interpretation:

`REDUCE_REQUIRES_PIT_CONDITIONAL_BINARY_MATERIALIZATION`

Supporting evidence:

- Normal executable partial REDUCE should not be removed: its first-executable subset shows Full EXIT net `-36,970`.
- Lot-blocked REDUCE is economically material: Policy A net `+345,840`.
- Mechanical lot-blocked REDUCE -> Full EXIT has material false-exit cost: `518,140`.
- Existing PIT fields partially separate harmful from beneficial cases, especially reason family and action_score, but not enough for a direct hard rule.

Rejected interpretations:

- `REDUCE_ACTION_ITSELF_HAS_LOW_ECONOMIC_VALUE`: not supported because executable partial REDUCE preserves more value than Full EXIT.
- `CURRENT_REDUCE_DESIGN_REMAINS_PREFERRED`: not fully supported because lot-blocked REDUCE remains a material post-entry capital-rotation gap.
- `REDUCE_IS_VALID_LOT_BLOCK_MATERIALIZATION_IS_THE_PROBLEM`: directionally true, but incomplete because lot-blocked Full EXIT should be conditional, not automatic.

## Required Final Answers

1. `TOTAL_PM_REDUCE_EVENTS`: `904`
2. `LOT_BLOCKED_REDUCE_COUNT`: `847`
3. `EXECUTABLE_REDUCE_COUNT`: `57`
4. `LOT_BLOCKED_AFFECTED_CAMPAIGNS`: `343`
5. `EXECUTABLE_REDUCE_AFFECTED_CAMPAIGNS`: `35`
6. `POLICY_A_AVOIDED_LOSS`: `863,980`
7. `POLICY_A_FORFEITED_GAIN`: `518,140`
8. `POLICY_A_NET_EFFECT`: `+345,840`
9. `POLICY_A_WINNER_FALSE_EXIT_COST`: `518,140`
10. `POLICY_B_AVOIDED_LOSS`: `897,810`
11. `POLICY_B_FORFEITED_GAIN`: `584,340`
12. `POLICY_B_NET_EFFECT`: `+313,470`
13. `POLICY_B_WINNER_FALSE_EXIT_COST`: `584,340`
14. `PARTIAL_REDUCE_ECONOMIC_VALUE`: `SUPPORTED`; executable partial REDUCE beats Full EXIT by `36,970` net in the inspected first-executable subset.
15. `LOT_BLOCKED_FULL_EXIT_ECONOMIC_VALUE`: `SUPPORTED_BUT_NOT_MECHANICALLY_ACCEPTED`; net `+345,840` but false-exit cost `518,140`.
16. `HARMFUL_VS_BENEFICIAL_PIT_SEPARABILITY`: `PARTIALLY_SEPARABLE`
17. `BF_WINNER_RETENTION_IMPROVEMENT`: `PARTIAL`
18. `BF_WEAK_STARTER_IMPROVEMENT`: `PARTIAL`
19. `BG_HIGH_NOTIONAL_TAIL_IMPROVEMENT`: `PARTIAL`
20. `BH_NET_HARM_RECOVERABLE_BY_POLICY_A`: `YES_SUBSTANTIALLY`
21. `BI_WINNER_REJECTION_PROBLEM_AVOIDED`: `YES`, because this is post-entry REDUCE evidence rather than entry exclusion.
22. `SHOULD_REDUCE_BE_REMOVED_GLOBALLY`: `NO`
23. `SHOULD_LOT_BLOCKED_REDUCE_AUTO_EXIT`: `NOT_AS_A_MECHANICAL_RULE_NOW`
24. `IS_CONDITIONAL_BINARY_RECONSIDERATION_SUPPORTED`: `YES`
25. `IS_THIS_A_CORRECTNESS_DEFECT`: `NO`; this is a design/economic materialization question, not a Runtime correctness defect.
26. `IS_DESIGN_CHANGE_JUSTIFIED`: `YES_FOR_SHADOW_DESIGN`
27. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: `NO`
28. `NEXT_RECOMMENDED_STEP`: design a PIT-only shadow contract for lot-blocked REDUCE binary materialization that can choose HOLD / partial REDUCE / Full EXIT without using future outcomes, and validate false-exit controls before any production semantics change.
29. `FINAL_JUDGMENT`: `PHASE32_BJ_REDUCE_FULL_EXIT_COUNTERFACTUAL_CHARACTERIZED_CONDITIONAL_LOT_BLOCKED_BINARY_RECONSIDERATION_SUPPORTED_GLOBAL_REDUCE_REMOVAL_REJECTED_NO_PRODUCTION_CHANGE`

## NO CHANGE Confirmation

- NO CODE CHANGE, except this report artifact.
- NO config change.
- NO Strategy parameter / threshold / weight change.
- NO PM / SELL / Corporate Action behavior change.
- NO fresh-run / resume / recover / replay / long Historical command executed.
- NO running Historical validation interruption.

