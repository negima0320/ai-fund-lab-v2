# Phase32-CQ — REENTRY Time + Renewed PIT Evidence NEW-Equivalent Lifecycle SHADOW Contract Design

## Scope

This phase designs and validates a SHADOW-only contract for Phase32-CP Design B:

`REENTRY lineage remains permanent, but the extra prior-ownership decision penalty can expire when the prior campaign is temporally stale and current PIT evidence proves a renewed independent opportunity.`

- Primary evidence run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Latest completed date used: `2023-09-22`
- Evidence window: `2022-10-03` through `2023-09-22`
- Population inherited from CM/CN/CP: 5,376 REENTRY rows and 267 REENTRY episodes.

The primary run is pre-CO, so old generic scalar `EXIT` artifacts were not treated as post-CO acceptance evidence. Semantic prior EXIT class was interpreted under the Phase32-CN strict-prior SHADOW reconstruction principle: use authoritative same-run prior PM/campaign reason evidence when the PC scalar collapsed to `EXIT`; do not rewrite old artifacts.

No Production code, config, Strategy semantics, thresholds, cooldowns, models, features, PC/PS, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run was changed or executed.

## References Preserved

Phase32-CM:

- 267 REENTRY episodes.
- 0 current REENTRY PASS / plans / fills.
- Primary post-churn block: current rank/requalification.

Phase32-CN:

- 267/267 prior EXITs reconstructable.
- 229 non-generic prior EXITs under current taxonomy.
- Restored semantics produce 25 SHADOW recovery-PASS episodes.
- 6 of those are long-delay `>60BD` cases.
- Remaining bottleneck is mixed provenance and requalification.

Phase32-CO:

- Repaired only prior EXIT semantic propagation.
- Did not change cooldown, rank/requalification, BQ, BUY_NEW, BUY_ADD, or PC/PS.

Phase32-CP:

- Permanent lineage is desirable.
- Permanent decision penalty is not.
- Time-only reset is not supported.
- Time + renewed PIT evidence is supported.
- Literal BUY_NEW reclassification is unnecessary.
- Universe erosion is material.
- No new component/model/feature is required.

## Proposed Lifecycle State Contract

`PROPOSED_REENTRY_LIFECYCLE_STATE_CONTRACT`:

| State | Meaning | Capital treatment |
| --- | --- | --- |
| `ACTIVE_REENTRY_PROTECTION` | Prior EXIT remains temporally/economically close. Immediate churn, cooldown, or unresolved same-episode rebuy risk remains plausible. | Existing strict REENTRY constraints apply. No NEW-equivalent treatment. |
| `REENTRY_REQUALIFICATION` | Prior campaign is aging, but current PIT evidence has not yet proven an independent renewed opportunity. | Still constrained as REENTRY. No stale-age-only release. |
| `REENTRY_NEW_EQUIVALENT_ELIGIBLE` | Prior campaign lineage remains auditable, but temporal staleness plus current PIT evidence proves a new independent opportunity. | Enter current capital competition on NEW-equivalent terms without a REENTRY-only rank penalty or bonus. |

This is a semantic lifecycle inside the existing REENTRY authority, not a new component and not a literal `BUY_NEW` relabel.

## Temporal Staleness Contract

`TEMPORAL_STALENESS_CONTRACT`:

NEW-equivalent treatment may not be considered until the prior full EXIT is beyond the short-term churn and transitional-thesis window. For SHADOW CQ, the minimum staleness floor is:

`business_days_since_exit > 60`

This was not optimized from outcome. It is a semantic safety floor derived from CP's temporal buckets:

- 0-3BD is immediate churn.
- 4-20BD remains plausibly same-thesis continuation.
- 21-60BD is transitional and still often carries unresolved prior-thesis evidence.
- >60BD is where prior campaign relevance is materially stale enough that current PIT evidence can dominate, but age alone is still insufficient.

`TEMPORAL_STALENESS_REQUIRES_FIXED_MINIMUM = YES`

