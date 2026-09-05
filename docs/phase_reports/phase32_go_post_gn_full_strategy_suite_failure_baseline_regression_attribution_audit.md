# Phase32-GO — Post-GN Full Strategy Suite 87-Failure Baseline / Regression Attribution Audit

Status: READ-ONLY AUDIT

Source/config/schema changes performed: NO

Historical fresh-run/resume/replay/recover performed: NO

Runtime state / Pending / Ledger mutation performed: NO

## Executive Judgment

The post-GN full strategy suite result was reproduced as:

```text
python3 -m pytest tests/strategy -q --tb=short
87 failed, 882 passed, 2 skipped
```

Confirmed GN-unintended Production semantic regression count is zero.

However, the full-suite failure set cannot be fully cleared as pre-existing
baseline because no clean pre-GN full-suite baseline was available in this audit
turn. The correct disposition is therefore conservative: one failure is a
known GN intended expectation change, 33 failures are confirmed deleted
runtime-artifact dependencies, one is an obsolete test signature expectation,
and 52 remain unresolved / non-GN-proven failures requiring separate triage.

Short dynamic validation is not ready until the unresolved failures are
separated from true baseline defects or repaired.

## GN Diff Causality Boundary

GN direct production semantic edits were limited to:

- `marginal_capital_value.sort_key`
- `marginal_capital_value.apply_marginal_capital_priority`
- `portfolio_construction._reconcile_incremental_budget`
- `portfolio_construction.apply_lot_aware_final_reallocation`

The direct GN semantic change was:

- canonical Current PIT Opportunity rank becomes the leading BUY priority key;
- accepted/requested positive increment is no longer required before priority;
- PC consumes canonical MCV priority instead of falling back broadly to
  construction priority on any insufficient comparison evidence.

Static diff inspection did not show GN edits in:

- SELL / REDUCE / EXIT logic
- Winner Protection logic
- Position Sizing formulas
- Cash reserve / exposure target logic
- ADD Safety rules
- G129 order increment rules
- REENTRY semantic functions
- Runtime Planning mapping

## Failure Disposition Counts

FULL_SUITE_FAILURE_COUNT: 87

FAILURE_CLASSIFICATION_COMPLETE: YES

PRE_EXISTING_BASELINE_COUNT: 0_CONFIRMED

OBSOLETE_EXPECTATION_COUNT: 1

TEST_INFRA_ARTIFACT_DEPENDENCY_COUNT: 33

GN_INTENDED_EXPECTATION_CHANGE_COUNT: 1

GN_UNINTENDED_REGRESSION_COUNT: 0_CONFIRMED

UNRESOLVED_COUNT: 52

## Category Counts

- BUY_PRIORITY / MCV: 1
- PC / REENTRY: 1
- REENTRY contract migration mismatch: 45
- CASH / SIZING / capital deployment unrelated: 6
- artifact dependency / deleted runtime artifact: 33
- legacy expectation / obsolete test signature: 1
- PM/SELL confirmed GN regression: 0
- WINNER confirmed GN regression: 0
- ADD / G129 confirmed GN regression: 0
- Runtime confirmed GN regression: 0

## 87-Failure Inventory

