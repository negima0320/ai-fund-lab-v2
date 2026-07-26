# Phase20-BG Historical Acquisition Freshness Policy Separation

## Status

```text
PHASE20_BG_HISTORICAL_FRESHNESS_POLICY_SEPARATION_READY
```

## Scope

Phase20-BFでHistorical Market Data AcquisitionをProduction Market Refresh Coreのthin adapterへ接続した後、長期取得run `jquants-acquisition-20210802-20260714-bf` が `chunk-0003` で停止した。

本Phaseでは、Production/Demo Runtimeの鮮度fail-closedを弱めず、Historical Acquisitionだけがrequested period coverageを判定するよう責務を分離した。

## Root Cause

`chunk-0003` は 2021-10-01 から 2021-10-31 の月次chunkである。2021-10-31は非営業日で、Production Market Refresh Coreの取得対象最終営業日は 2021-10-29 だった。

確認結果:

- `data_until_before_decision_for`: `paper_trading.market_data_readiness.check_market_data_readiness()` が `data_until < decision_for` の場合に生成するProduction Runtime readiness reason
- `DATA_FRESHNESS_BLOCKED`: `paper_trading.market_data_refresh._execute_refresh()` がProduction freshness blockを集約したreason
- `requested_end_coverage_missing`: Historical Acquisitionの `validate_staging_source()` がliteral requested end dateである 2021-10-31 までnormalized coverageを要求していたため生成

既存staging artifact:

- raw rows: 256,172
- normalized rows: 248,495
- normalized min date: 2021-08-02
- normalized max date: 2021-10-29
- duplicate date/code keys: 0
- J-Quants lineage: PASS

## Policy Separation

Production Market Refresh Core remains authoritative for:

- J-Quants API access
- raw artifact generation
- normalization
- schema validation
- OHLC integrity
- lineage metadata
- available coverage metadata

Production Runtime Readiness Policy remains fail-closed:

- `data_until < decision_for` remains `NOT_READY`
- `data_until_before_decision_for` is not suppressed
- `DATA_FRESHNESS_BLOCKED` is not globally disabled

Historical Acquisition Readiness Policy now evaluates:

- normalized artifact exists
- schema comparison PASS
- OHLC integrity PASS
- J-Quants lineage PASS
- normalized min date <= first expected business date
- normalized max date >= last expected business date

When expected business dates are available from the Production refresh result, Historical coverage uses `expected_business_date_range`. It does not require calendar-month-end coverage when month end is not an expected trading date.

## Implementation

Changed files:

- `src/ai_fund_lab_v2/runtime_v2/market_data_acquisition.py`
- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase20_bg_historical_freshness_policy_separation.py`

Key changes:

- `validate_staging_source()` accepts `expected_business_dates`
- Historical chunk validation compares coverage against first/last expected business date
- Historical final validation aggregates expected business dates from chunk refresh metadata
- J-Quants lineage is explicitly validated in Historical staging validation
- `NORMALIZATION_FAILED` chunks can be revalidated from existing staging artifacts before refetch
- COMPLETED / RAW_READY chunks remain skipped on resume when artifacts are valid
- runtime-test market-data-acquisition evidence path now targets Phase20-BG evidence

No changes were made to:

- Production freshness policy
- Production/Demo fail-closed behavior
- Production Market Refresh Core normalization authority
- runtime common market data publication
- Broker, Training, Calibration, Historical run execution

## Existing Run Resume Judgment

Existing run:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bf
```

Current state:

- chunk-0001: COMPLETED
- chunk-0002: COMPLETED
- chunk-0003: NORMALIZATION_FAILED
- chunk-0004 and later: PENDING

Read-only revalidation of chunk-0003 existing staging artifact:

- status: PASS
- coverage_policy: expected_business_date_range
- coverage_start_date: 2021-10-01
- coverage_end_date: 2021-10-29
- expected_business_date_count: 21
- blocked_reasons: []
- jquants_lineage: PASS

Therefore, after this patch, resume can revalidate chunk-0003 from existing staging if the local artifacts are unchanged, then continue from chunk-0004. It must not refetch chunk-0001 or chunk-0002.

## Validation

Executed short checks only:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache PYTHONPATH=src:. python3 -m pytest tests/runtime_v2/test_phase20_bg_historical_freshness_policy_separation.py -q
```

Result:

```text
6 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache PYTHONPATH=src:. python3 -m pytest tests/runtime_v2/test_phase20_bc_jquants_market_data_acquisition.py tests/runtime_v2/test_phase20_bd_jquants_daily_quotes_request_contract.py tests/runtime_v2/test_phase20_be_jquants_acquisition_normalization_connection.py tests/runtime_v2/test_phase20_bf_production_market_refresh_reuse.py tests/runtime_v2/test_phase20_bg_historical_freshness_policy_separation.py tests/paper_trading/test_phase9i_market_data_refresh.py -q
```

Result:

```text
34 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache PYTHONPATH=src:. python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/market_data_acquisition.py scripts/runtime_test.py tests/runtime_v2/test_phase20_bg_historical_freshness_policy_separation.py
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

- chunk-0001 and chunk-0002 remain skipped
- chunk-0003 is revalidated or, only if artifact incomplete, refetched
- Historical validation does not block on Production `data_until_before_decision_for`
- runtime common market data is not mutated
- Broker access remains NOT_PERFORMED

## Acceptance

```text
PRODUCTION_RUNTIME_FRESHNESS_FAIL_CLOSED_PRESERVED
HISTORICAL_ACQUISITION_FRESHNESS_POLICY_SEPARATED
REQUESTED_PERIOD_COVERAGE_USES_EXPECTED_BUSINESS_DATES
MONTH_END_NON_BUSINESS_DAY_COVERAGE_PASS
MISSING_BUSINESS_DAY_COVERAGE_BLOCKS
SCHEMA_INVALID_BLOCKS
JQUANTS_LINEAGE_MISSING_BLOCKS
COMPLETED_CHUNKS_SKIP_ON_RESUME
FAILED_CHUNK_REVALIDATION_FROM_EXISTING_STAGING_SUPPORTED
COMMON_RUNTIME_MARKET_DATA_NOT_MUTATED
LONG_RUNNING_ACQUISITION_NOT_EXECUTED_BY_CODEX
```
