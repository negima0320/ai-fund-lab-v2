# Phase4-AK Real Runtime Feature Generation Audit

## Audit Result

- status: complete
- readiness_status: `READY_FOR_LABEL_GENERATION`
- summary: `reports/candidate_ai/full_range/phase4ak_real_runtime_feature_generation_summary.json`

## Summary

- status: OK
- readiness_status: READY_FOR_LABEL_GENERATION
- schema_validation_status: OK
- leakage_audit_status: OK
- raw_row_count: 266849
- normalized_row_count: 253736
- feature_row_count: 4350
- eligible_count: 3866
- excluded_count: 484
- business_day_count: 60
- code_count: 4350
- date_min: 2026-03-02
- date_max: 2026-05-29
- feature_column_count: 13
- null_count: 4840
- forbidden_feature_detected: False
- future_column_detected: False
- label_column_detected: False
- recommended_next_action: Phase4-AL Label Generation: create future labels in a physically separate label table; do not mix labels into features.

## Checks

- OK: `summary_exists`
- OK: `feature_output_exists`
- OK: `manifest_exists`
- OK: `audit_exists`
- OK: `readiness_ready_for_label_generation`
- OK: `feature_generation_executed`
- OK: `schema_validation_ok`
- OK: `leakage_audit_ok`
- OK: `feature_rows_positive`
- OK: `eligible_count_positive`
- OK: `required_features_present`
- OK: `forbidden_feature_not_detected`
- OK: `future_column_not_detected`
- OK: `label_column_not_detected`
- OK: `manifest_real_runtime`
- OK: `runtime_candidate_ai_paths`
- OK: `promotion_not_performed`
- OK: `reader_switch_not_performed`
- OK: `label_training_inference_backtest_trading_not_executed`
- OK: `broker_order_paper_portfolio_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks Candidate feature generation only.
- It confirms no label generation, dataset builder, training, inference, backtest, trading, Paper Trading, promotion, reader switch, Broker API, or order placement occurred.
- Phase4-AL may generate future labels in a physically separate label table.
