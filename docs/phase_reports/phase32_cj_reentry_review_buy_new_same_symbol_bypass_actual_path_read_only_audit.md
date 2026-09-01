# Phase32-CJ — REENTRY Review Bypassed by BUY_NEW Same-Symbol Actual-Path Correctness Audit

Target run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

Evidence snapshot:

- run status at inspection: `RUNNING`
- latest completed business date used: `2023-08-29`
- completed business days used: `224`
- current continuation point observed read-only: `2023-08-30:market_refresh`
- source commit recorded by run state: `cf0a00b0271d170094aa0ce2bfbedc203c364406`
- no code, config, runtime state, Pending, Ledger, replay, recover, resume, or fresh-run was changed or executed

This report preserves Phase32-CI conclusions. This is a correctness audit, not a performance or PnL audit.

## Preserved CI Conclusion

Phase32-CI found no fixed explicit action priority, but did find an emergent `NEW > ADD > REENTRY` materialization pattern and a concrete action-classification correctness concern: symbols with prior SELL_EXIT history could appear in same-day Portfolio Construction as `semantic_buy_type=REENTRY`, `target_membership=false`, `REVIEW_REQUIRED`, but later materialize and fill as `BUY_NEW`.

CJ confirms that action-classification defect on actual artifacts.

## REENTRY Contract

`REENTRY_FAIL_CLOSED_AUTHORITY_CONTRACT`:

- A BUY after a symbol is flat following a ledger-proven full EXIT remains semantic `REENTRY`; it is not ordinary `BUY_NEW`.
- REENTRY is allowed only when strict-prior prior campaign identity and prior EXIT cause are available and current PIT evidence proves genuine recovery.
- Generic `EXIT`, empty, `SELL`, `UNKNOWN`, or unresolved prior EXIT context is insufficient and must fail safe to review / wait semantics.
- `target_membership=false` and `target_weight=0` for a REENTRY row means Portfolio Construction did not authorize current-day membership or capital for that semantic opportunity.
- Runtime, Position Sizing, Submit, and Ledger may preserve and consume lineage, but may not re-decide capital or override a PC REENTRY rejection.
- A later valid REENTRY must remain possible; this contract is not a permanent prior-ownership ban.

