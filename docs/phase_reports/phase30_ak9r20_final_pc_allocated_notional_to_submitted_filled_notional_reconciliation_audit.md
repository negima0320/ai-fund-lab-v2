# Phase30-AK9R20 - Final-PC Allocated Notional to Submitted/Filled Notional Reconciliation Audit

## Primary Judgment

`SYSTEM_CAUSED_FINAL_PC_TO_FILL_LOSS_MATERIAL = YES`

The current run's low exposure is not primarily explained by Final-PC failing to allocate capital. Final-PC, PS, and Runtime Planning preserve large executable BUY authority. The first material downstream disappearance is:

```text
FIRST_MATERIAL_NOTIONAL_LOSS_LAYER = PENDING_TO_SUBMIT_PASS_NOTIONAL_LOSS
```

The material blocker is Submit item-scoped review:

```text
pc_discrete_quantity_authority_lot_overshoot_unresolved
```

This affected 44 BUY items and `4,490,060 JPY` of Final-PC executable BUY authority over the completed audit window.

## Scope

Target run:

```text
runtime-test-historical-extended-smoke-20260817T094656753507Z
```

Comparison run:

```text
runtime-test-historical-extended-smoke-20260817T014925194738Z
```

Completed business days audited:

```text
2022-08-10
2022-08-12
2022-08-15
2022-08-16
2022-08-17
2022-08-18
2022-08-19
2022-08-22
2022-08-23
```

No implementation, replay, resume, fresh run, Strategy change, threshold change, cap change, or historical tuning was performed.

## Daily Funnel

Full day-level evidence:

```text
reports/phase_reports/phase30_ak9r20/daily_capital_funnel.json
```

Aggregate current-run funnel:

```text
FINAL_PC_ALLOCATED_BUY_NEW_NOTIONAL = 8,258,800
FINAL_PC_ALLOCATED_BUY_ADD_NOTIONAL = 120,940
PS_EXECUTABLE_BUY_NEW_NOTIONAL = 5,890,170
PS_EXECUTABLE_BUY_ADD_NOTIONAL = 120,940
RUNTIME_PLANNED_BUY_NEW_NOTIONAL = 5,890,170
RUNTIME_PLANNED_BUY_ADD_NOTIONAL = 120,940
PENDING_APPROVED_BUY_NEW_NOTIONAL = 5,661,750
PENDING_APPROVED_BUY_ADD_NOTIONAL = 120,940
SUBMIT_PASS_BUY_NEW_NOTIONAL = 1,292,630
SUBMIT_PASS_BUY_ADD_NOTIONAL = 0
SUBMITTED_BUY_NEW_NOTIONAL = 1,292,630
SUBMITTED_BUY_ADD_NOTIONAL = 0
FILLED_BUY_NEW_NOTIONAL = 1,281,900
FILLED_BUY_ADD_NOTIONAL = 0
SELL_FILLED_NOTIONAL = 946,480
CURRENT_AVG_EXPOSURE = 36.8579%
```

## Notional Loss Layers

```text
PC_TO_PS_NOTIONAL_LOSS = 2,368,630
PS_TO_RUNTIME_NOTIONAL_LOSS = 0
RUNTIME_TO_PENDING_NOTIONAL_LOSS = 228,420
PENDING_TO_SUBMIT_PASS_NOTIONAL_LOSS = 4,490,060
SUBMIT_PASS_TO_SUBMITTED_NOTIONAL_LOSS = 0
SUBMITTED_TO_FILL_NOTIONAL_LOSS = 10,730
```

The dominant layer is `PENDING_TO_SUBMIT_PASS`.

## Loss Classification

Full symbol inventory:

```text
reports/phase_reports/phase30_ak9r20/final_pc_to_fill_loss_items.json
```

Distribution:

```text
LEGITIMATE_CASH_CONSTRAINT = 3
SYSTEM_CAUSED_AUTHORITY_HANDOFF = 44
UNKNOWN = 22
```

The 44 system-caused cases all share:

```text
first_disappearance_layer = PENDING_TO_SUBMIT_PASS
exact_reason_code = pc_discrete_quantity_authority_lot_overshoot_unresolved
classification = SYSTEM_CAUSED_AUTHORITY_HANDOFF
```

The 3 legitimate cash cases are `DEFERRED_INSUFFICIENT_RESERVED_CASH`.

## REVIEW_REQUIRED Audit

```text
DOWNSTREAM_REVIEW_REQUIRED_COUNT = 44
DOWNSTREAM_REVIEW_REQUIRED_SYSTEM_CAUSED_COUNT = 44
DOWNSTREAM_REVIEW_REQUIRED_LEGITIMATE_COUNT = 0
```

`REVIEW_REQUIRED` itself is not the cause. The concrete reason is the Submit boundary failing to accept/consume PC discrete-lot overshoot authority:

```text
pc_discrete_quantity_authority_lot_overshoot_unresolved
```

## Pending Partial Approval

```text
PARTIAL_APPROVED_PENDING_DAY_COUNT = 9
APPROVED_BUY_ITEM_COUNT = 29
REVIEW_BUY_ITEM_COUNT = 44
APPROVED_BUY_SUBMITTED_COUNT = 29
REVIEW_BUY_EXPIRED_COUNT = 44
PARTIAL_REVIEW_MATERIAL_CAPITAL_DRAG = YES
```

Partial approval is action-effective for PASS items, but reviewed BUYs materially reduce deployment.

## BUY / SELL Same-Day Interaction

