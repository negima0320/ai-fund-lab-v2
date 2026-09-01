# Phase32-CP — REENTRY Temporal Lifecycle / Prior-Campaign Relevance READ-ONLY Audit

## Scope

This is a READ-ONLY audit of REENTRY temporal lifecycle semantics.

- Baseline run: `runtime-test-historical-extended-smoke-20260831T234344371102Z`
- Latest completed date used: `2023-09-22`
- Evidence window: `2022-10-03` through `2023-09-22`
- Prior references read: Phase32-CM, Phase32-CN, Phase32-CO, Strategy Architecture / Strategy Intelligence SoT, and Dual-Path Capital Competition SoT.

No Production code, Strategy semantics, thresholds, cooldowns, models, features, PC/PS, Runtime state, Pending, Ledger, resume, recover, replay, or fresh-run was changed or executed.

## Prior Conclusions Preserved

Phase32-CM established:

- 5,376 raw REENTRY rows.
- 267 REENTRY episodes.
- 0 REENTRY semantic PASS rows.
- 0 REENTRY runtime plans / fills.
- The first observed block is mostly current rank/requalification, not BQ, CA, capacity, CQ, or downside.
- Long-lived REENTRY suppression exists after active churn should have decayed.

Phase32-CN established:

- Strict-prior EXIT semantics can be reconstructed for all 267 episodes.
- 229/267 original prior EXITs were non-generic under the current taxonomy.
- Restoring semantic prior EXIT context in SHADOW raises recovery PASS from 0 to 25.
- 6 SHADOW PASS episodes are long-delay `>60BD` cases.
- Provenance repair is justified, but requalification tuning was not justified by CN alone.

Phase32-CO repaired only semantic prior EXIT provenance. CO did not change cooldown, rank, BQ, requalification, BUY_NEW, BUY_ADD, PC/PS, or capital allocation.

## Intended Temporal Philosophy

Architecture does not define REENTRY as a permanent ban or permanent discount. The current SoT says REENTRY should distinguish genuine recovery from churn / unresolved continuation. Prior campaign identity and prior EXIT cause must be retained, but once REENTRY is eligible it should enter current capital competition without permanent discount or bonus merely because it is REENTRY.

`REENTRY_TEMPORAL_PHILOSOPHY_CONTRACT`:

Short-term immediate rebuy must be controlled; the same unresolved failed thesis should not be repeatedly re-entered; prior EXIT semantics should matter while they remain economically relevant; historical campaign lineage remains permanently auditable; historical ownership alone must not permanently contaminate future independent opportunities when current PIT evidence shows a genuinely renewed opportunity.

## Temporal Population

Episodes were collapsed by symbol plus strict-prior closed-campaign lineage. The bucket below uses each episode's maximum observed elapsed business days by the `2023-09-22` cutoff, because this audit asks whether prior ownership continues to bind as time passes. This reproduces the CM aggregate shape and splits CM's `>60BD` population into `61-120BD` and `>120BD`.

| Elapsed BD bucket | Episodes | Lineage complete | Active churn first observed | PIT strength | Prior EXIT class | Main current block |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 0-3 | 33 | 30 | 33 | 11 partial, 22 weak | 26 trend/momentum, 6 generic, 1 hard-stop | churn 27; rank 6 |
| 4-10 | 64 | 62 | 62 | 1 clear, 36 partial, 27 weak | 43 trend/momentum, 12 generic, 9 hard-stop | rank 62; prior context 1; BQ 1 |
| 11-20 | 30 | 27 | 28 | 22 partial, 8 weak | 14 trend/momentum, 12 generic, 4 hard-stop | rank 26; prior context 4 |
| 21-40 | 24 | 24 | 18 | 17 partial, 7 weak | 12 trend/momentum, 8 hard-stop, 4 generic | rank 24 |
| 41-60 | 19 | 17 | 18 | 1 clear, 16 partial, 2 weak | 11 trend/momentum, 7 generic, 1 hard-stop | rank 18; prior context 1 |
| 61-120 | 44 | 39 | 35 | 2 clear, 31 partial, 11 weak | 17 trend/momentum, 18 generic, 9 hard-stop | rank 41; prior context 2; BQ 1 |
| >120 | 53 | 52 | 37 | 3 clear, 38 partial, 12 weak | 29 trend/momentum, 16 generic, 8 hard-stop | rank 47; trend 3; prior context 2; repeated churn 1 |

`TEMPORAL_BUCKET_POPULATION_COMPLETE = YES`

## Same Episode vs New Opportunity

