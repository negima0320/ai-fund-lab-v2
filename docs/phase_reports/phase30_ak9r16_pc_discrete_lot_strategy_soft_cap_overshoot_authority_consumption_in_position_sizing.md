# Phase30-AK9R16 - PC Discrete-Lot Strategy Soft-Cap Overshoot Authority Consumption in Position Sizing

## Primary Judgment

```text
PC_DISCRETE_QUANTITY_AUTHORITY_REMAINS_CANONICAL = YES
PC_SOFT_CAP_DISCRETE_OVERSHOOT_AUTHORITY_RECOGNIZED = YES
PS_CONSUMES_PC_AUTHORIZED_DISCRETE_QUANTITY = YES
PS_DUPLICATE_SOFT_CAP_REJECTION_REMOVED = YES
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO_FOR_REPAIRED_SCOPE
FRESH_VALIDATION_BLOCKERS = NONE_KNOWN_FOR_REPAIRED_SCOPE
FRESH_20BD_VALIDATION_READY = YES
```

Phase30-AK9R16 repairs the Phase30-AK9R15 `POSITION_SIZING_AUTHORITY_GAP`.
Portfolio Construction remains the canonical allocation and discrete quantity
authority. Position Sizing now recognizes the PC-authorized
`SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION` soft-cap overshoot only when
the canonical PC executable quantity authority is present, passing, and quantity
consistent.

No Strategy threshold, cap value, Candidate, Portfolio Construction, cash,
Submit, Runtime, replay, fresh Historical, or long Historical change was made.

## Repair Scope

The only implementation change is in
`src/ai_fund_lab_v2/strategy/position_sizing.py`.

Position Sizing already supported `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`
for legacy one-lot and lot-aware overshoot reasons. AK7R introduced the
PC-authorized residual-capital second-lot+ promotion reason, but the PS final
schema guard did not consume that reason and therefore rejected the 2022-08-24
`94320 BUY_ADD` row as `target_weight_above_position_cap:4`.

The repaired predicate now accepts:

```text
lot_overshoot_reason = SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION
```

only when:

```text
boundary_classification = DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX
strategy_cap_overshoot_applied = true
one_lot_fallback_applied = true
one_lot_feasibility_status = PASS
safety_hard_cap_preserved != false
target_weight <= safety_hard_cap
BUY_ADD economics / opportunity-cost checks pass
pc_positive_executable_quantity_authority.status = PASS
pc_positive_executable_quantity_authority.ps_must_consume_canonical_quantity = true
pc authority final_allocated_quantity == lot resolution canonical quantity
```

## AK9R15 94320 Equivalent Sentinel

```text
symbol = 94320
semantic_buy_type = BUY_ADD
current_quantity = 1100
target_weight = 0.181184
strategy soft cap = 0.18
safety hard cap = 0.25
PC executable quantity = 100
boundary = DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX
reason = SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION
PS result = PASS
quantity_delta_candidate = 100
target_quantity_candidate = 1200
pc_discrete_quantity_authority_consumed = true
```

## Preservation

```text
STRATEGY_SOFT_CAP_PRESERVED = YES
SAFETY_HARD_CAP_FAIL_CLOSED_PRESERVED = YES
UNAUTHORIZED_SOFT_CAP_OVERSHOOT_FAIL_CLOSED_PRESERVED = YES
PC_PS_QUANTITY_CONSISTENCY_GUARD_PRESERVED = YES
AK7R_CAPITAL_CONVERSION_PRESERVED = YES
AK2_ONE_LOT_AUTHORITY_PRESERVED = YES
SUBMIT_CANONICAL_QUANTITY_HANDOFF_PRESERVED = YES
VALID_PC_AUTHORITY_NOT_DROPPED_BY_PS = YES
PS_ARTIFACT_FAILURE_SCOPE_CONFORMANT = YES
```

Negative sentinels remain fail-closed for missing PC authority, above-Safety
target, PC/lot quantity mismatch, malformed `ps_must_consume_canonical_quantity`,
and arbitrary non-canonical overshoot reason.

## Non-Changes

```text
NEW_BUY_FILTER_CREATED = NO
NEW_ADD_FILTER_CREATED = NO
NEW_INVESTMENT_PRIORITY_CREATED = NO
FIXED_EXPOSURE_TARGET_CREATED = NO
PRODUCTION_STRATEGY_CHANGED = NO
STRATEGY_CAP_VALUE_CHANGED = NO
SAFETY_HARD_CAP_VALUE_CHANGED = NO
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r16_pycache python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q
102 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r16_pycache python3 -m compileall src/ai_fund_lab_v2/strategy src/ai_fund_lab_v2/runtime_v2
PASS

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r16_pycache python3 -m pytest \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_g_runtime_planning.py -q
176 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r16_pycache python3 -m pytest \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/runtime_v2/test_phase26_step6_submit_guard_authority.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py -q
53 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r16_pycache python3 -m pytest \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/strategy/test_phase27_d2d_position_sizing_plan.py -q
28 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r16_pycache python3 -m pytest \
  tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py -q
31 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak9r16_pycache python3 -m pytest \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/phase12/test_phase12_demo_submit_guard.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py -q
41 passed
```

`tests/runtime_v2/test_phase30_ak9r1b_selected_position_amount_guard.py` is not
present in this checkout; AK9R1B preservation was covered through the existing
Submit guard and planning-submit feasibility suites above.

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK9R17 - User-Operated Fresh 20BD End-to-End Validation
```
