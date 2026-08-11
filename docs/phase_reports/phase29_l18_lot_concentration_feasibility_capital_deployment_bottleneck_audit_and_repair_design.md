# Phase29-L18 - Lot / Concentration Feasibility Capital Deployment Bottleneck Audit and Repair Design

## 0. Summary

Task ID: Phase29-L18

Mode:

```text
READ_ONLY AUDIT + DESIGN ONLY
```

Run:

```text
runtime-test-historical-smoke-20260811T024356531918Z
```

Audit scope:

```text
2022-08-10 through 2022-08-24
```

Primary Judgment:

```text
PHASE29_L18_DISCRETE_LOT_AND_RESIDUAL_CAPITAL_REALLOCATION_GAPS_CONFIRMED_REPAIR_DESIGN_READY
```

Root Cause confirmed:

```text
YES
```

The root cause is not L16 and not ADD weakening. It is the combination of:

```text
DISCRETE_LOT_CONCENTRATION_BOUNDARY_GAP
RESIDUAL_CAPITAL_RECYCLING_GAP_AT_ALL_CANDIDATES_CONCENTRATION_BLOCKED
```

Continuous Portfolio Construction target weights can be valid at 18%, but one
executable lot can exceed the current 18% strategy concentration cap. The
current lot-aware pass then sets the candidate increment to zero. If all
participants are blocked this way, residual budget is conserved but returns to
Cash.

No implementation was performed in L18.

## 1. Authority Trace

Primary source functions:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
  _apply_target_weight_authority
  apply_lot_aware_final_reallocation

src/ai_fund_lab_v2/strategy/position_sizing.py
  build_lot_feasibility_preflight
  _lot_feasibility_row
  _raw_position
  _minimum_notional
  _lot_quantity

src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
  Runtime Planning consumes Position Sizing quantity_delta_candidate

src/ai_fund_lab_v2/runtime_v2/safety/portfolio_limits.py
  validates Safety hard concentration authority
```

Key authority facts:

```text
Strategy single-name cap: 0.18
Safety hard concentration maximum: 0.25
Effective maximum position weight in Position Sizing: min(0.18, 0.25) = 0.18
Minimum notional policy: max(50,000 JPY, reference_price * 100 shares * 1.02)
Lot quantity: floored to tradable unit
Runtime Planning lot rounding: already applied by Position Sizing
```

Detailed authority table:

```text
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/lot_concentration_authority_trace.csv
```

## 2. BUY_ADD Zero Quantity Root Cause

BUY_ADD zero quantity cases:

```text
4
```

Observed cases:

```text
2022-08-19 94320
2022-08-22 94320
2022-08-23 94320
2022-08-24 94320
```

All four cases are:

```text
CASE_B_DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_BUT_WITHIN_SAFETY_HARD_MAX
```

Example 2022-08-24:

```text
symbol = 94320
semantic_type = BUY_ADD
pm_action = ADD
current_quantity = 900
current_weight = 0.136879
desired_incremental_weight = 0.043121
target_weight_before_lot_adjustment = 0.18
reference_price = 151.3
lot_size = 100
minimum_executable_notional = 50,000
minimum_executable_weight = 0.050128
concentration_cap_weight = 0.18
safety_hard_cap_weight = 0.25
remaining_headroom_weight = 0.043121
one_lot_post_trade_weight = 0.187007
one_lot_within_strategy_cap = NO
one_lot_within_safety_hard_cap = YES
final_quantity_delta = 0
final_reason = minimum_lot_exceeds_concentration_cap
```

Interpretation:

```text
The ADD decision and continuous target are valid, but one executable lot is
larger than the remaining strategy-cap headroom. Current behavior therefore
zeros the ADD increment.
```

Detailed file:

```text
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/buy_add_zero_quantity_cases.csv
```

## 3. BUY_NEW Zero Quantity Root Cause

BUY_NEW zero quantity cases:

```text
3
```

Observed cases:

```text
2022-08-22 78780
2022-08-23 78780
2022-08-24 78780
```

2022-08-24:

```text
symbol = 78780
semantic_type = BUY_NEW
target_weight_before_lot_adjustment = 0.18
target_weight_after_lot_adjustment = 0.0
reference_price = 2420.0
minimum_executable_notional = 246,840
minimum_executable_weight = 0.247471
concentration_cap_weight = 0.18
safety_hard_cap_weight = 0.25
one_lot_post_trade_weight = 0.247471
one_lot_within_strategy_cap = NO
one_lot_within_safety_hard_cap = YES
final_quantity_delta = 0
final_reason = minimum_lot_exceeds_concentration_cap
```

2022-08-22 and 2022-08-23 had one-lot weights above both the 18% strategy cap
and the 25% Safety hard maximum, so they are hard/effective cap blocked. The
2022-08-24 row is the clean discrete boundary case: one lot is above Strategy
cap but below Safety hard maximum.

Conclusion:

```text
This is not BUY_ADD-specific. BUY_NEW shares the same continuous-weight /
discrete-lot boundary.
```

Detailed file:

```text
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/buy_new_zero_quantity_cases.csv
```

## 4. Concentration Semantics

Current concentration authority has two observed layers:

```text
Strategy allocation cap: 0.18
Safety hard concentration maximum: 0.25
```

However, the current effective cap used for allocation and lot feasibility is:

```text
min(strategy_maximum_position_weight, safety_maximum_position_weight) = 0.18
```

Therefore current behavior effectively requires:

```text
post-trade one-lot weight <= 0.18
```

The evidence confirms a discrete-lot / continuous-weight impedance mismatch.
For 94320, continuous target 18% is legal, but one lot would land at 18.4501%
to 18.7007% during the audited dates. That is above Strategy cap but below
Safety hard maximum.

This does not prove that a tolerance should be implemented immediately. It
proves that the current single effective cap collapses a valid continuous target
into zero executable quantity at the discrete boundary.

## 5. Residual Capital Recycling

Residual recycling exists:

```text
YES
```

Evidence:

```text
apply_lot_aware_final_reallocation has a sorted candidate queue,
skipped/promoted/rebatch_allocations evidence, and capital conservation fields.
```

Residual recycling complete:

```text
NO
```

For concentration-blocked days, the pass terminates after all lot-aware
participants are blocked:

```text
2022-08-19 residual_cash_reason = CONCENTRATION_LIMIT
2022-08-22 residual_cash_reason = CONCENTRATION_LIMIT
2022-08-23 residual_cash_reason = CONCENTRATION_LIMIT
2022-08-24 residual_cash_reason = CONCENTRATION_LIMIT
```

The current implementation conserves capital correctly, but does not solve the
case where all eligible candidates have at least one-lot infeasibility under the
18% effective cap. Cash is still valid after candidate exhaustion, but the root
cause should be materialized explicitly as residual capital recycled to all
eligible participants and then retained as Cash.

Detailed files:

```text
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/residual_capital_recycling_audit.csv
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/capital_reallocation_trace.csv
```

## 6. Repair Option Comparison

Recommended repair option:

```text
Option 5 - Hybrid:
Cap-Constrained Lot Floor + Iterative Residual Reallocation
```

Option 5 should include:

```text
1. Compute cap-constrained executable lots using current equity and PIT price.
2. If less than one lot is possible under the active cap, assign zero and recover residual.
3. Recycle residual through a deterministic Opportunity Cost queue.
4. Materialize per-candidate requested, executable, skipped, recycled, and residual evidence.
5. Keep Strategy cap and Safety hard cap separate in evidence.
6. Do not permit Safety hard cap breach.
7. Do not force deployment when no eligible lot-feasible candidate remains.
```

Detailed comparison:

```text
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/repair_option_comparison.md
```

## 7. Design Requirements for L19

Implementation readiness:

```text
DESIGN_READY_FOR_PHASE29_L19_IMPLEMENTATION
```

L19 must preserve:

```text
Production / Demo / Historical common Strategy
PIT-only evidence
ADD and BUY_ADD semantics
BUY_NEW eligibility semantics
SELL / REDUCE / EXIT semantics
L7 SELL quantity contract
L16 low-price / liquidity / REENTRY guards
Opportunity Cost
Dynamic Capital
Cash Exposure Authority
Compound Capital
Concentration as Safety / risk constraint
No forced deployment
```

Recommended L19 contract:

```text
PHASE29_L19_OPTION_5_CAP_CONSTRAINED_LOT_FLOOR_AND_ITERATIVE_RESIDUAL_REALLOCATION
```

Design contract:

```text
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/design_contract.json
```

## 8. Mandatory Final Fields

```text
Primary Judgment:
PHASE29_L18_DISCRETE_LOT_AND_RESIDUAL_CAPITAL_REALLOCATION_GAPS_CONFIRMED_REPAIR_DESIGN_READY

