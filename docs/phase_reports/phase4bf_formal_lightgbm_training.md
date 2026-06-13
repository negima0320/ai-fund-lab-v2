# Phase4-BF Formal LightGBM Training

- status: `OK`
- readiness_status: `READY_FOR_FORMAL_CANDIDATE_INFERENCE`
- purpose: train the first formal Candidate AI model from the Phase4-BE long-history dataset.

## Scope

Phase4-BF performs formal model training and training result audit only.

- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`
- production_model_promoted: `False`
- reader_switch_performed: `False`

## Input

- Phase4-BE long-history dataset
- target label: `label__momentum_candidate_label`
- model input: `feature__*` columns only
- dataset_row_count: `4970227`
- feature_column_count: `13`
- label_column_count: `8`

## Split

- Train: `2021-06-14` to `2024-12-30`
- Validation: `2025-01-06` to `2025-12-30`
- Test: `2026-01-05` to `2026-05-15`

Rows:

- train_row_count: `3581207`
- validation_row_count: `1022775`
- test_row_count: `366245`

Positive label rates:

- train_positive_rate: `0.096144`
- validation_positive_rate: `0.09569`
- test_positive_rate: `0.095594`

Random split is not allowed.

## Leakage Rule

The model must not use:

- `future_return_*`
- `future_max_return_*`
- `future_max_drawdown_*`
- `top_decile_*`
- `downside_bad_*`
- `momentum_candidate_label`
- any `label__*` column

## Model Policy

- Use `lightgbm.LGBMClassifier` when available.
- Use an existing sklearn fallback only if LightGBM is unavailable.
- Record model params and class imbalance strategy in the manifest.

Actual model:

- model_type: `lightgbm.LGBMClassifier`
- class_imbalance_strategy: `scale_pos_weight`
- scale_pos_weight: `9.401052`
- n_estimators: `160`
- learning_rate: `0.05`
- num_leaves: `31`
- min_child_samples: `200`

## Training Result

Validation:

- auc: `0.658141`
- average_precision: `0.158229`
- precision_at_top_50: `0.28`
- candidate_top_decile_rate_at_top_50: `0.28`
- candidate_downside_bad_rate_at_top_50: `0.54`
- candidate_mean_future_return_20d_at_top_50: `0.056965`
- candidate_mean_future_max_return_20d_at_top_50: `0.214404`

Test:

- auc: `0.681583`
- average_precision: `0.173527`
- precision_at_top_50: `0.14`
- candidate_top_decile_rate_at_top_50: `0.22`
- candidate_downside_bad_rate_at_top_50: `0.5`
- candidate_mean_future_return_20d_at_top_50: `-0.022353`
- candidate_mean_future_max_return_20d_at_top_50: `0.149494`

Score distribution:

- score_min: `0.03622431`
- score_max: `0.80317532`
- score_mean: `0.47091076`
- score_std: `0.14338149`
- unique_score_count: `1372347`
- all_same_score: `False`

Model structure:

- tree_count: `160`
- effective_split_count: `4800`
- feature_importance_nonzero_count: `10`

Top feature importances:

- `feature__liquidity_avg_volume_20d`: `827`
- `feature__price_momentum_return_60d`: `744`
- `feature__volatility_return_std_20d`: `692`
- `feature__trend_ma_20_60_ratio`: `559`
- `feature__volume_momentum_ratio_5d`: `455`

Artifacts:

- model_artifact_path: `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl`
- model_manifest_path: `.runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json`
- summary_path: `reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json`

## Readiness

Success readiness:

- `READY_FOR_FORMAL_CANDIDATE_INFERENCE`

Fallback readiness:

- `TRAINING_COMPLETE_WITH_WEAK_MODEL`

Next phase:

- Phase4-BG Formal Candidate Inference.
