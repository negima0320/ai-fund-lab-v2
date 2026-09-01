# Phase32-CI — NEW vs REENTRY vs ADD Action-Type Bias / Post-April Opportunity Capture Root-Cause Audit

Target run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

Evidence snapshot:

- run status at inspection: `RUNNING`
- source commit recorded in run commands: `cf0a00b0271d170094aa0ce2bfbedc203c364406`
- latest completed business date used: `2023-08-22`
- completed business days used: `219`
- no mutating Runtime command was executed

This is a READ-ONLY / SHADOW audit. No code, config, Production ranking, REENTRY rule, ADD rule, cooldown, PC/PS behavior, Candidate AI, thresholds, weights, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run action was changed or executed.

## Preserved CH / CG Conclusions

CI preserves Phase32-CG and Phase32-CH:

- Post-April plateau is not explained by exposure collapse.
- Capital continued to be deployed, mainly into BUY_NEW.
- The primary CH mechanism is `STARTER_REPLACEMENT_CHURN_WITH_WEAK_FOLLOW_THROUGH_AFTER_MAJOR_WINNER_ENGINE_DECAY`.
- Secondary mechanisms include `WINNER_CAPITALIZATION_FUNNEL_SUPPRESSION` and `ADD_VS_NEW_MARGINAL_CAPITAL_SEMANTIC_GAP`.
- `runtime_opportunity_score` is an uncalibrated relative model score, not a common marginal-yen value.
- CH did not justify Production change.

## Decision Contract Comparison

`NEW_REENTRY_ADD_DECISION_CONTRACT_COMPARISON`:

| Action | Recognition source | Extra action-specific gates | Capital allocation boundary | PS / Runtime boundary |
|---|---|---|---|---|
| `BUY_NEW` | Candidate / Opportunity + Buy Quality + PC membership | broker/safety/corporate action, BQ, cash/cap/lot, PC selection | PC can directly target new membership and allocate buy weight | PS turns PC target into executable lot; Runtime maps positive new-position quantity to `BUY_NEW` |
| `REENTRY` | Candidate plus prior closed-campaign context | all NEW gates plus prior exit identity, strict-prior exit context, churn protection, renewed current evidence, recovery / requalification gates | only if REENTRY semantic status passes; otherwise target membership stays false | PS/Runtime can consume REENTRY only if PC/PS materialize valid REENTRY quantity |
| `BUY_ADD` | Existing position + Runtime PM / Strategy PM + SI ADD worthiness + BQ | all current-position gates plus PM ADD, Strategy PM confirmation, ADD worthiness, prior ADD safeguards, no-loss averaging, continuation/downside checks, target increment, cap/headroom, lot feasibility | PC must preserve ADD as a positive incremental capital competitor and emit positive accepted increment | PS turns accepted increment into executable lot; Runtime maps positive existing-position delta to `BUY_ADD` |

The current contract is action-neutral in stated principle: BUY_NEW label alone and BUY_ADD label alone must not increase priority. In actual materialization, NEW has fewer prerequisite layers before it can reach PC/PS executable capital.

## Explicit Priority Search

Source / SoT evidence:

- `marginal_capital_value.sort_key` sorts by marginal capital value class, rank, insufficiency flag, then symbol.
- artifacts expose `buy_add_unconditional_priority=false` and `buy_new_unconditional_priority=false`.
- SoT says `BUY_ADD label alone must not increase priority` and `BUY_NEW label alone must not increase priority`.
- SoT allows strong NEW to outrank weak ADD and strong ADD to outrank weaker/comparable NEW.
- Runtime Planning consumes PC/PS priority and must not re-rank.

No fixed source/config ordering equivalent to:

```text
NEW > REENTRY > ADD
```

was found.

However, the source and artifacts show an important gap:

- `marginal_capital_value.candidate_intent` handles current-position `ADD` as `BUY_ADD`;
- it handles non-current `membership_intent=ADD_CANDIDATE` as `BUY_NEW`;
- it does not expose REENTRY as a first-class marginal-capital competitor in that function;
- REENTRY rows in the target run remain rejected/reviewed before executable capital.

`EXPLICIT_ACTION_TYPE_PRIORITY_FOUND = NO_FIXED_ACTION_ORDER_FOUND`

