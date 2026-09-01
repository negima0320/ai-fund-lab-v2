# Phase32-CM — REENTRY Zero-Fill / Requalification Suppression READ-ONLY Audit

## Scope

This is a READ-ONLY root-cause audit for:

- target run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- latest safely completed date used: `2023-09-22`
- evidence window: `2022-10-03` through `2023-09-22`

No source, config, runtime state, Pending, Ledger, replay, resume, recover, or fresh-run mutation was performed for this phase.

Mandatory prior conclusions preserved:

- Phase32-CI observed zero legitimate REENTRY fills despite a large REENTRY population and an emergent action-type bias.
- Phase32-CJ identified the separate correctness defect where REENTRY fail-closed could be bypassed by same-symbol BUY_NEW.
- Phase32-CK repaired that bypass by keeping fail-closed REENTRY symbols in PC participant/rebatch authority.
- Phase32-CM is not a CK regression audit. It asks why legitimate REENTRY itself does not materialize under the current semantic contract.

## Intended Contract

Architecture/SoT keeps REENTRY as a valid semantic action. Its role is not to permanently ban previously owned symbols, but to prevent short-term churn and require renewed, decision-time evidence after an EXIT.

The intended semantic contract is:

- prior campaign identity and prior EXIT context must be known;
- the prior EXIT reason must be semantically meaningful, not generic `EXIT` / `SELL` / `UNKNOWN`;
- cooldown/churn protection must pass;
- current PIT evidence must show genuine recovery matching the prior EXIT cause;
- current candidate, BQ, safety, capacity, continuation quality, and downside checks must otherwise pass;
- once eligible, REENTRY should enter the same capital competition without a permanent ownership-history penalty.

## Current Source Contract

The current REENTRY path in `portfolio_construction.py` classifies a symbol with a strict-prior closed campaign as `REENTRY`, then requires all of the following before `REENTRY_ELIGIBLE`:

- temporal strict-prior evidence passes;
- cooldown passes;
- prior campaign identity exists;
- prior EXIT context exists and is non-generic;
- current candidate/requalification status passes;
- BQ result is acceptable;
- corporate-action authority is non-blocking;
- capacity is available and not severe;
- Entry Admission is not BUY_WAIT / REJECT / REVIEW / NO_ADD;
- continuation quality is acceptable;
- downside risk is acceptable;
- repeated unresolved churn is not present;
- technical recovery passes when required by prior EXIT class;
- extra reason-specific checks pass, including stricter handling for hard-stop, portfolio-competition, and reversal prior exits.

This contract is intentionally fail-closed for generic or missing prior EXIT context.

## Population Reconstruction

REENTRY was rebuilt in two layers:

- raw rows: every daily REENTRY observation in PC evidence;
- episodes: repeated rows collapsed by symbol plus prior EXIT/campaign lineage into one reconsideration episode.

Counts:

| Metric | Count |
| --- | ---: |
| Raw REENTRY rows | 5,376 |
| REENTRY episodes | 267 |
| REENTRY semantic PASS rows | 0 |
| REENTRY runtime plans | 0 |
| REENTRY fills | 0 |

Row semantic status:

| Status | Rows |
| --- | ---: |
| `FAIL_CLOSED` | 4,894 |
| `REVIEW_REQUIRED` | 482 |
| `PASS` | 0 |

Episode-level result:

| Result | Episodes |
| --- | ---: |
| semantic PASS ever observed | 0 |
| target membership / positive PC target ever observed | 0 |
| executable / runtime plan ever observed | 0 |
| fill ever observed | 0 |

`REENTRY_FUNNEL_COMPLETE = YES`: all 267 episodes terminate before positive PC/PS/runtime materialization.

## First-Block Distribution

Episode first blocking reason:

| First blocking reason | Episodes | Share |
| --- | ---: | ---: |
| current opportunity rank/requalification | 209 | 78.3% |
| active churn / too soon | 27 | 10.1% |
| insufficient short-trend evidence | 10 | 3.7% |
| insufficient prior-exit context | 9 | 3.4% |
| prior-exit identity/context unavailable | 5 | 1.9% |
| BQ rejection | 5 | 1.9% |
| repeated unresolved churn | 2 | 0.7% |

Row-level first blocking reason:

| First blocking reason | Rows |
| --- | ---: |
| current opportunity rank/requalification | 3,611 |
| active churn / too soon | 631 |
| insufficient prior-exit context | 482 |
| insufficient short-trend evidence | 231 |
| repeated unresolved churn | 174 |
| BQ rejection | 132 |
| prior-exit identity/context unavailable | 96 |
| insufficient renewed momentum | 19 |

