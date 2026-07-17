# Phase17-BV8 Historical Submit PIT Universe Authority Integration Fix

## Executive Summary

Final judgment: `PHASE17_BV8_HISTORICAL_SUBMIT_PIT_AUTHORITY_ACCEPTED_RESUME_SAFE`

The 2026-06-29 submit halt was caused by the Historical submit adapter validating the PIT universe against the legacy operational Listed Issues parquet:

`.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`

That file only contained `Date >= 2026-07-06`, so `Date <= 2026-06-29` produced an empty PIT universe. Morning/Pending had already used the BV5 accepted Historical Listed Issues snapshot authority through the run-scoped historical as-of view:

`.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-06-29/data.parquet`

The Submit Guard now resolves Listed Issues from the same Historical as-of authority and records snapshot date/path/hash/row count/lineage evidence. Pending embedded `listed_info.current_listed=true` is still not trusted by itself.

## Root Cause

`HistoricalSubmitAdapter._resolve_open_price()` called `_symbol_in_pit_universe(Path(self.listed_issues_path), symbol, target_session_date)`.

The default `listed_issues_path` was the old operational raw path. It was not wired to:

- BV5 production Historical Listed Issues snapshot store
- `latest_snapshot_not_after_business_date`
- run-scoped `historical_asof_view.json`
- selected snapshot hash/lineage verification

For 2026-06-29, the old raw path had no rows not after the business date. The accepted BV5 snapshot had all 5 Pending symbols.

## Authority Comparison

Morning/as-of authority:

- selected snapshot date: `2026-06-29`
- path: `.runtime/operations/jquants/historical_snapshots/listed_issues/snapshots/2026-06-29/data.parquet`
- row count: `4436`
- content hash: `53bf031316c1d959686b4f9bb8f41710d69eb5e4d9210da2ff4ad208d12ec25d`
- future snapshot used: `false`

Old submit authority:

- path: `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`
- Date range: `2026-07-06` to `2026-07-15`
- PIT row count for 2026-06-29: `0`

## Fix

Implemented in `HistoricalSubmitAdapter`:

- Prefer run-scoped `historical_asof_view.json` Listed Issues authority.
- Fallback to BV5 snapshot resolver under `runtime_root/operations/jquants/historical_snapshots/listed_issues`.
- Keep legacy explicit path only for isolated fixtures with no accepted snapshot/as-of authority.
- Verify content hash from as-of authority.
- Reject future snapshot dates.
- Normalize numeric and alpha 5-character issue codes.
- Fail closed on Pending listed_info code mismatch.
- Include `pit_universe_authority` in adapter preflight evidence.
- Scope corporate action guard to the target symbol, while still halting when the target symbol itself has non-1.0 AdjFactor.

## Pending Symbol Resolution

Read-only adapter preflight against the target run evidence resolved all 5 symbols:

- `33500`: `DRY_RUN_READY`, snapshot `2026-06-29`, lineage match `true`
- `36810`: `DRY_RUN_READY`, snapshot `2026-06-29`, lineage match `true`
- `186A0`: `DRY_RUN_READY`, snapshot `2026-06-29`, lineage match `true`
- `70630`: `DRY_RUN_READY`, snapshot `2026-06-29`, lineage match `true`
- `31340`: `DRY_RUN_READY`, snapshot `2026-06-29`, lineage match `true`

## Resume Safety

Resume classification: `RESUME_SAFE`

Evidence:

- submit stopped before broker boundary acceptance
- submitted count: `0`
- blocked count: `5`
- broker write: `false`
- `.runtime/persistent_ledger/orders.jsonl`: `0` records
- `.runtime/persistent_ledger/executions.jsonl`: `0` records
- `.runtime/persistent_ledger/events.jsonl`: `0` records
- historical submission evidence directory absent
- Pending lineage matches corrected authority in read-only preflight

Codex did not execute Runtime Test resume.

## Verification

Passed:

- BV8 targeted tests: `8 passed`
- Related Runtime v2 tests: `34 passed`
- `py_compile`: PASS
- `git diff --check`: PASS

Full `tests/runtime_v2` result:

- `913 passed`
- `5 failed`

The 5 failures are demo sell_planning / PM fixture tests failing with `pm_input_stale_artifacts`. They are outside the Historical Submit PIT authority call graph and unrelated to `HistoricalSubmitAdapter`. They are recorded as residual non-BV8 regression failures.

## Prohibited Operations Confirmation

Not executed:

- Runtime Test run/resume/reset/rollback/close
- Frozen Run edit
- `.runtime` manual edit
- Pending manual edit
- Ledger manual edit
- Registry refresh
- J-Quants fetch
- broker write
- real order submit
- external notification
- xfail/skip

