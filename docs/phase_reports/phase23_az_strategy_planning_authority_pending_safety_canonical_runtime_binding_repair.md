# Phase23-AZ Strategy Planning Authority Pending Safety Canonical Runtime Binding Repair

## Primary Judgment

`PHASE23_AZ_CANONICAL_PENDING_SAFETY_RUNTIME_BINDING_SHORT_VALIDATION_PASS`

## Secondary Judgment

- `CANONICAL_STRATEGY_AUTHORITY_PATH_BOUND = YES`
- `SAFETY_PAYLOAD_REACHES_PENDING_PRODUCER = YES`
- `PENDING_PROMOTION_PRESERVES_SAFETY_AUTHORITY = YES`
- `PENDING_SERIALIZATION_PRESERVES_SAFETY_AUTHORITY = YES`
- `DATA_READINESS_ACTIVE_PENDING_READY = YES`
- `NEGATIVE_FAIL_CLOSED_PRESERVED = YES`
- `PRODUCTION_DEMO_CONTRACT_PRESERVED = YES`
- `ISOLATED_AND_RUNTIME_PATH_EQUIVALENT = YES_FOR_BINDING_CONTRACT`
- `READY_FOR_1BD_RUNTIME_RERUN = YES`

## Root Cause

Phase23-AY confirmed that AX helper existed but the actual canonical runtime path `runtime_v2.planning.strategy_authority.activate_strategy_planning_authority` generated approved pending without `safety_context`, `safety_decision_id`, or `safety_policy_version`. The safety payload was lost before or at the Strategy Planning Authority pending producer boundary, not during Data Readiness consumption.

## Repair Summary

`activate_strategy_planning_authority` now accepts explicit `safety_authority_payload`. `run_daily_operation --job morning` passes a payload built only from the already resolved effective runtime safety decision, Data Readiness historical safety authority, and runtime-test identity.

Historical `NEUTRAL` is materialized through the AX helper `materialize_historical_pending_safety_context`. `ALLOW` remains accepted as legacy-compatible input, but new historical materialization records `NEUTRAL`.

The pending producer now writes safety authority metadata to:

- top-level `PendingOrderPlan.safety_context`
- top-level `safety_decision_id` / `safety_policy_version`
- existing and extended item-level safety fields
- serialized current slot JSON

## Required Questions

AZ-RQ1: `activate_strategy_planning_authority` receives `safety_authority_payload`, explicitly supplied by `run_daily_operation` from effective safety decision and Data Readiness authority.

AZ-RQ2: The payload was lost before pending promotion in the Strategy Planning Authority producer. Promotion/serialization can preserve it once supplied.

AZ-RQ3: Canonical consumer authority is top-level `safety_context`; item-level fields preserve lineage for per-order traceability.

AZ-RQ4: Morning and Sell can share the same AX helper. AZ binds Morning Strategy Planning Authority; sell-side helpers already use the same materialization concept.

AZ-RQ5: Production/Demo behavior is preserved. Demo safety payload is not rewritten to `NEUTRAL`; it remains `ALLOW` in regression.

## Modified Files

- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`

## Short Validation

- py_compile: PASS
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -k phase23_az`: 3 passed
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`: 8 passed
- `tests/runtime_v2/test_phase13_p_pending_promotion.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py -k "safety_authority or pending_safety or strategy_authority"`: 6 passed
- One exploratory `-k` command selected zero tests; no failures were observed.

## Evidence

Canonical integration reproduction used 9 active pending items.

Evidence directory: `reports/phase23_az_strategy_planning_authority_pending_safety_canonical_runtime_binding_repair/`

Files: `canonical_call_path_before_after.json, canonical_runtime_integration_reproduction.json, data_readiness_acceptance.json, existing_run_hash_preservation.json, modified_files.json, negative_fail_closed_cases.json, pending_promotion_trace.json, pending_serialization_trace.json, previous_blocker_regression_check.json, production_demo_regression.json, safety_payload_input_trace.json, test_results.json`

## Existing Run Preservation

Existing run artifacts were not modified. Hash preservation: `True`.

## Runtime Rerun

No fresh-run, 1BD, 10BD, resume, Broker Write, Runtime Switch, or J-Quants fetch was performed. Operator may run 1BD after review.
