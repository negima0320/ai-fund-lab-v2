# Phase4-Z Isolated Real Runtime Normalized Audit

## Audit Result

- status: complete
- coverage_status: `ISOLATED_REAL_RUNTIME_NORMALIZED_READY`
- summary: `reports/candidate_ai/full_range/phase4z_real_runtime_normalized_isolated_summary.json`

## Summary

- status: OK
- coverage_status: ISOLATED_REAL_RUNTIME_NORMALIZED_READY
- data_source_type: real_runtime
- isolated_output_path: .runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
- isolated_manifest_path: .runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/manifest.json
- default_mock_path_unchanged: True
- mock_history_overwritten: False
- promotion_performed: False
- row_count: 4231
- code_count: 4231
- date_min: 2026-06-01
- date_max: 2026-06-01
- business_day_count: 1
- schema_mapping_status: OK
- coverage_status_detail: isolated rebuild success but insufficient for 60-day Candidate feature generation

## Checks

- OK: `isolated_output_exists`
- OK: `isolated_manifest_exists`
- OK: `data_source_type_real_runtime`
- OK: `source_provider_jquants`
- OK: `api_call_not_performed`
- OK: `promotion_status_not_promoted`
- OK: `default_mock_path_unchanged`
- OK: `mock_history_not_overwritten`
- OK: `schema_mapping_ok`
- OK: `row_count_positive`
- OK: `code_count_positive`
- OK: `coverage_stats_produced`
- OK: `reader_switch_not_performed`
- OK: `label_generation_not_implemented`
- OK: `training_inference_backtest_trading_not_implemented`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks isolated normalized output only.
- It confirms no promotion, reader switch, default mock overwrite, API call, label generation, training, inference, backtest, trading, broker API, order placement, or Portfolio auto-update occurred.
