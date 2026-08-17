# Phase30-AK9R17 - PC-to-PS Capital Conversion Loss Legitimacy Audit

## Primary Judgment

```text
PC_TO_PS_CAPITAL_CONVERSION_PRIMARY_CLASS =
  MULTI_CAUSAL_LEGITIMATE_SAFETY_AND_DISCRETE_LOT_BUDGET_CONSTRAINTS

REGRESSION_CONFIRMED = NO
VALID_PC_BUY_AUTHORITY_UNNECESSARILY_DROPPED_BY_PS = NO
VALID_PC_ADD_AUTHORITY_UNNECESSARILY_DROPPED_BY_PS = NO
SYSTEM_CAUSED_PC_PS_LOSS_MATERIAL_TO_LOW_EXPOSURE = NO
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
IMPLEMENTATION_REPAIR_REQUIRED = NO
```

The completed-window PC -> PS gap is real, but it is not a PS authority
handoff defect. Recomputed from actual artifacts, the 48 losses are all
`BUY_NEW` draft-PC-positive rows that final Portfolio Construction set to zero
before Position Sizing consumed them. No row in the loss set has valid canonical
PC executable authority with `ps_must_consume_canonical_quantity=true`.

## Exact Population

Window:

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

Recomputed funnel:

```text
PC_POSITIVE_BUY_NEW_COUNT = 121
PS_POSITIVE_BUY_NEW_COUNT = 73
PC_POSITIVE_BUY_NEW_TO_PS_NON_POSITIVE_COUNT = 48

PM_ADD_COUNT = 4
PC_POSITIVE_ADD_COUNT = 3
PS_POSITIVE_ADD_COUNT = 3
PC_POSITIVE_ADD_TO_PS_NON_POSITIVE_COUNT = 0
```

The count matches AK9R15 when `portfolio_construction_draft.json` is used as
the PC-positive population. Final `portfolio_construction.json` already has
these 48 rows at `target_weight=0`.

## Loss Classification

```text
PC_PS_LOSS_CLASS_DISTRIBUTION = {
  LEGITIMATE_SAFETY_CONSTRAINT: 26,
  GENUINELY_NON_EXECUTABLE: 22
}

BUY_NEW_PC_PS_LOSS_CLASS_DISTRIBUTION = {
  LEGITIMATE_SAFETY_CONSTRAINT: 26,
  GENUINELY_NON_EXECUTABLE: 22
}

BUY_ADD_PC_PS_LOSS_CLASS_DISTRIBUTION = {}
```

The effective blockers are final-PC lot rebatch reasons:

```text
minimum_lot_exceeds_safety_hard_cap = 26
minimum_lot_exceeds_remaining_budget = 22
```

PS-level reason codes are only generic `membership_intent:ADD_CANDIDATE` and
`pm_action:NEW`; PS is not independently re-rejecting a valid PC quantity in
this population.

## AK9R16 Counterfactual Scope

```text
AK9R16_EQUIVALENT_LOSS_COUNT = 0
AK9R16_EQUIVALENT_BUY_NEW_COUNT = 0
AK9R16_EQUIVALENT_BUY_ADD_COUNT = 0
AK9R16_EQUIVALENT_EXECUTABLE_NOTIONAL = 0.0
```

AK9R16 repaired PS recognition of PC-authorized
`SECOND_LOT_PLUS_RESIDUAL_CAPITAL_AWARE_PROMOTION` authority. No completed-window
loss row has that valid authority shape reaching PS and being rejected.

## Canonical Authority Check

```text
PC_CANONICAL_AUTHORITY_PRESENT_LOSS_COUNT = 0
PC_CANONICAL_AUTHORITY_PRESENT_SYSTEM_DROP_COUNT = 0
SYSTEM_CAUSED_LOT_AUTHORITY_DROP_COUNT = 0
```

All 48 loss rows have final PC target zero and no canonical PC executable
quantity authority requiring PS consumption.

## Lot / Capital Context

```text
GENUINE_LOT_CONSTRAINED_COUNT = 22
GENUINE_LOT_CONSTRAINED_NOTIONAL = 2,348,730
```

For the 22 residual-budget cases, lots were not admitted by final PC because
the remaining budget after higher-priority lot allocation could not support the
next executable lot under the active capital-conservation contract.

## Exposure Attribution

Capital-conversion notional by class:

```text
PC_PS_LOSS_EXECUTABLE_NOTIONAL_BY_CLASS = {
  GENUINELY_NON_EXECUTABLE: 2,348,730,
  LEGITIMATE_STRATEGY_CONSTRAINT: 0,
  LEGITIMATE_SAFETY_CONSTRAINT: 13,745,810,
  SYSTEM_CAUSED_DUPLICATE_AUTHORITY: 0,
  SYSTEM_CAUSED_AUTHORITY_HANDOFF_GAP: 0,
  SYSTEM_CAUSED_SHAPE_OR_IMPLEMENTATION_GAP: 0,
  UNKNOWN: 0
}
```

This is not hypothetical PnL. It is the one-lot notional associated with
blocked draft-positive opportunities.

## Previous Run Comparison

```text
PREVIOUS_GOOD_RUN_ID = runtime-test-historical-extended-smoke-20260817T014925194738Z
CURRENT_RUN_ID = runtime-test-historical-extended-smoke-20260817T094656753507Z

PREVIOUS_PC_POSITIVE_COUNT = 104
PREVIOUS_PS_POSITIVE_COUNT = 52
CURRENT_PC_POSITIVE_COUNT = 124
CURRENT_PS_POSITIVE_COUNT = 76

PC_TO_PS_CONVERSION_RATE_PREVIOUS = 0.500000
PC_TO_PS_CONVERSION_RATE_CURRENT = 0.612903

FIRST_MATERIAL_AUTHORITY_DIVERGENCE =
  2022-08-10; current converted 16/19 PC-positive BUY_NEW versus previous 13/19.
```

The first divergence is an improvement in conversion, not evidence of a
negative regression.

## Reason-Code Legitimacy Matrix

Created:

```text
reports/phase_reports/phase30_ak9r17/ps_reason_legitimacy_matrix.json
```

Key findings:

```text
PC_FINAL_TARGET_ZERO_CONSUMED_BY_PS:
  occurrence_count = 48
  classification = LEGITIMATE
  canonical_pc_authority_present_count = 0
  should_ps_remain_blocker = NO

minimum_lot_exceeds_remaining_budget:
  occurrence_count = 22
  classification = LEGITIMATE
  should_ps_remain_blocker = CONDITIONAL

minimum_lot_exceeds_safety_hard_cap:
  occurrence_count = 26
  classification = LEGITIMATE
  should_ps_remain_blocker = YES
```

The first row is intentionally marked `should_ps_remain_blocker=NO` because it
is not a PS-owned blocker; PS is consuming final PC zero.

## Repair Inventory

```text
SYSTEM_CAUSED_PC_PS_REPAIR_INVENTORY = []
```

No implementation repair is justified by this audit.

## Deliverables

```text
docs/phase_reports/phase30_ak9r17_pc_to_ps_capital_conversion_loss_legitimacy_audit.md
reports/phase_reports/phase30_ak9r17_pc_to_ps_capital_conversion_loss_legitimacy_audit.json
reports/phase_reports/phase30_ak9r17/pc_to_ps_loss_items.json
reports/phase_reports/phase30_ak9r17/ps_reason_legitimacy_matrix.json
```

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R17
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Recommended Next Task

```text
Return to user-operated fresh 20BD validation.
```
