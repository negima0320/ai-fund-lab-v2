# Phase4-V Post-expansion Readiness Audit

## Purpose

Phase4-V audits the artifacts produced after the Phase4-U controlled batch expansion.

The goal is to decide whether the system can move to a larger controlled batch or a full controlled feature generation gate, without implementing labels, datasets, model training, inference, backtest, trading, broker API calls, order placement, or Portfolio auto-update.

## Read Inputs

- `docs/phase_reports/phase4u_controlled_batch_expansion.md`
- `docs/phase_reports/phase4u_controlled_batch_expansion_audit.md`
- `reports/phase_reports/phase4u_controlled_batch_expansion_audit.json`
- `reports/candidate_ai/full_range/phase4u_controlled_batch_expansion_summary.json`
- `src/ai_fund_lab_v2/candidate_ai/full_range.py`
- `scripts/build_candidate_features_controlled_batch_expansion.py`
- `scripts/audit_phase4u_controlled_batch_expansion.py`
- `docs/phase_reports/phase4t_post_batch_integrity.md`
- `reports/candidate_ai/full_range/phase4t_post_batch_integrity_summary.json`

## Audit Scope

Phase4-V checks:

- runtime capacity
- chunk manifest integrity
- run manifest integrity
- resume/restart readiness
- simple feature output statistics
- schema validation re-audit
- leakage audit re-audit
- `data_source_type`, `feature_version`, and `schema_version` consistency
- readiness for the next controlled step

## Readiness Status

The audit emits one of:

- `READY_FOR_LARGER_CONTROLLED_BATCH`
- `READY_FOR_FULL_CONTROLLED_FEATURE_GENERATION`
- `BLOCKED_BY_ARTIFACT_INTEGRITY`
- `BLOCKED_BY_SCHEMA`
- `BLOCKED_BY_LEAKAGE`
- `BLOCKED_BY_STORAGE`
- `BLOCKED_BY_RESUME_STATE`
- `SKIPPED_NO_OUTPUT`

For the current mock four-chunk runtime, if all checks pass the expected status is:

- `READY_FOR_FULL_CONTROLLED_FEATURE_GENERATION`

This readiness is explicitly for `data_source_type=mock`. Real J-Quants runtime data must be audited separately.

## Output

The readiness summary is written to:

- `reports/candidate_ai/full_range/phase4v_post_expansion_readiness_summary.json`

The audit report is written to:

- `reports/phase_reports/phase4v_post_expansion_readiness_audit.json`
- `docs/phase_reports/phase4v_post_expansion_readiness_audit.md`

## Explicit Non-goals

Phase4-V does not implement:

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

Phase4-V is complete when:

- Phase4-U summary is available.
- post-expansion artifacts are integrity checked.
- feature output simple stats are produced.
- schema and leakage are re-audited.
- storage guard is checked.
- resume readiness is checked.
- readiness status is produced.
- audit and pytest pass.
