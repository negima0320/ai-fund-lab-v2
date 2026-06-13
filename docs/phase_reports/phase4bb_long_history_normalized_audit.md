# Phase4-BB Long History Normalized Audit

- status: `complete`
- readiness_status: `READY_FOR_LONG_HISTORY_FEATURE_REGENERATION`
- summary: `reports/candidate_ai/full_range/phase4bb_long_history_normalized_summary.json`

## Summary

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_FEATURE_REGENERATION`
- raw_row_count: `5261207`
- normalized_row_count: `5066399`
- price_missing_excluded_count: `194808`
- normalization_error_count: `0`
- date_min: `2021-06-14`
- date_max: `2026-06-12`
- business_day_count: `1222`
- code_count: `4988`
- duplicate_date_code_count: `0`
- schema_mapping_status: `OK`
- mock_path_unchanged: `True`
- promotion_status: `not_promoted`
- promotion_performed: `False`
- reader_switch_performed: `False`
- formal_training_coverage_sufficient_after_normalization: `True`
- isolated_output_path: `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet`
- recommended_next_action: `Phase4-BC Long History Feature Regeneration on isolated real_runtime normalized history; do not train yet.`

## Checks

- summary_exists: `True`
- isolated_output_exists: `True`
- manifest_exists: `True`
- readiness_ready: `True`
- normalized_rebuild_executed: `True`
- raw_row_count_positive: `True`
- normalized_row_count_positive: `True`
- raw_to_normalized_accounted_for: `True`
- normalization_error_count_zero: `True`
- schema_mapping_ok: `True`
- duplicate_date_code_zero: `True`
- business_day_count_positive: `True`
- manifest_row_count_matches_summary: `True`
- manifest_data_source_real_runtime: `True`
- manifest_phase_ok: `True`
- formal_training_coverage_sufficient: `True`
- mock_path_unchanged: `True`
- promotion_not_performed: `True`
- reader_switch_not_performed: `True`
- no_downstream_execution: `True`
- secret_terms_not_emitted: `True`

## Scope Guard

- Normalized rebuild only.
- No promotion, reader switch, feature generation, label generation, dataset rebuild, training, inference, backtest, trading, Paper Trading, broker API, or order placement.
- Mock normalized path remains unchanged.
