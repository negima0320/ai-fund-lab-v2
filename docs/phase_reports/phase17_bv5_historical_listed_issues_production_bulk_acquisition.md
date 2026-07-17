# Phase17-BV5 Historical Listed Issues Production Bulk Acquisition

## Executive Summary

Phase17-BV5 completed the production Historical Listed Issues bulk acquisition for Runtime v2. The accepted Trading Calendar authority selected 1221 trading days from 2021-07-16 through 2026-07-15. J-Quants `/v2/equities/master` snapshots were acquired into the production append-only snapshot store, not a probe root.

Final judgment: `PHASE17_BV5_HISTORICAL_LISTED_ISSUES_AUTHORITY_ACCEPTED`

## Acquisition Result

- Snapshot root: `.runtime/operations/jquants/historical_snapshots/listed_issues`
- Calendar source: `.runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet`
- Calendar content hash: `3f37d9ee53d7f8be050b6265f63a370150264a61f284e67b3fcd1008c0b1051b`
- Target business days: 1221
- API request count: 1221
- Fetched snapshots: 1221
- Skipped verified existing: 0
- Failed snapshots: 0
- Min snapshot date: 2021-07-16
- Max snapshot date: 2026-07-15
- Store schema hash distribution: `{'8cac33e2ee6cd9dd21d8c009fc6574dcfff69feab509bb9d12cbaf08457bc86e': 1221}`

## Validation

- Calendar alignment: `PASS`
- Index validation: `PASS`
- Missing snapshots: 0
- Invalid snapshots: 0
- Duplicate snapshots: 0
- Future snapshot usage: 0
- Provider date mismatches: 0

All 1221 target trading days have an exact-date, verified snapshot. No future snapshot was assigned to a past business date.

## Resolver Acceptance

Representative resolver validation status: `PASS`

Dates validated: 2021-07-16, 2022-01-04, 2023-01-04, 2024-01-04, 2025-01-06, 2026-06-29, 2026-07-06, 2026-07-15

Each representative date resolved with `selected_snapshot_date == business_date`, `future_snapshot_used=false`, `content_hash_verified=true`, and `row_count > 0`.

## Runtime Integration

Historical as-of integration status: `PASS`

For `business_date=2026-06-29`, Runtime v2 selected the production snapshot store path:

`.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-06-29/data.parquet`

The previous `listed_issues logical_view_empty` condition is resolved: row_count=4436, selected_snapshot_date=2026-06-29, future snapshot used=false.

## Tests

- Targeted BV2B/BV3/BV4/as-of tests: `37 passed in 3.91s`
- Full Runtime v2 regression: `904 passed in 23.30s`
- py_compile: PASS
- git diff --check: PASS
- JSON validation: PASS

## Prohibited Operations

BV5 did not run Runtime Test run/resume/reset/rollback/close, did not edit Frozen Runs, did not manually edit Ledger or Trading State, did not perform broker write/order submit/external notification, did not refetch OHLCV or Trading Calendar, did not run backtests, and did not promote probe roots as production authority.

## Evidence Files

- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/summary.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/acquisition_result.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/snapshot_inventory.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/calendar_alignment_validation.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/missing_invalid_snapshot_inventory.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/resolver_verification.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/runtime_integration_verification.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/2026_06_29_regression_readiness.json`
- `reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition/full_regression_verification.json`
- `reports/phase_reports/phase17_bv5_historical_listed_issues_production_bulk_acquisition.json`
