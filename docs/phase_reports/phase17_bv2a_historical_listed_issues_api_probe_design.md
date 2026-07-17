# Phase17-BV2A Historical Listed Issues API Probe and Acquisition Design

## Executive Summary

Final judgment: `PHASE17_BV2A_PROBE_COMMAND_READY`

This phase did not execute a J-Quants API fetch. It prepared and dry-run verified an operator command that probes `/v2/equities/master` historical date support through the existing formal `JQuantsClient` and `JQuantsRawIngestor`.

The probe command writes only to the probe runtime root:

```text
.runtime/operations/jquants/probes/historical_listed_issues/
```

It does not overwrite the current Runtime v2 Listed Issues parquet or the Phase9/formal config parquet.

## Existing Fetcher Assessment

`scripts/fetch_jquants_daily.py` already uses:

- `ai_fund_lab_v2.data_sources.jquants.JQuantsClient`
- `ai_fund_lab_v2.data_sources.jquants.JQuantsRawIngestor`
- `MarketDataStore`

The J-Quants fetch policy identifies `/v2/equities/master` as supporting:

- `date`
- `code`
- pagination

Required environment:

- `JQUANTS_API_KEY`

Optional environment:

- `JQUANTS_BASE_URL`
- `JQUANTS_RATE_LIMIT_PER_MINUTE`
- `JQUANTS_TIMEOUT_SECONDS`

## Probe Command

Dry-run, no fetch:

```bash
PYTHONPATH=src python3 scripts/probe_historical_listed_issues.py --dry-run
```

Operator fetch command, to be run by the user after approval:

```bash
PYTHONPATH=src python3 scripts/probe_historical_listed_issues.py --probe-root .runtime/operations/jquants/probes/historical_listed_issues --storage-format parquet --max-pages 100 --dates 2021-01-04 2021-06-15 2026-06-29 2026-07-06
```

Optional non-business-day probe:

```bash
PYTHONPATH=src python3 scripts/probe_historical_listed_issues.py --probe-root .runtime/operations/jquants/probes/historical_listed_issues --storage-format parquet --max-pages 100 --dates 2021-01-04 2021-06-15 2026-06-29 2026-07-06 --include-non-business-probe
```

Each date is isolated under its own runtime root and records row count, source hash, schema hash, request date, response `Date` min/max/unique, pagination pages, validation status, and secret-safe diagnostics.

## Date Semantics

The probe records these fields separately:

- `request_date`: API request parameter date
- `response Date`: J-Quants Equities Master snapshot effective date
- `target_date`: Runtime raw-store target date for the probe
- `fetched_at`: UTC local save time
- `snapshot_date`: response `Date` when present
- `provider_effective_date`: response `Date` when present

The response `Date` must be treated as the Equities Master snapshot date, not as a listing date.

## Current Store Comparison

Read-only comparison confirmed:

- Runtime v2 operational store starts at `2026-07-06`.
- Phase9/formal config store contains snapshots through `2026-06-26`.
- For `2026-06-29`, the short-term candidate is `selected_snapshot_date=2026-06-26`, `selection_policy=latest_snapshot_not_after_business_date`, `snapshot_age_days=3`, `future_snapshot_used=false`.

This is not approved as a fallback path in this phase. It must be formalized through a common Listed Issues snapshot authority.

## Acquisition Strategy

The probe result will select one of:

- A: 2021 onward daily snapshots are available.
- B: historical dates are available, but sparse snapshots are sufficient under `latest_snapshot_not_after_business_date`.
- C: API retention blocks 2021, so only prior J-Quants-derived local archives may be used.

Future snapshots must never be reverse-applied to earlier business dates.

## Authority Unification Plan

Runtime v2 and Phase9 Listed Issues data must be unified into one J-Quants snapshot authority. The resolver should select:

```text
latest_snapshot_not_after_business_date
```

Evidence must include:

- selected snapshot date
- snapshot age
- source hash
- schema hash
- future snapshot used flag

## Verification

Commands executed:

- `PYTHONPATH=src python3 scripts/probe_historical_listed_issues.py --dry-run`
- `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile scripts/probe_historical_listed_issues.py`
- read-only parquet comparison for current stores

No J-Quants fetch, Runtime Test, broker write, order submit, external notification, Registry refresh, Frozen Run edit, or current Listed Issues overwrite was executed.

## Evidence

- `reports/phase17_bv2a_historical_listed_issues_api_probe_design/summary.json`
- `reports/phase17_bv2a_historical_listed_issues_api_probe_design/probe_command_plan.json`
- `reports/phase17_bv2a_historical_listed_issues_api_probe_design/current_store_comparison.json`
- `reports/phase17_bv2a_historical_listed_issues_api_probe_design/acquisition_strategy_matrix.json`
- `reports/phase17_bv2a_historical_listed_issues_api_probe_design/runtime_authority_unification_plan.json`
- `reports/phase_reports/phase17_bv2a_historical_listed_issues_api_probe_design.json`
