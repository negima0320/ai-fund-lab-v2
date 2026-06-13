# Phase4-AJ Real Runtime Normalized Audit

## Audit Result

- status: complete
- readiness_status: `READY_FOR_REAL_RUNTIME_FEATURE_GENERATION`
- summary: `reports/candidate_ai/full_range/phase4aj_real_runtime_normalized_summary.json`

## Summary

- status: OK
- readiness_status: READY_FOR_REAL_RUNTIME_FEATURE_GENERATION
- raw_row_count: 266849
- normalized_row_count: 253736
- code_count: 4350
- date_min: 2026-03-02
- date_max: 2026-05-29
- business_day_count: 60
- normalization_error_count: 0
- price_missing_excluded_count: 13113
- schema_mapping_status: OK
- promotion_status: not_promoted
- promotion_performed: False
- reader_switch_performed: False
- mock_path_unchanged: True
- isolated_output_path: .runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
- recommended_next_action: Phase4-AK Real Runtime Feature Generation on isolated real_runtime normalized history; do not train yet.

## Checks

- OK: `summary_exists`
- OK: `isolated_output_exists`
- OK: `isolated_manifest_exists`
- OK: `readiness_ready_for_real_runtime_feature_generation`
- OK: `raw_row_count_positive`
- OK: `normalized_row_count_positive`
- OK: `raw_to_normalized_accounted_for`
- OK: `business_day_count_sufficient`
- OK: `code_count_positive`
- OK: `date_range_present`
- OK: `normalization_error_count_zero`
- OK: `schema_mapping_ok`
- OK: `manifest_row_count_matches_summary`
- OK: `manifest_data_source_real_runtime`
- OK: `manifest_schema_version_ok`
- OK: `promotion_status_not_promoted`
- OK: `promotion_not_performed`
- OK: `reader_switch_not_performed`
- OK: `mock_path_unchanged`
- OK: `feature_label_training_backtest_trading_not_executed`
- OK: `broker_order_paper_trading_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks isolated real_runtime normalized rebuild only.
- It confirms no promotion, reader switch, feature generation, label generation, dataset builder, training, inference, backtest, trading, Paper Trading, broker API, order placement, or Portfolio auto-update occurred.
- The mock normalized path under `.runtime/data/raw_normalized/jquants/equities_bars_daily/` must remain unchanged.
