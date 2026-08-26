# Phase31-G63 — PC→PS→Runtime Executable Decision Binding E2E Acceptance

## Primary Judgment

PHASE31_G63_PC_PS_RUNTIME_EXECUTABLE_DECISION_BINDING_E2E_ACCEPTED

G59/G61/G62 の multi-allocation / lot-aware priority semantics now bind through
Runtime Planning executable decision logic.

`LINEAGE PERSISTENCE != EXECUTABLE DECISION BINDING` was treated as the primary
acceptance principle. G63 adds executable-decision guards, not only lineage.

## Scope

Implemented the minimum Runtime Planning binding needed to consume PS-side G62
evidence.

Unchanged:

- Candidate ranking / eligibility authority
- Market Quality / Risk Pacing semantics
- PC remains capital allocation owner
- PS remains discrete quantity owner
- Runtime does not recompute capital priority
- BUY / SELL independence
- Safety authority
- Runtime order submission / pending / broker behavior
- Threshold / weight / Historical outcome-derived parameters

No fresh run, resume, or long Historical was executed.

## Implementation

Changed:

- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `tests/strategy/test_phase31_g63_runtime_executable_binding.py`

Runtime Planning now emits:

- `runtime_planning.g63_pc_ps_executable_binding.v1`
- `g63_pc_ps_runtime_executable_binding`

For each plan, Runtime records:

- `g63_runtime_binding`
- `g61_lot_aware_compatibility_consumed_by_runtime`
- `runtime_capital_priority_redecision = False`
- `lower_priority_implicit_promotion_runtime = False`
- `cash_winner_redecision_runtime = False`
- `ps_authorized_quantity_reoptimized_by_runtime = False`

## Executable Binding Behavior

Runtime consumes the PS G62 summary:

- `position_sizing.g61_lot_aware_compatibility_consumption.v1`

If PS says a BUY / ADD row is executable only while a higher-priority allocation
still requires explicit residual resolution, Runtime does not allow that row to
become an executable order.

Instead:

- `planning_intent = NO_ORDER`
- `planned_quantity = 0`
- `no_order_reason = G61_EXPLICIT_RESIDUAL_RESOLUTION_REQUIRED`

Runtime does not recalculate the quantity, choose a different security, or move
cash into a different winner.

## Fail-Closed Behavior

Runtime blocks malformed PS-side G61 binding evidence:

- PS G61 consumption `status = BLOCK`
- schema mismatch
- date mismatch
- G61 not actually consumed by PS
- lower-priority implicit promotion not explicitly prohibited
- PC quantity authority asserted
- PS quantity owner invalid
- PS capital-priority recomputation asserted

Legacy / pre-G61 position sizing remains accepted as
`NOT_AVAILABLE_LEGACY_COMPATIBILITY`.

## Focused Production-Equivalent E2E Acceptance

Synthetic production-equivalent chain:

`G61 PC compatibility evidence`
→ `G62 PS quantity decision`
→ `Runtime Planning`
→ `planned BUY / ADD / SELL`

Observed:

- top BUY with no unresolved higher-priority residual planned as `BUY_NEW`
- lower-priority BUY requiring explicit residual resolution became `NO_ORDER`
- another eligible BUY planned as `BUY_NEW`
- existing position positive quantity planned as `BUY_ADD`
- independent SELL reduce planned as `SELL_REDUCE`
- malformed PS G61 date mismatch failed closed

This confirms:

- PS quantity binds Runtime planned quantity
- Runtime does not independently rank or promote BUY candidates
- lower-priority implicit promotion is blocked at executable decision time
- ADD materializes from PS quantity
- SELL remains independent from BUY-side pacing

## Existing PIT Sanity

Source run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z`

Window:

- `2022-10-03` through `2022-10-19`
- 12 business dates

Method:

Existing PIT artifacts were read only. Current PC G61, PS G62, and Runtime G63
logic were applied in memory. No artifact was mutated.

Results:

- Dates evaluated: `12`
- Runtime binding PASS dates: `12`
- Runtime binding BLOCK dates: `0`
- Raw priority inversion dates in PC/G61 compatibility: `11`
- Runtime implicit-promotion dates: `0`
- Future input count: `0`
- Historical outcome input count: `0`

Note:

The existing PIT artifacts still reflect the prior SINGLE authoritative trading
path, so the 2022-10 window did not produce real multi-security BUY plans in
that read-only replay. Multi-security Runtime planning and ADD materialization
were therefore accepted via the focused production-equivalent E2E test above,
while existing PIT verified binding compatibility and no implicit promotion.

## Acceptance

PC_PS_RUNTIME_EXECUTABLE_BINDING = PASS

PS_QUANTITY_BINDS_RUNTIME = YES

RUNTIME_CAPITAL_PRIORITY_REDECISION = NO

LOWER_PRIORITY_IMPLICIT_PROMOTION_RUNTIME = NO

CASH_WINNER_REDECISION_RUNTIME = NO

MULTI_SECURITY_RUNTIME_PLANNING = YES

ADD_RUNTIME_BINDING = PASS

SELL_BUY_INDEPENDENCE = PASS

CAPITAL_CONSERVATION = PASS

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_STRATEGY_INPUT_COUNT = 0

## Focused Regression

Command:

`PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py tests/strategy/test_phase31_g57_multi_allocation_shadow.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase22_j_position_sizing.py`

Result:

`171 passed in 2.82s`

## Py Compile

Command:

`PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/runtime_planning.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Result:

PASS

## Required Flags

PHASE31_CONTINUES = YES

CANDIDATE_RANKING_AUTHORITY_CHANGED = NO

CANDIDATE_ELIGIBILITY_AUTHORITY_CHANGED = NO

MARKET_QUALITY_RISK_PACING_CHANGED = NO

PC_CAPITAL_ALLOCATION_OWNER = YES

PS_DISCRETE_QUANTITY_OWNER = YES

RUNTIME_CAPITAL_PRIORITY_REDECISION = NO

BUY_SELL_INDEPENDENCE_PRESERVED = YES

SAFETY_AUTHORITY_PRESERVED = YES

FUTURE_INFORMATION_USED = NO

HISTORICAL_OUTCOME_PARAMETER_SELECTION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Next

No additional research task is required before user-operated fresh long
Historical.

Proceed to user-run fresh long Historical validation.
