# Phase28-D26: Historical Morning Safety Ordering Regression Root Cause Diagnosis

## Executive Summary

Primary Judgment:

```text
PHASE28_D26_D19_MORNING_ORDERING_REGRESSION_CONFIRMED
```

Regression confirmed:

```text
YES
```

However, the confirmed regression is not a Historical Safety ordering regression. The previous and current 2023-04-04 morning manifests both show:

```text
safety_operation_guard
-> REVIEW_REQUIRED / SAFETY_MISSING / safety decision evidence missing
-> historical_safety_authority
-> PASS / NEUTRAL / data_readiness_historical_temporal_authority
```

The first behavior difference is after `environment_capability_decision`, where the current run includes D19's same-day `position_management_ai_runtime_producer` before formal Strategy generation. That new PM input changes Strategy Portfolio Construction and causes the actual halt.

## Compared Runs

Previous successful run:

```text
runtime-test-historical-smoke-20260806T053322547871Z
```

Evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T053322547871Z/daily/2023-04-04/morning/runtime_manifest.json
```

Result:

```text
2023-04-04 morning exit_code = 0
phase23_i_strategy_planning_authority_pipeline = PASS
```

Current failed run:

```text
runtime-test-historical-smoke-20260806T223320442615Z
```

Evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T223320442615Z/daily/2023-04-04/morning/runtime_manifest.json
```

Result:

```text
2023-04-04 morning exit_code = 10
final_state = BLOCKED
reason = morning pipeline blocked: strategy_runtime_planning_blocked
```

## Old vs New Stage Order

Old order around the relevant boundary:

```text
safety_operation_guard
current_sot_preflight
runtime_state_refresh
runtime_data_readiness_gate
historical_safety_authority
candidate_opportunity_ai_runtime_producer
environment_capability_decision
phase22_strategy_artifact_generation
phase23_i_strategy_planning_authority_pipeline
```

New order:

```text
safety_operation_guard
current_sot_preflight
runtime_state_refresh
runtime_data_readiness_gate
historical_safety_authority
candidate_opportunity_ai_runtime_producer
environment_capability_decision
position_management_ai_runtime_producer
phase22_strategy_artifact_generation
phase23_i_strategy_planning_authority_pipeline
```

First differing boundary:

```text
after environment_capability_decision
```

First changed stage:

```text
position_management_ai_runtime_producer
```

## Safety Authority Contract

Historical replay canonical Safety authority:

```text
data_readiness_historical_temporal_authority
```

For downstream planning, `latest_safety_decision.json` is not required when Data Readiness provides historical neutral authority. In code, `run_daily_operation.py` builds the effective safety decision after Data Readiness:

```text
_effective_runtime_safety_decision(...)
```

and passes that effective authority to Strategy Planning:

```text
_strategy_planning_safety_authority_payload(...)
```

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:506
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:515
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1917
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:1951
```

Architecture evidence:

```text
docs/02_architecture/runtime_architecture_v2.md:2592
docs/03_operations/runtime_test_command_guide.md:812
```

Important nuance:

```text
safety_operation_guard itself still consumes .runtime/runtime_state/safety/latest_safety_decision.json before Data Readiness in both runs.
```

That ordering is unchanged and did not stop the previous run. The historical authority is materialized later and is the authority consumed by downstream Strategy Planning.

## Direct Halt Producer

Direct halt producer:

```text
phase23_i_strategy_planning_authority_pipeline
```

Direct halt reason:

```text
strategy_runtime_planning_blocked
```

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:189
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:201
```

The consumer returns `BLOCKED` when `runtime_planning.json` has:

```text
producer_result_status = BLOCK
```

## Root Blocking Producer

Root blocking producer:

```text
portfolio_construction
```

Current run evidence:

```text
portfolio_construction producer_result_status = BLOCK
reason_codes include total_target_weight_above_target_gross_exposure
total_target_weight = 0.731271
target_gross_exposure = 0.72
target_weight_sum_tolerance = 0.0000025
```

The current `runtime_planning.json` then propagates:

```text
upstream_block:SOURCE_BLOCKED
upstream_block_propagation:position_sizing_or_portfolio_construction
```

and `phase23_i_strategy_planning_authority_pipeline` refuses to commit pending.

## D19 Causality

D19 direct causality:

```text
YES
```

D19 inserted the same-day Runtime PM producer before formal Strategy generation:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:617
```

Current PM output:

```text
43880 = HOLD
83060 = ADD
94320 = ADD
```

Previous Strategy PM artifact for the same holdings:

```text
43880 = UNRESOLVED
83060 = UNRESOLVED
94320 = UNRESOLVED
```

This changed Portfolio Construction from:

```text
PASS, total_target_weight = 0.36
```

to:

```text
BLOCK, total_target_weight = 0.731271 > target_gross_exposure = 0.72
```

## D25 Causality

D25 direct causality:

```text
NO
```

D25 changed Runtime Planning SELL_EXIT authority:

```text
negative delta + target_quantity zero + no PM_EXIT -> UNRESOLVED
```

But the current direct root block occurs earlier in Portfolio Construction. Runtime Planning is blocked by upstream source status and never reaches a clean executable SELL_EXIT/BUY_ADD quantity decision.

## Baseline Mismatch Relation

Classification:

```text
PARALLEL_REVIEW_NON_BLOCKING_DIAGNOSTIC
```

`BASELINE_CURRENT_SEMANTICS_MISMATCH` appears in the morning manifest, but it is not included in the current Strategy `root_reason_codes`, and it is not the direct cause of `SAFETY_MISSING` or `strategy_runtime_planning_blocked`.

## Regression Determination

```text
Same date previously passed: YES
Same profile: YES
Same historical safety policy expected: YES
Current behavior changed: YES
Regression confirmed: YES
```

Not a Safety regression:

```text
Safety guard REVIEW_REQUIRED existed in both runs.
Historical safety authority PASS existed in both runs.
Downstream Strategy safety binding existed in both runs.
```

Confirmed regression point:

```text
D19 same-day PM producer changed Strategy input before Portfolio Construction.
```

## Minimal Repair Scope

Recommended minimal scope:

```text
Repair Strategy Portfolio Construction / same-day PM exposure allocation semantics so D19 PM ADD/HOLD authority can be consumed without producing gross exposure over-allocation on historical replay.
```

Must preserve:

```text
D19 same-day PM ADD wiring
D25 SELL authority guard
historical safety authority override
```

Do not repair by:

```text
rolling back D19 wholesale
rolling back D25
requiring latest_safety_decision.json for historical replay
changing Safety thresholds
masking total_target_weight_above_target_gross_exposure
```

## Required Next Tests

Minimum next-phase regression fixtures:

```text
historical missing latest_safety_decision uses data_readiness historical authority
D19 same-day PM producer remains before Strategy generation
PM HOLD/ADD/ADD on 43880/83060/94320 does not overallocate gross exposure
D25 no-PM_EXIT target-zero SELL_EXIT guard remains intact
production/demo missing real Safety remains fail-closed
```

## Deliverables

```text
docs/phase_reports/phase28_d26_historical_morning_safety_ordering_regression_root_cause.md
reports/phase_reports/phase28_d26_historical_morning_safety_ordering_regression_root_cause.json
reports/phase28_d26_historical_morning_safety_ordering_regression_root_cause/
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
Phase28-D27 D19 Same-day PM Portfolio Exposure Allocation Repair Design
```