The fixed minimum is only a precondition. It does not by itself create eligibility.

`RESET_DAY_OPTIMIZED_FROM_HISTORICAL_OUTCOME = NO`

## Minimal Renewed PIT Evidence Set

`MINIMAL_RENEWED_PIT_EVIDENCE_SET`:

The narrowest existing evidence set sufficient for NEW-equivalent SHADOW treatment is:

- strict-prior prior campaign id and prior EXIT date;
- non-generic prior EXIT semantic class, reconstructed from PM/campaign authority when old PC scalar is generic;
- elapsed business days since EXIT above the staleness floor;
- cooldown/churn pass;
- current candidate/rank evidence sufficient for NEW-equivalent competition, not stricter REENTRY-only top-10 requalification;
- BQ action in `REDUCED_ALLOCATION_ONLY` or `FULL_ALLOCATION_ELIGIBLE`;
- current trend recovery: close/MA trend evidence supportive;
- current momentum recovery: non-negative 20D momentum;
- Entry Admission not `BUY_WAIT`, `REJECT`, `REVIEW_REQUIRED`, or `NO_ADD`;
- Continuation Quality and Downside Risk acceptable when provided;
- Corporate Action, broker, safety, and capacity non-blocking.

This answers why the case is a new opportunity rather than the old failed thesis returning: the prior campaign is stale, and current rank/BQ/trend/momentum/admission/risk evidence independently re-establishes forward opportunity quality at decision time.

## Prior EXIT Class Lifecycle Contract

`EXIT_CLASS_LIFECYCLE_CONTRACT`:

| Prior EXIT class | CQ lifecycle behavior |
| --- | --- |
| `TREND_MOMENTUM` | Normal temporal decay candidate. After >60BD, if current rank/BQ/trend/momentum and risk/admission evidence pass, old trend breakdown stops imposing a REENTRY-only penalty. |
| `HARD_STOP` | More conservative. Time alone never resets it. CQ requires exceptionally strong new-thesis evidence: >120BD, full BQ eligibility, top-rank current opportunity, trend recovery, and momentum recovery. Current population produced no HARD_STOP reset. |
| `GENERIC` / missing | Remains constrained / review-required. CQ does not fabricate missing semantic authority. Old age plus strong current evidence is not enough without Architecture support. |
| `REVERSAL` | Requires explicit Entry Admission normalization and adequate direct population before promotion. CQ leaves it constrained. |
| `PORTFOLIO_COMPETITION` | Requires renewed relative opportunity strength; insufficient direct population here. CQ leaves it constrained. |
| `CORPORATE_ACTION` | Requires resolved CA authority and class-specific validation; insufficient direct population here. CQ leaves it constrained. |
| `ADMINISTRATIVE` | Requires explicit administrative-return contract; insufficient direct population here. CQ leaves it constrained. |

## SHADOW Classifier

The CQ SHADOW classifier was applied to all 267 REENTRY episodes.

For an episode to become `REENTRY_NEW_EQUIVALENT_ELIGIBLE`, at least one strict-prior row in the episode had to satisfy:

1. not active churn and not cooldown-blocked;
2. `business_days_since_exit > 60`;
3. non-generic prior EXIT class;
4. no CA / broker / safety / Entry Admission / CQ / downside block;
5. BQ eligible;
6. class-specific renewed PIT evidence:
   - `TREND_MOMENTUM`: rank within current NEW-equivalent quality band, trend >= 1.0, momentum >= 0.0;
   - `HARD_STOP`: stricter new-thesis requirements; no observed HARD_STOP case passed;
   - other classes remain constrained due insufficient class-specific population.

Episode result:

| Proposed state | Episodes |
| --- | ---: |
| `REENTRY_NEW_EQUIVALENT_ELIGIBLE` | 14 |
| `ACTIVE_REENTRY_PROTECTION` | 107 |
| `REENTRY_REQUALIFICATION` | 146 |
| Total | 267 |