Classification was based only on decision-time PIT evidence already materialized in current artifacts: elapsed business days, active churn status, prior EXIT class, rank/requalification, BQ action, trend, momentum, Entry Admission, and current market regime. No future return, final campaign outcome, or Historical PnL was used.

| Class | Count | Interpretation |
| --- | ---: | --- |
| `SAME_SHORT_TERM_EPISODE` | 33 high-confidence immediate cases; 27 clear active-churn blocks | Immediate post-EXIT reappearance where churn control is clearly justified. |
| `LIKELY_SAME_THESIS_CONTINUATION` | 65 conservative weak / unresolved cases through 60BD | Current PIT evidence does not sufficiently show a renewed independent opportunity. |
| `TRANSITIONAL` | 95 | Some renewed evidence appears, but prior thesis relevance is not clearly stale enough or current evidence is only partial. |
| `NEWLY_FORMED_OPPORTUNITY` | 74 broad PIT-classified long-delay cases; 6 high-confidence CN SHADOW PASS cases | Prior campaign is old (`>=61BD`) and current PIT evidence is clear or partial renewed strength. The strictest subset already passes existing recovery logic after semantic restoration. |
| `INSUFFICIENT_EVIDENCE` | 0 for bucket assignment; some rows still have generic prior context | Materialized PIT fields were sufficient for this audit classification. |

`NEWLY_FORMED_OPPORTUNITY_COUNT = 74` broad PIT-classified `>=61BD` cases, with `6` high-confidence `>60BD` CN SHADOW recovery-PASS cases.

## Temporal Decay of Prior EXIT Relevance

Prior EXIT relevance decays with time, but not uniformly by class.

- `TREND_MOMENTUM`: strong temporal decay support. A trend/momentum EXIT remains relevant in the near term, but after 61/120+ BD current trend, momentum, rank, and BQ should dominate if renewed evidence is present.
- `HARD_STOP`: temporal decay exists but should be slower and evidence-specific. Hard-stop exits can still require a stronger new-thesis / full-quality confirmation, but not a permanent ownership penalty.
- `GENERIC`: does not become semantically informative with time. It should remain review/fail-closed for missing context, but that is a provenance/context insufficiency, not evidence that the old thesis remains alive forever.
- `REVERSAL`, `PORTFOLIO_COMPETITION`, `CORPORATE_ACTION`, `ADMINISTRATIVE`: current population did not provide enough direct observed volume to calibrate class-specific lifecycle rules. Architecture still supports class-specific treatment in principle.

`PRIOR_EXIT_RELEVANCE_DECAYS_WITH_TIME = YES`

`EXIT_CLASS_SPECIFIC_TEMPORAL_DECAY_SUPPORTED = YES_FOR_TREND_MOMENTUM_AND_CONDITIONALLY_FOR_HARD_STOP; INSUFFICIENT_DIRECT_VOLUME_FOR_OTHER_CLASSES`

## Short-Term Churn

The clearest undesirable churn population is the immediate post-EXIT bucket:

- 33 episodes are observed within 0-3BD.
- 27 episodes are explicitly blocked by active churn / too-soon semantics.
- These are exactly the cases REENTRY should prevent: immediate rebuy, unresolved weakness, repeated oscillation risk, and insufficient time for a new independent thesis.

`CLEAR_SHORT_TERM_CHURN_EPISODE_COUNT = 27` active-churn blocks, with `33` immediate 0-3BD same-episode observations.

`SHORT_TERM_CHURN_CONTROL_MATERIALLY_JUSTIFIED = YES`

## Long-Delay Opportunity Population

The long-delay population is material:

- `61-120BD`: 44 episodes.
- `>120BD`: 53 episodes.
- `>=61BD` total: 97 episodes.
- `>=61BD` with clear/partial renewed PIT evidence: 74 episodes.
- CN high-confidence `>60BD` SHADOW recovery PASS after semantic restoration: 6 episodes.

These cases are no longer credible as simple same-week churn. Current source still treats them as REENTRY indefinitely because a strict-prior closed campaign exists.

`LONG_DELAY_NEW_OPPORTUNITY_COUNT = 74` broad PIT-classified cases; `6` strict high-confidence SHADOW PASS cases.

`LONG_DELAY_PRIOR_OWNERSHIP_PENALTY_PRESENT = YES`

## Time Alone vs Time + Evidence

Time-only expiry is not supported as a Production rule. The `>=61BD` population still includes 23 weak cases, plus generic/hard-stop cases where context or new-thesis strength matters. Time alone would risk admitting stale weak symbols.

Time + renewed-strength evidence is supported. It preserves short-term churn control and prior EXIT semantics, but allows current PIT evidence to dominate once the prior campaign is economically stale and the current setup is independently strong enough.