The primary surface block is current opportunity rank/requalification. The deeper structural driver is that non-generic prior EXIT semantic context is never available in the observed episodes, so even later strengthened rows cannot satisfy all PASS conditions.

## Time Since EXIT

| Elapsed BD bucket | Episodes | Semantic PASS | Executable | Fill | Main blocks |
| --- | ---: | ---: | ---: | ---: | --- |
| 0-3 BD | 33 | 0 | 0 | 0 | active churn 27; rank/requalification 6 |
| 4-10 BD | 64 | 0 | 0 | 0 | rank/requalification 60; short-trend 3; BQ 1 |
| 11-20 BD | 30 | 0 | 0 | 0 | rank/requalification 26; prior context/identity 3; BQ 1 |
| 21-40 BD | 24 | 0 | 0 | 0 | rank/requalification 20; short-trend 3; BQ 1 |
| 41-60 BD | 19 | 0 | 0 | 0 | rank/requalification 18; prior context 1 |
| >60 BD | 97 | 0 | 0 | 0 | rank/requalification 79; prior context/identity 10; short-trend 4 |

Short-term churn protection explains 27 episodes. Post-churn suppression explains 240 episodes. Suppression remains present after 60+ business days, where 97 episodes still produce zero semantic PASS / executable / fill.

## Renewed-Strength Evidence

Using only current decision-time PIT fields already present in the artifacts, episodes were classified for audit purposes:

| PIT classification | Episodes |
| --- | ---: |
| `CLEARLY_RESTRENGTHENED` | 61 |
| `PARTIALLY_RESTRENGTHENED` | 148 |
| `NOT_RESTRENGTHENED` | 58 |
| `INSUFFICIENT_DATA` | 0 |

This is not a proposed Production rule. It is a read-only characterization showing that zero fills are not explained by an absence of renewed-strength evidence in every case.

Valid-looking blocked population:

- 61 episodes were clearly re-strengthened under existing PIT evidence but still never materialized as REENTRY.
- 50 of those had same-day funded NEW symbols.
- 1 had same-day ADD competition.
- In many episodes, first-block evidence and strongest later PIT evidence differ; the episode first block may be rank/requalification while the strongest row later has better current evidence but still cannot pass the full REENTRY contract.

Representative examples:

| Date | Symbol | Prior EXIT | Elapsed BD | Rank | BQ | Trend | Momentum | Block |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| 2022-11-18 | 45940 | 2022-11-10 `EXIT` | 5 | 4 | `REDUCED` | 1.227 | 1.127 | prior-exit identity/context unavailable |
| 2022-12-01 | 92270 | 2022-11-07 `EXIT` | 17 | 10 | `REDUCED` | 1.288 | 1.053 | current opportunity rank/requalification |
| 2022-12-08 | 67210 | 2022-11-18 `EXIT` | 13 | 8 | `REDUCED` | 1.065 | 0.530 | current opportunity rank/requalification |
| 2023-01-17 | 59860 | 2022-10-17 `EXIT` | 65 | 9 | `REDUCED` | 1.068 | 0.101 | current opportunity rank/requalification |
| 2023-01-19 | 83060 | 2022-10-04 `EXIT` | 76 | 1 | `REDUCED` | 1.022 | 0.199 | insufficient short-trend evidence |
| 2023-02-13 | 45860 | 2023-01-25 `EXIT` | 12 | 5 | `REDUCED` | 1.558 | 1.505 | insufficient prior-exit context |
| 2023-02-16 | 45750 | 2022-10-07 `EXIT` | 93 | 10 | `REDUCED` | 1.588 | 1.266 | current opportunity rank/requalification |

## Prior EXIT Context

All 267 observed episodes surface generic prior EXIT semantics in the inspected REENTRY evidence:

| Prior context classification | Episodes |
| --- | ---: |
| non-generic complete semantic context | 0 |
| generic context | 267 |
| incomplete context | 0 |

`PRIOR_EXIT_CONTEXT_COMPLETENESS_RATE = 0.0%` for non-generic semantic context.

This does not mean every prior campaign/date is absent. It means the REENTRY eligibility path does not receive a semantically resolved prior EXIT reason class sufficient to satisfy its own contract. Generic `EXIT` therefore behaves as a long-lived penalty.

For long-delay episodes over 20 business days, the dominant prior reason remained generic `EXIT`:

| Prior EXIT reason | Long-delay no-PASS episodes |
| --- | ---: |
| `EXIT` | 140 |

`EXIT_REASON_LONG_LIVED_PENALTY_FOUND = YES`: generic `EXIT` context remains suppressive long after active churn should have decayed.

## PASS Condition Audit

Episode-level individual PASS-condition satisfaction:

