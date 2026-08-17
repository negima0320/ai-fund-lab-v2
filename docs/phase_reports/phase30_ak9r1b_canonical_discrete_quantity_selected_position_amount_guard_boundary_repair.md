# Phase30-AK9R1B - Canonical Discrete Quantity / selected_position_amount Guard Boundary Repair

## Primary Judgment

```text
CANONICAL_DISCRETE_QUANTITY_PRECEDENCE_IMPLEMENTED = YES
SELECTED_POSITION_AMOUNT_FALLBACK_GUARD_PRESERVED = YES
SUBMIT_REMAINS_EXECUTION_SAFETY_VERIFIER = YES
AK9R0_FALSE_SELECTED_AMOUNT_REVIEWS_ELIMINATED = YES
AK9R1_ITEM_SCOPED_REVIEW_BOUNDARY_PRESERVED = YES
```

Phase30-AK9R1B repaired the AK9R1A-confirmed double authority at Submit:

```text
PC canonical discrete executable quantity = X / PASS
PS final quantity = X
Submit selected_position_amount sizing re-review blocks X
```

Submit now recognizes a valid
`PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY` as the canonical
Strategy allocation quantity when it is fully scoped and internally consistent.
The continuous `selected_position_amount` comparison remains fail-closed when
canonical discrete authority is absent or unverifiable.

## Implementation

Changed:

- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`

The Position Sizing authority handoff now preserves `phase29_l19_lot_resolution`
for non-one-lot AK7R discrete authority rows, allowing Submit to inspect the PC
canonical executable quantity evidence.

Planning Submit Feasibility now emits:

```text
canonical_discrete_quantity_submit_authority
canonical_discrete_quantity_precedence_applied
```

Submit applies precedence only when all required checks pass:

- PC authority type is `PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY`
- authority status is `PASS`
- `future_information_used = False`
- `ps_must_consume_canonical_quantity = True`
- semantic is `BUY_NEW`, `REENTRY`, or `BUY_ADD`
- item quantity matches PC final allocated quantity
- PS lot-resolution quantities match the PC canonical quantity
- quantity is trading-unit valid when `one_lot_quantity` is available
- Strategy cap and Safety hard cap preservation evidence passes

If PC authority is present but mismatched or unsafe, Submit returns
`REVIEW_REQUIRED`. If PC authority is absent, the existing
`estimated amount exceeds selected_position_amount` fallback remains active.

## Boundary Preservation

```text
AK7R_CANONICAL_QUANTITY_PRESERVED = YES
AK3R2B_AGGREGATE_CASH_AUTHORITY_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
CASH_FAIL_CLOSED_PRESERVED = YES
NO_FORCED_BUY = YES
```

No Candidate, PM, PC ranking, AK7R promotion, Strategy/Safety cap value,
AK3R2B cash-pruning, AK8R pending composition, same-day SELL proceeds, or
Current Valuation behavior was changed.

Submit remains an execution safety verifier. It still checks cash, buying power,
dynamic cash/exposure, position count, Strategy cap evidence, Safety hard cap
evidence, reservation price authority, and authority consistency.

## Sentinels

New AK9R1B sentinels:

```text
valid PC discrete authority + PS quantity match + selected_position_amount overshoot -> PASS
missing PC discrete authority + selected_position_amount overshoot -> REVIEW_REQUIRED
PC/PS quantity mismatch -> REVIEW_REQUIRED
Safety hard cap not preserved -> REVIEW_REQUIRED
```

The AK9R0 false `selected_position_amount` review class is eliminated for rows
with valid canonical PC discrete authority. Legitimate review and aggregate cash
boundaries remain outside this repair and continue to be governed by the existing
AK9R1 item-scoped and AK3R2B cash-feasible batch contracts.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

No historical outcome was used to tune Strategy parameters.

## Tests

Executed by Codex:

```text
python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase30_ak9r1b_accepts_pc_discrete_quantity_over_selected_amount tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase30_ak9r1b_preserves_selected_amount_review_without_pc_authority tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase30_ak9r1b_blocks_pc_ps_quantity_mismatch tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase30_ak9r1b_blocks_pc_discrete_strategy_or_safety_breach -q
4 passed

python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
24 passed

python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py -q
187 passed

python3 -m pytest tests/phase12/test_phase12_demo_submit_guard.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py -q
60 passed

python3 -m compileall -q src/ai_fund_lab_v2/runtime_v2 src/ai_fund_lab_v2/strategy tests/runtime_v2 tests/strategy
PASS
```

Fresh / long Historical:

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Required Final Judgments

```text
CANONICAL_DISCRETE_QUANTITY_PRECEDENCE_IMPLEMENTED = YES
SELECTED_POSITION_AMOUNT_FALLBACK_GUARD_PRESERVED = YES
SUBMIT_REMAINS_EXECUTION_SAFETY_VERIFIER = YES
AK9R0_FALSE_SELECTED_AMOUNT_REVIEWS_ELIMINATED = YES
AK9R1_ITEM_SCOPED_REVIEW_BOUNDARY_PRESERVED = YES
AK7R_CANONICAL_QUANTITY_PRESERVED = YES
AK3R2B_AGGREGATE_CASH_AUTHORITY_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
CASH_FAIL_CLOSED_PRESERVED = YES
NO_FORCED_BUY = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK9R2 - Consolidated Post-Repair Fresh Readiness Regression
```
