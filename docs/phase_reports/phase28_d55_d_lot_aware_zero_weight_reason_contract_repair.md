# Phase28-D55-D: Lot-Aware Zero-Weight Reason Contract Repair

## Primary Judgment

```text
PHASE28_D55_D_LOT_AWARE_ZERO_WEIGHT_REASON_CONTRACT_REPAIRED_SHORT_REGRESSION_PASS_FRESH_100BD_READY
```

D55-D repaired the Portfolio Construction final-pass contract violation exposed by run `runtime-test-historical-smoke-20260808T223705253100Z` on `2023-04-03`. No fresh run, resume, long historical run, runtime mutation, config change, threshold change, SELL semantic change, Submit Guard change, D55-A semantic change, D55-B lot-feasibility semantic change, or D55-C orchestration order change was executed.

## Root Cause

The downstream Runtime failure was:

```text
morning -> strategy_runtime_planning_blocked -> upstream_block:INCOMPATIBLE_SCHEMA
```

The first confirmed failed producer was the active Strategy `portfolio_construction.json` final pass:

```text
schema_version = portfolio_construction_shadow_error.v1
producer_result_status = BLOCK
error = missing_zero_weight_reason:3
```

Direct root cause:

```text
PC final lot-aware reallocation could reduce a PASS member to target_weight = 0
without materializing target_weight_resolution.zero_weight_reason.
```

Target evidence:

```text
symbol = 59350
draft target_weight = 0.18
PS preflight lot_feasible = false
PS preflight minimum_executable_weight = 0.45849
final PC decision = preserve cash / zero the candidate
missing field = target_weight_resolution.zero_weight_reason
```

## Implemented Repair

Changed only:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
```

Repair contract:

```text
If final lot-aware reallocation produces target_weight = 0
and target_weight_resolution.status = PASS
and no zero_weight_reason already exists,
PC materializes the lot-aware skipped reason as zero_weight_reason.
```

Materialized reasons:

```text
lot_or_broker_infeasible
minimum_lot_exceeds_concentration_cap
minimum_lot_exceeds_remaining_budget
lot_aware_zero_weight_preserved
```

For the target reproduction, `59350` now has:

```text
target_weight = 0.0
target_membership = false
zero_weight_reason = minimum_lot_exceeds_concentration_cap
portfolio_construction.v1 = PASS
```

## Validation

```text
py_compile = PASS
D55-B focused lot-aware regression = 4 passed
D55-A / D55-B / D55-C core regression = 131 passed
Runtime Planning / SELL / broker representative regression = 66 passed
Target run artifact reproduction using /private/tmp output = PASS
```

The target reproduction read existing run artifacts only and wrote the repaired output to:

```text
/private/tmp/phase28_d55_d_pc_final_reproduction.json
```

No existing 100BD artifact was mutated.

## Execution Flags

```text
Implementation changed = YES
Config changed = NO
Schema changed = NO
Threshold changed = NO
Runtime Authority violation = NO
Fresh run executed = NO
Resume executed = NO
Long Historical executed = NO
Runtime mutated = NO
```

## Fresh Gate

```text
Fresh 100BD Entry = READY
Recommended Next Phase = Phase28-D56 Fresh 100BD Runtime Conformance Run
```

## Deliverables

```text
docs/phase_reports/phase28_d55_d_lot_aware_zero_weight_reason_contract_repair.md
reports/phase_reports/phase28_d55_d_lot_aware_zero_weight_reason_contract_repair.json
reports/phase28_d55_d_lot_aware_zero_weight_reason_contract_repair/
```
