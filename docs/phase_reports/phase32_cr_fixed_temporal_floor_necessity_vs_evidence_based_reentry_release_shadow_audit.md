# Phase32-CR — Fixed Temporal Floor Necessity vs Evidence-Based REENTRY Release SHADOW Audit

## Scope

This is a READ-ONLY / SHADOW audit of whether REENTRY NEW-equivalent release requires a fixed elapsed-time floor such as CQ's `>60BD`, or whether active churn plus current PIT requalification evidence is sufficient.

- Primary evidence run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Latest completed date used: `2023-09-22`
- Evidence window: `2022-10-03` through `2023-09-22`
- Population inherited from CM/CN/CP/CQ: 5,376 REENTRY rows and 267 REENTRY episodes.

The primary run is pre-CO. Prior EXIT semantics were interpreted under the Phase32-CN strict-prior SHADOW reconstruction principle where old PC artifacts collapse scalar reason to generic `EXIT`. Old artifacts were not rewritten.

No Production code, config, Strategy semantics, thresholds, cooldowns, models, features, PC/PS, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run was changed or executed.

## Compared Designs

`DESIGN_F_CONTRACT`:

CQ fixed-floor contract:

```text
active churn/cooldown pass
+ business_days_since_exit > 60
+ renewed PIT evidence
-> REENTRY_NEW_EQUIVALENT_ELIGIBLE
```

This is conservative and blocks most near-term false resets, but it may suppress genuinely renewed opportunities before 60BD.

`DESIGN_E_CONTRACT`:

Evidence-based release after churn:

```text
active churn/cooldown pass
+ renewed independent PIT opportunity proven
-> REENTRY_NEW_EQUIVALENT_ELIGIBLE
```

Elapsed time remains evidence, but no extra `>60BD` hard gate exists.

## Existing Time Controls

`EXISTING_TIME_CONTROLS_COMPLETE = YES`

Current source time controls are:

- `portfolio_construction.REENTRY_COOLDOWN_BUSINESS_DAYS = 3`;
- `_semantic_reentry_evidence` computes `business_days_since_exit`;
- `reentry_cooldown_status = PASS` when `days_since_exit >= 3`, otherwise `FAIL_CLOSED`;
- `_canonical_reentry_semantic_eligibility` maps non-PASS cooldown to `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION`;
- there is no additional max-age, stale-prior-campaign boundary, or independent temporal relevance lifecycle;
- current PM has separate cooldown rules for existing-position ADD/reduce style flows, but the PC REENTRY semantic gate uses the 3BD constant above.

The current 3BD cooldown provides mandatory immediate-churn protection. It does not by itself prove that a 4-10BD opportunity is an independent new thesis rather than a fast rebound of the same failed setup.

## Current Requalification Evidence

`CURRENT_REQUALIFICATION_EVIDENCE_CONTRACT`:

Current REENTRY recovery uses:

- strict-prior prior EXIT identity and prior EXIT reason class;
- rank/current opportunity quality, currently with a REENTRY-specific `rank <= 10` recovery condition;
- BQ action;
- Corporate Action authority;
- liquidity/capacity;
- Entry Admission state/action/sufficiency;
- Continuation Quality;
- downside risk;
- trend recovery;
- momentum recovery;
- prior same-symbol exit count / repeated unresolved churn;
- reason-specific requirements for `TREND_MOMENTUM`, `HARD_STOP`, `CORPORATE_ACTION`, `PORTFOLIO_COMPETITION`, and `REVERSAL`;
- cooldown/churn status.

## Root Cause Of Existing Release Failure

`CURRENT_REQUALIFICATION_RELEASE_FAILURE_ROOT_CAUSE = MIXED`

The failure is not simply "rank blocks most cases." The current design has three interacting problems:

