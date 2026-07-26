# Phase20-BW Historical Data Readiness Previous Trading Date Authority Fix

## Primary Judgment

`PHASE20_BW_HISTORICAL_DATA_READINESS_PREVIOUS_TRADING_DATE_AUTHORITY_DEFECT_CONFIRMED`

## Target Run

- run_id: `runtime-test-historical-extended-smoke-20260726T035744318910Z`
- business_date: `2022-08-12`
- stopped_stage: `data_readiness`
- exit_code: `20`

## Failing Condition

Data Readiness selected fallback calendar authority and resolved:

- `current_valuation_previous_trading_date`: `2022-08-11`
- `current_valuation_expected_date`: `2022-08-11`
- `current_actual_as_of`: `2022-08-10`
- `existing_valuation_as_of`: `2022-08-10`
- `current_valuation_temporal_authority`: `stale_current_valuation`
- `current_valuation_temporal_reason`: `current_valuation_older_than_previous_trading_day`

This was incorrect because `2022-08-11` is non-trading in the run-scoped J-Quants trading calendar. The Runtime Test business-date sequence also skipped it:

```text
2022-08-10
2022-08-12
```

The correct previous trading date for the `2022-08-12` morning evaluation is `2022-08-10`.

## Root Cause

Historical Data Readiness resolved the operation calendar through the generic operations calendar resolver using a base path that did not point at the run-scoped Historical Market Refresh authority.

As a result, it fell back to the built-in weekday/holiday fallback. That fallback does not encode the 2022 J-Quants holiday calendar and treated `2022-08-11` as the previous trading day.

## Correct Authority

The correct authority is the run-scoped Historical logical input manifest trading calendar:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260726T035744318910Z/daily/2022-08-12/market_refresh/inputs/historical_asof/2022-08-12/raw/jquants/trading_calendar/data.parquet
```

Authority evidence:

- `logical_input_manifest.status`: `PASS`
- `historical_asof_view.authorities[trading_calendar].status`: `PASS`
- `logical_cutoff`: `2022-08-12`
- `2022-08-11 HolDiv`: `0`
- resolved previous trading date: `2022-08-10`

## Fix

Historical Data Readiness now resolves previous trading date in this order:

1. Run-scoped Historical logical input manifest `logical_paths.trading_calendar`
2. Historical as-of view `trading_calendar` authority
3. Explicit Historical contract calendar under operations

If a Historical run-scoped authority exists but is invalid, non-PASS, path-missing, or unreadable, Data Readiness fails closed with missing trading-calendar authority instead of falling back to calendar-day subtraction or Production/Demo fallback.

Production/Demo calendar behavior is unchanged.

## Regression Coverage

- Historical `2022-08-12` morning current valuation: `valuation_as_of=2022-08-10`, previous trading date `2022-08-10`, current valuation `READY`
- Normal business day: `2022-08-10` previous trading date `2022-08-09`
- Weekend boundary: Monday previous trading date resolves to prior Friday
- Holiday boundary: `2022-08-11` non-trading, `2022-08-12` previous trading date `2022-08-10`
- Consecutive holiday boundary
- Missing Historical calendar authority fail-closed
- Invalid manifest no fallback
- Production/Demo fallback behavior unchanged

## Validation

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase20_bw_historical_data_readiness_calendar_authority.py
PASS: 5

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py tests/runtime_v2/test_phase20_bw_historical_data_readiness_calendar_authority.py
PASS: 17

PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/data_readiness.py
PASS
```

Long-running Historical tests were not executed.

## Non-Changed Scope

- Candidate AI
- Opportunity AI
- Position Management
- BUY/SELL threshold
- Capital Deployment Policy
- Current Valuation price calculation
- Ledger
- Corporate Action Guard
- Accepted Generation
- Training
- Calibration
- Safety Policy

## User Re-run Command

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2022-08-12 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

## Final Status

`PHASE20_BW_HISTORICAL_DATA_READINESS_PREVIOUS_TRADING_DATE_AUTHORITY_FIX_COMPLETE`

Phase20 closure can proceed after the user-owned long-running Historical revalidation confirms no downstream stop.
