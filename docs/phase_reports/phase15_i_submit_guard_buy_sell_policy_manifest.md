# Phase15-I Submit Guard BUY/SELL Separation + Active Policy Manifest

## Status

`PHASE15I_SUBMIT_GUARD_BUY_SELL_POLICY_MANIFEST_COMPLETE`

Phase15-I updated Submit Guard so Submit no longer uses hidden `max_order_amount=100000` or a side-neutral notional cap in the regular Runtime path.

Submit now requires an explicit Capital Deployment Policy, separates BUY and SELL guard evidence, and emits active policy evidence at run-level and item-level.

## Implementation Summary

Implemented:

- Removed hidden Submit pipeline default:
  - `max_order_amount=100_000.0`
- Removed side-neutral notional cap from `run_submit_preflight`.
- Added Submit policy requirement:
  - direct `run_submit_pipeline` requires `capital_deployment_policy_path` or `capital_deployment_policy`
  - missing policy returns `REVIEW_REQUIRED`
- Added BUY policy guard evidence.
- Added SELL policy guard evidence.
- Added Submit Guard Active Policy Manifest fields:
  - `submit_guard_policy`
  - `submit_guard_item_evidence`
- Connected CLI `--capital-deployment-policy` to Submit pipeline.
- Propagated Submit Guard evidence to Runtime Manifest.
- Added Phase15-I regression tests.

## Changed Files

Code:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/models.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

Tests:

- `tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py`
- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`
- `tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`
- `tests/runtime_v2/test_phase14d3_pure_submit_path.py`
- `tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py`

Report:

- `docs/phase_reports/phase15_i_submit_guard_buy_sell_policy_manifest.md`
- `reports/phase_reports/phase15_i_submit_guard_buy_sell_policy_manifest.json`

## BUY Guard Specification

BUY is treated as new risk exposure.

Submit Guard records:

- Pending / Approval / duplicate submit checks
- Capital Deployment Policy source
- `estimated_amount`
- `capital_allocation_amount`
- Current `cash`
- Current `buying_power`
- `max_exposure`
- `max_position_weight`
- `max_buy_order_amount`
- Broker capability / symbol support via existing preflight
- Submit preflight decision

BUY is blocked when:

- Current cash is missing or insufficient
- Current buying power is missing or insufficient
- Current exposure plus estimated amount exceeds `max_exposure`
- Estimated amount exceeds `evaluation_capital * max_position_weight`
- Estimated amount exceeds explicit `max_buy_order_amount`

Submit Guard does not resize the order and does not apply a hidden 100,000 cap.

## SELL Guard Specification

SELL is treated as risk reduction.

Submit Guard records:

- SELL source as Runtime-owned Current position
- `quantity <= Current quantity`
- Broker available quantity source
- `max_sell_liquidation_amount`
- explicit SELL liquidation policy
- Pending / Approval / duplicate submit checks

SELL is not checked against BUY notional caps.

SELL is blocked when:

- Current position quantity is missing
- SELL quantity exceeds Current quantity
- Broker available quantity is missing
- SELL quantity exceeds broker available quantity
- Estimated amount exceeds explicit `max_sell_liquidation_amount`

## Broker Available Quantity Handling

Phase15-I does not formally connect Broker ReadOnly available quantity. That is intentionally left to Phase15-K.

Current Phase15-I behavior:

```text
broker_available_quantity_checked=false
broker_available_quantity_source=current_proxy
manual_review_required=true
```

This means SELL can be evaluated without reusing BUY caps, but the evidence makes clear this is not Full SELL Runtime Acceptance.

## Submit Guard Active Policy Manifest

Run-level:

```text
submit_guard_policy
```

Item-level:

```text
submit_guard_item_evidence
```

Minimum item fields now include:

```text
guard_policy_version
active_amount_policy
policy_source
policy_version
side
pending_item_id
symbol
quantity
estimated_amount
capital_allocation_amount
max_buy_order_amount
max_sell_liquidation_amount
target_investment_ratio
cash_buffer
max_exposure
max_position_weight
max_positions
notional_guard_source
quantity_guard_source
current_position_source
broker_available_quantity_checked
broker_available_quantity_source
guard_decision
guard_reason
manual_review_required
violated_policy
violated_policy_source
should_have_been_blocked_at_planning
blocked_at_submit_reason
```

## Tests

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
python3 -m pytest tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e43_broker_configuration_diagnostics.py
python3 -m pytest tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py
python3 -m pytest tests/runtime_v2/test_phase14d3_pure_submit_path.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/submit/models.py src/ai_fund_lab_v2/runtime_v2/submit/guards.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Result:

```text
PASS
```

## Still Not Fixed

Intentionally left for later Phase15 subphases:

- Morning hidden `max_orders=5`
- Morning hidden per-order `100000`
- SELL Broker ReadOnly available quantity formal connection
- Safety formal connection
- Report / Notification policy reason propagation

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
- Morning hidden cap removal
- SELL Broker ReadOnly available quantity formal connection
- Safety formal connection

## Final Judgment

`PHASE15I_SUBMIT_GUARD_BUY_SELL_POLICY_MANIFEST_COMPLETE`

