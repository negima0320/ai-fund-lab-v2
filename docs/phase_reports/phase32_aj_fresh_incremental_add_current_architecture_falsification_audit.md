# Phase32-AJ — Fresh Incremental ADD Current-Architecture Falsification Audit

## Scope

- Primary trusted run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted window: `2022-10-03` through `2023-10-10`
- Business days: `252`
- Mode: READ-ONLY falsification audit

No source, config, runtime state, Strategy parameter, threshold, weight, ADD tier, Cash policy, BQ, Risk Pacing, PC, PS, Runtime, fresh-run, resume, replay, recover, or long Historical action was modified or executed.

Forward outcome checks in this report are explicitly:

```text
POST_HOC_DIAGNOSTIC_ONLY
```

They were not used to select Production rules, thresholds, weights, or future Strategy parameters.

## References Read

- `docs/phase_reports/phase32_af_stuck_capital_new_add_cash_marginal_equivalence_audit.md`
- `docs/phase_reports/phase32_ag_add_zero_winner_root_cause_characterization.md`
- `docs/phase_reports/phase32_ah_add_intent_quality_pm_pc_materialization_root_cause_audit.md`
- `docs/phase_reports/phase32_ai_pm_add_signal_predictiveness_ai_evidence_characterization.md`
- current source for Runtime PM, Strategy PM, ADD investment evidence, PC, and PS
- current canonical run artifacts for the 19 strict HOLD fresh-strength candidates identified in Phase32-AI

## Executive Summary

Current architecture is not proven structurally incapable of representing/routing a genuine Fresh Incremental ADD Opportunity.

The 19 strict HOLD fresh-strength candidates are mostly persistent strength states, not proven refreshed incremental opportunities:

| Classification | Count |
| --- | ---: |
| `GENUINE_FRESH_INCREMENTAL_EVIDENCE` | `0` |
| `PLAUSIBLE_REFRESH` | `3` |
| `PERSISTENT_STRONG_STATE` | `14` |
| `RISK_OR_CAP_BLOCKED` | `2` |
| `INSUFFICIENT_EVIDENCE` | `0` |

Existing PIT artifacts can partially distinguish `strong today` from `stronger than recently` through opportunity rank, BQ action/band/score, SI entry action/state, momentum/acceleration/continuation evidence, relative strength, risk vote, current return, and prior ADD/campaign history. However, there is no single canonical authority contract that cleanly separates:

```text
HOLD_STRENGTH
ADD_CONSIDERATION
FRESH_INCREMENTAL_OPPORTUNITY
```

The demonstrated boundary issue is:

```text
SI/BQ/opportunity fresh-strength evidence can exist for a held symbol,
but if Strategy PM emits HOLD, PC never receives an ADD competitor.
```

This is a performance architecture concern and semantic-boundary gap, not a proven correctness defect and not proof that a new component is required.

Final falsification classification:

```text
HAS_CURRENT_ADD_ARCHITECTURE_BEEN_FALSIFIED: PARTIAL
```

Next-step gate:

```text
EXISTING_COMPONENT_SEMANTIC_REFACTOR_STUDY
```

## A — Required Capability

Momentum-style ADD requires a semantic distinction among:

| Semantic State | Meaning |
| --- | --- |
| `HOLD_STRENGTH` | The open campaign remains healthy enough to retain existing exposure. |
| `ADD_CONSIDERATION` | The held security is strong enough to be compared for additional capital. |
| `FRESH_INCREMENTAL_OPPORTUNITY` | Decision-time evidence shows a materially refreshed or strengthened opportunity that may justify another executable lot. |

Existing evidence can express pieces of `FRESH_INCREMENTAL_OPPORTUNITY`:

- acceleration / continuation state
- renewed or improving BQ action/band/score
- opportunity rank and rank improvement
- runtime opportunity score
- SI entry action/state such as `ADD_ALLOWED`, `ADD_REDUCED_ONLY`, `HEALTHY_CONTINUATION_ENTRY`
- relative strength / participation / trend health
- expected-edge compatibility
- recovery from deterioration
- no-loss state and current campaign return
- campaign age, prior ADD count, prior REDUCE context, exposure/headroom

