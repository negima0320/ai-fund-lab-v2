# Phase28-D31: Position Sizing Existing-Position Baseline and Transaction-Delta Repair Implementation

## Primary Judgment

```text
PHASE28_D31_POSITION_SIZING_EXISTING_BASELINE_TRANSACTION_DELTA_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
```

Restart Entry:

```text
APPROVED
```

## Implemented Repair

D31 implemented only the D30 Option D repair in `src/ai_fund_lab_v2/strategy/position_sizing.py`.

Existing-position sizing now separates:

```text
existing baseline quantity

from

incremental transaction delta
```

The previous failure mode was that Position Sizing applied BUY Quality and minimum meaningful notional logic to the whole existing-position target. That could turn an authoritative HOLD / ADD baseline into a synthetic negative quantity delta. D31 changes that behavior for existing positions only.

## Contract

Existing HOLD:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
quality_adjustment_scope = NOT_APPLIED_TO_EXISTING_BASELINE
```

Existing ADD with zero accepted increment:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
minimum_meaningful_notional_applied_to = TRANSACTION_DELTA_NOTIONAL
```

Existing ADD with positive accepted increment:

```text
baseline_quantity = current_quantity
transaction_quantity_candidate = lot-rounded accepted incremental transaction
quantity_delta_candidate = transaction_quantity_candidate
```

Existing ADD with tiny increment:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
reason = ADD_INCREMENT_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT
```

BUY_NEW keeps the existing total-target sizing path:

```text
quality_adjustment_scope = BUY_NEW_TOTAL_TARGET
minimum_meaningful_notional_applied_to = TOTAL_TARGET_NOTIONAL
```

REDUCE / EXIT / UNRESOLVED behavior is preserved:

```text
REDUCE -> partial negative delta when explicitly lower target is executable
EXIT -> full negative delta only under PM EXIT / remove authority
UNRESOLVED -> no implicit EXIT
```

## Changed Files

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase28_d31_position_sizing_existing_position_baseline_and_transaction_delta_repair_implementation.md`
- `reports/phase_reports/phase28_d31_position_sizing_existing_position_baseline_and_transaction_delta_repair_implementation.json`
- `reports/phase28_d31_position_sizing_existing_position_baseline_and_transaction_delta_repair_implementation/`

## Focused Results

| Check | Result |
| --- | --- |
| 83060 HOLD quality reject baseline | PASS |
| 94320 ADD zero increment baseline | PASS |
| Existing ADD positive increment | PASS |
| Existing ADD tiny increment | PASS |
| REDUCE partial negative delta | PASS |
| EXIT full negative delta | PASS |
| UNRESOLVED no implicit EXIT | PASS |
| BUY_NEW unchanged | PASS |
| Phase28-C ADD positive delta | PASS |
| Phase28-C ADD lot-zero regression | PASS |
| D12 / D19 PM ADD propagation selected regression | PASS |
| D25 SELL authority selected regression | PASS |
| D28 incremental budget selected regression | PASS |
| D8 / D3 pending regression | PASS |
| Compile | PASS |

## Validation Commands

```text
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q
```

Result:

```text
44 passed
```

```text
python3 -m pytest tests/strategy/test_phase22_d_position_management.py::test_phase28_d12_runtime_current_adapter_reads_runtime_pm_decision_type tests/strategy/test_phase22_d_position_management.py::test_phase28_d19_runtime_current_adapter_records_same_day_pm_source_evidence tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d28_20230404_incremental_budget_reconciliation_reproduction tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d28_add_sufficient_budget_still_increases_existing_position tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d28_zero_capacity_add_retains_baseline_without_sell tests/strategy/test_phase22_g_runtime_planning.py::test_phase28_d25_runtime_planning_blocks_target_zero_sell_exit_without_pm_exit_authority tests/strategy/test_phase22_g_runtime_planning.py::test_phase28_d25_runtime_planning_preserves_pm_exit_to_sell_exit tests/strategy/test_phase22_g_runtime_planning.py::test_phase28_d25_runtime_planning_maps_pm_reduce_to_sell_reduce_not_exit tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_lot_rounding_zero_delta_is_explicit -q
```

Result:

```text
13 passed
```

```text
python3 -m pytest tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
```

Result:

```text
14 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_d31 python3 -m py_compile src/ai_fund_lab_v2/strategy/position_sizing.py tests/strategy/test_phase22_j_position_sizing.py
```

Result:

```text
PASS
```

## Scope Guard

```text
Implementation changed: true
Config changed: false
Schema changed: false
Threshold changed: false
Portfolio Construction changed by D31: false
Runtime Planning changed by D31: false
Submit Guard changed: false
Broker changed: false
Resume executed: false
Fresh run executed: false
Long Historical executed: false
```

## Final Judgment

```text
Primary Judgment: PHASE28_D31_POSITION_SIZING_EXISTING_BASELINE_TRANSACTION_DELTA_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
Restart Entry: APPROVED
Root Cause repaired: Position Sizing applied BUY Quality / minimum notional to existing baseline instead of transaction delta
83060 result: HOLD baseline quantity preserved
94320 result: ADD zero-increment baseline quantity preserved
BUY_NEW changed: false
REDUCE / EXIT / UNRESOLVED preserved: true
Runtime Authority violation: false
Performance change: false
Repair Required: false
Next Phase: Fresh 100BD re-entry validation
```
