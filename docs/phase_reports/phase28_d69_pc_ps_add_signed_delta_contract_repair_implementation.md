# Phase28-D69 PC/PS ADD Signed-Delta Contract Repair Implementation

## Judgment

Primary Judgment:

```text
PHASE28_D69_PC_PS_ADD_SIGNED_DELTA_CONTRACT_REPAIR_IMPLEMENTED_EXACT_REPAIR_PASS_FULL_RELEVANT_REGRESSION_FAILED
```

D69 implemented the D68-approved production-common PC/PS ADD signed-delta contract repair. The exact D67 2023-05-09 / 76470 reproduction now passes as a valid zero ADD transaction. However, the full relevant regression set still has one open Strategy Planning Authority no-action empty pending failure, so the resume gate is not approved yet.

## Root Cause Repaired

Root cause repaired:

```text
YES
```

Changed implementation behavior:

```text
Position Sizing _raw_position ADD branch no longer consumes signed
target_weight_change via _ratio as executable ADD authority.
```

The ADD branch now relies on the already-resolved positive-only transaction delta lineage:

```text
1. lot_aware_accepted_incremental_weight
2. target_weight_resolution.lot_aware_final_reallocation.accepted_lot_increment_weight
3. accepted_incremental_weight
4. max(target_weight - current_weight, 0)
```

`target_weight_change` remains signed observability:

```text
YES
```

## Changed Files

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
tests/strategy/test_phase22_j_position_sizing.py
docs/phase_reports/phase28_d69_pc_ps_add_signed_delta_contract_repair_implementation.md
reports/phase_reports/phase28_d69_pc_ps_add_signed_delta_contract_repair_implementation.json
reports/phase28_d69_pc_ps_add_signed_delta_contract_repair_implementation/
docs/01_requirements/phase_roadmap.md
```

No Portfolio Construction, Runtime Planning, Strategy Planning Authority, Pending, Submit Guard, broker, config, schema, threshold, model, or Accepted Generation change was made.

## Exact 76470 Reproduction

Fixture:

```text
symbol = 76470
PM action = ADD
current_weight = 0.182409
target_weight = 0.18
post_add_target_weight = 0.18
target_weight_change = -0.002409
accepted_incremental_weight = 0
lot_aware_accepted_incremental_weight = 0
```

Observed after repair:

```text
Position Sizing = PASS
weight_delta = -0.002409
transaction_delta_weight = 0
transaction_quantity_candidate = 0
target_quantity_candidate = 6900
quantity_delta_candidate = 0
quantity_status = RESOLVED_ZERO_DELTA
ADD_TARGET_WEIGHT_UNCHANGED present
ADD_POSITIVE_QUANTITY_DELTA absent
```

Runtime Planning zero-delta regression also passed:

```text
existing ADD + quantity_delta_candidate = 0
→ NO_ACTION
```

## Preservation

Positive BUY_ADD preserved:

```text
YES
```

Above-cap ADD resolves zero/no-action:

```text
YES
```

REDUCE preserved:

```text
YES
```

EXIT preserved:

```text
YES
```

BUY_NEW preserved:

```text
YES
```

BUY / SELL independence preserved:

```text
YES
```

D61 preserved:

```text
YES
```

D63 preserved:

```text
YES
```

Fail-closed preserved:

```text
YES
```

Genuinely unresolved quantity still fails closed in Strategy Planning Authority.

## Validation

Focused regression:

```text
PASS
```

Executed:

```text
Position Sizing focused D69/D61/D36/D55/D31/C: 16 passed
Position Sizing full file: 62 passed
Portfolio Construction focused: 14 passed
Runtime Planning focused: 15 passed
Strategy Planning Authority unresolved fail-closed focused: 2 passed
Exact D67 reproduction + Runtime NO_ACTION + SPA unresolved fail-closed: 3 passed
```

py_compile:

```text
PASS
```

Full relevant regression:

```text
FAIL
115 passed
1 failed
```

Open failure:

```text
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase23_i_valid_no_action_remains_empty_pending_without_legacy_fallback

Expected: NO_ORDER_AUTHORIZED
Observed: REVIEW_REQUIRED
```

This failure is not confirmed as caused by the D69 code hunk. D69 changed only the Position Sizing ADD diagnostic consumption and added the exact signed-delta PS fixture. Still, because the requested full relevant regression is not green, D69 cannot approve the resume gate.

## Runtime / Execution Flags

```text
Config changed = NO
Schema changed = NO
Threshold changed = NO
Model changed = NO
Accepted Generation changed = NO
Runtime mutated = NO
Resume executed = NO
Fresh-run executed = NO
Long Historical executed = NO
```

## Resume / D66

D66 status:

```text
WAITING
```

Resume allowed after D69:

```text
NO
```

Fresh-run required after D69:

```text
NO
```

D67/D68 allowed resume only after D69 short regression PASS. Because one full relevant regression remains open, do not proceed to the resume gate yet.

## Next Phase

```text
Phase28-D70A Strategy Planning Authority no-action empty pending regression triage before resume gate
```

After that open regression is triaged or fixed and short validation is green, the resume gate can be reconsidered.
