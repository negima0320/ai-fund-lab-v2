# Phase4-BG Formal Candidate Inference Audit

## Audit Result

- status: `complete`
- readiness_status: `READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT`
- summary: `reports/candidate_ai/full_range/phase4bg_formal_candidate_inference_summary.json`

## Summary

- status: `OK`
- readiness_status: `READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT`
- model_type: `lightgbm.LGBMClassifier`
- model_version: `phase4bf_formal_candidate_model`
- target_date: `2026-06-12`
- input_feature_row_count: `4212`
- eligible_input_count: `4164`
- excluded_input_count: `48`
- scored_count: `4164`
- candidate_count: `50`
- top_n: `50`
- candidate_score_min: `0.05275475`
- candidate_score_max: `0.77225751`
- candidate_score_mean: `0.49145138`
- candidate_score_std: `0.14799808`
- unique_candidate_score_count: `4164`
- all_same_score: `False`
- ranking_effective: `True`
- feature_column_count: `13`
- candidate_reason_coverage: `1.0`
- leakage_audit_status: `OK`
- responsibility_boundary_status: `OK`
- recommended_next_action: `Phase4-BH Formal Candidate Quality Audit; do not backtest, trade, or promote yet.`

## Checks

- OK: `summary_exists`
- OK: `inference_executed`
- OK: `formal_inference`
- OK: `readiness_ready_for_quality_audit`
- OK: `model_artifact_detected`
- OK: `model_manifest_detected`
- OK: `model_version_present`
- OK: `input_rows_positive`
- OK: `eligible_rows_positive`
- OK: `scored_count_matches_eligible`
- OK: `candidate_count_top_n`
- OK: `score_stats_recorded`
- OK: `score_variation_exists`
- OK: `ranking_effective`
- OK: `top50_json_exists`
- OK: `top50_csv_exists`
- OK: `runtime_candidate_output_exists`
- OK: `runtime_inference_output_exists`
- OK: `candidate_schema_ok`
- OK: `candidate_rank_is_sequential`
- OK: `candidate_rank_unique`
- OK: `candidate_score_sorted_desc`
- OK: `candidate_reason_present`
- OK: `feature_snapshot_present`
- OK: `audit_flags_present`
- OK: `no_future_column_used_as_feature`
- OK: `no_label_column_used_as_feature`
- OK: `leakage_audit_ok`
- OK: `responsibility_boundary_ok`
- OK: `no_production_promotion`
- OK: `backtest_trading_broker_order_not_executed`
- OK: `secret_terms_not_emitted`

## Scope Guard

- Formal Candidate inference only.
- Candidate rank is an extraction rank, not a purchase rank.
- No production promotion, backtest, trading, Paper Trading, broker API, or order execution is performed.