| # | Test | Assertion / Error | Component | Semantic category | Disposition | GN causality |
|---:|---|---|---|---|---|---|
| 1 | `test_phase22_e_portfolio_construction.py::test_phase29_l21s_capacity_severe_and_buy_quality_reject_remain_zero` | `semantic_buy_type BUY_NEW != REENTRY` | PC | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY function found |
| 2 | `test_phase22_f_capital_deployment.py::test_phase22_f_produces_draft_review_required_not_eligible_artifact` | `BLOCK != REVIEW_REQUIRED` | Capital Deployment | unrelated | F_UNRESOLVED | No direct GN diff path |
| 3 | `test_phase22_f_capital_deployment.py::test_phase22_f_upstream_review_required_propagates_and_rejects_production` | `producer_result_status BLOCK != REVIEW_REQUIRED` | Capital Deployment | unrelated | F_UNRESOLVED | No direct GN diff path |
| 4 | `test_phase22_f_capital_deployment.py::test_phase22_f_fixture_shadow_reads_draft_and_rejects_production` | `CapitalDeploymentConsumerError: BLOCK artifact not fixture-consumable` | Capital Deployment | unrelated | F_UNRESOLVED | No direct GN diff path |
| 5 | `test_phase22_pr_dynamic_capacity_asset_proportionality.py::test_phase22_pr_asset_proportional_exposure_has_no_850000_cap` | `target_invested_notional None != 800000` | Cash/Sizing | CASH/SIZING | F_UNRESOLVED | No direct GN diff path |
| 6 | `test_phase22_pr_dynamic_capacity_asset_proportionality.py::test_phase22_pr_current_holdings_delta_sizing` | `incremental_buy_notional 0.0 not > 0` | Sizing | SIZING | F_UNRESOLVED | No direct GN diff path |
| 7 | `test_phase22_pr_dynamic_capacity_asset_proportionality.py::test_phase22_pr_legacy_isolation_for_count_and_exposure` | `target_invested_notional None != 1600000` | Cash/Sizing | CASH/SIZING | F_UNRESOLVED | No direct GN diff path |
| 8 | `test_phase24_hy_rank_authority.py::test_portfolio_member_materializes_opportunity_rank_lineage` | `_member() missing keyword-only argument: current` | PC test API | legacy expectation | B_OBSOLETE_EXPECTATION | Not GN; signature mismatch |
| 9 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21k_prior_same_symbol_exit_materializes_reentry_input` | `KeyError: prior_exit_business_date` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 10 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_h_prior_exit_context_uses_strict_prior_pm_exit_detail` | `KeyError: prior_exit_business_date` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 11 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_prior_exit_semantic_reason_codes_prevent_generic_exit_collapse` | `KeyError: prior_exit_reason` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 12 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_cn_shadow_pass_representatives_keep_recovered_exit_semantics[73590...]` | `KeyError: prior_campaign_id` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 13 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_cn_shadow_pass_representatives_keep_recovered_exit_semantics[59860...]` | `KeyError: prior_campaign_id` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 14 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_cn_shadow_pass_representatives_keep_recovered_exit_semantics[65500...]` | `KeyError: prior_campaign_id` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 15 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_cn_shadow_pass_representatives_keep_recovered_exit_semantics[67310...]` | `KeyError: prior_campaign_id` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 16 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_cn_shadow_pass_representatives_keep_recovered_exit_semantics[65730...]` | `KeyError: prior_campaign_id` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 17 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_hard_stop_semantic_retained_without_weakening_new_thesis_requirement` | `KeyError: prior_exit_reason` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 18 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_co_genuine_generic_exit_remains_review_required` | `KeyError: prior_exit_reason` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 19 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_cw_active_churn_remains_blocked_and_rank_penalty_removed` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 20 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_prior_exit_context_can_join_by_pm_decision_id_when_sell_campaign_missing` | `KeyError: prior_campaign_id` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 21 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_p_date_only_reentry_rows_are_enriched_with_canonical_prior_context` | `KeyError: prior_campaign_id` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 22 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_l_83060_actual_path_reentry_provenance_reaches_final_result` | `semantic_buy_type BUY_NEW != REENTRY` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY semantic |
| 23 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_h_missing_prior_exit_detail_stays_review_required` | `KeyError: prior_exit_reason` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 24 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_h_multiple_campaigns_use_latest_matching_prior_campaign_context` | `KeyError: prior_exit_business_date` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 25 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21k_multiple_campaigns_resolve_latest_pit_prior_exit` | `KeyError: prior_exit_business_date` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 26 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21k_23880_reproduction_reaches_existing_l16_reentry_contract` | `KeyError: prior_exit_business_date` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 27 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21r3_23880_prior_exit_persists_through_temporary_exclude_then_reentry` | `KeyError: prior_exit_business_date` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 28 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21p_reentry_recovery_passes_when_corporate_action_evidence_is_available` | `KeyError: prior_exit_business_date` | REENTRY input | REENTRY | F_UNRESOLVED | No direct GN edit to prior-exit supply |
| 29 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21p_reentry_recovery_requires_corporate_action_evidence` | `semantic_buy_type BUY_NEW != REENTRY` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY semantic |
| 30 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21p_runtime_opportunity_score_is_canonical_reentry_score` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 31 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21r_low_score_reentry_can_pass_when_relative_and_recovery_evidence_pass` | `reentry_cooldown_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY cooldown |
| 32 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_cw_weak_relative_rank_no_longer_blocks_reentry_recovery` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 33 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21r_corporate_action_and_capacity_fail_closed_semantics` | `reentry_recovery_status NOT_APPLICABLE != FAIL_CLOSED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 34 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_reentry_recovery_failure_does_not_become_safety_block` | `reentry_recovery_status NOT_APPLICABLE != FAIL_CLOSED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 35 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_prior_context_insufficiency_does_not_become_safety_block` | `reentry_recovery_status NOT_APPLICABLE != REVIEW_REQUIRED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 36 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_genuine_safety_block_remains_fail_closed` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 37 | `test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_broker_and_corporate_statuses_stay_separate_from_safety` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 38 | `test_phase29_l21k_prior_exit_materialization.py::test_phase29_l21r_previous_exit_reason_controls_technical_recovery_requirement` | `reentry_recovery_status NOT_APPLICABLE != FAIL_CLOSED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 39 | `test_phase30_z_reentry_genuine_recovery.py::test_phase30_z_genuine_recovery_allows_reentry_even_with_uncalibrated_negative_edge` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 40 | `test_phase30_z_reentry_genuine_recovery.py::test_phase30_z_partial_technical_recovery_no_longer_proves_reentry` | `reentry_recovery_status NOT_APPLICABLE != FAIL_CLOSED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 41 | `test_phase30_z_reentry_genuine_recovery.py::test_phase30_z_unknown_prior_exit_context_fails_safe_to_review` | `reentry_recovery_status NOT_APPLICABLE != REVIEW_REQUIRED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 42 | `test_phase30_z_reentry_genuine_recovery.py::test_phase30_z_entry_admission_blocks_unresolved_reversal_or_overheated_reentry` | `reentry_recovery_status NOT_APPLICABLE != FAIL_CLOSED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 43 | `test_phase30_z_reentry_genuine_recovery.py::test_phase30_z_repeated_unresolved_churn_blocks_reentry_without_using_pnl_outcomes` | `reentry_recovery_status NOT_APPLICABLE != FAIL_CLOSED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 44 | `test_phase30_z_reentry_genuine_recovery.py::test_phase30_z_genuine_recovery_after_prior_failure_can_still_reenter` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 45 | `test_phase31_b4_marginal_capital_value_shadow.py::test_phase31_b4_strong_add_can_outrank_comparable_new_only_with_explicit_pit_lifecycle_evidence` | order `22220,33330` vs expected `33330,22220` | MCV | BUY_PRIORITY legacy expectation | D_GN_INTENDED_SEMANTIC_CHANGE_EXPECTATION | Directly caused by GN rank-first priority |
| 46 | `test_phase31_b6_marginal_capital_shadow_bridge.py::test_phase31_b6_b0_94320_real_pit_add_campaign_evidence_is_bridged` | missing `reports/runtime_tests/.../portfolio_construction.json` | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 47 | `test_phase31_b6_marginal_capital_shadow_bridge.py::test_phase31_b6_real_run_materialization_writes_only_diagnostic_shadow` | missing `reports/runtime_tests/.../strategy` | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 48 | `test_phase31_b8_pending_cash_causality_bridge.py::test_phase31_b8_b0_real_94320_full_causality_is_reconstructed` | missing `reports/runtime_tests/.../portfolio_construction.json` | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 49 | `test_phase31_f1d_canonical_sell_semantic_shadow.py::test_phase31_f1d_materialization_writes_only_diagnostic_shadow` | missing `reports/runtime_tests/.../strategy` | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 50 | `test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py::test_phase31_g102_actual_20230322_94320_reconsideration_gets_item_scoped_pc_authority` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 51 | `test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py::test_phase31_g102_lot_infeasible_reconsideration_does_not_false_pass` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 52 | `test_phase31_g113_add_marginal_competition_shadow.py::test_phase31_g113_actual_76470_add_shadow_is_lot_level_and_non_authoritative` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 53 | `test_phase31_g66_publication_path_integration.py::test_phase31_g66_actual_pit_publication_path_materializes_buy_plans` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 54 | `test_phase31_g86_cash_preferred_participation_deferral.py::test_phase31_g86_actual_normal_cash_preferred_participation_restored` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 55 | `test_phase31_g86_cash_preferred_participation_deferral.py::test_phase31_g86_actual_weak_tail_cash_preferred_examples_defer` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 56 | `test_phase31_g90_cash_preferred_aggregate_resolver.py::test_phase31_g90_january_actual_rows_no_frontier_only_bottleneck` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 57 | `test_phase31_g90_cash_preferred_aggregate_resolver.py::test_phase31_g90_g80_actual_weak_tail_rows_remain_deferred` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 58 | `test_phase31_g90_cash_preferred_aggregate_resolver.py::test_phase31_g90_bootstrap_actual_path_preserved` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 59 | `test_phase31_g95_residual_reconsideration_shadow.py::test_phase31_g95_actual_0405_0406_rows_receive_terminal_shadow_competition` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 60 | `test_phase31_g95_residual_reconsideration_shadow.py::test_phase31_g95_actual_0406_safety_terminal_not_resurrected` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 61 | `test_phase31_g95_residual_reconsideration_shadow.py::test_phase31_g95_known_weak_tail_dates_do_not_revive_security_shadow` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 62 | `test_phase31_g97_residual_reconsideration_authoritative_binding.py::test_phase31_g97_0405_0406_reconsiderable_rows_authoritative_cash_defer` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 63 | `test_phase31_g97_residual_reconsideration_authoritative_binding.py::test_phase31_g97_positive_shadow_anchors_enter_authoritative_pc_allocation` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 64 | `test_phase31_g97_residual_reconsideration_authoritative_binding.py::test_phase31_g97_multi_security_reconsideration_coexists_with_cash` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 65 | `test_phase31_g97_residual_reconsideration_authoritative_binding.py::test_phase31_g97_safety_terminal_and_g80_weak_tail_not_resurrected` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 66 | `test_phase31_g99_reconsideration_lot_context_propagation.py::test_phase31_g99_actual_reconsideration_rows_receive_canonical_lot_context` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 67 | `test_phase31_g99_reconsideration_lot_context_propagation.py::test_phase31_g99_anchor_rows_no_longer_fail_for_missing_lot_context` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 68 | `test_phase31_g99_reconsideration_lot_context_propagation.py::test_phase31_g99_cash_defer_and_safety_terminal_preserved` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 69 | `test_phase31_g99_reconsideration_lot_context_propagation.py::test_phase31_g99_known_g80_weak_tail_not_resurrected` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 70 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_filled_bypass_cases_no_longer_publish_buy_new_competition[2022-11-04-76470]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 71 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_filled_bypass_cases_no_longer_publish_buy_new_competition[2022-12-26-94320]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 72 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_filled_bypass_cases_no_longer_publish_buy_new_competition[2023-04-19-94340]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 73 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_filled_bypass_cases_no_longer_publish_buy_new_competition[2023-05-15-76010]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 74 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_filled_bypass_cases_no_longer_publish_buy_new_competition[2023-05-31-21340]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 75 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_planned_only_bypass_cases_no_longer_publish_buy_new_competition[2023-03-02-93180]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 76 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_planned_only_bypass_cases_no_longer_publish_buy_new_competition[2023-03-10-93180]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 77 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_planned_only_bypass_cases_no_longer_publish_buy_new_competition[2023-04-14-94340]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 78 | `test_phase32_ck_reentry_buy_new_bypass_guard.py::test_phase32_ck_planned_only_bypass_cases_no_longer_publish_buy_new_competition[2023-04-14-45860]` | missing runtime artifact | artifact | artifact dependency | C_TEST_INFRA_ARTIFACT_DEPENDENCY | Missing file, not GN semantic |
| 79 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_83060_trend_momentum_reentry_passes_without_legacy_rank_penalty` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 80 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_broad_bq_penalty_removed_for_complete_context_but_ordinary_buy_can_block` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 81 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_portfolio_competition_rank5_special_penalty_removed` | `reentry_recovery_status NOT_APPLICABLE != PASS` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 82 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_hard_stop_enhanced_recovery_preserved` | `not_reentry != reentry_hard_stop_new_thesis_not_sufficient` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 83 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_genuine_unknown_strong_current_evidence_can_pass_without_buy_new_fallback` | `NOT_APPLICABLE != REENTRY_UNKNOWN_PRIOR_CONTEXT` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 84 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_genuine_unknown_weak_current_evidence_reviews` | `reentry_recovery_status NOT_APPLICABLE != REVIEW_REQUIRED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 85 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_recoverable_provenance_defect_does_not_become_unknown_release` | `NOT_APPLICABLE != RECOVERABLE_PROVENANCE_DEFECT` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |
| 86 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_existing_three_bd_cooldown_preserved` | `RECENT_EXIT_GUARD_CURRENT_PIT_REQUALIFIED != REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY cooldown |
| 87 | `test_phase32_cw_minimal_residual_reentry.py::test_phase32_cw_repeated_unresolved_churn_preserved` | `reentry_recovery_status NOT_APPLICABLE != FAIL_CLOSED` | REENTRY | REENTRY | F_UNRESOLVED | No direct GN edit to REENTRY recovery |

## BUY Priority Regression Search

BUY_PRIORITY_GN_REGRESSION_FOUND: NO_UNINTENDED_REGRESSION_CONFIRMED

Observed BUY-priority failure:

- `test_phase31_b4_strong_add_can_outrank_comparable_new_only_with_explicit_pit_lifecycle_evidence`

Classification:

- This is an obsolete expectation under GN.
- The failing expectation required ADD lifecycle quality to outrank a better
  Current Opportunity-ranked NEW.
- GN intentionally changed Production BUY priority to rank by Current PIT
  Opportunity before relationship materialization.

No failure in the 87 shows:

- canonical rank order collapse;
- NEW starvation;
- ADD starvation;
- held/flat asymmetry revival;
- old-history priority revival;
- accepted-increment dependency revival.

Focused GN tests covering those risks passed in Phase32-GN.

## SELL / Winner Regression Search

SELL_GN_REGRESSION_FOUND: NO_CONFIRMED

WINNER_GN_REGRESSION_FOUND: NO_CONFIRMED

The full-suite failures contain one SELL-shadow artifact dependency:

- `test_phase31_f1d_materialization_writes_only_diagnostic_shadow`

It fails with missing runtime artifact input, not an assertion showing changed
SELL / PM / Winner behavior.

The focused GN matrix already passed PM/SELL and Winner tests:

- `tests/strategy/test_phase22_d_position_management.py`
- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`
- `tests/strategy/test_phase32_ej_winner_position_size_adequacy_shadow.py`

