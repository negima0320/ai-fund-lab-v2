# Phase23-AS Portfolio Policy to Portfolio Construction Target Weight Authority Binding Repair

## Primary Judgment

```text
PHASE23_AS_PORTFOLIO_POLICY_TARGET_WEIGHT_AUTHORITY_BINDING_SHORT_VALIDATION_PASS
```

## Direct Root Cause

Target Run `runtime-test-historical-smoke-20260730T012530808938Z` halted because Portfolio Policy materialized `single_name_weight_cap = null`. Portfolio Construction requires `target_position_count`, `target_gross_exposure`, `cash_reserve`, and `single_name_weight_cap` to resolve Target Weight Authority. The null cap triggered `target_weight_authority_unresolved`, which correctly propagated fail-closed downstream.

## AQ Portfolio Policy Actual Output

The target run Portfolio Policy had valid `target_position_count=10`, `target_gross_exposure=0.79`, `cash_reserve=0.21`, and `deployment_posture=DEPLOY`, but `single_name_weight_cap` was null.

## Repair Summary

- Added explicit `single_name_weight_cap` authority to `configs/strategy/portfolio_policy.json`.
- Updated Portfolio Policy producer to materialize `single_name_weight_cap`, source, and authority metadata.
- Updated Portfolio Policy validation for ratio/absolute consistency.
- Updated Portfolio Construction to resolve allocation authority directly from Portfolio Policy artifact and to record Policy path/hash/decision lineage in `target_weight_authority`.
- Kept legacy Dynamic Position Count / Dynamic Cash Exposure out of the decision path.

## Target Weight Authority After Repair

`target_weight_authority` now includes Portfolio Policy artifact path/hash, decision id/hash, target position count, resolved target member count, target gross exposure, cash reserve, single-name cap, and PIT status.

## Validation

```text
py_compile: PASS
Portfolio Policy / Portfolio Construction targeted: 31 passed
Expanded Strategy regression: 124 passed
Evidence JSON validation: PASS
```

No fresh-run, resume, 1BD, 10BD, 20BD, Runtime Switch, Broker Write, or J-Quants acquisition was executed.

## Existing Run Preservation

Required runs were read-only. Hash evidence was recorded and no reclassification or mutation was performed.

## Runtime Rerun Readiness

```text
READY_FOR_1BD_RUNTIME_VALIDATION = YES
```

This is for operator execution after Evidence Review only.
