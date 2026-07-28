# Phase22-QD — End-to-End Data Completeness, Materialization, Source Lineage, and Silent Default Audit

## Executive Summary

Primary Judgment: `PHASE22_QD_MULTIPLE_CRITICAL_DATA_GAPS_IDENTIFIED`

This was an independent Evidence Review only. No code fix, Runtime Switch, artifact lifecycle promotion, consumer eligibility promotion, broker connection/write, production/demo submit, or new historical runtime was performed.

The audit confirms multiple critical Phase22 closure blockers remain. They are concentrated in Strategy Shadow input materialization, config/source lineage, corporate event coverage, accepted-generation historical authority, and empty-portfolio readiness. The existing 5BD Runtime evidence itself is present for the audited run and remains broker-write false / runtime-switch false, but Strategy Shadow is not ready for runtime consumption.

## Audit Scope

- Run ID: `runtime-test-historical-smoke-20260728T023230953202Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260728T023230953202Z`
- Audited dates: 2026-07-06, 2026-07-07, 2026-07-08, 2026-07-09, 2026-07-10
- Method: existing evidence JSON inspection, repo-wide static search, config inventory, lineage review, PIT/date authority review, and offline validation only.

## End-to-End Data Inventory

All expected daily Strategy Shadow artifacts exist for each audited business day: market context, corporate event, portfolio policy, dynamic position count, dynamic cash/exposure, portfolio construction, position management, capital deployment, position sizing, runtime planning, input manifest, source manifest, evidence index, summary, decision trace, and legacy comparison.

Existing runtime sections also have daily evidence directories for market refresh, data readiness, current valuation refresh, morning, sell planning, submit, execution, and runtime state refresh. This supports the historical Runtime PASS result already established by prior evidence, but it does not close Strategy Shadow consumer eligibility.

Detailed inventory: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/end_to_end_data_inventory.json`.

## Required vs Materialized

Materialized artifacts are present, but required inputs are not fully materialized or hash-backed:

- `position_sizing` uses a blank-path `price_volatility` source with `price_volatility_review_required` on all 5 days.
- `position_management` uses a blank-path `technical_features` source with `technical_features_review_required` on all 5 days.
- `portfolio_construction` and `capital_deployment` cite `configs/strategy/portfolio_policy.json` but record empty `policy_config` source hashes downstream.
- `runtime_planning` remains `REVIEW_REQUIRED` with unresolved quantity and mapping reason codes.

Detailed matrix: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/required_vs_materialized_matrix.json`.

## Config Existence and Dead References

`configs/strategy/portfolio_policy.json` is an active Strategy Shadow reference and is missing. Existing referenced configs include market context, dynamic position count, dynamic cash/exposure, position sizing, safety portfolio limits, and runtime v2 capital deployment.

The missing portfolio policy config is not merely a file inventory issue: `shadow_runtime._portfolio_policy_config()` constructs a BALANCED/MAINTAIN/NEUTRAL fallback when the file is absent, then downstream artifacts cite the missing path. This is classified as a confirmed silent-default authority defect for Strategy Shadow.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/config_existence_audit.json`, `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/dead_config_reference_audit.json`.

## Silent Default Audit

Confirmed defect:

- Missing `configs/strategy/portfolio_policy.json` silently becomes a default policy object in Strategy Shadow.

Review-required static hits:

- Strategy Shadow current/cash/exposure summaries coerce missing numeric ledger fields to zero while treating an existing `state.json` as PASS.
- Runtime readonly execution normalization also coerces missing cash/position numeric fields to zero. In this historical no-broker run this is not confirmed as a production defect, but it must be explicitly governed before switch readiness.
- Technical features and price volatility are explicit `REVIEW_REQUIRED` synthetic summaries, not silent PASS, but they are materialization gaps.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/silent_default_static_audit.json`.

## Runtime Evidence Missing/Empty Audit

No required daily Strategy Shadow JSON artifact was missing. Runtime evidence directories and JSON files are present across the 5 audited business days.

The incompleteness is semantic, not file-existence based: several artifacts are generated as DRAFT/NOT_ELIGIBLE and carry `REVIEW_REQUIRED` source roles or empty source hashes.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/runtime_evidence_missing_empty_audit.json`.

## Source Lineage

Source lineage gaps are confirmed:

- `position_management`: blank hash/path for `technical_features`.
- `position_sizing`: blank hash/path for `price_volatility` and blank `capital_deployment` because sizing references capital deployment as downstream in the shadow chain.
- `portfolio_construction` and `capital_deployment`: blank `policy_config` hash caused by missing portfolio policy config.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/source_lineage_audit.json`.

## PIT and Date Authority

`source_manifest.pit_validation.status` is `PASS` for all audited dates and no `DIRECT_SOURCE_PIT_VIOLATION` remains after PIT PASS classification.