Root Cause confirmed:
YES

BUY_ADD zero quantity root cause:
DISCRETE_LOT_CONCENTRATION_BOUNDARY_GAP; 94320 one lot exceeds 18% strategy cap but remains within 25% safety hard max in audited ADD cases
BUY_NEW zero quantity root cause:
DISCRETE_LOT_CONCENTRATION_BOUNDARY_GAP plus hard/effective cap block; 78780 one lot exceeds 18% strategy cap, and on some dates exceeds 25% safety hard max

Discrete lot / continuous weight mismatch:
YES
Residual capital recycling exists:
YES
Residual capital recycling complete:
NO

Concentration authority producer:
Portfolio Policy single_name_weight_cap / Position Sizing strategy_maximum_position_weight; Safety Layer separately produces safety_maximum_position_weight
Concentration authority layer:
Strategy allocation cap 0.18 with Safety hard maximum 0.25 observed; effective sizing cap currently 0.18
Concentration hard safety preserved:
YES

Minimum lot authority:
Position Sizing minimum_meaningful_notional policy, max(50,000 JPY, price * tradable_unit * 1.02)
Lot rounding authority:
Position Sizing _lot_quantity floors notional to tradable_unit lots before Runtime Planning

ADD semantics require change:
NO
BUY_ADD semantics require change:
NO
BUY_NEW semantics require change:
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
Historical-only Strategy required:
NO
Future leakage risk:
NO

Recommended repair option:
Option 5 - Cap-Constrained Lot Floor plus Iterative Residual Reallocation

Implementation readiness:
DESIGN_READY_FOR_PHASE29_L19_IMPLEMENTATION

Production code changed: NO
Strategy code changed: NO
Runtime code changed: NO
Config changed: NO
Schema changed: NO
Threshold changed: NO
Runtime mutated: NO
Pending mutated: NO
Ledger mutated: NO
Historical executed: NO
Fresh-run executed: NO
Resume executed: NO

Recommended next task:
Phase29-L19 - Production-Common Cap-Constrained Lot Floor and Iterative Residual Reallocation Implementation
```

## 9. Deliverables

```text
docs/phase_reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design.md
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/evidence_manifest.md
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/lot_concentration_authority_trace.csv
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/buy_add_zero_quantity_cases.csv
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/buy_new_zero_quantity_cases.csv
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/residual_capital_recycling_audit.csv
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/repair_option_comparison.md
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/design_contract.json
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/discrete_lot_boundary_cases.csv
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/capital_reallocation_trace.csv
reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design/summary_metrics.json
```
