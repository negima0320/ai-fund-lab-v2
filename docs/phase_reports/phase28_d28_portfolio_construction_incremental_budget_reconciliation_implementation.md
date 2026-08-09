# Phase28-D28: Portfolio Construction Incremental Budget Reconciliation Implementation

## Status

```text
COMPLETE
```

## Primary Judgment

```text
PHASE28_D28_INCREMENTAL_BUDGET_RECONCILIATION_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
```

## Fresh Test Entry Decision

```text
APPROVED
```

## Implemented Repair

Implemented the single approved Phase28-D27 repair in Portfolio Construction:

```text
baseline_existing_required_weight =
  HOLD current_weight
  + ADD current_weight
  + REDUCE remaining target_weight
  + EXIT 0

available_incremental_budget =
  max(0, target_gross_exposure - baseline_existing_required_weight)

eligible ADD increment and BUY_NEW allocation compete inside the same
available incremental budget.
```

The implementation is in:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
```

The new reconciliation is called after row-local target-weight resolution and
the Phase28-C canonical ADD bridge, before final aggregate target-weight
validation.

## Code Evidence

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py:1022
  calls _reconcile_incremental_budget after target weights are produced.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1049
  defines _reconcile_incremental_budget.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1093
  REDUCE / REMOVE / EXCLUDE baseline handling.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1097
  HOLD / ADD baseline handling from current_weight.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1107
  BUY_NEW incremental request handling.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1133
  baseline_existing_required_weight and available_incremental_budget.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1139
  baseline-over-budget fail-closed branch.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1173
  ADD increment and BUY_NEW shared allocation.

src/ai_fund_lab_v2/strategy/portfolio_construction.py:1227
  member-level reconciliation evidence materialization.
```

## 2023-04-04 Reproduction Fixture

Test:

```text
tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d28_20230404_incremental_budget_reconciliation_reproduction
```

Input reconstruction:

```text
target_gross_exposure = 0.72
43880 HOLD current_weight = 0.123279
83060 ADD current_weight = 0.17231
94320 ADD current_weight = 0.126961
67310 BUY_NEW requested = 0.144
59350 BUY_NEW requested = 0.144
```

Observed result:

```text
baseline_existing_required_weight = 0.42255
available_incremental_budget = 0.29745
accepted_add_increment = 0.0
accepted_buy_new_weight = 0.288
final_target_weight_sum = 0.71055
producer_result_status != BLOCK
```

## Focused Behavior Results

```text
HOLD below equal weight:
PASS - target_weight remains current_weight, no implicit equal-weight increase.

ADD with sufficient budget:
PASS - Phase28-C eligible ADD still increases existing target_weight.

Multiple ADD within budget:
PASS - both eligible ADD increments can be accepted.

Multiple ADD over budget:
PASS - weaker incremental allocation is trimmed/deferred by existing priority.

ADD plus BUY_NEW competition:
PASS - ADD increment and BUY_NEW compete in the same incremental budget.

REDUCE releases capacity:
PASS - REDUCE remaining target participates as baseline and releases capacity.

Zero capacity ADD:
PASS - ADD keeps baseline, accepted_incremental_weight is 0, no SELL escalation.

Baseline over budget:
PASS - fails closed with baseline_existing_required_weight_above_target_gross_exposure.
```

## Regression Results

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py
Result: 34 passed

PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py \
  tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py \
  tests/strategy/test_phase22_g_runtime_planning.py
Result: 73 passed

PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase22_d_position_management.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
Result: 73 passed

PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_d28 \
  python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  tests/strategy/test_phase22_e_portfolio_construction.py
Result: PASS
```

## Compatibility Judgment

```text
Phase28-C ADD bridge preserved: YES
D19 PM ADD actual runtime path preserved: YES
D25 PM intent-preserving SELL authority preserved: YES
Position Sizing boundary preserved: YES
Runtime Planning boundary preserved: YES
Submit Guard unchanged: YES
Broker unchanged: YES
```

## Mutation Flags

```text
implementation_changed = true
config_changed = false
schema_changed = false
threshold_changed = false
performance_threshold_changed = false
resume_executed = false
fresh_run_executed = false
long_historical_executed = false
runtime_authority_violation = false
```

## Changed Files

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
tests/strategy/test_phase22_e_portfolio_construction.py
docs/phase_reports/phase28_d28_portfolio_construction_incremental_budget_reconciliation_implementation.md
reports/phase_reports/phase28_d28_portfolio_construction_incremental_budget_reconciliation_implementation.json
reports/phase28_d28_portfolio_construction_incremental_budget_reconciliation_implementation/
docs/01_requirements/phase_roadmap.md
```

## Open Gaps

```text
No implementation gap found in short validation.
Full 100BD acceptance remains operator-owned and was not executed by Codex.
```

## Next Phase

```text
Phase28-D29 fresh 100BD runtime acceptance and evidence audit.
```
