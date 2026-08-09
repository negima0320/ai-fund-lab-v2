# Phase28-D41: Position Sizing Post-Passive-Convergence Generation Error Root Cause

## Judgment

Primary Judgment:

```text
PHASE28_D41_PS_PASSIVE_CONVERGENCE_STATE_NOT_SUPPORTED_ROOT_CAUSE_CONFIRMED
```

Root classification:

```text
PS_PASSIVE_CONVERGENCE_STATE_NOT_SUPPORTED
```

Secondary classification:

```text
PS_AGGREGATE_TARGET_VALIDATOR_OVER_STRICT
```

D39 causality:

```text
EXPECTED_EXPOSURE
```

Phase28-D41 was performed as read-only diagnosis. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## Target

```text
run_id: runtime-test-historical-smoke-20260807T075946923450Z
business_date: 2023-06-01
failing artifact: reports/runtime_tests/runs/runtime-test-historical-smoke-20260807T075946923450Z/daily/2023-06-01/strategy/position_sizing.json
recorded status: BLOCK
recorded reason_codes: ["strategy_shadow_generation_error"]
```

The runtime artifact only preserved the shadow wrapper reason. A focused read-only producer replay was used to expose the underlying Position Sizing exception without mutating runtime state.

## Direct Exception

Exact exception:

```text
PositionSizingSchemaError
```

Exact message:

```text
aggregate_target_weight_above_exposure_cap
```

Direct producer path:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
produce_position_sizing_artifact
line 257
validate_position_sizing_artifact(payload)
```

First failing validator location:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
lines 510-512
if target_exposure is not None and total is not None and total > target_exposure + aggregate_tolerance:
    errors.append("aggregate_target_weight_above_exposure_cap")
```

Raise location:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
line 541
raise PositionSizingSchemaError(";".join(errors))
```

Shadow runtime wrapper location:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py
lines 119-128
produce(...) catches Exception and writes _error_artifact(...)

src/ai_fund_lab_v2/strategy/shadow_runtime.py
line 646
reason_codes = ["strategy_shadow_generation_error"]
```

## First Failure Point

This is not a row-processing exception.

```text
last successful operation:
build_position_sizing_payload completed and materialized 50 positions in memory

first failed operation:
validate_position_sizing_artifact aggregate target cap validation

first failing symbol:
None

first failing input field:
total_target_weight

first failing value:
0.677443

compared against:
target_gross_exposure_ratio = 0.54
aggregate_tolerance = 0.000025
```

The failing comparison was:

```text
0.677443 > 0.54 + 0.000025
```

Before validation, `build_position_sizing_payload` had already marked the in-memory payload:

```text
producer_result_status = BLOCK
reason_codes = ["aggregate_target_weight_above_exposure_cap"]
positions = 50
```

The validation exception prevented this richer payload from being written; the shadow runtime then wrote only the generic `strategy_shadow_generation_error` fallback artifact.

## 2023-05-31 vs 2023-06-01

2023-05-31 Position Sizing passed because Portfolio Construction remained within the dynamic target:

```text
PC producer_result_status = PASS
target_gross_exposure = 0.72
baseline_existing_required_weight = 0.703472
available_incremental_budget = 0.016528
total_target_weight = 0.72

PS producer_result_status = PASS
PS target_gross_exposure_ratio = 0.72
PS total_target_weight = 0.72
positions = 49
```

2023-06-01 is the new D39 passive convergence state:

```text
PC producer_result_status = PASS
target_gross_exposure = 0.54
baseline_existing_required_weight = 0.677443
available_incremental_budget = 0
total_target_weight = 0.677443
aggregate_exposure_state = OVER_TARGET_EXISTING_BASELINE
transition_mode = PASSIVE_CONVERGENCE
positive_increment_allowed = false
reason_codes include:
  existing_baseline_over_dynamic_target_passive_convergence
  positive_increment_suppressed_while_over_target
```

Position Sizing still applied the unconditional aggregate invariant:

```text
sum(target_weight) <= target_gross_exposure_ratio
```

That invariant is no longer sufficient after D39, because D39 intentionally allows retained existing baseline to sit above the lowered dynamic exposure target when positive increments are suppressed.

## Passive Convergence Propagation

D39 state is present in the upstream Portfolio Construction artifact:

```text
aggregate_exposure_state = OVER_TARGET_EXISTING_BASELINE
transition_mode = PASSIVE_CONVERGENCE
positive_increment_allowed = false
baseline_existing_required_weight = 0.677443
target_gross_exposure = 0.54
total_target_weight = 0.677443
```

Position Sizing receives Portfolio Construction as `portfolio_construction_summary`, but the Position Sizing payload does not materialize or consume:

```text
aggregate_exposure_state
transition_mode
positive_increment_allowed
baseline_existing_required_weight
```

Relevant code evidence:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py:327
target_exposure is read from dynamic_cash_exposure_summary.summary.target_gross_exposure_ratio