Relevant SoT/source anchors:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`: REENTRY after a ledger-proven full EXIT starts a new campaign identity and must not be merged into ordinary NEW.
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`: REENTRY requires prior campaign identity, prior EXIT cause, cooldown, current evidence, and recovery.
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`: PS must not independently promote target weight or re-decide PC allocation.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: PC explicitly emits `downstream_reclassification_allowed=False` in the final deployment authority.

## All Five CI Cases

`ALL_FIVE_BYPASS_CASES_REPRODUCED = YES`

| Date | Symbol | Prior campaign | Prior EXIT date | Prior EXIT reason | Elapsed BD | PC semantic | REENTRY status | Target membership | Runtime source decision | Runtime intent | Fill qty | Resulting campaign |
|---|---|---|---|---|---:|---|---|---|---|---|---:|---|
| `2022-11-04` | `76470` | `pc-0fde8c381d30cb5e-76470-0001` | `2022-10-14` | `EXIT`; `weak_hold_score` | 14 | `REENTRY` | `REVIEW_REQUIRED`; `REENTRY_INSUFFICIENT_EVIDENCE`; `insufficient_prior_exit_context` | `false` | `rp-2022-11-04-76470-buy_new-21d5a9022b5feea6` | `BUY_NEW` | 100 | `pc-51d4bf0a29ba7f1b-76470-0001` |
| `2022-12-26` | `94320` | `pc-3e10dff1ccdebf0e-94320-0001` | `2022-12-05` | `EXIT` | 14 | `REENTRY` | `REVIEW_REQUIRED`; `REENTRY_INSUFFICIENT_EVIDENCE`; `insufficient_prior_exit_context` | `false` | `rp-2022-12-26-94320-buy_new-a989a74d8555c6f8` | `BUY_NEW` | 100 | `pc-86b7ed8997105419-94320-0001` |
| `2023-04-19` | `94340` | `pc-bc6bd9135efcebe2-94340-0001` | `2022-12-07` | `EXIT`; `weak_hold_score` | 94 | `REENTRY` | `REVIEW_REQUIRED`; `REENTRY_INSUFFICIENT_EVIDENCE`; `insufficient_prior_exit_context` | `false` | `rp-2023-04-19-94340-buy_new-bff147395311fece` | `BUY_NEW` | 500 | `pc-27c9cf3d2e387ac7-94340-0001` |
| `2023-05-15` | `76010` | `pc-050da4e70de542d2-76010-0001` | `2023-04-27` | `EXIT`; `profit_retention_break` | 11 | `REENTRY` | `REVIEW_REQUIRED`; `REENTRY_INSUFFICIENT_EVIDENCE`; `insufficient_prior_exit_context` | `false` | `rp-2023-05-15-76010-buy_new-165d0a1a7417d717` | `BUY_NEW` | 300 | `pc-d69a4723920a56a9-76010-0001` |
| `2023-05-31` | `21340` | `pc-01b419db9f700893-21340-0001` | `2023-05-17` | `EXIT`; `trend_and_opportunity_broken` | 9 | `REENTRY` | `REVIEW_REQUIRED`; `REENTRY_INSUFFICIENT_EVIDENCE`; `insufficient_prior_exit_context` | `false` | `rp-2023-05-31-21340-buy_new-7a0e639083296b5a` | `BUY_NEW` | 2700 | `pc-b362959b1d74e740-21340-0001` |

In all five cases:

- PC initially preserved prior ownership context and classified the same symbol as `REENTRY`.
- PC then also produced a capital-competition / lot-aware path with `competitor_type=NEW_BUY` or `semantic_type=BUY_NEW`.
- PS consumed that later positive PC discrete quantity authority as `semantic_buy_type=BUY_NEW`.
- Runtime consumed PS output as `BUY_NEW`; it did not receive an executable REENTRY authority and then relabel it.
- Submit and fill preserved the already-wrong `BUY_NEW` source decision type.

## General Pattern Search

Search criteria:

```text
prior SELL_EXIT exists
same-day PC semantic_buy_type=REENTRY
same-day REENTRY target_membership=false or status != PASS
same symbol receives positive BUY_NEW Runtime plan and/or fill
```

Results across completed evidence through `2023-08-29`:

- filled bypass cases: `5`
- planned bypass cases including non-filled: `9`
- additional planned-only cases: `4`
- valid semantic REENTRY PASS rows observed: `0`
- active churn-protection REENTRY rows observed: `588`
- active churn-protection rows that became BUY_NEW plans: `0`

Additional planned-only cases:

| Date | Symbol | Prior EXIT date | Elapsed BD | REENTRY state | Runtime BUY_NEW plan | Planned quantity |
|---|---|---|---:|---|---|---:|
| `2023-03-02` | `93180` | `2023-02-24` | 3 | `REENTRY_INSUFFICIENT_EVIDENCE` | `rp-2023-03-02-93180-buy_new-002bcb2f14ca1191` | 11300 |
| `2023-03-10` | `93180` | `2023-02-24` | 9 | `REENTRY_INSUFFICIENT_EVIDENCE` | `rp-2023-03-10-93180-buy_new-bc20416d8f2c9205` | 17000 |
| `2023-04-14` | `94340` | `2022-12-07` | 91 | `REENTRY_INSUFFICIENT_EVIDENCE` | `rp-2023-04-14-94340-buy_new-b3669fc441ff1f1b` | 400 |
| `2023-04-14` | `45860` | `2023-01-25` | 56 | `REENTRY_INSUFFICIENT_EVIDENCE` | `rp-2023-04-14-45860-buy_new-59983c57ce67feb2` | 300 |

`TOTAL_REENTRY_TO_BUY_NEW_BYPASS_CASES = 9_PLANNED; 5_FILLED`

## First Divergence Boundary

`FIRST_DIVERGENCE_BOUNDARY = PORTFOLIO_CONSTRUCTION_LOT_AWARE_RESIDUAL_RECONSIDERATION_AND_PARTICIPANT_TYPING`

The first bad boundary is inside Portfolio Construction after initial REENTRY classification:

1. `_resolve_low_price_reentry_allocation_guard` correctly detects semantic REENTRY and sets failed/review REENTRY rows to `final_weight=0`, `final_membership=false`.
2. Later capital competition / residual reallocation code treats any non-current `membership_intent=ADD_CANDIDATE` with positive requested/accepted weight as `participant_type=BUY_NEW`.
3. This path does not require the existing `semantic_buy_type=REENTRY` to have `eligibility_status=PASS`.
4. Lot-aware final reallocation then publishes `phase29_l19_lot_resolution.semantic_type=BUY_NEW` and `pc_positive_executable_quantity_authority.status=PASS`.
5. Position Sizing consumes that G102/PC quantity authority and rewrites the row to `semantic_buy_type=BUY_NEW`.
6. Runtime maps the positive zero-current-position quantity to `BUY_NEW`.

Source anchors:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: non-current `membership == ADD_CANDIDATE` is mapped to `participant_type = BUY_NEW` in capital competition preparation.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: `_lot_authority_semantic_type` can preserve `REENTRY` only if the member's semantic is still present at the participant boundary.
- `src/ai_fund_lab_v2/strategy/position_sizing.py`: `_canonical_sizing_intent_type` maps non-current `ADD_CANDIDATE` to `NEW_BUY`.
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`: `_map_action` maps `membership == ADD_CANDIDATE` to `BUY_NEW`.