`SHADOW_LIFECYCLE_POPULATION_COMPLETE = YES`

## Safety Controls

Negative control results:

| Safety control | Escape count |
| --- | ---: |
| Immediate churn / cooldown escape | 0 |
| Weak stale symbol escape | 0 |
| HARD_STOP false reset | 0 |

`IMMEDIATE_CHURN_ESCAPE_COUNT = 0`

`WEAK_STALE_ESCAPE_COUNT = 0`

`HARD_STOP_FALSE_RESET_COUNT = 0`

Blocked reasons among non-eligible episodes:

| Reason | Episodes |
| --- | ---: |
| temporal staleness floor not met | 118 |
| active churn or cooldown | 107 |
| renewed trend/momentum/rank not sufficient | 12 |
| generic or missing prior EXIT context | 10 |
| BQ not eligible | 3 |
| hard-stop new thesis not sufficient | 2 |
| Entry Admission block | 1 |

## Positive Controls

`HIGH_CONFIDENCE_NEW_EQUIVALENT_CASE_COUNT = 14`

All 14 positive-control cases are `TREND_MOMENTUM` prior EXITs with >60BD staleness, BQ eligible, supportive trend, non-negative momentum, and current rank inside the NEW-equivalent quality band.

Representative cases:

| Date | Symbol | Elapsed BD | Prior class | Rank | Trend | Momentum | BQ | Regime | Reason |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 2022-12-30 | 83060 | 62 | `TREND_MOMENTUM` | 16 | 1.097673 | 0.203466 | `REDUCED_ALLOCATION_ONLY` | BEAR | stale trend/momentum recovery with current rank support |
| 2023-01-13 | 59860 | 63 | `TREND_MOMENTUM` | 20 | 1.073411 | 0.110638 | `REDUCED_ALLOCATION_ONLY` | BEAR | stale trend/momentum recovery with current rank support |
| 2023-03-06 | 73590 | 101 | `TREND_MOMENTUM` | 20 | 1.562344 | 1.177251 | `REDUCED_ALLOCATION_ONLY` | BULL | stale trend/momentum recovery with current rank support |
| 2023-03-09 | 65500 | 96 | `TREND_MOMENTUM` | 19 | 1.646612 | 0.699346 | `REDUCED_ALLOCATION_ONLY` | BULL | stale trend/momentum recovery with current rank support |
| 2023-04-20 | 76470 | 61 | `TREND_MOMENTUM` | 12 | 1.021611 | 0.040000 | `REDUCED_ALLOCATION_ONLY` | BULL | stale trend/momentum recovery with current rank support |
| 2023-06-13 | 99840 | 124 | `TREND_MOMENTUM` | 17 | 1.129735 | 0.262202 | `FULL_ALLOCATION_ELIGIBLE` | BULL | stale trend/momentum recovery with current rank support |
| 2023-08-31 | 61730 | 77 | `TREND_MOMENTUM` | 20 | 2.222602 | 1.795699 | `REDUCED_ALLOCATION_ONLY` | RECOVERY | stale trend/momentum recovery with current rank support |
| 2023-09-20 | 53800 | 189 | `TREND_MOMENTUM` | 19 | 1.047248 | 0.278751 | `REDUCED_ALLOCATION_ONLY` | BULL | stale trend/momentum recovery with current rank support |

## CN Long-Delay Six Coverage

`CN_LONG_DELAY_SIX_COVERAGE = 6/6_COVERED`

The 6 CN long-delay SHADOW recovery-PASS cases satisfy CQ because they already pass the existing recovery contract after restored prior EXIT semantics and are beyond the >60BD staleness floor. CQ is broader than CN recovery PASS because CQ removes the permanent REENTRY-only rank/requalification penalty once temporal staleness and renewed PIT evidence are satisfied. CQ is still stricter than CP's broad 74-case population because generic, hard-stop-without-new-thesis, weak, and insufficient-rank/momentum cases remain constrained.

