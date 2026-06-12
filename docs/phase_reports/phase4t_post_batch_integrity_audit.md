# Phase4-T Post-batch Integrity Audit

## Audit Result

- status: complete
- integrity_status: `READY_FOR_CONTROLLED_BATCH_EXPANSION`
- recommended_next_action: ready for controlled batch expansion with the same stop-on-first-failure guard
- summary: `reports/candidate_ai/full_range/phase4t_post_batch_integrity_summary.json`

## Integrity Summary

- checked_chunk_count: 2
- final_output_exists_count: 2
- tmp_leftover_count: 0
- chunk_manifest_count: 2
- chunk_audit_count: 2
- success_manifest_count: 2
- failed_manifest_count: 0
- row_count_match: True
- eligible_excluded_count_match: True
- schema_validation_all_ok: True
- leakage_audit_all_ok: True
- resume_success_skip_ready: True
- duplicate_output_count: 0
- duplicate_manifest_count: 0
- orphan_output_count: 0
- orphan_manifest_count: 0

## Checks

- OK: `phase4s_summary_exists`
- OK: `post_batch_integrity_summary_exists`
- OK: `final_output_exists`
- OK: `chunk_manifest_exists`
- OK: `chunk_audit_exists`
- OK: `run_manifest_exists`
- OK: `row_count_consistency_checked`
- OK: `eligible_excluded_consistency_checked`
- OK: `schema_leakage_ok_checked`
- OK: `resume_success_skip_checked`
- OK: `duplicate_orphan_detection_exists`
- OK: `integrity_status_produced`
- OK: `ready_or_clear_blocked_or_skipped_status_produced`
- OK: `full_range_generation_not_executed`
- OK: `label_generation_not_implemented`
- OK: `training_inference_backtest_trading_not_implemented`
- OK: `no_secret_terms_in_reports`

## Scope Guard

- This audit only checks artifacts from a two-chunk controlled batch.
- It does not implement all-chunk generation, labels, dataset building, training, inference, backtest, broker API, orders, trading, or Portfolio auto-update.
