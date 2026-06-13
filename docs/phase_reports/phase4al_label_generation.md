# Phase4-AL Label Generation

## Purpose

Phase4-AL generates the Candidate AI label table from `real_runtime` normalized daily quotes.

This phase generates labels only. It does not modify the Phase4-AK feature table, join labels into features, build datasets, train models, infer, backtest, trade, run Paper Trading, promote data, switch readers, call Broker APIs, place orders, or update Portfolio state.

## Inputs

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
.runtime/candidate_ai/features/phase4ak_real_runtime_features_2026-05-29.json
reports/candidate_ai/full_range/phase4ak_real_runtime_feature_generation_summary.json
```

Required Phase4-AK readiness:

```text
READY_FOR_LABEL_GENERATION
```

## Label Columns

Phase4-AL generates:

```text
future_return_5d
future_return_10d
future_return_20d
future_max_return_20d
future_max_drawdown_20d
top_decile_20d
downside_bad_20d
momentum_candidate_label
```

These columns are labels, not features. They must not appear in the Candidate feature table.

## Label Rule

For each `target_date` and `code`, labels are calculated from future normalized close prices.

- `future_return_5d`: `Close_t+5 / Close_t - 1`
- `future_return_10d`: `Close_t+10 / Close_t - 1`
- `future_return_20d`: `Close_t+20 / Close_t - 1`
- `future_max_return_20d`: `max(Close_t+1 ... Close_t+20) / Close_t - 1`
- `future_max_drawdown_20d`: `min(Close_t+1 ... Close_t+20) / Close_t - 1`
- `top_decile_20d`: top 10% by `future_return_20d` within the same `target_date`
- `downside_bad_20d`: `future_max_drawdown_20d <= -0.10`
- `momentum_candidate_label`: `top_decile_20d == true and downside_bad_20d == false`

Rows are generated only where a 20-observation future horizon exists.

## Output

Runtime output:

```text
.runtime/candidate_ai/labels/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
```

Phase reports:

```text
reports/candidate_ai/full_range/phase4al_label_generation_summary.json
reports/phase_reports/phase4al_label_generation_audit.json
docs/phase_reports/phase4al_label_generation_audit.md
```

## Isolation Guard

Phase4-AL verifies:

- feature table is not modified
- feature table is not joined with labels
- label table is physically separate under `.runtime/candidate_ai/labels/`
- labels are not used for inference
- dataset builder is not executed

## Readiness

Success readiness:

```text
READY_FOR_DATASET_BUILDER
```

Blocking statuses:

- `BLOCKED_BY_LABEL_GENERATION`
- `BLOCKED_BY_LABEL_LEAKAGE`
- `BLOCKED_BY_OUTPUT_PATH_SAFETY`

## Next Phase

Recommended next phase:

```text
Phase4-AM Dataset Builder
```

Phase4-AM may join feature and label tables for a training dataset only. Inference datasets must not include labels.