## CP 74 Broad Population

CP identified 74 broad `>=61BD` clear/partial renewed-PIT cases. CQ does not automatically accept all 74.

| CP74 classification | Count |
| --- | ---: |
| NEW-equivalent eligible | 14 |
| Remain constrained | 60 |
| Ambiguous | 0 |

`CP74_NEW_EQUIVALENT_ELIGIBLE_COUNT = 14`

`CP74_REMAIN_CONSTRAINED_COUNT = 60`

`CP74_AMBIGUOUS_COUNT = 0`

Main reasons the remaining 60 stay constrained:

- hard-stop new thesis not sufficient;
- trend/momentum/rank not jointly sufficient;
- generic or missing prior EXIT context;
- temporal-staleness evidence not satisfied at the actual strongest row;
- one residual active churn/cooldown case.

## Rank / Requalification Treatment

`NEW_EQUIVALENT_RANK_TREATMENT = OPTION_2`

Once temporal staleness plus renewed PIT evidence proves an independent current opportunity, the old REENTRY-specific rank/requalification penalty expires. The security should enter current capital competition under the same current opportunity-quality semantics as a genuine NEW candidate.

This does not mean rank is ignored. It means rank is used as current opportunity evidence and capital-competition input, not as a permanent REENTRY-only extra hurdle. This is semantically consistent with Architecture: eligible REENTRY competes with no permanent discount or bonus.

## Capital Competition Contract

`NEW_EQUIVALENT_CAPITAL_COMPETITION_CONTRACT`:

- no REENTRY bonus;
- no NEW bonus;
- no ADD bonus;
- no forced allocation;
- historical ownership lineage must not alter the current opportunity score;
- current marginal opportunity is compared through existing capital-competition authority;
- capital allocation remains subject to PC/PS/lot/cash/budget/runtime contracts;
- if accepted after prior full EXIT, campaign authority creates a new campaign while preserving prior-campaign lineage.

## Label and BUY_ADD Boundaries

`BUY_NEW_MISCLASSIFICATION_REQUIRED = NO`

The lifecycle remains REENTRY lineage with NEW-equivalent capital treatment after lifecycle PASS. It does not falsify the action label.

`BUY_ADD_G129_SEMANTICS_PRESERVED = YES`

Design B does not touch current-position detection, BUY_ADD classification, PM ADD intent, PC/PS ADD materialization, Submit quantity authority, or G129 order-increment semantics.

## Universe Release

`PERMANENT_REENTRY_UNIVERSE_RELEASED_BY_DESIGN_B`:

| Metric | Count |
| --- | ---: |
| REENTRY rows inspected | 5,376 |
| REENTRY episodes inspected | 267 |
| NEW-equivalent eligible episodes | 14 |
| Unique symbols released | 14 |
| REENTRY rows that would carry lifecycle release | 196 |
| Days with at least one released REENTRY row | 143 of 239 |
| Average daily released share of REENTRY rows | 3.1% |

The semantic release is intentionally narrow. It addresses permanent-penalty structure without flooding the system with all old prior-owned symbols.

## False-Reset Risk

`FALSE_RESET_RISK_CLASSIFICATION = CONTROLLED_MODERATE`

Risk remains in:

- old trend/momentum exits with rank just inside the NEW-equivalent quality band but still only reduced BQ;
- symbols that show one strong rebound while the broader thesis remains unresolved;
- generic prior EXIT context that could tempt age-only release;
- hard-stop exits where current evidence is not strong enough to define a new thesis.

CQ controls these by requiring non-generic prior context, >60BD temporal staleness, BQ eligibility, trend and momentum recovery, Entry Admission/CQ/downside non-blocking, and stricter HARD_STOP handling.

## Architecture Placement

`NARROWEST_IMPLEMENTATION_BOUNDARY`:

The lifecycle belongs inside existing Portfolio Construction REENTRY semantic eligibility and recovery materialization:

- `portfolio_construction._semantic_reentry_evidence`
- `portfolio_construction._reentry_recovery_evidence`
- `portfolio_construction._canonical_reentry_semantic_eligibility`
- downstream capital-competition materialization where eligible REENTRY is treated as NEW-equivalent without relabeling.

No standalone REENTRY lifecycle service/module is needed.

## Implementation-Ready Contract Draft

`IMPLEMENTATION_READY_CONTRACT_COMPLETE = YES`

Inputs:

- current business date;
- strict-prior prior exit business date;
- strict-prior prior campaign id;
- prior EXIT semantic reason/class/codes and PM source ids;
- current rank/opportunity evidence;
- BQ decision;
- trend and momentum evidence;
- Entry Admission;
- CQ/downside;
- CA/broker/safety/capacity evidence;
- current-position status.

Authority:

- PC owns REENTRY semantic eligibility and capital-competition materialization.
- PM/campaign artifacts own prior EXIT semantic provenance.
- Existing Candidate/BQ/Strategy Intelligence artifacts own current PIT evidence.

State transition:

1. If current position exists, not REENTRY; BUY_ADD/HOLD/SELL path remains unchanged.
2. If no strict-prior full EXIT, normal BUY_NEW path remains unchanged.
3. If strict-prior full EXIT exists, classify as REENTRY lineage.
4. If cooldown/churn active, `ACTIVE_REENTRY_PROTECTION`.
5. If temporal staleness not satisfied, `REENTRY_REQUALIFICATION`.
6. If prior context is generic/missing, stay constrained/review-required.
7. If class-specific renewed PIT evidence passes, `REENTRY_NEW_EQUIVALENT_ELIGIBLE`.
8. Otherwise stay `REENTRY_REQUALIFICATION`.

Negative controls:

- immediate churn cannot escape;
- weak stale symbols cannot escape;
- HARD_STOP cannot reset without stronger new-thesis evidence;
- generic/missing prior context cannot be fabricated;
- CA/broker/safety/admission blocks remain blocking.

Positive controls:

- stale `TREND_MOMENTUM` prior EXIT with restored context, current rank support, BQ eligibility, trend recovery, momentum recovery, and acceptable CQ/downside can become NEW-equivalent eligible.

Lineage behavior:

- semantic label remains REENTRY lineage;
- prior campaign id/reason/fills remain auditable;
- accepted/fill path creates a new campaign under existing campaign authority after full prior EXIT.

Capital treatment:

- lifecycle PASS removes only the extra prior-ownership penalty;
- capital competition remains normal and may still allocate zero.

Fail-closed invariants:

- malformed or stale evidence fails closed;
- missing prior campaign identity fails closed/review;
- future information is forbidden;
- old run artifacts are never rewritten;
- Production acceptance requires post-CO actual-path evidence.

## Production Readiness

`PRODUCTION_IMPLEMENTATION_READINESS = YES_AFTER_CO_ACTUAL_PATH_ACCEPTANCE`

The SHADOW contract is narrow enough for a future Production implementation after a user-operated post-CO actual-path run confirms prior EXIT semantic materialization. CQ itself does not execute that implementation.

`OUTCOME_DATA_USED_TO_DEFINE_CONTRACT = NO`