Boundary note:

`REENTRY_FIRST_CLASS_MARGINAL_COMPETITOR_GAP = STRUCTURALLY_PRESENT`

## Action Conversion Funnels

| Period | Action | PC opportunity rows | PC/PS selected rows | BUY fills | Notional | Fill / opportunity |
|---|---|---:|---:|---:|---:|---:|
| Growth `2023-01-18` -> `2023-04-10` | NEW | 1,243 | 393 | 78 | 6,205,660 | 6.28% |
| Growth | REENTRY | 1,210 | 0 | 0 | 0 | 0.00% |
| Growth | ADD | 58 canonical PC ADD rows | 9 | 7 | 197,060 | 12.07% |
| Post-April `2023-04-11` -> `2023-08-22` | NEW | 1,333 | 423 | 153 | 15,870,240 | 11.48% |
| Post-April | REENTRY | 2,667 | 0 | 0 | 0 | 0.00% |
| Post-April | ADD | 9 canonical PC ADD rows | 0 | 0 | 0 | 0.00% |
| Plateau `2023-06-19` -> `2023-08-08` | NEW | 544 | 183 | 68 | 7,338,070 | 12.50% |
| Plateau | REENTRY | 1,057 | 0 | 0 | 0 | 0.00% |
| Plateau | ADD | 7 canonical PC ADD rows | 0 | 0 | 0 | 0.00% |

Additional PM observability ADD rows:

- Growth PM ADD observations: `74`
- Post-April PM ADD observations: `96`
- Plateau PM ADD observations: `43`

The post-April action mix is not a raw opportunity shortage. It is a conversion asymmetry:

```text
NEW reaches PC/PS/fill repeatedly.
REENTRY remains at semantic/review/requalification gates.
ADD is mostly converted to HOLD or zero increment before PS.
```

## REENTRY Audit

Post-April REENTRY rows:

| Metric | Count |
|---|---:|
| REENTRY PC rows | 2,667 |
| selected / target membership true | 0 |
| REENTRY fills | 0 |
| positive raw `runtime_opportunity_score` rows | 313 |
| long-lived positive-score non-active-churn rows | 241 |

Post-April REENTRY block classification:

| First REENTRY block | Count |
|---|---:|
| current evidence not requalified | 2,112 |
| prior context / insufficient evidence | 278 |
| active churn protection | 277 |

Plateau REENTRY block classification:

| First REENTRY block | Count |
|---|---:|
| current evidence not requalified | 849 |
| active churn protection | 105 |
| prior context / insufficient evidence | 103 |

Representative long-lived positive-score REENTRY rows:

| Date | Symbol | Prior exit | Elapsed BD | Score | BQ | State | Block |
|---|---|---|---:|---:|---|---|---|
| `2023-04-11` | `83060` | `2022-10-04` | 127 | 0.240059 | REDUCED_ALLOCATION_ONLY | REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE | current evidence not requalified |
| `2023-04-11` | `93180` | `2023-02-24` | 31 | 0.185198 | REDUCED_ALLOCATION_ONLY | REENTRY_INSUFFICIENT_EVIDENCE | prior context / insufficient evidence |
| `2023-06-19` | `67310` | `2023-04-11` | 46 | 0.143161 | REDUCED_ALLOCATION_ONLY | REENTRY_INSUFFICIENT_EVIDENCE | prior context / insufficient evidence |
| `2023-06-20` | `99840` | `2022-12-20` | 122 | 0.102968 | REDUCED_ALLOCATION_ONLY | REENTRY_INSUFFICIENT_EVIDENCE | prior context / insufficient evidence |
| `2023-06-23` | `76470` | `2023-01-24` | 103 | 0.206826 | REDUCED_ALLOCATION_ONLY | REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE | current evidence not requalified |

`LONG_LIVED_PRIOR_OWNERSHIP_PENALTY_FOUND = PARTIAL_STRUCTURAL_GATING_FOUND_NOT_PROVEN_AS_INVALID_PENALTY`

Reason:

- REENTRY faces durable additional requirements after churn protection is satisfied.
- Positive raw score alone is not valid REENTRY authority because the score is not a marginal-yen or reentry-recovery unit.
- CI did not find a semantic PASS REENTRY that was then defeated by a weaker NEW.

