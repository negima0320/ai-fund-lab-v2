# Phase32-CW — Minimal Residual REENTRY / UNKNOWN Context Production Repair

## Scope

Implemented the accepted Phase32-CU Production contract with the Phase32-CV missing/generic-context amendment.

No fresh-run, resume, recover, replay, long Historical, runtime-state mutation, Pending mutation, Ledger mutation, or target-run mutation was executed.

## Root Cause

The pre-CW REENTRY path still treated prior ownership as a broad penalty surface:

- complete-context REENTRY failed independently on REENTRY-only rank `>10`;
- portfolio-competition prior cause had a special rank `>5` hurdle;
- BQ / quality-like current evidence could be duplicated as REENTRY-specific failure rather than ordinary current BUY authority;
- generic action labels were not explicitly separated from genuinely unknown old context;
- there was no materialized `REENTRY_UNKNOWN_PRIOR_CONTEXT` lifecycle.

This conflicted with CU/CV: REENTRY is lifecycle/provenance, not a permanent rank, quality, time, or capital discount.

## CU/CV Contract Implemented

Implemented in `src/ai_fund_lab_v2/strategy/portfolio_construction.py`:

- added explicit generic action labels: `EXIT`, `SELL`, `SELL_EXIT`, `UNKNOWN`, empty;
- added `reentry_prior_exit_context_classification`;
- distinguished:
  - `COMPLETE_AUTHORITATIVE_CONTEXT`;
  - `RECOVERABLE_PROVENANCE_DEFECT`;
  - `REENTRY_UNKNOWN_PRIOR_CONTEXT`;
- generic action labels default to recoverable provenance defect unless explicitly classified as genuine unknown;
- `REENTRY_UNKNOWN_PRIOR_CONTEXT` can pass only with conservative strong current PIT evidence;
- complete TREND_MOMENTUM context no longer fails solely on REENTRY rank `>10`;
- portfolio-competition special rank `>5` hurdle was removed;
- broad BQ rejection was removed from complete-context REENTRY recovery and left to ordinary current BUY/PC authority;
- existing 3BD cooldown remains unchanged;
- repeated unresolved churn remains unchanged;
- TREND_MOMENTUM prior-cause trend/momentum recovery remains;
- HARD_STOP enhanced recovery remains and now uses explicit strong current evidence composition;
- CK BUY_NEW bypass guard remains intact.

## Protections Retained

- REENTRY lineage and prior campaign auditability.
- CO prior EXIT semantic priority over generic action labels.
- Recoverable provenance-defect fail-closed / REVIEW_REQUIRED.
- `REENTRY_COOLDOWN_BUSINESS_DAYS = 3`.
- Repeated unresolved churn protection.
- Prior-cause technical recovery for TREND_MOMENTUM / HARD_STOP / CORPORATE_ACTION.
- REVERSAL normalization through Entry Admission.
- HARD_STOP enhanced recovery.
- Safety / broker / corporate-action / capacity fail-closed behavior.
- CK blocked-REENTRY no BUY_NEW bypass.
- BUY_ADD / G129 active-position semantics.

## UNKNOWN Lifecycle

`REENTRY_UNKNOWN_PRIOR_CONTEXT` means:

- prior ownership is known;
- old authoritative semantic reason is genuinely unrecoverable or outside the current taxonomy;
- history remains visible as REENTRY lineage;
- no BUY_NEW fallback is allowed;
- it is not a permanent ban;
- it may pass only when current PIT evidence is conservatively strong.

Strong current PIT evidence currently reuses existing fields:

- rank within the existing strong current opportunity band;
- `FULL_ALLOCATION_ELIGIBLE` BQ;
- trend recovery;
- momentum recovery;
- Entry Admission non-blocking;
- CQ / downside acceptable where present;
- CA non-blocking;
- capacity available and non-severe.

No new model, component, feature, score, or day threshold was added.

## Files Changed

Source:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Tests:

- `tests/strategy/test_phase32_cw_minimal_residual_reentry.py`
- `tests/strategy/test_phase30_z_reentry_genuine_recovery.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`

Architecture / SoT:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`

Phase report:

- `docs/phase_reports/phase32_cw_minimal_residual_reentry_unknown_context_production_repair.md`

## Tests Changed

Added CW focused tests for:

- 83060-style TREND_MOMENTUM REENTRY positive control;
- complete-context rank `>10` no longer failing recovery;
- broad BQ penalty removed from recovery while ordinary current BUY authority can still block;
- portfolio-competition rank `>5` special hurdle removed;
- HARD_STOP enhanced recovery retained;
- genuine UNKNOWN strong-current-evidence PASS;
- genuine UNKNOWN weak-current-evidence REVIEW_REQUIRED;
- recoverable provenance defect not masquerading as UNKNOWN;
- existing 3BD cooldown retained;
- repeated unresolved churn retained.

Updated old legacy assertions that expected REENTRY-only rank failure or generic action-label failure reason.

## Focused Validation

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase32cw_pycache PYTHONPATH=src python3 -m compileall -q \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  tests/strategy/test_phase32_cw_minimal_residual_reentry.py \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/strategy/test_phase22_e_portfolio_construction.py
```

Result: PASS.

