# AI Fund Lab vNext Phase1 Completion Report

## Purpose

Phase1 built the Data Foundation for J-Quants raw ingestion, runtime storage, schema validation, manifest tracking, Parquet operation, and normalized raw handoff. It intentionally did not implement AI decision logic, feature calculation, future labels, backtests, paper trading, broker integration, or orders.

## Implemented Phases

- Phase1-A: Python minimum structure, settings, RuntimePaths, MarketDataStore, Feature Builder entry, storage_report, tests, README.
- Phase1-A-Fix1: J-Quants client timeout/auth/rate-limit error handling and secret-safe tests.
- Phase1-B: J-Quants V2 raw endpoint methods, pagination, raw ingestion, daily fetch CLI, missing-data log entry.
- Phase1-B-LiveSmoke: Manual live smoke CLI separated from pytest.
- Phase1-C: Trading calendar service, fetch plan builder, raw quality report.
- Phase1-D: Raw store hardening, schema validation, manifest, diff summary.
- Phase1-E: Parquet backend, safe migration, manifest query CLI.
- Phase1-F: Raw operations checks, validation drilldown, refetch plan, parquet readiness.
- Phase1-G: daily_quotes normalized raw schema v2 and raw_normalized storage.
- Phase1-H: final audit, excluded daily quote classification, completion report.

## Main Modules

- `ai_fund_lab_v2.config.settings`
- `ai_fund_lab_v2.runtime.paths`
- `ai_fund_lab_v2.data_sources.jquants.client`
- `ai_fund_lab_v2.data_sources.jquants.raw_ingestion`
- `ai_fund_lab_v2.data_store.market_data_store`
- `ai_fund_lab_v2.data_store.schema`
- `ai_fund_lab_v2.data_store.storage_backends`
- `ai_fund_lab_v2.data_store.manifest`
- `ai_fund_lab_v2.data_quality.trading_calendar`
- `ai_fund_lab_v2.data_quality.fetch_plan`
- `ai_fund_lab_v2.data_quality.raw_quality`
- `ai_fund_lab_v2.data_quality.normalization`
- `ai_fund_lab_v2.data_quality.daily_quote_exclusions`
- `ai_fund_lab_v2.data_quality.phase1_audit`

## Main CLIs

- `scripts/fetch_jquants_daily.py`
- `scripts/smoke_jquants_api.py`
- `scripts/check_jquants_raw_quality.py`
- `scripts/migrate_raw_storage.py`
- `scripts/show_jquants_manifest.py`
- `scripts/inspect_raw_validation.py`
- `scripts/build_jquants_refetch_plan.py`
- `scripts/check_parquet_readiness.py`
- `scripts/normalize_jquants_raw.py`
- `scripts/inspect_daily_quote_exclusions.py`
- `scripts/audit_phase1_completion.py`
- `scripts/write_phase1_completion_report.py`
- `scripts/storage_report.py`

## Storage Layout

- Raw: `.runtime/data/raw/jquants/`
- Normalized raw: `.runtime/data/raw_normalized/jquants/`
- Features: `.runtime/data/features/`
- Future labels: `.runtime/data/labels/`
- Logs: `.runtime/logs/`
- Cache: `.runtime/cache/`
- Reports: `.runtime/reports/`
- Manifest: `.runtime/data/raw/jquants/manifest.jsonl`

## J-Quants Endpoints

- `/v2/equities/bars/daily`
- `/v2/equities/master`
- `/v2/markets/calendar`
- `/v2/fins/summary`

## Raw And Normalized Raw Policy

Raw data remains immutable source evidence under `.runtime/data/raw`. daily_quotes raw schema v1 keeps strict `O/H/L/C/Vo` validation and may remain `ERROR` when upstream raw lacks those fields. Phase1-G adds `daily_quotes_normalized` schema v2 under `.runtime/data/raw_normalized`, with `Open/High/Low/Close/Volume`, `PriceSource`, and `SchemaVersion=2`.

Phase2 feature builders should read normalized raw, not raw v1 daily quotes directly. Future labels remain separate and are not generated in Phase1.

## Daily Quote Exclusion Policy

- raw daily_quotes records: 2
- normalized daily_quotes records: 1
- excluded records: 1
- missing patterns: `{'all_ohlcv_and_adjusted_ohlcv_missing': 1}`
- estimated reasons: `{'unknown_not_joined_to_listed_issues': 1}`

Do not treat excluded records as normal without a market-data reason. Keep raw v1 unchanged, keep excluded records out of normalized raw, and investigate unknown/no-price-volume records before Phase2 features.

Phase2 feature builders should read daily_quotes_normalized only. Excluded raw records must not enter feature or AI inputs unless a later data-quality rule explicitly normalizes them.

## Manifest Policy

Fetch, migration, and normalization events are appended to the J-Quants manifest. Request params are sanitized. API keys, tokens, Authorization values, and x-api-key values are not written.

## Parquet Policy

Parquet is available for raw and normalized raw storage. JSONL remains readable for migration and inspection. Parquet readiness is checked before considering Parquet as the default raw format.

## Runtime And Secret Policy

Runtime outputs are centralized under `.runtime`. `.env` and `.runtime` are excluded from Git. `.env.example` is the only tracked credential template. Secrets must not appear in stdout, stderr, logs, reports, or manifest.

## Tests

The normal test suite uses mocks and fixtures and does not call the live J-Quants API. Live smoke remains manual CLI only.

## Explicitly Not Implemented In Phase1

- AI decision body
- Feature calculation body
- `future_return_*` label generation
- AI training
- Backtest
- Paper trading
- Broker integration
- Tachibana integration
- Order placement
- News/SNS/LLM decision AI
- v1 model/profile/backtest carryover

## Completion Decision

- audit_status: NG
- decision: 未完了

Phase1 can be treated as conditionally complete when normalized raw is used as the Phase2 input and the excluded daily quote records remain excluded until a later quality rule justifies inclusion.

## Phase2 Entry Conditions

- Use `daily_quotes_normalized` as the initial price input.
- Keep raw v1 as source evidence only.
- Do not use excluded daily quote records as feature inputs.
- Keep future labels separate from features.
- Continue running `python3 -m pytest` before moving to feature work.

## First Phase2 Task

Define the minimal feature contract that reads normalized raw and produces non-AI, non-label feature tables under `.runtime/data/features`, with strict prevention of future information leakage.