`VALID_REENTRY_OPPORTUNITIES_SUPPRESSED_COUNT = 0_CONFIRMED_SEMANTIC_PASS_REENTRY; 241_LONG_LIVED_POSITIVE_SCORE_REENTRY_ROWS_REQUIRE_SHADOW_REVIEW`

## ADD Suppression Audit

CH's post-April ADD evidence is preserved:

| Population | Count |
|---|---:|
| Post-April Runtime PM ADD observations | 96 |
| Post-April canonical PC ADD rows | 9 |
| Post-April selected positive ADD increments | 0 |
| Post-April BUY_ADD fills | 0 |

Post-April canonical PC ADD blockers:

| First block | Count |
|---|---:|
| PC ADD target weight unchanged | 6 |
| BUY Quality blocks incremental ADD | 3 |

Plateau PM ADD 43 split:

| First block | Count |
|---|---:|
| Runtime PM ADD -> Strategy PM HOLD | 36 |
| PC ADD target weight unchanged | 4 |
| BUY Quality blocks incremental ADD | 3 |

`ADD_STRUCTURALLY_HARDER_TO_MATERIALIZE_THAN_NEW = YES`

`ADD_EXTRA_BURDEN_SEMANTICALLY_JUSTIFIED = PARTIAL`

Justified parts:

- ADD should require current-position authority, no-loss averaging, continuation/downside evidence, cap/headroom, and lot feasibility.
- BUY_ADD must not be created from fallback/residual mechanics.

Potentially excessive / unresolved parts:

- Runtime PM ADD observations often become canonical HOLD before PC.
- PM ADD remains broad and HOLD-like.
- ADD lacks a separate high-resolution marginal next-lot value boundary.

## Same-Day Action Competition

Same-day action competition population, from `2023-03-01` onward:

- dates with at least two positive/opportunity-like action classes: `71`
- NEW vs REENTRY pair dates: `68`
- NEW vs ADD pair dates: `30`
- REENTRY vs ADD pair dates: `33`

Conditional winner counts:

| Pair | NEW wins | REENTRY wins | ADD wins | Cash/none | Other action wins |
|---|---:|---:|---:|---:|---:|
| NEW vs REENTRY | 58 | 0 | n/a | 8 | 2 |
| NEW vs ADD | 25 | n/a | 2 | 3 | 0 |
| REENTRY vs ADD | n/a | 0 | 2 | 4 | 27 |

`ACTION_TYPE_CONDITIONAL_WIN_RATES = NEW_DOMINANT_WHEN_REENTRY_PRESENT; ADD_CAN_WIN_IN_GROWTH_BUT_NOT_POST_APRIL; REENTRY_ZERO_WINS`

Representative same-day PIT examples:

| Date | Pair | Capital winner | Non-NEW evidence | First non-NEW block |
|---|---|---|---|---|
| `2023-03-01` | NEW vs REENTRY | NEW | 93180 raw score 0.242769, BQ REDUCED | REENTRY churn protection |
| `2023-03-03` | NEW vs REENTRY | NEW | 93180 raw score 0.239711, BQ REDUCED | REENTRY insufficient evidence |
| `2023-03-10` | NEW vs ADD | NEW | 94320 ADD raw score 0.197295 | BUY Quality blocks incremental ADD |
| `2023-04-11` | NEW vs REENTRY | NEW | 83060 score 0.240059; 93180 score 0.185198 | current evidence not requalified / prior context insufficient |
| `2023-06-20` | NEW vs ADD | NEW | 40520 ADD, BQ FULL, score 0.154782 | PC ADD target weight unchanged |
| `2023-07-03` | NEW vs REENTRY | NEW | multiple REENTRY rows present | current evidence / prior context gates |

Raw-score-only bypass screen:

- post-April raw-score comparable-or-stronger non-NEW rows vs funded NEW: `1,358`
- split: `1,350` REENTRY, `8` ADD

This count is not treated as valid suppressed-opportunity count. It proves the opposite: numerical cross-action ordering by raw score is unsafe because many funded NEW rows had low or negative raw score while REENTRY rows were still semantically ineligible.

