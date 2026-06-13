# Phase4-AE Post-fetch Raw Coverage Audit

## Audit Result

- status: incomplete
- readiness_status: `BLOCKED_BY_REQUEST_MANIFEST_MISMATCH`
- summary: `reports/candidate_ai/full_range/phase4ae_post_fetch_raw_coverage_summary.json`

## Summary

- status: BLOCKED
- readiness_status: BLOCKED_BY_REQUEST_MANIFEST_MISMATCH
- phase4ad_readiness_status: READY_FOR_POST_FETCH_RAW_AUDIT
- planned_request_count: 59
- completed_request_count: 59
- raw_response_file_count: 65
- request_manifest_count: 65
- fetched_date_min: 2026-03-02
- fetched_date_max: 2026-05-29
- fetched_date_count: 60
- fetched_business_day_count: 60
- required_business_day_count: 60
- coverage_sufficient_for_features: True
- missing_business_day_count: 0
- empty_response_date_count: 5
- row_count: 266849
- code_count: 4505
- duplicate_date_code_count: 0
- raw_schema_status: OK
- manifest_consistency_status: ERROR
- recommended_next_action: Phase4-AF Real Runtime Normalized Rebuild from Raw.

## Checks

- OK: `summary_exists`
- OK: `phase4ad_summary_detected`
- OK: `raw_manifest_detected`
- NG: `request_manifest_count_ok`
- NG: `response_file_count_ok`
- OK: `completed_request_count_ok`
- OK: `raw_schema_checked`
- OK: `manifest_consistency_checked`
- OK: `coverage_decision_produced`
- OK: `normalized_not_executed`
- OK: `mock_path_not_written`
- OK: `promotion_not_performed`
- OK: `reader_switch_not_performed`
- OK: `feature_label_training_backtest_trading_not_executed`
- OK: `secret_not_detected`

## Scope Guard

- Phase4-AE audits raw coverage only.
- It does not call APIs, fetch, refetch, write normalized data, promote data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.