## Parallel Authority Audit

`PARALLEL_REENTRY_AND_NEW_AUTHORITIES_EXIST = YES`

The same symbol has two same-day authority surfaces:

- Authority A: PC `portfolio_members` row with `semantic_buy_type=REENTRY`, prior campaign, prior EXIT date, `target_membership=false`, and REENTRY review/fail-closed status.
- Authority B: PC residual / lot-aware / capital-competition output that treats the same symbol as `NEW_BUY` because `membership_intent=ADD_CANDIDATE` and current quantity is zero.

`BUY_NEW_PATH_CONSUMES_REENTRY_FAIL_CLOSED_STATE = NO_AS_AUTHORITY; YES_AS_OBSERVABILITY_ONLY`

Runtime artifacts can carry a compact `reentry_binding` or `reentry_semantic_eligibility`, but the positive quantity contract consumed by Submit is already `BUY_NEW`. The BUY_NEW path is aware enough to display REENTRY reason codes in observability, but not enough to block execution.

## Same-Symbol Join Semantics

`PRIOR_OWNERSHIP_CONTEXT_LOST_AT_JOIN = YES_AT_PC_RESIDUAL_RECONSIDERATION_JOIN; NO_AT_INITIAL_PC_REENTRY_CLASSIFICATION`

Initial PC candidate materialization is strict-prior and prior-ownership aware:

- prior campaign IDs are present;
- prior EXIT dates are before the current business date;
- prior EXIT reasons/reason codes are carried where available;
- `semantic_buy_type=REENTRY` is assigned correctly.

The context is lost later when capital competition / residual reallocation joins by symbol/index and participant type but derives BUY_NEW participation from `membership_intent=ADD_CANDIDATE` rather than from the semantic REENTRY eligibility result.

## Action Inference Audit

`ZERO_CURRENT_POSITION_INCORRECTLY_IMPLIES_BUY_NEW = YES_WITH_MEMBERSHIP_ADD_CANDIDATE`

The defect is not a bare `current_quantity == 0` rule alone. The actual path is:

