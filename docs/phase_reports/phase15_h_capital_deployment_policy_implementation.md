# Phase15-H Capital Deployment Policy Implementation

## Status

`PHASE15H_CAPITAL_DEPLOYMENT_POLICY_IMPLEMENTED`

Phase15-H implemented the explicit Capital Deployment Policy / Policy Source foundation required before removing hidden Runtime policy from Morning and Submit.

The objective of this phase was not to remove all hidden caps or split BUY / SELL guards. It was to ensure Runtime can read, validate, and emit an explicit policy source, and can stop guarded jobs when the policy is missing or invalid.

## Implementation Summary

Implemented:

- Added Capital Deployment Policy model and loader.
- Added explicit demo policy artifact.
- Added CLI option:
  - `--capital-deployment-policy`
- Added Runtime Manifest policy evidence fields.
- Added guarded job behavior for missing / invalid policy:
  - `morning`
  - `sell_planning`
  - `submit`
- Added regression tests for valid, missing, incomplete, CLI manifest, missing CLI behavior, and explicit `max_positions` evidence.

Not implemented in Phase15-H by design:

- Submit hidden `max_order_amount=100000` removal
- Morning hidden `max_orders=5` removal
- Morning hidden per-order `100000` cap removal
- BUY / SELL Guard separation
- SELL Broker available quantity evidence
- Safety connection
- Report / Notification policy reason propagation

## Changed Files

Code:

- `src/ai_fund_lab_v2/runtime_v2/policy/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

Config:

- `configs/runtime_v2/capital_deployment_demo.json`

Tests:

- `tests/runtime_v2/test_phase15h_capital_deployment_policy.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`
- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`
- `tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py`
- `tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py`
- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`

Report:

- `docs/phase_reports/phase15_h_capital_deployment_policy_implementation.md`
- `reports/phase_reports/phase15_h_capital_deployment_policy_implementation.json`

## Policy Schema

Required fields:

| Field | Required | Notes |
|---|---:|---|
| `policy_version` | Yes | Non-empty string |
| `policy_source` | Yes | Non-empty string retained in manifest |
| `evaluation_capital` | Yes | Positive number |
| `target_investment_ratio` | Yes | Ratio `0.0 <= value <= 1.0` |
| `cash_buffer` | Yes | Ratio `0.0 <= value <= 1.0` |
| `max_exposure` | Yes | Non-negative number, must be `<= evaluation_capital` |
| `max_position_weight` | Yes | Ratio `0.0 <= value <= 1.0` |
| `max_positions` | Yes | Positive integer |
| `min_order_amount` | Yes | Non-negative number |
| `max_buy_order_amount` | Yes | Non-negative number or `null` |
| `max_sell_liquidation_amount` | Yes | Non-negative number or `null` |
| `buy_notional_policy` | Yes | Non-empty string |
| `sell_liquidation_policy` | Yes | Non-empty string |
| `manual_review_threshold.buy_amount` | Yes | Non-negative number or `null` |
| `manual_review_threshold.sell_liquidation_amount` | Yes | Non-negative number or `null` |

Validation rule:

- `target_investment_ratio + cash_buffer <= 1.0`

The loader does not provide hidden defaults. Missing required fields produce validation errors.

## Demo Policy

Created:

```text
configs/runtime_v2/capital_deployment_demo.json
```

The demo policy defines:

- `evaluation_capital=1000000`
- `target_investment_ratio=0.85`
- `cash_buffer=0.05`
- `max_exposure=850000`
- `max_position_weight=0.2`
- `max_positions=5`
- `max_buy_order_amount=null`
- `max_sell_liquidation_amount=null`

`max_positions=5` is now represented as explicit policy evidence when the CLI is given this policy. Phase15-H does not yet remove the legacy hidden `--max-orders` / Morning default behavior.

## CLI Behavior

New option:

```text
--capital-deployment-policy configs/runtime_v2/capital_deployment_demo.json
```

Policy is evaluated for every CLI run and emitted to the manifest.

Policy is required before guarded jobs proceed:

- `morning`
- `sell_planning`
- `submit`

For missing or invalid policy:

- Runtime does not fallback to hidden defaults.
- Planning / Submit guarded job does not proceed.
- `policy_missing=true` for missing policy.
- `final_state=REVIEW_REQUIRED`.
- `exit_code=20`.

## Manifest Fields

Runtime manifest now emits:

```text
capital_deployment_policy_loaded
capital_deployment_policy_source
capital_deployment_policy_path
capital_deployment_policy_version
evaluation_capital
target_investment_ratio
cash_buffer
max_exposure
max_position_weight
active_max_positions
max_positions_source
max_positions_policy_version
max_buy_order_amount
max_sell_liquidation_amount
buy_notional_policy
sell_liquidation_policy
policy_validation_status
policy_missing
```

The same payload is also emitted in the `capital_deployment_policy` manifest stage.

## Regression Tests

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15h_capital_deployment_policy.py
python3 -m pytest tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py
python3 -m pytest tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py
python3 -m pytest tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py
python3 -m pytest tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py
python3 -m pytest tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py
```

Result:

```text
PASS
```

## No Hidden Policy Regression Preparation

Phase15-H added the explicit policy source and manifest proof needed for the next fixes.

Next regression targets:

- Submit `max_order_amount=100000` must be replaced by explicit BUY / SELL policy sources.
- Morning `max_orders=5` must either be derived from explicit policy or removed from policy behavior.
- Morning per-order `100000` cap must be replaced by explicit Capital Deployment constraints.
- Submit manifest must include active policy details from Capital Deployment Policy and side-specific guard decisions.

## Prohibited Actions Check

Not performed:

- Submit execution
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd / plist modification
- Current direct edit
- Runtime bypass creation
- fake adapter Full Runtime PASS declaration
- hidden cap removal beyond Phase15-H scope
- BUY / SELL Guard separation beyond Phase15-H scope

## Final Judgment

`PHASE15H_CAPITAL_DEPLOYMENT_POLICY_IMPLEMENTED`

