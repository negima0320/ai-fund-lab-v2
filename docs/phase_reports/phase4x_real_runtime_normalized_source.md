# Phase4-X Real Runtime Normalized History Source Audit

## Purpose

Phase4-X audits existing `.runtime` raw, normalized, and manifest files to decide whether real J-Quants-derived `daily_quotes_normalized` history can be safely identified or rebuilt without calling the API.

This phase does not execute a rebuild. It only audits provenance and feasibility.

## Read Inputs

- `docs/phase_reports/phase4w_real_runtime_coverage.md`
- `docs/phase_reports/phase4w_real_runtime_coverage_audit.md`
- `reports/phase_reports/phase4w_real_runtime_coverage_audit.json`
- `reports/candidate_ai/full_range/phase4w_real_runtime_coverage_summary.json`
- `docs/phase_reports/phase4k_normalized_history_readiness.md`
- `reports/candidate_ai/phase4k_mock_normalized_history_manifest.json`
- Phase1 Data Foundation runtime paths, raw data, normalized data, and manifests

## Audit Scope

Phase4-X classifies:

- real raw J-Quants data
- real normalized J-Quants data
- mock normalized history
- fixture data
- missing data

It then checks:

- whether existing normalized history can be trusted as real_runtime
- whether existing raw data can rebuild real_runtime normalized history
- whether manifest provenance proves J-Quants origin
- whether mock/fixture data is kept separate

## Provenance Rules

`real_runtime` classification is intentionally strict:

- Phase1 Data Foundation manifest exists.
- mock manifest is absent for the selected normalized file.
- fixture markers are absent.
- source provider or endpoint is J-Quants, such as `/v2/equities/bars/daily`.
- no API call is performed by this audit.
- storage schema matches `daily_quotes_normalized` when normalized data is considered.

If normalized history is marked as Phase4-K mock, it is not trusted as real_runtime.

## Rebuild Feasibility

Rebuild feasibility is true only when:

- raw daily quotes exist.
- raw manifest exists.
- the normalizer function exists.
- the audit can identify the raw data as J-Quants derived.

If rebuilding would overwrite mock normalized history at the default output path, the audit reports `would_overwrite_mock_history=true` and recommends using an isolated output path or clearing mock history first.

## Readiness Status

The audit emits one of:

- `READY_TO_REBUILD_REAL_RUNTIME_NORMALIZED_FROM_RAW`
- `READY_TO_USE_EXISTING_REAL_RUNTIME_NORMALIZED`
- `BLOCKED_BY_MISSING_RAW_DATA`
- `BLOCKED_BY_MISSING_MANIFEST`
- `BLOCKED_BY_MOCK_ONLY`
- `BLOCKED_BY_UNKNOWN_PROVENANCE`
- `SKIPPED_NO_RUNTIME_DATA`

## Output

The source summary is written to:

- `reports/candidate_ai/full_range/phase4x_real_runtime_normalized_source_summary.json`

The audit report is written to:

- `reports/phase_reports/phase4x_real_runtime_normalized_source_audit.json`
- `docs/phase_reports/phase4x_real_runtime_normalized_source_audit.md`

## Explicit Non-goals

Phase4-X does not implement:

- J-Quants API calls
- real API connection
- credential requests
- normalized rebuild execution
- mock history overwrite
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

Phase4-X is complete when:

- runtime inventory is produced.
- provenance classification is produced.
- mock history is not misclassified.
- rebuild feasibility is assessed.
- readiness status is produced.
- audit and pytest pass.
