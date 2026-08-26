# Phase31-G66 — Top-Level PC Multi-Allocation Lot Context Publication Repair

## PRIMARY_JUDGMENT

PHASE31_G66_TOP_LEVEL_PC_MULTI_ALLOCATION_LOT_CONTEXT_PUBLICATION_REPAIRED_AND_ACCEPTANCE_COMPLETED

G66 is accepted at the production publication path level.

The original G65 actual-path gap was repaired at the publication boundary:
when a final Portfolio Construction artifact is promoted for production
consumption, the top-level `capital_competition` now publishes the lot-aware
final reallocation `canonical_multi_allocation_deployment_set.v1` evidence
instead of the pre-lot / insufficient-context G61 evidence.

No fresh-run, resume, replay, or Historical execution was performed for this
acceptance completion.

## Actual 1BD Morning HALT Audit

Target run:

```text
runtime-test-historical-extended-smoke-20260823T134411283008Z
```

Target boundary:

```text
2022-10-03:morning
```

Actual result:

```text
fresh_run_summary.status = HALT
fresh_run_summary.exit_code = 30
fresh_run_summary.error = Runtime CLI stopped at 2022-10-03:morning with exit code 10
morning/cli_result.exit_code = 10
morning/planning_evidence.status = BLOCK
morning/planning_evidence.reason = strategy_runtime_planning_blocked
```

Direct cause:

```text
MORNING_HALT_ROOT_CAUSE = strategy_runtime_planning_blocked
```

Concrete causal chain:

```text
portfolio_construction.top_level_capital_competition
-> canonical_multi_allocation_deployment_set.business_date = ""
-> lot_aware_allocation_to_sizing_compatibility.business_date = ""
-> security_allocations = 0
-> lot_executable_count = 0
-> position_sizing.producer_result_status = BLOCK
-> position_sizing.reason_codes = [G61_COMPATIBILITY_DATE_MISMATCH]
-> runtime_planning.producer_result_status = BLOCK
-> runtime_planning.reason_codes include G61_PS_CONSUMPTION_BLOCK
-> morning pipeline blocked: strategy_runtime_planning_blocked
-> exit code 10
```

G66 publication defect causal relation:

```text
G66_PUBLICATION_DEFECT_CAUSAL_RELATION = YES
```

The halted run already contained `pre_lot_capital_competition` and
`G66_LOT_AWARE_MULTI_ALLOCATION_PUBLISHED_TOP_LEVEL`, but its top-level
published multi-allocation evidence was still empty / date-unbound. PS
therefore correctly fail-closed on `G61_COMPATIBILITY_DATE_MISMATCH`.

## Implementation Summary

Changed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py`
- `tests/strategy/test_phase31_g62_position_sizing_g61_binding.py`
- `tests/strategy/test_phase31_g66_publication_path_integration.py`

Key repair:

- `promote_final_portfolio_construction_for_production()` replaces production
  top-level `capital_competition` with
  `lot_aware_final_reallocation.capital_competition` when final reallocation is
  PASS.
- The previous top-level competition is preserved as
  `pre_lot_capital_competition`.
- The production artifact persists
  `G66_LOT_AWARE_MULTI_ALLOCATION_PUBLISHED_TOP_LEVEL`.
- PS preserves executable multi-allocation rows from G61 compatibility and does
  not let legacy SINGLE cash-winner evidence zero them.

This remains a publication / connectivity repair only.

## Focused Integration Regression

Permanent regression added:

```text
tests/strategy/test_phase31_g66_publication_path_integration.py
```

The test uses existing 2022-10-03 PIT artifacts from the halted run and writes
only temporary test artifacts under `tmp_path`. It does not invoke any runtime
fresh-run, resume, replay, or Historical execution.

Path exercised:

```text
final PC production promotion
-> top-level canonical_multi_allocation_deployment_set
-> G61 compatibility
-> Position Sizing
-> Runtime Planning
```

Assertions covered:

- top-level PC publishes lot-aware final G61, not pre-lot G61
- G61 lot executable rows > 0
- PS positive quantity rows > 0
- Runtime BUY_NEW / BUY_ADD planned quantity rows > 0
- lower-priority implicit promotion = 0
- PS quantity authority preserved
- Market Quality semantics unchanged

## Validation

Focused G66 integration:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g66_publication_path_integration.py
```

Result:

```text
1 passed
```

Focused G61/G62/G66 regression:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g66_publication_path_integration.py tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py
```

Result:

```text
10 passed
```

Python compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-g66 PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py tests/strategy/test_phase31_g66_publication_path_integration.py
```

Result:

```text
PASS
```

Note: a first `py_compile` attempt without `PYTHONPYCACHEPREFIX` failed because
macOS Python tried to write `.pyc` files under `/Users/negishi/Library/Caches`,
which is outside the writable sandbox. The compile check passed after directing
the cache to `/private/tmp`.

## Acceptance Fields

MORNING_HALT_ROOT_CAUSE = CONFIRMED

G66_PUBLICATION_PATH_INTEGRATION = PASS

G61_LOT_EXECUTABLE_GT_0 = YES

PS_POSITIVE_QUANTITY_GT_0 = YES

RUNTIME_BUY_PLAN_GT_0 = YES

LOWER_PRIORITY_IMPLICIT_PROMOTION = 0

PS_QUANTITY_AUTHORITY_PRESERVED = YES

MARKET_QUALITY_SEMANTICS_CHANGED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_INPUT_COUNT = 0

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Preserved Semantics

Market Quality / Risk Pacing semantics changed: NO

Candidate ranking / eligibility changed: NO

Threshold / weight / allocation tuning introduced: NO

PC remains capital allocation owner: YES

PS remains discrete quantity owner: YES

Runtime capital priority redecision introduced: NO

BUY / SELL independence changed: NO

Safety semantics changed: NO

## Recommendation

G66 acceptance completion is satisfied.

Next operator action can proceed to the user-operated fresh long Historical
gate, with the explicit regression requirement that actual bootstrap BUY
materialization remains covered by
`tests/strategy/test_phase31_g66_publication_path_integration.py`.
