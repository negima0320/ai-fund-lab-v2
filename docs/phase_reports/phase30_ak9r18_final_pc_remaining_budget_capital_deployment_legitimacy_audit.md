# Phase30-AK9R18 - Final PC Remaining-Budget / Capital Deployment Legitimacy Audit

## Primary Judgment

```text
CURRENT_LOW_EXPOSURE_PRIMARY_CLASS = MULTI_CAUSAL
CAPITAL_DEPLOYMENT_REGRESSION_CONFIRMED = PARTIAL
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES_MINOR_FINAL_PC_BUDGET_AUTHORITY_MISMATCH
IMPLEMENTATION_REPAIR_REQUIRED = YES_FOCUSED_LOW_PRIORITY
```

AK9R18 confirms that the 22 AK9R17 `minimum_lot_exceeds_remaining_budget`
cases are mostly legitimate final-PC priority budget exhaustion. However, one
case is system-caused:

```text
2022-08-12 / 60310
classification = SYSTEM_CAUSED_BUDGET_AUTHORITY_MISMATCH
blocked executable notional = 34,530
```

For `60310`, final PC residual strategy budget was enough for the canonical
discrete executable one lot, but the remaining-budget skip aligns with the
higher draft continuous target weight. This is a small but real final-PC
continuous-vs-discrete budget authority mismatch.

## Remaining Budget Meaning

```text
REMAINING_BUDGET_CANONICAL_PRODUCER =
  Portfolio Construction lot-aware final reallocation /
  PORTFOLIO_CONSTRUCTION_LOT_FIRST_CAPITAL_CONSERVATION

REMAINING_BUDGET_FORMULA =
  deployable_budget_weight - allocated_increment_weight,
  bounded by target_gross_exposure - baseline_existing_required_weight

REMAINING_BUDGET_SEMANTIC =
  Strategy deployable incremental allocation budget inside final PC lot rebatch.
```

This is not raw cash, broker buying power, pending reserved cash, or final
account cash.

## Daily Reconstruction

Created:

```text
reports/phase_reports/phase30_ak9r18/daily_capital_budget_reconstruction.json
```

```text
DAILY_CAPITAL_BUDGET_RECONSTRUCTION_COMPLETE = YES
```

The reconstruction includes starting cash/equity, current market value,
draft/final PC positive counts, deployable budget, committed notional, residual
capital, final cash, and final exposure for 2022-08-10 through 2022-08-23.

## 22 Remaining-Budget Cases

Created:

```text
reports/phase_reports/phase30_ak9r18/remaining_budget_loss_items.json
```

```text
REMAINING_BUDGET_CASE_CLASS_DISTRIBUTION = {
  LEGITIMATE_PRIORITY_BUDGET_EXHAUSTION: 21,
  SYSTEM_CAUSED_BUDGET_AUTHORITY_MISMATCH: 1
}
```

All 22 could be funded from raw cash, but raw cash is not the final-PC budget
authority. The legitimate cases could not fit within remaining Strategy
deployable budget after higher-priority lot allocations under the final-PC
capital conservation contract.

## Raw Cash vs Deployable Budget

```text
HIGH_CASH_PRIMARY_CLASS =
  MULTI_CAUSAL_DOWNSTREAM_CASH_FEASIBLE_EXECUTION_AND_DISCRETE_LOT_CONSTRAINTS_NOT_FINAL_PC_REMAINING_BUDGET_PRIMARY
```

Final account cash is high, but final-PC remaining-budget behavior is not the
primary explanation. PC deployable/allocated notional is materially higher than
actual filled exposure; the remaining gap sits beyond this audit's final-PC
boundary, in downstream cash-feasible execution / discrete order realization.

## Residual Recycling

```text
RESIDUAL_CAPITAL_RECYCLE_ATTEMPT_COUNT = 95
RESIDUAL_CAPITAL_RECYCLE_SUCCESS_COUNT = 45
RESIDUAL_CAPITAL_STRANDED_COUNT = 1
RESIDUAL_CAPITAL_STRANDED_NOTIONAL = 34,530
SYSTEM_CAUSED_RESIDUAL_RECYCLING_GAP = PARTIAL
DAYS_WITH_EXECUTABLE_CANDIDATES_AND_UNUSED_DEPLOYABLE_BUDGET = 1
```

Residual recycling is active and generally works. The single stranded case is
`2022-08-12 / 60310`.

## Final PC Zero Reasons

```text
FINAL_PC_ZERO_REASON_DISTRIBUTION = {
  OTHER_ZERO_NO_ACTIVE_DRAFT_ALLOCATION: 263,
  minimum_lot_exceeds_safety_hard_cap: 26,
  minimum_lot_exceeds_remaining_budget: 24
}

FINAL_PC_ZERO_NOTIONAL_BY_REASON = {
  OTHER_ZERO_NO_ACTIVE_DRAFT_ALLOCATION: 0,
  minimum_lot_exceeds_safety_hard_cap: 13,745,810,
  minimum_lot_exceeds_remaining_budget: 2,428,630
}
```

