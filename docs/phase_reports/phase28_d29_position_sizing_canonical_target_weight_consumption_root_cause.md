# Phase28-D29: Position Sizing Canonical Target-Weight Consumption Root Cause Diagnosis

## Status

```text
COMPLETE
```

## Primary Judgment

```text
PHASE28_D29_MULTIPLE_POSITION_SIZING_DEFECTS_CONFIRMED
```

Supporting judgments:

```text
PHASE28_D29_POSITION_SIZING_CANONICAL_TARGET_CONSUMPTION_GAP_CONFIRMED
PHASE28_D29_HOLD_BASELINE_PRESERVATION_DEFECT_CONFIRMED
PHASE28_D29_ADD_MINIMUM_NOTIONAL_BASELINE_ERASURE_DEFECT_CONFIRMED
```

The duplicate-row hypothesis is rejected for the target 2023-04-13 evidence:

```text
PHASE28_D29_POSITION_SIZING_DUPLICATE_ROW_SELECTION_DEFECT_CONFIRMED = false
```

## Target Evidence

```text
Run: runtime-test-historical-smoke-20260806T232756773314Z
Business date: 2023-04-13
Evidence root: reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T232756773314Z
Target symbols: 83060, 94320
```

## Root Cause

Position Sizing consumes the correct canonical Portfolio Construction rows, but then rewrites canonical target weights with BUY Quality / allocation adjustment logic inside Position Sizing.

For existing HOLD / ADD baseline rows, this violates the Portfolio Construction -> Position Sizing boundary:

```text
Portfolio Construction owns target_weight.
Position Sizing converts target_weight to target_notional, target_quantity_candidate,
and quantity_delta_candidate.
```

Code evidence:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py:1299
  _ps_summary selects payload.portfolio_members from Portfolio Construction.

src/ai_fund_lab_v2/strategy/position_sizing.py:365
  Position Sizing uses portfolio_construction_summary.rows.

src/ai_fund_lab_v2/strategy/position_sizing.py:660
  _raw_position resolves canonical row target_weight.

src/ai_fund_lab_v2/strategy/position_sizing.py:679
  adjusted = target * quality.

src/ai_fund_lab_v2/strategy/position_sizing.py:697
  target is overwritten with capped adjusted weight.

src/ai_fund_lab_v2/strategy/position_sizing.py:711
  minimum meaningful notional path sets target_quantity_candidate = 0.

src/ai_fund_lab_v2/strategy/runtime_planning.py:1246
  Runtime Planning maps negative quantity delta.

src/ai_fund_lab_v2/strategy/runtime_planning.py:1256
  Full negative delta without PM EXIT becomes REVIEW_REQUIRED.
```

## 83060 Trace

```text
PM action: HOLD
PM decision: pm-2023-04-13-83060-hold
PM reason: downside_risk_contained

Portfolio Construction canonical row:
member_id = phase22-e-2023-04-13-83060
pm_action = HOLD
membership_intent = RETAIN
weight_intent = MAINTAIN
current_weight = 0.085181
current_quantity = 100
target_weight = 0.085181
baseline_existing_weight = 0.085181
accepted_incremental_weight = 0.0

Position Sizing row:
position_reference = phase22-e-2023-04-13-83060
target_weight_resolution.resolved_weight = 0.085181
quality_action = REJECT
quality_allocation_adjustment = 0.0
effective target_weight = 0.0
target_quantity_candidate = 0
quantity_delta_candidate = -100

Runtime Planning:
planning_reason = planning_conflict_review:full_liquidation_authority_missing:83060
```

First divergence:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py:679
adjusted = target * quality
```

For 83060, target was 0.085181 and quality was 0.0, so Position Sizing produced target 0.0.

## 94320 Trace

