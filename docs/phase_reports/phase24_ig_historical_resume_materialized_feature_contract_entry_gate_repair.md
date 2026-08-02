# Phase24-IG Historical Resume Materialized Feature Contract Entry Gate Repair

## 1. Primary Judgment

`PHASE24_IG_RESUME_FEATURE_CONTRACT_ENTRY_GATE_REPAIRED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

## 2. Repair Summary

`validate_plan_entry_gate` now supports resume-aware validation:

```text
completed day -> run-scoped materialized feature evidence
failed day    -> run-scoped materialized feature evidence
future day    -> plan expectation
```

Normal plan/run validation keeps the existing behavior.

## 3. Safety Properties

The repair does not disable the Entry Gate. Completed and failed days still fail closed when run-scoped materialized feature evidence is missing or mismatched.

The repair does not mutate:

```text
Run State
Ledger
Current
Pending
Feature Contracts
Run Evidence
```

## 4. Target Read-only Verification

The repaired gate was applied read-only to the target run's `plan.json` and `run_state.json`.

Result:

```text
target validate PASS
resume target = 2023-06-14:morning
```

## 5. Operator Action

Runtime resume remains Operator-owned and was not executed by Codex.
