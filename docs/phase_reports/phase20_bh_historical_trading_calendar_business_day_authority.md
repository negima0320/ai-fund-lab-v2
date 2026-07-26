# Phase20-BH Historical Trading Calendar Business-Day Authority Fix

## Status

```text
PHASE20_BH_HISTORICAL_TRADING_CALENDAR_BUSINESS_DAY_AUTHORITY_READY
```

## Scope

Phase20-BGでHistorical Acquisitionのcoverage policyを `expected_business_date_range` に分離した後、既存run `jquants-acquisition-20210802-20260714-bf` は `chunk-0005` で停止した。

本Phaseでは、Production Freshness Policyを弱めず、Historical coverageのexpected business datesをTrading Calendar authorityから正しく導出するよう修正した。

## Root Cause

Production Market Refresh Coreのper-date fetchでは、daily quotes取得前に既存raw trading calendarからtarget datesを計算していた。対象chunkのcalendarは同じrefresh内で後から取得されるため、2021-12-31のJ-Quants calendar区分がtarget datesへ反映されなかった。

その結果、2021-12-31はJ-Quants Trading Calendar上 `HolDiv=0` で非営業日にもかかわらず、weekday fallback相当で `required_dates` に含まれた。

混同されていた概念:

- `latest_trading_calendar_date`: calendar datasetの最終レコード日
- `last_expected_business_date`: calendar authorityで営業日と判定された最終日

`chunk-0005` の旧状態:

- start_date: 2021-12-01
- end_date: 2021-12-31
- old coverage_end_date: 2021-12-31
- old expected_business_date_count: 23
- old blocked_reasons: `requested_end_coverage_missing`

## Trading Calendar Evidence

Existing run artifact:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bf/raw/jquants/trading_calendar/data.parquet
```

Schema fields observed:

- `Date`: calendar record date
- `HolDiv`: J-Quants holiday division / business-day classification
- `source`: lineage
- `endpoint`: source endpoint
- metadata fields: `pagination_page`, `target_date`, `code`, `business_key`, `fetched_at`

Observed 2021 year-end rows:

| Date | HolDiv | Historical business day after fix |
| --- | --- | --- |
| 2021-12-29 | 1 | yes |
| 2021-12-30 | 1 | yes |
| 2021-12-31 | 0 | no |

## Implementation

Changed files:

- `src/ai_fund_lab_v2/paper_trading/market_data_refresh.py`
- `src/ai_fund_lab_v2/runtime_v2/market_data_acquisition.py`
- `scripts/runtime_test.py`
- `tests/paper_trading/test_phase9i_market_data_refresh.py`
- `tests/runtime_v2/test_phase20_bh_historical_trading_calendar_business_day_authority.py`

Key changes:

- Production Market Refresh per-date mode fetches Trading Calendar before deriving target daily quote dates.
- `_business_dates()` now receives the newly fetched calendar records plus existing calendar records.
- `required_dates` excludes `HolDiv=0` holiday rows when calendar authority covers the requested period.
- `MarketDataRefreshResult` now exposes `first_required_date` and `last_required_date`.
- Historical `validate_staging_source()` persists `first_expected_business_date`, `last_expected_business_date`, and `expected_business_dates`.
- runtime-test market-data-acquisition evidence path now targets Phase20-BH evidence.

No changes were made to:

- Production Runtime freshness fail-closed
- `DATA_FRESHNESS_BLOCKED` semantics
- daily quote normalization
- schema authority
- OHLC integrity logic
- Broker, Training, Calibration, Runtime common market data publish

## Existing Run Revalidation

Read-only revalidation of `chunk-0005` using existing Trading Calendar artifact:

- calendar authority expected first business date: 2021-12-01
- calendar authority expected last business date: 2021-12-30
- expected business date count: 22
- normalized latest date: 2021-12-30
- J-Quants lineage: PASS
- validation status: PASS
- blocked_reasons: []

Therefore, after this patch, resume can revalidate `chunk-0005` from existing staging if local artifacts are unchanged, then continue from `chunk-0006`. It must not refetch `chunk-0001` through `chunk-0004`.

## Validation

Executed short checks only:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache PYTHONPATH=src:. python3 -m pytest tests/runtime_v2/test_phase20_bh_historical_trading_calendar_business_day_authority.py -q
```

Result:

```text
7 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache PYTHONPATH=src:. python3 -m pytest tests/runtime_v2/test_phase20_bc_jquants_market_data_acquisition.py tests/runtime_v2/test_phase20_bd_jquants_daily_quotes_request_contract.py tests/runtime_v2/test_phase20_be_jquants_acquisition_normalization_connection.py tests/runtime_v2/test_phase20_bf_production_market_refresh_reuse.py tests/runtime_v2/test_phase20_bg_historical_freshness_policy_separation.py tests/runtime_v2/test_phase20_bh_historical_trading_calendar_business_day_authority.py tests/paper_trading/test_phase9i_market_data_refresh.py -q
```

Result:

```text
41 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache PYTHONPATH=src:. python3 -m py_compile src/ai_fund_lab_v2/paper_trading/market_data_refresh.py src/ai_fund_lab_v2/runtime_v2/market_data_acquisition.py scripts/runtime_test.py tests/runtime_v2/test_phase20_bh_historical_trading_calendar_business_day_authority.py tests/paper_trading/test_phase9i_market_data_refresh.py
```

Result:

```text
PASS
```

## User Resume Command

Codex did not run the long acquisition resume. User-side command:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py market-data-acquisition resume \
  --run-id jquants-acquisition-20210802-20260714-bf \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

Expected checks:

- completed chunk count
- first non-completed chunk
- chunk-0001 to chunk-0004 are not refetched
- chunk-0005 passes
- coverage_end is the final business date, 2021-12-30
- Historical output does not treat Production freshness block as coverage failure
- `runtime_market_data_mutated=false`
- final_judgment

## Acceptance

```text
TRADING_CALENDAR_BUSINESS_DAY_AUTHORITY_USED
HOLIDAY_ROWS_EXCLUDED_FROM_EXPECTED_BUSINESS_DATES
COVERAGE_END_EQUALS_LAST_EXPECTED_BUSINESS_DATE
PRODUCTION_FRESHNESS_FAIL_CLOSED_PRESERVED
PRODUCTION_NORMALIZATION_AUTHORITY_PRESERVED
RESUME_CONTRACT_PRESERVED
UNIT_AND_REGRESSION_PASS
RUNTIME_COMMON_MARKET_DATA_NOT_MUTATED
BROKER_ACCESS_NOT_PERFORMED
HEAVY_ACQUISITION_NOT_EXECUTED_BY_CODEX
```
