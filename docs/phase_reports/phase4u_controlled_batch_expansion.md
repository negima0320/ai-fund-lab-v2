# Phase4-U Controlled Batch Expansion

## Purpose

Phase4-U expands the controlled Candidate feature batch after the Phase4-T post-batch integrity gate is READY.

This phase remains a guarded dry-run style execution step. It does not generalize into all-chunk or full-period feature generation.

## Read Inputs

- `docs/phase_reports/phase4t_post_batch_integrity.md`
- `docs/phase_reports/phase4t_post_batch_integrity_audit.md`
- `reports/phase_reports/phase4t_post_batch_integrity_audit.json`
- `reports/candidate_ai/full_range/phase4t_post_batch_integrity_summary.json`
- `docs/phase_reports/phase4s_first_controlled_batch.md`
- `reports/candidate_ai/full_range/phase4s_first_controlled_batch_summary.json`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_first_controlled_batch.py`
- `scripts/audit_phase4t_post_batch_integrity.py`

## Integrity Gate

Phase4-U requires the Phase4-T gate to be READY:

- `integrity_status = READY_FOR_CONTROLLED_BATCH_EXPANSION`
- `tmp_leftover_count = 0`
- `schema_validation_all_ok = true`
- `leakage_audit_all_ok = true`
- `resume_success_skip_ready = true`
- `duplicate_output_count = 0`
- `orphan_output_count = 0`

If the gate is not READY, expansion is `BLOCKED`.

## Controlled Expansion Policy

- `max_chunks_to_execute = 4`
- `stop_on_first_failure = true`
- `max_failed_chunks_allowed = 0`
- SUCCESS chunks are skipped.
- FAILED chunks are rerun candidates.
- Missing chunks are execution candidates.
- Partial tmp output is reported as a warning.
- Manifest inconsistency blocks execution.
- Schema validation and leakage audit must be `OK`.

The current mock runtime has four chunks, so this phase may complete the small mock run. That is still a controlled expansion and not full-range production.

## Output

The controlled expansion summary is written to:

- `reports/candidate_ai/full_range/phase4u_controlled_batch_expansion_summary.json`

The audit is written to:

- `reports/phase_reports/phase4u_controlled_batch_expansion_audit.json`
- `docs/phase_reports/phase4u_controlled_batch_expansion_audit.md`

## Post-expansion Integrity

Phase4-U records a simple post-expansion integrity section:

- final output count
- chunk manifest count
- chunk audit count
- run manifest completed count
- tmp leftover count
- duplicate output count
- duplicate manifest count
- orphan output count
- orphan manifest count

## Explicit Non-goals

Phase4-U does not implement:

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

Phase4-U is complete when:

- Phase4-T integrity gate is checked.
- at most four chunks are controlled by the expansion runner.
- existing SUCCESS chunks are skipped.
- missing chunks are executed.
- no failure is tolerated.
- schema validation and leakage audit remain OK.
- post-expansion integrity is reported.
- audit and pytest pass.
