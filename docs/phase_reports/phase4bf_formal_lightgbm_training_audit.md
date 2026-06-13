# Phase4-BF Formal LightGBM Training Audit

- status: `complete`
- readiness_status: `READY_FOR_FORMAL_CANDIDATE_INFERENCE`
- summary: `reports/candidate_ai/full_range/phase4bf_formal_lightgbm_training_summary.json`

## Summary

- status: `OK`
- readiness_status: `READY_FOR_FORMAL_CANDIDATE_INFERENCE`
- model_type: `lightgbm.LGBMClassifier`
- dataset_row_count: `4970227`
- train_row_count: `3581207`
- validation_row_count: `1022775`
- test_row_count: `366245`
- feature_column_count: `13`
- label_column_count: `8`
- train_positive_rate: `0.096144`
- validation_positive_rate: `0.09569`
- test_positive_rate: `0.095594`
- validation_auc: `0.658141`
- validation_average_precision: `0.158229`
- validation_precision_at_top_50: `0.28`
- test_auc: `0.681583`
- test_average_precision: `0.173527`
- test_precision_at_top_50: `0.14`
- score_min: `0.03622431`
- score_max: `0.80317532`
- score_mean: `0.47091076`
- score_std: `0.14338149`
- unique_score_count: `1372347`
- all_same_score: `False`
- feature_importance_nonzero_count: `10`
- effective_split_count: `4800`
- leakage_audit_status: `OK`
- recommended_next_action: `Phase4-BG Formal Candidate Inference.`

## Checks

- summary_exists: `True`
- training_executed: `True`
- formal_training: `True`
- readiness_allows_inference: `True`
- model_artifact_exists: `True`
- model_manifest_exists: `True`
- model_payload_has_feature_columns: `True`
- dataset_rows_positive: `True`
- split_rows_positive: `True`
- positive_labels_positive: `True`
- random_split_not_used: `True`
- no_future_column_used_as_feature: `True`
- no_label_column_used_as_feature: `True`
- leakage_audit_ok: `True`
- metrics_recorded: `True`
- score_variation_exists: `True`
- feature_importance_recorded: `True`
- no_production_promotion: `True`
- inference_backtest_trading_not_executed: `True`
- secret_terms_not_emitted: `True`

## Scope Guard

- Formal training only.
- No inference, backtest, trading, promotion, reader switch, broker API, or order placement.
