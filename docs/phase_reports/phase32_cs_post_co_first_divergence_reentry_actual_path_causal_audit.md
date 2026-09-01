# Phase32-CS — Post-CO First-Divergence / REENTRY Actual-Path Causal Audit

## Scope

This is a READ-ONLY causal comparison between:

- Pre-CO run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Post-CO run: `runtime-test-historical-extended-smoke-20260901T205837445258Z`

The comparison asks whether Phase32-CO's prior EXIT semantic provenance repair changed actual REENTRY eligibility, planning, filling, and portfolio state. It is not a profitability comparison.

No code, config, Runtime state, Pending, Ledger, resume, recover, replay, fresh-run, or run artifact was modified.

## Evidence Coverage

- Pre-CO run completed through `2024-06-07`; run is now halted/abandoned evidence.
- Post-CO run completed through `2022-11-07`; current `run_state.next_job = 2022-11-08:market_refresh`.
- Latest common completed date used: `2022-11-07`.

`LATEST_COMMON_COMPLETED_DATE_USED = 2022-11-07`

## First Divergence

Raw artifact hashes differ from day one because run ids, source commits, and artifact paths differ. Those were not treated as material decision differences.

The first material semantic artifact difference appears at:

`FIRST_DIVERGENCE_DATE = 2022-10-05`

`FIRST_DIVERGENCE_STAGE = strategy/portfolio_construction`

On `2022-10-05`, post-CO PC materializes non-generic scalar prior EXIT reasons where pre-CO still materializes generic `EXIT`:

| Symbol | Pre-CO scalar | Post-CO scalar | Reason codes | State |
| --- | --- | --- | --- | --- |
| 83060 | `EXIT` | `strategy_intelligence_sell_side_evidence_connected` | `strategy_intelligence_sell_side_evidence_connected`, `trend_and_opportunity_broken` | still blocked by churn |
| 89180 | `EXIT` | `hard_stop_current_return` | `hard_stop_current_return`, `strategy_intelligence_sell_side_evidence_connected` | still blocked by churn |

This proves the CO repair is visible in actual post-CO PC artifacts before any holdings/cash divergence.

The first causal decision divergence, meaning the first divergence that changes allocation/planning/fill, appears at:

`FIRST_CAUSAL_DECISION_DIVERGENCE = 2022-10-25:strategy/portfolio_construction`

## Pre-Divergence Determinism

After normalizing run-specific paths, ids, hashes, and timestamps, Candidate, BQ, PM, PS, Runtime Planning, fills, holdings/cash behavior remain materially identical before the CO semantic PC differences. The early 2022-10-05 PC differences are expected direct CO semantic effects and do not yet change portfolio state.

`PRE_DIVERGENCE_DETERMINISM_PASS = YES_EXCEPT_EXPECTED_CO_SEMANTIC_FIELDS`

## 83060 Path Comparison

Prior history:

- Prior campaign full EXIT date: `2022-10-04`
- Prior PM decision id: `pm-2022-10-04-83060-exit`
- Prior PM action: `EXIT`
- Prior reason codes: `strategy_intelligence_sell_side_evidence_connected`, `trend_and_opportunity_broken`
- Prior EXIT class: `TREND_MOMENTUM`

2022-10-25 PC comparison:

| Field | Pre-CO | Post-CO |
| --- | --- | --- |
| semantic buy type | `REENTRY` | `REENTRY` |
| business days since EXIT | 14 | 14 |
| scalar prior reason | `EXIT` | `strategy_intelligence_sell_side_evidence_connected` |
| prior reason codes | preserved | preserved |
| prior EXIT class | `TREND_MOMENTUM` | `TREND_MOMENTUM` |
| opportunity rank | 10 | 10 |
| construction priority | 19 | 19 |
| BQ | `REDUCED_ALLOCATION_ONLY`; source BQ row is high/full eligible evidence | `REDUCED_ALLOCATION_ONLY`; source BQ row is high/full eligible evidence |
| trend close/MA20 | 1.055926 | 1.055926 |
| 20D momentum | 0.033324 | 0.033324 |
| Entry Admission | `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION` | same |
| CQ / downside | PASS / PASS | PASS / PASS |
| REENTRY recovery | `REVIEW_REQUIRED`, `insufficient_prior_exit_context` | `PASS`, `reentry_recovery_qualified` |
| PC target membership | false | true |
| PC target weight | 0.0 | 0.067556 |
| Runtime planning | `NO_ORDER` | `BUY_NEW` planning intent from accepted post-full-exit buy chain |
| Fill | none | BUY 100 @ 712.0 |
| New campaign | none | `pc-800e4a57dc576701-83060-0001` |

