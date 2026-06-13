# Phase4-AQ Candidate Inference Smoke Audit

## Audit Result

- status: complete
- readiness_status: `READY_FOR_CANDIDATE_OUTPUT_AUDIT_SMOKE`
- summary: `reports/candidate_ai/full_range/phase4aq_candidate_inference_smoke_summary.json`

## Summary

- status: OK
- readiness_status: READY_FOR_CANDIDATE_OUTPUT_AUDIT_SMOKE
- model_type: lightgbm.LGBMClassifier
- target_date: 2026-05-29
- input_feature_row_count: 4221
- eligible_input_count: 3866
- excluded_input_count: 355
- scored_count: 3866
- candidate_count: 50
- top_n: 50
- candidate_score_min: 0.093605
- candidate_score_max: 0.093605
- candidate_score_mean: 0.093605
- feature_column_count: 13
- leakage_audit_status: OK
- recommended_next_action: Phase4-AR Candidate Output Audit Smoke; do not promote, backtest, or trade.

## Checks

- OK: `summary_exists`
- OK: `inference_executed`
- OK: `smoke_test`
- OK: `readiness_ready_for_candidate_output_audit_smoke`
- OK: `model_artifact_detected`
- OK: `model_manifest_detected`
- OK: `input_rows_positive`
- OK: `eligible_rows_positive`
- OK: `scored_count_matches_eligible`
- OK: `candidate_count_top_n`
- OK: `score_stats_recorded`
- OK: `top50_json_exists`
- OK: `top50_csv_exists`
- OK: `runtime_candidate_output_exists`
- OK: `runtime_inference_output_exists`
- OK: `candidate_schema_ok`
- OK: `candidate_rank_is_sequential`
- OK: `candidate_score_sorted_desc`
- OK: `candidate_reason_present`
- OK: `no_future_column_used_as_feature`
- OK: `no_label_column_used_as_feature`
- OK: `leakage_audit_ok`
- OK: `no_production_promotion`
- OK: `backtest_trading_broker_order_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- This audit checks Candidate inference smoke only.
- Candidate rank is a candidate extraction rank, not a purchase rank.
- It confirms no production promotion, backtest, trading, broker API, or order execution is performed.