`COMPARABLE_OR_STRONGER_NON_NEW_OPPORTUNITY_BYPASSED_COUNT = 0_CONFIRMED_BY_FULL_SEMANTIC_AUTHORITY; 1,358_RAW_SCORE_ONLY_SHADOW_CASES`

## Score Comparability

`NEW_REENTRY_SCORE_COMPARABLE = NO`

`NEW_ADD_SCORE_COMPARABLE = NO`

`REENTRY_ADD_SCORE_COMPARABLE = NO`

`CROSS_ACTION_RANKING_USES_INCOMPARABLE_SCORE = PARTIAL`

Explanation:

- `runtime_opportunity_score` is shared as ranking evidence, but not calibrated as expected return, yen value, or reentry recovery value.
- PC marginal-capital class/rank logic uses available score/rank evidence after action-specific eligibility and accepted-increment filtering.
- Because REENTRY and many ADD rows do not reach the same accepted-increment population, full cross-action ranking often never occurs.
- Where coarse ranking exists, it does not solve the common marginal-yen comparability gap.

## NEW Admission Burden

`NEW_MARGINAL_CAPITAL_AUTHORITY_LOWER_BURDEN = YES_STRUCTURALLY`

NEW receives capital after Candidate/BQ/PC/PS/lot/cash gates, without having to prove:

- prior exit context;
- churn recovery;
- renewed thesis after a failed prior campaign;
- current-position continuation;
- no-loss averaging;
- prior ADD history;
- positive incremental next-lot value beyond current exposure.

This is not automatically wrong. NEW genuinely represents new exposure and should not inherit held-position constraints. But the burden asymmetry materially contributes to the observed effective allocation.

## Winner Capture Decline

BUY fill follow-through after PIT populations were frozen:

| Period | Action | Entries | Notional | +3BD positive | +5BD positive | +10BD positive | +10BD material winner >=10k |
|---|---|---:|---:|---:|---:|---:|---:|
| Growth | BUY_NEW | 78 | 6,205,660 | 47.44% | 44.87% | 44.87% | 7.69% |
| Growth | BUY_ADD | 7 | 197,060 | 57.14% | 57.14% | 71.43% | 0.00% |
| Growth | REENTRY | 0 | 0 | n/a | n/a | n/a | n/a |
| Post-April | BUY_NEW | 156 | 15,870,240 | 42.00% | 41.50% | 38.13% | 8.63% |
| Post-April | BUY_ADD | 0 | 0 | n/a | n/a | n/a | n/a |
| Post-April | REENTRY | 0 | 0 | n/a | n/a | n/a | n/a |
| Plateau | BUY_NEW | 68 | 7,338,070 | 38.24% | 38.24% | 36.36% | 3.03% |

`POST_APRIL_WINNER_CAPTURE_RATE_DECLINED = YES`

`POST_APRIL_NEW_WINNER_CAPTURE_RATE = +10BD positive 38.13%; material >=10k 8.63%; Plateau material >=10k 3.03%`

`POST_APRIL_REENTRY_WINNER_CAPTURE_RATE = INSUFFICIENT_EXECUTED_SAMPLE_ZERO_FILLS`

`POST_APRIL_ADD_WINNER_CAPTURE_RATE = INSUFFICIENT_EXECUTED_SAMPLE_ZERO_FILLS`

`MARKET_FOLLOW_THROUGH_DECLINE_WITHIN_ACTION_TYPE = YES_FOR_BUY_NEW`

This prevents over-attribution to action bias: within the same BUY_NEW action type, follow-through weakened post-April and especially in the Plateau window.

## Candidate Selection vs Capital Selection

`CANDIDATE_SELECTION_WEAKNESS_SUPPORTED = YES_PARTIAL`

Evidence:

- BQ supply did not disappear, but post-April BUY_NEW follow-through weakened.
- Plateau BUY_NEW +10BD positive rate fell to `36.36%`, and +10BD material winner rate fell to `3.03%`.

`CAPITAL_SELECTION_WEAKNESS_SUPPORTED = YES_PARTIAL`

Evidence:

- NEW captured almost all incremental capital after April.
- REENTRY had 2,667 post-April PC rows and no selected/fill path.
- ADD had 96 PM observations but zero post-April fills.
- Cross-action score comparability is not sufficient to prove that selected NEW was economically superior to blocked REENTRY/ADD.