1. Pre-CO artifacts collapse authoritative prior EXIT semantics into scalar `EXIT`, which CN/CO addressed as a provenance problem.
2. Once a symbol has strict-prior ownership, current source keeps it permanently in a stricter REENTRY branch.
3. The REENTRY branch uses a rank/requalification hurdle as an extra recovery gate, even when renewed PIT evidence would make the symbol comparable to a current NEW opportunity.

Rank remains semantically valid as current opportunity evidence and capital-competition input. It becomes semantically invalid when used as a permanent REENTRY-only penalty after current PIT evidence already proves the old weakness is resolved.

## Design E Reclassification

Design E was applied to all post-churn REENTRY episodes by removing only CQ's fixed `>60BD` precondition. All other safety checks stayed intact:

- non-generic prior EXIT context required;
- no active churn/cooldown;
- no CA / broker / safety / Entry Admission / CQ / downside block;
- BQ eligible;
- `TREND_MOMENTUM` requires rank support plus trend and momentum recovery;
- `HARD_STOP` remains stricter and does not release without strong new thesis evidence;
- generic/missing prior context remains constrained.

Result:

| Design | Eligible episodes |
| --- | ---: |
| Design F: fixed `>60BD` + evidence | 14 |
| Design E: evidence after churn | 26 |
| Incremental Design E cases | 12 |

`POST_CHURN_EVIDENCE_ONLY_ELIGIBLE_COUNT = 26`

`DESIGN_F_ELIGIBLE_COUNT = 14`

`DESIGN_E_ELIGIBLE_COUNT = 26`

`DESIGN_E_INCREMENTAL_CASE_COUNT = 12`

## Evidence-Only Eligible By Age

`EVIDENCE_ONLY_ELIGIBLE_BY_AGE_BUCKET`:

| Age bucket | Design E eligible episodes |
| --- | ---: |
| 4-10BD | 5 |
| 11-20BD | 5 |
| 21-40BD | 5 |
| 41-60BD | 0 |
| 61-120BD | 8 |
| >120BD | 3 |

No active-churn 0-3BD case escaped.

## Pre-60BD Positive Cases

Design E finds 15 pre-60BD eligible episodes:

| Bucket | Count | CR classification |
| --- | ---: | --- |
| 4-10BD | 5 | `FALSE_RESET_RISK` |
| 11-20BD | 5 | `PLAUSIBLE_BUT_TRANSITIONAL` |
| 21-40BD | 5 | `HIGH_CONFIDENCE_INDEPENDENT_OPPORTUNITY` |

Representative pre-60 evidence-only cases:

| Date | Symbol | BD | Prior class | Rank | Trend | Momentum | BQ | CR classification |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| 2023-03-08 | 47720 | 4 | `TREND_MOMENTUM` | 20 | 1.037528 | 0.314685 | `REDUCED_ALLOCATION_ONLY` | false-reset risk |
| 2023-05-30 | 21340 | 8 | `TREND_MOMENTUM` | 10 | 1.880342 | 1.000000 | `REDUCED_ALLOCATION_ONLY` | false-reset risk despite strong current evidence |
| 2023-04-12 | 45980 | 14 | `TREND_MOMENTUM` | 20 | 1.146004 | 0.222128 | `REDUCED_ALLOCATION_ONLY` | plausible transitional |
| 2023-02-17 | 76470 | 17 | `TREND_MOMENTUM` | 20 | 1.046512 | 0.038462 | `REDUCED_ALLOCATION_ONLY` | plausible transitional |
| 2023-03-07 | 71380 | 25 | `TREND_MOMENTUM` | 18 | 1.778806 | 0.994633 | `REDUCED_ALLOCATION_ONLY` | high-confidence independent |
| 2023-06-05 | 44920 | 35 | `TREND_MOMENTUM` | 17 | 1.923874 | 1.477220 | `REDUCED_ALLOCATION_ONLY` | high-confidence independent |

`PRE60_HIGH_CONFIDENCE_INDEPENDENT_COUNT = 5`

