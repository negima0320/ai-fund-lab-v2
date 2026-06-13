# Phase4-AO Dataset Builder Retry

## Purpose

Phase4-AO retries the Candidate AI dataset builder after Phase4-AN expanded historical feature coverage.

Phase4-AM was blocked because the feature table only had `target_date = 2026-05-29`, while the label table covered `2026-03-02` to `2026-04-27`. Phase4-AN generated historical feature rows for each `target_date + code`, so Phase4-AO joins the historical feature table and label table again.

## Scope

Phase4-AO does only the dataset builder retry.

It performs:

- dataset build retry
- join coverage audit
- feature / label separation check
- time-series split generation
- leakage audit
- dataset statistics

It does not perform:

- LightGBM training
- inference
- backtest
- trading

## Inputs

- Historical feature table from Phase4-AN
- Label table from Phase4-AL

Join key:

```text
target_date
code
```

## Dataset Shape

Dataset rows keep feature and label columns physically separated:

```text
feature__*
label__*
```

Feature columns must not contain:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
candidate_label
backtest
trade
portfolio
order
pnl
```

## Split Rule

Phase4-AO keeps the Phase4-B time-series split rule:

```text
Train:      <= 2024-12-31
Validation: 2025-01-01 to 2025-12-31
Test:       >= 2026-01-01
```

Current real_runtime data is 2026-only, so rows are expected to fall into the test split. Missing train and validation periods are acceptable at this phase as long as random split is not introduced.

## Readiness

Readiness is `READY_FOR_FIRST_LIGHTGBM_TRAINING` when:

- `joined_row_count > 0`
- `join_success_rate > 0`
- leakage audit is `OK`
- feature / label separation is maintained
- training, inference, backtest, and trading are not executed

Otherwise readiness remains blocked by one of:

- `BLOCKED_BY_JOIN_COVERAGE`
- `BLOCKED_BY_DATASET_BUILDER`
- `BLOCKED_BY_LEAKAGE_AUDIT`

## Outputs

Runtime outputs:

```text
.runtime/candidate_ai/datasets/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
```

Reports:

```text
reports/candidate_ai/full_range/phase4ao_dataset_retry_summary.json
reports/phase_reports/phase4ao_dataset_retry_audit.json
docs/phase_reports/phase4ao_dataset_retry_audit.md
```

## Next Phase

If readiness is `READY_FOR_FIRST_LIGHTGBM_TRAINING`, the next phase is Phase4-AP First LightGBM Training.
