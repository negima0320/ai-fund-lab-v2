# Phase17-BV1 Historical Listed Issues Capability Investigation

## Executive Summary

Phase17-BV1 investigated the Historical Listed Issues / Equities Master capability without J-Quants fetch, Runtime Test execution, code changes, Registry refresh, `.runtime` edits, broker writes, or external notifications.

Final judgment: `PHASE17_BV1_PARTIAL_HISTORICAL_MASTER_RECONSTRUCTION_REQUIRED`

Root cause for the 2026-06-29 10BD Historical Smoke halt is confirmed: Runtime v2 Historical As-of resolver reads `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`, whose earliest snapshot is 2026-07-06. Therefore `Date <= 2026-06-29` returns zero rows and `logical_view_empty` fail-closes market refresh.

## Current Pipeline

- Endpoint: `/v2/equities/master`
- Client method: `JQuantsClient.fetch_all_listed_issues(date=..., code=..., max_pages=...)`
- Ingestor: `JQuantsRawIngestor.fetch_and_store(endpoint_name="listed_issues", date=..., code=..., max_pages=...)`
- Implemented request parameters: `date, code, pagination_key, max_pages`
- Unsupported local range parameters: `from_date, to_date`
- Raw schema required fields: `Date, Code, CoName, Mkt`
- Raw schema key fields: `Date, Code`

## Current Coverage

Runtime v2 operational Listed Issues:

- Path: `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`
- Rows: `22193`
- Snapshot dates: `2026-07-06` to `2026-07-15`
- Snapshot count: `5`

Formal Phase9/config Listed Issues:

- Path: `.runtime/data/raw/jquants/listed_issues/data.parquet`
- Rows: `44439`
- Snapshot dates: `2026-06-01` to `2026-06-26`
- Snapshot count: `10`

Coverage gaps:

- 2021-01-01 to 2026-05-31: no local Listed Issues snapshots
- 2026-06-27 to 2026-07-05: no Runtime v2 operations snapshots; formal path has only up to 2026-06-26
- 2026-06-29 cannot be resolved with the current operations path
- 2021-01-04 cannot be resolved with any current local Listed Issues path

## J-Quants Capability

Local implementation declares `/v2/equities/master` support for:

- `date`
- `code`
- pagination

It does not support `from` / `to` range fetch for Listed Issues. Existing Phase9-I3 Evidence recorded `/v2/equities/master` with `date=2026-06-16` returning OK with 4,446 rows. BV1 did not perform a new API fetch, so 2021-to-present direct availability remains unproven.

Capability assessment:

- Recent single-date snapshot: `SUPPORTED_BY_EXISTING_EVIDENCE`
- 2021-to-present daily snapshots: `UNVERIFIED_WITHOUT_FETCH`
- Minimum viable strategy if API allows date: `per-business-date or sparse snapshot-date fetch using date=YYYY-MM-DD and all-pages pagination`

## Resolver Contract Audit

Current resolver logic:

`Read physical parquet, detect date column, logical = frame[Date <= business_date], fail closed if logical row count is 0.`

Current problem:

`For full-snapshot master data, selecting all Date <= business_date can include multiple full snapshots and duplicate Code rows. Consumers such as _symbol_in_pit_universe select max Date per symbol check, but materialized logical inputs may contain multiple snapshots.`

BV2 contract needed:

`Select latest official snapshot_date not after business_date for Listed Issues, evidence selected_snapshot_date/source_hash/schema_hash/age, and materialize one snapshot only.`

The current resolver prevents future leakage by excluding rows whose `Date` is after the business date. It also fail-closes when no prior rows exist. However, for full-snapshot master data, BV2 should select exactly the latest official snapshot not after the business date and materialize that snapshot, rather than carrying all historical snapshots forward into the logical view.

## BV2 Boundary

BV2 should not backfill by applying the 2026-07-06 snapshot to earlier dates. The safe boundary is:

1. Build an append-only J-Quants-derived snapshot store.
2. Preserve each raw snapshot and its request/response identity.
3. Resolve by `latest_snapshot_not_after_business_date`.
4. Evidence `selected_snapshot_date`, `snapshot_age_days`, `source_hash`, `schema_hash`, and `future_snapshot_used=false`.
5. Fail closed when no previous snapshot, empty snapshot, schema mismatch, or hash mismatch occurs.

## Required BV2 Acquisition Plan

Because BV1 did not fetch data, BV2 should first prepare an operator-run command plan for controlled J-Quants acquisition. Candidate strategy:

- Fetch `/v2/equities/master` with `date=YYYY-MM-DD` using trading calendar dates or month-start/update-date candidates.
- Start with a small probe set: 2021-01-04, 2021-06-15, 2026-06-29, 2026-07-06.
- If successful, expand to the chosen snapshot cadence.
- Store into a separate snapshot area, not by overwriting current `data.parquet`.

## Evidence Files

- `reports/phase17_bv1_historical_listed_issues_capability_investigation/summary.json`
- `reports/phase17_bv1_historical_listed_issues_capability_investigation/current_pipeline_inventory.json`
- `reports/phase17_bv1_historical_listed_issues_capability_investigation/jquants_capability_matrix.json`
- `reports/phase17_bv1_historical_listed_issues_capability_investigation/historical_coverage_gap.json`
- `reports/phase17_bv1_historical_listed_issues_capability_investigation/resolver_contract_audit.json`
- `reports/phase_reports/phase17_bv1_historical_listed_issues_capability_investigation.json`

## Prohibited Operations Confirmation

- J-Quants fetch: not performed
- Runtime Test run/resume/reset/rollback/close: not performed
- Frozen Run editing: not performed
- `.runtime` manual edit: not performed
- Ledger edit: not performed
- Registry refresh: not performed
- broker write / order submit: not performed
- external notification: not performed
- code modification: not performed

## Final Judgment

`PHASE17_BV1_PARTIAL_HISTORICAL_MASTER_RECONSTRUCTION_REQUIRED`
