# Phase31-C0E — Alternative G Shadow Structural Revalidation

Status: COMPLETE
Task type: READ-ONLY / DIAGNOSTIC MATERIALIZATION / STRUCTURAL REVALIDATION

## PRIMARY_JUDGMENT

```text
PHASE31_C0E_ALTERNATIVE_G_SHADOW_STRUCTURAL_GATE_PASS_WITH_EXPLAINED_C0A_SCOPE_DIFFERENCE
```

The C0D Alternative G shadow successfully materialized across the full usable development window. Canonical artifacts were unchanged, PIT proof passed, future-information usage remained zero, campaign-scope leakage remained zero, production consumer count remained zero, baseline EXIT was not interfered with, and unresolved parameters were exposed explicitly.

The only material reconciliation difference versus C0A is explained: C0A counted all zeroed REDUCE rows, while the C0D/C0E shadow is scoped specifically to lot-unrepresentable REDUCE. The development run contains 324 lot-unrepresentable REDUCE rows and 20 minimum-notional-unrepresentable REDUCE rows.

STRUCTURAL_GATE:

```text
PASS
```

This does not authorize mutating Strategy implementation.

## Target

TARGET_RUN:

```text
runtime-test-historical-extended-smoke-20260818T015851711672Z
```

Path:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z
```

TARGET_WINDOW:

```text
2022-08-10 through 2022-12-15
```

DEVELOPMENT_RUN_MATERIALIZED:

```text
YES
```

Materialized artifact path:

```text
daily/<BUSINESS_DATE>/diagnostic_shadow/unrepresentable_reduce_exit_shadow.json
```

Date-level coverage:

| Status | Count |
|---|---:|
| MATERIALIZED | 86 |
| SOURCE_EVIDENCE_MISSING | 0 |
| PIT_INVALID | 0 |
| OTHER_EXPLICIT_REASON | 0 |

## Aggregate Counts

| Metric | Value |
|---|---:|
| TOTAL_BUSINESS_DAYS_SCANNED | 86 |
| TOTAL_PM_DECISION_ROWS | 997 |
| TOTAL_REDUCE_ROWS | 344 |
| REPRESENTABLE_REDUCE_COUNT | 0 |
| UNREPRESENTABLE_REDUCE_COUNT | 324 |
| ONE_LOT_UNREPRESENTABLE_COUNT | 309 |
| MULTI_LOT_UNREPRESENTABLE_COUNT | 15 |
| STRUCTURALLY_ELIGIBLE_COUNT | 324 |
| G1_IMMEDIATE_STRUCTURAL_COUNT | 1 |
| G2_PERSISTENT_STRUCTURAL_COUNT | 225 |
| G3_HYBRID_STRUCTURAL_COUNT | 226 |
| RECOVERY_BLOCKED_COUNT | 2 |
| PARAMETER_UNRESOLVED_COUNT | 225 |
| EVIDENCE_INSUFFICIENT_COUNT | 20 |
| PIT_PROOF_PASS_COUNT | 997 |
| PIT_PROOF_FAIL_COUNT | 0 |
| FUTURE_INFORMATION_USED_COUNT | 0 |
| CAMPAIGN_SCOPE_LEAK_COUNT | 0 |
| CANONICAL_ARTIFACT_MUTATION_COUNT | 0 |

Required expected values:

```text
FUTURE_INFORMATION_USED_COUNT = 0
CAMPAIGN_SCOPE_LEAK_COUNT = 0
CANONICAL_ARTIFACT_MUTATION_COUNT = 0
```

All passed.

## C0A Reconciliation

| Metric | C0A | C0E |
|---|---:|---:|
| PM REDUCE count | 344 | 344 |
| Zeroed / unrepresentable REDUCE count | 344 | 324 lot-unrepresentable |

C0A_COUNT_RECONCILIATION_STATUS:

```text
EXPLAINED_DIFFERENCE
```

Difference:

```text
20 REDUCE rows were intentional no-order because of REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL,
not REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT.
```

Examples:

- 2022-08-12 / 89180: `rounded_reduce_quantity = 1200`, `reduce_final_sell_quantity = 0`, semantic = `REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL`.
- 2022-08-15 / 36640: `rounded_reduce_quantity = 100`, `reduce_final_sell_quantity = 0`, semantic = `REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL`.
- 2022-09-29 / 33500: `rounded_reduce_quantity = 200`, `reduce_final_sell_quantity = 0`, semantic = `REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL`.

C0D/C0E are scoped to Alternative G's discrete-lot representation problem. Minimum-notional intentional no-order is adjacent but not the same family.

## 61750 Control

61750_CONTROL_STATUS:

```text
PASS
```

61750 is represented as the expected persistent one-lot unrepresentable REDUCE control case.

Summary:

| Field | Value |
|---|---|
| first shadow-observed REDUCE date | 2022-09-13 |
| last REDUCE date in usable window | 2022-12-15 |
| REDUCE rows | 63 |
| unrepresentable REDUCE rows | 63 |
| baseline PM action | REDUCE |
| reduce_intensity | LIGHT |
| current quantity | 100 |
| tradable unit | 100 |
| representation error | 0.25 |
| max prior unrepresentable REDUCE count | 62 |
| persistence state | PERSISTENCE_EVIDENCE_PRESENT |
| PIT proof | PASS |

State distribution:

| Shadow state | Rows |
|---|---:|
| PARAMETER_UNRESOLVED | 61 |
| RECOVERY_BLOCKED | 1 |
| UNREPRESENTABLE_PRESERVE | 1 |

Last usable REDUCE row, 2022-12-15:

```text
prior_unrepresentable_reduce_count = 62
deterioration_state = DETERIORATION_CONFIRMED
recovery_state = NO_RECOVERY
parameter_resolution_state = VALIDATION_REQUIRED_UNSET
shadow_state = PARAMETER_UNRESOLVED
pit_validation_state = PASS
```

C0E does not require `61750 -> EXIT`. The correct result is persistent structural eligibility with unresolved parameters.

61750_FUTURE_DELISTING_INFORMATION_USED:

```text
NO
```

The shadow uses only contemporaneous PM / PS / Runtime Planning / Strategy Intelligence / Market Context evidence through 2022-12-15.

## Winner Recovery Controls

WINNER_CONTROL_RECOVERY_REPRESENTATION_STATUS:

```text
PARTIAL
```

The shadow represents the development winner controls without hindsight and does not force EXIT. However, explicit `RECOVERY_BLOCKED` appears only when the current PM row is still REDUCE while current PIT recovery evidence is visible. Several controls recover through later HOLD/ADD states, where Alternative G is not applicable because baseline PM action is no longer REDUCE.

| Symbol | REDUCE rows | Unrepresentable | Shadow states | Interpretation |
|---|---:|---:|---|---|
| 40800 | 2 | 2 | `UNREPRESENTABLE_PRESERVE` | Preserved; no EXIT candidate. |
| 27670 | 3 | 3 | `PARAMETER_UNRESOLVED`, `UNREPRESENTABLE_PRESERVE` | Persistent evidence appears but no deterministic EXIT; no recovery hindsight used. |
| 92270 | 1 | 1 | `UNREPRESENTABLE_PRESERVE` | First-occurrence caution preserved. |
| 66330 | 9 | 9 | `PARAMETER_UNRESOLVED`, `UNREPRESENTABLE_PRESERVE` | Persistent structural cases exposed as unresolved, not forced EXIT. |
| 32050 | 10 | 10 | `PARAMETER_UNRESOLVED`, `UNREPRESENTABLE_PRESERVE` | Persistent structural cases exposed as unresolved, not forced EXIT. |

Recovery-block rows observed in the full run:

| Date | Symbol | Evidence |
|---|---|---|
| 2022-09-08 | 27880 | `HEALTHY_CONTINUATION_ENTRY`, `ADD_ALLOWED`, supportive continuation evidence |
| 2022-12-14 | 61750 | `HEALTHY_CONTINUATION_ENTRY`, `ADD_ALLOWED`, supportive continuation evidence |

RECOVERY_BLOCK_WITHOUT_CANONICAL_EVIDENCE_COUNT:

```text
0
```

## Branch Structural Audit

Immediate branch:

| Metric | Value |
|---|---:|
| IMMEDIATE_CANDIDATE_EVIDENCE_COMPLETE_COUNT | 1 |
| IMMEDIATE_CANDIDATE_EVIDENCE_INCOMPLETE_COUNT | 0 |

The single G1/G3 immediate structural candidate:

```text
date = 2022-08-22
symbol = 60540
campaign_id = pc-e801a412256c5ea9-60540-0001
reduce_intensity = STRONG
shadow_state = IMMEDIATE_EXIT_CANDIDATE
```

This does not mean production EXIT is authorized. It means the shadow can structurally identify an immediate candidate from current PIT semantics without downstream conversion.

Persistent branch:

| Metric | Value |
|---|---:|
| PERSISTENT_CANDIDATE_COUNT | 225 |
| PERSISTENT_PARAMETER_RESOLVED_COUNT | 0 |
| PERSISTENT_PARAMETER_UNRESOLVED_COUNT | 225 |
| PERSISTENT_EVIDENCE_INSUFFICIENT_COUNT | 0 |

This is expected under C0C: persistence parameters remain unset and must be validated later.

## Parameter-Unresolved Anatomy

PARAMETER_UNRESOLVED_BY_CAUSE:

| Cause | Count |
|---|---:|
| PERSISTENCE_MINIMUM_UNSET | 225 |
| RECENT_WINDOW_UNSET | 225 |
| DETERIORATION_SUFFICIENCY_UNSET | 225 |
| RECOVERY_RESET_STRENGTH_UNSET | 225 |
| REPRESENTATION_ERROR_MATERIALITY_UNSET | 225 |

Minimum parameter set requiring later validation:

- persistence minimum;
- recent-window length;
- deterioration sufficiency semantics;
- recovery reset strength;
- representation-error materiality.

C0E chooses no values.

## Evidence-Insufficient Anatomy

EVIDENCE_INSUFFICIENT_BY_CAUSE:

| Cause | Count |
|---|---:|
| REDUCE_ZEROED_BY_MINIMUM_NOTIONAL_NOT_LOT_SCOPE | 20 |

These cases are not a C0D bridge failure for Alternative G. They are intentional no-order REDUCE rows, but the reason is minimum-notional rather than discrete-lot unrepresentability.

## PIT / Scope / Interference Audits

PIT_PROOF_PASS_RATE:

```text
997 / 997 = 100%
```

FUTURE_INFORMATION_USED:

```text
NO
```

CAMPAIGN_SCOPE_LEAK_COUNT:

```text
0
```

RESTART_DETERMINISM_REAL_RUN:

```text
PASS
```

Representative dates were rematerialized from artifacts and produced identical diagnostic shadow artifacts:

```text
2022-08-12
2022-08-15
2022-09-08
```

REPRESENTABLE_REDUCE_FALSE_ESCALATION_COUNT:

```text
0
```

Development run has no representable REDUCE sample:

```text
REPRESENTABLE_REDUCE_COUNT = 0
```

Therefore normal representable REDUCE protection is covered by C0D focused tests, not by this development run.

BASELINE_EXIT_INTERFERENCE_COUNT:

```text
0
```

Baseline EXIT rows inspected:

```text
120
```

INVALID_BUY_DEPENDENCY_COUNT:

```text
0
```

B10_BUSINESS_AUTHORITY_DEPENDENCY:

```text
NO
```

PRODUCTION_CONSUMER_COUNT:

```text
0
```

Repository search found the shadow referenced only by the diagnostic producer and focused tests.

## Canonical Artifact Mutation

Before and after materialization, canonical artifacts were hash-compared for all 86 dates across:

- `strategy/position_management.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `strategy/strategy_intelligence.json`
- `strategy/market_context.json`
- `strategy/portfolio_construction.json`
- `morning/pending_generation_evidence.json`
- `execution/fills.json` where present