Safety blocked notional is not deployable opportunity loss.

## Position / Policy Authorities

```text
ACTIVE_POSITION_COUNT_AUTHORITIES = {
  portfolio_policy.target_position_count: 9,
  position_sizing.dynamic_position_count: 9,
  portfolio_policy.meaningful_allocation_position_count: 50,
  portfolio_policy.maximum_position_count: null,
  strategy_single_name_soft_cap: 0.18,
  safety_single_name_hard_cap: 0.25,
  target_gross_exposure: 1.0,
  cash_reserve_ratio: 0.0
}

LEGACY_POSITION_COUNT_CONSTRAINT_ACTIVE = NO
LEGACY_CAPITAL_POLICY_ACTIVE = NO
```

No fixed cash reserve or legacy capital policy explains the high cash.

## Capital Conservation Contract

```text
CAPITAL_CONSERVATION_CONTRACT =
  PORTFOLIO_CONSTRUCTION_LOT_FIRST_CAPITAL_CONSERVATION:
  allocated_increment_weight + residual_cash_weight == deployable_budget_weight;
  baseline_existing_required_weight + deployable_budget_weight == target_gross_exposure.

INTENTIONAL_CASH_RESERVE_AMOUNT_BY_DAY = 0 for all completed days
INTENTIONAL_CASH_RESERVE_RATIO_BY_DAY = 0 for all completed days
```

## Previous Run Comparison

```text
PREVIOUS_AVG_DEPLOYABLE_BUDGET = 529,858.84
CURRENT_AVG_DEPLOYABLE_BUDGET = 799,140.69

PREVIOUS_AVG_FINAL_PC_ALLOCATED_NOTIONAL = 480,428.63
CURRENT_AVG_FINAL_PC_ALLOCATED_NOTIONAL = 686,040.42

PREVIOUS_RESIDUAL_RECYCLE_RATE = 0.325581
CURRENT_RESIDUAL_RECYCLE_RATE = 0.473684

PREVIOUS_AVG_EXPOSURE = 0.758660
CURRENT_AVG_EXPOSURE = 0.368579

FIRST_MATERIAL_CAPITAL_DEPLOYMENT_DIVERGENCE =
  2022-08-10: current PC deployable/allocated notional and actual exposure
  exceeded previous; no negative PC capital deployment regression starts on
  the first completed day.
```

The lower current realized exposure is not explained by a broad final-PC
remaining-budget regression.

## Materiality

```text
SYSTEM_CAUSED_STRANDED_CAPITAL_NOTIONAL = 34,530
SYSTEM_CAUSED_BLOCKED_EXECUTABLE_LOT_COUNT = 1
SYSTEM_CAUSED_BLOCKED_EXECUTABLE_NOTIONAL = 34,530
```

This is a valid defect, but it is not material enough to explain the completed
window's high cash / low exposure by itself.

## Repair Inventory

```text
SYSTEM_CAUSED_CAPITAL_DEPLOYMENT_REPAIR_INVENTORY = [
  {
    class: SYSTEM_CAUSED_BUDGET_AUTHORITY_MISMATCH,
    affected_count: 1,
    affected_notional: 34530,
    first_layer: Portfolio Construction lot-aware final reallocation remaining-budget skip,
    repair_boundary:
      Final-PC remaining-budget comparison should use canonical discrete
      executable lot notional/weight, not draft continuous target weight,
      when deciding budget skip for a lot-feasible row.
    priority: LOW_FOCUSED_BEFORE_LONG_VALIDATION
  }
]
```

## Preservation

```text
SAFETY_BLOCKERS_REMAIN_LEGITIMATE = YES
GENUINE_LOT_BLOCKERS_REMAIN_LEGITIMATE = YES
NO_FORCED_INVESTMENT_RECOMMENDED = YES
FIXED_EXPOSURE_TARGET_RECOMMENDED = NO
```

## Deliverables

```text
docs/phase_reports/phase30_ak9r18_final_pc_remaining_budget_capital_deployment_legitimacy_audit.md
reports/phase_reports/phase30_ak9r18_final_pc_remaining_budget_capital_deployment_legitimacy_audit.json
reports/phase_reports/phase30_ak9r18/daily_capital_budget_reconstruction.json
reports/phase_reports/phase30_ak9r18/remaining_budget_loss_items.json
reports/phase_reports/phase30_ak9r18/capital_deployment_comparison.json
```

## Historical

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R18
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Recommended Next Task

```text
Phase30-AK9R19 - Final-PC Discrete Executable Remaining-Budget Comparison Focused Repair
```