## Negative Controls

Naive Design E, with all CQ safety controls except the `>60BD` floor, produced:

| Control | Escape count |
| --- | ---: |
| Active churn / cooldown | 0 |
| Weak current opportunity | 0 |
| HARD_STOP false release | 0 |

However, CR classifies the 5 eligible 4-10BD cases as same-thesis / false-reset risk because current evidence can be strong while the prior campaign is still too temporally close to confidently declare a genuinely independent opportunity.

`ACTIVE_CHURN_ESCAPE_COUNT = 0`

`UNRESOLVED_THESIS_ESCAPE_COUNT = 5_POTENTIAL_FALSE_RESET_RISK_CASES_IN_4_10BD`

`WEAK_OPPORTUNITY_ESCAPE_COUNT = 0`

`HARD_STOP_FALSE_RELEASE_COUNT = 0`

## Does Fixed 60BD Add Independent Safety?

`FIXED_60BD_ADDS_INDEPENDENT_SAFETY = PARTIAL_BUT_OVERBROAD`

The 60BD floor contributes real safety by blocking near-term same-thesis rebounds that are not fully captured by current rank/trend/momentum evidence, especially 4-10BD cases. But it is overbroad because it also blocks 21-40BD cases with strong, multi-signal renewed PIT evidence and no active churn.

The audit therefore does not support removing all temporal gating after 3BD. It also does not support hard-coding `>60BD` as semantically necessary.

## Same-Thesis Continuity Detection

`SAME_THESIS_CONTINUITY_DETECTABLE_WITH_EXISTING_PIT = PARTIAL`

Existing PIT evidence can identify many unresolved-thesis cases through:

- trend recovery failure;
- momentum recovery failure;
- weak rank/current opportunity;
- BQ rejection;
- Entry Admission blocks;
- continuation/downside status;
- repeated same-symbol churn count;
- generic/missing prior context.

But existing fields do not fully prove independence for very near-term 4-10BD rebounds. Time still carries independent semantic information there: the old campaign may simply be oscillating around the same failed trend.

## Preferred Role Of Elapsed Time

`PREFERRED_ROLE_OF_ELAPSED_TIME = ROLE_B_SUPPORTING_EVIDENCE_WITH_SHORT_HARD_CHURN_FLOOR`

Elapsed time should not be a long blunt hard gate such as `>60BD`. It should:

- remain a hard gate only for immediate churn / very-near-term same-thesis risk;
- become supporting confidence evidence after the short churn window;
- not permanently constrain a symbol once current PIT evidence proves an independent opportunity.

## HARD_STOP And Generic Context

`HARD_STOP_TEMPORAL_REQUIREMENT = BOTH_STRONGER_EVIDENCE_AND_EXTRA_TEMPORAL_CAUTION_REQUIRED; INSUFFICIENT_EVIDENCE_FOR_GENERAL_RELEASE`

HARD_STOP should not inherit the trend/momentum release rule. It requires stronger new-thesis proof, and the current CR evidence produced no HARD_STOP release.

`GENERIC_CONTEXT_EVIDENCE_ONLY_RELEASE_SUPPORTED = NO`

Generic or missing prior EXIT context remains constrained. CR does not fabricate semantic authority from current evidence alone.

## Design F vs Design E Safety Comparison

`DESIGN_F_VS_E_SAFETY_COMPARISON`:

| Dimension | Design F: fixed `>60BD` + evidence | Design E: evidence after churn |
| --- | --- | --- |
| Immediate churn protection | PASS | PASS |
| Weak stale symbol protection | PASS | PASS |
| HARD_STOP false release | PASS | PASS |
| 4-10BD same-thesis risk | Strong protection | Risk: 5 false-reset-risk cases |
| 21-40BD renewed opportunity suppression | Over-suppresses | Releases 5 high-confidence cases |
| Permanent-penalty avoidance | Partial | Better |
| Architecture simplicity | Simple but blunt | More semantically aligned but needs precise near-term guard |
| Explainability | Easy but arbitrary at 60BD | Better if expressed as churn floor + evidence + elapsed-time confidence |

