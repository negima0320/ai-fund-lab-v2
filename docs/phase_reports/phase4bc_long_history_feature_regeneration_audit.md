# Phase4-BC Long History Feature Regeneration Audit

- status: `complete`
- readiness_status: `READY_FOR_LONG_HISTORY_LABEL_REGENERATION`
- summary: `reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json`

## Summary

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_LABEL_REGENERATION`
- feature_row_count: `5066399`
- eligible_count: `4784948`
- excluded_count: `281451`
- target_date_min: `2021-06-14`
- target_date_max: `2026-06-12`
- target_date_count: `1222`
- feature_column_count: `13`
- schema_validation_status: `OK`
- leakage_audit_status: `OK`
- all_null_feature_count_train: `0`
- constant_feature_count_train: `0`
- near_constant_feature_count_train: `0`
- high_null_feature_count_train: `0`
- all_null_feature_count_validation: `0`
- constant_feature_count_validation: `0`
- high_null_feature_count_validation: `0`
- all_null_feature_count_test: `0`
- constant_feature_count_test: `0`
- high_null_feature_count_test: `0`
- at_null_constant_problem_resolved: `True`
- recommended_next_action: `Phase4-BD Long History Label Regeneration: regenerate labels in a physically separate label table.`

## Checks

- summary_exists: `True`
- feature_output_exists: `True`
- manifest_exists: `True`
- audit_exists: `True`
- readiness_ready: `True`
- feature_generation_executed: `True`
- feature_rows_positive: `True`
- schema_validation_ok: `True`
- leakage_audit_ok: `True`
- no_forbidden_future_label_columns: `True`
- train_all_null_resolved: `True`
- train_variance_available: `True`
- at_problem_resolved: `True`
- manifest_counts_match: `True`
- no_downstream_execution: `True`
- secret_terms_not_emitted: `True`
- train_quality_payload_present: `True`

## Scope Guard

- Feature regeneration and feature quality audit only.
- No label generation, dataset rebuild, training, inference, backtest, trading, promotion, reader switch, broker API, or order placement.
