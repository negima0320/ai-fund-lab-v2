# Phase28-D36: Position Sizing Existing-Position Retained-Baseline Cap Validation Repair Implementation

## Primary Judgment

```text
PHASE28_D36_EXISTING_BASELINE_CAP_VALIDATION_REPAIRED_SHORT_VALIDATION_PASS
```

Supporting Judgment:

```text
PHASE28_D36_CAP_DIRECTIONALITY_CONTRACT_RESTORED_FRESH_100BD_READY
```

Fresh Test Entry Decision:

```text
READY
```

## Implemented Repair

D36 repaired the D35-confirmed validation defect. Position Sizing now distinguishes:

```text
existing retained baseline drift above cap
```

from:

```text
new or incremental exposure above cap
```

The maximum position cap value remains unchanged:

```text
maximum_position_weight = 0.18
```

No config, schema, or threshold was changed.

## Code Changes

Primary repair:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
```

The final position validator still rejects `target_weight > maximum_position_weight` unless the over-cap target is directionally allowed:

```text
existing HOLD / ADD
membership_intent = RETAIN
accepted_incremental_weight = 0
quantity_delta_candidate = 0
target_weight equals current_weight or baseline_existing_weight
```

or:

```text
PM REDUCE
quantity_delta_candidate <= 0
target_weight <= current_weight
```

Small focused chain repair:

```text
src/ai_fund_lab_v2/strategy/runtime_planning.py
```

Runtime Planning now resolves current-position `quantity_delta_candidate = 0` before PM ADD fallback, so existing ADD zero-delta maps to:

```text
NO_ACTION
```

instead of reviving BUY_ADD intent after Position Sizing has produced a zero delta.

## Cap Directionality

D36 confirms the cap is enforced as a maximum for new or increasing exposure, not as an automatic forced-liquidation invariant after market drift.

Overweight concentration should be addressed by explicit PM / Portfolio Construction REDUCE authority, not by Position Sizing schema failure.

## 76470 Result

Focused D35 reproduction now passes:

```text
symbol = 76470
pm_action = ADD
current_quantity = 6900
current_weight = 0.182844
target_weight = 0.182844
accepted_incremental_weight = 0.0
maximum_position_weight = 0.18
target_quantity_candidate = 6900
quantity_delta_candidate = 0
producer_result_status = PASS
```

Observed evidence:

```text
EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT
```

Focused PS -> Runtime Planning chain:

```text
76470 planning_intent = NO_ACTION
planned_quantity = 0
quantity_delta_candidate = 0
```

## Validation Matrix

```text
76470 reproduction PASS
existing HOLD above cap + delta0 PASS
existing ADD zero increment above cap PASS
existing ADD positive increment above cap remains blocked
BUY_NEW above cap remains capped and validator blocks over-cap mutation
artificial existing target increase above cap remains blocked
REDUCE above-cap risk-reducing target PASS
EXIT above-cap PASS
D31 regression PASS
D34 regression PASS
D25 regression PASS
D28 regression PASS
Phase28-C regression PASS
ordinary below-cap cases PASS
compile PASS
JSON validation PASS
git diff --check PASS
```

## Scope Guard

```text
Implementation changed: true
Config changed: false
Schema changed: false
Threshold changed: false
Maximum position cap changed: false
Runtime Authority violation: false
Resume executed: false
Fresh run executed: false
Long Historical executed: false
```

## Open Gaps

D35's error artifact observability gap remains open. D36 did not redesign `position_sizing_shadow_error.v1`.

## Next Phase

```text
Fresh 100BD validation by operator
```
