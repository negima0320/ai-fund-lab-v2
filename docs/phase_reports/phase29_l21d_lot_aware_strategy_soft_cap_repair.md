# Phase29-L21D — Lot-Aware Strategy Soft Cap Repair

## Primary Judgment

`PHASE29_L21D_LOT_AWARE_STRATEGY_SOFT_CAP_REPAIR_IMPLEMENTED`.

The L21C recommendation B path was implemented: Strategy cap remains the desired target / attribution boundary, while a narrow lot-aware overshoot is allowed only for existing-position `BUY_ADD` when the minimum executable lot crosses Strategy cap but remains inside Safety hard cap.

## Root Cause

L19 correctly separated Strategy cap from Safety hard cap and produced `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX` evidence, but Portfolio Construction re-applied Strategy cap as a hard final allocation blocker. That converted economically eligible PM ADD candidates back to cash before Position Sizing could produce a positive canonical quantity delta.

## Files Changed

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `docs/phase_reports/phase29_l21d_lot_aware_strategy_soft_cap_repair.md`

## Config Changed

NO.

## Strategy Cap Value

`0.18`.

## Strategy Cap Semantics Before/After

Before: Strategy cap was treated as a hard terminal blocker during lot-aware final reallocation, even when L19 evidence showed the minimum lot was inside Safety hard cap.

After: Strategy cap remains the canonical strategy target cap. A Strategy cap overshoot can be applied only for existing-position `BUY_ADD` with positive ADD economics, L19 `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`, and post-trade weight at or below Safety hard cap.

## Safety Hard Cap Value

`0.25`.

## Safety Semantics Changed

NO. Safety hard cap remains a hard boundary.

## BUY_ADD Overshoot Scope

Allowed only when all are true:

- existing position
- PM action is `ADD`
- ADD allocation eligibility is `PASS`
- incremental investment value is `POSITIVE`
- opportunity cost is `PASS`
- L19 boundary is `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`
- minimum lot post-trade weight is greater than Strategy cap and less than or equal to Safety hard cap

Evidence now carries `strategy_target_cap`, `strategy_cap_overshoot_applied`, `strategy_cap_overshoot_weight`, `post_trade_weight`, `safety_hard_cap`, `safety_margin_after_trade`, and `lot_overshoot_reason`.

## BUY_NEW Semantics Changed

NO. `BUY_NEW` remains blocked by Strategy cap and Safety hard cap rules as before.

## Forced Deployment Introduced

NO.

## New Component Added

NO.

## Positive Boundary Tests

- `test_phase29_l21d_lot_boundary_authorizes_buy_add_strategy_soft_overshoot`
- `test_phase29_l19_ps_preflight_materializes_strategy_safety_lot_boundary`

## Negative Boundary Tests

- `test_phase29_l21d_strategy_soft_overshoot_requires_add_economic_pass`
- `test_phase29_l19_buy_new_safety_hard_breach_blocks_without_forced_deployment`
- `test_phase29_l19_ps_preflight_separates_buy_new_safety_hard_breach`

## Safety Regression

PASS. Safety hard cap breach remains blocked and Safety hard cap schema checks were not loosened.

## L19 Regression

PASS. L19 Strategy/Safety cap separation evidence remains present and is now consumed by PC for the narrow eligible ADD case.

## Phase28 ADD Bridge Regression

PASS. Existing Phase28 ADD bridge sizing and lot-aware final target consumption tests pass.

## Runtime Planning Regression

PASS. Runtime Planning was not changed. Existing canonical positive quantity delta mapping continues to produce `BUY_ADD` for current holdings.

## Current Run Mutation

NO.

## Long Historical Executed

NO.

## Validation Commands

- `PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l21d or phase29_l19 or phase28_d55_b'`
- `PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l19 or phase28_d55_b or phase28_d61'`
- `PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py -k 'canonical_quantity_delta or existing_add_zero_delta or BUY_ADD or buy_add'`
- `PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_l21d python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py`
- `git diff --check`
- `PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py`
- `PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py`

## Recommended Operator Validation

Run the next short historical/resume validation from the operator-controlled workflow, verifying that previously stranded eligible PM ADD cases produce positive Position Sizing deltas and map naturally to Runtime Planning `BUY_ADD`, while post-trade weights remain at or below Safety hard cap.
