# Phase17-BA Submit Temporal Authority Contract Fix

## Verdict

`PHASE17_BA_SUBMIT_TEMPORAL_AUTHORITY_CONTRACT_ACCEPTED`

This is a code and test acceptance for the submit temporal authority contract only. It is not a Phase17 Historical 5BD smoke completion verdict.

## Frozen Evidence

Frozen run was read only:

- `runtime-test-historical-smoke-20260715T092642592380Z`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T092642592380Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T092642592380Z/daily/2026-07-07/data_readiness/data_readiness.json`
- `.runtime/persistent_ledger/state.json`
- `.runtime/pending_order_plan/pending_order_plan.json`

No `runtime_test.py run/resume/rollback/reset/backup/close` command was executed, and no Pending, Ledger, Current, broker, external delivery, J-Quants fetch, or AI retraining action was performed.

## Root Cause

Primary classification: Temporal Authority Bug.

Secondary classification: Producer/Consumer Contract Mismatch.

Day2 submit ran at `2026-07-07T08:45:00+09:00`. At that time the `2026-07-07` close did not exist, so the valid Current Valuation authority was the previous trading day close, `2026-07-06`.

The frozen Data Readiness evidence for submit had:

- `readiness_scope=submit`
- `valuation_as_of=2026-07-06`
- `source_market_date=2026-07-06`
- `current_valuation_expected_date=2026-07-07`
- `current_valuation_temporal_reason=current_valuation_not_business_date_close`
- `review_reasons=["current_valuation_not_ready"]`

Morning and sell planning already accepted `previous_trading_day_close_is_latest_available_at_morning_evaluation`; submit did not. The mismatch was in the shared Data Readiness Current Valuation temporal validator, where submit was not included in the morning/pre-close valuation scope.

## Contract Before

- Morning and sell planning: allowed same-day valuation or previous trading day close.
- Submit: required business-date close even before the close was available.
- Current valuation refresh and execution: required business-date close.
- `source_market_date` mismatch was not explicitly classified in the Current Valuation temporal authority evidence.

## Contract After

The Runtime common Current Valuation temporal authority now applies across Production, Demo, and Historical:

- Pre-close morning, sell planning, and submit allow same-day valuation if already refreshed, otherwise the previous trading day close.
- After `15:40:00` JST, same-day close is required.
- `current_valuation` and `execution` scopes continue to require business-date close.
- Future-dated valuation remains `HALT`.
- Missing valuation, missing previous trading date, stale valuation older than the previous trading day, and `source_market_date` mismatch remain fail-closed as `REVIEW_REQUIRED`.
- Evidence now includes evaluation time, close confirmation status, close confirmation cutoff, and source market date status.

This is not a Historical-only exception. The same validator is used by Data Readiness for Production, Demo, and Historical; environment differences remain outside the valuation temporal contract.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py`
- `docs/phase_reports/phase17_ba_submit_temporal_authority_contract_fix.md`
- `reports/phase17_ba_submit_temporal_authority_contract_fix/summary.json`
- `reports/phase_reports/phase17_ba_submit_temporal_authority_contract_fix.json`

## Tests

Passed:

- `python3 -m pytest -q tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py`
- `python3 -m pytest -q tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py`
- `PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.tmp_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/data_readiness.py tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py`

Additional regression run:

- `python3 -m pytest -q tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py`
- Result: 48 passed, 2 failed.
- Failure classification: legacy CLI fixture readiness gaps, not BA temporal authority. The generated manifests showed Current Valuation temporal status `READY`; failures were due to missing `broker_readonly_snapshot`, missing `market_evidence`, `pending_policy_hash_missing`, or `pending_slot_missing`.

## Production Impact

Production morning submit can now proceed when the latest valid Current Valuation is the previous trading day close and the submit evaluation time is before same-day close confirmation.

Production remains fail-closed for:

- future valuation
- stale valuation older than the previous trading day
- source market date mismatch
- missing valuation evidence
- missing previous trading date authority
- post-close submit with only previous trading day valuation
- current valuation refresh without business-date close

No Runtime Test identity, run ID, profile ID, Historical mode, or smoke-test profile is used as a trading permission condition.

## Historical And Demo Scope

Historical and Demo use the same Temporal Authority validator. Historical-specific behavior remains limited to external effects, simulation, and evidence environment composition. Demo-specific behavior remains limited to demo broker/external-action capabilities.

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
