# Phase32-BR ADD Repeated-Lot Quantity Consistency Narrow Repair

## Executive Summary

Phase32-BR repaired the Phase32-BQ `94340` multi-lot ADD quantity inconsistency
at the source of materialization.

The defect was:

```text
current_quantity = 700
accepted_incremental_quantity = 200 per ADD lot
old pre_quantity sequence = 700, 800, 900
old final target = 1100
sum accepted delta = 600
BF expected final target = 700 + 600 = 1300
```

The repair makes repeated ADD lot candidates advance by the same executable
increment quantity used by the candidate:

```text
pre_quantity(lot N+1) = post_quantity(lot N)
```

For the BQ `94340` reproduction, the repaired sequence is:

```text
700 -> 900
900 -> 1100
1100 -> 1300
```

The BF PC-to-PS boundary now passes on the saved `2022-10-11` artifact
reproduction, with `94340` aggregated as:

```text
current_quantity = 700
final_quantity_delta = 600
final_target_quantity = 1300
```

No fresh-run, resume, replay, or backtest was executed.

## Required Inputs

Read:

- `docs/phase_reports/phase32_bq_post_bo_2022_10_11_morning_halt_exact_trace.md`
- `docs/phase_reports/phase32_bf_pc_to_ps_consumer_switch_boundary_validator.md`

## Changed Files

```text
src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py
src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py
tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
docs/phase_reports/phase32_br_add_repeated_lot_quantity_consistency_narrow_repair.md
```

## Repair Boundary

The narrow source repair is in ADD next-lot materialization:

```text
common_marginal_capital_frontier_shadow._add_next_lot_candidates()
```

Before BR, each ADD candidate could use `ps_row.transaction_quantity_candidate`
as its executable increment, while the next hypothetical pre-state advanced by
only `trading_unit`.

After BR:

```text
increment_quantity = resolved ADD lot executable increment
pre_quantity = current_quantity + increment_quantity * (increment_index - 1)
prior_notional = increment_quantity * reference_price * (increment_index - 1)
```

The source authority is materialized on each candidate:

```text
increment_quantity_source_authority =
  PS_PREFLIGHT_TRANSACTION_QUANTITY_CANDIDATE
  or PC_OR_TRADING_UNIT_DEFAULT
```

This keeps PS preflight executable quantity separate from the trading unit.
The trading unit remains the rounding floor; it is no longer implicitly treated
as the repeated-lot step when the executable ADD increment is larger.

## BF Guard Tightening

The BF boundary validator still enforces the original aggregate invariant:

```text
final_target_quantity = current_quantity + final_quantity_delta
```

BR also adds a narrow per-lot ADD chain check before aggregation:

```text
target_quantity(lot N) = pre_quantity(lot N) + accepted_incremental_quantity(lot N)
pre_quantity(lot N+1) = target_quantity(lot N)
```

New fail-closed reasons:

```text
add_lot_target_quantity_inconsistent
add_repeated_lot_quantity_progression_inconsistent
```

This preserves fail-closed behavior for corrupted or mixed ADD sequences.

## BQ 2022-10-11 Reproduction

Input artifacts:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z/daily/2022-10-11/strategy/portfolio_construction.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z/daily/2022-10-11/strategy/position_sizing_preflight.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z/daily/2022-10-11/strategy/marginal_capital_frontier_authority.json
```

Read-only reproduction after BR:

```text
authority_result.status = PASS
authority_result.accepted_target_count = 7
pc_to_ps_consumer_switch_boundary.status = PASS
pc_to_ps_consumer_switch_boundary.aggregated_ps_target_count = 5
pc_to_ps_consumer_switch_boundary.review_reasons = []
```

`94340` accepted targets:

| Lot | Pre quantity | Accepted incremental quantity | Target quantity |
| ---: | ---: | ---: | ---: |
| 1 | 700 | 200 | 900 |
| 2 | 900 | 200 | 1100 |
| 3 | 1100 | 200 | 1300 |

`94340` BF aggregated target:

| Field | Value |
| --- | ---: |
| `current_quantity` | 700 |
| `final_quantity_delta` | 600 |
| `final_target_quantity` | 1300 |

The prior BQ blocker is absent:

```text
ps_final_quantity_delta_inconsistent not present
```

## Non-Regression

The existing 100-share ADD path remains intact:

```text
current_quantity = 200
accepted lots = 3 x 100
final_quantity_delta = 300
final_target_quantity = 500
BF boundary status = PASS
```

NEW and REENTRY generation were not changed. Cash, budget, BO PIT flags, PS
quantity arithmetic, Runtime mapping, Pending/Orders/Execution, REDUCE/EXIT,
Risk Pacing, and legacy fallback policy were not changed.

Legacy fallback remains disabled:

```text
legacy_target_gap_input_used = false
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

## Verification

Focused regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py

46 passed
```

Broader adjacent regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py

88 passed
```

BO/BG adjacent regression slice:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py

204 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py

PASS
```

## Final Judgments

```text
PHASE32_BR_ADD_QUANTITY_PROGRESSION_REPAIRED = YES
PHASE32_BR_BQ_94340_FINAL_TARGET = 1300
PHASE32_BR_BF_BOUNDARY_PASS = YES
PHASE32_BR_PS_NET_DELTA_PASS = YES
PHASE32_BR_100_SHARE_ADD_REGRESSION = PASS
PHASE32_BR_MULTI_LOT_ADD_REGRESSION = PASS
PHASE32_BR_LEGACY_FALLBACK_USED = NO
PHASE32_BR_REGRESSION_STATUS = PASS
PHASE32_BR_RESUME_READY = YES
PHASE32_BR_NEXT_STEP = User-operated resume or short fresh validation from the post-BO halted run to confirm 2022-10-11 morning proceeds past the BF boundary.
```
