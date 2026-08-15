# Phase29-L21F — BUY_ADD Soft-Cap Position Sizing Integration Repair

## Primary Judgment

`PHASE29_L21F_BUY_ADD_SOFT_CAP_POSITION_SIZING_INTEGRATION_REPAIRED_SHORT_VALIDATION_PASS`.

## Root Cause Repaired

YES.

L21E confirmed that Portfolio Construction correctly authorized an existing `BUY_ADD` lot-aware Strategy-cap overshoot, but Position Sizing final validation still rejected the row with `target_weight_above_position_cap:0` because `maximum_position_weight` remained `0.18`.

L21F repairs that integration gap by making Position Sizing consume the existing L19/L21D authorization for exactly that narrow case.

## Files Changed

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`
- `docs/phase_reports/phase29_l21f_buy_add_soft_cap_position_sizing_integration_repair.md`

## PS Overshoot Authorization Consumer

Position Sizing now allows `target_weight > maximum_position_weight` only when all are true:

- existing position with current quantity
- `pm_action = ADD`
- `membership_intent = RETAIN`
- semantic type is `BUY_ADD`
- ADD economics are already PASS
- `lot_aware_accepted_incremental_weight > 0`
- L19 boundary is `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`
- `strategy_cap_overshoot_applied = true`
- overshoot reason is `LOT_AWARE_STRATEGY_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`
- target remains at or below Safety hard cap
- Safety hard cap is preserved

If any condition is missing or malformed, Position Sizing keeps the existing fail-closed cap validation.

## Strategy Cap Preserved

YES. The normal `target_weight <= maximum_position_weight` contract remains active. The Strategy cap value remains `0.18`.

## Safety Hard Cap Preserved

YES. The Safety hard cap remains `0.25`, and the L21D exception is not applied to the Safety-cap validator.

## BUY_NEW Semantics Changed

NO.

## BUY_ADD Positive Quantity Materialized

YES. Focused PS regression materializes:

```text
target_weight = 0.194658
maximum_position_weight = 0.18
safety_maximum_position_weight = 0.25
quantity_delta_candidate = 400
target_quantity_candidate = 1300
quantity_status = RESOLVED_CANDIDATE
```

## Runtime Planning Special Case Added

NO. Runtime Planning was not changed.

Runtime Planning focused regression confirms that once PS supplies positive quantity, existing mapping produces:

```text
planning_intent = BUY_ADD
planned_quantity = 400
strategy_plan_quantity_unresolved absent
```

## Duplicate Constraint Authority Removed/Resolved

YES. The duplicate downstream hard enforcement of Strategy cap inside PS validation is resolved for L21D-authorized existing `BUY_ADD` only.

## New Component Added

NO.

## Historical-only Logic Added

NO.

## Canonical Quantity Materialization

PC remains target authority and PS remains final quantity authority.

PC no longer copies preflight `executable_quantity_delta = 0` into `final_quantity_delta` as if it were final canonical quantity. It now records:

```text
preflight_executable_quantity_delta = <preflight value>
final_quantity_delta = null
```

PS final is responsible for materializing the actual positive quantity.

## Focused Test Results

PASS:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21d or phase29_l19 or phase28_d55_b'
9 passed

PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l21f or phase29_l19 or phase28_d55_b or phase28_d61 or phase28_d36 or phase29_g'
27 passed

PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py -k 'phase29_l21f or canonical_quantity_delta or buy_add or existing_add_zero_delta'
3 passed
```

## Regression Test Results

PASS:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py
74 passed

PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py
80 passed

PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py
45 passed
```

## py_compile

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_l21f python3 -m py_compile src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/runtime_planning.py
```

## git diff --check

PASS.

## Long Historical Executed

NO.

## Current Run Mutated

NO.

## Recommended Next Validation

Operator should run the next short historical/fresh validation and verify the former `2022-08-19` / `94320` halt path:

- PC final remains `strategy_cap_overshoot_applied = true`
- PS final emits positive `quantity_delta_candidate`
- Runtime Planning emits `BUY_ADD` with `planned_quantity > 0`
- Morning no longer reports `strategy_plan_quantity_unresolved:94320`
- post-trade target remains `<= 0.25` Safety hard cap
