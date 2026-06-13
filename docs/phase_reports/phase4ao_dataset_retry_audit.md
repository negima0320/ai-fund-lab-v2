# Phase4-AO Dataset Builder Retry Audit

## Audit Result

- status: complete
- readiness_status: `READY_FOR_FIRST_LIGHTGBM_TRAINING`
- summary: `reports/candidate_ai/full_range/phase4ao_dataset_retry_summary.json`

## Summary

- status: OK
- readiness_status: READY_FOR_FIRST_LIGHTGBM_TRAINING
- feature_row_count: 253736
- label_row_count: 167668
- joined_row_count: 167668
- join_success_rate: 1.0
- train_row_count: 0
- validation_row_count: 0
- test_row_count: 167668
- feature_column_count: 13
- label_column_count: 8
- leakage_audit_status: OK
- future_column_detected_in_features: False
- label_column_detected_in_features: False
- recommended_next_action: Phase4-AP First LightGBM Training.

## Checks

- OK: `summary_exists`
- OK: `dataset_output_exists`
- OK: `manifest_exists`
- OK: `audit_exists`
- OK: `dataset_builder_executed`
- OK: `readiness_ready_for_first_lightgbm_training`
- OK: `joined_rows_positive`
- OK: `join_success_rate_positive`
- OK: `split_counts_recorded`
- OK: `test_split_has_rows_for_current_runtime`
- OK: `feature_label_separation_ok`
- OK: `leakage_audit_ok`
- OK: `no_future_columns_in_features`
- OK: `no_label_columns_in_features`
- OK: `manifest_counts_match_summary`
- OK: `training_inference_backtest_trading_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks dataset builder retry only.
- It confirms Phase4-AN historical feature rows join with Phase4-AL labels by target_date + code.
- It confirms feature columns and label columns remain prefixed and separated.
- It confirms training, inference, backtest, and trading are not executed.
