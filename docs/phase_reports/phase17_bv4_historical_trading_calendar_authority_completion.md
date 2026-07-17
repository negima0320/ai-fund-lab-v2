# Phase17-BV4 Historical Trading Calendar Authority Completion

## Executive Summary

 Final judgment: `PHASE17_BV4_TARGETED_FIX_REQUIRED`

Update after Phase17-BV4A: the operator acquired and validated the Historical Trading Calendar authority for `2021-07-16` through `2026-07-15`. Phase17-BV4A accepted the authority with `PHASE17_BV4_CALENDAR_AUTHORITY_ACCEPTED`.

Implemented and verified:

- Historical Trading Calendar authority store
- acquisition CLI
- resume/checkpoint behavior
- verified-existing skip
- validation contract
- canonical business-day consumer function
- BV3 Listed Issues acquisition compatibility
- targeted tests
- full `tests/runtime_v2` regression

Codex did not execute a real J-Quants API fetch. Because the calendar API retention boundary for `2021-07-16` was not confirmed, this phase cannot honestly be marked `PHASE17_BV4_CALENDAR_ACQUISITION_READY` yet.

## Current Gap

Current operational calendar:

```text
.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet
```

Coverage:

```text
2026-02-16 through 2026-07-15
```

Required window:

```text
2021-07-16 through 2026-07-15
```

The existing operational calendar was not overwritten.

## J-Quants Capability

Endpoint:

```text
/v2/markets/calendar
```

Existing client support:

- `JQuantsClient.fetch_all_trading_calendar`
- `from` / `to`
- `date`
- pagination
- range fetch preferred

Raw ingestor support already exists for `trading_calendar` range fetch.

## Store Contract

Formal root:

```text
.runtime/operations/jquants/historical_snapshots/trading_calendar/
```

Layout:

```text
data.parquet
manifest.json
index.json
acquisition_manifest.json
validation.json
```

Canonical consumer columns:

- `calendar_date`
- `is_trading_day`
- `holiday_division`
- `source`
- `endpoint`
- `fetched_at`

The store records source request range, response range, row count, unique date count, schema hash, content hash, endpoint, pagination metadata, duplicate date count, status distribution, and validation status.

## Validation

Fail-closed checks include:

- unreadable parquet
- unreadable manifest
- content hash mismatch
- duplicate `calendar_date`
- missing required coverage window

Calendar consumers use the canonical authority, not weekday inference or holiday-library inference.

## BV3 Integration

Fixture verification confirms BV3 Listed Issues acquisition target generation can use:

```text
.runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet
```

Expected after operator acquisition:

```text
calendar_coverage_status=PASS
calendar_min_date<=2021-07-16
calendar_max_date>=2026-07-15
```

Current runtime integration remains pending until the historical calendar is actually acquired.

## Operator Commands

Calendar acquisition candidate:

```bash
PYTHONPATH=src python3 scripts/acquire_historical_trading_calendar.py --calendar-root .runtime/operations/jquants/historical_snapshots/trading_calendar --start-date 2021-07-16 --end-date 2026-07-15 --storage-format parquet --max-pages 100 --retry-count 3 --sleep-seconds 1.0 --resume --skip-verified-existing --write-evidence
```

Post-acquisition validation:

```bash
PYTHONPATH=src python3 scripts/acquire_historical_trading_calendar.py --calendar-root .runtime/operations/jquants/historical_snapshots/trading_calendar --start-date 2021-07-16 --end-date 2026-07-15 --validate-only --write-evidence
```

BV3 dry-run after calendar acquisition:

```bash
PYTHONPATH=src python3 scripts/acquire_historical_listed_issues_snapshots.py --snapshot-root .runtime/operations/jquants/historical_snapshots/listed_issues --start-date 2021-07-16 --end-date 2026-07-15 --calendar-source .runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet --storage-format parquet --max-pages 100 --sleep-seconds 1.0 --retry-count 3 --resume --skip-verified-existing --write-evidence --dry-run
```

## Verification

Targeted:

```text
22 passed
```

Full Runtime v2:

```text
902 passed
```

Also passed:

- dry-run
- py_compile
- git diff --check
- JSON validation

## Prohibited Operations Confirmation

Not executed:

- real J-Quants bulk fetch
- Listed Issues bulk fetch
- Runtime Test run/resume/reset/rollback/close
- Frozen Run edit
- operational calendar overwrite
- probe artifact promotion
- Ledger edit
- Registry refresh
- broker write
- order submit
- external notification
- weekday-inference fake calendar generation
- future data back-application

## Evidence

- `reports/phase17_bv4_historical_trading_calendar_authority_completion/summary.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/current_calendar_gap.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/jquants_calendar_capability.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/calendar_store_contract.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/acquisition_plan.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/retention_boundary.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/validation_contract.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/bv3_integration_verification.json`
- `reports/phase17_bv4_historical_trading_calendar_authority_completion/operator_command.json`
- `reports/phase_reports/phase17_bv4_historical_trading_calendar_authority_completion.json`
