# Phase4-AE Post-fetch Raw Coverage Audit

## Purpose

Phase4-AE audits the raw J-Quants daily quotes fetched in Phase4-AD.

This phase checks raw coverage, row count, code count, empty responses, manifest consistency, duplicate date/code rows, and secret non-disclosure.

It does not call J-Quants APIs, fetch or refetch data, rebuild normalized data, write to normalized paths, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Read Inputs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/candidate_ai_design.md`
- `docs/03_ai_design/candidate_training_data_design.md`
- `docs/03_ai_design/candidate_feature_builder_design.md`
- `docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan.md`
- `docs/phase_reports/phase4ac_real_runtime_history_fetch_dry_run.md`
- `docs/phase_reports/phase4ad_controlled_real_runtime_history_fetch.md`
- `reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json`
- `reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_summary.json`
- `reports/candidate_ai/full_range/phase4ac_real_runtime_history_fetch_dry_run_requests.json`
- `reports/candidate_ai/full_range/phase4ad_controlled_real_runtime_history_fetch_summary.json`
- `reports/phase_reports/phase4ad_controlled_real_runtime_history_fetch_audit.json`
- `.runtime/data/raw/jquants/equities_bars_daily/manifest.json`
- `.runtime/data/raw/jquants/equities_bars_daily/request_manifests/`
- `.runtime/data/raw/jquants/equities_bars_daily/responses/`

## Audit Target

Runtime raw root:

```text
.runtime/data/raw/jquants/equities_bars_daily/
```

Phase4-AD wrote:

- run manifest
- per-request manifests
- response JSON files

Phase4-AE reads these files only. It writes summary and audit reports under `reports/` and `docs/phase_reports/`.

## Current Result

At the time of this report, Phase4-AD produced:

- planned requests: 59
- completed requests: 59
- request manifests: 59
- response files: 59
- fetched row count: 240202
- fetched code count: 4503
- fetched data dates: 54
- fetched date range: 2026-03-10 to 2026-05-29
- empty response dates: 5

Because Candidate feature generation requires at least 60 business/data dates, Phase4-AE blocks normalization readiness with:

```text
BLOCKED_BY_COVERAGE_GAP
```

## Coverage Rule

Required:

```text
required_business_day_count = 60
```

The important distinction:

- request success count is not enough
- response files are not enough
- raw data coverage must be based on dates with non-empty `data` rows

If `fetched_business_day_count < 60`:

```text
coverage_sufficient_for_features = false
readiness_status = BLOCKED_BY_COVERAGE_GAP
```

## Empty Response Rule

Responses with:

```json
{"data": []}
```

are recorded as `empty_response_dates`.

They are not counted as fetched data dates for Candidate feature lookback.

## Missing Requested Dates

`missing_requested_dates` contains requested dates that did not produce non-empty raw data.

This includes empty response dates and any requested date without a response file.

## Schema Rule

Raw response schema is considered OK when:

- response payload has `data` as a list
- each non-empty row is a mapping
- each row has at least `Date` and `Code`

Full OHLCV validation is deferred to the existing raw/normalize validation phases.

## Manifest Consistency Rule

Manifest consistency is OK when:

- run manifest exists
- request manifest count equals planned request count
- response file count equals planned request count
- completed request count equals planned request count

## Secret Safety Rule

Phase4-AE checks reports and manifests for disallowed secret-related markers:

- `Authorization`
- `x-api-key`
- `password`
- `cookie`
- `id_token`
- `refresh_token`

Credential values are not printed or written by Phase4-AE.

## Explicit Non-goals

Phase4-AE does not implement:

- J-Quants API call
- additional fetch
- refetch
- normalized data rebuild
- `.runtime/data/raw_normalized_real_runtime/` writes
- `.runtime/data/raw_normalized/` writes
- promotion
- reader switch
- Candidate feature full generation
- label generation
- dataset builder
- Candidate AI model
- training
- inference
- backtest
- Historical Evaluation
- Opportunity AI
- Position Management AI
- Capital Allocation
- Paper Trading
- Broker API
- order placement
- trading
- Portfolio auto-update

## Output Reports

Summary:

- `reports/candidate_ai/full_range/phase4ae_post_fetch_raw_coverage_summary.json`

Audit:

- `reports/phase_reports/phase4ae_post_fetch_raw_coverage_audit.json`
- `docs/phase_reports/phase4ae_post_fetch_raw_coverage_audit.md`

## Phase4-AF Proposal

If coverage remains insufficient:

```text
Phase4-AF Real Runtime Fetch Range Extension Plan
```

If coverage is sufficient:

```text
Phase4-AF Real Runtime Normalized Rebuild from Raw
```

The current expected next step is the range extension plan, because fetched data dates are below 60.
