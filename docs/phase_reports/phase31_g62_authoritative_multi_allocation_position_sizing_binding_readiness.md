# Phase31-G62 — Authoritative Multi-Allocation / Position Sizing Binding Readiness

## Primary Judgment

PHASE31_G62_AUTHORITATIVE_MULTI_ALLOCATION_POSITION_SIZING_BINDING_READY_ACCEPTED

Position Sizing can now explicitly consume G61
`portfolio_construction.lot_aware_allocation_to_sizing_compatibility.v1`
evidence without taking over capital priority authority or allowing lower-
priority implicit promotion.

## Scope

Implemented PS-side consumption and validation only.

Unchanged:

- Candidate ranking / eligibility authority
- Market Quality / Risk Pacing semantics
- Position Sizing discrete quantity ownership
- PC remains not the final quantity owner
- BUY / SELL independence
- Runtime order behavior
- Threshold / weight / Historical outcome-derived parameters

No fresh run, resume, replay, or long Historical was executed.

## Implementation

Changed:

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase31_g62_position_sizing_g61_binding.py`

Position Sizing now emits:

- `position_sizing.g61_lot_aware_compatibility_consumption.v1`
- `g61_lot_aware_compatibility_consumption`

The consumption summary records:

- `g61_compatibility_consumed_by_ps`
- unresolved higher-priority allocation count
- lower-priority rows requiring explicit residual resolution
- residual capital carried through PS
- capital conservation evidence
- ADD compatibility
- no PS capital-priority recomputation
- no ordinary lot-feasibility priority redecision

Each sizing row with matching G61 evidence receives:

- `g61_lot_aware_compatibility_consumed_by_ps`
- `g61_lot_aware_compatibility`
- `lower_priority_implicit_promotion_allowed = False`
- `position_sizing_recomputes_capital_priority = False`
- `ordinary_lot_feasibility_priority_redecision_allowed = False`

## Fail-Closed Behavior

PS blocks if G61 compatibility evidence is present but malformed:

- missing compatibility payload
- schema mismatch
- date mismatch
- invalid authority status
- malformed compatibility rows
- lower-priority implicit promotion not explicitly prohibited
- residual capital not explicit
- PC quantity authority asserted
- PS quantity authority not preserved

Legacy / pre-G61 summaries remain compatible as
`NOT_AVAILABLE_LEGACY_COMPATIBILITY`.

## Real-PIT Sanity

Source run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z`

Window:

- `2022-10-03` through `2022-10-19`
- 12 business dates

Method:

Existing PIT artifacts were read only. Current G61 PC compatibility evidence was
rebuilt in memory from same-date PC draft members and same-date PS sizing
context, then consumed by current Position Sizing in memory. No artifact was
mutated.

Results:

- Dates evaluated: `12`
- PS PASS dates: `12`
- PS REVIEW dates: `0`
- PS BLOCK dates: `0`
- G61 consumption PASS dates: `12`
- G61 consumption BLOCK dates: `0`
- Allocation rows consumed by PS: `126`
- Raw priority inversion dates: `11`
- Post-PS implicit promotion dates: `0`
- Multi-executable dates: `11`
- ADD rows: `5`
- ADD compatibility failures: `0`
- Runtime order behavior change count: `0`
- Future input count: `0`
- Historical outcome input count: `0`

Representative residual propagation:

| Date | Consumption | Rows Requiring Explicit Residual Resolution | Residual Capital Weight |
| --- | --- | ---: | ---: |
| `2022-10-03` | PASS | 14 | `0.490919` |
| `2022-10-04` | PASS | 14 | `0.433601` |
| `2022-10-05` | PASS | 9 | `0.192831` |
| `2022-10-06` | PASS | 3 | `0.133542` |
| `2022-10-07` | PASS | 4 | `0.089754` |

Interpretation:

G60/G61 raw lot facts still exist, but they now reach PS as explicit residual
and unresolved-priority evidence. PS does not reinterpret ordinary lot
feasibility as capital priority and does not silently promote lower-ranked
securities.

## Acceptance

G61_COMPATIBILITY_CONSUMED_BY_PS = YES

LOWER_PRIORITY_IMPLICIT_PROMOTION = NO

PRIORITY_SEMANTICS_PRESERVED_THROUGH_PS = YES

RESIDUAL_CAPITAL_EXPLICIT_THROUGH_PS = YES

PS_DISCRETE_QUANTITY_AUTHORITY_PRESERVED = YES

PC_DISCRETE_QUANTITY_AUTHORITY = NO

EXECUTABLE_MULTI_SECURITY = YES

ADD_COMPATIBILITY = PASS

CAPITAL_CONSERVATION = PASS

MARKET_QUALITY_SEMANTICS_CHANGED = NO

RUNTIME_ORDER_BEHAVIOR_CHANGE = 0

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_STRATEGY_INPUT_COUNT = 0

## Focused Regression

Command:

`PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py tests/strategy/test_phase31_g57_multi_allocation_shadow.py tests/strategy/test_phase22_j_position_sizing.py`

Result:

`121 passed in 2.35s`

## Py Compile

Command:

`PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Result:

PASS

## Required Flags

PHASE31_CONTINUES = YES

CANDIDATE_RANKING_AUTHORITY_CHANGED = NO

CANDIDATE_ELIGIBILITY_AUTHORITY_CHANGED = NO

MARKET_QUALITY_RISK_PACING_CHANGED = NO

PS_DISCRETE_QUANTITY_AUTHORITY_PRESERVED = YES

PC_FINAL_QUANTITY_OWNER = NO

BUY_SELL_INDEPENDENCE_PRESERVED = YES

FUTURE_INFORMATION_USED = NO

HISTORICAL_OUTCOME_PARAMETER_SELECTION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Next

PHASE31_G63_PC_PS_RUNTIME_EXECUTABLE_DECISION_BINDING_E2E_ACCEPTANCE

Proceed to E2E acceptance only after confirming Runtime can consume the PS
binding evidence without reintroducing an independent capital-priority decision.