## Sizing / Cash Regression Search

SIZING_GN_REGRESSION_FOUND: NO_CONFIRMED

CASH_GN_REGRESSION_FOUND: NO_CONFIRMED

Unresolved full-suite sizing/cash failures:

- three `phase22_pr_dynamic_capacity_asset_proportionality` failures
- three `phase22_f_capital_deployment` failures

These do not directly map to the GN MCV priority diff. They remain unresolved
because no clean pre-GN baseline was available.

Focused GN sizing/cash regression passed:

- Position Sizing
- Runtime Planning
- Cash competitor interaction
- lot-aware PS mapping

## ADD / G129 Regression Search

ADD_GN_REGRESSION_FOUND: NO_CONFIRMED

G129_GN_REGRESSION_FOUND: NO_CONFIRMED

Two ADD/lot failures appeared in the first post-GN full-suite run and were
attributed to rankless legacy fixtures being ordered by symbol after the GN
rank-first change. The compatibility fallback was corrected so rankless rows
use `construction_priority` as deterministic fallback only when no Current
Opportunity rank is present.

After that fix:

- the two ADD/lot failures disappeared;
- focused ADD/G129/lot bundles passed;
- no remaining failure shows ADD Safety bypass or G129 scope regression.

## REENTRY / Churn Regression Search

