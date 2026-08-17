# Phase30-AK3R1 - Submit Feasibility Minimum Executable One-Lot Authority Handoff Repair

Task ID: `Phase30-AK3R1`

Type: `FOCUSED_IMPLEMENTATION_REPAIR`

## Primary Judgment

```text
SUBMIT_FEASIBILITY_MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY_HANDOFF_REPAIRED
```

The AK3R0 root cause is repaired in the Production-common path. Canonical
AK2 `PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION` evidence is
now consumable by Runtime position sizing authority and Submit feasibility.

## Implemented Repair

Changed files:

```text
src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py
src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py
tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
```

Runtime `PositionSizingAuthority` now recognizes AK2 minimum executable one-lot
authority only when all required guards are present:

```text
authority_type = PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION
decision = ADMIT
reason = MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED
intent in BUY_NEW / REENTRY
current quantity = 0
final quantity = exactly one lot
one-lot notional matches canonical lot evidence
Strategy cap preserved
Safety hard cap preserved
lot feasibility PASS
```

Submit feasibility now verifies item-level consistency before accepting
selected-position overshoot:

```text
item symbol matches authority
item quantity equals authorized one-lot quantity
strategy executable notional equals authorized one-lot notional
authority decision remains ADMIT
Strategy/Safety preservation evidence remains valid
```

If the authority is absent or inconsistent, existing `REVIEW_REQUIRED` behavior
is preserved.

## Sentinel Results

```text
Authorized AK2 one-lot overshoot -> PASS
Same overshoot without authority -> REVIEW_REQUIRED
Tampered symbol authority -> REVIEW_REQUIRED
More than one lot with AK2 authority -> REVIEW_REQUIRED
Legacy normal BUY within selected amount -> PASS
Mixed legacy BUY + authorized AK2 one-lot batch -> PASS
Existing atomic batch protection -> PRESERVED
```

## Preservation

```text
AK2_MINIMUM_ONE_LOT_AUTHORITY_PRESERVED = YES
NORMAL_BUY_SUBMIT_FEASIBILITY_PRESERVED = YES
UNAUTHORIZED_NOTIONAL_OVERSHOOT_REVIEW_PRESERVED = YES
ATOMIC_BUY_BATCH_PROTECTION_PRESERVED = YES
BUY_ADD_BEHAVIOR_UNCHANGED = YES
SECOND_LOT_PLUS_BEHAVIOR_UNCHANGED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
```

## Required Final Judgments

```text
SUBMIT_FEASIBILITY_ONE_LOT_HANDOFF_REPAIRED = YES
AUTHORIZED_ONE_LOT_SELECTED_AMOUNT_OVERSHOOT_ACCEPTED = YES
UNAUTHORIZED_OVERSHOOT_REVIEW_PRESERVED = YES
NORMAL_BUY_SUBMISSION_PRESERVED = YES
ATOMIC_BATCH_AK2_REGRESSION_REPAIRED = YES
AK2_AUTHORITY_END_TO_END_CONSUMABLE = YES
BUY_ADD_BEHAVIOR_UNCHANGED = YES
```

## Tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r1_pycache python3 -m compileall \
  src/ai_fund_lab_v2/runtime_v2 src/ai_fund_lab_v2/strategy
PASS

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r1_pycache python3 -m pytest \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
20 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r1_pycache python3 -m pytest \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/runtime_v2/test_phase26_step6_submit_guard_authority.py -q
42 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r1_pycache python3 -m pytest \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/strategy/test_phase22_g_runtime_planning.py -q
154 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r1_pycache python3 -m pytest \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
39 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r1_pycache python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q
119 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r1_pycache python3 -m pytest \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py -q
117 passed
```

## Historical Runs

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Deliverables

```text
docs/phase_reports/phase30_ak3r1_submit_feasibility_minimum_executable_one_lot_handoff_repair.md
reports/phase_reports/phase30_ak3r1_submit_feasibility_minimum_executable_one_lot_handoff_repair.json
```

## Recommended Next Task

```text
Phase30-AK3R2 - Fresh 5-10BD Post-AK3R1 Zero-BUY / One-Lot Submit Validation
```
