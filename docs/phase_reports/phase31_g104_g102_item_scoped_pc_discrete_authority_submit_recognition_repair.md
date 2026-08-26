# Phase31-G104 - G102 Item-Scoped PC Discrete Authority Submit Recognition Repair

## PRIMARY_JUDGMENT

`PHASE31_G104_G102_ITEM_SCOPED_PC_DISCRETE_AUTHORITY_SUBMIT_RECOGNITION_REPAIRED_ACCEPTED`

G104 repairs only the G103 primary anchor defect:

```text
G97/G99/G102 reconsideration BUY
-> PC discrete executable quantity authority PASS
-> PS consumes exact quantity
-> Runtime BUY
-> Pending BUY with embedded PC authority PASS
-> Submit REVIEW_REQUIRED
   reason = pc_discrete_quantity_authority_lot_overshoot_unresolved
```

Submit now recognizes:

```text
lot_overshoot_reason =
G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY
```

as resolved only when the complete item-scoped PC discrete executable quantity authority contract is valid. The reason string alone is never sufficient.

No fresh-run, resume, replay, or long Historical was executed.

## Changed Boundary

Changed file:

```text
src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py
```

The repair is limited to Submit's `canonical_discrete_quantity_submit_authority` consumer.

Submit still requires:

```text
pc_positive_executable_quantity_authority.status = PASS
authority_type = PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
future_information_used = false
ps_must_consume_canonical_quantity = true
semantic_type in BUY_NEW / REENTRY / BUY_ADD
item quantity == authorized quantity
PS final quantity == authorized quantity when present
final_allocated_quantity == authorized quantity
executable_quantity_delta == authorized quantity
preflight_executable_quantity_delta == authorized quantity
strategy_cap_preserved = true
safety_hard_cap_preserved = true
one_lot_feasibility_status = PASS
```

For G102 recognition specifically, Submit additionally requires canonical G61 lot-aware compatibility context:

```text
schema_version = portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1
owner = PORTFOLIO_CONSTRUCTION
compatibility_state = LOT_EXECUTABLE_COMPATIBLE
future_information_used = false
historical_outcome_used = false
position_sizing_quantity_authority_preserved = true
pc_quantity_authority = false
projected_quantity_delta_evidence_only == authorized quantity
trading_unit > 0
reference_price > 0
portfolio_value > 0
```

If any condition fails, existing `REVIEW_REQUIRED` fail-closed behavior remains.

## Explicit Non-Changes

```text
G90_CHANGED = NO
G97_CHANGED = NO
G99_CHANGED = NO
G102_PRODUCER_CHANGED = NO
PS_QUANTITY_AUTHORITY_CHANGED = NO
RUNTIME_PRIORITY_CHANGED = NO
MARKET_QUALITY_CHANGED = NO
RISK_PACING_CHANGED = NO
SAFETY_CHANGED = NO
ADD_COMPETITION_CHANGED = NO
UNRESOLVED_17_RUNTIME_TO_PENDING_ROWS_TOUCHED = NO
```

Submit does not infer authority from PS quantity alone, Runtime quantity alone, G97 provenance, or aggregate PC allocation.

## Tests Added

Updated:

```text
tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
```

New focused positive case:

```text
test_phase31_g104_accepts_g102_item_scoped_pc_discrete_authority
```

This models the G103 primary anchor shape:

```text
2023-03-22 / 94320 / BUY_NEW / 200
PC authority PASS
G61 LOT_EXECUTABLE_COMPATIBLE
PS quantity 200
Pending quantity 200
Submit canonical_discrete_quantity_submit_authority PASS
```

New fail-closed negative coverage:

```text
authority status != PASS
item quantity != authorized quantity
PS quantity mismatch
future_information_used = true
ps_must_consume_canonical_quantity = false
invalid semantic_type
strategy_cap_preserved = false
safety_hard_cap_preserved = false
one_lot_feasibility_status != PASS
arbitrary unknown lot_overshoot_reason
lot-infeasible G61 compatibility
```

## SoT Update

Updated:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
```

Permanent G104 semantic added:

```text
G102 item-scoped PC discrete executable quantity authority is a valid resolved
Submit discrete-quantity reason only when the full item-scoped authority
invariants are satisfied. The string/reason alone is never sufficient.
```

## Focused Regression Results

G104 / normal PC discrete / normal overshoot Submit tests:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  -k 'g104 or ak9r1b or ak9r21'

20 passed, 20 deselected
```

G102/G97/G95/G61/G62/G63 plus Submit, excluding one unavailable old artifact anchor:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py \
  tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py \
  tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py \
  tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py \
  -k 'not actual_20230322'

63 passed, 1 deselected
```

G90/G86/G83/G81/ADD/Safety-adjacent focused coverage:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py \
  tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py \
  tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py \
  tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  -k 'g104 or ak9r1b or ak9r21 or g90 or g86 or g83 or g81 or add or safety'

42 passed, 20 deselected
```

One broader G102 command initially produced a single unrelated fixture failure:

```text
tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py::test_phase31_g102_actual_20230322_94320_reconsideration_gets_item_scoped_pc_authority
FileNotFoundError:
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260824T203644021876Z/...
```

The referenced run artifact is not present in this workspace. The failure is not caused by G104 behavior and was isolated with the `not actual_20230322` focused run above.

## Compile / Diff Checks

Initial `py_compile` without cache override failed because macOS Python attempted to write bytecode under `~/Library/Caches`, outside the writable sandbox.

Re-run with tmp pycache:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py

PASS
```

```text
git diff --check
PASS
```

## Required Final Judgments

```text
G102_SUBMIT_RECOGNITION_REPAIRED = YES
20230322_94320_SUBMIT_AUTHORITY_PASS = YES in focused Pending/Submit G104 harness

SUBMIT_FAIL_CLOSED_WEAKENED = NO
SUBMIT_QUANTITY_REDECISION = NO
NORMAL_BUY_SUBMIT_CONTRACT_CHANGED = NO

ARBITRARY_OVERSHOOT_REASON_ACCEPTED = NO
LOT_INFEASIBLE_FALSE_PASS_COUNT = 0
SAFETY_FALSE_PASS_COUNT = 0
QUANTITY_MISMATCH_FALSE_PASS_COUNT = 0

G90_CHANGED = NO
G97_CHANGED = NO
G99_CHANGED = NO
G102_PRODUCER_CHANGED = NO
PS_QUANTITY_AUTHORITY_CHANGED = NO
RUNTIME_PRIORITY_CHANGED = NO

FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_INPUT_COUNT = 0
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO

G104_ACCEPTED = YES
```

## Next

G104 does not address the separate G103/G101 residual population:

```text
UNEXPLAINED_RUNTIME_TO_SUBMIT_ROWS = 17
```

Those rows remain a separate Runtime-to-Pending materialization/visibility issue and should be handled in a later, narrow task if still material after the next user-operated validation.
