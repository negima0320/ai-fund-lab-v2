# Phase15-N Safety / Operation Guard Runtime Connection

## Status

`PHASE15N_SAFETY_OPERATION_GUARD_RUNTIME_CONNECTION_COMPLETE`

Phase15-N connects Safety / Operation Guard evidence to Runtime v2 normal Planning and Submit paths. Runtime no longer treats missing Safety evidence as an implicit allow. Missing, invalid, review-required, blocked, or halt Safety decisions now stop the relevant Runtime path before order submission.

## Objective

Connect Safety / Operation Guard to:

```text
Morning Planning
SELL Planning
Submit Guard
Runtime Manifest
Regression
```

The purpose is to ensure Runtime v2 can support safe automated trading by requiring explicit Safety evidence before BUY / SELL planning and submit decisions.

## Safety Decision Contract

Runtime reads Safety evidence from:

```text
.runtime/runtime_state/safety/latest_safety_decision.json
```

Required contract fields:

```text
safety_decision_id
safety_policy_version
safety_source
business_date
runtime_mode
decision
reason
review_required
block_buy
block_sell
block_submit
halt_runtime
emergency_stop
generated_at
expires_at
```

Supported decisions:

```text
ALLOW
REVIEW_REQUIRED
BLOCKED
HALT
```

Missing or invalid Safety evidence is treated as `REVIEW_REQUIRED`. No placeholder allow is generated.

## Implementation Summary

Implemented:

- Added Runtime Safety decision loader and action guard.
- Connected Safety evidence to CLI normal path.
- Connected Safety evidence to Morning Planning.
- Connected Safety evidence to SELL Planning.
- Connected Safety evidence to Submit Guard.
- Missing Safety blocks `morning`, `sell_planning`, and `submit`.
- `HALT` / `emergency_stop` stops Runtime flow with `HALT`.
- BUY and SELL Safety controls are separated.
- Submit item evidence now includes Safety policy and decision fields.
- Runtime manifest includes top-level Safety evidence and a `safety_operation_guard` stage.
- Existing normal-path regression fixtures now write explicit Safety ALLOW artifacts where they expect PASS.

## BUY / SELL Separation

BUY is treated as new risk exposure. SELL is treated as risk reduction / liquidation.

Behavior:

- `block_buy=true` stops BUY planning and BUY submit.
- `block_buy=true` does not stop SELL liquidation.
- `block_sell=true` stops SELL planning and SELL submit.
- `block_submit=true` stops both BUY and SELL submit.
- `halt_runtime=true`, `emergency_stop=true`, or `decision=HALT` stops Runtime flow.

## Submit Guard Evidence

Submit Guard item evidence now includes:

```text
safety_decision_id
safety_policy_version
safety_source
safety_decision
safety_reason
safety_block_buy
safety_block_sell
safety_block_submit
safety_halt_runtime
safety_emergency_stop
safety_guard_status
```

When Safety blocks an item:

```text
violated_policy=safety_operation_guard
manual_review_required=true
demo_submit_executed=false
submitted_count=0
```

Broker preflight / submit is not called for Safety-blocked items.

## Planning Evidence

Morning Planning and SELL Planning results now carry:

```text
safety_decision_id
safety_policy_version
safety_source
safety_decision
safety_reason
safety_status
safety_block_buy
safety_block_sell
safety_block_submit
safety_halt_runtime
```

This makes Review Required / Halt reasons visible in CLI stage details and Runtime manifest evidence.

## Changed Files

Code:

- `src/ai_fund_lab_v2/runtime_v2/safety_decision.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

Tests:

- `tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py`
- `tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py`
- `tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py`
- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`
- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`
- `tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`
- `tests/runtime_v2/test_phase15h_capital_deployment_policy.py`

Reports:

- `docs/phase_reports/phase15_n_safety_operation_guard_runtime_connection.md`
- `reports/phase_reports/phase15_n_safety_operation_guard_runtime_connection.json`

## Regression Coverage

Covered:

- Missing Safety blocks Morning Planning.
- Missing Safety blocks Submit before Broker call.
- ALLOW permits normal path.
- `block_buy=true` stops BUY but permits SELL liquidation.
- `block_sell=true` stops SELL Planning and SELL Submit.
- `HALT` stops Submit and produces Runtime halt status.
- CLI manifest retains Safety evidence.
- Existing Phase15-H/I/K/L/M and Phase14 Runtime normal-path tests remain green with explicit Safety evidence.

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase13_p_pending_models.py tests/runtime_v2/test_phase13_p_pending_consume.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py
```

Result:

```text
72 passed
```

## Still Not Fixed

Intentionally left for later Phase15 subphases:

- Report / Notification policy reason propagation.
- Operator Review apply path.
- Candidate / Opportunity AI direct execution contract.
- Position Management AI -> SELL Planning formal connection.
- Production broker capability.
- real notification send.
- launchd automated operation readiness.

## Prohibited Actions Check

Not performed:

- Broker Write
- Demo order
- Production order
- Notification real send
- launchd / plist modification
- Current direct edit
- Runtime bypass creation
- fake adapter Full Runtime PASS declaration
- Report / Notification propagation
- Operator Review apply path

## Final Judgment

```text
PHASE15N_SAFETY_OPERATION_GUARD_RUNTIME_CONNECTION_COMPLETE
```