CI does not prove a clean final-stage "bad NEW beat valid REENTRY/ADD" defect. The stronger finding is an emergent action-type materialization asymmetry.

## Prior Ownership / Classification Correctness

Post-April BUY_NEW-like admissions by prior ownership context:

| Class | Count | Notional |
|---|---:|---:|
| never-owned NEW | 153 | 15,657,790 |
| previously owned but filled as BUY_NEW | 3 | 212,450 |

Across the full inspected run, five BUY_NEW fills occurred for symbols that already had prior SELL_EXIT history:

| Date | Symbol | PC same-day classification | PC REENTRY status | Fill type | Fill campaign |
|---|---|---|---|---|---|
| `2022-11-04` | `76470` | REENTRY target false | REVIEW_REQUIRED / insufficient prior context | BUY_NEW | `pc-51d4bf0a29ba7f1b-76470-0001` |
| `2022-12-26` | `94320` | REENTRY target false | REVIEW_REQUIRED / insufficient prior context | BUY_NEW | `pc-86b7ed8997105419-94320-0001` |
| `2023-04-19` | `94340` | REENTRY target false | REVIEW_REQUIRED / insufficient prior context | BUY_NEW | `pc-27c9cf3d2e387ac7-94340-0001` |
| `2023-05-15` | `76010` | REENTRY target false | REVIEW_REQUIRED / insufficient prior context | BUY_NEW | `pc-d69a4723920a56a9-76010-0001` |
| `2023-05-31` | `21340` | REENTRY target false | REVIEW_REQUIRED / insufficient prior context | BUY_NEW | `pc-b362959b1d74e740-21340-0001` |

Representative boundary, `2023-05-31 21340`:

```text
PC: semantic_buy_type=REENTRY, target_membership=false, prior exit=2023-05-17,
    REENTRY_INSUFFICIENT_EVIDENCE / insufficient_prior_exit_context
Runtime planning: rp-2023-05-31-21340-buy_new-... planning_intent=BUY_NEW, qty=2700
Fill: source_decision_type=BUY_NEW, qty=2700
```

`ACTION_CLASSIFICATION_CORRECTNESS_DEFECT_FOUND = YES`

This is not the main post-April plateau explanation by notional, but it is a concrete correctness concern: a same-symbol prior-ownership / REENTRY review state can coexist with a downstream BUY_NEW fill for that symbol.

`STARTER_LOOP_DOMINATED_BY_NEVER_OWNED_NEW = YES`

The post-April replacement loop is overwhelmingly genuinely never-owned NEW by count and notional. The three previously-owned-as-BUY_NEW post-April cases are correctness-significant but not the dominant capital mass.

## Root Cause Hierarchy

### Primary Action-Bias Root Cause

`EMERGENT_ORDERING_FROM_ACTION_SPECIFIC_GATES`

Observed effective ordering:

```text
NEW > ADD > REENTRY
```

with a caveat:

- ADD had Growth fills, but post-April ADD fell to zero because it rarely survived canonical ADD materialization.
- REENTRY had no fills in the inspected run and is the most gated path.
- NEW is not explicitly promoted, but it is the only action class consistently reaching executable capital after April.

### Secondary Causes

1. `REENTRY_FIRST_CLASS_MARGINAL_COMPETITOR_GAP`

   REENTRY is visible in PC artifacts, but never selected in the inspected run and is not handled as a first-class intent by `marginal_capital_value.candidate_intent`.

2. `REENTRY_PRIOR_CONTEXT_AND_CURRENT_REQUALIFICATION_BURDEN`

   Many long-lived positive-score prior-owned rows remain blocked by current evidence or prior-context insufficiency. This is partly legitimate fail-closed behavior, partly unresolved semantic burden.

3. `ADD_PM_TO_STRATEGY_PM_TO_PC_SUPPRESSION`

   Runtime PM ADD often becomes canonical Strategy HOLD. Canonical ADD rows then often carry zero incremental target.

4. `INCOMPARABLE_SCORE_DOMAINS`

   Raw score ordering across NEW / REENTRY / ADD is not a valid economic comparison.

