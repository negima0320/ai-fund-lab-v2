# Phase4-AG Real Runtime Extension Fetch Dry-run

## Purpose

Phase4-AG converts the Phase4-AF extension plan into a no-live request artifact for the six additional daily quote dates.

This phase does not call J-Quants APIs, fetch or refetch data, read credentials, create tokens, initialize an HTTP client, write raw responses, update raw manifests, rebuild normalized data, write to normalized paths, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Input

- `reports/candidate_ai/full_range/phase4af_trading_calendar_correction_fetch_extension_plan_summary.json`
- `docs/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan.md`
- `.runtime/data/raw/jquants/equities_bars_daily/`

## Extension Request Dates

Phase4-AF determined that current non-empty raw trading-day coverage is 54 days. Six additional non-empty trading days are needed to reach 60.

The extension request sequence is:

```text
2026-03-02
2026-03-03
2026-03-04
2026-03-05
2026-03-06
2026-03-09
```

## Request Shape

Each dry-run request has:

```text
endpoint = /v2/equities/bars/daily
method = GET
params.date = YYYY-MM-DD
params.code = None
params.pagination_key = None
```

Pagination is not known during dry-run. Controlled fetch must discover additional pages from live responses with a bounded `max_pages` guard.

## Merge Policy

Future controlled extension fetch must:

- preserve existing raw response files
- preserve existing request manifests
- preserve existing successful request manifests
- fetch only extension dates
- skip same-date existing SUCCESS manifests
- mark same-date existing FAILED manifests as rerun candidates
- defer raw manifest update to Phase4-AH
- defer normalized rebuild to a later post-extension audit phase

## Output

Summary:

- `reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_summary.json`

Requests:

- `reports/candidate_ai/full_range/phase4ag_real_runtime_extension_fetch_dry_run_requests.json`

Audit:

- `reports/phase_reports/phase4ag_real_runtime_extension_fetch_dry_run_audit.json`
- `docs/phase_reports/phase4ag_real_runtime_extension_fetch_dry_run_audit.md`

## Readiness

If the dry-run request artifact is generated from a valid Phase4-AF summary, no API/fetch/credential/raw write occurs, and the generated count matches the extension count:

```text
READY_FOR_CONTROLLED_EXTENSION_FETCH
```

Blocking statuses:

- `BLOCKED_BY_MISSING_PHASE4AF_SUMMARY`
- `BLOCKED_BY_PHASE4AF_NOT_READY`
- `BLOCKED_BY_EXTENSION_NOT_REQUIRED`
- `BLOCKED_BY_EXTENSION_REQUEST_SEQUENCE_MISMATCH`
- `BLOCKED_BY_OUTPUT_PATH_SAFETY`
- `BLOCKED_BY_API_SAFETY_RULE`
- `BLOCKED_BY_DRY_RUN_ARTIFACT`

## Phase4-AH Proposal

Phase4-AH should execute controlled extension fetch for only the six extension dates. It must preserve existing raw artifacts and must not rebuild normalized data yet.
