# Phase17-BV2B Historical Listed Issues Probe Runtime Fix

## Executive Summary

Final judgment: `PHASE17_BV2B_PROBE_RUNTIME_FIX_ACCEPTED`

The BV2A probe CLI stopped after a successful `2026-06-29` J-Quants fetch/save because the probe code referenced a non-existent `FetchResult.storage_format` field.

Codex did not execute a real J-Quants API fetch in this phase.

## Root Cause

`JQuantsRawIngestor.fetch_and_store()` returns:

- `endpoint_name`
- `endpoint`
- `records_saved`
- `output_path`
- `validation_status`
- `diff_summary`

It does not return `storage_format`.

The probe CLI incorrectly called:

```python
create_storage_backend(fetch_result.storage_format).read_records(data_path)
```

The fetch and save had already completed. Evidence in the partial probe root shows:

- `2026-06-29/data/raw/jquants/manifest.jsonl`
- `2026-06-29/data/raw/jquants/listed_issues/data.parquet`
- manifest `status=OK`
- manifest `record_count=4436`
- manifest `storage_format=parquet`

## Fix

The probe now resolves storage format authority from the persisted manifest and validates it against the requested CLI storage format and output path.

Authority order:

1. latest manifest `storage_format`
2. requested `args.storage_format`
3. output suffix as consistency check only

Fail-closed conditions:

- manifest format differs from requested format
- manifest storage path differs from `FetchResult.output_path`
- output suffix differs from requested format when manifest is absent
- backend read/schema processing raises after save

No ad hoc `FetchResult.storage_format` field was added.

## Partial Probe Root

The existing root was not deleted:

```text
.runtime/operations/jquants/probes/historical_listed_issues/
```

It contains partial user-run artifacts for:

- `2021-01-04`
- `2021-06-15`
- `2026-06-29`

The recommended retry root is:

```text
.runtime/operations/jquants/probes/historical_listed_issues_bv2b/
```

## Retry Command

```bash
PYTHONPATH=src python3 scripts/probe_historical_listed_issues.py --probe-root .runtime/operations/jquants/probes/historical_listed_issues_bv2b --storage-format parquet --max-pages 100 --dates 2021-01-04 2021-06-15 2026-06-29 2026-07-06
```

## Verification

Executed without real API fetch:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_phase17_bv2b_historical_listed_issues_probe_runtime_fix.py
```

Result:

```text
7 passed
```

Also passed:

- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile scripts/probe_historical_listed_issues.py`
- `git diff --check -- scripts/probe_historical_listed_issues.py tests/test_phase17_bv2b_historical_listed_issues_probe_runtime_fix.py`
- dry-run for the new retry root

## Safety Confirmation

Not executed:

- real J-Quants API fetch
- Runtime Test run/resume/reset/rollback/close
- operational Listed Issues overwrite
- Phase9/formal config Listed Issues overwrite
- Ledger edit
- Registry refresh
- broker write
- order submit
- external notification

## Evidence

- `reports/phase17_bv2b_historical_listed_issues_probe_runtime_fix/summary.json`
- `reports/phase17_bv2b_historical_listed_issues_probe_runtime_fix/root_cause.json`
- `reports/phase17_bv2b_historical_listed_issues_probe_runtime_fix/fetch_result_contract.json`
- `reports/phase17_bv2b_historical_listed_issues_probe_runtime_fix/storage_authority_verification.json`
- `reports/phase17_bv2b_historical_listed_issues_probe_runtime_fix/partial_probe_artifact_inventory.json`
- `reports/phase17_bv2b_historical_listed_issues_probe_runtime_fix/test_verification.json`
- `reports/phase_reports/phase17_bv2b_historical_listed_issues_probe_runtime_fix.json`
