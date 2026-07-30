# Phase23-A: Submit HALT, Corporate Event Propagation, Position Management Wiring Root Cause Audit

Generated: 2026-07-28T00:00:00+09:00

## Final Judgment

`PHASE23_A_ROOT_CAUSE_AUDIT_COMPLETE_REPAIRS_REQUIRED`

10BD rerun status: `NOT_READY_FOR_10BD_RERUN`

Phase23-A is complete as a root-cause audit only. No production code repair, Runtime Switch, broker write, demo/production submit, active consumer promotion, or long Runtime Test rerun was performed.

## Audited Runtime Evidence

- Phase22 5BD foundation run: `runtime-test-historical-smoke-20260728T042516796181Z`
- Phase23 10BD HALT run: `runtime-test-historical-smoke-20260728T044704027154Z`
- 10BD HALT point: `2026-06-19:submit`
- Daily submit result: exit `20`, `REVIEW_REQUIRED`, reason `historical_safety_temporal_authority_missing`
- Runtime Test aggregate result: exit `30`, status `HALT`

## Root Cause Summary

| ID | Domain | Status | Priority | Finding |
|---|---|---:|---:|---|
| `P23A-HALT-001` | submit_halt | CONFIRMED | P0 | MISSING_HISTORICAL_SAFETY_AUTHORITY_ON_ACTIVE_PENDING |
| `P23A-HALT-002` | runtime_test_halt_mapping | CONFIRMED | P1 | EXPECTED_EXIT_CODE_TRANSLATION |
| `P23A-HALT-003` | halt_observability | CONFIRMED | P0 | SUMMARY_AGGREGATION_BUG |
| `P23A-HALT-004` | halt_state_persistence | CONFIRMED | P0 | STALE_STATE_READ_BEFORE_WRITE |
| `P23A-CE-001` | corporate_event | CONFIRMED | P1 | SOURCE_COVERAGE_GAP_AND_REVIEW_PROPAGATION |
| `P23A-PM-001` | position_management | CONFIRMED | P0 | POSITION_LIFECYCLE_INPUT_WIRING_GAP |
| `P23A-CAND-001` | candidate_zero_row | CONFIRMED | P1 | CANDIDATE_SOURCE_AVAILABLE_BUT_RUNTIME_CANDIDACY_UNUSABLE |
| `P23A-AG-001` | accepted_generation_binding | CONFIRMED_WITH_PIT_RISK | P1 | RESOLVED_BINDING_WITH_HISTORICAL_PIT_MISMATCH_RISK |
| `P23A-EMPTY-001` | initial_empty_portfolio | CONFIRMED_REGRESSION | P0 | EMPTY_STATE_AUTHORITY_REGRESSION |


## Key Findings

1. Submit HALT is rooted in an active `APPROVED` pending order plan for `2026-06-19` whose Data Readiness safety authority fields are incomplete. The previous day passed with complete historical safety authority, but the new active pending path reaches `historical_safety_temporal_authority_missing` and `pending_safety_evidence_missing`.
2. Runtime Test exit `30` is the expected runner-level HALT translation of a nonzero daily Runtime CLI exit `20`; the bug is not the translation itself but the missing/contradictory HALT observability.
3. HALT observability has two confirmed defects: run_state embeds `NOT_HALTED` because summary is computed before writing `halted_at`, and fresh summary leaves `root_reason` blank because `_runtime_halt_summary` ignores submit manifest top-level `reason` and Data Readiness review reasons.
4. Corporate Event remains `REVIEW_REQUIRED` because full source coverage is required and earnings/financial statements/corporate actions sources are missing or not implemented. This is explicit, not a silent PASS.
5. Position Management has a Strategy wiring gap: Runtime current portfolio is visible as source evidence, but PM positions are generated only from existing PM decisions, so current holdings are not converted into PM decision rows.
6. Candidate/opportunity artifacts are present and date-selected without latest fallback, but downstream candidate eligibility is still unusable (`SOURCE_UNAVAILABLE` attribution and unresolved planning). This points to candidate membership/eligibility adaptation rather than source discovery.
7. Accepted Generation binding is resolved and hashed, but using a generation accepted/effective on `2026-07-20` for `2026-07-06..10` replay dates remains a PIT authority risk.
8. The targeted empty portfolio authority test currently fails: expected `READY`, observed `REVIEW_REQUIRED`.

## Repair Gate

Do not run another 10BD/20BD/1y/3y Runtime Test until the P0 items are repaired and a controlled short validation confirms:

- submit HALT root_reason propagation is trustworthy;
- historical pending safety authority is materialized consistently;
- initial empty portfolio authority returns the expected READY/READY_EMPTY contract;
- Strategy PM receives Runtime-owned current holdings as actionable PM rows.

## Detail Artifacts

All machine-readable audit outputs are under `reports/phase23_a_submit_halt_and_strategy_runtime_root_cause_audit`. The summary JSON is `reports/phase_reports/phase23_a_submit_halt_and_strategy_runtime_root_cause_audit.json`.
