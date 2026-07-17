# Phase17-BV3 Historical Listed Issues Production Snapshot Store

## Executive Summary

Final judgment: `PHASE17_BV3_TARGETED_FIX_REQUIRED`

The formal Historical Listed Issues snapshot foundation is implemented and tested:

- append-only production snapshot store
- bulk acquisition CLI
- resume/checkpoint behavior
- verified-existing skip
- store index rebuild and validation
- common Historical resolver using `latest_snapshot_not_after_business_date`
- Runtime v2 Historical as-of integration
- targeted tests and full `tests/runtime_v2` regression

No real J-Quants bulk fetch was executed by Codex.

The remaining blocker is not the Listed Issues store implementation. The configured Trading Calendar authority only covers:

```text
2026-02-16 through 2026-07-15
```

Therefore it cannot generate the full 2021-07-16 through 2026-07-15 acquisition target list. The operator bulk command is ready after a full historical trading calendar parquet is supplied.

## Store Contract

Formal root:

```text
.runtime/operations/jquants/historical_snapshots/listed_issues/
```

Layout:

```text
snapshots/<snapshot_date>/data.parquet
snapshots/<snapshot_date>/manifest.json
index.json
latest.json
acquisition_manifest.json
```

Each manifest records:

- requested date
- provider effective date
- snapshot date
- row count
- schema hash
- content hash
- endpoint
- fetched_at
- pagination metadata
- storage format/path
- duplicate key count
- validation status
- classification
- previous snapshot diff
- future snapshot flag

Same `snapshot_date` plus same `content_hash` is idempotent. Same `snapshot_date` with different content is not overwritten.

## Resolver Contract

Selection policy:

```text
latest_snapshot_not_after_business_date
```

Fail-closed conditions include:

- missing index
- empty store
- no snapshot not after business date
- future snapshot selected
- snapshot age too old
- missing artifact
- content hash mismatch
- manifest date mismatch
- manifest future leakage
- non-historical mode

The resolver is Historical-only and does not replace Demo/Production current-day master authority.

## Runtime Integration

`resolve_historical_market_data_asof()` now uses the formal snapshot store when:

```text
<operations_root>/jquants/historical_snapshots/listed_issues/index.json
```

exists. If not, legacy operational raw behavior is preserved.

Runtime Test still performs no J-Quants fetch; it can only consume pre-acquired snapshots.

## Dry-Run Result

Command executed without API fetch:

```bash
PYTHONPATH=src python3 scripts/acquire_historical_listed_issues_snapshots.py --snapshot-root .runtime/operations/jquants/historical_snapshots/listed_issues --start-date 2021-07-16 --end-date 2026-07-15 --calendar-source .runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet --storage-format parquet --max-pages 100 --sleep-seconds 1.0 --retry-count 3 --resume --skip-verified-existing --write-evidence --dry-run
```

Result:

```text
dry-run PASS
calendar_coverage_status=REVIEW_REQUIRED
calendar_min_date=2026-02-16
calendar_max_date=2026-07-15
estimated_api_requests=102
```

This is intentionally not treated as full 2021-07-16 coverage.

## Operator Command After Calendar Fix

```bash
PYTHONPATH=src python3 scripts/acquire_historical_listed_issues_snapshots.py --snapshot-root .runtime/operations/jquants/historical_snapshots/listed_issues --start-date 2021-07-16 --end-date 2026-07-15 --calendar-source <FULL_HISTORICAL_TRADING_CALENDAR_PARQUET> --storage-format parquet --max-pages 100 --sleep-seconds 1.0 --retry-count 3 --resume --skip-verified-existing --write-evidence
```

## Verification

Targeted:

```text
13 passed
```

Related regression:

```text
26 passed
```

Full Runtime v2:

```text
893 passed
```

Also passed:

- `py_compile`
- `git diff --check`
- acquisition CLI dry-run
- JSON evidence validation

## Prohibited Operations Confirmation

Not executed:

- real J-Quants bulk fetch
- Runtime Test run/resume/reset/rollback/close
- Frozen Run edit
- existing formal `.runtime` data manual edit
- probe artifact promotion
- Ledger edit
- Registry refresh
- broker write
- order submit
- external notification
- future snapshot back-application

## Evidence

- `reports/phase17_bv3_historical_listed_issues_production_snapshot_store/summary.json`
- `reports/phase17_bv3_historical_listed_issues_production_snapshot_store/store_contract.json`
- `reports/phase17_bv3_historical_listed_issues_production_snapshot_store/resolver_contract.json`
- `reports/phase17_bv3_historical_listed_issues_production_snapshot_store/acquisition_plan.json`
- `reports/phase17_bv3_historical_listed_issues_production_snapshot_store/api_request_estimate.json`
- `reports/phase17_bv3_historical_listed_issues_production_snapshot_store/test_inventory.json`
- `reports/phase17_bv3_historical_listed_issues_production_snapshot_store/operator_command.json`
- `reports/phase_reports/phase17_bv3_historical_listed_issues_production_snapshot_store.json`