src/ai_fund_lab_v2/strategy/position_sizing.py:388-393
total_target_weight is compared against target_exposure without passive convergence branching

src/ai_fund_lab_v2/strategy/position_sizing.py:510-512
schema validation repeats the same aggregate cap check
```

Therefore this is not a propagation gap in Portfolio Construction. It is a Position Sizing state-consumption gap.

## Row Inventory

Focused replay materialized 50 rows before final validation failed.

Target symbols:

| Symbol | PM Action | PS target_weight | PS current_weight | transaction_delta_weight | quantity_delta_candidate | quantity_status | row status |
|---|---:|---:|---:|---:|---:|---|---|
| 21340 | ADD | 0.117487 | 0.117487 | 0.0 | 0 | RESOLVED_ZERO_DELTA | SIZED |
| 30410 | ADD | 0.120700 | 0.120700 | 0.0 | 0 | RESOLVED_ZERO_DELTA | SIZED |
| 38560 | NEW | 0.0 | 0.0 | 0.0 | 0 | RESOLVED_ZERO_DELTA | SIZED |
| 59550 | ADD | 0.091236 | 0.091236 | 0.0 | 0 | RESOLVED_ZERO_DELTA | SIZED |
| 67310 | NEW | 0.0 | 0.0 | 0.0 | 0 | RESOLVED_ZERO_DELTA | SIZED |
| 83060 | NEW | 0.0 | 0.0 | 0.0 | 0 | RESOLVED_ZERO_DELTA | SIZED |
| 93990 | REDUCE | 0.048188 | 0.064251 | 0.016063 | 0 | PRICE_UNAVAILABLE | SIZED |
| 94320 | ADD | 0.116166 | 0.116166 | 0.0 | 0 | RESOLVED_ZERO_DELTA | SIZED |

ADD zero-increment rows were processed correctly before final failure.

93990 REDUCE was directionally processed before final failure:

```text
target_weight moved from 0.064251 to 0.048188
transaction_delta_weight = 0.016063
pm_action = REDUCE
membership_intent = REDUCE_CANDIDATE
```

Its quantity remained unresolved because reference price was unavailable, but that is not the first failure and not the cause of the `strategy_shadow_generation_error`.

## D36 Relationship

D36 is analogous, not directly reusable as-is.

D36 established retained-baseline cap semantics for existing single-name position cap validation. D41 is the aggregate-level equivalent: Position Sizing must distinguish passive retained baseline above a lowered dynamic gross target from a true aggregate overweight violation.

The reusable principle is:

```text
existing baseline retention with no positive transaction delta can be valid when authority evidence proves passive convergence
```

The exact D36 implementation should not be blindly copied because the D41 failure is in aggregate target exposure validation, not single-name concentration validation.

## D39 Relationship

D39 is not the defective producer.

D39 correctly changed Portfolio Construction to allow:

```text
OVER_TARGET_EXISTING_BASELINE
PASSIVE_CONVERGENCE
positive_increment_allowed = false
accepted positive increments = 0
```

D39 exposed a downstream Position Sizing contract gap. Causality is:

```text
EXPECTED_EXPOSURE
```

It is expected that D39 would surface this if Position Sizing still enforced `total_target_weight <= target_gross_exposure_ratio` unconditionally.

## Root Cause

Root cause:

```text
Position Sizing rejects aggregate total_target_weight above target_gross_exposure_ratio even when Portfolio Construction has authoritative passive-convergence evidence that existing baseline is above the lowered dynamic target and positive increments are suppressed.
```

Not root cause:

```text
PS_ROW_PROCESSING_EXCEPTION
PS_FINALIZATION_EXCEPTION
PS_PASSIVE_CONVERGENCE_STATE_PROPAGATION_GAP
Portfolio Construction D39 defect
Runtime Planning defect
```

## Minimal Repair Scope

Next Phase:

```text
Phase28-D42
```

Minimal repair scope:

```text
Position Sizing aggregate validation and artifact materialization for authoritative passive convergence state from Portfolio Construction.
```

D42 should repair only Position Sizing:

```text
consume PC incremental_budget_reconciliation aggregate_exposure_state and transition_mode
allow aggregate total_target_weight above target only when OVER_TARGET_EXISTING_BASELINE / PASSIVE_CONVERGENCE evidence is present
require positive_increment_allowed = false
require accepted positive increments = 0
preserve true aggregate conflicts as BLOCK
```

Do not change:

```text
Portfolio Construction D39
Runtime Planning
Pending
Approval
Submit
Broker
Config
Schema
Threshold
```

## Evidence

Evidence directory:

```text
reports/phase28_d41_position_sizing_post_passive_convergence_generation_error_root_cause/
```

Files:

```text
position_sizing_exception_trace.json
20230531_vs_20230601_ps_input_diff.json
20230601_ps_row_inventory.json
passive_convergence_state_propagation_audit.json
aggregate_target_validator_audit.json
d39_causality.json
first_failure_point.json
root_cause.json
minimal_repair_scope.json
next_phase_contract.json
```
