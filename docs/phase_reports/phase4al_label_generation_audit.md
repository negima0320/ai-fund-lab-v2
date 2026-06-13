# Phase4-AL Label Generation Audit

## Audit Result

- status: complete
- readiness_status: `READY_FOR_DATASET_BUILDER`
- summary: `reports/candidate_ai/full_range/phase4al_label_generation_summary.json`

## Summary

- status: OK
- readiness_status: READY_FOR_DATASET_BUILDER
- label_generation_executed: True
- label_row_count: 167668
- label_column_count: 8
- future_return_5d_count: 167668
- future_return_10d_count: 167668
- future_return_20d_count: 167668
- future_max_return_20d_count: 167668
- future_max_drawdown_20d_count: 167668
- top_decile_20d_count: 16786
- downside_bad_20d_count: 32191
- momentum_candidate_label_count: 15830
- feature_table_modified: False
- feature_table_joined: False
- leakage_audit_status: OK
- recommended_next_action: Phase4-AM Dataset Builder: join feature and label tables only for training dataset; inference dataset must not include labels.

## Checks

- OK: `summary_exists`
- OK: `label_output_exists`
- OK: `manifest_exists`
- OK: `audit_exists`
- OK: `readiness_ready_for_dataset_builder`
- OK: `label_generation_executed`
- OK: `label_rows_positive`
- OK: `label_columns_present`
- OK: `label_output_under_runtime_labels`
- OK: `manifest_real_runtime`
- OK: `feature_table_not_modified`
- OK: `feature_table_not_joined`
- OK: `leakage_audit_ok`
- OK: `all_numeric_label_counts_positive`
- OK: `boolean_label_counts_recorded`
- OK: `dataset_training_inference_backtest_trading_not_executed`
- OK: `broker_order_paper_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks label generation only.
- It confirms labels are stored separately under `.runtime/candidate_ai/labels/`.
- It confirms the Phase4-AK feature table is not modified or joined.
- Phase4-AM may join features and labels only for a training dataset; inference datasets must not include labels.
