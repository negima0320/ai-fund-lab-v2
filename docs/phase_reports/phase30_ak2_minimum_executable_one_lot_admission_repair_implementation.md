# Phase30-AK2 - Minimum Executable One-Lot Admission Repair Implementation

## Scope

Task ID: `Phase30-AK2`

Type: `IMPLEMENTATION_REPAIR`

Target:

```text
BUY_NEW / REENTRY
current quantity = 0
0 -> 1lot only
```

No Strategy cap, Safety hard cap, Candidate, Selection threshold, Entry
threshold, Risk threshold, lot size, model, Accepted Generation, forced BUY,
forced exposure, fixed position count, fresh run, or long Historical change was
made.

## Primary Judgment

```text
MINIMUM_EXECUTABLE_ONE_LOT_REPAIR_IMPLEMENTED = YES
BUY_NEW_ZERO_TO_ONE_LOT_ACTION_EFFECTIVE = YES
REENTRY_ZERO_TO_ONE_LOT_ACTION_EFFECTIVE = YES
BUY_ADD_BEHAVIOR_UNCHANGED = YES
SECOND_LOT_PLUS_BEHAVIOR_UNCHANGED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
ONE_PRODUCTION_ONE_LOT_PATH = YES
```

## Implementation Summary

The repair made the existing one-lot admission architecture action-effective
for guarded BUY_NEW / REENTRY `0 -> 1lot` cases.

Changed production code:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
```

Portfolio Construction now emits explicit
`minimum_executable_one_lot_authority` when:

- participant is BUY_NEW or REENTRY,
- current quantity is zero,
- original PC positive target is below one lot,
- promoted final target is exactly one lot,
- Entry / one-lot admission passes,
- Strategy cap is preserved,
- Safety hard cap is preserved,
- broker / lot feasibility is PASS,
- remaining budget is sufficient.

The canonical reason is:

```text
MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED
```

Position Sizing consumes this authority only after PC has materialized it. PS
does not independently round up positive sub-lot targets.

## 0 -> 1lot Admission

New evidence materialized:

```text
minimum_executable_one_lot_authority:
  authority_type = PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION
  decision = ADMIT
  reason = MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED
  symbol
  intent
  current_quantity
  original_pc_target_weight
  original_pc_increment_weight
  original_pc_target_notional
  one_lot_weight
  one_lot_notional
  target_to_one_lot_ratio
  projected_one_lot_portfolio_weight
  strategy_cap
  safety_cap
  admission_decision
  final_promoted_target_weight
  ps_final_quantity
  future_information_used = false
```

This evidence is copied into the member-level `phase29_l19_lot_resolution` and
target-weight resolution so the PC -> PS authority chain remains auditable.

## Guard Preservation

```text
SAFETY_HARD_CAP_BREACH -> NEVER_ADMIT
Strategy cap breach without existing policy authority -> BLOCK
BUY_WAIT / REJECT / REVIEW_REQUIRED -> BLOCK_OR_DEFER
OVERHEATED_DECELERATING_ENTRY / REVERSAL_RISK_ENTRY -> DEFER
cash insufficient -> BLOCK
broker / lot infeasible -> BLOCK
```

## BUY_NEW / REENTRY Scope

```text
BUY_NEW_ZERO_TO_ONE_LOT_ACTION_EFFECTIVE = YES
REENTRY_ZERO_TO_ONE_LOT_ACTION_EFFECTIVE = YES
```

The REENTRY semantic is preserved in `phase29_l19_lot_resolution.semantic_type`
instead of being collapsed into generic BUY_NEW.

## BUY_ADD / Second-Lot Preservation

```text
BUY_ADD_BEHAVIOR_UNCHANGED = YES
SECOND_LOT_PLUS_BEHAVIOR_UNCHANGED = YES
```

The minimum executable authority rejects existing positions and BUY_ADD. The
existing Strategy soft-cap one-lot ADD path remains separate and unchanged.

## PC / PS Authority Preservation

```text
PC_ALLOCATION_AUTHORITY = PRESERVED
PS_QUANTITY_AUTHORITY = PRESERVED
ONE_PRODUCTION_ONE_LOT_PATH = YES
```

Chain:

```text
PC positive sub-lot target
-> PS lot preflight
-> PC explicit minimum executable one-lot authorization
-> PS final quantity = one lot
```

No parallel one-lot engine was introduced.

## Regression Results

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak2_pycache python3 -m compileall src/ai_fund_lab_v2/strategy
PASS

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak2_pycache python3 -m pytest \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/strategy/test_phase22_j_position_sizing.py -q
106 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak2_pycache python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/strategy/test_phase22_g_runtime_planning.py -q
167 passed
```

AE1 dedicated test file was not present in this workspace. BUY_ADD preservation
was covered through the existing Portfolio Construction, Position Sizing, and
Runtime Planning BUY_ADD regressions.

## Preservation Flags

```text
PHASE29_LOT_CAPITAL_CONVERSION_PRESERVED = YES
PHASE30_W_ONE_LOT_ADMISSION_PRESERVED = YES
PHASE30_S_PC_PS_HANDOFF_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
BUY_ADD_BEHAVIOR_UNCHANGED = YES
SECOND_LOT_PLUS_BEHAVIOR_UNCHANGED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

No Historical outcome was used as runtime input or for parameter selection.

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
FRESH_RUN_EXECUTED_BY_CODEX = NO
```

## Fresh Validation Gate

```text
USER_OPERATED_FRESH_VALIDATION_READY
```

## Recommended Next Task

```text
Phase30-AK3 - Fresh 5-10BD One-Lot Admission / Price-Bias Validation
```
