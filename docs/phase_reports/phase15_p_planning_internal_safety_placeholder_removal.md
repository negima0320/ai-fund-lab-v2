# Phase15-P Planning Internal SafetySignal Placeholder Removal

## Status

`PHASE15P_PLANNING_INTERNAL_SAFETY_PLACEHOLDER_REMOVAL_COMPLETE`

Phase15-P removes the Phase15-O Core blocker:

```text
Planning Internal Safety Placeholder
```

Morning Planning and SELL Planning no longer generate internal `SafetySignal` placeholder allow records. Planning now receives Runtime Safety / Operation Guard evidence through `RuntimeSafetyContext`, and OrderPlan / Pending / Approval retain the Safety context needed for later Submit-side consistency comparison.

## Implementation Summary

Implemented:

- Removed `SafetySignal` from Runtime v2 Planning models.
- Removed `safety_signals` from `PlanningInput`.
- Added `RuntimeSafetyContext` to `PlanningInput`.
- Changed Planner to use `runtime_safety` only.
- Removed Morning Planning internal `_safety(...)` placeholder generation.
- Removed SELL Planning internal `_safety(...)` placeholder generation.
- Added OrderPlan safety evidence:
  - `safety_decision_id`
  - `safety_policy_version`
  - `safety_source`
  - `safety_decision`
  - `safety_reason`
- Added OrderPlan item safety evidence with the same fields.
- Added Pending plan / item Safety context retention.
- Added Approval request / artifact / Pending approval link Safety context retention.
- Added Submit item evidence fields for Pending-origin Safety context:
  - `pending_safety_decision_id`
  - `pending_safety_policy_version`
  - `pending_safety_source`
  - `pending_safety_decision`
  - `pending_safety_reason`

Submit comparison between Planning Safety context and Submit Runtime Safety is intentionally left as future work. Phase15-P creates the evidence foundation.

## Evidence

Source scan result:

```text
No implementation-side SafetySignal / safety_signals / placeholder allow references remain under src/ai_fund_lab_v2/runtime_v2.
```

Runtime Safety source remains:

```text
.runtime/runtime_state/safety/latest_safety_decision.json
```

Planning receives Safety through:

```text
PlanningInput.runtime_safety: RuntimeSafetyContext
```

## Changed Files

Code:

- `src/ai_fund_lab_v2/runtime_v2/planning/models.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/order_plan_builder.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/approval/models.py`
- `src/ai_fund_lab_v2/runtime_v2/approval/policy.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/simulation/harness.py`

Tests:

- `tests/runtime_v2/test_phase15p_planning_internal_safety_placeholder_removal.py`
- `tests/runtime_v2/planning_fixtures.py`
- `tests/runtime_v2/test_phase13_s_planning_models.py`
- `tests/runtime_v2/test_phase13_s_order_plan_builder.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`

Reports:

- `docs/phase_reports/phase15_p_planning_internal_safety_placeholder_removal.md`
- `reports/phase_reports/phase15_p_planning_internal_safety_placeholder_removal.json`

## Regression Coverage

Added:

- Planning source has no internal `SafetySignal` placeholder allow.
- `PlanningInput` has `runtime_safety` and no `safety_signals`.
- Planner carries Runtime Safety evidence into OrderPlan.
- Morning OrderPlan keeps Safety evidence.
- Pending plan and Pending items keep Safety context.
- Approval artifact and Pending approval link keep Safety context.

Retention verified:

- Phase15-H Policy Loader.
- Phase15-I Submit Guard.
- Phase15-K Morning Policy.
- Phase15-L Policy Hash.
- Phase15-M SELL Broker Evidence.
- Phase15-N Safety Runtime.
- Phase15-O Runtime Core Flow regression set.

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15p_planning_internal_safety_placeholder_removal.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase13_p_pending_models.py tests/runtime_v2/test_phase13_p_pending_consume.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase13_o_ledger_models.py tests/runtime_v2/test_phase13_s_planning_models.py tests/runtime_v2/test_phase13_s_order_plan_builder.py
```

Result:

```text
92 passed
```

Additional verification:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile ...
```

Result:

```text
PASS
```

## Phase15-O Gap Closure

Phase15-O gap:

```text
Planning Internal Safety Placeholder
```

Resolution:

```text
CLOSED
```

Planning no longer creates pseudo Safety allow records. Runtime Safety / Operation Guard evidence is now the only Safety input used by Planning and SELL Planning.

## Still Not Full Runtime PASS

This phase closes the Core blocker found in Phase15-O, but it does not perform:

- Broker Write
- Demo order
- Production order
- Notification real send
- launchd operation
- Demo Operation rehearsal
- Report / Notification semantic propagation
- Submit-time comparison enforcement between Planning Safety and Submit Safety

## Prohibited Actions Check

Not performed:

- Broker Write
- Demo order
- Production order
- Notification real send
- launchd / plist modification
- Current direct edit
- Runtime bypass creation

## Final Judgment

```text
PHASE15P_PLANNING_INTERNAL_SAFETY_PLACEHOLDER_REMOVAL_COMPLETE
```
