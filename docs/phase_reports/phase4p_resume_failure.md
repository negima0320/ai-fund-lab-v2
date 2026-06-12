# Phase4-P Controlled Execution Failure / Resume Audit

## Purpose

Phase4-P fixes the failure and resume/restart behavior for Phase4-O controlled execution before any full-range Candidate feature generation is allowed.

The goal is to confirm that a failed controlled chunk does not pollute final feature outputs, and that existing manifests can drive safe skip/rerun decisions.

## Read Inputs

- `docs/phase_reports/phase4o_full_range_controlled_execution.md`
- `docs/phase_reports/phase4o_full_range_controlled_execution_audit.md`
- `reports/phase_reports/phase4o_full_range_controlled_execution_audit.json`
- `reports/candidate_ai/full_range/phase4o_full_range_controlled_summary.json`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_full_range_controlled.py`
- `scripts/audit_phase4o_full_range_controlled_execution.py`

## Implemented Scope

- Test-only controlled execution failure injection.
- Failed chunk manifest recording.
- Resume/restart detection for completed, failed, missing, partial, unknown, and duplicate states.
- Fixture-only resume failure check script.
- Phase4-P audit script and reports.

## Failure Injection

`ControlledExecutionFailureInjection` supports these test-only switches:

- `force_schema_validation_failure`
- `force_leakage_audit_failure`
- `force_write_failure`
- `force_atomic_move_failure`

Default behavior is unchanged because all switches default to false.

## Validation Failure Policy

When schema validation failure is injected:

- final output is not written.
- tmp output remains isolated under `.runtime/candidate_ai/tmp/full_range/`.
- chunk manifest status is `FAILED`.
- error message records `validation failure injected`.
- run manifest increments `failed_chunk_count`.

## Leakage Failure Policy

When leakage audit failure is injected:

- final output is not written.
- chunk manifest status is `FAILED`.
- error message records `leakage failure injected`.
- run manifest increments `failed_chunk_count`.

## Write / Atomic Move Failure Policy

When write failure is injected:

- final output is not written.
- chunk manifest status is `FAILED`.
- error message records `write failure injected`.

When atomic move failure is injected:

- tmp output remains isolated.
- final output is not written.
- chunk manifest status is `FAILED`.
- error message records `atomic move failure injected`.

## Resume / Restart Policy

- `SUCCESS` or `COMPLETED` manifest becomes a skip candidate.
- `FAILED` or `ERROR` manifest becomes a rerun candidate.
- partial tmp output creates a warning.
- `SUCCESS` manifest with missing final output creates an inconsistency.
- unknown manifest status creates an inconsistency.
- duplicate chunk manifest creates an inconsistency.

## Runtime Outputs

The fixture check writes:

- `reports/candidate_ai/full_range/phase4p_resume_failure_summary.json`

The audit writes:

- `reports/phase_reports/phase4p_resume_failure_audit.json`
- `docs/phase_reports/phase4p_resume_failure_audit.md`

## Explicit Non-goals

Phase4-P does not implement:

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

Phase4-P is complete when:

- validation and leakage failures do not write final outputs.
- failed chunk manifests are recorded.
- completed chunks are skip candidates.
- failed chunks are rerun candidates.
- partial tmp, missing output, unknown status, and duplicate manifests are detected.
- run manifest counts are updated.
- audit and pytest pass.
