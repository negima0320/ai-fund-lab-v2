# Phase29-L21T-C - One-Lot Discrete Quantity Materialization Repair

Task ID: `Phase29-L21T-C`

Mode: focused Production-common implementation + short regression. No fresh-run, resume-run, long Historical run, Runtime/Pending state mutation, Accepted Generation change, model change, threshold tuning, Safety hard-cap relaxation, Buy Quality change, REENTRY redesign, Market Context change, or Corporate Action policy change was performed.

## Primary Judgment

`PHASE29_L21T_C_ONE_LOT_DISCRETE_QUANTITY_MATERIALIZATION_REPAIRED_FOCUSED_REGRESSION_PASS`

`L21T_FRESH_VALIDATION_READY = YES`

## Root Cause

The confirmed defect was in Position Sizing quantity materialization.

Producer / consumer chain:

```text
Portfolio Construction L19/L21S lot-aware final reallocation
-> phase29_l19_lot_resolution one-lot authority
-> Position Sizing target_weight / target_notional
-> _lot_quantity continuous-notional floor
-> Runtime Planning planned_quantity
-> Strategy Planning Authority pending item creation
```

For `78780` on `2022-08-24`, PC had already approved:

- `one_lot_quantity = 100`
- `one_lot_notional = 242000.0`
- `one_lot_fallback_applied = true`
- `one_lot_feasibility_status = PASS`
- `strategy_cap_overshoot_applied = true`
- post-trade weight `0.243189`, below Safety hard cap `0.25`

PS preserved that evidence but then recalculated:

```text
target_notional = target_weight * portfolio_value = 241999.81
_lot_quantity(241999.81, price=2420, unit=100) = 0
```

Thus a valid approved `242000 JPY / 100 shares` discrete authority was defeated by a later continuous-notional floor. Runtime Planning correctly consumed the zero PS quantity and emitted `NO_ORDER`.

## Repair

Changed production file:

- `src/ai_fund_lab_v2/strategy/position_sizing.py`

Position Sizing now resolves a local one-lot discrete quantity authority before final BUY-side quantity materialization. The helper validates the existing PC/L19 authority again before use:

- semantic type is `BUY_NEW`, `REENTRY`, or `BUY_ADD`;
- Strategy cap overshoot authority is coherent;
- `one_lot_fallback_applied == true`;
- `one_lot_feasibility_status == PASS`;
- authorized quantity is positive and no larger than `one_lot_quantity`;
- quantity aligns to `trading_unit`;
- `one_lot_notional` matches `price * authorized_quantity`;
- post-trade target remains within Safety hard cap;
- `safety_hard_cap_preserved` is not false.

When valid, PS materializes:

```text
target_quantity_candidate / transaction_quantity_candidate
from final_allocated_quantity, executable_quantity_delta, or one_lot_quantity
```

instead of recomputing the authorized one-lot expression from continuous target notional.

## Contract Preservation

Safety hard cap:

- 25% remains hard.
- one-lot authority is not consumed if target or post-trade evidence exceeds Safety hard cap.

Strategy 18%:

- remains the normal Strategy cap.
- Safety-contained one-lot overshoot remains explicit.
- one-lot authority cannot materialize 2+ lots.

Minimum meaningful notional:

- remains diagnostic-only for otherwise executable one-lot BUY paths.
- no hard gate was reintroduced.

Intent semantics:

- BUY_NEW remains BUY_NEW.
- BUY_ADD remains BUY_ADD and uses the approved one-lot increment.
- REENTRY remains REENTRY.
- SELL / REDUCE / EXIT paths were not changed.

## Evidence

Successful rows now expose:

- `continuous_target_notional`
- `discrete_authorized_quantity`
- `discrete_authorized_notional`
- `final_target_quantity`
- `final_quantity_delta`
- `one_lot_authority_consumed`
- `one_lot_authority_reason`
- `safety_hard_cap_validation`
- existing `phase29_l19_lot_resolution`
- final `quantity_status`

## Regression Results

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l21t_c or phase29_l21t_b or phase29_l21f or phase29_l21s or phase29_l19' -q
```

Result:

```text
17 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py -k 'phase29_l21t_b or phase29_l21f or sell_reduce_exit or sell' -q
```

Result:

```text
8 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -k 'phase29_l21t_b or phase23_bo or sell' -q
```

Result:

```text
3 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21s or phase29_l19 or phase28_d55_b or phase29_l21d or phase29_l16_sell_reduce_exit' -q
```

Result:

```text
16 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py -q
```

Result:

```text
219 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_qe_input_materialization.py -q
```

Result:

```text
23 passed
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -q
```

Result:

```text
18 passed
```

Static:

```text
py_compile PASS
git diff --check PASS
```

## Completion

L21T-C is complete at focused-regression scope. User-operated fresh validation is ready.

```text
L21T_FRESH_VALIDATION_READY = YES
```
