# Phase4-Y Real Runtime Normalized Rebuild Plan

## Purpose

Phase4-Y defines the plan for rebuilding real_runtime `daily_quotes_normalized` from real J-Quants raw daily quotes without overwriting Phase4-K mock normalized history.

This phase is design and dry-run planning only. It does not execute normalized rebuilds.

## Read Inputs

- `docs/phase_reports/phase4x_real_runtime_normalized_source.md`
- `docs/phase_reports/phase4x_real_runtime_normalized_source_audit.md`
- `reports/phase_reports/phase4x_real_runtime_normalized_source_audit.json`
- `reports/candidate_ai/full_range/phase4x_real_runtime_normalized_source_summary.json`
- Phase1 Data Foundation normalization code
- runtime raw and normalized data locations

## Isolated Output Path

The planned real_runtime normalized output is isolated from the default mock path:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
```

This prevents accidental overwrite of:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
```

The isolated manifest is planned at:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/manifest.json
```

## Schema Mapping

The plan follows the existing `normalize_daily_quotes()` behavior:

```text
Date -> Date
Code -> Code
AdjO or O -> Open
AdjH or H -> High
AdjL or L -> Low
AdjC or C -> Close
AdjVo or Vo -> Volume
```

## Dry-run Diff

The audit reads raw records and applies the normalizer in memory to estimate:

- raw input row count
- expected normalized row count
- expected date range
- expected code count
- existing mock normalized row count
- existing mock normalized date range
- overwrite risk
- isolated output path

No normalized output is written.

## Provenance Manifest Design

The future real_runtime normalized manifest must include:

- `data_source_type = real_runtime`
- `source_provider = jquants`
- `api_call_performed = false`
- `source_raw_path`
- `source_raw_manifest_path`
- `created_at`
- `normalizer_version`
- `schema_version`
- `row_count`
- `code_count`
- `date_min`
- `date_max`
- `input_hash_optional`
- `output_hash_optional`

## Promotion / Switch Conditions

Candidate readers may use the isolated real_runtime path only when:

- provenance manifest exists.
- `data_source_type` is `real_runtime`.
- `source_provider` is `jquants`.
- mock manifest is absent for the selected path.
- `api_call_performed` is explicitly recorded.
- schema validation is OK.
- coverage audit is OK.
- reader selection is gated by manifest provenance, not by path alone.

## Rollback Plan

Rollback is simple because the default mock path is unchanged:

- delete isolated real_runtime output directory.
- keep the default mock normalized path untouched.
- keep reader selection behind a manifest gate.
- run coverage audit before any promotion.

## Readiness Status

The audit emits one of:

- `READY_TO_IMPLEMENT_ISOLATED_REAL_RUNTIME_NORMALIZED_REBUILD`
- `BLOCKED_BY_MISSING_RAW`
- `BLOCKED_BY_MISSING_NORMALIZER`
- `BLOCKED_BY_SCHEMA_MAPPING`
- `BLOCKED_BY_OVERWRITE_RISK`
- `BLOCKED_BY_UNKNOWN_PROVENANCE`
- `SKIPPED_NO_RAW`

## Explicit Non-goals

Phase4-Y does not implement:

- normalized rebuild execution
- mock history overwrite
- J-Quants API call
- credential request
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

Phase4-Y is complete when:

- isolated output path is defined.
- schema mapping is defined.
- dry-run diff is produced.
- provenance manifest design is defined.
- promotion condition is defined.
- rollback plan is defined.
- readiness status is produced.
- audit and pytest pass.
