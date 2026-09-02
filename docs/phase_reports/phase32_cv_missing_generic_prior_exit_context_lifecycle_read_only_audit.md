# Phase32-CV — Missing / Generic Prior EXIT Context Lifecycle READ-ONLY Audit

## Scope

This is a READ-ONLY / SHADOW audit. No Production code, config, runtime state, Pending, Ledger, run artifact, resume, recover, replay, or fresh-run was changed or executed.

Evidence runs:

- Post-CO current-system run: `runtime-test-historical-extended-smoke-20260901T205837445258Z`
- Long-horizon pre-CO supporting run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`

The pre-CO run is used through the Phase32-CN strict-prior reconstruction principle. CO-repairable scalar `EXIT` collapse is not counted as genuinely unknown history.

No later returns, future price, future regime, MFE/MAE, final campaign outcome, or Historical PnL were used.

## Evidence Coverage

Post-CO run state:

- completed business days: `30`
- latest completed date: `2022-11-15`
- run status: `COMPLETED`

Pre-CO run state:

- completed business days: `413`
- latest completed date available: `2024-06-07`
- run status: `HALT` at `2024-06-10:market_refresh`

For population counts, CV preserves the accepted CN/CR comparable cutoff:

- CN/CR population cutoff used for strict-prior reconstruction counts: `2023-09-22`

## Missing Context Classes

`MISSING_CONTEXT_CLASSIFICATION_CONTRACT`:

| Class | Meaning | Production handling |
| --- | --- | --- |
| `RECOVERABLE_PROVENANCE_DEFECT` | Authoritative prior EXIT reason exists upstream but was lost or materialized as generic `EXIT` / `SELL` before REENTRY consumption. | Correctness fail-closed at decision time; repair provenance; never silently convert to BUY_NEW. |
| `GENUINELY_UNRESOLVABLE_HISTORICAL_CONTEXT` | Prior ownership is known, but authoritative semantic EXIT reason cannot be reconstructed from available same-run strict-prior PM / campaign / ledger artifacts under the current taxonomy. | Preserve UNKNOWN/GENERIC lineage; keep short-churn and ordinary BUY safety; may release historical penalty only through strong current PIT independence contract. |
| `COMPLETE_AUTHORITATIVE_CONTEXT` | Prior campaign, EXIT date, semantic reason, reason codes, source PM decision id, and source decision id are available and non-generic. | Normal REENTRY lifecycle. Prior cause is context, not permanent penalty. |

## Population Quantification

Accepted CN comparable population:

- total REENTRY episodes: `267`
- original non-generic prior EXITs under current taxonomy: `229`
- original generic under current taxonomy: `38`
- original missing: `0`

`RECOVERABLE_PROVENANCE_DEFECT_COUNT = 229`

These are not genuinely unknown. CN showed the upstream PM/campaign evidence was non-generic and CO repaired the scalar propagation path.

`GENUINELY_UNRESOLVABLE_CONTEXT_COUNT = 38`

These remain generic under the current taxonomy after strict-prior reconstruction. Some may be human-interpretable but are not machine-authoritative semantic classes today; CV does not invent their prior EXIT reason.

`COMPLETE_AUTHORITATIVE_CONTEXT_COUNT = 229` after CO-style propagation is applied to the recoverable population.

Post-CO early actual-path run through `2022-11-15` shows missing/generic context is not the dominant new condition:

- actual REENTRY episodes observed by direct PC artifact scan: `37`
- TREND_MOMENTUM: `23`
- HARD_STOP: `6`
- GENERIC-class: `8`

The observed GENERIC cases include taxonomy limitations such as `profit_retention_break` and generic `strategy_intelligence_sell_side_evidence_connected`, not only absent source evidence. This supports treating new missing context as exceptional and classifiable, not as a normal permanent-ban state.

`POST_CO_NEW_MISSING_CONTEXT_EXPECTED_FREQUENCY = RARE_EXCEPTION`

Rationale: CO plus campaign/provenance authority should normally materialize non-generic prior EXIT semantics when they exist. New missing context should indicate either a recoverable source/provenance defect, an unsupported taxonomy class, or a genuinely unresolvable historical artifact.

## Permanent Ban Necessity

`PERMANENT_UNKNOWN_CONTEXT_BAN_JUSTIFIED = NO`

Unknown history is not evidence of known danger. A permanent `prior reason unknown -> REVIEW_REQUIRED forever` rule recreates the long-lived prior-ownership suppression that CT/CU are removing. It is justified for recoverable provenance defects until repaired, but not as a permanent Strategy state for genuinely old unrecoverable history.

This does not permit immediate release. Unknown context still needs:

- strict REENTRY lineage;
- no BUY_NEW fallback;
- existing short cooldown;
- repeated unresolved churn guard;
- ordinary BQ / Entry / CQ / downside / safety / broker / CA / capacity gates;
- stronger current PIT independence evidence because HARD_STOP cannot be ruled out.

## Current Opportunity Evidence Set

`UNKNOWN_CONTEXT_CURRENT_OPPORTUNITY_EVIDENCE_SET`:

Existing PIT authorities that can prove current independence without inventing prior reason:

- current candidate / opportunity rank and membership;
- current `runtime_opportunity_score` as diagnostic/supporting only;
- Buy Quality action;
- Entry Admission state/action/sufficiency;
- Continuation Quality;
- Downside Risk;
- trend close over MA20;
- 20D momentum;
- current regime/context;
- corporate-action authority;
- broker/safety status;
- capacity/liquidity;
- current flat position state;
- prior same-symbol exit count / repeated churn state;
- elapsed business days as supporting evidence of stale prior thesis, not a new hard threshold.

`INDEPENDENT_OPPORTUNITY_PROVABLE_WITHOUT_PRIOR_EXIT_REASON = PARTIALLY`

It is partially provable because current PIT evidence can establish strong current opportunity and low current risk, but cannot identify the original failure mode or exclude an old HARD_STOP cause. Therefore Model C can be accepted only with a stricter current-evidence standard than ordinary TREND_MOMENTUM recovery and with no near-term release.

`NEW_UNKNOWN_CONTEXT_TIME_THRESHOLD_REQUIRED = NO`

CV does not authorize a new 30BD / 60BD / 90BD / 120BD threshold. Time may support staleness, but the contract must be evidence-led and must not recreate a blunt long-lived gate.

`UNKNOWN_CONTEXT_SHORT_CHURN_PROTECTION_PRESERVED = YES`

Unknown-context REENTRY must still obey the existing 3BD cooldown, repeated unresolved churn guard, and all ordinary current BUY safety gates.

## HARD_STOP Ambiguity

`UNKNOWN_PRIOR_HARD_STOP_RISK_CONTRACT`:

If prior EXIT reason is genuinely unknown, the system cannot know whether it was HARD_STOP. This uncertainty does not justify permanent blocking, but it does require conservative current-evidence treatment:

- near-term unknown-context REENTRY remains REVIEW_REQUIRED / fail-closed;
- unknown context cannot be released solely by rank or BQ;
- release requires strong current PIT independence across opportunity, BQ, trend, momentum, Entry Admission, CQ/downside, safety, CA, broker, and capacity;
- if any safety/CA/broker/Entry/CQ/downside evidence is missing or non-PASS, keep REVIEW_REQUIRED / fail-closed;
- do not fabricate a prior class and do not reuse TREND_MOMENTUM-specific recovery as if HARD_STOP were impossible.

## Shadow Contract Comparison

`MODEL_P_VS_MODEL_C_COMPARISON`:

| Dimension | Model P: permanent fail-closed | Model C: context decay / current evidence |
| --- | --- | --- |
| Recoverable provenance defect | Correctly blocks until repaired | Correctly blocks until repaired |
| Genuine old unknown context | Blocks forever | Preserves UNKNOWN lineage, may release historical penalty through strong current PIT evidence |
| Short churn | Blocks | Blocks |
| HARD_STOP ambiguity | Safe but overbroad | Conservative stronger evidence required |
| Opportunity universe erosion | Material, permanent | Reduced without falsifying history |
| BUY_NEW fallback risk | None | None if CK-style guard remains |
| Architecture fit | Overly punitive prior ownership | Better fit: history preserved, current opportunity can dominate |

Preferred contract:

- Model P for recoverable provenance defects.
- Model C for genuinely unresolvable old context.

## Unknown-Context Release Characterization

The accepted CN population establishes `38` genuinely generic-source episodes. CV did not find a repository artifact that lists those 38 isolated episode ids separately from CO-recoverable scalar `EXIT` cases, so exact per-symbol Model C release counts for only the 38 cannot be safely asserted beyond the CN aggregate without rebuilding CN's strict-prior reconstruction artifact.

Conservative decision:

- `UNKNOWN_CONTEXT_RELEASE_ELIGIBLE_COUNT = INSUFFICIENT_ISOLATED_EVIDENCE_FOR_EXACT_COUNT`
- `UNKNOWN_CONTEXT_RELEASE_AMBIGUOUS_COUNT = 38_POTENTIAL_GENUINE_UNKNOWN_CONTEXT_EPISODES`
- `UNKNOWN_CONTEXT_FALSE_RELEASE_COUNT = 0_UNDER_TARGET_CONTRACT_BY_DEFINITION`
- `UNKNOWN_CONTEXT_HIGH_CONFIDENCE_RELEASE_CASE_COUNT = 0_CONFIRMED_FROM_ISOLATED_GENUINE_UNKNOWN_POPULATION`

Supplemental direct PC scan through the CN cutoff found many apparent generic/scalar-insufficient rows with strong current PIT evidence, but those rows mix CO-recoverable provenance defects with genuinely generic historical context. Because the task explicitly forbids counting CO-repairable generic `EXIT` as genuinely unknown, this scan is not used as the final release count.

Implication: the contract question is resolved, but a future implementation should add fixtures that explicitly construct genuine unknown-context cases rather than relying on old scalar artifacts.

## Operational Contract

`PROVENANCE_DEFECT_VS_UNKNOWN_HISTORY_OPERATIONAL_CONTRACT`:

| Situation | Correctness status | Action |
| --- | --- | --- |
| authoritative prior EXIT semantic evidence exists upstream but is lost | correctness defect | fail closed, repair provenance, no BUY_NEW fallback |
| prior context is missing in a post-CO normal path where it should exist | correctness defect or taxonomy gap | fail closed and investigate |
| prior ownership known, but old semantic context genuinely unrecoverable | Strategy lifecycle state, not permanent correctness defect | preserve UNKNOWN REENTRY lineage; apply short churn, strong current PIT independence, and ordinary BUY authority |
| current PIT evidence weak/ambiguous | not eligible | REVIEW_REQUIRED / fail-closed |
| current PIT evidence strongly independent and all safety gates pass | eligible for neutral capital competition | no bonus, no penalty, still REENTRY-lineage |

`UNKNOWN_CONTEXT_BUY_NEW_FALLBACK_ALLOWED = NO`

Even when released, the symbol remains prior-owned / REENTRY-lineage. History must not be falsified.

`UNKNOWN_CONTEXT_CAPITAL_COMPETITION_CONTRACT`:

If the accepted release contract passes:

- no REENTRY bonus;
- no REENTRY discount;
- no NEW bonus;
- ordinary current marginal opportunity competition;
- new campaign identity only if accepted/fill occurs after a full prior EXIT;
- prior unknown lineage remains auditable.

## CU Amendment

`CU_MISSING_CONTEXT_CONTRACT_AMENDMENT`:

Amend CU's missing-context rule as follows:

1. Recoverable missing authority remains fail-closed and is a correctness defect.
2. Genuinely unresolvable old context becomes `REENTRY_UNKNOWN_PRIOR_CONTEXT`, not a permanent ban.
3. `REENTRY_UNKNOWN_PRIOR_CONTEXT` preserves lineage and forbids BUY_NEW fallback.
4. Short churn, repeated unresolved churn, and all ordinary BUY safety gates remain mandatory.
5. Current independent opportunity evidence may release the historical penalty only under a stronger unknown-context standard that accounts for unknown HARD_STOP risk.
6. No new model, feature, score, or Historical-return-tuned threshold is authorized.

## Architecture Simplicity

`NEW_COMPONENT_REQUIRED = NO`

`NEW_MODEL_REQUIRED = NO`

`NEW_FEATURE_REQUIRED = NO`

Existing REENTRY lineage, current BUY authority, churn authority, and current PIT evidence are enough to express the contract. Future implementation should modify PC semantic eligibility / recovery composition, not create a new classifier service.

`OUTCOME_DATA_USED_TO_DEFINE_UNKNOWN_CONTEXT_POLICY = NO`

## Production Readiness

`CU_PRODUCTION_IMPLEMENTATION_BLOCKED_BY_MISSING_CONTEXT = NO_CONTRACT_RESOLVED`

The missing/generic context question no longer blocks CU Production cleanup. The implementation must keep recoverable provenance defects fail-closed while allowing genuinely unrecoverable old context to use an UNKNOWN lineage lifecycle with stronger current-evidence release. Exact release counts for the old genuine-unknown population are not required for correctness implementation and should not be tuned from PnL.

## Required Final Answers

1. `LATEST_POST_CO_COMPLETED_DATE_USED`: `2022-11-15`
2. `LATEST_PRE_CO_COMPLETED_DATE_USED`: `2024-06-07` available; `2023-09-22` used for CN/CR comparable population counts.
3. `MISSING_CONTEXT_CLASSIFICATION_CONTRACT`: three classes: recoverable provenance defect, genuinely unresolvable historical context, complete authoritative context.
4. `RECOVERABLE_PROVENANCE_DEFECT_COUNT`: `229`
5. `GENUINELY_UNRESOLVABLE_CONTEXT_COUNT`: `38`
6. `POST_CO_NEW_MISSING_CONTEXT_EXPECTED_FREQUENCY`: `RARE_EXCEPTION`
7. `PERMANENT_UNKNOWN_CONTEXT_BAN_JUSTIFIED`: `NO`
8. `UNKNOWN_CONTEXT_CURRENT_OPPORTUNITY_EVIDENCE_SET`: current rank/opportunity, BQ, Entry Admission, CQ, downside, trend, momentum, CA, broker/safety, capacity, regime/context, current flat state, churn history, elapsed time as supporting evidence.
9. `INDEPENDENT_OPPORTUNITY_PROVABLE_WITHOUT_PRIOR_EXIT_REASON`: `PARTIALLY`
10. `NEW_UNKNOWN_CONTEXT_TIME_THRESHOLD_REQUIRED`: `NO`
11. `UNKNOWN_CONTEXT_SHORT_CHURN_PROTECTION_PRESERVED`: `YES`
12. `UNKNOWN_PRIOR_HARD_STOP_RISK_CONTRACT`: no permanent block; require conservative strong current PIT evidence and keep near-term/missing safety fail-closed.
13. `MODEL_P_VS_MODEL_C_COMPARISON`: Model P for recoverable defects; Model C for genuinely unresolvable old context.
14. `UNKNOWN_CONTEXT_RELEASE_ELIGIBLE_COUNT`: `INSUFFICIENT_ISOLATED_EVIDENCE_FOR_EXACT_COUNT`
15. `UNKNOWN_CONTEXT_RELEASE_AMBIGUOUS_COUNT`: `38_POTENTIAL_GENUINE_UNKNOWN_CONTEXT_EPISODES`
16. `UNKNOWN_CONTEXT_FALSE_RELEASE_COUNT`: `0_UNDER_TARGET_CONTRACT_BY_DEFINITION`
17. `UNKNOWN_CONTEXT_HIGH_CONFIDENCE_RELEASE_CASE_COUNT`: `0_CONFIRMED_FROM_ISOLATED_GENUINE_UNKNOWN_POPULATION`
18. `PROVENANCE_DEFECT_VS_UNKNOWN_HISTORY_OPERATIONAL_CONTRACT`: recoverable defect fail-closed/repair; genuine unknown is lifecycle state, not permanent correctness defect.
19. `UNKNOWN_CONTEXT_BUY_NEW_FALLBACK_ALLOWED`: `NO`
20. `UNKNOWN_CONTEXT_CAPITAL_COMPETITION_CONTRACT`: neutral current marginal opportunity competition after accepted release; lineage preserved.
21. `CU_MISSING_CONTEXT_CONTRACT_AMENDMENT`: distinguish recoverable defect from genuine unknown; genuine unknown may release historical penalty via stronger current PIT independence while preserving lineage and short churn.
22. `NEW_COMPONENT_REQUIRED`: `NO`
23. `NEW_MODEL_REQUIRED`: `NO`
24. `NEW_FEATURE_REQUIRED`: `NO`
25. `OUTCOME_DATA_USED_TO_DEFINE_UNKNOWN_CONTEXT_POLICY`: `NO`
26. `CU_PRODUCTION_IMPLEMENTATION_BLOCKED_BY_MISSING_CONTEXT`: `NO_CONTRACT_RESOLVED`
27. `PRODUCTION_CHANGE_EXECUTED`: `NO`
28. `TARGET_RUN_MUTATED`: `NO`
29. `NEXT_RECOMMENDED_STEP`: proceed to CU Production cleanup with the CV amendment: implement residual REENTRY protection plus `REENTRY_UNKNOWN_PRIOR_CONTEXT` handling, add explicit fixtures for recoverable defect vs genuine unknown, and keep all changes focused inside existing PC semantic authority.
30. `FINAL_JUDGMENT`: `PHASE32_CV_UNKNOWN_PRIOR_CONTEXT_PERMANENT_BAN_NOT_JUSTIFIED_CONTEXT_DECAY_CONTRACT_RESOLVED_READ_ONLY_NO_MUTATION`

## Final Judgment

`PHASE32_CV_UNKNOWN_PRIOR_CONTEXT_PERMANENT_BAN_NOT_JUSTIFIED_CONTEXT_DECAY_CONTRACT_RESOLVED_READ_ONLY_NO_MUTATION`
