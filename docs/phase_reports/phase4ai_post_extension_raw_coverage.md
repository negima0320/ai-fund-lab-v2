# Phase4-AI Post-extension Raw Coverage Audit

## Purpose

Phase4-AI audits the integrated raw J-Quants daily quotes after Phase4-AD and Phase4-AH.

The goal is to confirm whether the raw data now has at least 60 non-empty trading dates and can proceed to real runtime normalized rebuild.

This phase is audit only. It does not call APIs, fetch data, rebuild normalized data, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Inputs

- `docs/phase_reports/phase4ae_post_fetch_raw_coverage.md`
- `docs/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan.md`
- `docs/phase_reports/phase4ah_controlled_extension_fetch.md`
- `reports/candidate_ai/full_range/phase4ae_post_fetch_raw_coverage_summary.json`
- `reports/candidate_ai/full_range/phase4af_trading_calendar_correction_fetch_extension_plan_summary.json`
- `reports/candidate_ai/full_range/phase4ah_controlled_extension_fetch_summary.json`
- `.runtime/data/raw/jquants/equities_bars_daily/`

## Audit Rules

Coverage:

```text
required_non_empty_trading_day_count = 60
```

Only response dates with non-empty `payload.data` rows count toward coverage.

Schema consistency:

- response payload must contain `data` as a list
- each non-empty row must be a mapping
- each row must include `Date` and `Code`

Manifest consistency:

- raw run manifest exists
- request manifests exist
- response files exist
- request manifest dates match response dates
- all request manifests are `SUCCESS`
- run manifest `completed_request_count` matches current request manifest count

The run manifest may keep historical attempt counts. A warning is recorded if `planned_request_count` differs from current artifact count, but that alone does not block if the current artifact set is internally consistent.

## Output

Summary:

- `reports/candidate_ai/full_range/phase4ai_post_extension_raw_coverage_summary.json`

Audit:

- `reports/phase_reports/phase4ai_post_extension_raw_coverage_audit.json`
- `docs/phase_reports/phase4ai_post_extension_raw_coverage_audit.md`

## Readiness

If coverage, schema, manifest consistency, and secret checks pass:

```text
READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD
```

Blocking statuses:

- `BLOCKED_BY_COVERAGE_GAP`
- `BLOCKED_BY_RAW_INTEGRITY`
- `BLOCKED_BY_SECRET_LEAK`

## Next Phase

Phase4-AJ should rebuild real runtime normalized data from the integrated raw daily quotes.

Phase4-AJ must not modify the mock normalized path, promote data, or switch readers.
