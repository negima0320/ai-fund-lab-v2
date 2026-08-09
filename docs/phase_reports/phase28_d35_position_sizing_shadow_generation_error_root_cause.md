# Phase28-D35: Position Sizing Shadow Generation Error Root Cause Diagnosis

## Primary Judgment

```text
PHASE28_D35_POSITION_SIZING_EXISTING_BASELINE_CAP_VALIDATION_ROOT_CAUSE_CONFIRMED_D36_READY
```

Root Cause Classification:

```text
POSITION_SIZING_INPUT_SHAPE_REGRESSION
```

No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## Direct Exception

Focused replay of the 2023-05-09 Position Sizing producer using immutable strategy artifacts recovered the masked exception:

```text
Exception type:
PositionSizingSchemaError

Exception message:
target_weight_above_position_cap:1
```

Failing code path:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py:277-294
  calls position_sizing.produce_position_sizing_artifact(...)

src/ai_fund_lab_v2/strategy/position_sizing.py:256
  validate_position_sizing_artifact(payload)

src/ai_fund_lab_v2/strategy/position_sizing.py:1585-1586
  target_weight > maximum_position_weight
  -> errors.append("target_weight_above_position_cap:1")

src/ai_fund_lab_v2/strategy/position_sizing.py:540
  raise PositionSizingSchemaError(...)
```

The exception is caught and masked here:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py:120-132
```

The shadow error artifact preserved only:

```text
error = target_weight_above_position_cap:1
reason_codes = ["strategy_shadow_generation_error"]
```

## Failing Row

The failing validation row is:

```text
row_index = 1
symbol = 76470
pm_action = ADD
membership_intent = RETAIN
weight_intent = INCREASE
current_quantity = 6900
current_weight = 0.182844
target_weight = 0.182844
accepted_incremental_weight = 0.0
maximum_position_weight = 0.18
quantity_delta_candidate = 0
```

76470 was the direct failing row. It was not a row-generation crash: Position Sizing built the row successfully and preserved current quantity as expected.

## Failure Stage

Generation failed during final artifact validation, after all 50 Position Sizing rows had been materialized.

Last successful operation:

```text
build_position_sizing_payload completed
producer_result_status = PASS
positions_built = 50
76470 target_quantity_candidate = 6900
76470 quantity_delta_candidate = 0
```

First failed operation:

```text
_validate_position row index 1
target_weight 0.182844 > maximum_position_weight 0.18 + tolerance 0.000001
```

The row immediately before the failing validation row was:

```text
row_index = 0
symbol = 76010
target_weight = 0.14231
maximum_position_weight = 0.18
validation PASS
```

## 2023-05-08 vs 2023-05-09

The key input difference is 76470 crossing the strategy maximum position cap:

```text
2023-05-08:
76470 current_weight = target_weight = 0.173881
maximum_position_weight = 0.18
Position Sizing PASS

2023-05-09:
76470 current_weight = target_weight = 0.182844
maximum_position_weight = 0.18
Position Sizing BLOCK via schema exception
```

The shape is otherwise the D31 expected ADD zero-increment baseline case:

```text
ADD + zero accepted increment
-> preserve current_quantity
-> quantity_delta_candidate = 0
```

That quantity behavior succeeded. The failure is the final cap validator treating an authoritative retained existing baseline above strategy cap as a schema error.

## D31 Causality

```text
PARTIAL
```

D31 transaction-delta logic did not throw. It succeeded for 76470:

```text
target_quantity_candidate = 6900
quantity_delta_candidate = 0
```

However, the failing input shape is a D31 existing ADD zero-increment baseline-retention case. D31 preserved the baseline as intended, while the older final validation rule still required every produced `target_weight` to be below `maximum_position_weight`. The semantic gap is between existing-baseline preservation and final cap validation, not an exception inside D31 transaction-delta code.

## D34 Causality

```text
NO
```

D34 is not directly involved:

```text
failing symbol = 76470
pm_action = ADD
REDUCE row involved = false
reduce_intensity resolver involved = false
Position Sizing shared REDUCE authority import = false
```

The failure is `target_weight` versus `maximum_position_weight`, not REDUCE authority, REDUCE intensity, or D34 resolver behavior.

## Root Cause

Position Sizing final schema validation rejects an authoritative retained current-position baseline when market movement causes the retained `current_weight / target_weight` to exceed the configured strategy maximum position weight.

The exact trigger on 2023-05-09:

```text
76470
target_weight = current_weight = 0.182844
maximum_position_weight = 0.18
accepted_incremental_weight = 0.0
quantity_delta_candidate = 0
```

Earlier dates succeeded because the same retained ADD zero-increment row was still below cap, e.g. 2023-05-08 had 76470 at `0.173881`.

## Minimal D36 Repair Scope

Recommended bounded D36 repair:

```text
Position Sizing existing-position retained-baseline cap validation repair
```

The repair should preserve:

```text
D19
D25
D28
D31 quantity semantics
D34 reduce authority
Phase28-C
```

It should not weaken cap enforcement for:

```text
BUY_NEW
positive ADD increments
new exposure
REDUCE
EXIT
```

It should only address authoritative current-position baseline retention where:

```text
current_position = true
pm_action in HOLD / ADD
accepted_incremental_weight = 0
target_weight == current_weight or baseline_existing_weight
quantity_delta_candidate = 0
```

## Observability Gap

`position_sizing_shadow_error.v1` should ideally preserve sanitized diagnostic fields:

```text
exception_type
exception_message
producer_stage
stack_top
failing_symbol
failing_row_index
sanitized_input_field_values
```

D35 does not implement that repair.

## Deliverables

```text
docs/phase_reports/phase28_d35_position_sizing_shadow_generation_error_root_cause.md
reports/phase_reports/phase28_d35_position_sizing_shadow_generation_error_root_cause.json
reports/phase28_d35_position_sizing_shadow_generation_error_root_cause/
```

## Completion Status

```text
Underlying exception recovered: YES
First failing operation identified: YES
Failing row/symbol identified: YES
Last-good vs failed input difference documented: YES
D31/D34 causality separated: YES
Minimal D36 repair scope selected: YES
Implementation changed: false
Config changed: false
Schema changed: false
Threshold changed: false
Resume executed: false
Fresh run executed: false
Long Historical executed: false
Runtime mutated: false
```
