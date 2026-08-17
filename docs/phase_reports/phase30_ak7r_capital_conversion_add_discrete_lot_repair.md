# Phase30-AK7R - Capital Conversion / ADD Discrete-Lot Focused Repair

## Scope

Task ID: `Phase30-AK7R`

Type: `FOCUSED_PRODUCTION_COMMON_IMPLEMENTATION_REPAIR`

Authorized implementation scope:

1. Repair the PC/PS discrete executable quantity handoff gap where PC
   materialized positive executable quantity but PS top-level quantity became
   zero.
2. Implement PC-authoritative residual-capital-aware second-lot+ ADD promotion
   with nearest-lot distance evidence.

No Strategy threshold, Candidate, model, cap, Safety, Submit, Execution, fresh
Historical, long Historical, replay, or runtime-run mutation was performed.

## Primary Judgment

```text
PC_POSITIVE_EXECUTABLE_QUANTITY_TO_PS_HANDOFF_REPAIRED = YES
SECOND_LOT_PLUS_RESIDUAL_PROMOTION_IMPLEMENTED = YES
NEAREST_LOT_DISTANCE_EVIDENCE_MATERIALIZED = YES
```

AK7R repairs the capital conversion under-conversion at the PC -> PS boundary
without making PS an allocation authority. Portfolio Construction remains the
capital allocation authority and now emits canonical executable quantity
authority when lot-aware final reallocation has already materialized an
executable discrete quantity. Position Sizing consumes that authority and no
longer recomputes a conflicting zero quantity.

## PC Positive Executable Quantity Handoff

Portfolio Construction now emits:

```text
pc_positive_executable_quantity_authority:
  authority_type = PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
  status = PASS / NOT_APPLICABLE
  final_allocated_quantity
  accepted_lot_increment_weight
  ps_must_consume_canonical_quantity
  future_information_used = false
```

The authority is written both in member-level `phase29_l19_lot_resolution` and
inside `target_weight_resolution.lot_aware_final_reallocation`.

Position Sizing now validates and consumes this authority for `BUY_NEW`,
`REENTRY`, and `BUY_ADD` only when:

- PC authority status is `PASS`,
- quantity is positive and a trading-unit multiple,
- reference price is valid,
- Safety hard cap is preserved,
- Strategy cap is preserved or the existing PC soft-cap overshoot authority is
  present,
- ADD economics / opportunity-cost / lifecycle guards pass for `BUY_ADD`,
- current quantity scope matches the semantic.

## Second-Lot+ ADD Promotion

Implemented design:

```text
RESIDUAL_CAPITAL_AWARE_PROMOTION_WITH_NEAREST_LOT_DISTANCE_EVIDENCE
```

For existing-position `BUY_ADD`, PC materializes:

```text
second_lot_plus_promotion:
  schema_version = second_lot_plus_residual_promotion.v1
  requested_increment_lots
  lower_boundary_lots
  upper_boundary_lots
  lower_boundary_weight
  upper_boundary_weight
  distance_to_lower_weight
  distance_to_upper_weight
  nearest_lot_distance_evidence.threshold_source =
    DETERMINISTIC_LOT_MIDPOINT_NOT_HISTORICAL_OUTCOME
```

The deterministic midpoint rule is architecture-level market discreteness
evidence. It is not selected from historical return. A fractional ADD increment
closer to the lower executable boundary remains unpromoted. A fractional ADD
increment closer to the next executable lot becomes eligible for the existing
residual-capital priority competition, but is not automatically filled.

## Preservation

```text
AK2_ZERO_TO_ONE_LOT_SCOPE_PRESERVED = YES
BUY_NEW_MINIMUM_ONE_LOT_BEHAVIOR_PRESERVED = YES
PM_ADD_REMAINS_INTENT_ONLY = YES
PC_REMAINS_CAPITAL_ALLOCATION_AUTHORITY = YES
PS_REMAINS_EXECUTABLE_QUANTITY_CONSUMER = YES
RESIDUAL_PRIORITY_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
CASH_FEASIBILITY_PRESERVED = YES
NO_LOSS_AVERAGING_PRESERVED = YES
OPPORTUNITY_COST_PRESERVED = YES
AK3R2B_RESERVED_CASH_PRUNING_PRESERVED = YES
NO_FORCED_INVESTMENT = YES
FIXED_EXPOSURE_TARGET_CREATED = NO
```

AK2 remains scoped to `BUY_NEW` / `REENTRY` 0 -> 1lot. AK7R does not create a
general one-lot round-up rule for ADD.

## Runtime Boundary

AK7R intentionally did not repair:

```text
BUY_NEW_RUNTIME_TO_FILL_DROP_DISTRIBUTION.sell-only execution boundary
```

That remains a separate Runtime / Submit / Execution root-cause audit item.

## Tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak7r_pycache python3 -m compileall src/ai_fund_lab_v2/strategy
PASS

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak7r_pycache python3 -m pytest \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py -q
26 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak7r_pycache python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py -q
223 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak7r_pycache python3 -m pytest \
  tests/strategy/test_phase22_g_runtime_planning.py \
  tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
75 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak7r_pycache python3 -m pytest \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/runtime_v2/test_phase26_step6_submit_guard_authority.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
42 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak7r_pycache python3 -m pytest \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/strategy/test_phase27_d2d_position_sizing_plan.py -q
28 passed
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

```text
Phase30-AK8 - Runtime BUY Intent / Sell-Only Execution Boundary Root-Cause Audit
```