`83060_PATH_COMPARISON = CO_RESTORED_PRIOR_EXIT_SCALAR_REENTRY_REVIEW_REQUIRED_TO_PASS_PC_ALLOCATED_AND_FILLED`

## 21950 Path Comparison

2022-10-25 PC comparison:

| Field | Pre-CO | Post-CO |
| --- | --- | --- |
| semantic buy type | `BUY_NEW` | `BUY_NEW` |
| prior ownership | none | none |
| opportunity rank | 40 | 40 |
| construction priority | 42 | 42 |
| BQ | `REDUCED_ALLOCATION_ONLY`, low quality score 0.519126 | same |
| trend close/MA20 | 0.972352 | same |
| 20D momentum | -0.196907 | same |
| Entry Admission | `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION` | same |
| PC target membership | true | false |
| PC target weight | 0.074111 | 0.0 |
| Runtime planning | `BUY_NEW` | `NO_ORDER` |
| Fill | BUY 100 @ 739.0 | none |
| Campaign | `pc-e5cd1dbaddd94198-21950-0001` | none |

21950 did not change because its own evidence changed. It was displaced because 83060 entered the deployable PC set after CO restored its prior EXIT semantic context.

`21950_PATH_COMPARISON = UNCHANGED_BUY_NEW_EVIDENCE_DISPLACED_BY_POST_CO_83060_REENTRY_PASS_CAPITAL_COMPETITION`

## CO Actual-Path Semantics

`POST_CO_AUTHORITATIVE_PRIOR_EXIT_REASON_OBSERVED = YES`

Actual post-CO artifacts before and at the first causal divergence show PM-derived non-generic scalar prior reasons:

- 83060: `strategy_intelligence_sell_side_evidence_connected`
- 89180: `hard_stop_current_return`

`PRE_CO_GENERIC_COLLAPSE_REPRODUCED = YES`

Pre-CO equivalent PC artifacts preserve reason codes but keep scalar `prior_exit_reason` / `previous_exit_reason` as generic `EXIT`, causing the recovery consumer to return `insufficient_prior_exit_context`.

`CO_CAUSED_REENTRY_ELIGIBILITY_CHANGE = YES`

Through the first causal divergence window, exactly one symbol changes from pre-CO blocked to post-CO PASS because of restored prior EXIT semantics:

| Date | Symbol | Pre-CO | Post-CO | Cause |
| --- | --- | --- | --- | --- |
| 2022-10-25 | 83060 | `REVIEW_REQUIRED`, `insufficient_prior_exit_context` | `PASS`, `reentry_recovery_qualified` | scalar prior EXIT reason restored from generic `EXIT` to non-generic PM semantic reason |

## REENTRY Plan / Fill Counts

Through the first causal divergence date (`2022-10-25`):

- `POST_CO_REENTRY_PASS_COUNT_TO_FIRST_DIVERGENCE = 1`
- `POST_CO_REENTRY_PLAN_COUNT_TO_FIRST_DIVERGENCE = 1`
- `POST_CO_REENTRY_FILL_COUNT_TO_FIRST_DIVERGENCE = 1`

The event is 83060 on `2022-10-25`.

Through the latest common completed date (`2022-11-07`), post-CO still has only this one REENTRY PASS / plan / fill event in the inspected population.

