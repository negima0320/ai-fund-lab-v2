# Phase4-BB Long History Normalized Rebuild

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_FEATURE_REGENERATION`
- normalized_rebuild_executed: `True`
- raw_row_count: `5261207`
- normalized_row_count: `5066399`
- price_missing_excluded_count: `194808`
- normalization_error_count: `0`
- date range: `2021-06-14` to `2026-06-12`
- business_day_count: `1222`
- code_count: `4988`
- duplicate_date_code_count: `0`
- schema_mapping_status: `OK`
- data_source_type: `real_runtime`

## Output

- isolated_output_path: `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet`
- manifest_path: `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/manifest.json`
- output_format: `parquet`
- normalizer_version: `normalize_daily_quotes_v1`
- normalized_schema_version: `2`

## Safety

- mock_path_unchanged: `True`
- promotion_status: `not_promoted`
- promotion_performed: `False`
- reader_switch_performed: `False`
- feature_generation_executed: `False`
- label_generation_executed: `False`
- dataset_rebuild_executed: `False`
- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`
- broker_api_executed: `False`
- order_executed: `False`
- portfolio_auto_update_executed: `False`

## Coverage

- formal_training_coverage_sufficient_after_normalization: `True`
- first_trainable_target_date: `2021-09-09`
- last_label_target_date: `2026-05-15`

## Recommended Next Action

Proceed to Phase4-BC Long History Feature Regeneration on the isolated `real_runtime` normalized history. Do not train yet.