5. `MARKET_FOLLOW_THROUGH_DECLINE`

   Even within BUY_NEW, post-April follow-through weakened. Action bias is not the only cause.

## Principle Judgment

`ACTION_NEUTRAL_MARGINAL_CAPITAL_PRINCIPLE_SATISFIED = PARTIAL`

Why not YES:

- REENTRY / ADD face additional materialization barriers before they can compete for the same yen.
- Scores are not common marginal-yen values.
- REENTRY has no actual capital wins.
- Some prior-owned symbols can be filled as BUY_NEW despite REENTRY review state.

Why not NO:

- no explicit NEW-first priority was found;
- BUY_NEW label alone and BUY_ADD label alone are explicitly not supposed to increase priority;
- many non-NEW rows are semantically ineligible, not proven valid opportunities.

## Repairability

`REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE = YES`

Recommended scope is still shadow/design, not Production:

- normalize REENTRY as a first-class PC marginal-capital competitor only after REENTRY semantic PASS;
- keep prior-exit and churn gates fail-closed;
- add read-only diagnostics for long-lived positive-score REENTRY rows;
- separate PM held-position strength from executable ADD consideration;
- add a same-symbol classification guard / audit for REENTRY-review rows that later materialize as BUY_NEW;
- keep PC as the owner of action-neutral marginal capital comparison.

`NEW_COMPONENT_REQUIRED = NO`

`NEW_MODEL_REQUIRED = NO`