```text
MIXED_BUY_SELL_DAY_COUNT = 7
BUY_NOTIONAL_ON_MIXED_DAYS = 840,950
SELL_NOTIONAL_ON_MIXED_DAYS = 946,480
VALID_BUY_LOST_ON_MIXED_DAYS_COUNT = 34
VALID_BUY_LOST_ON_MIXED_DAYS_NOTIONAL = 3,541,810
BUY_SELL_INDEPENDENCE_FRESH_ACTION_EFFECTIVE = YES
```

AK8R BUY/SELL independence is action-effective: SELLs and PASS BUYs submit/fill on mixed days. The remaining issue is item-scoped BUY review, not BUY/SELL atomic coupling.

## Fill / Current Reconciliation

```text
FILL_TO_CURRENT_POSITION_RECONCILIATION = PASS
FILL_TO_CASH_RECONCILIATION = PASS
CURRENT_STATE_ACCOUNTING_MISMATCH_NOTIONAL = 0
```

Cash reconciled exactly day by day from prior cash plus SELL fills minus BUY fills.

## Turnover vs Exposure

```text
TOTAL_BUY_FILLED_NOTIONAL = 1,281,900
TOTAL_SELL_FILLED_NOTIONAL = 946,480
GROSS_TURNOVER = 2,228,380
AVERAGE_HOLDING_POSITION_COUNT = 8.89
SAME_OR_NEXT_DAY_SELL_COUNT = 16
SHORT_HOLD_CHURN_NOTIONAL = 654,850
LOW_EXPOSURE_EXECUTION_PRIMARY_CLASS = MULTI_CAUSAL
```

Low exposure is multi-causal:

- material BUY conversion loss at Submit review
- significant SELL turnover and short-hold churn

The primary system defect is still the downstream Submit authority handoff.

## Previous Good Run Comparison

Comparison evidence:

```text
reports/phase_reports/phase30_ak9r20/previous_vs_current_execution_comparison.json
```

```text
PREVIOUS_FINAL_PC_ALLOCATED_NOTIONAL = 5,745,610
CURRENT_FINAL_PC_ALLOCATED_NOTIONAL = 8,379,740
PREVIOUS_SUBMITTED_BUY_NOTIONAL = unavailable in copied previous submit evidence
CURRENT_SUBMITTED_BUY_NOTIONAL = 1,292,630
PREVIOUS_FILLED_BUY_NOTIONAL = 2,052,520
CURRENT_FILLED_BUY_NOTIONAL = 1,281,900
PREVIOUS_FILLED_SELL_NOTIONAL = 1,118,850
CURRENT_FILLED_SELL_NOTIONAL = 946,480
PREVIOUS_AVG_EXPOSURE = 75.8660%
CURRENT_AVG_EXPOSURE = 36.8579%
FIRST_MATERIAL_END_TO_END_DIVERGENCE_LAYER = FILLED_BUY_NOTIONAL
```

Current Final-PC/PS/Runtime planned notional is higher than the comparison run, yet filled BUY notional is lower. This confirms the negative divergence is downstream of Runtime Planning, with copied current evidence locating the actionable current-run layer at Submit item review.

## Repair-Chain Attribution

```text
FIRST_REPAIR_ASSOCIATED_WITH_DIVERGENT_BEHAVIOR = AK9R16/AK9R19 authority surface implicated by Submit reason
CAUSAL_REPAIR_REGRESSION_CONFIRMED = UNPROVEN
```

Do not infer causality from phase order. The artifact-level evidence proves the active divergent behavior but does not prove which repair introduced it.

## Required Judgments

```text
DAILY_CAPITAL_FUNNEL_COMPLETE = YES
FIRST_MATERIAL_NOTIONAL_LOSS_LAYER = PENDING_TO_SUBMIT_PASS_NOTIONAL_LOSS
FINAL_PC_TO_FILL_LOSS_CLASS_DISTRIBUTION = {"LEGITIMATE_CASH_CONSTRAINT": 3, "SYSTEM_CAUSED_AUTHORITY_HANDOFF": 44, "UNKNOWN": 22}
CASH_FEASIBLE_BUT_NOT_SUBMITTED_COUNT = 44
CASH_FEASIBLE_BUT_NOT_SUBMITTED_NOTIONAL = 4,490,060
CASH_FEASIBLE_BUT_NOT_FILLED_COUNT = 44
CASH_FEASIBLE_BUT_NOT_FILLED_NOTIONAL = 4,490,060
VALID_FINAL_PC_BUY_AUTHORITY_PRESERVED_TO_FILL = PARTIAL
VALID_FINAL_PC_ADD_AUTHORITY_PRESERVED_TO_FILL = PARTIAL
SYSTEM_CAUSED_FINAL_PC_TO_FILL_LOSS_MATERIAL = YES
SYSTEM_CAUSED_FINAL_PC_TO_FILL_LOSS_NOTIONAL = 4,490,060
CURRENT_LOW_EXPOSURE_END_TO_END_PRIMARY_CLASS = MULTI_CAUSAL_DOWNSTREAM_SUBMIT_REVIEW_AND_SELL_TURNOVER
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Repair Inventory

```json
[
  {
    "layer": "PENDING_TO_SUBMIT_PASS",
    "class": "SYSTEM_CAUSED_AUTHORITY_HANDOFF",
    "affected_count": 44,
    "affected_notional": 4490060.0,
    "reason": "pc_discrete_quantity_authority_lot_overshoot_unresolved",
    "recommended_repair_boundary": "Submit guard / PositionSizingAuthority consumption of PC discrete-lot overshoot authority",
    "priority": "P0"
  }
]
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R20
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Recommended Next Task

`Phase30-AK9R21 - Submit Guard PC Discrete-Lot Overshoot Authority Consumption Focused Repair`
