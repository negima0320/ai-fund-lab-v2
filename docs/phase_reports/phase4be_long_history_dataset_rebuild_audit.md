# Phase4-BE Long History Dataset Rebuild Audit

- status: `complete`
- readiness_status: `READY_FOR_FORMAL_LIGHTGBM_TRAINING`
- summary: `reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json`

## Summary

- status: `OK`
- readiness_status: `READY_FOR_FORMAL_LIGHTGBM_TRAINING`
- joined_row_count: `4970227`
- join_success_rate: `1.0`
- train_row_count: `3341627`
- validation_row_count: `1022775`
- test_row_count: `366245`
- train_positive_rate: `0.09606`
- validation_positive_rate: `0.09569`
- test_positive_rate: `0.095594`
- feature_column_count: `13`
- label_column_count: `8`
- leakage_audit_status: `OK`
- train_all_null_feature_count: `0`
- train_constant_feature_count: `0`
- train_high_null_feature_count: `0`
- train_feature_variance_available: `True`
- validation_feature_variance_available: `True`
- test_feature_variance_available: `True`
- recommended_next_action: `Phase4-BF Formal LightGBM Training using this long-history training dataset.`

## Checks

- summary_exists: `True`
- dataset_output_exists: `True`
- manifest_exists: `True`
- audit_exists: `True`
- readiness_ready: `True`
- dataset_rebuild_executed: `True`
- joined_rows_positive: `True`
- join_success_rate_positive: `True`
- split_rows_positive: `True`
- split_positives_positive: `True`
- feature_label_counts_positive: `True`
- no_future_or_label_in_features: `True`
- no_feature_in_labels: `True`
- leakage_audit_ok: `True`
- train_feature_quality_ok: `True`
- validation_test_variance_ok: `True`
- manifest_counts_match: `True`
- no_downstream_execution: `True`
- secret_terms_not_emitted: `True`

## Scope Guard

- Dataset rebuild and dataset audit only.
- Labels are joined only into the training dataset with `label__` prefixes.
- Inference datasets must not include labels.
- No training, inference, backtest, trading, promotion, reader switch, broker API, or order placement.
