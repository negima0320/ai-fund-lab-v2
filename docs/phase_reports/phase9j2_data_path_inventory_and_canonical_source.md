# Phase9-J2 Data Path Inventory and Canonical Source

- judgment: CANONICAL_NORMALIZED_MISSING
- phase9_previous_normalized_path: `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet`
- lookback_shortfall_cause: REFERENCE_PATH_MISMATCH_LONG_RAW_EXISTS_BUT_CANONICAL_NORMALIZED_MISSING
- canonical_config_path: `config/phase9_data_sources.yaml`

## Adopted Canonical Paths

- raw_daily_quotes: `.runtime/data/raw/jquants/equities_bars_daily/responses`
- normalized_daily_quotes: `null`
- listed_info: `.runtime/data/raw/jquants/listed_issues/data.parquet`
- trading_calendar: `.runtime/data/raw/jquants/trading_calendar/data.parquet`

## Key Candidates

### Raw Daily Quotes

| path | type | rows | min_date | max_date | codes | usable | reason |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| `.runtime/data/raw/jquants/equities_bars_daily/data.parquet` | raw_daily_quotes | 48940 | 2026-06-01 | 2026-06-15 | 4453 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/responses` | raw_daily_quotes_response_dir | 1305 | 2021-06-14 | 2026-06-12 | 0 | True | long_raw_responses_available_requires_normalization |
| `.runtime/data/raw/jquants/equities_bars_daily/request_manifests/2026-06-12.json` | raw_daily_quotes | 1 | 2026-06-12 | 2026-06-12 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/responses/2026-06-12_page_001.json` | raw_daily_quotes | 1 | 2026-06-12 | 2026-06-12 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/request_manifests/2026-06-11.json` | raw_daily_quotes | 1 | 2026-06-11 | 2026-06-11 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/responses/2026-06-11_page_001.json` | raw_daily_quotes | 1 | 2026-06-11 | 2026-06-11 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/request_manifests/2026-06-10.json` | raw_daily_quotes | 1 | 2026-06-10 | 2026-06-10 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/responses/2026-06-10_page_001.json` | raw_daily_quotes | 1 | 2026-06-10 | 2026-06-10 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/request_manifests/2026-06-09.json` | raw_daily_quotes | 1 | 2026-06-09 | 2026-06-09 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/responses/2026-06-09_page_001.json` | raw_daily_quotes | 1 | 2026-06-09 | 2026-06-09 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/request_manifests/2026-06-08.json` | raw_daily_quotes | 1 | 2026-06-08 | 2026-06-08 | 0 | True | jquants_derived |
| `.runtime/data/raw/jquants/equities_bars_daily/responses/2026-06-08_page_001.json` | raw_daily_quotes | 1 | 2026-06-08 | 2026-06-08 | 0 | True | jquants_derived |

### Normalized Daily Quotes

| path | type | rows | min_date | max_date | codes | usable | reason |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet` | normalized_daily_quotes | 46378 | 2026-06-01 | 2026-06-15 | 4270 | True | jquants_derived |
| `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet` | normalized_daily_quotes | 4231 | 2026-06-01 | 2026-06-01 | 4231 | True | jquants_derived |
| `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/manifest.json` | normalized_daily_quotes | 1 |  |  | 0 | True | jquants_derived |

### Listed Info

| path | type | rows | min_date | max_date | codes | usable | reason |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| `.runtime/data/raw/jquants/listed_issues/data.parquet` | listed_info | 8895 | 2026-06-01 | 2026-06-16 | 4454 | True | jquants_derived |
| `.runtime/data/raw/jquants/listed_issues/data.jsonl` | listed_info | 4449 | 2026-06-01 | 2026-06-01 | 4449 | True | jquants_derived |

### Trading Calendar

| path | type | rows | min_date | max_date | codes | usable | reason |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| `.runtime/data/raw/jquants/trading_calendar/data.parquet` | trading_calendar | 81 | 2026-03-02 | 2026-06-16 | 1 | True | jquants_derived |
| `.runtime/data/raw/jquants/trading_calendar/data.jsonl` | trading_calendar | 72 | 2026-03-02 | 2026-06-07 | 1 | True | jquants_derived |
| `reports/candidate_ai/full_range/phase4af_trading_calendar_correction_fetch_extension_plan_summary.json` | trading_calendar | 1 |  |  | 0 | False | not_jquants_derived |
| `reports/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan_audit.json` | trading_calendar | 1 |  |  | 0 | False | not_jquants_derived |

## Canonical Sources

- raw_daily_quotes: source=config usable=True path=`.runtime/data/raw/jquants/equities_bars_daily/responses`
- normalized_daily_quotes: source=missing usable=False path=`null`
- listed_info: source=config usable=True path=`.runtime/data/raw/jquants/listed_issues/data.parquet`
- trading_calendar: source=config usable=True path=`.runtime/data/raw/jquants/trading_calendar/data.parquet`
- candidate_features: source=config usable=True path=`.runtime/phase9/features/2026-06-15/candidate_features.parquet`
- opportunity_features: source=config usable=True path=`.runtime/phase9/features/2026-06-15/opportunity_feature_input.parquet`
- position_features: source=config usable=True path=`.runtime/phase9/features/2026-06-15/position_feature_input.parquet`
- capital_policy_inputs: source=config usable=True path=`.runtime/phase9/features/2026-06-15/capital_policy_input.parquet`
- model_manifests: source=missing usable=False path=`null`

## Prohibited Actions

- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- paper_ledger_fill_executed: False
- virtual_fill_executed: False
- model_retraining_executed: False
- inference_executed: False
- order_plan_generation_executed: False
- full_backtest_executed: False