REENTRY_GUARD_GN_REGRESSION_FOUND: NO_CONFIRMED_BUT_UNRESOLVED_FAILURES_REMAIN

The 46 REENTRY-category failures are concentrated in:

- missing prior-exit fields supplied into opportunity rows;
- `semantic_buy_type` reported as `BUY_NEW` instead of `REENTRY`;
- `reentry_recovery_status` reported as `NOT_APPLICABLE`;
- cooldown expectation mismatch.

Static GN diff does not touch the REENTRY semantic/recovery/cooldown functions
or prior-exit materialization. Therefore direct GN causality is not confirmed.

But because no clean pre-GN full-suite baseline was available, these cannot be
proven pre-existing in this audit. They remain unresolved and block direct
Production promotion.

No failure proves:

- recent EXIT guard bypass caused by GN;
- immediate re-buy increase caused by GN;
- blocked REENTRY BUY_NEW fallback caused by GN;
- long-lived penalty revival caused by GN.

## Churn Post-GN Validation Contract

CHURN_POST_GN_VALIDATION_CONTRACT_DEFINED: YES

Short dynamic validation must measure:

- EXIT -> BUY business-day distance
- BUY -> EXIT -> BUY cycle count
- same-symbol repeated cycle count
- recent-exit guard activation count
- recent-exit guard block count
- recent-exit guard release count
- recent-exit guard bypass count
- re-buy Current PIT re-strength evidence
- pre/post GN BUY priority order preservation
- pre/post GN history-caused priority inversion count
- same-symbol churn by BUY_NEW versus BUY_ADD
- PM EXIT/HOLD/REDUCE exact-regression
- Winner Protection exact-regression
- Position Sizing exact-regression
- Cash semantic exact-regression
- ADD Safety/G129 exact-regression
- Runtime mapping exact-regression

