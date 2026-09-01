# Phase32-CK — REENTRY Fail-Closed BUY_NEW Bypass PC Participant/Rebatch Repair

Target evidence run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

This phase repairs the Phase32-CJ production correctness defect. The target run was used as immutable evidence only. No resume, resume dry-run, recover, replay, fresh-run, long Historical, runtime-state mutation, Pending mutation, Ledger mutation, Strategy parameter change, threshold change, model change, or feature change was executed.

## Root Cause Confirmation

Phase32-CJ identified:

- `PRIMARY_ROOT_CAUSE = PC_MERGE_DEFECT`
- `FIRST_DIVERGENCE_BOUNDARY = PORTFOLIO_CONSTRUCTION_LOT_AWARE_RESIDUAL_RECONSIDERATION_AND_PARTICIPANT_TYPING`
- narrowest repair boundary: `PORTFOLIO_CONSTRUCTION_PARTICIPANT_TYPING_AND_LOT_AWARE_RESIDUAL_REALLOCATION_GUARD`

CK confirms and preserves that conclusion.

The bad path was:

1. Initial PC member materialization correctly classified a prior-owned flat symbol as `semantic_buy_type=REENTRY`.
2. REENTRY recovery/provenance was not `PASS`, so the member had `target_membership=false` / `target_weight=0`.
3. Later PC incremental budget / capital competition / lot-aware reallocation treated non-current `membership_intent=ADD_CANDIDATE` as ordinary `BUY_NEW`.
4. That later PC authority could publish positive BUY_NEW competition/allocation and G102 lot resolution.
5. PS and Runtime consumed the already-wrong upstream BUY_NEW authority.

Therefore the repair belongs in PC participant typing and lot-aware residual/rebatch authority, not in Runtime reclassification.

## Repair

Changed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py`

Implemented a PC-local guard:

- Detects members whose semantic buy type is `REENTRY`.
- Requires actual prior EXIT lineage surface (`prior_campaign_id` or `prior_exit_business_date`) before applying the CK guard, so old abstract REENTRY quality fixtures without prior lineage are not over-blocked.
- Allows valid `REENTRY` when semantic/recovery eligibility is `PASS`.
- Blocks non-PASS prior-owned REENTRY from being typed as `NEW_BUY` in capital competition.
- Zeroes NEW_BUY requested/accepted competition weights for that blocked path.
- Blocks non-PASS prior-owned REENTRY from lot-aware final reallocation BUY_NEW rebatch.
- Preserves the original REENTRY semantic and prior lineage; it does not add a permanent prior-ownership ban.

Code anchors:

- `portfolio_construction.py:5942` `_blocked_reentry_buy_new_reason`
- `portfolio_construction.py:5983` `_capital_competitor_type`
- `portfolio_construction.py:5993` `_capital_competitor_requested_weight`
- `portfolio_construction.py:6005` `_capital_competitor_accepted_weight`
- `portfolio_construction.py:2498` incremental budget participant guard
- `portfolio_construction.py:6840` lot-aware final reallocation guard

## Why This Is Canonical

This is not a hash bypass, Runtime override, downstream relabel, or Strategy semantic change.

PC is the first authority that creates the invalid positive executable BUY_NEW surface after the initial REENTRY rejection. The repair prevents PC from publishing that contradictory authority. PS and Runtime therefore continue to consume PC authority normally.

The repair does not:

- change REENTRY cooldowns;
- change REENTRY recovery thresholds;
- change candidate selection;
- change buy/add/sell weights;
- change capital preference models;
- change G129 BUY_ADD order-increment semantics;
- create a symbol-only ban;
- regenerate campaigns downstream.

## Focused Validation

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py
14 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_reentry_pass_keeps_semantic_when_one_lot_fallback_applies tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_buy_add_one_lot_fallback_preserves_add_semantics tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_canonical_add_is_not_reentry_and_remains_positive_when_low_price_capped
9 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py
19 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase31_a5_executable_membership_guard.py::test_phase32_aa_50280_unresolved_historical_sell_ca_adjustment_cannot_be_approved_pending tests/runtime_v2/test_phase31_a5_executable_membership_guard.py::test_phase32_aa_historical_sell_ca_pass_remains_submittable tests/runtime_v2/test_phase31_a5_executable_membership_guard.py::test_phase32_aa_buy_item_review_plus_pass_sell_preserves_partial_submission
3 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase32_ac_partial_submit_recovery_dry_run_is_deterministic_and_read_only tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase32_ac_partial_submit_recovery_preserves_accepted_order_and_rewinds_pending tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase32_ae_partial_submit_finalization_dry_run_is_read_only tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase32_ae_partial_submit_finalization_executes_preserved_order_once
4 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py
13 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_buy_add_fill_runtime_id_merges_when_open_campaign_lineage_proves_identity tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_actual_shaped_add_history_anchors_merge_with_canonical_bridge tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py::test_phase31_g129_conflicting_fill_campaign_without_canonical_bridge_does_not_merge
9 passed
```

