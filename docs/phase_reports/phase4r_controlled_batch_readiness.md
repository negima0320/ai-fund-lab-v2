# Phase4-R Controlled Batch Readiness Audit

## Purpose

Phase4-R creates the final readiness gate before any controlled batch execution over the full chunk plan.

This phase is audit-only. It does not execute all chunks or start full-range feature generation.

## Read Inputs

- `docs/phase_reports/phase4q_resume_aware_controlled_runner.md`
- `docs/phase_reports/phase4q_resume_aware_controlled_runner_audit.md`
- `reports/phase_reports/phase4q_resume_aware_controlled_runner_audit.json`
- `reports/candidate_ai/full_range/phase4q_resume_aware_controlled_summary.json`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_full_range_resume_controlled.py`
- `scripts/audit_phase4q_resume_aware_controlled_runner.py`
- `docs/phase_reports/phase4l_full_range_feature_dry_run_design.md`
- `docs/phase_reports/phase4m_full_range_feature_dry_run_skeleton.md`
- `docs/phase_reports/phase4n_full_range_no_write_gate.md`
- `docs/phase_reports/phase4o_full_range_controlled_execution.md`
- `docs/phase_reports/phase4p_resume_failure.md`

## Readiness Gate

The audit emits one of these gate statuses:

- `READY_FOR_CONTROLLED_BATCH_EXECUTION`
- `BLOCKED_BY_CHUNK_PLAN`
- `BLOCKED_BY_RESUME_STATE`
- `BLOCKED_BY_MANIFEST_INCONSISTENCY`
- `BLOCKED_BY_STORAGE`
- `BLOCKED_BY_SCHEMA`
- `BLOCKED_BY_LEAKAGE`
- `SKIPPED_NO_DATA`

## READY Conditions

The gate is READY only when:

- `chunk_count > 0`
- `input_row_count > 0`
- `manifest_inconsistency_count = 0`
- `resume_state_consistent = true`
- `feature_version_consistent = true`
- `schema_version_consistent = true`
- `data_source_type_consistent = true`
- `preflight_schema_validation_status = OK`
- `preflight_leakage_audit_status = OK`
- runtime free space is sufficient, or free-space check is explicitly handled
- `stop_on_first_failure = true`
- `max_failed_chunks_allowed = 0`

## Batch Summary Output

The summary is written to:

- `reports/candidate_ai/full_range/phase4r_controlled_batch_readiness_summary.json`

It includes:

- chunk/date/code chunk counts
- input row count
- estimated feature row count
- estimated output size
- runtime free-space check
- completed / failed / missing chunk counts
- partial tmp warning count
- manifest inconsistency count
- version consistency checks
- resume state consistency
- preflight schema and leakage audit status
- stop condition
- recommended next action

## Stop Condition

- `stop_on_first_failure = true`
- `max_failed_chunks_allowed = 0`
- If any chunk fails, controlled batch execution must stop.
- Final output remains only for successful chunks.
- FAILED chunks must be recorded by manifest and become resume/rerun targets.

## Rerun Procedure

- SUCCESS chunks are skipped.
- FAILED chunks are rerun.
- Missing chunks are run.
- Partial tmp outputs must be reviewed and isolated.
- Manifest inconsistency blocks execution.

## Storage Guard

The audit checks free space under the runtime directory with `shutil.disk_usage` when available.

If the check cannot be performed, the summary records `UNKNOWN` rather than silently passing without evidence.

## Explicit Non-goals

Phase4-R does not implement:

- all-chunk feature generation
- full-period feature generation
- label generation
- dataset builder
- Candidate AI model
- training
- inference
- backtest
- Historical Evaluation
- Opportunity AI
- Position Management AI
- Capital Allocation
- Paper Trading
- Order Manager
- Broker live API
- order placement
- trading
- Portfolio auto-update

## Completion Criteria

Phase4-R is complete when:

- batch readiness summary is generated.
- gate status is produced.
- chunk count and distribution are checked.
- estimated output size is produced.
- storage guard is present.
- resume and manifest consistency are checked.
- stop condition is explicit.
- audit and pytest pass.