`TIME_ONLY_RESET_SUPPORTED = NO`

`TIME_PLUS_EVIDENCE_RESET_SUPPORTED = YES`

## NEW Label vs NEW-Equivalent Treatment

Literal `BUY_NEW` reclassification is not required and is not the preferred architecture. The symbol can retain REENTRY lineage while the decision penalty expires. This preserves auditability and avoids pretending the historical campaign never existed.

Preferred semantics:

- retain prior campaign id, prior EXIT reason, fills, and campaign history;
- classify the current decision as a REENTRY lineage event;
- when temporal + renewed-evidence lifecycle passes, let the opportunity compete on NEW-equivalent capital terms;
- create a new campaign if accepted/fill occurs after a full prior EXIT.

`LITERAL_BUY_NEW_RECLASSIFICATION_REQUIRED = NO`

`NEW_EQUIVALENT_CAPITAL_TREATMENT_SUPPORTED = YES`

`HISTORICAL_LINEAGE_CAN_BE_PRESERVED_WHILE_PENALTY_EXPIRES = YES`

## Block Reasons By Temporal Bucket

| Bucket | Dominant block pattern |
| --- | --- |
| 0-3BD | Active churn / too soon; this is expected and materially justified. |
| 4-10BD | Mostly rank/requalification after churn clears; still near enough to prior EXIT that same-thesis caution is defensible. |
| 11-20BD | Rank/requalification and prior-context review; still plausibly same-thesis continuation. |
| 21-40BD | Rank/requalification dominates; some cases become transitional. |
| 41-60BD | Rank/requalification dominates; partial renewed strength is common. |
| 61-120BD | Rank/requalification dominates despite 33 clear/partial current PIT cases; prior ownership continues to invoke stricter REENTRY lifecycle. |
| >120BD | Rank/requalification dominates despite 41 clear/partial current PIT cases; prior ownership remains a permanent semantic branch. |

`BLOCK_REASON_BY_TEMPORAL_BUCKET = RANK_REQUALIFICATION_DOMINATES_AFTER_CHURN; PRIOR_CONTEXT_AND_REASON_SPECIFIC_RECOVERY_REMAIN_SECONDARY_BLOCKS`

## Structurally Permanent Penalty Test

Current source has a structurally permanent prior-ownership branch:

- `portfolio_construction._semantic_reentry_evidence` returns `REENTRY` whenever a strict-prior `prior_exit_business_date < business_date` exists and the symbol has no current position.
- The only time gate is `REENTRY_COOLDOWN_BUSINESS_DAYS`; after cooldown, the symbol remains REENTRY.
- `_reentry_recovery_evidence` and `_canonical_reentry_semantic_eligibility` continue to require prior EXIT context, reason-specific recovery, rank/requalification, and churn/recovery checks indefinitely.
- There is no max-age, stale-prior-campaign relevance boundary, or time + evidence reset into NEW-equivalent treatment.

This is not an immediate blanket ban, but it is a structurally permanent stricter branch for previously owned symbols.

`STRUCTURALLY_PERMANENT_PRIOR_OWNERSHIP_PENALTY_FOUND = YES`

## Universe Erosion

Prior-owned symbols become a material share of the candidate universe over time:

| Period | Days | Unique candidates | Unique REENTRY symbols | Unique REENTRY share | Avg daily REENTRY | Avg daily candidates | Avg daily REENTRY share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 Q4 | 62 | 535 | 58 | 10.8% | 12.0 | 43.4 | 27.7% |
| 2023 Q1 | 60 | 376 | 96 | 25.5% | 19.9 | 42.9 | 46.4% |
| 2023 Q2 | 62 | 208 | 130 | 62.5% | 30.4 | 43.3 | 70.3% |
| 2023 Q3 to cutoff | 57 | 434 | 141 | 32.5% | 27.2 | 44.2 | 61.6% |

This supports cumulative opportunity-universe erosion. The erosion is semantic, not an outcome/PnL conclusion: more symbols migrate from unrestricted BUY_NEW consideration into a permanently stricter REENTRY branch as the run matures.

`OPPORTUNITY_UNIVERSE_EROSION_SUPPORTED = YES`

`UNIVERSE_EROSION_MATERIALITY = MATERIAL`

## Regime Dependence

The broad `>=61BD` renewed-strength population appears across regimes:

| Regime | Newly formed long-delay episodes |
| --- | ---: |
| BULL | 44 |
| BEAR | 10 |
| RECOVERY | 8 |
| RANGE | 7 |
| CORRECTION | 5 |

