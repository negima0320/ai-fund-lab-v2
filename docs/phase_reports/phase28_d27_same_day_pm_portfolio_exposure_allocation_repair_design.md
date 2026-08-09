# Phase28-D27: Same-day PM Portfolio Exposure Allocation Repair Design

## Executive Summary

Primary Judgment:

```text
PHASE28_D27_INCREMENTAL_BUDGET_RECONCILIATION_DESIGN_COMPLETE_D28_READY
```

Implementation Entry Decision:

```text
READY
```

D27 confirms the D26 regression is repairable in Portfolio Construction without rolling back D19, weakening D25, changing Phase28-C, or tuning the 0.72 exposure policy.

Selected repair option:

```text
Option B - Incremental budget allocator
```

Implementation packaging:

```text
Portfolio Construction incremental budget reconciliation
```

## Current 2023-04-04 Reconstruction

Current failed run:

```text
runtime-test-historical-smoke-20260806T223320442615Z
```

Portfolio Construction:

```text
producer_result_status = BLOCK
target_gross_exposure = 0.72
target_weight_sum_tolerance = 0.0000025
total_target_weight = 0.731271
overage = 0.011271
```

The overage is not a floating-point/tolerance issue.

Allocation construction:

| Symbol | Status | PM | Current Weight | Final Target | Contribution |
|---|---|---:|---:|---:|---:|
| 43880 | existing | HOLD | 0.123279 | 0.144 | HOLD contribution |
| 83060 | existing | ADD | 0.17231 | 0.17231 | existing ADD baseline |
| 94320 | existing | ADD | 0.126961 | 0.126961 | existing ADD baseline |
| 67310 | new | BUY_NEW | 0 | 0.144 | new BUY |
| 59350 | new | BUY_NEW | 0 | 0.144 | new BUY |

Sum:

```text
0.144 + 0.17231 + 0.126961 + 0.144 + 0.144 = 0.731271
```

## Root Cause

Root cause classification:

```text
D. Portfolio-level normalization occurs before ADD / existing baseline reconciliation and not after
```

Supporting classifications:

```text
C. BUY_NEW allocation and existing-position baseline / ADD allocation compete in separate implicit budgets
E. Opportunity Cost comparison ranks candidates but does not enforce aggregate exposure
```

Not root cause:

```text
F. Cash reserve / target gross exposure source mismatch
G. Floating-point/tolerance only
```

