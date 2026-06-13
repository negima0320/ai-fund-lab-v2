# Phase4-BD Long History Label Regeneration

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_DATASET_REBUILD`
- label_row_count: `4970227`
- label_column_count: `8`
- label target_date range: `2021-06-14` to `2026-05-15`
- label_target_date_count: `1202`
- code_count: `4780`
- momentum_candidate_label_positive_rate: `0.09601`
- purpose: regenerate Candidate AI label table from long-history real_runtime normalized data.

## Scope

Phase4-BD performs label regeneration and label audit only.

- feature table is not modified
- feature table is not joined
- dataset_rebuild_executed: `False`
- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`
- promotion_performed: `False`
- reader_switch_performed: `False`

## Input

- `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet`
- `.runtime/candidate_ai/features/` Phase4-BC long-history feature artifact reference

## Output

- `.runtime/candidate_ai/labels/`
- `.runtime/candidate_ai/manifests/`
- `.runtime/candidate_ai/audit/`
- `reports/candidate_ai/full_range/phase4bd_long_history_label_regeneration_summary.json`
- `reports/phase_reports/phase4bd_long_history_label_regeneration_audit.json`

## Label Scope

Generated label columns:

- `future_return_5d`
- `future_return_10d`
- `future_return_20d`
- `future_max_return_20d`
- `future_max_drawdown_20d`
- `top_decile_20d`
- `downside_bad_20d`
- `momentum_candidate_label`

These columns are labels only. They must not be written into the feature table.

## Label Counts

- future_return_5d_count: `4970227`
- future_return_10d_count: `4970227`
- future_return_20d_count: `4970227`
- future_max_return_20d_count: `4970227`
- future_max_drawdown_20d_count: `4970227`
- top_decile_20d_count: `497577`
- downside_bad_20d_count: `759344`
- momentum_candidate_label_count: `477192`

## Split Distribution

- train_label_row_count_estimate: `3341627`
- train_positive_rate: `0.09606`
- validation_label_row_count_estimate: `1022775`
- validation_positive_rate: `0.09569`
- test_label_row_count_estimate: `366245`
- test_positive_rate: `0.095594`

## Isolation Audit

- feature_table_modified: `False`
- feature_table_joined: `False`
- leakage_audit_status: `OK`
- dataset_rebuild_executed: `False`
- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`
- promotion_performed: `False`
- reader_switch_performed: `False`

## Horizon Rule

Labels use future data after `target_date`.

- 5d / 10d / 20d returns use the future 5th / 10th / 20th business-day close.
- `future_max_return_20d` and `future_max_drawdown_20d` use the next 20 business days.
- rows without a complete 20-business-day future horizon are excluded from the label table and counted as unavailable tail rows.

Result:

- label_unavailable_tail_target_date_count: `1220`
- label_unavailable_tail_row_count: `96172`

## Readiness

Success readiness:

- `READY_FOR_LONG_HISTORY_DATASET_REBUILD`

Next phase:

- Phase4-BE Long History Dataset Rebuild.