```text
PM action: ADD
PM decision: pm-2023-04-13-94320-add
PM reasons: strong_trend_continuation, opportunity_rank_still_high, no_loss_averaging

Portfolio Construction canonical row:
member_id = phase22-e-2023-04-13-94320
pm_action = ADD
membership_intent = RETAIN
weight_intent = INCREASE
current_weight = 0.047587
current_quantity = 300
target_weight = 0.047587
target_weight_change = 0.0
baseline_existing_weight = 0.047587
accepted_incremental_weight = 0.0

Position Sizing row:
position_reference = phase22-e-2023-04-13-94320
target_weight_resolution.resolved_weight = 0.047587
quality_action = REDUCED_ALLOCATION_ONLY
quality_allocation_adjustment = 0.712227
effective target_weight = 0.033893
target_notional = 34016.03
minimum_meaningful_notional = 50000.0
target_quantity_candidate = 0
quantity_delta_candidate = -300

Runtime Planning:
planning_reason = planning_conflict_review:full_liquidation_authority_missing:94320
```

First divergence:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py:679
adjusted = target * quality
```

Secondary defect:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py:711
minimum_meaningful_notional_unmet zeroes the entire target quantity, including
an existing baseline position.
```

## Duplicate Hypothesis

Result:

```text
NO
```

Evidence:

```text
Portfolio Construction row count for 83060 = 1
Portfolio Construction row count for 94320 = 1
Position Sizing row count for 83060 = 1
Position Sizing row count for 94320 = 1
```

`candidate_duplicate_reconciled:*` is present as a reason code on the canonical row. It is not evidence that both pre-reconciliation and post-reconciliation rows remain in the downstream Position Sizing input.

## Minimum Meaningful Notional Semantics

Architecture says Position Sizing converts target weight to notional and quantity; it does not own target membership or target weight. For existing positions:

```text
HOLD -> target quantity approximately equals current quantity
ADD -> positive quantity delta candidate only when executable
```

Therefore, minimum meaningful notional should not erase an existing-position baseline. It may make an incremental transaction not executable, but for ADD with `accepted_incremental_weight = 0`, the expected preservation is:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
```

D29 does not implement that repair.

## Canonical Replay

Diagnostic-only replay using PC canonical target weights and existing PS price/equity evidence:

```text
portfolio_total_equity = 1003630.0

83060:
target_weight = 0.085181
target_notional = 85490.21
reference_price = 850.7
trading_unit = 100
target_quantity_candidate = 100
current_quantity = 100
quantity_delta_candidate = 0

94320:
target_weight = 0.047587
target_notional = 47759.74
reference_price = 159.2
trading_unit = 100
lot-rounded target_quantity_candidate = 200
current_quantity = 300
quantity_delta_candidate = -100
```

For 94320, the mechanical quantity replay still yields a partial negative delta because canonical target notional is below current notional. However, the PM ADD + zero accepted increment semantics indicate the D30 repair should preserve existing baseline quantity unless Portfolio Construction/PM produces REDUCE or EXIT authority.

## Causality

```text
D28 direct causality: PARTIAL
```

D28 did not create the Position Sizing consumer bug. It correctly materialized existing baseline target weights. The fresh run then exposed that Position Sizing still treats BUY Quality as a post-PC target-weight modifier and can erase existing baseline quantities.

```text
D19 direct causality: PARTIAL
```

D19 allowed same-day PM ADD/HOLD authority to reach the canonical strategy chain. It exposed the consumer bug but did not create the Position Sizing defect.

```text
D25 direct causality: NO
```

D25 correctly prevents full liquidation when Position Sizing emits target-zero / full negative delta without PM EXIT authority.

## Minimal Repair Scope

Primary D30 target:

```text
Position Sizing canonical PC row consumption and existing-position baseline preservation repair.
```

Required D30 contract:

```text
Position Sizing must consume exactly one canonical reconciled PC target row per symbol.
For current positions, Position Sizing must preserve PC target_weight as the sizing target and must not apply BUY Quality as a second target-weight modifier.
HOLD baseline target > 0 maps to current quantity / zero delta when lot rounding confirms retention.
ADD with accepted_incremental_weight = 0 retains baseline and emits zero delta, not SELL.
Minimum meaningful notional applies to incremental executable transaction sizing, not to erasing existing baseline quantity.
```

## Mutation Flags

```text
implementation_changed = false
config_changed = false
schema_changed = false
threshold_changed = false
resume_executed = false
fresh_run_executed = false
long_historical_executed = false
runtime_mutated = false
```

## Next Phase

```text
Phase28-D30 Position Sizing Canonical Target-Weight Consumption and Existing Baseline Preservation Repair Design
```
