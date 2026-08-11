# Phase29-L19 - Cap-Constrained Lot Floor and Iterative Residual Reallocation Implementation

## 0. Summary

Task ID: Phase29-L19

Mode:

```text
IMPLEMENTATION + SHORT REGRESSION ONLY
```

Primary Judgment:

```text
PHASE29_L19_CAP_CONSTRAINED_LOT_FLOOR_AND_ITERATIVE_RESIDUAL_REALLOCATION_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_HISTORICAL_REQUIRED
```

Root Cause addressed:

```text
YES
```

Implemented the Phase29-L18 Option 5 design as additive Production-common
Strategy evidence and lot-aware allocation behavior. The implementation does
not force deployment and does not turn the 25% Safety hard maximum into a normal
allocation target.

## 1. Implementation

Changed files:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
src/ai_fund_lab_v2/strategy/portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
tests/strategy/test_phase22_e_portfolio_construction.py
docs/01_requirements/phase_roadmap.md
```

Position Sizing now materializes `phase29_l19_lot_resolution` in lot feasibility
preflight rows. It separates:

```text
strategy_cap_weight
safety_hard_cap_weight
remaining_strategy_headroom
remaining_safety_headroom
one_lot_notional
one_lot_weight
minimum_policy_lots
maximum_strategy_feasible_lots
maximum_safety_feasible_lots
requested_lots
executable_lots
executable_quantity_delta
boundary_classification
```

Portfolio Construction now carries the L19 lot resolution into lot-aware final
reallocation evidence and per-member fields:

```text
phase29_l19_lot_resolution
phase29_l19_allocation_iterations
phase29_l19_cap_constrained_lot_floor_enabled
phase29_l19_strategy_safety_cap_separated
phase29_l19_reallocation_iterations
phase29_l19_residual_recycled_weight
phase29_l19_candidate_exhaustion_status
```

The existing candidate queue and residual recycling semantics are preserved.
When a candidate is blocked, the remaining budget continues to the next eligible
Opportunity Cost participant. If all candidates are exhausted, Cash remains
valid with explicit evidence.

## 2. Safety Contract

Strategy cap preserved:

```text
YES
```

Safety hard max preserved:

```text
YES
```

Strategy cap / Safety cap authority separated:

```text
YES
```

The implementation does not set `effective_cap = 25%`. It records Safety hard
headroom separately and keeps normal executable allocation constrained by the
Strategy cap. Safety hard breach cases are classified explicitly.

Forced deployment introduced:

```text
NO
```

## 3. Semantics Preservation

```text
BUY_ADD semantics changed: NO
ADD weakened: NO
BUY_NEW eligibility semantics changed: NO
SELL semantics changed: NO
REDUCE semantics changed: NO
EXIT semantics changed: NO
L7 SELL quantity contract preserved: YES
L16 low-price guard preserved: YES
L16 liquidity cap preserved: YES
L16 REENTRY preserved: YES
Opportunity Cost preserved: YES
Dynamic Capital preserved: YES
Cash Exposure Authority preserved: YES
Compound Capital preserved: YES
```

No Runtime, Pending, Ledger, quarantine, fresh-run, resume, or Historical state
was mutated.

## 4. Regression

Focused L19 tests:

```text
6 passed
```

Portfolio Construction + Position Sizing full focused files:

```text
149 passed
```

L16 + L7 SELL focused regression:

```text
18 passed
```

Compile:

```text
py_compile PASS
```

Diff check:

```text
git diff --check PASS
```

Historical / fresh-run / resume:

```text
NOT EXECUTED
```

## 5. Mandatory Final Fields

```text
Primary Judgment:
PHASE29_L19_CAP_CONSTRAINED_LOT_FLOOR_AND_ITERATIVE_RESIDUAL_REALLOCATION_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_HISTORICAL_REQUIRED

Root Cause addressed:
YES

Cap-constrained lot floor implemented:
YES

Iterative residual reallocation implemented:
YES

Strategy cap preserved:
YES

Safety hard max preserved:
YES

Strategy cap / Safety cap authority separated:
YES

BUY_ADD semantics changed:
NO

ADD weakened:
NO

BUY_NEW eligibility semantics changed:
NO

SELL semantics changed:
NO

REDUCE semantics changed:
NO

EXIT semantics changed:
NO

L7 SELL quantity contract preserved:
YES

L16 low-price guard preserved:
YES

L16 liquidity cap preserved:
YES

L16 REENTRY preserved:
YES

Opportunity Cost preserved:
YES

Dynamic Capital preserved:
YES

Cash Exposure Authority preserved:
YES

Compound Capital preserved:
YES

Forced deployment introduced:
NO

Historical-only Strategy introduced:
NO

Future leakage introduced:
NO

Production code changed:
YES

Strategy code changed:
YES

Runtime code changed:
NO

Config changed:
NO

Schema changed:
NO

Runtime mutated:
NO

Pending mutated:
NO

Ledger mutated:
NO

Historical executed:
NO

Fresh-run executed:
NO

Resume executed:
NO

Short regression:
PASS

Fresh-run required after implementation:
YES

Recommended next task:
Operator-run fresh Historical validation from 2022-08-10 to 2026-08-09, followed by Phase29-L20 read-only effect attribution and execution-HALT separation audit if needed.
```

## 6. Deliverables

```text
docs/phase_reports/phase29_l19_cap_constrained_lot_floor_iterative_residual_reallocation_implementation.md
reports/phase29_l19_cap_constrained_lot_floor_iterative_residual_reallocation_implementation/evidence_manifest.md
```