No later PnL, future return, future regime, final campaign outcome, selected/bought outcome, or threshold sweep was used to define the contract.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-09-22`
2. `PROPOSED_REENTRY_LIFECYCLE_STATE_CONTRACT`: `ACTIVE_REENTRY_PROTECTION -> REENTRY_REQUALIFICATION -> REENTRY_NEW_EQUIVALENT_ELIGIBLE`
3. `RESET_DAY_OPTIMIZED_FROM_HISTORICAL_OUTCOME`: `NO`
4. `TEMPORAL_STALENESS_CONTRACT`: `business_days_since_exit > 60` as SHADOW minimum plus renewed PIT evidence; age alone is insufficient.
5. `TEMPORAL_STALENESS_REQUIRES_FIXED_MINIMUM`: `YES`
6. `MINIMAL_RENEWED_PIT_EVIDENCE_SET`: strict-prior lineage/context, age floor, churn pass, rank/current opportunity quality, BQ eligible, trend recovery, momentum recovery, Entry Admission/CQ/downside/CA/broker/safety non-blocking.
7. `EXIT_CLASS_LIFECYCLE_CONTRACT`: trend/momentum decays normally; hard-stop requires stricter new thesis; generic/missing remains constrained; other classes need more direct population.
8. `SHADOW_LIFECYCLE_POPULATION_COMPLETE`: `YES`
9. `IMMEDIATE_CHURN_ESCAPE_COUNT`: `0`
10. `WEAK_STALE_ESCAPE_COUNT`: `0`
11. `HARD_STOP_FALSE_RESET_COUNT`: `0`
12. `HIGH_CONFIDENCE_NEW_EQUIVALENT_CASE_COUNT`: `14`
13. `CN_LONG_DELAY_SIX_COVERAGE`: `6/6_COVERED`
14. `CP74_NEW_EQUIVALENT_ELIGIBLE_COUNT`: `14`
15. `CP74_REMAIN_CONSTRAINED_COUNT`: `60`
16. `CP74_AMBIGUOUS_COUNT`: `0`
17. `NEW_EQUIVALENT_RANK_TREATMENT`: `OPTION_2`
18. `NEW_EQUIVALENT_CAPITAL_COMPETITION_CONTRACT`: no bonus, no forced allocation, normal current capital competition, lineage preserved.
19. `BUY_NEW_MISCLASSIFICATION_REQUIRED`: `NO`
20. `BUY_ADD_G129_SEMANTICS_PRESERVED`: `YES`
21. `PERMANENT_REENTRY_UNIVERSE_RELEASED_BY_DESIGN_B`: `14 episodes / 14 symbols / 196 rows / 143 days with release / 3.1% average daily REENTRY-row release`
22. `FALSE_RESET_RISK_CLASSIFICATION`: `CONTROLLED_MODERATE`
23. `OUTCOME_DATA_USED_TO_DEFINE_CONTRACT`: `NO`
24. `NARROWEST_IMPLEMENTATION_BOUNDARY`: existing PC REENTRY semantic eligibility, recovery evidence, and capital-competition materialization.
25. `IMPLEMENTATION_READY_CONTRACT_COMPLETE`: `YES`
26. `NEW_COMPONENT_REQUIRED`: `NO`
27. `NEW_MODEL_REQUIRED`: `NO`
28. `NEW_FEATURE_REQUIRED`: `NO`
29. `PRODUCTION_IMPLEMENTATION_READINESS`: `YES_AFTER_CO_ACTUAL_PATH_ACCEPTANCE`
30. `PRODUCTION_CHANGE_EXECUTED`: `NO`
31. `TARGET_RUN_MUTATED`: `NO`
32. `NEXT_RECOMMENDED_STEP`: after post-CO actual-path acceptance, implement the narrow Design B lifecycle in existing PC REENTRY semantic eligibility with focused tests for the 14 positive controls and the negative controls above.
33. `FINAL_JUDGMENT`: `PHASE32_CQ_DESIGN_B_REENTRY_TIME_PLUS_RENEWED_PIT_NEW_EQUIVALENT_LIFECYCLE_SHADOW_CONTRACT_ACCEPTED_PRODUCTION_READY_AFTER_CO_ACTUAL_PATH_ACCEPTANCE`

## Final Judgment

`PHASE32_CQ_DESIGN_B_REENTRY_TIME_PLUS_RENEWED_PIT_NEW_EQUIVALENT_LIFECYCLE_SHADOW_CONTRACT_ACCEPTED_PRODUCTION_READY_AFTER_CO_ACTUAL_PATH_ACCEPTANCE`

