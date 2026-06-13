# Phase4-AB No-live Real Runtime History Fetch Plan

## Purpose

Phase4-AB fixes the no-live fetch plan needed to expand isolated `real_runtime` J-Quants daily quotes history to at least 60 business days.

This phase is plan and audit only. It does not call J-Quants APIs, execute fetches, retrieve live data, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Read Inputs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/candidate_ai_design.md`
- `docs/03_ai_design/candidate_feature_catalog.md`
- `docs/03_ai_design/candidate_training_data_design.md`
- `docs/03_ai_design/candidate_feature_builder_design.md`
- `docs/phase_reports/phase4_handoff_summary.md`
- `docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan.md`
- `docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan_audit.md`
- `reports/candidate_ai/full_range/phase4aa_real_runtime_coverage_gap_plan_summary.json`
- `reports/phase_reports/phase4aa_real_runtime_coverage_gap_plan_audit.json`
- `.runtime/data/raw/jquants/trading_calendar/`
- `.runtime/data/raw_normalized_real_runtime/`
- `.runtime/data/raw_normalized/`

## Current Coverage

Phase4-AA reported:

- `current_business_day_count = 1`
- `required_business_day_count = 60`
- `missing_business_day_count = 59`
- `row_count = 4231`
- `code_count = 4231`
- `date_min = 2026-06-01`
- `date_max = 2026-06-01`
- `normalization_error_count = 218`
- `api_call_performed = false`
- `promotion_status = not_promoted`
- mock path unchanged

## Required Coverage

Minimum feature-readiness coverage:

- at least 60 target business days
- at least one code with full 60-business-day lookback
- post-fetch raw coverage audit OK
- post-normalize coverage audit OK
- schema validation OK
- leakage audit OK
- provenance manifest OK

Training readiness remains broader:

- prefer 2021-06-01 onward
- do not treat the 60-business-day plan as training-ready

## Target Date Range

The no-live plan uses existing trading calendar raw data and the Phase4-AA target end date.

Current planned target:

```text
target_end_date = 2026-06-01
target_start_date = 2026-03-10
required_business_day_count = 60
```

The target business day list is written to:

```text
reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json
```

The current isolated real_runtime already contains `2026-06-01`, so the missing fetch list contains 59 business days.

## Business Day Plan

The plan reads:

```text
.runtime/data/raw/jquants/trading_calendar/data.parquet
.runtime/data/raw/jquants/trading_calendar/data.jsonl
```

Business days are identified using the existing Phase1 convention:

```text
HolDiv == "1"
```

If trading calendar raw data is missing or insufficient, readiness becomes:

```text
BLOCKED_BY_TRADING_CALENDAR
```

Because Phase4-AB is no-live only, any final live-fetch phase must re-audit the trading calendar before execution.

## J-Quants Endpoint Request Plan

Endpoint:

```text
/v2/equities/bars/daily
```

Request template:

```json
{
  "date": "<YYYY-MM-DD from missing_business_day_list>",
  "code": null,
  "pagination_key": "<optional next pagination key>"
}
```

Initial request estimate:

```text
planned_request_count = len(missing_business_day_list)
```

For the current state:

```text
planned_request_count = 59
```

This is a minimum first-page estimate. Pagination can increase actual request count.

## Pagination Policy

For each target date:

- request first page
- if response contains a next pagination key, continue
- record each pagination page in raw manifest
- stop when no next pagination key exists

## Max Pages Policy

Every future fetch must set a `max_pages` guard.

Recommended default for Phase4-AC dry-run:

```text
max_pages = 1
```

Controlled live fetch phases must use an explicit cap and fail safely if the cap is exceeded.

## Rate Limit Policy

J-Quants Light plan:

```text
60 req/min
```

Policy:

- no burst
- at most 1 request per second
- bounded retry delay for transient errors
- retry metadata must not contain credential values

## Retry / Backoff Policy

Retry only:

- timeout
- temporary network failure
- HTTP 5xx
- HTTP 429

Do not blindly retry:

- 401
- 403
- malformed request

All retry logs and reports must be sanitized.

## Storage Plan

Raw fetch output:

```text
.runtime/data/raw/jquants/equities_bars_daily/
```

Isolated real_runtime normalized output:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/
```

Mock normalized path that must remain unchanged:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/
```

## Manifest / Provenance Plan

Required fields:

- `data_source_type`
- `source_provider`
- `api_call_performed`
- `source_raw_path`
- `source_raw_manifest_path`
- `fetch_range_start`
- `fetch_range_end`
- `normalizer_version`
- `schema_version`
- `row_count`
- `code_count`
- `date_min`
- `date_max`
- `input_hash_optional`
- `output_hash_optional`
- `promotion_status`

Future fetch phases must keep:

```text
promotion_status = not_promoted
```

until promotion is explicitly approved.

## API Credential Safety Rule

Phase4-AB does not read, validate, print, or log API credentials.

Future fetch phases must:

- read credentials from environment or `.env`
- never commit credentials
- never print credential values
- never write credential values to stdout, stderr, logs, reports, manifests, or snapshots
- sanitize errors before reporting

## Post-fetch Raw Audit Condition

Before normalization:

- every planned missing business day must have raw records, or a documented market/calendar reason
- raw manifest must record endpoint, request date, storage path, record count, validation status, and sanitized request params
- duplicate fetches must not create duplicate logical records
- mock normalized path must remain untouched

## Post-normalize Coverage Audit Condition

Before any feature generation:

- `business_day_count >= 60`
- per-code lookback sufficiency is measured
- schema validation OK
- leakage audit OK
- provenance manifest OK
- output path is isolated real_runtime, not default mock normalized

## Promotion Gate

Promotion is forbidden until:

- raw audit OK
- normalize audit OK
- coverage audit OK
- schema validation OK
- leakage audit OK
- provenance manifest OK
- `business_day_count >= 60`
- human approval exists
- `promotion_status = approved`

## Reader Switch Gate

Reader switch is forbidden until:

- promotion gate passes
- source is explicitly selected as real_runtime
- rollback path is documented
- Safety / Operation review accepts the source

## Rollback Plan

Before reader switch:

- delete or quarantine only isolated real_runtime outputs
- keep mock normalized path unchanged
- no Candidate reader is affected

After any future promotion:

- revert reader config to the previous approved source
- keep all manifests and audit files
- do not silently delete evidence

## Readiness Status

If Phase4-AA summary exists, isolated real_runtime is detected, trading calendar can produce at least 60 business days, and all safety rules are defined:

```text
READY_FOR_NO_LIVE_FETCH_DRY_RUN_CLI
```

## Output Reports

Summary:

- `reports/candidate_ai/full_range/phase4ab_no_live_real_runtime_fetch_plan_summary.json`

Audit:

- `reports/phase_reports/phase4ab_no_live_real_runtime_fetch_plan_audit.json`
- `docs/phase_reports/phase4ab_no_live_real_runtime_fetch_plan_audit.md`

## Explicit Non-goals

Phase4-AB does not implement:

- J-Quants API call
- live fetch
- real data retrieval
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
- Order Manager
- Broker API
- order placement
- trading
- Portfolio auto-update

## Phase4-AC Proposal

Phase4-AC should implement a mock/no-live dry-run CLI that reads this fetch plan and prints the planned endpoint/date/request sequence without calling J-Quants.
