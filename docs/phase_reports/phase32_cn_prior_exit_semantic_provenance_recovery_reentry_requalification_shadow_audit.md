# Phase32-CN — Prior EXIT Semantic Provenance Recovery / REENTRY Requalification SHADOW Audit

## Scope

This is a READ-ONLY / SHADOW audit for:

- target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- baseline evidence window used: `2022-10-03` through `2023-09-22`
- baseline preserved from Phase32-CM: 5,376 raw REENTRY rows, 267 REENTRY episodes, 0 REENTRY PASS, 0 runtime plans, 0 fills

The run directory now contains later artifacts, but CN preserves the CM-mandated population and cutoff so that the semantic restoration experiment is measured against the same accepted CM baseline.

No Production code, Strategy semantics, thresholds, cooldowns, models, features, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run was changed or executed.

## Authority Contract

Authoritative prior EXIT semantics are owned at decision time by PM / Strategy position-management evidence and then by the canonical campaign lifecycle artifact:

- PM decision artifacts: `daily/<date>/position_management/pm_decisions.json` and `daily/<date>/strategy/position_management.json`
- campaign lifecycle authority: `daily/<date>/positions/position_campaigns.json`
- strict-prior PM EXIT context bridge: `shadow_runtime._strict_prior_pm_exit_decision_evidence_by_campaign`
- REENTRY consumer: `portfolio_construction._semantic_reentry_evidence`, `_reentry_recovery_evidence`, and `_canonical_reentry_semantic_eligibility`

The current REENTRY reason taxonomy is the existing `_previous_exit_reason_class` taxonomy:

- `CORPORATE_ACTION`
- `HARD_STOP`
- `REVERSAL`
- `TREND_MOMENTUM`
- `PORTFOLIO_COMPETITION`
- `ADMINISTRATIVE`
- `GENERIC`

No new taxonomy was invented for CN. Some PM reason codes that are meaningful to humans, such as generic risk-reduction wording without one of the existing taxonomy tokens, remain `GENERIC` under the current source contract.

## Reconstruction

All 267 REENTRY episodes were reconstructed to the strict-prior EXIT that created the prior closed campaign.

Reconstruction sources:

| Source | Use |
| --- | --- |
| `positions/position_campaigns.json` `pm_decision_evidence_events` | preferred closed-campaign PM semantic authority |
| `position_management/pm_decisions.json` | fallback PM decision authority |
| `strategy/position_management.json` | fallback Strategy/PM decision authority |
| PC REENTRY member fields | current REENTRY-consumed prior context |

Result:

| Metric | Count |
| --- | ---: |
| REENTRY episodes | 267 |
| prior EXITs reconstructed | 267 |
| original non-generic under current taxonomy | 229 |
| original generic under current taxonomy | 38 |
| original missing | 0 |

Original non-generic breakdown under the existing taxonomy:

| Prior EXIT class | Episodes |
| --- | ---: |
| `TREND_MOMENTUM` | 200 |
| `HARD_STOP` | 29 |
| `GENERIC` | 38 |

The original EXIT decision time usually had meaningful PM reason codes. Examples:

| Symbol | Prior EXIT | Original PM reason/codes | Current REENTRY scalar reason |
| --- | --- | --- | --- |
| 83060 | 2022-10-04 | `trend_and_opportunity_broken` | `EXIT` |
| 33700 | 2022-10-05 | `pm_discrete_control_persistent_deterioration_exit`, `risk_increased_but_trend_not_broken` | `EXIT` |
| 45750 | 2022-10-07 | `risk_increased_but_trend_not_broken` | `EXIT` |
| 59860 | 2022-10-17 | `pm_discrete_control_persistent_deterioration_exit`, `risk_increased_but_trend_not_broken` | `EXIT` |
| 67310 | 2023-04-11 | trend/risk deterioration PM context | `EXIT` |

## Provenance Loss Boundary

The first semantic loss is not at original PM decision time. It occurs after strict-prior PM/campaign evidence exists and before or during the prior-exit bridge into PC REENTRY member materialization.

Observed mechanism:

- original PM and closed-campaign evidence contain non-generic reason codes for 229/267 episodes;
- PC REENTRY members can carry `prior_exit_reason_codes`, but scalar `prior_exit_reason` / `previous_exit_reason` is `EXIT` for all 267 episodes;
- current `_reentry_recovery_evidence` treats scalar `previous_exit_reason in {"", "UNKNOWN", "EXIT", "SELL"}` as insufficient prior context even when reason codes classify as non-generic;
- therefore REENTRY recovery still emits `insufficient_prior_exit_context` or other fail-closed states instead of consuming the authoritative original EXIT semantics as the primary scalar reason.

First boundary:

`prior-exit bridge -> PC opportunity/member materialization -> REENTRY evidence builder`

The collapse mechanism is:

`specific PM EXIT reason/codes are preserved upstream, but REENTRY scalar prior reason is normalized to action-level EXIT; current recovery logic then lets that generic scalar override the recovered code semantics.`

## SHADOW Restoration Method

CN built an audit-only mapping from same-run, strict-prior, same-campaign artifacts:

- key: symbol + prior campaign id + prior EXIT business date
- restored fields in memory only:
  - `prior_exit_reason`
  - `previous_exit_reason`
  - `prior_exit_reason_codes`
  - `previous_exit_reason_codes`
- source: original PM / campaign evidence
- no symbol-only guessing
- no future data
- no later outcome
- no synthetic reason when existing taxonomy classified the source as `GENERIC`

The restored rows were then passed through the existing current REENTRY recovery logic in SHADOW. This does not allocate capital, submit orders, or mutate artifacts. It measures whether the unchanged REENTRY recovery contract would recognize more legitimate candidates once the semantic reason is no longer collapsed to `EXIT`.

## SHADOW Results

Current baseline:

| Population | PASS |
| --- | ---: |
| 267 current REENTRY episodes | 0 |

With recovered prior EXIT semantics:

| SHADOW result | Count |
| --- | ---: |
| recovery PASS / would enter capital competition | 25 |
| fail-closed | 233 |
| review-required | 9 |

Recovery reason distribution after semantic restoration:

| Reason | Episodes |
| --- | ---: |
| `reentry_recovery_qualified` | 25 |
| `reentry_opportunity_not_requalified` | 202 |
| `reentry_trend_recovery_not_satisfied` | 19 |
| `insufficient_prior_exit_context` | 9 |
| `reentry_hard_stop_new_thesis_not_sufficient` | 6 |
| `reentry_buy_quality_not_requalified` | 3 |
| `reentry_repeated_unresolved_churn` | 2 |
| `reentry_momentum_recovery_not_satisfied` | 1 |

PASS by prior EXIT class:

| Prior EXIT class | Episodes | SHADOW PASS | Main remaining blocker |
| --- | ---: | ---: | --- |
| `TREND_MOMENTUM` | 200 | 25 | rank/requalification |
| `HARD_STOP` | 29 | 0 | hard-stop new thesis / rank |
| `GENERIC` | 38 | 0 | context remains generic |

Post-churn and long-delay:

| Population | Episodes / count |
| --- | ---: |
| post-churn SHADOW PASS | 25 |
| long-delay `>60BD` SHADOW PASS | 6 |
| clearly re-strengthened with recoverable context | 8 |
| clearly re-strengthened SHADOW PASS | 1 |

Same-day capital context for SHADOW PASS episodes:

| Same-day competition | Count |
| --- | ---: |
| same-day NEW present | 0 |
| same-day ADD present | 24 |

Representative SHADOW PASS episodes:

| Date | Symbol | Prior EXIT | Prior class | Elapsed BD | Rank | BQ |
| --- | --- | --- | --- | ---: | ---: | --- |
| 2023-03-08 | 73590 | 2022-10-13 | `TREND_MOMENTUM` | 103 | 16 | `REDUCED_ALLOCATION_ONLY` |
| 2023-01-16 | 59860 | 2022-10-17 | `TREND_MOMENTUM` | 64 | 16 | `REDUCED_ALLOCATION_ONLY` |
| 2023-04-03 | 65500 | 2022-10-25 | `TREND_MOMENTUM` | 113 | 13 | `REDUCED_ALLOCATION_ONLY` |
| 2023-06-28 | 67310 | 2023-04-11 | `TREND_MOMENTUM` | 55 | 7 | `REDUCED_ALLOCATION_ONLY` |
| 2023-08-21 | 65730 | 2023-01-20 | `TREND_MOMENTUM` | 150 | 11 | `REDUCED_ALLOCATION_ONLY` |