The need for temporal lifecycle handling is not limited to a single regime. No regime-specific threshold is justified here.

`TEMPORAL_RESET_NEED_REGIME_DEPENDENT = NO_FIXED_REGIME_THRESHOLD_SUPPORTED; PHENOMENON_OBSERVED_ACROSS_REGIMES`

## Evidence Sufficiency

Existing artifacts already contain enough PIT evidence for a SHADOW temporal lifecycle:

- strict-prior campaign id and prior EXIT date;
- elapsed business days since prior EXIT;
- prior EXIT reason / reason codes after CO;
- rank and requalification fields;
- BQ action;
- trend and momentum recovery fields;
- Entry Admission, continuation quality, downside risk, corporate action, and capacity status;
- market regime context.

No new model, feature, or component is required to distinguish immediate churn, stale weak reconsideration, and genuine renewed opportunity at the semantic-lifecycle layer.

`EXISTING_PIT_EVIDENCE_SUFFICIENT_FOR_TEMPORAL_LIFECYCLE = YES_FOR_SHADOW_AND_FOCUSED_DESIGN; PRODUCTION_ACCEPTANCE_REQUIRES_FRESH_POST_CO_ACTUAL_PATH_EVIDENCE`

## Candidate Designs

### Design A — Temporary REENTRY State

Semantic contract: a symbol remains under stricter REENTRY while cooldown / churn / unresolved-thesis relevance is active; after a designed lifecycle expiry it remains lineaged but no longer carries the churn penalty.

Safety: simple, but time-only expiry is too blunt and risks weak old symbols.

Required changes: REENTRY eligibility needs a relevance-age boundary.

New component/model/feature: no.

### Design B — REENTRY Lineage Retained, Penalty Expires

Semantic contract: prior ownership lineage remains permanent, but the extra REENTRY penalty expires only when both temporal staleness and renewed current PIT evidence pass. The symbol then competes on NEW-equivalent terms while preserving prior campaign lineage.

Safety: preserves churn protection, missing-context fail-closed, hard-stop caution, and current evidence dominance for old independent opportunities.

Required changes: add a temporal lifecycle state inside existing REENTRY semantic eligibility and capital-competition materialization; do not relabel as literal BUY_NEW.

New component/model/feature: no.

### Design C — Evidence-Defined Campaign Reset

Semantic contract: a sufficiently independent current trend marks old campaign relevance expired and starts a new campaign if accepted, while retaining prior campaign audit history.

Safety: close to Design B, but requires careful wording to avoid implying lineage deletion.

Required changes: campaign relevance state plus acceptance-time new campaign materialization.

New component/model/feature: no.

`PREFERRED_TEMPORAL_LIFECYCLE_DESIGN = DESIGN_B_REENTRY_LINEAGE_RETAINED_PENALTY_EXPIRES_WITH_TIME_PLUS_RENEWED_PIT_EVIDENCE`

## Repair Boundary Assessment

A future Production change is repairable inside existing architecture:

- keep REENTRY as lineage;
- keep short-term churn protection;
- keep fail-closed missing/generic prior context where semantic authority is genuinely unavailable;
- preserve reason-specific recovery, especially for hard-stop/corporate-action contexts;
- add an explicit temporal relevance lifecycle that lets old prior-campaign penalty expire only with renewed PIT evidence;
- allow NEW-equivalent capital competition after lifecycle PASS without changing BUY_NEW labels, thresholds, weights, models, or ADD/G129 behavior.

`TEMPORAL_LIFECYCLE_REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE = YES`

`NEW_COMPONENT_REQUIRED = NO`

`NEW_MODEL_REQUIRED = NO`

`NEW_FEATURE_REQUIRED = NO`

`PRODUCTION_CHANGE_JUSTIFIED = CONDITIONAL_YES_FOR_NARROW_TEMPORAL_LIFECYCLE_AFTER_POST_CO_ACTUAL_PATH_ACCEPTANCE; NO_CODE_CHANGE_IN_CP`

## No Outcome Tuning

No later PnL, later returns, future regime, final campaign outcome, selected winner subset, performance-maximizing sweep, or Historical profitability was used to select reset days or classify the Production rule.

The only outcome-related statement inherited here is that later outcomes may be diagnostic after PIT populations are frozen. CP did not use outcome diagnostics to choose a threshold or rule.

`OUTCOME_TUNING_USED = NO`

