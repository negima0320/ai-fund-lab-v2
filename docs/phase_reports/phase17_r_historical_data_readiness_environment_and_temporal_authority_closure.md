# Phase17-R Historical Data Readiness Environment and Temporal Authority Closure

## Summary

Phase17-R investigated and closed the 5BD clean rerun failure at Data Readiness.

Failed run:

- `runtime-test-historical-smoke-20260714T211613683513Z`
- `2026-07-06 market_refresh`: PASS
- `2026-07-06 data_readiness`: HALT, exit 30

Direct HALT reason:

- `runtime_acceptance_requires_demo_mode`

Final judgement:

```text
PHASE17_R_HISTORICAL_DATA_READINESS_ACCEPTED
```

Recommended next prefix:

```text
Phase17-S
```

## Root Cause

The failure was a Data Readiness bug, not a Historical Environment Composition failure.

The runtime command had already entered the correct historical composition:

- `mode=historical`
- `broker_environment=historical_simulated`
- `notification-mode=payload-only`
- `runtime_execution_path=regular_runtime`
- external effects disabled

However Data Readiness still had its own demo-only environment acceptance rule and converted the historical run into:

- `acceptance_scope=demo_acceptance_only`
- `runtime_environment.status=HALT`
- `reason=runtime_acceptance_requires_demo_mode`

Data Readiness also evaluated the wrong temporal evidence:

- Feature readiness came from `.runtime/operations/feature_consumer_readiness/2026-07-14.json`
- Feature artifacts came from `.runtime/operations/feature_artifacts/2026-07-14/`
- Current actual as-of came from a latest real-time timestamp
- Safety came from `.runtime/runtime_state/safety/latest_safety_decision.json`

## Closure

Implemented closure in the normal Runtime v2 mainline only. No alternate historical runtime, historical-only Current, Ledger, Pending, Feature Producer, Submit, or Execution path was added.

Changes:

- Data Readiness now resolves feature authority from `.runtime/operations/feature_date_contract/<business_date>.json`.
- Historical Data Readiness accepts `historical_replay` only when the broker environment is `historical_simulated` and external effects are disabled.
- Historical Current temporal authority is limited to confirmed empty initial Current state.
- Historical Safety temporal authority no longer reuses latest safety evidence; neutral no-event safety is allowed only for empty Current, empty or consumed Pending, and no external effects.
- Runtime Test runner now passes selected Feature Date Contract output to `data_readiness` jobs.
- Runtime-test Data Readiness evidence can be isolated under `reports/runtime_tests/runs/<run_id>/daily/<business_date>/data_readiness/`.

## Evidence

Key evidence files:

- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/read_audit.json`
- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/failure_classification.json`
- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/data_readiness_call_graph.json`
- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/environment_scope_trace.json`
- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/feature_resolution_after.json`
- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/current_temporal_authority_review.json`
- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/safety_temporal_authority_review.json`
- `reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure/five_bd_entry_gate_recheck.json`

## Acceptance Gates

All requested gates passed:

- `FAILURE_ROOT_CAUSE_CONFIRMED`
- `HISTORICAL_ENVIRONMENT_COMPOSITION_PASS`
- `NO_DEMO_IDENTITY_SPOOFING`
- `ACCEPTANCE_SCOPE_HISTORICAL_REPLAY_PASS`
- `NO_RUNTIME_ACCEPTANCE_REQUIRES_DEMO_MODE`
- `FEATURE_DATE_CONTRACT_AUTHORITY_PASS`
- `FEATURE_READINESS_2026_07_06_PASS`
- `FEATURE_READINESS_2026_07_08_CARRYOVER_PASS`
- `FEATURE_READINESS_2026_07_09_PASS`
- `NO_LATEST_FEATURE_FALLBACK`
- `CURRENT_TEMPORAL_AUTHORITY_PASS`
- `NO_FUTURE_CURRENT_STATE`
- `SAFETY_TEMPORAL_AUTHORITY_PASS`
- `NO_LATEST_SAFETY_REUSE`
- `HISTORICAL_JOB_SEQUENCE_PASS`
- `DATA_READINESS_EVIDENCE_ISOLATED`
- `DEMO_DATA_READINESS_UNCHANGED`
- `PRODUCTION_DATA_READINESS_UNCHANGED`
- `SUBMIT_UNCHANGED`
- `EXECUTION_UNCHANGED`
- `NO_TRADING_STATE_MUTATION`
- `NO_5BD_RUNTIME_EXECUTION`

## Verification

Executed:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_r_pycache python3 -m pytest -q tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_r_pycache python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py
```

Results:

- `10 passed`
- `11 passed`

## Operations Not Performed

The following were not performed:

- 5BD Runtime execution
- Failed run resume
- Trading State reset
- Restore or rollback
- Current, Ledger, Pending, or Runtime State manual mutation
- Feature generation or promotion
- Canonical update
- J-Quants fetch
- Submit
- Execution
- Demo or Production operation