These are recovery-contract PASS cases, not final Production fills. They would still have to pass ordinary capital competition, PC/PS sizing, lot, cash, Pending, submit, and execution contracts.

## Interpretation

Semantic provenance loss is real and material:

- original non-generic prior EXIT semantics exist for 229/267 episodes;
- all 267 current REENTRY members expose generic scalar `EXIT` to the recovery contract;
- restoring authoritative semantics in SHADOW changes recovery PASS from 0 to 25.

However provenance restoration alone does not explain all suppression:

- 242/267 episodes still do not reach SHADOW recovery PASS;
- the primary remaining block is current opportunity rank/requalification, `202` episodes;
- hard-stop and generic-at-source cases remain blocked under the unchanged current taxonomy;
- restored semantics produce legitimate PASS cases but not a broad REENTRY flood.

Therefore the best-supported classification is:

`MIXED_PROVENANCE_AND_REQUALIFICATION`

The provenance defect explains the hard zero and creates a permanent action-level `EXIT` penalty. Current requalification semantics remain the dominant bottleneck after context restoration.

## Repair Boundary Assessment

The narrowest future Production repair boundary is not a threshold or model change. It is:

1. repair prior EXIT semantic propagation/materialization so the scalar prior reason consumed by REENTRY is the authoritative PM/campaign semantic reason, not action-level `EXIT`;
2. preserve reason codes and source PM decision id in the same prior-exit context envelope;
3. continue to fail closed when original source context is genuinely generic or missing;
4. preserve cooldown and churn protection;
5. run a follow-up SHADOW/acceptance check before considering any requalification gate change.

