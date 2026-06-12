# Phase4-Z Isolated Real Runtime Normalized Rebuild

## Purpose

Phase4-Z rebuilds real_runtime `daily_quotes_normalized` from existing real J-Quants raw daily quotes into an isolated no-promotion path.

This phase writes only to the isolated real_runtime normalized path. It does not overwrite the default mock normalized path, switch readers, promote data, generate Candidate features, generate labels, train, infer, backtest, trade, call APIs, place orders, or update Portfolio state.

## Read Inputs

- `docs/phase_reports/phase4y_real_runtime_normalized_rebuild_plan.md`
- `docs/phase_reports/phase4y_real_runtime_normalized_rebuild_plan_audit.md`
- `reports/phase_reports/phase4y_real_runtime_normalized_rebuild_plan_audit.json`
- `reports/candidate_ai/full_range/phase4y_real_runtime_normalized_rebuild_plan_summary.json`
- `.runtime/data/raw/jquants/equities_bars_daily/data.parquet`
- `.runtime/data/raw/jquants/manifest.jsonl`
- Phase1 Data Foundation normalizer

## Isolated Output

The isolated output path is:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
```

The isolated provenance manifest is:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/manifest.json
```

The default mock path remains unchanged:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
```

## Schema Mapping

The rebuild follows the existing `normalize_daily_quotes()` mapping:

```text
Date -> Date
Code -> Code
AdjO or O -> Open
AdjH or H -> High
AdjL or L -> Low
AdjC or C -> Close
AdjVo or Vo -> Volume
```

## Provenance Manifest

The manifest includes:

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
- `promotion_status = not_promoted`
- `mock_history_overwritten = false`

## Coverage Status

`ISOLATED_REAL_RUNTIME_NORMALIZED_READY` means the isolated rebuild succeeded.

It does not imply the data has enough history for 60-day Candidate feature generation. A one-day raw snapshot is expected to produce:

```text
isolated rebuild success but insufficient for 60-day Candidate feature generation
```

## Output Reports

Summary:

- `reports/candidate_ai/full_range/phase4z_real_runtime_normalized_isolated_summary.json`

Audit:

- `reports/phase_reports/phase4z_real_runtime_normalized_isolated_audit.json`
- `docs/phase_reports/phase4z_real_runtime_normalized_isolated_audit.md`

## Explicit Non-goals

Phase4-Z does not implement:

- default mock normalized overwrite
- reader switch
- promotion
- Candidate feature generation
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
- J-Quants API call
- order placement
- trading
- Portfolio auto-update

## Completion Criteria

Phase4-Z is complete when:

- isolated output exists.
- isolated manifest exists.
- manifest provenance is real_runtime/J-Quants/no API call.
- default mock path is unchanged.
- promotion is not performed.
- coverage stats are produced.
- audit and pytest pass.
