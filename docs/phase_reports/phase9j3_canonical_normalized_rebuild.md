# Phase9-J3 Canonical Normalized Rebuild

- status: CANONICAL_NORMALIZED_READY
- target_data_until: 2026-06-18
- raw_source_path: `.runtime/data/raw/jquants/equities_bars_daily/responses`
- supplemental_raw_table: `.runtime/data/raw/jquants/equities_bars_daily/data.parquet`
- raw_coverage: 2021-06-14 to 2026-06-12
- supplemental_coverage: 2026-06-01 to 2026-06-18
- normalized_output_path: `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet`
- row_count: 5086522
- min_date: 2021-06-14
- max_date: 2026-06-18
- code_count: 5005
- duplicate_check_status: OK
- abnormal_price_check_status: OK
- future_row_check_status: OK
- readiness_status: READY
- lookback_ready: True
- config_before: .runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
- config_after: .runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
- config_updated: True
- feature_refresh_status: NOT_RUN
- candidate_eligible_rows: 0
- opportunity_non_null_feature_rows: 0

## Blocked Reasons

- none

## Warnings

- none

## Safety

- jquants_only_source_used: True
- model_retraining_executed: False
- inference_executed: False
- order_plan_generation_executed: False
- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- paper_ledger_fill_executed: False
- virtual_fill_executed: False

## Next Action

- Phase9-K model manifest / retrain eligibility review.