`POST_CO_REENTRY_EVENT_POPULATION_FOR_NEXT_AUDIT = 1 event: 2022-10-25 83060, prior EXIT 2022-10-04, prior class TREND_MOMENTUM, filled BUY 100`

## Classification Integrity

Legitimate prior-owned symbols remain semantically REENTRY at PC. The downstream Runtime order chain still uses `BUY_NEW` as the post-full-exit buy planning/order action label, but PC retains REENTRY lineage and passes prior campaign context into the decision materialization. No evidence was found that a blocked REENTRY was bypassed by same-symbol BUY_NEW.

`CK_REENTRY_BUY_NEW_BYPASS_RECURRED = NO`

`ACTIVE_CHURN_PROTECTION_PRESERVED = YES`

Evidence:

- 2022-10-05 83060 and 89180 receive restored scalar prior reasons, but remain blocked by churn protection.
- No post-CO REENTRY row with failed cooldown was observed as PASS through the first divergence window.

`BUY_ADD_G129_PRESERVED = YES_NO_RELEVANT_ADD_DIVERGENCE_OBSERVED`

No BUY_ADD/G129 path participated in the first divergence chain.

## Capital Competition Causal Chain

`CAPITAL_COMPETITION_CAUSAL_CHAIN_CONFIRMED = YES`

Confirmed chain:

```text
CO semantic repair
-> 83060 prior EXIT scalar becomes strategy_intelligence_sell_side_evidence_connected instead of EXIT
-> prior EXIT class TREND_MOMENTUM can be consumed with preserved reason codes
-> REENTRY recovery becomes PASS instead of insufficient_prior_exit_context
-> 83060 PC target membership becomes true with target_weight 0.067556
-> 21950 BUY_NEW remains lower-quality/low-rank and loses allocation
-> Runtime planning emits BUY for 83060 and NO_ORDER for 21950
-> execution fills 83060 BUY 100 instead of 21950 BUY 100
-> holdings/cash diverge from 2022-10-25 onward
```

## Direct vs Cascading Differences

`DIRECT_CO_EFFECT_COUNT = 1`

Direct causal effect: 83060 REENTRY changes from review-required/zero target to PASS/positive target.

`CASCADE_DIFFERENCE_COUNT = 1`

Immediate cascade: 21950's own BUY_NEW evidence remains materially unchanged, but it loses allocation/fill because 83060 enters capital competition.

`UNRELATED_DIFFERENCE_COUNT = 0`

No unrelated material divergence was identified before or at the first causal divergence. Later differences after 2022-10-25 should be treated as potentially cascading from the changed holdings/cash path unless separately proven otherwise.

## CO Acceptance

`PNL_USED_FOR_CO_ACCEPTANCE = NO`

No later return, PnL, final campaign outcome, future price, future regime, or selected winner outcome was used to judge CO.

`CO_ACTUAL_PATH_ACCEPTANCE = PASS`

Reason:

- post-CO actual artifacts materialize non-generic authoritative prior EXIT scalar semantics;
- pre-CO generic collapse is reproduced;
- restored semantics change actual REENTRY eligibility exactly where expected;
- churn protection remains active for near-immediate cases;
- no BUY_NEW bypass recurrence was observed;
- downstream PC/PS/Runtime/fill path consumes the changed eligibility and creates one actual filled REENTRY-lineage event.

Important boundary:

CS accepts CO's actual-path provenance repair. It does not answer whether the broader REENTRY penalty mechanism should remain as-is, and it does not judge whether the 14BD 83060 release is the ideal future lifecycle rule. That question belongs to the CQ/CR temporal lifecycle track.

`POST_CO_RUN_USEFUL_FOR_REENTRY_NECESSITY_AUDIT = YES`

The 83060 event is especially useful because it is an actual filled, post-CO REENTRY-lineage case at 14BD, where CQ/CR already raised the question of near-term floor vs evidence-based release.

## Required Final Answers

