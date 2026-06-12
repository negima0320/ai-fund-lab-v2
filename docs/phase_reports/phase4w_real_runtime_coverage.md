# Phase4-W Real Runtime Coverage / Chunk Scale Readiness

## Purpose

Phase4-W checks whether the full controlled feature generation readiness proven with mock normalized history can be applied to existing real J-Quants-derived `daily_quotes_normalized` data under `.runtime`.

This phase reads existing normalized runtime data only. It does not call the J-Quants API.

## Read Inputs

- `docs/phase_reports/phase4v_post_expansion_readiness.md`
- `docs/phase_reports/phase4v_post_expansion_readiness_audit.md`
- `reports/phase_reports/phase4v_post_expansion_readiness_audit.json`
- `reports/candidate_ai/full_range/phase4v_post_expansion_readiness_summary.json`
- `docs/phase_reports/phase4k_normalized_history_readiness.md`
- `reports/phase_reports/phase4k_normalized_history_readiness_audit.json`
- `src/ai_fund_lab_v2/candidate_ai/normalized_data_reader.py`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`

## Audit Scope

Phase4-W checks:

- real_runtime `daily_quotes_normalized` discovery
- mock/fixture versus real_runtime identification
- date coverage
- business day coverage
- code coverage
- row coverage
- per-code 60 business day lookback coverage
- chunk scale estimate
- storage estimate
- readiness for real_runtime full controlled feature generation

## Mock Misclassification Guard

Phase4-K mock normalized history must not be treated as real runtime data.

If only mock history exists, the audit emits:

- `SKIPPED_NO_REAL_RUNTIME_DATA`

If real runtime data exists but coverage is insufficient, the audit emits:

- `BLOCKED_BY_REAL_RUNTIME_DATA_COVERAGE`

## Readiness Status

The audit emits one of:

- `READY_FOR_REAL_RUNTIME_FULL_CONTROLLED_FEATURE_GENERATION`
- `BLOCKED_BY_REAL_RUNTIME_DATA_COVERAGE`
- `BLOCKED_BY_STORAGE`
- `BLOCKED_BY_SCHEMA`
- `SKIPPED_NO_REAL_RUNTIME_DATA`

READY requires:

- `is_real_runtime = true`
- `api_call_performed = false`
- `business_day_count >= 60`
- `codes_with_60_business_day_lookback > 0`
- `row_count > 0`
- schema mapping is possible
- runtime free space is sufficient, or the storage check is safely treated as unknown/sufficient

## Output

The coverage summary is written to:

- `reports/candidate_ai/full_range/phase4w_real_runtime_coverage_summary.json`

The audit report is written to:

- `reports/phase_reports/phase4w_real_runtime_coverage_audit.json`
- `docs/phase_reports/phase4w_real_runtime_coverage_audit.md`

## Explicit Non-goals

Phase4-W does not implement:

- real API connection
- J-Quants API call
- mock history as real_runtime
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
- Broker live API
- order placement
- trading
- Portfolio auto-update

## Completion Criteria

Phase4-W is complete when:

- existing normalized runtime data is discovered or clearly skipped.
- mock/real_runtime identification is explicit.
- coverage statistics are produced.
- per-code lookback coverage is produced.
- chunk scale estimate is produced.
- readiness status is produced.
- audit and pytest pass.