`PRODUCTION_CHANGE_JUSTIFIED = NO`

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-08-22`
2. `NEW_REENTRY_ADD_DECISION_CONTRACT_COMPARISON = BUY_NEW has direct Candidate/BQ/PC/PS path; REENTRY adds prior-exit/churn/recovery gates; ADD adds PM/Strategy-PM/SI/target-increment/lot-cap gates before PS/Runtime`
3. `EXPLICIT_ACTION_TYPE_PRIORITY_FOUND = NO_FIXED_ACTION_ORDER_FOUND`
4. `IMPLICIT_ACTION_TYPE_BIAS_SUPPORTED = YES`
5. `GROWTH_NEW_OPPORTUNITY_TO_FILL_RATE = 78 / 1,243 = 6.28%`
6. `POST_APRIL_NEW_OPPORTUNITY_TO_FILL_RATE = 153 / 1,333 = 11.48%`
7. `GROWTH_REENTRY_OPPORTUNITY_TO_FILL_RATE = 0 / 1,210 = 0.00%`
8. `POST_APRIL_REENTRY_OPPORTUNITY_TO_FILL_RATE = 0 / 2,667 = 0.00%`
9. `GROWTH_ADD_OPPORTUNITY_TO_FILL_RATE = 7 / 58 canonical PC ADD rows = 12.07%; 7 / 74 PM ADD observations = 9.46%`
10. `POST_APRIL_ADD_OPPORTUNITY_TO_FILL_RATE = 0 / 9 canonical PC ADD rows = 0.00%; 0 / 96 PM ADD observations = 0.00%`
11. `ACTION_TYPE_CONDITIONAL_WIN_RATES = NEW vs REENTRY: NEW 58, REENTRY 0, cash/none 8, other 2; NEW vs ADD: NEW 25, ADD 2, cash/none 3; REENTRY vs ADD: REENTRY 0, ADD 2, cash/none 4, other 27`
12. `NEW_REENTRY_SCORE_COMPARABLE = NO`
13. `NEW_ADD_SCORE_COMPARABLE = NO`
14. `REENTRY_ADD_SCORE_COMPARABLE = NO`
15. `CROSS_ACTION_RANKING_USES_INCOMPARABLE_SCORE = PARTIAL`
16. `LONG_LIVED_PRIOR_OWNERSHIP_PENALTY_FOUND = PARTIAL_STRUCTURAL_GATING_FOUND_NOT_PROVEN_AS_INVALID_PENALTY`
17. `VALID_REENTRY_OPPORTUNITIES_SUPPRESSED_COUNT = 0_CONFIRMED_SEMANTIC_PASS_REENTRY; 241_LONG_LIVED_POSITIVE_SCORE_REENTRY_ROWS_REQUIRE_SHADOW_REVIEW`
18. `ADD_STRUCTURALLY_HARDER_TO_MATERIALIZE_THAN_NEW = YES`
19. `ADD_EXTRA_BURDEN_SEMANTICALLY_JUSTIFIED = PARTIAL`
20. `NEW_MARGINAL_CAPITAL_AUTHORITY_LOWER_BURDEN = YES_STRUCTURALLY`
21. `POST_APRIL_WINNER_CAPTURE_RATE_DECLINED = YES`
22. `POST_APRIL_NEW_WINNER_CAPTURE_RATE = +10BD positive 38.13%; material >=10k 8.63%; Plateau material >=10k 3.03%`
23. `POST_APRIL_REENTRY_WINNER_CAPTURE_RATE = INSUFFICIENT_EXECUTED_SAMPLE_ZERO_FILLS`
24. `POST_APRIL_ADD_WINNER_CAPTURE_RATE = INSUFFICIENT_EXECUTED_SAMPLE_ZERO_FILLS`
25. `CANDIDATE_SELECTION_WEAKNESS_SUPPORTED = YES_PARTIAL`
26. `CAPITAL_SELECTION_WEAKNESS_SUPPORTED = YES_PARTIAL`
27. `COMPARABLE_OR_STRONGER_NON_NEW_OPPORTUNITY_BYPASSED_COUNT = 0_CONFIRMED_BY_FULL_SEMANTIC_AUTHORITY; 1,358_RAW_SCORE_ONLY_SHADOW_CASES`
28. `STARTER_LOOP_DOMINATED_BY_NEVER_OWNED_NEW = YES`
29. `ACTION_CLASSIFICATION_CORRECTNESS_DEFECT_FOUND = YES`
30. `MARKET_FOLLOW_THROUGH_DECLINE_WITHIN_ACTION_TYPE = YES_FOR_BUY_NEW`
31. `ACTION_NEUTRAL_MARGINAL_CAPITAL_PRINCIPLE_SATISFIED = PARTIAL`
32. `OBSERVED_EFFECTIVE_ACTION_ORDERING = NEW > ADD > REENTRY`
33. `ORDERING_IS_EXPLICIT_OR_EMERGENT = EMERGENT_FROM_GATES`
34. `PRIMARY_ACTION_BIAS_ROOT_CAUSE = REENTRY_AND_ADD_ACTION_SPECIFIC_MATERIALIZATION_GATES_PREVENT_NON_NEW_FROM_REACHING_EXECUTABLE_CAPITAL`
35. `SECONDARY_ACTION_BIAS_CAUSES = REENTRY first-class competitor gap; prior-context/current-requalification burden; PM ADD to Strategy PM HOLD conversion; ADD target-weight zero; incomparable score domains; weaker post-April market follow-through`
36. `ACTION_BIAS_CONTRIBUTES_TO_POST_APRIL_PLATEAU = YES_PARTIAL`
37. `MARKET_REALITY_CONTRIBUTION = MATERIAL`
38. `REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE = YES`
39. `NEW_COMPONENT_REQUIRED = NO`
40. `NEW_MODEL_REQUIRED = NO`
41. `PRODUCTION_CHANGE_JUSTIFIED = NO`
42. `NEXT_RECOMMENDED_STEP = READ-ONLY/SHADOW first-class REENTRY and ADD consideration materialization audit inside existing PC-owned marginal-capital architecture, plus same-symbol BUY_NEW-vs-REENTRY classification guard evidence; no Production change.`
43. `FINAL_JUDGMENT = PHASE32_CI_IMPLICIT_ACTION_TYPE_BIAS_IDENTIFIED_EMERGENT_NEW_OVER_NON_NEW_FROM_REENTRY_AND_ADD_MATERIALIZATION_GATES_ACTION_CLASSIFICATION_CORRECTNESS_DEFECT_FOUND_SHADOW_FOLLOWUP_REQUIRED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

## Final Judgment

`PHASE32_CI_IMPLICIT_ACTION_TYPE_BIAS_IDENTIFIED_EMERGENT_NEW_OVER_NON_NEW_FROM_REENTRY_AND_ADD_MATERIALIZATION_GATES_ACTION_CLASSIFICATION_CORRECTNESS_DEFECT_FOUND_SHADOW_FOLLOWUP_REQUIRED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