CANONICAL_ARTIFACT_MUTATION_COUNT:

```text
0
```

ACTUAL_TRADING_PATH_MUTATED:

```text
NO
```

## Verification Commands

Focused tests and regressions:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_c0e_pycache python3 -m pytest -q \
  tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py \
  tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_d34_reduce_intensity_quantities_are_partial_sells \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase29_l21t_ad_runtime_planning_preserves_reduce_intentional_no_order_semantic
```

Result:

```text
22 passed in 3.83s
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase31_c0e_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py \
  tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py
```

Result:

```text
PASS
```

## Required Output Summary

DEVELOPMENT_RUN_MATERIALIZED:

```text
YES
```

C0A_COUNT_RECONCILIATION_STATUS:

```text
EXPLAINED_DIFFERENCE
```

61750_CONTROL_STATUS:

```text
PASS
```

WINNER_CONTROL_RECOVERY_REPRESENTATION_STATUS:

```text
PARTIAL
```

STRUCTURAL_GATE:

```text
PASS
```

PERFORMANCE_VALIDATION_AUTHORIZED:

```text
YES
```

This authorizes only separate validation-period evaluation work. It does not authorize mutating Strategy implementation.

MUTATING_IMPLEMENTATION_AUTHORIZED:

```text
NO
```

LONG_HISTORICAL_EXECUTED:

```text
NO
```

## Limitations

- C0E is structural revalidation only, not profitability validation.
- C0E does not tune persistence count, recent windows, deterioration thresholds, or recovery thresholds.
- The development run has no representable REDUCE sample, so representable REDUCE protection relies on focused C0D tests.
- Winner recovery controls are represented without hindsight, but explicit `RECOVERY_BLOCKED` appears only when recovery evidence coincides with a REDUCE row.
- Minimum-notional zeroed REDUCE is adjacent but outside Alternative G's current discrete-lot scope.

## NEXT_TASK_RECOMMENDATION

```text
Phase31-C0F — Alternative G Validation-Period Parameter / Performance Evaluation Design or Execution Preparation
```

Do not execute C0F in this task.

## Final Questions

### 1. Does C0D shadow successfully materialize across the real development run?

```text
YES
```

### 2. Does it reproduce the lot-unrepresentable REDUCE population found in C0A?

```text
EXPLAINED_DIFFERENCE
```

It reproduces all 344 PM REDUCE rows. It identifies 324 discrete-lot-unrepresentable rows. The remaining 20 C0A zeroed REDUCE rows are minimum-notional unrepresentable, not discrete-lot unrepresentable.

### 3. Does 61750 appear as the expected persistent one-lot unrepresentable REDUCE control case?

```text
YES
```

### 4. Can known recovery/winner controls be represented without hindsight?

```text
PARTIAL
```

They are preserved without EXIT and without hindsight. Explicit recovery-block semantics appear only where recovery evidence is present on a REDUCE row.

### 5. Are G1 immediate and G2 persistent branches structurally usable on real evidence?

```text
YES
```

G1 has 1 structural candidate. G2 has 225 persistent structural candidates, all parameter-unresolved as designed.

### 6. Are unresolved parameters explicitly exposed rather than hidden as constants?

```text
YES
```

### 7. Is all shadow decision evidence PIT-safe?

```text
YES
```

### 8. Did any shadow operation mutate canonical trading artifacts?

```text
NO
```

### 9. Is the shadow structurally ready to proceed to a separate validation period?

```text
YES
```

### 10. Is mutating Alternative G implementation authorized?

```text
NO
```
