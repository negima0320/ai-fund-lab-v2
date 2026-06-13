# Phase4-AJ Real Runtime Normalized Rebuild from Raw

## Purpose

Phase4-AJ rebuilds isolated `real_runtime` daily quotes normalized data from the raw J-Quants daily quote response files fetched in Phase4-AD and Phase4-AH.

This phase performs normalization only. It does not promote the output, switch readers, generate Candidate features, generate labels, build datasets, train, infer, backtest, trade, call Broker APIs, place orders, run Paper Trading, or update Portfolio state.

## Input

- Raw response directory: `.runtime/data/raw/jquants/equities_bars_daily/responses/`
- Raw run manifest: `.runtime/data/raw/jquants/equities_bars_daily/manifest.json`
- Phase4-AI coverage summary: `reports/candidate_ai/full_range/phase4ai_post_extension_raw_coverage_summary.json`

Phase4-AJ requires Phase4-AI readiness:

```text
READY_FOR_REAL_RUNTIME_NORMALIZED_REBUILD
```

## Normalized Mapping

Phase4-AJ uses the existing Phase1 normalizer:

```text
normalize_daily_quotes()
```

The normalized schema is `daily_quotes_normalized` schema version 2.

Mapping policy:

- `Open`: `AdjO` if complete, otherwise `O`
- `High`: `AdjH` if complete, otherwise `H`
- `Low`: `AdjL` if complete, otherwise `L`
- `Close`: `AdjC` if complete, otherwise `C`
- `Volume`: `AdjVo` if complete, otherwise `Vo`
- `PriceSource`: `adjusted` or `unadjusted`

If a raw row has `Date` and `Code` but both adjusted and unadjusted OHLCV fields are missing, Phase4-AJ excludes that row from normalized output and records it as `price_missing_excluded_count`. This keeps the normalized schema strict: normalized rows must not contain null price columns.

## Output

The only normalized output path Phase4-AJ may update is:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/
```

Expected files:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/manifest.json
```

The default mock normalized path must remain unchanged:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/
```

## Promotion and Reader Switch

Phase4-AJ explicitly records:

```text
promotion_status = not_promoted
promotion_performed = false
reader_switch_performed = false
```

Promotion and reader switching are out of scope.

## Readiness Criteria

Success readiness is:

```text
READY_FOR_REAL_RUNTIME_FEATURE_GENERATION
```

Required conditions:

- normalized schema mapping is OK
- normalization error count is 0
- raw rows are accounted for by `normalized_row_count + price_missing_excluded_count`
- business day count is at least 60
- mock normalized path is unchanged
- promotion is not performed
- reader switch is not performed

Blocking statuses:

- `BLOCKED_BY_RAW_SCHEMA`
- `BLOCKED_BY_NORMALIZATION_ERROR`
- `BLOCKED_BY_OUTPUT_PATH_SAFETY`
- `BLOCKED_BY_PROMOTION_RULE`

## Audit Outputs

Phase4-AJ writes:

```text
reports/candidate_ai/full_range/phase4aj_real_runtime_normalized_summary.json
reports/phase_reports/phase4aj_real_runtime_normalized_audit.json
docs/phase_reports/phase4aj_real_runtime_normalized_audit.md
```

## Next Phase

Recommended next phase:

```text
Phase4-AK Real Runtime Feature Generation
```

Phase4-AK may run the Candidate Feature Builder against the isolated `real_runtime` normalized 60-business-day history. It still must not train the Candidate AI.
