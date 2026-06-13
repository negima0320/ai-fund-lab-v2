# Phase4-AF Trading Calendar Correction / Fetch Range Extension Plan

## Purpose

Phase4-AF re-audits the Phase4-AE raw coverage gap by separating expected market-closed empty responses from true missing non-empty trading days.

This phase creates a fetch range extension plan only. It does not call J-Quants APIs, fetch or refetch data, read credentials, initialize an HTTP client, rebuild normalized data, write to normalized paths, promote data, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.

## Inputs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/candidate_ai_design.md`
- `docs/03_ai_design/candidate_training_data_design.md`
- `docs/03_ai_design/candidate_feature_builder_design.md`
- `docs/phase_reports/phase4ae_post_fetch_raw_coverage.md`
- `docs/phase_reports/phase4ae_post_fetch_raw_coverage_audit.md`
- `reports/candidate_ai/full_range/phase4ae_post_fetch_raw_coverage_summary.json`
- `reports/phase_reports/phase4ae_post_fetch_raw_coverage_audit.json`
- `.runtime/data/raw/jquants/equities_bars_daily/`
- `.runtime/data/raw/jquants/trading_calendar/`

## Calendar Correction Rule

Phase4-AE counted every missing required business date as a coverage gap. Phase4-AF corrects that by classifying each empty response date:

- market closed day: expected empty, not a coverage gap
- market open day: unexpected empty, blocking condition

The correction uses:

- trading calendar raw records when available
- weekend detection
- known Japan market holiday overrides for 2026

This matters because the current trading calendar raw has `HolDiv=1` for some dates that produced empty daily quote responses. For Phase4-AF, non-empty daily quote coverage is the source of truth for feature lookback readiness, while empty responses on known market-closed days are accepted as expected empty.

## Coverage Rule

The Candidate feature lookback requirement remains:

```text
required_non_empty_trading_day_count = 60
```

Only non-empty daily quote dates that are market-open dates count toward this requirement.

If the count is below 60 and there are no unexpected empty trading dates, Phase4-AF creates a past-direction extension plan.

## Extension Plan Rule

The extension plan:

- extends backward from the current earliest non-empty raw date
- uses market-open days only
- avoids existing non-empty dates
- writes no raw data
- preserves existing successful manifests and response files

Expected next phase when extension is required:

```text
Phase4-AG Real Runtime Extension Fetch Dry-run
```

## 2026-06-01 Classification

`2026-06-01` appeared in the Phase4-AE required date list but was not part of the Phase4-AD raw request set. It came from the isolated current normalized date used before the AD extension fetch.

Phase4-AF treats it as:

```text
missing_requested_trading_date
```

It should not be used as latest raw coverage until raw daily quotes for `2026-06-01` are explicitly fetched and audited.

## Merge Policy

Future extension fetches must:

- write only new request manifests and response files for extension dates
- preserve existing successful request manifests
- preserve existing response files
- keep existing raw data intact
- avoid promotion and reader switch
- rerun post-fetch raw audit after extension

## Output

Summary:

- `reports/candidate_ai/full_range/phase4af_trading_calendar_correction_fetch_extension_plan_summary.json`

Audit:

- `reports/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan_audit.json`
- `docs/phase_reports/phase4af_trading_calendar_correction_fetch_extension_plan_audit.md`

## Readiness

Readiness candidates:

- `READY_FOR_EXTENSION_FETCH_DRY_RUN`
- `READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD`
- `BLOCKED_BY_MISSING_PHASE4AE_SUMMARY`
- `BLOCKED_BY_PHASE4AE_NOT_COVERAGE_GAP`
- `BLOCKED_BY_TRADING_CALENDAR_CLASSIFICATION`
- `BLOCKED_BY_UNEXPECTED_EMPTY_TRADING_DATES`
- `BLOCKED_BY_EXTENSION_PLAN`
- `BLOCKED_BY_OUTPUT_PATH_SAFETY`
- `BLOCKED_BY_SECRET_SAFETY`

## Phase4-AG Proposal

If `extension_fetch_required=true`, Phase4-AG should create a no-live dry-run for the extension request list. It must not call the API yet.
