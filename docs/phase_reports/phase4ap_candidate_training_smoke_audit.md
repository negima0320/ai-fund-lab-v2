# Phase4-AP Candidate Training Smoke Audit

## Audit Result

- status: complete
- readiness_status: `READY_FOR_CANDIDATE_INFERENCE_SMOKE`
- summary: `reports/candidate_ai/full_range/phase4ap_candidate_training_smoke_summary.json`

## Summary

- status: OK
- readiness_status: READY_FOR_CANDIDATE_INFERENCE_SMOKE
- model_type: lightgbm.LGBMClassifier
- dataset_row_count: 167668
- smoke_train_row_count: 117900
- smoke_validation_row_count: 49768
- feature_column_count: 13
- label_column_count: 8
- positive_label_rate: 0.094413
- auc: 0.5
- average_precision: 0.096327
- accuracy: 0.903673
- precision_at_top_50: 0.0
- leakage_audit_status: OK
- recommended_next_action: Phase4-AQ Candidate Inference Smoke using the smoke model; do not promote to production.

## Checks

- OK: `summary_exists`
- OK: `training_executed`
- OK: `smoke_test`
- OK: `readiness_ready_for_candidate_inference_smoke`
- OK: `model_artifact_exists`
- OK: `model_manifest_exists`
- OK: `model_payload_has_feature_columns`
- OK: `dataset_rows_positive`
- OK: `smoke_train_rows_positive`
- OK: `smoke_validation_rows_positive`
- OK: `positive_labels_positive`
- OK: `random_split_not_used`
- OK: `no_future_column_used_as_feature`
- OK: `no_label_column_used_as_feature`
- OK: `leakage_audit_ok`
- OK: `metrics_recorded`
- OK: `no_production_promotion`
- OK: `inference_backtest_trading_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks Candidate AI training smoke only.
- It confirms no random split is used.
- It confirms future and label columns are not used as features.
- It confirms no production promotion, backtest, or trading is executed.
