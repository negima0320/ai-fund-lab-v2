# Phase23-X: Fins Summary Legacy-Key Cleanup and Clean Materialization Validation

## 1. Primary Judgment

```text
PHASE23_X_FINS_SUMMARY_CLEAN_MATERIALIZATION_VALIDATED
```

Legacy code-only `fins_summary` rows for `2026-07-06..2026-07-17` were safely removed from raw parquet. Clean raw materialization is now present in `.runtime/data/raw/jquants/fins_summary/data.parquet`.

## 2. Secondary Judgment

```text
FINANCIAL_CONSUMER_VALIDATION_PASS_OPERATIONS_PROMOTION_REVIEW_REQUIRED
```

Corporate Event financial statement consumption passed against the cleaned raw file, including `DiscNo` propagation and source reference uniqueness. Overall Corporate Event status remains `REVIEW_REQUIRED` because other source coverage conditions still require review.

## 3. Phase23 Status

```text
PHASE23_CONTINUES
```

No Phase23 closure, Phase24 handoff, Runtime Switch, Broker Write, or 10BD execution was performed.

## 4. Legacy-Key Inventory

Pre-cleanup inventory:

```text
total_rows = 980
target_range_legacy_rows = 474
target_range_repaired_rows = 494
target_range_unknown_rows = 0
outside_range_legacy_rows = 12
```

Post-cleanup inventory:

```text
total_rows = 506
target_range_legacy_rows = 0
target_range_repaired_rows = 494
target_range_unknown_rows = 0
outside_range_legacy_rows = 12
```

## 5. Cleanup Scope

Deleted rows matched all conditions:

```text
endpoint == /v2/fins/summary
DiscDate or target_date within 2026-07-06..2026-07-17
business_key == Code
```

Repaired rows, out-of-range rows, unknown key rows, manifests, and other endpoints were retained.

## 6. Migration / Repair CLI

Added reusable CLI:

```text
scripts/repair_jquants_raw_business_keys.py
```

It supports:

```text
--endpoint fins_summary
--from-date
--to-date
--runtime-dir
--dry-run
--backup-dir
--confirm
```

Live execution requires `--confirm`.

## 7. Backup

Backup was created:

```text
.runtime/backups/phase23_x_fins_summary_legacy_key_cleanup/20260729T033845Z/
```

Backup contains:

```text
data.parquet
manifest.jsonl
pre_cleanup_summary.json
pre_cleanup_hashes.json
repair_result.json
```

## 8. Atomicity

The CLI writes to a temporary parquet file, reads it back, validates count and schema, then atomically replaces the target file. Failure test confirms original parquet and manifest remain unchanged if validation fails.

## 9. Count Reconciliation

```text
980 - 474 = 506
```

Expected clean count matched actual post-cleanup count.

## 10. Post-Cleanup Raw Quality

Post-cleanup:

```text
schema validation = OK
raw quality = OK
row_count = 506
target_range_row_count = 494
target_range_legacy_rows = 0
target_range_repaired_rows = 494
target_range_unknown_rows = 0
duplicate DiscDate+Code+DiscNo = 0
duplicate target_date+business_key+endpoint = 0
```

## 11. Manifest Contract

Manifest history was not deleted or rewritten.

Cleanup evidence is stored in the backup directory, not as a rewritten fetch manifest. Existing fetch manifest remains append-only.

## 12. Idempotency

Second live execution returned:

```text
status = NO_CHANGE
legacy_rows_removed = 0
row_count = 506
hash unchanged
```

## 13. Corporate Event Validation

Short validation for `2026-07-06` used cleaned raw `fins_summary`.

Result:

```text
financial_event_count = 27
source_reference_unique = true
revision_id_non_empty_count = 27
source_reference_with_revision_id_count = 27
latest_fallback_used = false
future_leakage_used = false
```

Overall artifact status remains `REVIEW_REQUIRED` due to non-`fins_summary` coverage conditions.

## 14. Operations Promotion Readiness

Clean raw `fins_summary` is ready for operator promotion review.

Promotion was not executed. Current blockers:

```text
operations fins_summary missing
operations earnings_calendar missing
Corporate Event overall status remains REVIEW_REQUIRED pending source coverage review
```

## 15. Operations Runbook更新

Updated:

```text
docs/03_operations/jquants_data_operations_runbook.md
```

Added legacy key cleanup dry-run/live commands, backup, count reconciliation, manifest handling, raw quality, promotion conditions, and rollback.

## 16. Short Validation

```text
py_compile PASS
cleanup/raw-quality targeted tests: 56 passed
broad J-Quants/Corporate Event regression: 90 passed
repair CLI --help PASS
dry-run on .runtime PASS
live cleanup on .runtime PASS
idempotency PASS
inspect_raw_validation PASS
check_jquants_raw_quality PASS
Corporate Event financial consumer validation PASS
```

## 17. 10BD Gate

```text
NOT_READY_FOR_10BD_FINS_SUMMARY_OPERATIONS_PROMOTION_AND_CE_REVIEW_REQUIRED
```

10BD was not executed.

## 18. Next Operator Action

Review Phase23-X Evidence, then decide whether to promote cleaned `fins_summary` and `earnings_calendar` raw files to operations paths using the runbook. After promotion, rerun Corporate Event Validation Gate before reconsidering 10BD.