```text
current_quantity = 0
membership_intent = ADD_CANDIDATE
semantic_buy_type = REENTRY / REVIEW_REQUIRED
-> participant_type = BUY_NEW
-> PS intent_type = NEW_BUY
-> Runtime planning_intent = BUY_NEW
```

This is invalid for prior-owned symbols whose semantic REENTRY authority is not PASS.

## PC / PS / Runtime Authority

`DOWNSTREAM_ALLOWED_TO_OVERRIDE_PC_REENTRY_REJECTION = NO_BY_CONTRACT; YES_BY_CURRENT_DEFECTIVE_PATH`

PC is the authoritative admission and capital allocation owner. If semantic REENTRY is review-required and `target_membership=false`, downstream components are not allowed to create a positive executable quantity for that same symbol under a different BUY_NEW meaning.

`POSITIVE_PS_QUANTITY_SOURCE_FOR_BYPASS = PC_LOT_AWARE_G102_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_WITH_SEMANTIC_TYPE_BUY_NEW`

For all five filled cases, PS positive quantity came from PC lot-aware residual/rebatch authority:

- `lot_aware_accepted_buy_new_weight > 0`
- `phase29_l19_lot_resolution.semantic_type = BUY_NEW`
- `pc_positive_executable_quantity_authority.status = PASS`
- `canonical_sizing_evidence.intent_type = NEW_BUY`
- `quantity_status = RESOLVED_CANDIDATE`

`RUNTIME_BUY_NEW_CLASSIFICATION_SOURCE = INCORRECT_UPSTREAM_BUY_NEW_AUTHORITY_FROM_PC_PS`

Runtime received incorrect upstream BUY_NEW authority. It did not receive a valid REENTRY authority and independently reclassify it.

## Campaign Identity

`BYPASS_BREAKS_REENTRY_LINEAGE = YES`

Each filled bypass creates a fresh `position_campaign_id` as if ordinary BUY_NEW had occurred. A valid accepted REENTRY should also create a new campaign, but it must retain prior-exit/reentry context and source decision semantics. These filled rows are `source_decision_type=BUY_NEW` and do not preserve the REENTRY decision lineage as executable authority.

## Churn Safety Impact

`ACTIVE_CHURN_PROTECTION_BYPASSED_COUNT = 0`

The observed filled bypasses all have `REENTRY_CHURN_PROTECTION_SATISFIED` but fail `REENTRY_INSUFFICIENT_EVIDENCE`. This is still a correctness defect because the REENTRY fail-closed / review-required recovery gate is bypassed. It is not evidence that active short-term churn protection itself was bypassed in this target evidence.

## Negative Controls

- `GENUINE_NEW_CONTROL_PASS = YES`: `351` BUY_NEW fills had no same-day prior REENTRY context and remain valid controls for ordinary never-owned NEW handling.
- `BUY_ADD_CONTROL_PASS = YES`: `16` BUY_ADD fills were observed and are not implicated by this same-symbol REENTRY bypass.
- `VALID_REENTRY_CONTROL_PASS_OR_NOT_AVAILABLE = NOT_AVAILABLE`: no semantic REENTRY PASS rows were observed in completed evidence through `2023-08-29`.
- `ACTIVE_CHURN_CONTROL_PASS = YES`: `588` active churn-protection REENTRY rows were observed and none became positive BUY_NEW Runtime plans.

## Root Cause Classification

`PRIMARY_ROOT_CAUSE = PC_MERGE_DEFECT`

More specifically:

```text
PC residual / lot-aware capital competition derives BUY_NEW authority from
membership_intent=ADD_CANDIDATE and current zero position without binding to
semantic_buy_type=REENTRY eligibility_status=PASS.
```

`SECONDARY_CAUSES = ZERO_POSITION_ACTION_INFERENCE_DEFECT; PRIOR_OWNERSHIP_CONTEXT_PROPAGATION_DEFECT; PS_PROVENANCE_DEFECT`