CW / CK / CO / G129 / PC focused regression:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase32cw_pycache PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_cw_minimal_residual_reentry.py \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g26_first_time_buy_new_has_non_reentry_semantic_contract \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21r3_reentry_capacity_authority_resolves_normal_excessive_and_missing_cases \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g26_reentry_rejection_is_symbol_local_and_next_competitor_survives \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21r3_prior_exit_persists_when_buy_quality_temporarily_excludes_candidate \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_reentry_pass_keeps_semantic_when_one_lot_fallback_applies \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_canonical_add_is_not_reentry_and_remains_positive_when_low_price_capped \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews \
  tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py
```

Result:

```text
88 passed, 1 skipped
```

Broader adjacent PC / Strategy Intelligence / campaign regression:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase32cw_pycache PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase30_j_strategy_intelligence.py \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase32_l_reentry_new_campaign_keeps_fill_campaign_then_add_inherits_it \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_buy_add_fill_runtime_id_merges_when_open_campaign_lineage_proves_identity \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_shaped_add_history_anchors_merge_with_canonical_bridge \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_conflicting_fill_campaign_without_canonical_bridge_does_not_merge
```

Result:

```text
136 passed
```

## Unresolved Safety Gap

No blocking safety gap was found in focused validation. CR near-term unsafe controls remain represented by cooldown and repeated unresolved churn tests. CW did not add a new fixed day threshold; if future actual-path evidence shows a 4-10BD unsafe same-thesis release that cannot be explained by existing residual protections, that should stop the next phase rather than tuning from PnL.

## Fresh Validation Requirement

Fresh validation is required and belongs to the user-operated Historical path:

- confirm actual post-CW REENTRY lineage remains visible;
- confirm 83060-style positive path remains REENTRY, not fake BUY_NEW;
- inspect CR near-term negative controls on new artifacts;
- confirm no CK bypass recurrence;
- confirm no G129 regression.

No long Historical was executed by Codex.

## Required Final Answers

1. `CU_CV_CONTRACT_IMPLEMENTED`: `YES`
2. `REENTRY_LINEAGE_PRESERVED`: `YES`
3. `COMPLETE_CONTEXT_PATH_IMPLEMENTED`: `YES`
4. `RECOVERABLE_PROVENANCE_DEFECT_FAIL_CLOSED_IMPLEMENTED`: `YES`
5. `REENTRY_UNKNOWN_PRIOR_CONTEXT_IMPLEMENTED`: `YES`
6. `UNKNOWN_BUY_NEW_FALLBACK_ALLOWED`: `NO`
7. `CO_PROVENANCE_PRESERVED`: `YES`
8. `CK_BYPASS_GUARD_PRESERVED`: `YES`
9. `BUY_ADD_G129_PRESERVED`: `YES`
10. `REENTRY_RANK_GT10_PENALTY_REMOVED`: `YES`
11. `PORTFOLIO_COMPETITION_RANK5_PENALTY_REMOVED`: `YES`
12. `DUPLICATE_REENTRY_BQ_QUALITY_GATE_REMOVED_OR_MIGRATED`: `YES`
13. `THREE_BD_COOLDOWN_PRESERVED`: `YES`
14. `REPEATED_UNRESOLVED_CHURN_GUARD_PRESERVED`: `YES`
15. `TREND_MOMENTUM_PRIOR_CAUSE_RECOVERY_PRESERVED`: `YES`
16. `HARD_STOP_ENHANCED_RECOVERY_PRESERVED`: `YES`
17. `NEW_TIME_THRESHOLD_ADDED`: `NO`
18. `REENTRY_CAPITAL_COMPETITION_NEUTRALITY_IMPLEMENTED`: `YES`
19. `83060_POSITIVE_CONTROL_PASS`: `YES`
20. `CR_NEAR_TERM_NEGATIVE_CONTROLS_PASS`: `YES_FOCUSED_RESIDUAL_GUARDS_PASS`
21. `GENUINE_UNKNOWN_FIXTURES_PASS`: `YES`
22. `PROVENANCE_DEFECT_VS_UNKNOWN_DISTINCTION_TESTED`: `YES`
23. `GENUINE_BUY_NEW_UNCHANGED`: `YES`
24. `LEGACY_TESTS_CLEANED`: `YES`
25. `ARCHITECTURE_SOT_UPDATED`: `YES`
26. `NEW_COMPONENT_REQUIRED`: `NO`
27. `NEW_MODEL_REQUIRED`: `NO`
28. `NEW_FEATURE_REQUIRED`: `NO`
29. `FOCUSED_TEST_RESULT`: `PASS: 88 passed, 1 skipped; compile PASS`
30. `ADJACENT_REGRESSION_RESULT`: `PASS: 136 passed`
31. `FRESH_VALIDATION_REQUIRED`: `YES`
32. `LONG_HISTORICAL_EXECUTED`: `NO`
33. `TARGET_RUN_MUTATED`: `NO`
34. `NEXT_RECOMMENDED_STEP`: user-operated fresh Historical validation, then READ-ONLY post-CW actual-path acceptance for REENTRY lineage, 83060, CR near-term controls, CK, CO, and G129.
35. `FINAL_JUDGMENT`: `PHASE32_CW_MINIMAL_RESIDUAL_REENTRY_UNKNOWN_CONTEXT_PRODUCTION_REPAIR_ACCEPTED_FOCUSED_VALIDATION_PASS_FRESH_VALIDATION_REQUIRED`

## Final Judgment

`PHASE32_CW_MINIMAL_RESIDUAL_REENTRY_UNKNOWN_CONTEXT_PRODUCTION_REPAIR_ACCEPTED_FOCUSED_VALIDATION_PASS_FRESH_VALIDATION_REQUIRED`