Feature Date Authority is sourced from `completed_runtime_job_feature_date_command_resolution` for all dates. On 2026-07-09, selected/materialized feature date is 2026-07-09 while planned feature date is 2026-07-08, so `planned_matches_materialized=false`. Authority status is still PASS, but this mismatch should remain visible as audit evidence.

Historical Accepted Generation authority remains unresolved for closure: prior QB/PZ evidence identified accepted generation effective_from 2026-07-20 against 2026-07-06 through 2026-07-10 runtime dates, and the daily input manifests do not expose enough effective_from/status fields to independently close that concern from file existence alone.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/pit_date_authority_audit.json`.

## Generated vs Actually Used

All Phase22 Strategy artifacts are generated, but not all generated artifacts are eligible or usable downstream. Downstream components correctly propagate non-eligibility rather than becoming runtime consumers.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/data_usage_audit.json`.

## Existing Runtime Completeness

Existing 5BD runtime evidence is complete enough to preserve the established Historical Runtime PASS / NOT_HALTED / broker_write false / runtime_switch false conclusion. QD found no additional broker mutation or runtime-switch evidence.

However, related offline validation exposed an existing empty-current data-readiness failure: `tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py::test_phase17_x_data_readiness_accepts_pending_safety_authority_and_empty_current_pm` expected `READY` but returned `REVIEW_REQUIRED`. QD did not repair this.

This does not imply strategy production readiness because Strategy Shadow remains DRAFT and NOT_ELIGIBLE.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/existing_runtime_data_completeness_audit.json`.

## Learning Input Contamination

No confirmed learning-input contamination was found in this audit.

PnL, ledger, broker, realized/unrealized, benchmark, and execution terms found in the repo are used in runtime observability, PM held-position inference/evaluation, labels, or leakage audits. This audit did not find evidence that broker/paper/backtest/current portfolio/PnL data is used as Candidate or Opportunity training/inference input in violation of the J-Quants-only learning constraint.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/learning_input_contamination_audit.json`.

## Initial Empty Portfolio Path

Runtime v2 mainline has empty-current authority code, but current QD validation found a related existing test failure. Strategy Shadow also does not yet prove the initial empty portfolio path: latest Strategy PM artifacts still include `position_management_shadow_positions_required`.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/initial_empty_portfolio_data_path.json`.

## New Gaps

- `QD-GAP-07`: Runtime Planning quantity/membership mapping remains unresolved in Strategy Shadow.
- `QD-GAP-08`: Missing numeric-to-zero coercions need explicit switch-readiness authority review.
- `QD-GAP-09`: Existing empty-current sell-planning data readiness test currently returns `REVIEW_REQUIRED` where the test expects `READY`.

## Known Gaps Confirmed

- `QD-GAP-01`: price volatility materialization missing.
- `QD-GAP-02`: PM technical features materialization missing.
- `QD-GAP-03`: portfolio policy config missing plus silent default fallback.
- `QD-GAP-04`: corporate event coverage PARTIAL.
- `QD-GAP-05`: accepted generation historical PIT/effective_from review remains unresolved.
- `QD-GAP-06`: Strategy Shadow initial empty portfolio path not proven.

## Gap Severity Classification

Critical: `QD-GAP-01`, `QD-GAP-02`, `QD-GAP-03`.

High: `QD-GAP-04`, `QD-GAP-05`, `QD-GAP-06`, `QD-GAP-09`.

Medium: `QD-GAP-07`, `QD-GAP-08`.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/gap_classification.json`.

## Closure Recovery Plan

Recommended repair order:

1. Materialize PIT-valid price volatility with source path/hash lineage.
2. Materialize Strategy PM technical features or wire existing PM feature evidence with explicit source hashes.
3. Replace portfolio policy missing-file fallback with explicit config authority in a repair task.
4. Complete or explicitly contract corporate event partial coverage semantics.
5. Expose accepted generation effective_from/status in daily input manifests/evidence index and prove historical PIT eligibility.
6. Repair/prove the empty-current data-readiness path and add isolated Strategy Shadow empty-portfolio validation before any switch-readiness review.

Evidence: `reports/phase22_qd_end_to_end_data_completeness_materialization_source_lineage_and_silent_default_audit/closure_recovery_plan.json`.

## Recommended Next Task

Recommended next task: repair the data materialization and authority gaps before any closure, switch, or Phase23 readiness review. The immediate target should be price volatility, technical features, and portfolio policy config authority because they directly drive downstream DRAFT/NOT_ELIGIBLE Strategy Shadow status.

## Non-Readiness Statement

Phase22 complete: NO.

Phase23 ready: NO.

Runtime Switch ready: NO.

Strategy production ready: NO.