## Regression Matrix

Filled CJ bypass cases:

| Case | Result |
|---|---|
| `2022-11-04 76470` | PASS |
| `2022-12-26 94320` | PASS |
| `2023-04-19 94340` | PASS |
| `2023-05-15 76010` | PASS |
| `2023-05-31 21340` | PASS |

Planned-only CJ bypass cases:

| Case | Result |
|---|---|
| `2023-03-02 93180` | PASS |
| `2023-03-10 93180` | PASS |
| `2023-04-14 94340` | PASS |
| `2023-04-14 45860` | PASS |

Controls:

| Control | Result |
|---|---|
| genuine never-owned BUY_NEW | PASS |
| BUY_ADD / G129 | PASS |
| active churn REENTRY blocked | PASS |
| insufficient-evidence REENTRY blocked | PASS |
| valid REENTRY PASS remains possible | PASS |
| valid REENTRY not relabelled BUY_NEW | PASS |
| no permanent ownership ban | PASS |

## Required Final Answers

1. `PC_PARTICIPANT_TYPING_REPAIRED`: `YES`
2. `LOT_AWARE_REBATCH_REENTRY_GUARD_ADDED`: `YES`
3. `REENTRY_SEMANTIC_PRESERVED_END_TO_END`: `YES`
4. `REENTRY_FAIL_CLOSED_CANNOT_EMIT_BUY_NEW`: `YES`
5. `76470_REGRESSION_PASS`: `PASS`
6. `94320_REGRESSION_PASS`: `PASS`
7. `94340_REGRESSION_PASS`: `PASS`
8. `76010_REGRESSION_PASS`: `PASS`
9. `21340_REGRESSION_PASS`: `PASS`
10. `93180_PLANNED_BYPASS_REGRESSION_PASS`: `PASS`
11. `45860_PLANNED_BYPASS_REGRESSION_PASS`: `PASS`
12. `GENUINE_NEW_UNCHANGED`: `YES`
13. `BUY_ADD_UNCHANGED`: `YES`
14. `ACTIVE_CHURN_PROTECTION_PRESERVED`: `YES`
15. `REENTRY_INSUFFICIENT_EVIDENCE_FAIL_CLOSED`: `YES`
16. `VALID_REENTRY_REMAINS_POSSIBLE`: `YES`
17. `VALID_REENTRY_NOT_RELABELLED_BUY_NEW`: `YES`
18. `PRIOR_EXIT_LINEAGE_PRESERVED`: `YES`
19. `PERMANENT_PRIOR_OWNERSHIP_BAN_ADDED`: `NO`
20. `SYMBOL_ONLY_JOIN_ADDED`: `NO`
21. `DOWNSTREAM_CAMPAIGN_REGENERATION_ADDED`: `NO`
22. `PS_DEFENSIVE_GUARD_ADDED`: `NO_NOT_REQUIRED`
23. `RUNTIME_DEFENSIVE_GUARD_ADDED`: `NO_NOT_REQUIRED`
24. `STRATEGY_SEMANTICS_CHANGED`: `NO`
25. `NEW_COMPONENT_ADDED`: `NO`
26. `NEW_MODEL_ADDED`: `NO`
27. `NEW_FEATURE_ADDED`: `NO`
28. `TARGET_RUN_MUTATED`: `NO`
29. `RESUME_EXECUTED`: `NO`
30. `FRESH_RUN_EXECUTED`: `NO`
31. `FUTURE_FRESH_VALIDATION_REQUIRED`: `YES`
32. `NEXT_RECOMMENDED_STEP`: user-operated fresh Historical validation from the accepted post-CK source, with the CJ bypass dates inspected on the new evidence.
33. `FINAL_JUDGMENT`: `PHASE32_CK_REENTRY_FAIL_CLOSED_BUY_NEW_BYPASS_PC_PARTICIPANT_REBATCH_REPAIRED_FOCUSED_VALIDATION_PASS_FRESH_VALIDATION_REQUIRED`

## Final Judgment

`PHASE32_CK_REENTRY_FAIL_CLOSED_BUY_NEW_BYPASS_PC_PARTICIPANT_REBATCH_REPAIRED_FOCUSED_VALIDATION_PASS_FRESH_VALIDATION_REQUIRED`