| Condition | Episodes satisfying |
| --- | ---: |
| cooldown pass | 240 |
| non-generic prior EXIT context | 0 |
| rank <= 10 | 72 |
| BQ eligible | 265 |
| corporate action OK | 267 |
| capacity OK | 267 |
| Entry Admission OK | 267 |
| continuation quality OK | 267 |
| downside OK | 267 |
| trend pass | 199 |
| momentum pass | 249 |
| all conditions simultaneously | 0 |

The observed data supports `REENTRY_PASS_NEAR_IMPOSSIBLE_IN_OBSERVED_DATA = YES`. The hard zero is not BQ, CA, capacity, CQ, or downside; it is the combination of current requalification gates with a never-satisfied non-generic prior EXIT semantic context condition.

## Diagnostic Later Outcomes

The strong/weak populations above were frozen using PIT evidence first. Later outcomes were then characterized diagnostically only. These outcomes were not used to define thresholds or Production rules.

Approximate one-lot diagnostic outcomes for blocked clearly re-strengthened episodes:

| Horizon | n | Positive rate | Mean | Median | >=10k winners | <=-10k losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| +3BD | 55 | 21.8% | -11,108.5 | -3,200.0 | 2 | 18 |
| +5BD | 53 | 18.9% | -12,602.3 | -3,800.0 | 4 | 17 |
| +10BD | 44 | 29.5% | -12,699.5 | -1,700.0 | 5 | 12 |

For partially re-strengthened episodes:

| Horizon | n | Positive rate | Mean | Median | >=10k winners | <=-10k losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| +3BD | 98 | 33.7% | -2,356.2 | -500.0 | 2 | 10 |
| +5BD | 78 | 33.3% | -2,700.3 | -700.0 | 5 | 12 |
| +10BD | 34 | 17.6% | -9,632.9 | -3,400.0 | 2 | 10 |

Diagnostic characterization: blocked clearly re-strengthened cases were not uniformly profitable. This does not invalidate the semantic finding: zero REENTRY fills are not economically proven necessary by PIT evidence alone, and the current architecture suppresses all such cases before capital competition.

## Regime Breakdown

All REENTRY episodes:

| Regime | Episodes |
| --- | ---: |
| `BULL` | 112 |
| `RANGE` | 68 |
| `CORRECTION` | 35 |
| `RECOVERY` | 33 |
| `BEAR` | 19 |

Clearly re-strengthened episodes:

| Regime | Episodes |
| --- | ---: |
| `BULL` | 26 |
| `RANGE` | 13 |
| `RECOVERY` | 11 |
| `CORRECTION` | 7 |
| `BEAR` | 4 |

Post-churn episodes:

| Regime | Episodes |
| --- | ---: |
| `BULL` | 96 |
| `RANGE` | 64 |
| `CORRECTION` | 32 |
| `RECOVERY` | 31 |
| `BEAR` | 17 |

REENTRY suppression is not confined to BEAR/CORRECTION conditions. It occurs materially in BULL and RECOVERY as well.

## Correctness vs Semantics

No CK-style Runtime correctness regression was found in this audit. The evidence does not show that fail-closed REENTRY was bypassed by BUY_NEW after CK; CM did not retest that path as its primary purpose.

The supported finding is semantic/authority overconstraint:

- the architecture says prior ownership should not become a permanent penalty;
- the current implementation requires non-generic prior EXIT semantic context;
- actual artifacts provide generic `EXIT` context for all 267 episodes;
- therefore all REENTRY episodes are structurally unable to pass, even when cooldown has passed and current PIT evidence has materially re-strengthened.

This is not evidence that Production should immediately allow more REENTRY fills. It is evidence that the existing REENTRY architecture needs a shadow follow-up to test whether already-available PIT and prior-exit evidence can safely distinguish:

- immediate churn-prone rebuy;
- weak stale reconsideration;
- genuine renewed opportunity.

