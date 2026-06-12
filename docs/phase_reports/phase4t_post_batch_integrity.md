# Phase4-T Post-batch Integrity Audit

## Purpose

Phase4-T audits the artifacts produced by the Phase4-S first controlled batch.

The goal is to confirm that final outputs, chunk manifests, chunk audits, run manifest, and resume state are mutually consistent before expanding the controlled batch.

## Read Inputs

- `docs/phase_reports/phase4s_first_controlled_batch.md`
- `docs/phase_reports/phase4s_first_controlled_batch_audit.md`
- `reports/phase_reports/phase4s_first_controlled_batch_audit.json`
- `reports/candidate_ai/full_range/phase4s_first_controlled_batch_summary.json`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_first_controlled_batch.py`
- `scripts/audit_phase4s_first_controlled_batch.py`

## Integrity Checks

- final feature output exists.
- tmp output remains absent after atomic move.
- chunk manifest exists.
- chunk audit exists.
- run manifest exists.
- output row count matches chunk manifest row count.
- eligible/excluded counts match output rows.
- schema validation is `OK`.
- leakage audit is `OK`.
- run manifest completed/failed counts match SUCCESS/FAILED manifests.
- resume state treats SUCCESS chunks as skip candidates.
- duplicate outputs/manifests are absent.
- orphan outputs/manifests are absent.
- data source, feature version, and schema version are consistent.

## Integrity Status

The audit emits one of:

- `READY_FOR_CONTROLLED_BATCH_EXPANSION`
- `BLOCKED_BY_MISSING_OUTPUT`
- `BLOCKED_BY_MANIFEST_MISMATCH`
- `BLOCKED_BY_AUDIT_FAILURE`
- `BLOCKED_BY_RESUME_STATE`
- `BLOCKED_BY_ORPHAN_ARTIFACT`
- `SKIPPED_NO_BATCH_OUTPUT`

## READY Conditions

The status is READY only when:

- `checked_chunk_count > 0`
- `final_output_exists_count = checked_chunk_count`
- `tmp_leftover_count = 0`
- `chunk_manifest_count = checked_chunk_count`
- `chunk_audit_count = checked_chunk_count`
- row count matches.
- eligible/excluded count matches.
- schema and leakage audits are all OK.
- resume state can skip successful chunks.
- duplicate and orphan counts are zero.
- data source, feature version, and schema version are consistent.

## Output

The summary is written to:

- `reports/candidate_ai/full_range/phase4t_post_batch_integrity_summary.json`

The audit is written to:

- `reports/phase_reports/phase4t_post_batch_integrity_audit.json`
- `docs/phase_reports/phase4t_post_batch_integrity_audit.md`

## Explicit Non-goals

Phase4-T does not implement:

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

Phase4-T is complete when:

- integrity summary is generated.
- final output / manifest / audit / run manifest consistency is checked.
- resume SUCCESS skip readiness is confirmed.
- duplicate/orphan detection exists.
- audit and pytest pass.