Secondary details:

- PS maps non-current `ADD_CANDIDATE` to `NEW_BUY`, consuming the already-bad PC authority.
- Runtime maps the positive PS zero-position quantity to `BUY_NEW`, consuming rather than creating the defect.
- Prior ownership is preserved initially but not enforced at later PC participant/rebatch boundaries.
- Campaign lineage becomes ordinary BUY_NEW source lineage after the bad boundary.

Not primary:

- `RUNTIME_RECLASSIFICATION_DEFECT`: not primary; Runtime consumes incorrect upstream authority.
- `CAMPAIGN_IDENTITY_DEFECT`: downstream symptom, not first cause.
- `CANDIDATE_PARALLEL_AUTHORITY_DEFECT`: partial symptom, but the first authoritative executable quantity is produced at PC residual/rebatch participant typing.

## Narrowest Correct Future Repair Boundary

`NARROWEST_CORRECT_REPAIR_BOUNDARY = PORTFOLIO_CONSTRUCTION_PARTICIPANT_TYPING_AND_LOT_AWARE_RESIDUAL_REALLOCATION_GUARD`

Future repair should be at PC, before PS receives executable quantity:

- If a non-current candidate has authoritative prior closed campaign / SELL_EXIT history and PC semantic classification is `REENTRY`, then every PC capital participant, residual reconsideration row, lot-aware rebatch row, and G102 quantity authority must use `REENTRY`, not `BUY_NEW`.
- If REENTRY status is not PASS, PC must not publish positive `accepted_buy_new_weight`, `lot_aware_accepted_buy_new_weight`, or `pc_positive_executable_quantity_authority` for that symbol.
- Never-owned NEW remains unchanged.
- Valid ADD remains unchanged.
- Legitimate REENTRY remains possible when semantic REENTRY PASS evidence exists.
- Active churn and insufficient prior-exit context remain fail-closed.
- PS and Runtime can retain defensive guards, but the main fix should prevent the bad PC authority from being created.

No new model or component is required.

## Target Run Implication

`TARGET_RUN_VALIDATION_IMPACT = CURRENT_RUN_NOT_CLEAN_PRODUCTION_EQUIVALENT_FOR_REENTRY_CLASSIFICATION; PERFORMANCE_INTERPRETATION_REQUIRES_DEFECT_ANNOTATION; NO_READ_ONLY_ABANDON_OR_RESUME_ACTION`

