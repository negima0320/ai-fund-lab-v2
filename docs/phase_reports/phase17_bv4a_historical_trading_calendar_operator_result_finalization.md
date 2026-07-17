# Phase17-BV4A Historical Trading Calendar Operator Result Finalization

## Executive Summary

Final judgment: `PHASE17_BV4_CALENDAR_AUTHORITY_ACCEPTED`

The operator-acquired Historical Trading Calendar authority is valid and accepted.

Codex did not re-fetch J-Quants data. Validation was read-only against the saved authority.

## Calendar Authority

Accepted authority:

```text
.runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet
```

Validation:

```text
status=PASS
min_date=2021-07-16
max_date=2026-07-15
row_count=1826
unique_date_count=1826
trading_day_count=1221
duplicate_date_count=0
missing_required_dates=[]
content_hash_verified=true
```

Content hash:

```text
3f37d9ee53d7f8be050b6265f63a370150264a61f284e67b3fcd1008c0b1051b
```

Schema hash:

```text
717a0cbcb4b81c4cc81d7545eb0c514c8de47446ac85187a1954692be9fcca07
```

Endpoint:

```text
/v2/markets/calendar
```

Request classification:

```text
FETCH_SUPPORTED_FULL_RANGE
```

## Circular Reference Classification

Classification:

```text
OUTPUT_SERIALIZATION_ONLY
```

Root cause:

The CLI progress callback stored the same result payload object that was later augmented with `progress_records`. This created a self-reference only when printing/writing the operator-facing JSON result.

The saved calendar parquet, manifest, index, and validation artifacts were already complete and hash-verified. No calendar reacquisition is required.

Fix:

- `progress_records` now stores a JSON-safe deep copy.
- `write_json()` serializes a JSON-safe payload.
- Mock CLI main test confirms `acquisition_result.json` writes without circular reference.

## BV3 Readiness

BV3 dry-run against the accepted calendar authority now reports:

```text
calendar_coverage_status=PASS
target_business_day_count=1221
estimated_api_requests=1221
```

BV3 Listed Issues bulk acquisition can proceed.

## Verification

```text
BV4 CLI targeted: 11 passed
BV3/BV4 targeted: 24 passed
full tests/runtime_v2: 904 passed
py_compile: PASS
git diff --check: PASS
JSON validation: PASS
```

Calendar authority hashes were preserved before/after the output serialization fix.

## Prohibited Operations Confirmation

Not executed by Codex:

- J-Quants API refetch
- Runtime Test run/resume/reset/rollback/close
- `.runtime` manual edit
- Calendar parquet/manifest/index manual edit
- Listed Issues bulk fetch
- broker write
- order submit
- external notification

## Evidence

- `reports/phase17_bv4a_historical_trading_calendar_operator_result_finalization/summary.json`
- `reports/phase17_bv4a_historical_trading_calendar_operator_result_finalization/operator_result.json`
- `reports/phase17_bv4a_historical_trading_calendar_operator_result_finalization/calendar_authority_validation.json`
- `reports/phase17_bv4a_historical_trading_calendar_operator_result_finalization/output_serialization_classification.json`
- `reports/phase_reports/phase17_bv4a_historical_trading_calendar_operator_result_finalization.json`
