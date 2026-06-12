# Phase4-S First Controlled Batch Execution

## Purpose

Phase4-S executes the first controlled batch with an explicit small limit before any all-chunk or full-period generation is allowed.

This phase confirms that the Phase4-R readiness gate can protect execution, and that the Phase4-Q resume-aware runner can safely execute multiple chunks.

## Read Inputs

- `docs/phase_reports/phase4r_controlled_batch_readiness.md`
- `docs/phase_reports/phase4r_controlled_batch_readiness_audit.md`
- `reports/phase_reports/phase4r_controlled_batch_readiness_audit.json`
- `reports/candidate_ai/full_range/phase4r_controlled_batch_readiness_summary.json`
- `docs/phase_reports/phase4q_resume_aware_controlled_runner.md`
- `reports/candidate_ai/full_range/phase4q_resume_aware_controlled_summary.json`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_full_range_resume_controlled.py`

## Execution Guard

Phase4-S requires:

- `gate_status = READY_FOR_CONTROLLED_BATCH_EXECUTION`
- `manifest_inconsistency_count = 0`
- `runtime_free_space_sufficient = true`
- `preflight_schema_validation_status = OK`
- `preflight_leakage_audit_status = OK`
- `max_chunks_to_execute = 2`
- `stop_on_first_failure = true`
- `max_failed_chunks_allowed = 0`

If the readiness gate is not READY, execution is skipped and the summary is `BLOCKED`.

## Controlled Batch Policy

- SUCCESS chunks are skipped.
- FAILED chunks are rerun.
- Missing chunks are run.
- Partial tmp output is reported as warning through the underlying resume-aware runner.
- Manifest inconsistency blocks execution.
- At most two chunks are executed.

## Success Behavior

For each successful chunk:

- output is first written under `.runtime/candidate_ai/tmp/full_range/`.
- schema validation must be `OK`.
- leakage audit must be `OK`.
- tmp output is atomically moved to final feature output.
- chunk manifest status is `SUCCESS`.
- run manifest is updated.

## Failure Behavior

If a chunk fails:

- final output is not written for the failed chunk.
- chunk manifest status is `FAILED`.
- `stop_on_first_failure = true` stops subsequent chunk execution.
- run manifest records the failed chunk.
- summary records `stopped_on_failure` and `stop_reason`.

## Summary Output

The Phase4-S summary is written to:

- `reports/candidate_ai/full_range/phase4s_first_controlled_batch_summary.json`

The audit is written to:

- `reports/phase_reports/phase4s_first_controlled_batch_audit.json`
- `docs/phase_reports/phase4s_first_controlled_batch_audit.md`

## Explicit Non-goals

Phase4-S does not implement:

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

Phase4-S is complete when:

- readiness gate is checked.
- exactly the configured max two chunks or fewer are executed.
- tmp-to-final atomic move is confirmed.
- chunk manifests and run manifest are written.
- schema validation and leakage audit are OK.
- audit and pytest pass.
