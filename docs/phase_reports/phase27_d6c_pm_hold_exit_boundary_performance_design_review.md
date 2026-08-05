# Phase27-D6-C PM HOLD / EXIT Boundary Performance Design Review

## 1. Scope

Phase27-D6-C freezes the PM HOLD / REDUCE / EXIT Expected Edge boundary design and integrates it into common SoT.

```text
Implementation Change: false
PM Logic Change: false
Runtime Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D6C_PM_HOLD_EXIT_BOUNDARY_FROZEN_COMMON_SOT_UPDATED
```

Supporting:

```json
{
  "hold_boundary": "FROZEN",
  "exit_boundary": "FROZEN",
  "reduce_review": "COMPLETE",
  "risk_review": "UPDATED",
  "common_sot": "UPDATED",
  "implementation_entry": "READY_FOR_PM_BOUNDARY_IMPLEMENTATION"
}
```

## 3. Boundary Design

```text
Expected Edge adequate
  -> HOLD

Expected Edge / risk-reward weakening while campaign optionality remains
  -> REDUCE candidate

Expected Edge insufficient, continuation broken, severe risk, or Safety full-close requirement
  -> EXIT
```

HOLD is active continuation. A small Expected Edge decline does not automatically become EXIT.

REDUCE remains a distinct Risk Review / campaign-preserving exposure-trim concept. D6-C does not remove REDUCE.

EXIT is full close for insufficient Expected Edge, broken continuation/signal, severe risk, or Safety. Trend alone and profit alone are not EXIT authority.

## 4. Risk Review

Profit alone does not create action. Large embedded gain plus drawdown, volatility, concentration, or changed risk/reward can be supporting Risk Review evidence that affects Expected Edge.

## 5. Common SoT Updated

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/position_management_decision_trace_contract.md
docs/02_architecture/autonomous_ai_operations_architecture.md
```

## 6. Open Questions

Expected Edge numeric representation, HOLD/REDUCE/EXIT thresholds, Risk Review threshold, Profit Review threshold, REDUCE necessity, and ADD boundary remain open for later implementation design.

## 7. Evidence

```text
reports/phase27_d6c_pm_hold_exit_boundary_performance_design_review
```

No Runtime, PM implementation, Historical, fresh-run, resume, 10BD, 100BD, or long regression was executed.

