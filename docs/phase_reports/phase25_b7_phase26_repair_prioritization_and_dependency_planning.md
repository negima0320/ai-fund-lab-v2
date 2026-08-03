# Phase25-B7 Phase26 Repair Prioritization and Dependency Planning

## Primary Judgment

`PHASE25_B7_PHASE26_EXECUTION_READY`

## Executive Summary

Phase25-B7 converts B1 through B6 findings into a Phase26 repair plan.

No Runtime, Strategy, Planning, Submit, Safety, schema, or config behavior was changed in this task.

The Phase26 repair path is now a single ordered path:

```text
Closure Foundation

↓

Capital

↓

Position Count

↓

Cash / Exposure

↓

Planning / Submit / Current / Generation

↓

Observability

↓

Regression

↓

Performance Readiness
```

Performance improvement remains blocked until the architecture repair path proves that Runtime decisions are no longer ambiguous.

## Inputs

- Phase25-B1 Architecture Conformance Matrix
- Phase25-B2 Legacy Authority and Consumer Inventory
- Phase25-B3 Authority Conflict Inventory
- Phase25-B4 Migration Completion Audit
- Phase25-B5 Closure Gate Failure Review
- Phase25-B6 Observability Gap Inventory
- Phase25 Architecture Conformance Gap Inventory

## Repair Classification

| Classification | Phase26 Meaning |
|---|---|
| Authority Repair | Select one runtime authority winner and define source priority |
| Legacy Retirement | Remove or reclassify old active authority from Production/Demo/Historical runtime |
| Migration Completion | Prove producer, artifact, schema, consumer, runtime evidence, and old-path-zero |
| Observability | Materialize selected authority, binding constraint, reason, and old-path usage |
| Closure | Apply B5 closure contract to every Phase26 step |
| Regression | Prove compile/unit/short/mode/negative/full migration behavior |
| Documentation | Update SoT and closure labels after evidence exists |

## Critical Repair Order

| Order | Component | Reason |
|---:|---|---|
| 0 | Closure and negative assertion foundation | Prevents repeating Phase21-24 closure failure. |
| 1 | Capital | Root dependency for compound reinvestment, sizing, exposure, planning, and submit. |
| 2 | Position Count | Controls number of planned/allowed positions and depends on repaired capital semantics. |
| 3 | Cash / Exposure | Controls deployment, cash drag, safety boundary, and planning feasibility. |
| 4 | Portfolio Policy / Position Sizing | Aligns dynamic targets and per-position notional with active runtime authority. |
| 5 | Runtime Planning / Planning Authority | Consumes repaired capital, position, exposure, and sizing decisions. |
| 6 | Submit / Submit Guard | Must consume the same authority as planning and prove legacy preflight cap is not active. |
| 7 | Current / Ledger / Broker / Projection | Defines cash, equity, buying power, and projection source precedence. |
| 8 | Accepted Generation / Temporal | Proves candidate source, business date, and fallback-zero across modes. |
| 9 | Observability Materialization | Makes runtime winners, constraints, reasons, and old-path-zero visible. |
| 10 | Full Migration Regression | Proves repaired components are actually active and old paths are absent. |
| 11 | Performance Readiness | Reopens performance evaluation only after architecture ambiguity is closed. |

## Phase26 Steps

### Step0: Architecture Foundation

Purpose:

- Install B5 closure contract before accepting any repair.
- Require old-path-zero and FULL_MIGRATION_REGRESSION.

Acceptance:

- Closure label type declared
- Producer, Artifact, Consumer, Runtime Evidence required
- Old Consumer Zero required
- Old Config Zero required
- Old Schema Zero required
- Old Fallback Zero required
- Negative Assertion required
- FULL_MIGRATION_REGRESSION required

### Step1: Authority Repair

Purpose:

- Repair Capital authority first.
- Resolve fixed evaluation capital versus active deployment capital.
- Resolve per-position notional cap source.

Acceptance:

