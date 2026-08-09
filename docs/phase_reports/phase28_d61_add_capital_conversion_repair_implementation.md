# Phase28-D61 Production-common ADD Capital Conversion Repair Implementation

## Primary Judgment

```text
PHASE28_D61_ADD_CAPITAL_CONVERSION_REPAIR_IMPLEMENTED_SHORT_VALIDATION_PASS
```

D61 implemented the D60-approved Production-common ADD capital conversion repair. This is not a performance-specific hack and does not force BUY_ADD.

No fresh-run, resume, long historical, production trading execution, config change, schema change, threshold change, Submit Guard change, SELL lifecycle change, D55-A resolver change, Runtime Planning mapping change, D62 pending-safety change, or `BASELINE_CURRENT_SEMANTICS_MISMATCH` repair was performed.

## Changed Files

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
```

## Changed Functions

```text
portfolio_construction._resolve_canonical_add_allocation_bridge
position_sizing._resolved_lot_aware_add_increment
position_sizing._raw_position
```

Focused tests added:

```text
test_phase28_d61_add_current_above_base_target_still_requests_increment_when_eligible
test_phase28_d61_ps_prefers_pc_lot_aware_add_increment_over_pre_lot_increment
```

## Before Semantic

Portfolio Construction:

```text
desired_increment = max(candidate_target_weight - current_weight, 0)
eligible requires desired_increment > 0
```

Therefore, `PM ADD + D55-A PASS` could still produce `request=0` whenever `current_weight >= ordinary base target`.

Position Sizing:

```text
ADD transaction_delta_weight used accepted_incremental_weight first.
```

Therefore, PC final lot-aware positive ADD increments could be recalculated as zero in PS when the pre-lot accepted increment was below minimum executable notional or lot size.

## After Semantic

Portfolio Construction:

```text
add_increment_request = max(candidate_target_weight, 0)
post_add_target = current_weight + add_increment_request
```

The final target remains constrained by:

- D55-A PASS
- expected-edge / incremental value / opportunity cost
- campaign continuation
- no-loss averaging
- broker eligibility
- capital availability
- concentration
- execution feasibility
- single-name cap
- target gross exposure
- incremental budget reconciliation

This repairs target/current collision without creating an unconditional one-lot BUY_ADD rule.

Position Sizing:

```text
ADD transaction_delta_weight now prefers:
1. lot_aware_accepted_incremental_weight
2. target_weight_resolution.lot_aware_final_reallocation.accepted_lot_increment_weight
3. accepted_incremental_weight
4. max(target_weight - current_weight, 0)
```

This preserves PC final lot-aware lineage while keeping PS as final quantity authority.

## Repair Locations

Target/current collision repair:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
_resolve_canonical_add_allocation_bridge
```

Lot-aware reuse:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
apply_lot_aware_final_reallocation
```

No new lot resolver was added. D55-B two-pass primitive remains the lot-aware implementation.

PC -> PS lineage repair:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
_resolved_lot_aware_add_increment
_raw_position
```

## Runtime / Resolver Proof

Runtime Planning mapping:

```text
unchanged in D61
```

Validated by:

```text
test_phase27_d2e_runtime_planning_maps_canonical_quantity_delta_to_runtime_action
test_phase27_d2e_canonical_delta_disables_pm_fallback
```

D55-A resolver:

```text
unchanged in D61
```

D61 consumes existing D55-A evidence through the existing Portfolio Construction bridge and does not change eligibility thresholds or evidence semantics.

## Safety / Threshold / Config Proof

```text
Config changed = NO
Schema changed = NO
Threshold changed = NO
Safety policy changed = NO
Submit Guard changed = NO
Broker changed = NO
SELL lifecycle changed = NO
Pending lifecycle changed = NO
```

Unsafe minimum lot and over-target passive convergence remain fail-closed / preserved through existing tests.

## Regression Results

Focused PC/PS regression:

```text
8 passed
```

Full PC/PS regression:

```text
117 passed
```

Runtime mapping regression:

```text
2 passed
```

Compile/import check:

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile ...
PASS
```

Initial `py_compile` without `PYTHONPYCACHEPREFIX` hit a macOS cache permission error under `~/Library/Caches`; rerun with `/tmp` pycache passed.

## D61 Regression Matrix

Case A, existing ADD / current > base target:

```text
PASS
```

Case B, safe minimum lot:

```text
PASS through existing D55-B lot-aware primitive regression
```

Case C, unsafe minimum lot:

```text
PASS, no forced one-lot behavior
```

Case D, PC positive -> PS positive:

```text
PASS
```

Case E, HOLD / NO_ACTION:

```text
PASS through full PS regression
```

Case F, BUY_NEW:

```text
PASS through D55-B BUY_NEW regression
```

Case G, Runtime mapping:

```text
PASS, Runtime Planning unchanged
```

## Remaining Known Gaps

```text
Fresh 100BD = NOT executed by Codex
Phase28-D62 historical_pending_safety_authority_mismatch = NOT repaired in D61; D63 scope
BASELINE_CURRENT_SEMANTICS_MISMATCH = NOT repaired in D61
```

## Deliverables

- `reports/phase28_d61_add_capital_conversion_repair_implementation/implementation_summary.json`
- `reports/phase28_d61_add_capital_conversion_repair_implementation/semantic_before_after.json`
- `reports/phase28_d61_add_capital_conversion_repair_implementation/lineage_evidence.json`
- `reports/phase28_d61_add_capital_conversion_repair_implementation/validation_results.json`
- `reports/phase28_d61_add_capital_conversion_repair_implementation/regression_matrix.json`
- `reports/phase28_d61_add_capital_conversion_repair_implementation/open_gaps.json`
- `reports/phase_reports/phase28_d61_add_capital_conversion_repair_implementation.json`

## Next Phase Gate

```text
Phase28-D63 = APPROVED
```

D63 should repair the D62-confirmed Production-common Pending Safety EMPTY-terminal false-positive.

## Execution Flags

```text
Implementation changed = YES
Config changed = NO
Schema changed = NO
Threshold changed = NO
Runtime mutated = NO
Resume executed = NO
Fresh run executed = NO
Long Historical executed = NO
```
