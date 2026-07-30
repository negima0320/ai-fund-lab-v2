# Phase23-W: Fins Summary Business Key Authority and Source-Row Collapse Investigation

## 1. Primary Judgment

```text
PHASE23_W_FINS_SUMMARY_SOURCE_ROW_COLLAPSE_REVIEW_REQUIRED
```

The 20 collapsed source rows cannot be classified as exact duplicates or distinct disclosures from the current persisted artifacts. The pre-dedup source rows were not retained in parquet, manifest, or secret-safe logs.

## 2. Secondary Judgment

```text
PHASE23_W_FINS_SUMMARY_DISCLOSURE_IDENTITY_KEY_REPAIRED_SHORT_VALIDATION_PASS
```

The old `fins_summary` raw key was not a valid disclosure identity. The Production-common key now preserves J-Quants disclosure identity.

## 3. Phase23 Status

```text
PHASE23_CONTINUES
```

No Phase23 closure, Phase24 handoff, Runtime Switch, Broker Write, or 10BD execution was performed.

## 4. Operator Fetch Summary

Operator fetch range:

```text
2026-07-06..2026-07-17
```

Manifest entries were generated for 10 business days. Six dates had `validation_status=WARNING` and `duplicate_key_count > 0`.

## 5. Count Reconciliation

```text
existing parquet rows = 12
API fetch records_saved total = 494
persisted parquet rows = 486
12 + 494 - 486 = 20
```

The 20-row delta matches the manifest duplicate-key total.

## 6. Current Business Key

Before Phase23-W, storage uniqueness was:

```text
target_date
business_key
endpoint
```

For `fins_summary`, `target_date` defaulted to `DiscDate`, and `business_key` defaulted to `Code`. The effective old key was:

```text
DiscDate + Code + endpoint
```

`DiscNo`, `DiscTime`, `DocType`, `CurPerType`, and period fields were not part of the old raw upsert key.

## 7. Collapse Point

The collapse point is:

```text
MarketDataStore.upsert dict overwrite by (target_date, business_key, endpoint)
```

The API client appends paginated rows. Schema validation reports duplicate keys but does not drop records. The parquet writer writes the already-merged dictionary values.

## 8. Duplicate Group Classification

Actual 20 collapsed rows:

```text
UNRESOLVED
```

Reason: only post-collapse parquet and aggregate manifest diagnostics exist. The discarded source rows are unavailable, so exact duplicate vs distinct disclosure cannot be proven after the fact without re-fetch/capture.

## 9. Disclosure Identity Contract

New Production-common raw identity:

```text
DiscDate + Code + DiscNo
```

Fallback when `DiscNo` is absent:

```text
DiscDate + Code + DiscTime + DocType + CurPerType + CurPerSt + CurPerEn + CurFYSt + CurFYEn
```

JPX describes J-Quants as providing corporate financial information, including quarterly financial statement data. J-Quants Pro financial statement docs expose disclosure date/time and issue code fields, and the official J-Quants Python client exposes `get_fin_summary` / `get_fin_summary_range`.

References:

- https://www.jpx.co.jp/english/markets/other-data-services/j-quants-api/index.html
- https://jpx.gitbook.io/j-quants-pro/api-reference/statements
- https://github.com/J-Quants/jquants-api-client-python

## 10. PIT / Revision Contract

`fins_summary` raw must retain multiple same-day same-company disclosures:

```text
corrections
earnings forecast revisions
dividend forecast revisions
financial statements
other DocType rows
```

Raw storage must not latest-only aggregate by `Code`, `DiscDate`, or `DiscDate + Code`.

## 11. Corporate Event Consumer Impact

Before Phase23-W, Corporate Event financial statement `source_reference` used:

```text
code + date + doc_type
```

It now includes `DiscNo` and propagates it as `revision_id`:

```text
code + date + DiscNo + doc_type
```

This preserves distinct disclosure authority after raw rematerialization.

## 12. 修正内容

Updated:

```text
src/ai_fund_lab_v2/data_store/schema.py
src/ai_fund_lab_v2/data_store/market_data_store.py
src/ai_fund_lab_v2/strategy/corporate_event.py
scripts/show_jquants_manifest.py
```

Key changes:

- `fins_summary` validation uses disclosure identity instead of `DiscDate + Code`.
- raw upsert business key uses `DiscNo` when available.
- missing `DiscNo` has a deterministic disclosure-attribute fallback.
- manifest diff now reports `exact_source_duplicate_count` and `business_key_collision_count`.
- Corporate Event source reference and revision id include `DiscNo`.
- manifest table output exposes the new duplicate diagnostics.

## 13. Re-materialization Contract

Because old parquet may have already collapsed source rows, affected `fins_summary` ranges must be re-fetched by the operator after backup.

Affected range at minimum:

```text
2026-07-06..2026-07-17
```

Also re-fetch any other `fins_summary` range fetched under the old key with `duplicate_key_count > 0`.

Existing manifest history must remain append-only. Do not delete manifest entries. Promote to operations path only after raw quality and latest manifest validation.

## 14. Operations Runbook更新

Updated:

```text
docs/03_operations/jquants_data_operations_runbook.md
```

Added:

- `trading_calendar` dry-run/live fetch commands,
- calendar coverage and manifest validation,
- `fins_summary` business key contract,
- duplicate warning interpretation,
- business-key repair rematerialization procedure.

## 15. Short Validation

```text
py_compile PASS
targeted ingestion/schema/manifest/Corporate Event tests: 40 passed
J-Quants targeted regression set: 82 passed
fetch_jquants_daily.py --help PASS
show_jquants_manifest.py --help PASS
```

No real J-Quants fetch was executed.

## 16. Evidence

Evidence directory:

```text
reports/phase23_w_fins_summary_business_key_authority_and_source_row_collapse_investigation/
```

Required files were generated:

```text
fins_summary_current_business_key.json
fins_summary_collapse_pipeline.json
fins_summary_duplicate_group_classification.json
fins_summary_disclosure_identity_contract.json
fins_summary_pit_revision_contract.json
fins_summary_consumer_impact_audit.json
fins_summary_business_key_decision.json
fins_summary_rematerialization_contract.json
trading_calendar_runbook_gap_repair.json
operations_runbook_update_audit.json
modified_files.json
short_validation_results.json
```

## 17. 10BD Gate

```text
NOT_READY_FOR_10BD_FINS_SUMMARY_BUSINESS_KEY_AUTHORITY_REVIEW_REQUIRED
```

Reason: actual 20 collapsed source rows remain unclassified until operator re-fetches the affected range under the repaired key/diagnostic contract.

## 18. Next Operator Action

1. Back up current `fins_summary` parquet.
2. Re-fetch `fins_summary` for `2026-07-06..2026-07-17` after confirming `trading_calendar` coverage.
3. Inspect latest manifest fields:

```text
duplicate_key_count
exact_source_duplicate_count
business_key_collision_count
```

4. Validate raw quality.
5. Promote to operations path only after Evidence Review.
