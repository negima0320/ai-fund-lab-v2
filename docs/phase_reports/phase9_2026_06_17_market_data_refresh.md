# Phase9-I Market Data Refresh Report

- status: MARKET_DATA_READY_FOR_LATEST_AVAILABLE
- from_date: 2026-06-17
- to_date: 2026-06-17
- dry_run: False
- allow_api_fetch: True
- fetch_mode: per-date
- data_until: 2026-06-17

## Endpoints

| endpoint | status | existing_latest | fetched_rows | rows | max_date | raw_path | normalized_path |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| daily_quotes | COMPLETED | 2026-06-16 | 4446 | 57832 | 2026-06-17 | `.runtime/data/raw/jquants/equities_bars_daily/data.parquet` | `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet` |
| listed_info | COMPLETED | 2026-06-16 | 4446 | 13341 | 2026-06-17 | `.runtime/data/raw/jquants/listed_issues/data.parquet` | `` |
| trading_calendar | COMPLETED | 2026-06-16 | 1 | 82 | 2026-06-17 | `.runtime/data/raw/jquants/trading_calendar/data.parquet` | `` |

## Readiness

- status: READY
- data_until: 2026-06-17
- blocked_reasons: 
- latest_successful_daily_quotes_date: 2026-06-17
- latest_normalized_daily_quotes_date: 2026-06-17
- latest_listed_info_date: 2026-06-17
- latest_trading_calendar_date: 2026-06-17

## Safety Flags

- jquants_api_fetch_executed: True
- feature_generation_executed: False
- model_retraining_executed: False
- inference_executed: False
- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- virtual_fill_executed: False
- live_order_allowed: False

## Warnings

- daily_quotes_normalization_status=ERROR
