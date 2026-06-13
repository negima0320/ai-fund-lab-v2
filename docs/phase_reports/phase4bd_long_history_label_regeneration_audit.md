# Phase4-BD Long History Label Regeneration Audit

- status: `complete`
- readiness_status: `READY_FOR_LONG_HISTORY_DATASET_REBUILD`
- summary: `reports/candidate_ai/full_range/phase4bd_long_history_label_regeneration_summary.json`

## Summary

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_DATASET_REBUILD`
- label_row_count: `4970227`
- label_column_count: `8`
- label_target_date_min: `2021-06-14`
- label_target_date_max: `2026-05-15`
- label_target_date_count: `1202`
- code_count: `4780`
- future_return_5d_count: `4970227`
- future_return_10d_count: `4970227`
- future_return_20d_count: `4970227`
- future_max_return_20d_count: `4970227`
- future_max_drawdown_20d_count: `4970227`
- top_decile_20d_count: `497577`
- downside_bad_20d_count: `759344`
- momentum_candidate_label_count: `477192`
- momentum_candidate_label_positive_rate: `0.09601`
- train_label_row_count_estimate: `3341627`
- validation_label_row_count_estimate: `1022775`
- test_label_row_count_estimate: `366245`
- train_positive_rate: `0.09606`
- validation_positive_rate: `0.09569`
- test_positive_rate: `0.095594`
- label_unavailable_tail_target_date_count: `1220`
- label_unavailable_tail_row_count: `96172`
- feature_table_modified: `False`
- feature_table_joined: `False`
- leakage_audit_status: `OK`
- recommended_next_action: `Phase4-BE Long History Dataset Rebuild: join feature and label tables for training only; inference datasets must not include labels.`

## Checks

- summary_exists: `True`
- label_output_exists: `True`
- manifest_exists: `True`
- audit_exists: `True`
- readiness_ready: `True`
- label_generation_executed: `True`
- label_rows_positive: `True`
- label_output_under_runtime_labels: `True`
- manifest_counts_match: `True`
- all_numeric_label_counts_positive: `True`
- boolean_label_counts_positive: `True`
- split_coverage_positive: `True`
- split_positive_rate_positive: `True`
- feature_table_not_modified: `True`
- feature_table_not_joined: `True`
- leakage_audit_ok: `True`
- no_downstream_execution: `True`
- secret_terms_not_emitted: `True`

## Scope Guard

- Label regeneration and label audit only.
- Label columns are stored separately under `.runtime/candidate_ai/labels/`.
- No dataset rebuild, training, inference, backtest, trading, promotion, reader switch, broker API, or order placement.
