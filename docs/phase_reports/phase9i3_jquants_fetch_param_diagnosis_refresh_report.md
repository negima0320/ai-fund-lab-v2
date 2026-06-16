# Phase9-I Market Data Refresh Report

- status: PARTIAL_AVAILABLE
- from_date: 2026-06-02
- to_date: 2026-06-16
- dry_run: False
- allow_api_fetch: True
- fetch_mode: per-date
- data_until: 2026-06-15

## Endpoints

| endpoint | status | existing_latest | fetched_rows | rows | max_date | raw_path | normalized_path |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| daily_quotes | COMPLETED | 2026-06-01 | 44491 | 48940 | 2026-06-15 | `.runtime/data/raw/jquants/equities_bars_daily/data.parquet` | `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet` |
| listed_info | COMPLETED | 2026-06-01 | 4446 | 8895 | 2026-06-16 | `.runtime/data/raw/jquants/listed_issues/data.parquet` | `` |
| trading_calendar | COMPLETED | 2026-06-07 | 15 | 81 | 2026-06-16 | `.runtime/data/raw/jquants/trading_calendar/data.parquet` | `` |

## Readiness

- status: NOT_READY
- data_until: 2026-06-15
- blocked_reasons: data_until_before_decision_for
- latest_successful_daily_quotes_date: 2026-06-15
- latest_normalized_daily_quotes_date: 2026-06-15
- latest_listed_info_date: 2026-06-16
- latest_trading_calendar_date: 2026-06-16

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

## Blocked Reasons

- data_until_before_decision_for

## Warnings

- daily_quotes_normalization_status=ERROR