## Production Philosophy

`PREFERRED_PRODUCTION_REENTRY_RELEASE_PHILOSOPHY = FIXED_FLOOR_PLUS_EVIDENCE_REQUIRED`

Important qualification:

CR does not validate CQ's `>60BD` as the correct fixed floor. It validates that some short temporal floor beyond the current 3BD cooldown is semantically useful because current PIT evidence alone releases 4-10BD cases that are not high-confidence independent opportunities.

The preferred Production philosophy is therefore:

```text
permanent lineage
+ non-permanent penalty
+ immediate/near-term churn floor
+ evidence-based release after that floor
+ elapsed time as supporting confidence, not permanent punishment
```

The exact future floor must be justified by churn / thesis-continuity semantics and focused negative controls, not by PnL optimization.

## Narrowest Future Implementation Change

`NARROWEST_FUTURE_IMPLEMENTATION_CHANGE`:

Modify the existing Portfolio Construction REENTRY lifecycle only:

- extend `_canonical_reentry_semantic_eligibility` with an explicit lifecycle state;
- keep `_reentry_recovery_evidence` as the source of renewed PIT evidence;
- add a near-term thesis-continuity guard before `REENTRY_NEW_EQUIVALENT_ELIGIBLE`;
- remove the permanent REENTRY-only rank penalty after lifecycle release;
- materialize NEW-equivalent capital treatment downstream without relabeling to BUY_NEW;
- preserve generic/missing fail-closed and HARD_STOP stricter requirements.

No standalone service/module is needed.

## Outcome Usage

No later performance, future return, future regime, MFE/MAE, campaign outcome, selected/bought outcome, or threshold sweep was used to choose the time rule. Optional outcome diagnostics were not needed for this CR conclusion.

`OUTCOME_DATA_USED_TO_CHOOSE_TIME_RULE = NO`

`OUTCOME_DIAGNOSTIC_CHANGED_CONTRACT = NO`

## Production Decision

`PRODUCTION_CHANGE_JUSTIFIED = MORE_SHADOW_EVIDENCE_REQUIRED_FOR_EXACT_FLOOR; YES_FOR_REJECTING_PERMANENT_PENALTY_AND_YES_FOR_REJECTING_UNQUALIFIED_60BD_AS_SEMANTICALLY_NECESSARY`