Code evidence:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py:887
src/ai_fund_lab_v2/strategy/portfolio_construction.py:982
src/ai_fund_lab_v2/strategy/portfolio_construction.py:1018
```

The current implementation computes equal-weight `base_weight = target_gross_exposure / selected_count`, applies ADD bridge row-by-row, then only blocks if the total exceeds the target. It does not reconcile existing baseline, ADD increments, and BUY_NEW into one budget before final validation.

## Budget Authority

`target_gross_exposure` is the Portfolio Construction hard allocation budget for final target weights:

```text
sum(target_weight) <= target_gross_exposure
```

Architecture evidence:

```text
docs/02_architecture/strategy_architecture_v1.md:378
docs/02_architecture/strategy_architecture_v1.md:382
docs/02_architecture/strategy_architecture_v1.md:385
```

For 2023-04-04:

```text
target_gross_exposure = 0.72
target cash reserve ~= 0.28
```

D27 does not change this policy.

## Participant Contract

The following share one portfolio budget:

```text
existing HOLD baseline
existing ADD baseline
existing REDUCE remaining target
accepted ADD incremental weight
BUY_NEW target weight
cash reserve
```

ADD must not have a separate bucket. BUY_NEW must not have a separate bucket. Cash retention remains valid if the incremental budget is not earned.

## HOLD Treatment

PM HOLD means existing position continuity. It does not mean automatic increase to equal-weight target.

D27 contract:

```text
HOLD baseline = current_weight
```

unless an explicit Portfolio rebalance authority exists. No such authority is established for D28 scope.

For 43880:

```text
current_weight = 0.123279
current PC target = 0.144
unexplained HOLD increase = 0.020721
```

D28 should remove that implicit HOLD increase.

## ADD Treatment

PM ADD is increase intent, not guaranteed execution.

Valid ADD increase requires:

```text
PM ADD
ADD eligibility PASS
Opportunity Cost PASS
portfolio incremental budget available
```

If evidence or budget is unavailable:

```text
retain baseline
no executable ADD
never SELL_EXIT
```

For 2023-04-04, both ADD rows fail closed on ADD evidence, so accepted ADD increment is zero.

## BUY_NEW Treatment

BUY_NEW competes with accepted ADD increments for:

```text
available_incremental_budget =
target_gross_exposure - baseline_existing_required_weight
```

ADD must not starve stronger new buys by separate bucket, and new buys must not starve valid ADD by separate bucket. Opportunity Cost and construction priority decide competition inside that common budget.

## REDUCE Treatment

PM REDUCE releases capacity only after Portfolio Construction accepts a lower target weight:

```text
REDUCE current baseline - REDUCE target = freed capacity
```

Freed capacity may be allocated to accepted ADD / BUY_NEW. REDUCE does not silently escalate to EXIT.

## Opportunity Cost Role

Phase28-B/C intended Opportunity Cost to compare:

```text
Existing ADD
New BUY
Cash retention
```

Current implementation checks Opportunity Cost inside ADD bridge, but does not use it to allocate a shared portfolio budget. D27 classifies this as:

```text
COMPARISON_EXISTS_BUDGET_ENFORCEMENT_GAP
```

## Selected Repair Contract

Algorithm contract:

1. Resolve `target_gross_exposure`, cash reserve, and caps.
2. Classify baseline existing weights, REDUCE/EXIT releases, ADD incremental requests, and BUY_NEW requests.
3. Compute:

```text
available_incremental_budget =
target_gross_exposure - baseline_existing_required_weight
```

4. Allocate accepted ADD increments and BUY_NEW weights within the available budget using existing priority / Opportunity Cost / quality evidence.
5. Trim or defer weakest incremental allocations when requests exceed budget.
6. Emit reconciliation evidence before aggregate validation.
7. Still fail closed if final sum exceeds `target_gross_exposure + tolerance`.

## 2023-04-04 Design Replay

Baseline existing:

```text
43880 HOLD = 0.123279
83060 ADD baseline = 0.17231
94320 ADD baseline = 0.126961
baseline_existing_required_weight = 0.42255
```

Available incremental budget:

```text
0.72 - 0.42255 = 0.29745
```

Accepted incremental allocations:

```text
ADD increment = 0.0
67310 BUY_NEW = 0.144
59350 BUY_NEW = 0.144
```

Final sum:

```text
0.123279 + 0.17231 + 0.126961 + 0.144 + 0.144 = 0.71055
```

Result:

```text
0.71055 <= 0.72
cash reserve ~= 0.28945
```

## PC / PS Boundary

Repair belongs in Portfolio Construction.

Architecture boundary:

```text
Portfolio Construction = target weights / portfolio budget
Position Sizing = quantities / lots / notional
```

Position Sizing must not reinterpret portfolio selection or target weights.

## Compatibility

D19 preserved:

```text
YES
```

D25 preserved:

```text
YES
```

Phase28-C preserved:

```text
YES
```

D28 must keep same-day PM producer ordering, keep PM ADD as BUY_ADD-capable when budget and evidence pass, and keep PM_EXIT as the only full-liquidation authority.

## Required Fixtures

Minimum D28 fixtures:

```text
existing HOLD only -> PASS
existing ADD with sufficient budget -> increase
two ADDs within budget -> both increase
two ADDs exceeding budget -> budget-aware allocation
HOLD + two ADD 2023-04-04 reproduction -> <= target gross exposure
ADD + BUY_NEW competition -> Opportunity Cost respected
REDUCE frees capacity for ADD / BUY_NEW
no capacity for ADD -> retain existing, no SELL
post-reconciliation still over target -> BLOCK
D19 same-day PM wiring PASS
D25 SELL authority PASS
Phase28-C ADD bridge PASS
```

## Deliverables

```text
docs/phase_reports/phase28_d27_same_day_pm_portfolio_exposure_allocation_repair_design.md
reports/phase_reports/phase28_d27_same_day_pm_portfolio_exposure_allocation_repair_design.json
reports/phase28_d27_same_day_pm_portfolio_exposure_allocation_repair_design/
```

## Mutation Declaration

```text
implementation_changed=false
config_changed=false
schema_changed=false
threshold_changed=false
resume_executed=false
fresh_run_executed=false
long_historical_executed=false
runtime_mutated=false
```

## Next Phase

```text
Phase28-D28 Portfolio Construction Incremental Budget Reconciliation Implementation
```