No new model, component, or raw feature is required for that next step. The likely repair/design boundary is inside existing REENTRY prior-exit semantic materialization and current requalification authority.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-09-22`
2. `REENTRY_INTENDED_SEMANTIC_CONTRACT`: prevent short-term churn, require strict-prior prior EXIT identity/context plus renewed current PIT strength, then allow eligible REENTRY into normal capital competition without permanent past-ownership penalty.
3. `RAW_REENTRY_ROW_COUNT`: `5,376`
4. `REENTRY_EPISODE_COUNT`: `267`
5. `REENTRY_FUNNEL_COMPLETE`: `YES`
6. `PRIMARY_REENTRY_BLOCK_REASON`: `current opportunity rank/requalification` by first-block episode count, `209/267`; deep structural suppression driver is non-generic prior EXIT context never materializing.
7. `SECONDARY_REENTRY_BLOCK_REASONS`: active churn `27`, insufficient short-trend `10`, insufficient prior-exit context `9`, prior-exit identity/context unavailable `5`, BQ rejection `5`, repeated unresolved churn `2`.
8. `SHORT_TERM_CHURN_BLOCK_COUNT`: `27`
9. `POST_CHURN_REENTRY_BLOCK_COUNT`: `240`
10. `LONG_DELAY_REENTRY_SUPPRESSION_PRESENT`: `YES`; `97` episodes at `>60BD`, zero PASS/executable/fill.
11. `CLEARLY_RESTRENGTHENED_REENTRY_EPISODE_COUNT`: `61`
12. `VALID_LOOKING_REENTRY_BLOCKED_COUNT`: `61`
13. `STRONG_REENTRY_BYPASSED_BY_NEW_COUNT`: `50`
14. `STRONG_REENTRY_BYPASSED_BY_ADD_COUNT`: `1`
15. `EXIT_REASON_LONG_LIVED_PENALTY_FOUND`: `YES`; generic prior reason `EXIT` remains a long-lived suppressor.
16. `PRIOR_EXIT_CONTEXT_COMPLETENESS_RATE`: `0.0%` for non-generic semantic prior EXIT context.
17. `MISSING_CONTEXT_PRIMARY_SUPPRESSION_DRIVER`: `YES`; all observed episodes fail the non-generic context prerequisite.
18. `REENTRY_PASS_CONDITION_SET`: temporal strict-prior, cooldown, prior campaign identity, non-generic prior EXIT context, current candidate/requalification, BQ, CA, capacity, Entry Admission, CQ, downside, churn, technical recovery, and reason-specific recovery checks.
19. `REENTRY_PASS_CONDITIONS_STRUCTURALLY_OVERCONSTRAINED`: `YES`, in observed data, because required non-generic prior EXIT context is never supplied and all-condition simultaneous pass is `0/267`.
20. `REENTRY_PASS_NEAR_IMPOSSIBLE_IN_OBSERVED_DATA`: `YES`
21. `REENTRY_CORRECTNESS_DEFECT_FOUND`: `UNCONFIRMED_AS_RUNTIME_DEFECT`; no direct CK-style bypass/regression found by CM. A semantic/context authority defect is supported.
22. `REENTRY_SEMANTIC_OVERCONSTRAINT_SUPPORTED`: `YES`
23. `BLOCKED_CLEARLY_RESTRENGTHENED_LATER_OUTCOME_CHARACTERIZATION`: later outcomes were mixed and often negative diagnostically; they do not justify Production threshold changes, but they confirm the strong-blocked population was real and not empty.
24. `REENTRY_OPPORTUNITY_SUPPRESSION_MATERIALITY`: `MATERIAL`
25. `REENTRY_SUPPRESSION_REGIME_DEPENDENT`: `NO_NOT_ONLY_UNFAVORABLE_REGIMES`; suppression appears in BULL/RECOVERY/RANGE as well.
26. `EXISTING_PIT_EVIDENCE_SUFFICIENT_FOR_REENTRY_REQUALIFICATION`: `YES_FOR_SHADOW_CLASSIFICATION`; Production still lacks accepted non-generic prior EXIT semantic authority.
27. `REPAIRABLE_INSIDE_EXISTING_REENTRY_ARCHITECTURE`: `YES`
28. `NEW_COMPONENT_REQUIRED`: `NO`
29. `NEW_MODEL_REQUIRED`: `NO`
30. `NEW_FEATURE_REQUIRED`: `NO`
31. `PRODUCTION_CHANGE_JUSTIFIED`: `NO_NOT_FROM_CM_ALONE`
32. `SHADOW_FOLLOWUP_JUSTIFIED`: `YES`
33. `NEXT_RECOMMENDED_STEP`: design and run a shadow-only REENTRY requalification contract that preserves churn prevention and fail-closed missing-context behavior while testing whether already-available prior EXIT semantics and current PIT re-strengthening can requalify post-churn episodes.
34. `FINAL_JUDGMENT`: `PHASE32_CM_REENTRY_ZERO_FILL_ROOT_CAUSE_IDENTIFIED_SEMANTIC_CONTEXT_OVERCONSTRAINT_AND_CURRENT_REQUALIFICATION_SUPPRESSION_SHADOW_FOLLOWUP_JUSTIFIED_NO_PRODUCTION_CHANGE`

## Final Judgment

`PHASE32_CM_REENTRY_ZERO_FILL_ROOT_CAUSE_IDENTIFIED_SEMANTIC_CONTEXT_OVERCONSTRAINT_AND_CURRENT_REQUALIFICATION_SUPPRESSION_SHADOW_FOLLOWUP_JUSTIFIED_NO_PRODUCTION_CHANGE`
