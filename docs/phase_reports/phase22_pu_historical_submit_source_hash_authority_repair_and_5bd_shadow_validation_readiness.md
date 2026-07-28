# Phase22-PU — Historical Submit Source Hash Authority Repair and 5BD Shadow Validation Readiness

## Status

REVIEW_REQUIRED for final 5BD operator validation. Implementation and isolated tests are complete.

## Root Cause

The halted 5BD run `runtime-test-historical-smoke-20260728T000142649543Z` stopped at `2026-07-06:submit` with five blocked buy items. Submit read the run-scoped normalized OHLCV parquet, but the expected hash came from the old Phase17 PIT manifest:

- Expected: `c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d`
- Actual run-scoped normalized parquet: `dd0d6ee474a2eb09ce55beda8b7494cde09bab1e3d773de0d6760313e9dc7c07`

Classification: `MORNING_VS_SUBMIT_RESOLVER_MISMATCH` plus stale manifest authority.

## Repair

- Added `historical_source_identity_v1` with distinct `physical_file_hash`, `logical_dataset_hash/content_hash`, `schema_hash`, row/date/symbol stats, materialization identity, and manifest linkage.
- `market_refresh` historical logical input materialization now writes `source_identities` into `logical_input_manifest.json`.
- `HistoricalSubmitAdapter` now validates Submit against the run-scoped logical input manifest when `historical_asof_view_path` is present; it no longer uses the Phase17 PIT manifest as expected hash authority in that path.
- New mismatch reasons include content mismatch, raw-vs-normalized mismatch, cross-run source rejection, business-date mismatch, and missing bound manifest.
- `runtime_test.py run-status`, `fresh-run` summary, and `show --artifact run` now expose HALT summaries with date/job/reason/hash/path/action fields.

## Approval Isolation

Historical Submit remains bound to Pending approval via `.runtime/pending_order_plan/pending_order_plan.json`. The operations demo approval artifact under `.runtime/operations/approval_artifact/2026-07-06/approval_artifact.json` is not treated as Historical submit authority.

## Verification

- `python3 -m pytest tests/runtime_v2/test_phase22_pu_historical_submit_source_identity.py -q` → 8 passed
- `python3 -m pytest tests/strategy -q` → 130 passed
- Phase22 P/PR/PS/PT/PU subset in combined run passed; existing Phase19 system_status tests failed because current shared runtime status returned exit code 20 where tests expect 10.
- Targeted compile with `PYTHONPYCACHEPREFIX=/private/tmp/phase22_pu_pycache` passed.
- Full compile without `PYTHONPYCACHEPREFIX` was blocked by sandbox pycache writes to `/Users/negishi/Library/Caches`.

## Operator 5BD Validation

Codex did not run 5BD. Preserve the existing HALT evidence, then abandon it before starting a new fresh-run:

```bash
env PYTHONPATH=src python3 scripts/runtime_test.py abandon --run-id runtime-test-historical-smoke-20260728T000142649543Z --reason phase22_pu_repaired_source_identity_rerun --confirm --explicit-mutation-confirm --json
env PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --business-days 5 --start-date 2026-07-06 --initial-cash 1000000 --confirm --explicit-mutation-confirm --json
```

After the run:

```bash
env PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
env PYTHONPATH=src python3 scripts/runtime_test.py show --run-id <new-run-id> --artifact run --json
```
