# Phase9-I Market Data Refresh Report

- status: DRY_RUN
- from_date: 2026-06-02
- to_date: 2026-06-16
- dry_run: True
- allow_api_fetch: False

## Endpoints

| endpoint | status | existing_latest | fetched_rows | rows | max_date | raw_path | normalized_path |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| daily_quotes | DRY_RUN | 2026-06-01 | 0 | 0 |  | `.runtime/data/raw/jquants/equities_bars_daily/data.parquet` | `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet` |
| listed_info | DRY_RUN | 2026-06-01 | 0 | 0 |  | `.runtime/data/raw/jquants/listed_issues/data.parquet` | `` |
| trading_calendar | DRY_RUN | 2026-06-07 | 0 | 0 |  | `.runtime/data/raw/jquants/trading_calendar/data.parquet` | `` |

## Readiness

- status: NOT_READY
- data_until: 2026-06-01
- blocked_reasons: data_until_before_decision_for

## Safety Flags

- jquants_api_fetch_executed: False
- feature_generation_executed: False
- model_retraining_executed: False
- inference_executed: False
- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- virtual_fill_executed: False
- live_order_allowed: False
