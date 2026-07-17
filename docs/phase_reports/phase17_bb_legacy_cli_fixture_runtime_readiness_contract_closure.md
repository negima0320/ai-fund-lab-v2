# Phase17-BB Legacy CLI Fixture and Runtime Readiness Contract Closure

## Verdict

`PHASE17_BB_LEGACY_CLI_FIXTURE_RUNTIME_READINESS_CONTRACT_ACCEPTED`

This is a closure for the two legacy CLI fixture failures left after Phase17-BA. It is not a Historical 5BD smoke completion verdict.

## Scope

Frozen run remained read only:

- `runtime-test-historical-smoke-20260715T092642592380Z`

No `runtime_test.py run/resume/rollback/reset/backup/close` command was executed. No Pending, Ledger, Current, broker write, external delivery, J-Quants fetch, or AI retraining action was performed.

## Initial Failure Reproduction

Command:

`python3 -m pytest -q -vv tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py`

Initial result:

- `48 passed`
- `2 failed`

Failed tests:

- `test_phase14e17_cli_submit_job_records_submit_pipeline_stage`
- `test_phase15i_cli_manifest_contains_submit_guard_policy_and_item_evidence`

## Root Cause Classification

### `test_phase14e17_cli_submit_job_records_submit_pipeline_stage`

Classification: A. fixture only was not following the current Runtime Contract.

The fixture had an active approved pending slot but did not provide the full current Submit readiness authorities:

- `market_evidence_missing`
- `broker_readonly_snapshot_missing`
- `pending_policy_hash_missing`
- after the first fixture repair: `pending_safety_evidence_missing`

Production impact: in real Production, these must remain fail-closed before Submit.

Demo impact: Demo submit fixtures must still provide formal market, broker readonly, pending policy, and pending safety authorities.

Historical impact: Historical uses historical simulated authorities and must not rely on real broker state.

### `test_phase15i_cli_manifest_contains_submit_guard_policy_and_item_evidence`

Classification: A. fixture only was not following the current Runtime Contract.

The CLI fixture expected Submit guard manifest assertions but had no pending slot and lacked the formal pre-submit authorities:

- `pending_slot_missing`
- `market_evidence_missing`
- `broker_readonly_snapshot_missing`
- after pending slot repair: `pending_safety_evidence_missing`

Production impact: active pending without safety identity must remain fail-closed.

Demo impact: Demo guard fixture now creates a formal approved pending slot and readiness evidence before expecting Submit stage execution.

Historical impact: no Historical fallback was added to Demo/Production.

## Secondary Fixture Contract Cleanup

Additional semantic regression found older Phase15AS fixture drift:

- Opportunity feature fixture did not satisfy the current Opportunity consumer schema.
- The canonical model path assertion compared old default constants instead of the current registry-resolved accepted artifact paths.

Classification: A. fixture only was not following the current Runtime Contract.

The fixture now uses `CANDIDATE_REQUIRED_COLUMNS`, `OPPORTUNITY_REQUIRED_COLUMNS`, and `resolve_buy_ai_model_paths()` to match current Runtime authority.

## Changes

Changed files:

- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`
- `tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py`
- `tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py`
- `docs/phase_reports/phase17_bb_legacy_cli_fixture_runtime_readiness_contract_closure.md`
- `reports/phase17_bb_legacy_cli_fixture_runtime_readiness_contract_closure/summary.json`
- `reports/phase_reports/phase17_bb_legacy_cli_fixture_runtime_readiness_contract_closure.json`

Runtime production code was not changed for BB. The fail-closed readiness checks were preserved.

## Contract Confirmation

Confirmed current Runtime contract:

- terminal EMPTY pending slot exists: READY
- pending slot missing: REVIEW_REQUIRED
- active pending with missing policy hash: REVIEW_REQUIRED
- active pending with missing safety evidence: REVIEW_REQUIRED
- Production/Demo submit requires broker readonly snapshot and market evidence.
- Historical simulated environment must not require real broker write or real broker state as a trading permission.
- market_refresh omission remains fail-closed as `market_evidence_missing`.

## Test Results

Passed:

- `python3 -m pytest -q tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py::test_phase14e17_cli_submit_job_records_submit_pipeline_stage tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py::test_phase15i_cli_manifest_contains_submit_guard_policy_and_item_evidence`
  - `2 passed`
- `python3 -m pytest -q -vv tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py`
  - `50 passed`
- `python3 -m pytest -q tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py`
  - `7 passed`
- `python3 -m pytest -q tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py`
  - `19 passed`
- Combined regression:
  - `76 passed`
- `py_compile`
  - PASS

## Frozen Hashes

- `run_state.json`: `f34453ed80d0958d2d1bc6b7c6adc13faa93621726a623c73f536e4fab4d9014`
- Day2 submit Data Readiness evidence: `2ac8f2114bcc9f7cf6349c9095146025436ec20636b0918d782fcd4e7f135246`
- `.runtime/persistent_ledger/state.json`: `6ff00996e2b78be4efe7d90b339a36c4102d6a2d055db32abdc258e6bc777481`
- `.runtime/pending_order_plan/pending_order_plan.json`: `e92aa0a544b30b8bf1f9228ace7278ba52b7baac9f546407bb9578c26a987355`

## Next Operator Sequence

1. Read-only confirm clean baseline candidate.
2. If required, get explicit user approval before rollback or reset.
3. Confirm Current, Pending, Ledger, and Runtime State.
4. Create a new plan.
5. Confirm `baseline_compatibility_status=PASS`.
6. Start a new 5BD Historical Smoke with a new Run ID.