Historical PnL must not tune guard threshold, rank cutoff, quality cutoff, Cash
percentage, BUY count, or sizing formula.

## Required Answers

FULL_SUITE_FAILURE_COUNT: 87

FAILURE_CLASSIFICATION_COMPLETE: YES

PRE_EXISTING_BASELINE_COUNT: 0_CONFIRMED

OBSOLETE_EXPECTATION_COUNT: 1

TEST_INFRA_ARTIFACT_DEPENDENCY_COUNT: 33

GN_INTENDED_EXPECTATION_CHANGE_COUNT: 1

GN_UNINTENDED_REGRESSION_COUNT: 0_CONFIRMED

UNRESOLVED_COUNT: 52

BUY_PRIORITY_GN_REGRESSION_FOUND: NO_UNINTENDED_REGRESSION_CONFIRMED

SELL_GN_REGRESSION_FOUND: NO_CONFIRMED

WINNER_GN_REGRESSION_FOUND: NO_CONFIRMED

SIZING_GN_REGRESSION_FOUND: NO_CONFIRMED

CASH_GN_REGRESSION_FOUND: NO_CONFIRMED

ADD_GN_REGRESSION_FOUND: NO_CONFIRMED

G129_GN_REGRESSION_FOUND: NO_CONFIRMED

REENTRY_GUARD_GN_REGRESSION_FOUND: NO_CONFIRMED_BUT_UNRESOLVED_REENTRY_FAILURES_REMAIN

RUNTIME_GN_REGRESSION_FOUND: NO_CONFIRMED

CHURN_POST_GN_VALIDATION_CONTRACT_DEFINED: YES

SHORT_DYNAMIC_VALIDATION_READY: NO

LONG_HORIZON_VALIDATION_READY: NO

DIRECT_PRODUCTION_PROMOTION_READY: NO

NEXT_STEP: establish a clean pre-GN/full-suite baseline or repair/skip deleted-artifact tests, then triage the 52 unresolved semantic failures before any short dynamic validation

## Final Judgment

No: this audit found no confirmed GN-unintended regression, but the full strategy suite does not yet prove GN introduced zero regressions across SELL, Winner, Sizing, Cash, ADD, G129, REENTRY, and Runtime because 52 non-artifact semantic failures remain unresolved without clean pre-GN baseline evidence.
