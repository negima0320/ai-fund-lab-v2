# Phase4-AM Dataset Builder Audit

## Audit Result

- status: complete
- readiness_status: `BLOCKED_BY_JOIN_COVERAGE`
- summary: `reports/candidate_ai/full_range/phase4am_dataset_builder_summary.json`

## Summary

- status: BLOCKED
- readiness_status: BLOCKED_BY_JOIN_COVERAGE
- feature_row_count: 4350
- label_row_count: 167668
- joined_row_count: 0
- join_success_rate: 0.0
- train_row_count: 0
- validation_row_count: 0
- test_row_count: 0
- feature_column_count: 13
- label_column_count: 0
- leakage_audit_status: OK
- recommended_next_action: Generate a historical feature table for label target dates, then rerun Phase4-AM; do not train yet.

## Checks

- OK: `summary_exists`
- OK: `dataset_output_exists`
- OK: `manifest_exists`
- OK: `audit_exists`
- OK: `dataset_build_executed`
- OK: `feature_and_label_counts_recorded`
- OK: `join_result_valid`
- OK: `split_counts_recorded`
- OK: `feature_label_separation_ok`
- OK: `leakage_audit_ok`
- OK: `dataset_columns_prefixed_when_rows_exist`
- OK: `training_inference_backtest_trading_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks dataset build only.
- It confirms feature and label columns are prefixed and separated.
- It confirms training, inference, backtest, and trading are not executed.
- If current feature and label target dates do not overlap, readiness remains blocked by join coverage.