- Capital authority winner selected
- Fixed `evaluation_capital=1000000` no longer acts as active deployment capital
- Runtime evidence proves selected capital source and binding constraint
- Old capital config authority is zero or explicitly safety-only

### Step2: Legacy Retirement

Purpose:

- Retire active fixed position-count and cash/exposure authorities.

Acceptance:

- Dynamic position count consumer active
- Fixed `max_positions=5` no longer active runtime authority
- Dynamic cash/exposure consumer active
- Fixed target/cash/max exposure no longer active runtime target authority
- Safety hard limits remain fail-closed and separately classified

### Step3: Migration Completion

Purpose:

- Complete Planning, Submit, Current, Accepted Generation, Temporal, Pending/Resume consumer proof.

Acceptance:

- Production consumer active
- Demo consumer active
- Historical consumer active
- New producer, schema, artifact, and runtime consumer aligned
- Old runtime path activation zero
- Mode parity evidence exists

### Step4: Observability Materialization

Purpose:

- Materialize why runtime decisions happened.

Required traces:

- Selected authority trace
- Capital authority trace
- Planning constraint trace
- Position count trace
- Cash/exposure reason trace
- Accepted generation trace
- Current source trace
- Submit decision trace
- Safety guard trace
- Runtime legacy usage trace
- Mode authority trace

### Step5: Regression

Purpose:

- Prove architecture conformance and migration completion.

Acceptance:

- Compile PASS
- Unit PASS
- Short runtime PASS
- Negative assertion PASS
- Mode parity PASS
- FULL_MIGRATION_REGRESSION PASS
- Architecture PASS only where evidence proves it

### Step6: Performance Readiness

Purpose:

- Resume Performance Evaluation after architecture ambiguity is closed.

Acceptance:

- Critical architecture gaps closed or explicitly deferred
- Critical migration gaps closed or explicitly deferred
- Critical observability gaps closed
- Historical test ladder ready for user execution

## Dependency Plan

```text
Capital

↓

Position Count

↓

Cash / Exposure

↓

Position Sizing and Portfolio Policy

↓

Planning Authority and Aggregate Feasibility

↓

Submit / Submit Guard

↓

Current / Ledger / Broker / Projection

↓

Accepted Generation / Temporal

↓

Observability

↓

Regression
```

## Regression Order

1. Compile
2. Unit
3. Schema validation
4. Read-only evidence validation
5. Short runtime regression
6. Negative assertion regression
7. Mode parity regression
8. Architecture conformance regression
9. User Historical Test ladder

## User Test Plan

| Timing | Test | Executor |
|---|---|---|
| After Step0 | Compile + unit + contract validation | Codex |
| After Step1 | Short runtime | Codex |
| After Step2 | Short runtime + negative assertion | Codex |
| After Step3 | 10BD | User |
| After Step4 | 20BD | User |
| After Step5 | 60BD | User |
| Phase26 closure candidate | 200BD | User |
| Phase26 final closure | 252BD | User |

## Stop Conditions

- Runtime crash
- Old consumer/config/schema/fallback usage in a repaired component
- Missing selected authority in a repaired component
- Missing binding constraint in a repaired component
- Corporate Action Manual Review remains a valid fail-closed stop

## Recommended Next Task

`Phase26-Step0 Architecture Foundation and Closure Gate Contract Implementation`

## Created Files

- `docs/phase_reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning.md`
- `reports/phase_reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning.json`
- `reports/phase_reports/phase26_repair_master_plan.json`
- `reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning/repair_order.md`
- `reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning/dependency_graph.md`
- `reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning/phase26_steps.md`
- `reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning/regression_matrix.md`
- `reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning/acceptance_matrix.md`
- `reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning/user_test_plan.md`
- `reports/phase25_b7_phase26_repair_prioritization_and_dependency_planning/validation_results.md`

## Validation

Validation performed:

- JSON syntax validation for B7 summary
- JSON syntax validation for Phase26 repair master plan
- Required evidence file presence

Runtime validation:

- Not executed

Historical tests:

- Not executed

