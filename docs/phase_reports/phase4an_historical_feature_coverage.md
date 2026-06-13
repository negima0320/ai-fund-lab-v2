# Phase4-AN Historical Feature Coverage Expansion

## Purpose

Phase4-AN expands Candidate feature coverage from a latest-date snapshot into historical feature rows.

The purpose is to cover the Phase4-AL label target date range so Phase4-AM Dataset Builder can be retried safely.

This phase does not change labels, does not change Dataset Builder, and does not run training, inference, backtest, trading, Paper Trading, Broker APIs, order placement, or Portfolio auto-update.

## Background

Phase4-AM was blocked:

```text
BLOCKED_BY_JOIN_COVERAGE
```

Cause:

```text
feature target_date = 2026-05-29
label target_date range = 2026-03-02 ... 2026-04-27
joined_row_count = 0
```

## Historical Feature Generation

Phase4-AN reads:

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
.runtime/candidate_ai/labels/phase4al_labels_2026-03-02_2026-04-27.json
```

For each normalized `Date + Code`, it builds a feature row using only rows at or before that `Date`.

This preserves the leakage rule:

```text
feature target_date uses only target_date and past data
```

Rows with insufficient lookback are still emitted with:

```text
universe_eligible = false
excluded_reason = insufficient_history
```

This is intentional. Coverage expansion is separate from candidate quality.

## Coverage Criteria

Success requires:

```text
actual feature target_date range includes label target_date range
overlap target_date count > 0
schema validation OK
leakage audit OK
```

Success readiness:

```text
READY_FOR_DATASET_BUILDER_RETRY
```

## Output

Runtime output:

```text
.runtime/candidate_ai/features/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
```

Phase reports:

```text
reports/candidate_ai/full_range/phase4an_historical_feature_coverage_summary.json
reports/phase_reports/phase4an_historical_feature_coverage_audit.json
docs/phase_reports/phase4an_historical_feature_coverage_audit.md
```

## Next Phase

Recommended next phase:

```text
Phase4-AO Dataset Builder Retry
```

Phase4-AO should rerun Dataset Builder with the historical feature table and the existing label table.