No BUY_NEW, ADD, BQ, PC/PS, cooldown, rank, threshold, model, feature, or capital allocation change is justified by CN alone.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-09-22`
2. `AUTHORITATIVE_EXIT_REASON_SOURCE`: PM / Strategy position-management decision artifacts, persisted into `positions/position_campaigns.json` `pm_decision_evidence_events`; Runtime/Ledger proves execution but is not the owner of semantic EXIT reason.
3. `AUTHORITATIVE_EXIT_REASON_TAXONOMY`: existing `_previous_exit_reason_class` taxonomy: `CORPORATE_ACTION`, `HARD_STOP`, `REVERSAL`, `TREND_MOMENTUM`, `PORTFOLIO_COMPETITION`, `ADMINISTRATIVE`, `GENERIC`.
4. `PRIOR_EXITS_RECONSTRUCTED_COUNT`: `267/267`
5. `ORIGINAL_NON_GENERIC_EXIT_REASON_COUNT`: `229`
6. `ORIGINAL_GENERIC_ONLY_EXIT_COUNT`: `38`
7. `FIRST_EXIT_SEMANTIC_PROVENANCE_LOSS_BOUNDARY`: `prior-exit bridge -> PC opportunity/member materialization -> REENTRY evidence builder`
8. `EXIT_REASON_COLLAPSE_MECHANISM`: authoritative PM reason/codes survive upstream, but scalar `prior_exit_reason` / `previous_exit_reason` is materialized as generic action `EXIT`; current recovery logic treats that scalar as insufficient context even when codes are present.
9. `RECOVERABLE_NON_GENERIC_PRIOR_EXIT_EPISODE_COUNT`: `229`
10. `RECOVERABLE_NON_GENERIC_PRIOR_EXIT_RATE`: `85.8%`
11. `SHADOW_PRIOR_EXIT_SEMANTIC_RECOVERY_COMPLETE`: `YES_FOR_267_EPISODES`; `229` recoverable non-generic, `38` correctly remain generic under current taxonomy.
12. `SHADOW_REENTRY_PASS_COUNT_WITH_RECOVERED_EXIT_SEMANTICS`: `25` recovery PASS / would-enter-capital-competition episodes.
13. `PASS_RECOVERY_DELTA_FROM_SEMANTIC_RESTORATION`: `+25` episodes, from `0` to `25`.
14. `POST_CHURN_SHADOW_PASS_COUNT`: `25`
15. `CLEARLY_RESTRENGTHENED_RECOVERABLE_CONTEXT_COUNT`: `8` under exact current recovery-function re-evaluation of best available episode rows.
16. `CLEARLY_RESTRENGTHENED_SHADOW_PASS_COUNT`: `1`
17. `PRIMARY_POST_RECOVERY_REENTRY_BLOCK_REASON`: `current opportunity rank/requalification`, `202` episodes.
18. `REQUALIFICATION_OVERCONSTRAINT_REMAINS_AFTER_CONTEXT_RECOVERY`: `YES`; provenance restoration removes the hard zero but leaves most episodes blocked by rank/requalification or reason-specific recovery.
19. `SHADOW_PASS_BY_PRIOR_EXIT_CLASS`: `TREND_MOMENTUM 25/200`, `HARD_STOP 0/29`, `GENERIC 0/38`.
20. `LONG_DELAY_SHADOW_PASS_COUNT`: `6`
21. `SHADOW_PASS_EPISODES_WITH_SAME_DAY_NEW`: `0`
22. `SHADOW_PASS_EPISODES_WITH_SAME_DAY_ADD`: `24`
23. `OUTCOME_DATA_USED_FOR_PASS_CLASSIFICATION`: `NO`
24. `PRIMARY_REENTRY_ZERO_FILL_ROOT_CAUSE_AFTER_CN`: `MIXED_PROVENANCE_AND_REQUALIFICATION`
25. `NARROWEST_CORRECT_REPAIR_BOUNDARY`: prior EXIT semantic context materialization into PC/REENTRY, specifically scalar reason plus reason codes plus PM source id, followed by separate SHADOW validation of remaining requalification gates.
26. `REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE`: `YES`
27. `ACTIVE_CHURN_PROTECTION_CAN_BE_PRESERVED`: `YES`
28. `PERMANENT_PRIOR_OWNERSHIP_BAN_REQUIRED`: `NO`
29. `NEW_COMPONENT_REQUIRED`: `NO`
30. `NEW_MODEL_REQUIRED`: `NO`
31. `NEW_FEATURE_REQUIRED`: `NO`
32. `PRODUCTION_REPAIR_JUSTIFIED_FROM_CN`: `YES_FOR_NARROW_PROVENANCE_PROPAGATION_REPAIR_ONLY`; `NO` for threshold/rank/requalification tuning.
33. `PRODUCTION_CHANGE_EXECUTED`: `NO`
34. `TARGET_RUN_MUTATED`: `NO`
35. `RESUME_EXECUTED`: `NO`
36. `FRESH_RUN_EXECUTED`: `NO`
37. `NEXT_RECOMMENDED_STEP`: implement a narrow provenance-only repair that makes authoritative PM/campaign prior EXIT scalar semantics available to REENTRY, then run focused tests plus a READ-ONLY actual-path acceptance audit; defer any requalification-gate redesign until after restored-context evidence is measured.
38. `FINAL_JUDGMENT`: `PHASE32_CN_PRIOR_EXIT_SEMANTIC_PROVENANCE_LOSS_CONFIRMED_SHADOW_RESTORATION_RECOVERS_25_REENTRY_RECOVERY_PASS_CASES_MIXED_REQUALIFICATION_BOTTLENECK_REMAINS_NARROW_PROVENANCE_REPAIR_JUSTIFIED`

## Final Judgment

`PHASE32_CN_PRIOR_EXIT_SEMANTIC_PROVENANCE_LOSS_CONFIRMED_SHADOW_RESTORATION_RECOVERS_25_REENTRY_RECOVERY_PASS_CASES_MIXED_REQUALIFICATION_BOTTLENECK_REMAINS_NARROW_PROVENANCE_REPAIR_JUSTIFIED`
