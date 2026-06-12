# Phase4-Q Resume-aware Controlled Runner

## Purpose

Phase4-Q connects the Phase4-P resume/restart checks to the controlled execution runner.

This phase is still a small dry-run only. It does not start full-range Candidate feature generation.

## Read Inputs

- `docs/phase_reports/phase4p_resume_failure.md`
- `docs/phase_reports/phase4p_resume_failure_audit.md`
- `reports/phase_reports/phase4p_resume_failure_audit.json`
- `reports/candidate_ai/full_range/phase4p_resume_failure_summary.json`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_full_range_controlled.py`
- `scripts/check_candidate_features_full_range_resume_failure.py`

## Implemented Scope

- Resume-aware controlled runner.
- Small CLI for resume-aware controlled execution.
- Audit script with fixture-based SUCCESS skip, FAILED rerun, missing run, partial tmp warning, and inconsistency block checks.
- Phase4-Q tests.

## Runner Policy

- `SUCCESS` / `COMPLETED` chunk manifests are skipped.
- `FAILED` / `ERROR` chunk manifests are rerun candidates.
- Missing chunks are run candidates.
- Partial tmp output is reported as a warning.
- Manifest inconsistency blocks execution.
- `max_chunks_to_execute` must be `<= 2`.
- Executed chunks reuse the controlled execution tmp-to-final atomic move.
- Executed chunks must pass schema validation and leakage audit.

## Summary Output

The runner writes:

- `reports/candidate_ai/full_range/phase4q_resume_aware_controlled_summary.json`

The summary includes:

- `status`
- `runner_status`
- `max_chunks_to_execute`
- `planned_chunk_count`
- `skipped_success_chunk_count`
- `rerun_failed_chunk_count`
- `run_missing_chunk_count`
- `executed_chunk_count`
- `blocked_inconsistency_count`
- `partial_tmp_warning_count`
- `completed_chunk_count`
- `failed_chunk_count`
- `feature_generation_executed`
- `label_generation_executed`
- `training_executed`
- `backtest_executed`
- `trading_executed`

## Audit Output

- `reports/phase_reports/phase4q_resume_aware_controlled_runner_audit.json`
- `docs/phase_reports/phase4q_resume_aware_controlled_runner_audit.md`

## Explicit Non-goals

Phase4-Q does not implement:

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

Phase4-Q is complete when:

- SUCCESS chunk skip is confirmed.
- FAILED chunk rerun is confirmed.
- missing chunk run is confirmed.
- partial tmp warning is confirmed.
- manifest inconsistency blocks execution.
- max execution is capped at two chunks.
- tmp-to-final atomic move remains intact.
- schema validation and leakage audit pass for executed chunks.
- audit and pytest pass.
