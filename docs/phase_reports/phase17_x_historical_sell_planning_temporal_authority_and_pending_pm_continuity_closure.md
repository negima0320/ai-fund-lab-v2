# Phase17-X Historical SELL Planning Temporal Authority and Pending/PM Continuity Closure

## Verdict

`PHASE17_X_HISTORICAL_SELL_PLANNING_TEMPORAL_AUTHORITY_ACCEPTED`

Historical SELL planning can now use the same formal authority chain as Demo/Production while remaining fail-closed for external effects. The frozen run
`runtime-test-historical-smoke-20260714T231426061528Z` was not resumed or mutated.

## Required Evidence Reviewed

- `docs/phase_reports/phase17_w_historical_morning_capability_guard_closure.md`
- `docs/phase_reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure.md`
- `docs/phase_reports/phase17_s_historical_morning_json_serialization_and_evidence_closure.md`
- `docs/phase_reports/phase17_v_opportunity_market_sector_runtime_authority_closure.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/operational_data_architecture.md`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/storage/json_safe.py`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `scripts/runtime_test.py`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260714T231426061528Z/daily/2026-07-06/data_readiness/data_readiness.json`
- `.runtime/runtime_state/run_manifest/2026-07-06/runtime-v2-sell_planning-2026-07-06-20260714T231444.352849+0000.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/persistent_ledger/state.json`
- `.runtime/runtime_state/current_state.json`
- `.runtime/runtime_state/safety/latest_safety_decision.json`

Requested but not present in the repository under the provided paths:

- `docs/02_architecture/runtime_test_contract.md`
- `docs/02_architecture/runtime_artifact_registry_contract.md`
- `docs/02_architecture/runtime_feature_contract.md`
- `docs/02_architecture/runtime_historical_contract.md`
- `docs/02_architecture/runtime_data_readiness_contract.md`

## Frozen Run Classification

The frozen SELL planning run stopped at Data Readiness with:

- `historical_safety_temporal_authority_missing`
- `pending_safety_evidence_missing`
- `pm_input_stale_artifacts`

Classification:

- Safety: not a simple string path mismatch. The latest safety pointer referenced a different business date (`2026-07-10`) and a demo/high-risk review decision, so Historical replay lacked a valid run-scoped safety identity for `2026-07-06`.
- Pending: not an artifact hash mismatch. The pending plan carried Historical neutral item-level safety fields, but no run/profile/evidence-root authority metadata, so Data Readiness could not prove that the empty `safety_decision_id` was intentional replay authority.
- PM Current: primarily a temporal authority mismatch. Ledger `as_of` was wall-clock `2026-07-14T23:14:10...`, while the authoritative runtime current state was business-date scoped to `2026-07-06`.

## Implemented Closure

- Data Readiness now accepts Historical pending safety only when `safety_context` matches all of:
  `historical_initial_no_external_effect`, `ALLOW`, `historical_replay_neutral_safety_v1`,
  `data_readiness_historical_temporal_authority`, business date, runtime-test run id, profile id, and evidence root.
- Morning pending generation now writes that run-scoped Historical safety authority into the pending `safety_context`.
- Safety readiness can reuse that verified pending authority when the latest safety pointer is stale for Historical replay.
- PM input validation now uses authoritative runtime current state for Historical empty Current and normalizes `pm_current_as_of`, `position_state_as_of`, and `valuation_as_of` to the business date only under that contract.
- SELL planning now has its own capability guard for Historical replay and remains fail-closed for broker write, submit, notification delivery, Tachibana demo/production writes, missing run id, missing profile id, and missing evidence root.
- CLI sell planning now preserves existing Morning BUY Pending when PM returns `NO_POSITION`; it no longer overwrites pending with a SELL no-signal pending in that path.
- CLI now writes run-scoped sell planning evidence under `daily/<business_date>/sell_planning/`.

## Validation

Passed:

- `python3 -m py_compile` for touched runtime modules and Phase17-X test.
- `python3 -m pytest -q tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py`

Observed unrelated/pre-existing broader-suite blockers:

- PM producer tests hit `artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`.
- Older Data Readiness tests still use pre-Phase17-V opportunity feature fixtures missing market/sector columns.

These are not Historical-only relaxations and were not resolved by mutating frozen evidence.
