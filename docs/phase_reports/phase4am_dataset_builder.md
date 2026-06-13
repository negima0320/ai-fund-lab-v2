# Phase4-AM Dataset Builder

## Purpose

Phase4-AM joins Candidate feature table rows and label table rows into a training dataset using:

```text
target_date
code
```

This phase builds a dataset only. It does not run LightGBM training, inference, backtest, trading, Paper Trading, Broker APIs, order placement, or Portfolio auto-update.

## Inputs

```text
.runtime/candidate_ai/features/phase4ak_real_runtime_features_2026-05-29.json
.runtime/candidate_ai/labels/phase4al_labels_2026-03-02_2026-04-27.json
```

The builder requires:

```text
Phase4-AK readiness = READY_FOR_LABEL_GENERATION
Phase4-AL readiness = READY_FOR_DATASET_BUILDER
```

## Current Join Coverage

The current Phase4-AK feature table is a latest-date cross section:

```text
feature target_date = 2026-05-29
```

The current Phase4-AL label table contains rows whose 20-day future horizon is available:

```text
label target_date range = 2026-03-02 ... 2026-04-27
```

Therefore, the current real runtime artifacts do not overlap on `target_date + code`.

The builder still executes and writes dataset, manifest, and audit files, but readiness is blocked as:

```text
BLOCKED_BY_JOIN_COVERAGE
```

This is the correct safe result. The builder must not synthesize historical features or move labels into the latest feature table.

## Dataset Schema

Dataset metadata:

```text
target_date
as_of_date
code
dataset_version
feature_version
label_version
split
created_at
```

Feature columns are prefixed:

```text
feature__*
```

Label columns are prefixed:

```text
label__future_return_5d
label__future_return_10d
label__future_return_20d
label__future_max_return_20d
label__future_max_drawdown_20d
label__top_decile_20d
label__downside_bad_20d
label__momentum_candidate_label
```

## Split Rule

The split rule is time-series only:

```text
Train:      2021-06-01 ... 2024-12-31
Validation: 2025-01-01 ... 2025-12-31
Test:       2026-01-01 ...
```

Current available data is in 2026, so joined rows would be assigned to `test`. Missing train/validation periods are allowed at this phase, but random split is not allowed.

## Output

Runtime output:

```text
.runtime/candidate_ai/datasets/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
```

Phase reports:

```text
reports/candidate_ai/full_range/phase4am_dataset_builder_summary.json
reports/phase_reports/phase4am_dataset_builder_audit.json
docs/phase_reports/phase4am_dataset_builder_audit.md
```

## Readiness

Success readiness:

```text
READY_FOR_FIRST_TRAINING
```

Current blocked readiness:

```text
BLOCKED_BY_JOIN_COVERAGE
```

To reach `READY_FOR_FIRST_TRAINING`, the system needs a historical feature table for the same target dates as the label table.

## Next Phase

Before Phase4-AN First LightGBM Training, create a historical feature table for label target dates, then rerun Phase4-AM.