1. `PRE_CO_RUN_ID`: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
2. `POST_CO_RUN_ID`: `runtime-test-historical-extended-smoke-20260901T205837445258Z`
3. `LATEST_COMMON_COMPLETED_DATE_USED`: `2022-11-07`
4. `FIRST_DIVERGENCE_DATE`: `2022-10-05`
5. `FIRST_DIVERGENCE_STAGE`: `strategy/portfolio_construction`
6. `FIRST_CAUSAL_DECISION_DIVERGENCE`: `2022-10-25:strategy/portfolio_construction:83060_REENTRY_REVIEW_REQUIRED_TO_PASS`
7. `21950_PATH_COMPARISON`: unchanged BUY_NEW evidence; pre-CO allocated/fills 100; post-CO displaced to NO_ORDER by 83060 REENTRY PASS.
8. `83060_PATH_COMPARISON`: pre-CO scalar `EXIT` -> insufficient prior context; post-CO scalar PM semantic reason -> REENTRY PASS -> PC target -> BUY 100 fill.
9. `POST_CO_AUTHORITATIVE_PRIOR_EXIT_REASON_OBSERVED`: `YES`
10. `PRE_CO_GENERIC_COLLAPSE_REPRODUCED`: `YES`
11. `CO_CAUSED_REENTRY_ELIGIBILITY_CHANGE`: `YES: 83060 on 2022-10-25`
12. `POST_CO_REENTRY_PASS_COUNT_TO_FIRST_DIVERGENCE`: `1`
13. `POST_CO_REENTRY_PLAN_COUNT_TO_FIRST_DIVERGENCE`: `1`
14. `POST_CO_REENTRY_FILL_COUNT_TO_FIRST_DIVERGENCE`: `1`
15. `CK_REENTRY_BUY_NEW_BYPASS_RECURRED`: `NO`
16. `ACTIVE_CHURN_PROTECTION_PRESERVED`: `YES`
17. `BUY_ADD_G129_PRESERVED`: `YES_NO_RELEVANT_ADD_DIVERGENCE_OBSERVED`
18. `CAPITAL_COMPETITION_CAUSAL_CHAIN_CONFIRMED`: `YES`
19. `DIRECT_CO_EFFECT_COUNT`: `1`
20. `CASCADE_DIFFERENCE_COUNT`: `1`
21. `UNRELATED_DIFFERENCE_COUNT`: `0`
22. `PRE_DIVERGENCE_DETERMINISM_PASS`: `YES_EXCEPT_EXPECTED_CO_SEMANTIC_FIELD_DIFFERENCES`
23. `PNL_USED_FOR_CO_ACCEPTANCE`: `NO`
24. `CO_ACTUAL_PATH_ACCEPTANCE`: `PASS`
25. `POST_CO_RUN_USEFUL_FOR_REENTRY_NECESSITY_AUDIT`: `YES`
26. `POST_CO_REENTRY_EVENT_POPULATION_FOR_NEXT_AUDIT`: `1: 2022-10-25 83060 TREND_MOMENTUM REENTRY-lineage filled BUY 100`
27. `PRODUCTION_CHANGE_EXECUTED`: `NO`
28. `TARGET_RUN_MUTATED`: `NO`
29. `NEXT_RECOMMENDED_STEP`: perform a READ-ONLY REENTRY necessity / near-term lifecycle audit using the post-CO actual 83060 fill and any later post-CO REENTRY events; do not use PnL to accept/reject CO.
30. `FINAL_JUDGMENT`: `PHASE32_CS_POST_CO_FIRST_DIVERGENCE_CAUSALLY_TRACED_CO_REPAIRED_PRIOR_EXIT_SEMANTICS_CHANGED_83060_REENTRY_TO_PASS_AND_FILLED_NO_UNRELATED_DIVERGENCE_FOUND`

## Final Judgment

`PHASE32_CS_POST_CO_FIRST_DIVERGENCE_CAUSALLY_TRACED_CO_REPAIRED_PRIOR_EXIT_SEMANTICS_CHANGED_83060_REENTRY_TO_PASS_AND_FILLED_NO_UNRELATED_DIVERGENCE_FOUND`

