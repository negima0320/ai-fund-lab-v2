# Phase32-CJ — Quality-Deployable NEW/REENTRY Lot-Aware Boundary Narrow Repair

## Executive Summary

Phase32-CJ repaired the narrow PC lot-aware/BF boundary defect identified in Phase32-CI without relaxing the Phase32-CH Adaptive Buy Quality ceiling.

The defect was that reduced-quality high-price one-lot rows could still pass the legacy PC one-lot rescue path and consume the remaining lot-aware budget before legitimate quality-deployable multi-lot NEW rows reached BF. In the Day-0 trace this caused 89180 and 76470 to be zeroed by `minimum_lot_exceeds_remaining_budget`, even though their quality-authorized targets supported at least one trading lot.

The repair makes the legacy one-lot admission quality-ceiling-aware:

- If a NEW/REENTRY row has an enforced quality-authorized target and one trading lot exceeds that target, PC lot-aware admission now fail-closes with `lot_minimum_exceeds_quality_authorized_target`.
- If the quality-authorized target supports one or more lots, PC lot-aware no longer lets earlier below-ceiling one-lot rescue rows consume the budget ahead of it.
- Final lot-aware allocation is capped at the quality-authorized target; later budget/reallocation cannot re-expand to the pre-quality target.

No implicit one-lot rescue was added. The CH-intended 37820 reduction behavior remains preserved. ADD admission, BF-only ADD authority, cap/Cash/budget/Risk Pacing, PS arithmetic, Runtime, REDUCE, EXIT, and legacy fallback-zero contracts are unchanged.

## Scope

Changed files:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`

Production behavior changed only at the intended PC lot-aware target authority boundary for quality-reduced entry candidates. No fresh-run, resume, replay, or backtest was executed.

## Implementation

### Quality Ceiling Source Resolution

Added PC helper resolution for the entry quality ceiling:

- Direct member field: `quality_authorized_target_weight`
- Target resolution field: `target_weight_resolution.quality_authorized_target_weight`
- Adaptive Buy Quality adjustment field: `post_quality_target_weight`

The enforcement state is resolved from:

- `quality_target_upper_bound_enforced`
- `target_weight_resolution.quality_target_upper_bound_enforced`
- or a reduced `quality_authorized_target_weight < pre_quality_base_target_weight`

### One-Lot Rescue Guard

`_quality_adjusted_one_lot_admission()` now blocks reduced NEW/REENTRY one-lot rescue when:

- participant is `BUY_NEW`
- quality ceiling is enforced
- `quality_authorized_target_weight` is known
- one-lot minimum weight is known
- `quality_authorized_target_weight < one_lot_weight`

The exact blocked reason is:

`lot_minimum_exceeds_quality_authorized_target`

This preserves the Phase32-CI non-scope decision for 33700 / 83060 / 92420 / 58200: below-one-lot reduced targets remain non-deployable unless a future explicit PIT authority is designed.

### Final Reallocation Bound

The final lot-aware allocation loop now enforces:

`final_deployable_target_weight <= quality_authorized_target_weight`

for quality-ceiling-enforced NEW/REENTRY rows. This prevents later PC budget/reallocation steps from re-expanding reduced allocation back to the pre-quality/base target.

## Focused Reproduction Results

### 89180 / 76470

Regression test:

`test_phase32_cj_quality_deployable_new_reaches_lot_aware_boundary_after_reduced_one_lot_blocks`

Result:

- 33700 and 92420 are blocked at PC lot-aware with `lot_minimum_exceeds_quality_authorized_target`.
- 89180 remains positive:
  - quality-authorized target: 1.9686%
  - final target: 1.9500%
  - final quantity: 3900 shares
- 76470 remains positive:
  - quality-authorized target: 1.9385%
  - final target: 1.8000%
  - final quantity: 1200 shares
- Capital conservation: PASS

### 37820 / Below-One-Lot Controls / 94340

Regression test:

`test_phase32_cj_ch_controls_preserve_37820_and_below_one_lot_quality_blocks`

Result:

- 37820 CH behavior preserved:
  - final target: 2.0400%
  - final quantity: 300 shares
  - below quality-authorized target 2.4103%
- 33700 / 83060 / 92420 / 58200 remain blocked with `lot_minimum_exceeds_quality_authorized_target`.
- 94340 full-allocation control remains positive:
  - final target: 2.8820%
  - final quantity: 200 shares

## Verification

Commands run:

```bash
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k phase32_cj
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py
python3 -m pytest tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
python3 -m pytest tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
PYTHONPYCACHEPREFIX=/tmp/phase32_cj_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py
```

Results:

- CJ focused tests: PASS, 2 passed
- Portfolio construction suite: PASS, 124 passed
- Marginal capital frontier authority suite: PASS, 45 passed
- BG switch + AS shadow suites: PASS, 25 passed
- `py_compile`: PASS

## Guardrail Preservation

- CH quality ceiling: preserved
- Candidate/deployability separation: preserved
- CC NEW/REENTRY multi-lot path: preserved
- BV zero-target block: preserved
- BZ ADD PASS-only / BF-only authority: preserved
- BR quantity consistency: preserved
- BT Strategy/Safety cap: preserved
- Cash/budget conservation: preserved
- Risk Pacing: preserved
- PS arithmetic: unchanged
- Runtime: unchanged
- REDUCE/EXIT: unchanged
- Legacy fallback zero: preserved
- PIT-only: preserved

## Final Judgments

PHASE32_CJ_PC_LOT_AWARE_ZERO_COLLAPSE_REPAIRED = YES

PHASE32_CJ_QUALITY_BOUND_PRESERVED = YES

PHASE32_CJ_89180_POSITIVE_TARGET_RESTORED = YES

PHASE32_CJ_76470_POSITIVE_TARGET_RESTORED = YES

PHASE32_CJ_37820_CH_BEHAVIOR_PRESERVED = YES

PHASE32_CJ_BELOW_ONE_LOT_BLOCK_PRESERVED = YES

PHASE32_CJ_CC_BF_PS_COMPATIBLE = YES

PHASE32_CJ_BV_BZ_GUARDRAILS_PRESERVED = YES

PHASE32_CJ_REGRESSION_STATUS = PASS

PHASE32_CJ_FRESH_VALIDATION_READY = YES

PHASE32_CJ_NEXT_STEP = User-operated short fresh validation from 2022-10-03 to confirm Day-0 BUY_NEW breadth recovers without reintroducing below-one-lot implicit rescue or quality ceiling re-expansion.