The target run contains actual filled correctness-defect trades. It should not be treated as clean Production-equivalent evidence for same-symbol REENTRY/BUY_NEW classification. This does not by itself prove valuation/PnL arithmetic is wrong, and CJ does not mutate or abandon the run.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-08-29`
2. `REENTRY_FAIL_CLOSED_AUTHORITY_CONTRACT = prior-owned flat symbol after ledger-proven SELL_EXIT remains REENTRY; REENTRY requires strict-prior campaign/EXIT context and current PIT recovery evidence; REVIEW_REQUIRED/FAIL_CLOSED target_membership=false cannot be overridden by BUY_NEW`
3. `ALL_FIVE_BYPASS_CASES_REPRODUCED = YES`
4. `TOTAL_REENTRY_TO_BUY_NEW_BYPASS_CASES = 9_PLANNED; 5_FILLED`
5. `FIRST_DIVERGENCE_BOUNDARY = PORTFOLIO_CONSTRUCTION_LOT_AWARE_RESIDUAL_RECONSIDERATION_AND_PARTICIPANT_TYPING`
6. `PARALLEL_REENTRY_AND_NEW_AUTHORITIES_EXIST = YES`
7. `BUY_NEW_PATH_CONSUMES_REENTRY_FAIL_CLOSED_STATE = NO_AS_AUTHORITY; YES_AS_OBSERVABILITY_ONLY`
8. `PRIOR_OWNERSHIP_CONTEXT_LOST_AT_JOIN = YES_AT_PC_RESIDUAL_RECONSIDERATION_JOIN; NO_AT_INITIAL_PC_REENTRY_CLASSIFICATION`
9. `ZERO_CURRENT_POSITION_INCORRECTLY_IMPLIES_BUY_NEW = YES_WITH_MEMBERSHIP_ADD_CANDIDATE`
10. `DOWNSTREAM_ALLOWED_TO_OVERRIDE_PC_REENTRY_REJECTION = NO_BY_CONTRACT; YES_BY_CURRENT_DEFECTIVE_PATH`
11. `POSITIVE_PS_QUANTITY_SOURCE_FOR_BYPASS = PC_LOT_AWARE_G102_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY_WITH_SEMANTIC_TYPE_BUY_NEW`
12. `RUNTIME_BUY_NEW_CLASSIFICATION_SOURCE = INCORRECT_UPSTREAM_BUY_NEW_AUTHORITY_FROM_PC_PS`
13. `BYPASS_BREAKS_REENTRY_LINEAGE = YES`
14. `ACTIVE_CHURN_PROTECTION_BYPASSED_COUNT = 0`
15. `GENUINE_NEW_CONTROL_PASS = YES`
16. `BUY_ADD_CONTROL_PASS = YES`
17. `VALID_REENTRY_CONTROL_PASS_OR_NOT_AVAILABLE = NOT_AVAILABLE`
18. `ACTIVE_CHURN_CONTROL_PASS = YES`
19. `PRIMARY_ROOT_CAUSE = PC_MERGE_DEFECT`
20. `SECONDARY_CAUSES = ZERO_POSITION_ACTION_INFERENCE_DEFECT; PRIOR_OWNERSHIP_CONTEXT_PROPAGATION_DEFECT; PS_PROVENANCE_DEFECT`
21. `NARROWEST_CORRECT_REPAIR_BOUNDARY = PORTFOLIO_CONSTRUCTION_PARTICIPANT_TYPING_AND_LOT_AWARE_RESIDUAL_REALLOCATION_GUARD`
22. `CORRECTNESS_DEFECT_CONFIRMED = YES`
23. `STRATEGY_SEMANTICS_CHANGE_REQUIRED = NO`
24. `NEW_COMPONENT_REQUIRED = NO`
25. `NEW_MODEL_REQUIRED = NO`
26. `NEW_FEATURE_REQUIRED = NO`
27. `PRODUCTION_REPAIR_REQUIRED = YES`
28. `TARGET_RUN_MUTATED = NO`
29. `RESUME_EXECUTED = NO`
30. `FRESH_RUN_EXECUTED = NO`
31. `TARGET_RUN_VALIDATION_IMPACT = NOT_CLEAN_PRODUCTION_EQUIVALENT_FOR_REENTRY_CLASSIFICATION; KEEP_AS_ANNOTATED_DEFECT_EVIDENCE`
32. `NEXT_RECOMMENDED_STEP = implement narrow PC participant/rebatch guard preventing REENTRY REVIEW_REQUIRED/FAIL_CLOSED rows from publishing BUY_NEW executable authority, with focused actual-path tests for the five CI/CJ cases plus planned-only cases and negative controls`
33. `FINAL_JUDGMENT = PHASE32_CJ_REENTRY_REVIEW_BYPASSED_BY_BUY_NEW_ACTUAL_PATH_CORRECTNESS_DEFECT_CONFIRMED_PC_MERGE_AND_PARTICIPANT_TYPING_ROOT_CAUSE_PRODUCTION_REPAIR_REQUIRED`

## Final Judgment

`PHASE32_CJ_REENTRY_REVIEW_BYPASSED_BY_BUY_NEW_ACTUAL_PATH_CORRECTNESS_DEFECT_CONFIRMED_PC_MERGE_AND_PARTICIPANT_TYPING_ROOT_CAUSE_PRODUCTION_REPAIR_REQUIRED`