But those pieces are distributed across existing components. Current artifacts do not expose one canonical final semantic saying: "this is a fresh incremental ADD opportunity, separate from persistent strong HOLD state."

## B — 19 HOLD Fresh-Strength Candidates

The 19 strict HOLD fresh-strength candidates were distributed as:

| Symbol | Count |
| --- | ---: |
| `54010` | `6` |
| `77760` | `5` |
| `21340` | `4` |
| `40520` | `2` |
| `43880` | `1` |
| `37780` | `1` |

All 19 shared the same first materialization result:

```text
PM action = HOLD
PC ADD competitor existed = NO
First boundary = PM_ACTION_HOLD_PREVENTS_PC_ADD_MATERIALIZATION
```

Per-row characterization:

| Date | Symbol | PM Action | SI Entry | BQ | Rank | Current Return | Prior / Change Evidence | PC ADD Competitor | Classification |
| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| `2023-02-02` | `77760` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+9.28%` | risk vote `3`; prior BQ improved from `BUY_WAIT` | `NO` | `RISK_OR_CAP_BLOCKED` |
| `2023-02-06` | `77760` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+7.12%` | BQ `BUY_WAIT -> FULL`; relative `MIXED -> SUPPORTIVE`; risk `3 -> 1` | `NO` | `PLAUSIBLE_REFRESH` |
| `2023-02-07` | `77760` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+10.32%` | strong continuation persisted | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-02-08` | `77760` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+13.77%` | decelerating but supportive continuation | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-02-09` | `77760` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+15.63%` | supportive persistence/trend/relative state | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-02-22` | `54010` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `3` | `+16.41%` | prior PM ADD streak; SI shifted `NO_ADD -> ADD_REDUCED` | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-02-27` | `54010` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `4` | `+16.19%` | continuation state persisted | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-03-01` | `54010` | `HOLD` | `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `3` | `+15.28%` | BQ `BUY_WAIT -> FULL`; SI `ADD_REDUCED -> ADD_ALLOWED` | `NO` | `PLAUSIBLE_REFRESH` |
| `2023-03-02` | `54010` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `4` | `+16.87%` | immediately after prior `ADD_ALLOWED` relaxed | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-03-03` | `54010` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+17.43%` | supportive but repeated state | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-03-06` | `54010` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+18.27%` | supportive persistence/trend continued | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-03-27` | `43880` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `2` | `+10.60%` | prior ADD/REDUCE/ADD alternation; not clean fresh evidence | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-06-12` | `21340` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `3` | `+22.73%` | prior repeated ADD state | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-06-14` | `21340` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `2` | `+32.00%` | high state persisted; no clean refresh | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-06-15` | `21340` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `2` | `+45.16%` | high state persisted | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-06-16` | `40520` | `HOLD` | `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+8.59%` | limited prior evidence in immediate lookback | `NO` | `PLAUSIBLE_REFRESH` |
| `2023-06-19` | `21340` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `2` | `+46.88%` | prior ADD on `2023-06-16`; repeated high state | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-06-19` | `40520` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `4` | `+25.37%` | prior `2023-06-16` `ADD_ALLOWED`; now reduced | `NO` | `PERSISTENT_STRONG_STATE` |
| `2023-07-05` | `37780` | `HOLD` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `5` | `+19.77%` | rank improved `6 -> 5`, but risk vote worsened `1 -> 3` | `NO` | `RISK_OR_CAP_BLOCKED` |

Answer:

```text
HOW_MANY_OF_THE_19_HOLD_FRESH_STRENGTH_CANDIDATES_ARE_GENUINE_REFRESHED_OPPORTUNITIES: 0
```

There are `3` plausible refresh rows, but none meet the stricter decision-time standard for genuine refreshed incremental opportunity.

## C — Temporal Change Reconstruction

For the 19 candidates, prior 1-5BD evidence showed that current artifacts can reconstruct some change:

- BQ transitions, for example `BUY_WAIT -> FULL_ALLOCATION_ELIGIBLE`
- SI transitions, for example `ADD_REDUCED_ONLY -> ADD_ALLOWED`
- rank movement, for example `6 -> 5`
- risk-vote movement, for example `3 -> 1` or `1 -> 3`
- acceleration/persistence/trend/relative-support state movement

However, most rows were repeated strong-state continuations with stable top ranks, high BQ, positive current returns, and supportive trend evidence.

Classification:

```text
CAN_EXISTING_PIT_EVIDENCE_REPRESENT_STRENGTH_CHANGE: YES_PARTIALLY
```

Reason:

Existing artifacts can distinguish some state changes, but the distinction is distributed and coarse. They do not provide a canonical "fresh incremental ADD opportunity" authority that is independent from persistent campaign strength.

## D — Existing Component Trace

### Candidate / Opportunity

Held symbols can be evaluated by existing candidate/opportunity logic. PC members for current positions can carry:

- `candidate_duplicate_reconciled:<symbol>`
- `current_position=true`
- `opportunity_buy_rank`
- `runtime_opportunity_score`
- opportunity rank authority payload

Representative actual artifact: `2023-03-01` `54010` was a current position with `pm_action=HOLD`, but still carried:

- BQ `FULL_ALLOCATION_ELIGIBLE / HIGH`
- `opportunity_buy_rank=3`
- `runtime_opportunity_score=0.07834583`
- SI `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY`
- selection-quality consumed evidence for rank, entry action, supportive dimensions, trend health, persistence, and participation

Conclusion:

```text
CAN_HELD_SECURITIES_BE_EVALUATED_BY_EXISTING_CANDIDATE_OPPORTUNITY_LOGIC: YES
```

### PM

Runtime PM ADD triggers include continuation/rank/no-loss/risk evidence:

- `strong_trend_continuation`: `add_score >= 0.72`
- `opportunity_rank_still_high`: `buy_rank <= 5`
- `no_loss_averaging`: `current_return > 0.0`
- `add_downside_risk_contained`: `downside < 0.50`

But current source also records that legacy ADD indicates strong continuation/rank/risk evidence while incremental investment value is not separately proven.

Strategy PM can convert ADD to HOLD when structured ADD worthiness is not PASS:

```text
action == ADD
-> structured_add_worthiness != PASS
-> action = HOLD
-> structured_add_worthiness_no_add
```

Structured ADD worthiness can fail on prior ADD count `>= 5`, prior REDUCE history, continuation quality, risk, or missing campaign identity.

For the 19 current AJ rows, PM output is already HOLD, so the useful SI/BQ/opportunity evidence is not materialized as PC ADD authority.

### Strategy Intelligence

SI recognizes states relevant to ADD consideration:

- `ADD_ALLOWED`
- `ADD_REDUCED_ONLY`
- `HEALTHY_CONTINUATION_ENTRY`
- `CONTINUATION_WITH_CAUTION`
- acceleration, persistence, trend, relative/supportive dimensions

But SI evidence is explicitly not action authority in the current contract. It can support consideration; it does not by itself create an ADD action.

### Buy Quality

BQ independently records quality action/band/score and can improve from `BUY_WAIT` to `FULL_ALLOCATION_ELIGIBLE / HIGH` for held names. BQ is therefore available as quality evidence for held securities, but it is not the canonical action authority for ADD.

### Portfolio Construction

PC can technically classify an ADD competitor when a member is both:

```text
current_position = true
pm_action = ADD
```

Unheld candidates become `NEW_BUY` when:

```text
current_position = false
membership_intent = ADD_CANDIDATE
```

Therefore PC can compare/deploy ADD only after PM/SI upstream state materializes as `pm_action=ADD`. If PM emits HOLD, PC treats the member as retain/baseline, not incremental capital competition.

### Position Sizing

PS can size positive BUY_ADD when existing position plus `pm_action=ADD` reaches it, and it consumes PC discrete executable quantity authority or one-lot authority. When existing position plus HOLD reaches PS, baseline is preserved with no transaction delta.

## E — Information Loss / Authority Gap Map

For all 19 AJ candidates:

```text
Candidate/Opportunity evidence: preserved enough for rank/score
Strategy Intelligence evidence: preserved enough for ADD consideration state
BQ evidence: preserved
PM action: HOLD
PC ADD competitor: absent
PS ADD sizing: not reached
```

First observed boundary:

```text
PM_ACTION_HOLD_PREVENTS_PC_ADD_MATERIALIZATION
```

Interpreted strictly:

- The first actual routing boundary is PM action materialization.
- The deeper semantic issue is PM/SI action-authority separation: SI/BQ can describe ADD-like quality or consideration while Strategy PM remains HOLD.
- PC is not the first bad boundary for these 19 rows because PC never receives ADD authority.

## F — Existing Architecture Sufficiency Hypotheses

| Hypothesis | Evidence For | Evidence Against | Classification |
| --- | --- | --- | --- |
| H0 Current architecture is sufficient | Held symbols carry opportunity/BQ/SI evidence; PM/PC/PS can route ADD when `pm_action=ADD`; no genuine fresh case was proven among 19. | No canonical tri-state semantics; PM/SI split can leave plausible refresh as HOLD. | `PARTIALLY_SUPPORTED` |
| H1 PM semantic gap | PM ADD is mostly state strength in AI; PM can output HOLD despite SI `ADD_ALLOWED`; source says incremental value is not separately proven. | Among the 19, no genuine fresh opportunity was proven; PM may be correctly conservative. | `SUPPORTED_AS_PERFORMANCE_ARCHITECTURE_CONCERN` |
| H2 Bridge / propagation gap | SI/BQ ADD-like evidence does not reach PC as ADD if PM action is HOLD. | When PM emits ADD and SI allows it, PC and PS can process ADD. | `SUPPORTED_NARROWLY` |
| H3 PC authority gap | AF/AG found marginal-capital semantic gaps and downstream compression. | AJ's 19 rows never reach PC as ADD; PC is not first boundary here. | `NOT_FIRST_BOUNDARY_FOR_AJ` |
| H4 Evidence gap | Existing PIT evidence is partial and distributed; 0/19 genuine fresh confirmed. | SI/BQ/rank trajectories do carry some state-change evidence. | `PARTIALLY_SUPPORTED` |
| H5 Opportunity scarcity | Only 3 plausible refresh rows; most candidates were persistent state or risk/cap blocked. | The 19 strict rows show some ADD-like evidence exists, so scarcity alone is not fully proven. | `SUPPORTED_BUT_NOT_EXCLUSIVE` |

## G — Held vs Unheld Opportunity Symmetry

The user question:

```text
Is NEW vs ADD fundamentally the same security opportunity, with action type mainly determined by whether the security is already held?
```

Characterization:

| Evidence Dimension | Classification |
| --- | --- |
| candidate/opportunity rank | `COMMON_SECURITY_OPPORTUNITY` |
| runtime opportunity score | `COMMON_SECURITY_OPPORTUNITY` |
| BQ score/band/action | `COMMON_SECURITY_OPPORTUNITY` |
| market/regime/liquidity/execution feasibility | `COMMON_SECURITY_OPPORTUNITY` |
| momentum trajectory, trend health, relative strength, participation | `COMMON_SECURITY_OPPORTUNITY` |
| expected-edge evidence in broad security sense | `COMMON_SECURITY_OPPORTUNITY` |
| current position quantity/weight/headroom | `HOLDING_SPECIFIC_INCREMENTAL_EVIDENCE` |
| average cost, current return, no-loss averaging | `HOLDING_SPECIFIC_INCREMENTAL_EVIDENCE` |
| campaign id, campaign age, campaign health | `HOLDING_SPECIFIC_INCREMENTAL_EVIDENCE` |
| prior ADD / REDUCE history | `HOLDING_SPECIFIC_INCREMENTAL_EVIDENCE` |
| MFE/giveback/profit protection state | `HOLDING_SPECIFIC_INCREMENTAL_EVIDENCE` |
| incremental expected edge vs existing exposure baseline | `HOLDING_SPECIFIC_INCREMENTAL_EVIDENCE` |
| opportunity cost of next lot vs NEW candidates | `HOLDING_SPECIFIC_INCREMENTAL_EVIDENCE` |
| downside risk / concentration / safety cap for existing position | `POSITION_RISK_ONLY` |
| PM action ADD/HOLD | `ACTION_SPECIFIC_IMPLEMENTATION_ARTIFACT` |
| PC competitor type `ADD` / `NEW_BUY` | `ACTION_SPECIFIC_IMPLEMENTATION_ARTIFACT` |
| PC membership intent `RETAIN` / `ADD_CANDIDATE` | `ACTION_SPECIFIC_IMPLEMENTATION_ARTIFACT` |

Answer:

NEW and ADD share a large common security-opportunity substrate. ADD is not merely NEW with `already_held=true`, because ADD also requires holding-specific incremental evidence: current exposure, no-loss state, campaign identity/age, prior add history, risk cap, and next-lot opportunity cost.

## H — New Component Necessity Test

Classification:

```text
EXISTING_COMPONENT_REFACTOR_LIKELY_SUFFICIENT
```

New component necessity is not proven.

Reason:

- Existing Candidate/Opportunity, SI, BQ, PM, PC, and PS already hold most required evidence.
- Existing PC/PS can route and size ADD when upstream `pm_action=ADD` exists.
- The 19 strict candidates do not prove actual missed genuine fresh incremental opportunity.
- The missing capability appears to be a canonical semantic boundary/propagation contract, not a whole new authority owner.
- Adding a new component now would risk duplicating Candidate/Opportunity, PM, SI, or PC responsibility without proof that current owners cannot represent the needed concept.

Answer:

```text
IS_A_NEW_COMPONENT_NECESSARY: NO
```

## I — Prior ADD History Gate Re-evaluation

Classification:

```text
SAFEGUARD_BEHAVIOR_JUSTIFIED
```

with caveat:

```text
POSSIBLE_LONG_LIVED_VETO: NOT_PROVEN
```

Evidence:

- Phase32-AH found the repeated `76470` post-limit cases were blocked by `prior_add_history_limits_incremental_add`.
- In the AJ 19 strict HOLD candidates, no row met the standard for genuine refreshed incremental opportunity.
- Most cases after limiting conditions were persistent strong state, not clean renewal.
- The gate therefore behaves as a legitimate exposure/churn safeguard on available decision-time evidence.

This does not prove the `>=5` rule is globally optimal. It only means the current evidence does not prove it blocked a genuine refreshed opportunity.

## J — Decision-Time Counterfactual Routing Audit

For the 3 `PLAUSIBLE_REFRESH` rows:

| Date | Symbol | Current Evidence | Could PM express? | Could SI authorize consideration? | Could PC receive? | Could PS size? | Missing Semantic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `2023-02-06` | `77760` | BQ and risk improvement with top-5 rank | Technically yes, if action authority accepted refreshed evidence | Yes, `ADD_REDUCED_ONLY` | Only if `pm_action=ADD` | Yes, if PC/PM emits executable increment | canonical bridge from refresh evidence to ADD consideration/action |
| `2023-03-01` | `54010` | BQ `BUY_WAIT -> FULL`; SI `ADD_ALLOWED`; rank `3` | Technically yes | Yes, strongest of 3 | Only if `pm_action=ADD` | Yes, if PC/PM emits executable increment | PM/SI action-authority bridge |
| `2023-06-16` | `40520` | SI `ADD_ALLOWED`; BQ HIGH; limited immediate prior evidence | Technically yes, evidence weaker due prior gap | Yes | Only if `pm_action=ADD` | Yes, if PC/PM emits executable increment | freshness standard and materialization contract |

This is a structural counterfactual only. No profit simulation or threshold proposal was performed.

## K — POST_HOC_DIAGNOSTIC_ONLY

These outcomes were computed only after decision-time classifications were frozen.

| Class | n | +5BD Mean | +5BD Median | +5BD Positive Rate | +20BD Mean | +20BD Median | +20BD Positive Rate | MFE20 Mean | MFE20 Median | MAE20 Mean | MAE20 Median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `PLAUSIBLE_REFRESH` | `3` | `+2.18%` | `+3.62%` | `66.7%` | `+5.79%` | `-3.00%` | `33.3%` | `+21.94%` | `+18.42%` | `-6.85%` | `-7.16%` |
| `PERSISTENT_STRONG_STATE` | `14` | `+1.46%` | `+0.73%` | `57.1%` | `-4.49%` | `-3.15%` | `35.7%` | `+18.32%` | `+7.33%` | `-16.25%` | `-11.71%` |
| `RISK_OR_CAP_BLOCKED` | `2` | `+0.82%` | `+0.82%` | `50.0%` | `-1.76%` | `-1.76%` | `50.0%` | `+23.03%` | `+23.03%` | `-16.22%` | `-16.22%` |

Interpretation:

The categories are behaviorally plausible but far too small and post-hoc to justify Production decisions. They do not change the decision-time finding that genuine fresh incremental opportunity was not proven among the 19 candidates.

## L — Current Design Falsification Standard

Answer:

```text
HAS_CURRENT_ADD_ARCHITECTURE_BEEN_FALSIFIED: PARTIAL
```

Exact proven insufficient boundary:

```text
PM/SI action-authority boundary:
held-symbol SI/BQ/opportunity ADD-like or plausible refresh evidence can remain PM HOLD,
therefore PC receives RETAIN/HOLD and no ADD competitor is materialized.
```

Why not `YES`:

- No genuine refreshed incremental opportunity was proven among the 19 strict candidates.
- Existing components already capture much of the relevant PIT evidence.
- Existing PC/PS can route ADD when PM emits ADD authority.
- New component necessity is not proven.

Why not `NO`:

- The architecture does not currently expose a clean canonical semantic contract separating HOLD strength, ADD consideration, and fresh incremental opportunity.
- The first actual routing boundary for the 19 rows is PM action materialization before PC.

## Required Final Answers

1. `HOW_MANY_OF_THE_19_HOLD_FRESH_STRENGTH_CANDIDATES_ARE_GENUINE_REFRESHED_OPPORTUNITIES`

```text
0
```

There are `3` `PLAUSIBLE_REFRESH` rows, but no row met the stricter genuine refreshed incremental opportunity standard using only decision-time evidence.

2. `CAN_EXISTING_PIT_EVIDENCE_DISTINGUISH_STATE_FROM_CHANGE`

```text
YES_PARTIALLY
```

3. `WHICH_COMPONENT_FIRST_LOSES_OR_FAILS_TO_USE_FRESH_STRENGTH_EVIDENCE`

```text
PM action materialization / PM-SI action-authority boundary
```

For the 19 AJ rows, PM emits HOLD, so PC never receives ADD competitor authority.

4. `CAN_HELD_SECURITIES_BE_EVALUATED_BY_EXISTING_CANDIDATE_OPPORTUNITY_LOGIC`

```text
YES
```

5. `WHAT_EVIDENCE_IS_COMMON_BETWEEN_NEW_AND_ADD`

```text
candidate/opportunity rank, runtime opportunity score, BQ score/band/action,
momentum/trajectory, trend health, relative strength, participation,
market/regime/liquidity/execution feasibility, broad expected-edge evidence
```

6. `WHAT_EVIDENCE_IS_LEGITIMATELY_ADD_SPECIFIC`

```text
current quantity/weight/headroom, average cost, current return/no-loss,
campaign id/age/health, prior ADD/REDUCE history, MFE/giveback/profit protection,
incremental next-lot value vs existing exposure, opportunity cost vs NEW,
existing-position risk/concentration/safety cap
```

7. `IS_PM_THE_FIRST_BAD_BOUNDARY`

```text
YES_FOR_THE_19_AJ_ROWS_AS_ROUTING_BOUNDARY
```

Strictly, the first observed routing boundary is PM action = HOLD. Semantically, this is a PM/SI action-authority boundary, not a standalone proof that PM must be redesigned.

8. `IS_STRATEGY_INTELLIGENCE_THE_FIRST_BAD_BOUNDARY`

```text
NO_AS_SOLE_BOUNDARY
```

SI preserves ADD consideration evidence and marks it non-action-authoritative. The issue is the boundary between SI evidence and PM action authority.

9. `IS_PC_THE_FIRST_BAD_BOUNDARY`

```text
NO
```

PC never receives ADD authority for the 19 AJ rows.

10. `IS_EXISTING_ARCHITECTURE_SUFFICIENT_WITH_SEMANTIC_REFACTORING`

```text
LIKELY_YES
```

Existing components appear to hold the necessary evidence, but the semantic contract needs clarification.

11. `IS_A_NEW_COMPONENT_NECESSARY`

```text
NO
```

Necessity is not proven.

12. `IS_PRIOR_ADD_HISTORY_A_SAFEGUARD_OR_LONG_LIVED_VETO`

```text
SAFEGUARD_BEHAVIOR_JUSTIFIED; LONG_LIVED_VETO_NOT_PROVEN
```

13. `HAS_CURRENT_ADD_ARCHITECTURE_BEEN_FALSIFIED`

```text
PARTIAL
```

14. `WHAT_EXACT_BOUNDARY_IS_PROVEN_INSUFFICIENT`

```text
The PM/SI action-authority boundary for held symbols with ADD-like SI/BQ/opportunity evidence
that remain PM HOLD and therefore never materialize as PC ADD competitors.
```

15. `WHAT_SHOULD_THE_NEXT_PHASE_STUDY`

```text
EXISTING_COMPONENT_SEMANTIC_REFACTOR_STUDY
```

## Proven Defect / Performance Concern / Unproven Hypothesis

| Type | Judgment |
| --- | --- |
| Proven correctness defect | `NONE_CONFIRMED_IN_AJ` |
| Performance architecture concern | `CONFIRMED`: existing evidence is distributed and PM/SI/PC semantics do not cleanly expose fresh incremental ADD opportunity. |
| Unproven hypothesis | New component necessity, PC as first bad boundary for the 19 rows, prior ADD gate blocking genuine refresh, and existence of genuine missed fresh incremental opportunities among the 19. |

## Next-Step Gate

Choose exactly one:

```text
EXISTING_COMPONENT_SEMANTIC_REFACTOR_STUDY
```

Recommended study boundary:

- clarify the semantic contract among `HOLD_STRENGTH`, `ADD_CONSIDERATION`, and `FRESH_INCREMENTAL_OPPORTUNITY`
- study how existing PM/SI/BQ/opportunity evidence should be interpreted by existing authority owners
- avoid adding a new component unless a later study proves current authority owners cannot carry the contract

No implementation is recommended in AJ.

## Final Judgment

```text
PHASE32_AJ_CURRENT_ADD_ARCHITECTURE_PARTIALLY_FALSIFIED_EXISTING_COMPONENT_SEMANTIC_REFACTOR_STUDY_REQUIRED
```

Current architecture is not fully falsified. The actual-path insufficiency is narrow and located at the PM/SI action-authority boundary before PC ADD materialization. Existing components appear capable enough to justify semantic refactoring study before any new component or broader redesign is considered.
