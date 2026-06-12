# Phase4-AA Real Runtime Coverage Gap / Fetch-Normalize Plan

## Purpose

Phase4-AA audits the coverage gap in isolated `real_runtime` normalized J-Quants daily quotes and defines the safe fetch-normalize plan needed before Candidate feature generation can use real runtime history.

This phase is planning and audit only. It does not call J-Quants APIs, execute fetches, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Read Inputs

- `docs/phase_reports/phase4z_real_runtime_normalized_isolated.md`
- `docs/phase_reports/phase4z_real_runtime_normalized_isolated_audit.md`
- `reports/candidate_ai/full_range/phase4z_real_runtime_normalized_isolated_summary.json`
- `reports/phase_reports/phase4z_real_runtime_normalized_isolated_audit.json`
- Phase1 runtime and data-store layout
- `.runtime/data/raw/jquants/`
- `.runtime/data/raw_normalized_real_runtime/`

## Current Coverage

The Phase4-Z isolated rebuild currently reports:

- `data_source_type = real_runtime`
- `api_call_performed = false`
- isolated path: `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet`
- `row_count = 4231`
- `code_count = 4231`
- `date_min = 2026-06-01`
- `date_max = 2026-06-01`
- `business_day_count = 1`
- `normalization_error_count = 218`
- `coverage_status = ISOLATED_REAL_RUNTIME_NORMALIZED_READY`

This means the isolated rebuild itself is valid, but it is not enough for 60-business-day Candidate feature lookback.

## Required Coverage

Minimum Candidate feature generation readiness requires:

- `business_day_count >= 60`
- `codes_with_60_business_day_lookback > 0`
- per-code lookback sufficient for the selected `as_of_date`
- date range covers at least the previous 60 business days from `as_of_date`
- schema validation OK
- leakage audit OK
- provenance manifest OK

Recommended Candidate AI training readiness requires broader history:

- 2021-06 onward where available
- or at least the full planned train/validation/test range from the Candidate training data design

## Coverage Gap

Current gap:

- `current_business_day_count = 1`
- `required_business_day_count = 60`
- `missing_business_day_count = 59`

Therefore Phase4-AA readiness is:

```text
READY_FOR_REAL_RUNTIME_HISTORY_FETCH_PLAN
```

This readiness means a safe fetch-normalize plan can be prepared. It does not mean Candidate feature full generation should start.

## Fetch Range Plan

Phase4-AA does not call J-Quants APIs. It defines the future fetch range policy only.

Initial feature-readiness fetch:

- `target_end_date = latest available date`
- `target_start_date = target_end_date - at least 90 calendar days`
- `minimum_required_business_days = 60`

Training-readiness fetch:

- `preferred_training_start_date = 2021-06-01`
- fetch through latest available date
- use trading calendar to verify actual business-day coverage

The generated Phase4-AA summary records the concrete planned `fetch_range_start` and `fetch_range_end` based on the current isolated `date_max`.

## Normalization Plan

Future raw daily quotes fetch output remains under:

```text
.runtime/data/raw/jquants/equities_bars_daily/
```

Future real runtime normalized output remains isolated under:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/
```

The default mock normalized path must remain unchanged:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/
```

## Manifest / Provenance Plan

Every future real runtime normalized rebuild must write a manifest with:

- `data_source_type = real_runtime`
- `source_provider = jquants`
- `api_call_performed = true/false`
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
- `promotion_status = not_promoted`

## API Safety Rule

Phase4-AA performs no API call.

When a later phase performs a fetch:

- API credentials must come from environment or `.env` and must not be committed.
- Secret values must not be logged, printed, or written to reports.
- Fetch must first produce a dry-run plan.
- Fetch output must write only to runtime raw paths.
- Normalize output must write only to isolated real runtime normalized paths.
- Mock normalized paths must not be overwritten.
- Post-fetch provenance and coverage audit must pass before any promotion discussion.

## Promotion Gate

Reader switch is forbidden until all gates pass:

- coverage audit OK
- `business_day_count >= 60`
- schema validation OK
- leakage audit OK
- provenance manifest OK
- normalized source path is isolated real runtime, not mock
- `promotion_status = approved`

Until that approval exists:

- `promotion_status = not_promoted`
- reader switch is forbidden
- Candidate feature full generation must continue to avoid real runtime promotion assumptions

## Rollback Plan

Before reader switch:

- delete or quarantine only isolated real runtime output
- keep `.runtime/data/raw_normalized/` mock history untouched
- no Candidate reader is affected

After any future promotion:

- use manifest provenance to identify the promoted source
- revert reader configuration to the previous approved source
- keep audit trail; do not silently delete history

## Output Reports

Summary:

- `reports/candidate_ai/full_range/phase4aa_real_runtime_coverage_gap_plan_summary.json`

Audit:

- `reports/phase_reports/phase4aa_real_runtime_coverage_gap_plan_audit.json`
- `docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan_audit.md`

## Explicit Non-goals

Phase4-AA does not implement:

- J-Quants API calls
- live fetch execution
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

## Phase4-AB Proposal

Phase4-AB should create a no-live fetch plan artifact for 60-business-day real runtime history expansion, including exact target dates from trading calendar, endpoint request plan, rate-limit plan, and post-fetch coverage audit expectations.
