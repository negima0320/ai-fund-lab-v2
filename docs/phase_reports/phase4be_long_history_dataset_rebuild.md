# Phase4-BE Long History Dataset Rebuild

- status: `OK`
- readiness_status: `READY_FOR_FORMAL_LIGHTGBM_TRAINING`
- joined_row_count: `4970227`
- join_success_rate: `1.0`
- feature_column_count: `13`
- label_column_count: `8`
- target_date range: `2021-06-14` to `2026-05-15`
- purpose: rebuild the formal Candidate AI training dataset from long-history feature and label tables.

## Scope

Phase4-BE performs dataset rebuild and dataset audit only.

- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`
- promotion_performed: `False`
- reader_switch_performed: `False`

Labels are joined only into the training dataset with `label__` prefixes. Inference datasets must not include labels; inference datasets must not include labels.

## Input

- Phase4-BC long-history feature table
- Phase4-BD long-history label table

Join key:

- `target_date`
- `code`

## Output

- `.runtime/candidate_ai/datasets/`
- `.runtime/candidate_ai/manifests/`
- `.runtime/candidate_ai/audit/`
- `reports/candidate_ai/full_range/phase4be_long_history_dataset_rebuild_summary.json`
- `reports/phase_reports/phase4be_long_history_dataset_rebuild_audit.json`

## Split

- Train: `2021-09-09` to `2024-12-31`
- Validation: `2025-01-01` to `2025-12-31`
- Test: `2026-01-01` to `2026-05-15`

## Split Result

- train_row_count: `3341627`
- train_positive_count: `320996`
- train_positive_rate: `0.09606`
- validation_row_count: `1022775`
- validation_positive_count: `97869`
- validation_positive_rate: `0.09569`
- test_row_count: `366245`
- test_positive_count: `35011`
- test_positive_rate: `0.095594`

## Leakage Rule

- `future_return_*`, `future_max_return_*`, `future_max_drawdown_*`, `top_decile_*`, `downside_bad_*`, and `momentum_candidate_label` must not appear in feature columns.
- Feature columns are stored as `feature__*`.
- Label columns are stored as `label__*`.

Result:

- future_column_detected_in_features: `False`
- label_column_detected_in_features: `False`
- feature_column_detected_in_labels: `False`
- leakage_audit_status: `OK`

## Dataset Feature Quality

- train_all_null_feature_count: `0`
- train_constant_feature_count: `0`
- train_high_null_feature_count: `0`
- train_feature_variance_available: `True`
- validation_feature_variance_available: `True`
- test_feature_variance_available: `True`

## Scope Guard

- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`
- promotion_performed: `False`
- reader_switch_performed: `False`

## Readiness

Success readiness:

- `READY_FOR_FORMAL_LIGHTGBM_TRAINING`

Next phase:

- Phase4-BF Formal LightGBM Training.