CR supports a future Production change away from permanent REENTRY penalty, but not immediate implementation of a pure evidence-after-3BD release. The next step should refine the near-term thesis-continuity floor/guard in SHADOW.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-09-22`
2. `DESIGN_F_CONTRACT`: active churn pass + `business_days_since_exit > 60` + renewed PIT evidence -> NEW-equivalent eligible.
3. `DESIGN_E_CONTRACT`: active churn/cooldown pass + renewed independent PIT opportunity proven -> NEW-equivalent eligible, with no extra 60BD hard gate.
4. `EXISTING_TIME_CONTROLS_COMPLETE`: `YES`
5. `CURRENT_REQUALIFICATION_EVIDENCE_CONTRACT`: prior EXIT context/class, cooldown, rank/current opportunity, BQ, trend, momentum, Entry Admission, CQ, downside, CA, broker/safety/capacity, repeated churn, reason-specific recovery.
6. `CURRENT_REQUALIFICATION_RELEASE_FAILURE_ROOT_CAUSE`: `MIXED`
7. `POST_CHURN_EVIDENCE_ONLY_ELIGIBLE_COUNT`: `26`
8. `EVIDENCE_ONLY_ELIGIBLE_BY_AGE_BUCKET`: `4-10BD=5; 11-20BD=5; 21-40BD=5; 41-60BD=0; 61-120BD=8; >120BD=3`
9. `PRE60_HIGH_CONFIDENCE_INDEPENDENT_COUNT`: `5`
10. `ACTIVE_CHURN_ESCAPE_COUNT`: `0`
11. `UNRESOLVED_THESIS_ESCAPE_COUNT`: `5_POTENTIAL_FALSE_RESET_RISK_CASES_IN_4_10BD`
12. `WEAK_OPPORTUNITY_ESCAPE_COUNT`: `0`
13. `HARD_STOP_FALSE_RELEASE_COUNT`: `0`
14. `FIXED_60BD_ADDS_INDEPENDENT_SAFETY`: `PARTIAL_BUT_OVERBROAD`
15. `SAME_THESIS_CONTINUITY_DETECTABLE_WITH_EXISTING_PIT`: `PARTIAL`
16. `PREFERRED_ROLE_OF_ELAPSED_TIME`: `SUPPORTING_EVIDENCE_WITH_SHORT_HARD_CHURN_FLOOR`
17. `HARD_STOP_TEMPORAL_REQUIREMENT`: `BOTH_STRONGER_EVIDENCE_AND_EXTRA_TEMPORAL_CAUTION_REQUIRED`
18. `GENERIC_CONTEXT_EVIDENCE_ONLY_RELEASE_SUPPORTED`: `NO`
19. `DESIGN_F_VS_E_SAFETY_COMPARISON`: Design F is safer but overbroad; naive Design E avoids permanent penalty but releases 5 near-term false-reset-risk cases.
20. `DESIGN_F_ELIGIBLE_COUNT`: `14`
21. `DESIGN_E_ELIGIBLE_COUNT`: `26`
22. `DESIGN_E_INCREMENTAL_CASE_COUNT`: `12`
23. `OUTCOME_DATA_USED_TO_CHOOSE_TIME_RULE`: `NO`
24. `OUTCOME_DIAGNOSTIC_CHANGED_CONTRACT`: `NO`
25. `PREFERRED_PRODUCTION_REENTRY_RELEASE_PHILOSOPHY`: `FIXED_FLOOR_PLUS_EVIDENCE_REQUIRED`, but not necessarily CQ's `>60BD`.
26. `NARROWEST_FUTURE_IMPLEMENTATION_CHANGE`: existing PC REENTRY semantic eligibility/recovery/capital-treatment materialization; add near-term thesis-continuity guard and lifecycle release.
27. `NEW_COMPONENT_REQUIRED`: `NO`
28. `NEW_MODEL_REQUIRED`: `NO`
29. `NEW_FEATURE_REQUIRED`: `NO`
30. `PRODUCTION_CHANGE_JUSTIFIED`: `MORE_SHADOW_EVIDENCE_REQUIRED_FOR_EXACT_FLOOR`
31. `PRODUCTION_CHANGE_EXECUTED`: `NO`
32. `TARGET_RUN_MUTATED`: `NO`
33. `NEXT_RECOMMENDED_STEP`: run a focused SHADOW refinement to define the near-term thesis-continuity floor/guard, using negative controls for 4-10BD false resets and positive controls for 21-40BD renewed independent opportunities; do not use PnL to pick the floor.
34. `FINAL_JUDGMENT`: `PHASE32_CR_FIXED_60BD_FLOOR_NOT_SEMANTICALLY_REQUIRED_BUT_PURE_EVIDENCE_AFTER_3BD_NOT_SAFE_NEAR_TERM_FLOOR_PLUS_RENEWED_PIT_EVIDENCE_REQUIRED_SHADOW_ONLY`

## Final Judgment

`PHASE32_CR_FIXED_60BD_FLOOR_NOT_SEMANTICALLY_REQUIRED_BUT_PURE_EVIDENCE_AFTER_3BD_NOT_SAFE_NEAR_TERM_FLOOR_PLUS_RENEWED_PIT_EVIDENCE_REQUIRED_SHADOW_ONLY`

