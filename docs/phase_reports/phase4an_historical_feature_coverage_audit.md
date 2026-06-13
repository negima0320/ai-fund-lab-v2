# Phase4-AN Historical Feature Coverage Audit

## Audit Result

- status: complete
- readiness_status: `READY_FOR_DATASET_BUILDER_RETRY`
- summary: `reports/candidate_ai/full_range/phase4an_historical_feature_coverage_summary.json`

## Summary

- status: OK
- readiness_status: READY_FOR_DATASET_BUILDER_RETRY
- feature_target_date_count: 60
- label_target_date_count: 40
- overlap_target_date_count: 40
- expected_feature_target_date_min: 2026-03-02
- expected_feature_target_date_max: 2026-04-27
- actual_feature_target_date_min: 2026-03-02
- actual_feature_target_date_max: 2026-05-29
- generated_historical_feature_row_count: 253736
- generated_historical_feature_date_count: 60
- eligible_count: 3866
- excluded_count: 249870
- schema_validation_status: OK
- leakage_audit_status: OK
- join_coverage_readiness: True
- recommended_next_action: Phase4-AO Dataset Builder Retry using the historical feature table.

## Checks

- OK: `summary_exists`
- OK: `historical_feature_output_exists`
- OK: `manifest_exists`
- OK: `audit_exists`
- OK: `readiness_ready_for_dataset_builder_retry`
- OK: `historical_feature_generation_executed`
- OK: `feature_rows_positive`
- OK: `feature_target_dates_cover_labels`
- OK: `overlap_target_dates_positive`
- OK: `schema_validation_ok`
- OK: `leakage_audit_ok`
- OK: `manifest_counts_match`
- OK: `no_forbidden_future_label_columns`
- OK: `label_dataset_training_inference_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks historical feature coverage only.
- It confirms label generation, dataset builder, training, inference, backtest, and trading are not executed.
- Phase4-AO may retry Dataset Builder using the historical feature table.