`POST_CLASSIFICATION_OUTCOME_DIAGNOSTIC_ONLY = YES`

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-09-22`
2. `REENTRY_TEMPORAL_PHILOSOPHY_CONTRACT`: temporary churn-control and prior-thesis recovery semantic; permanent lineage, non-permanent penalty.
3. `TEMPORAL_BUCKET_POPULATION_COMPLETE`: `YES`
4. `NEWLY_FORMED_OPPORTUNITY_COUNT`: `74` broad `>=61BD` renewed-PIT cases; `6` high-confidence CN SHADOW recovery-PASS cases.
5. `PRIOR_EXIT_RELEVANCE_DECAYS_WITH_TIME`: `YES`
6. `EXIT_CLASS_SPECIFIC_TEMPORAL_DECAY_SUPPORTED`: `YES_FOR_TREND_MOMENTUM; CONDITIONAL_FOR_HARD_STOP; INSUFFICIENT_DIRECT_VOLUME_FOR_OTHER_CLASSES`
7. `CLEAR_SHORT_TERM_CHURN_EPISODE_COUNT`: `27` active-churn blocks; `33` immediate 0-3BD same-episode observations.
8. `SHORT_TERM_CHURN_CONTROL_MATERIALLY_JUSTIFIED`: `YES`
9. `LONG_DELAY_NEW_OPPORTUNITY_COUNT`: `74` broad; `6` strict high-confidence.
10. `LONG_DELAY_PRIOR_OWNERSHIP_PENALTY_PRESENT`: `YES`
11. `TIME_ONLY_RESET_SUPPORTED`: `NO`
12. `TIME_PLUS_EVIDENCE_RESET_SUPPORTED`: `YES`
13. `LITERAL_BUY_NEW_RECLASSIFICATION_REQUIRED`: `NO`
14. `NEW_EQUIVALENT_CAPITAL_TREATMENT_SUPPORTED`: `YES`
15. `HISTORICAL_LINEAGE_CAN_BE_PRESERVED_WHILE_PENALTY_EXPIRES`: `YES`
16. `BLOCK_REASON_BY_TEMPORAL_BUCKET`: `RANK_REQUALIFICATION_DOMINATES_AFTER_CHURN; PRIOR_CONTEXT/TREND/BQ_SECONDARY`
17. `STRUCTURALLY_PERMANENT_PRIOR_OWNERSHIP_PENALTY_FOUND`: `YES`
18. `OPPORTUNITY_UNIVERSE_EROSION_SUPPORTED`: `YES`
19. `UNIVERSE_EROSION_MATERIALITY`: `MATERIAL`
20. `TEMPORAL_RESET_NEED_REGIME_DEPENDENT`: `NO_FIXED_REGIME_DEPENDENCE_SUPPORTED`
21. `EXISTING_PIT_EVIDENCE_SUFFICIENT_FOR_TEMPORAL_LIFECYCLE`: `YES_FOR_SHADOW_DESIGN`
22. `PREFERRED_TEMPORAL_LIFECYCLE_DESIGN`: `DESIGN_B_REENTRY_LINEAGE_RETAINED_PENALTY_EXPIRES_WITH_TIME_PLUS_RENEWED_PIT_EVIDENCE`
23. `OUTCOME_TUNING_USED`: `NO`
24. `POST_CLASSIFICATION_OUTCOME_DIAGNOSTIC_ONLY`: `YES`
25. `TEMPORAL_LIFECYCLE_REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE`: `YES`
26. `NEW_COMPONENT_REQUIRED`: `NO`
27. `NEW_MODEL_REQUIRED`: `NO`
28. `NEW_FEATURE_REQUIRED`: `NO`
29. `PRODUCTION_CHANGE_JUSTIFIED`: `CONDITIONAL_YES_FOR_NARROW_TEMPORAL_LIFECYCLE_AFTER_POST_CO_ACTUAL_PATH_ACCEPTANCE`
30. `NEXT_RECOMMENDED_STEP`: run a SHADOW design phase for Design B after user-operated post-CO fresh actual-path evidence confirms semantic prior EXIT materialization; do not implement a Production lifecycle change from CP alone.
31. `FINAL_JUDGMENT`: `PHASE32_CP_STRUCTURALLY_PERMANENT_REENTRY_PRIOR_OWNERSHIP_PENALTY_CONFIRMED_TIME_PLUS_EVIDENCE_NEW_EQUIVALENT_LIFECYCLE_SUPPORTED_READ_ONLY`

## Final Judgment

`PHASE32_CP_STRUCTURALLY_PERMANENT_REENTRY_PRIOR_OWNERSHIP_PENALTY_CONFIRMED_TIME_PLUS_EVIDENCE_NEW_EQUIVALENT_LIFECYCLE_SUPPORTED_READ_ONLY`

