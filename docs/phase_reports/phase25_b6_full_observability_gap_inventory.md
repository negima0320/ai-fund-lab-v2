# Phase25-B6 Full Observability Gap Inventory

## Primary Judgment

`PHASE25_B6_CRITICAL_OBSERVABILITY_GAPS_CONFIRMED`

## Executive Summary

Phase25-B6 reviewed whether Production / Demo / Historical common Runtime evidence can explain why major runtime decisions were made.

Conclusion: Runtime evidence is `PARTIAL` overall. It often shows what happened, but it does not always prove why a specific authority, source, constraint, guard, fallback, or old path status won.

The largest observability failure is not missing artifacts. It is missing decision-level materialization of:

- selected authority
- authority winner
- binding constraint
- old consumer used
- old config used
- old schema used
- old fallback used

Therefore, Phase26 must add explicit materialization of runtime decision rationale before Architecture Conformance or Migration Completion can be closed.

## Scope

Reviewed minimum B6 scope:

- Authority
- Capital
- Planning
- Position Count
- Cash / Exposure
- Accepted Generation
- Current
- Submit
- Safety
- Runtime old consumer/config/schema/fallback usage

## Classification Summary

| Classification | Count |
|---|---:|
| `OBSERVABILITY_COMPLETE` | 0 |
| `PARTIAL` | 7 |
| `NOT_OBSERVABLE` | 0 |
| `NOT_MATERIALIZED` | 3 |
| `UNKNOWN` | 0 |
| `EVIDENCE_REQUIRED` | 2 |

## Severity Summary

| Severity | Count |
|---|---:|
| CRITICAL | 4 |
| HIGH | 6 |
| MEDIUM | 2 |
| LOW | 0 |

## Critical Observability Gaps

### P25-GAP-OBS-AUTH-001

Selected authority and runtime winner are not materialized as a canonical trace.

- Severity: `CRITICAL`
- Classification: `NOT_MATERIALIZED`
- Runtime impact: Evidence cannot fully explain which authority won when multiple authorities or legacy paths coexist.

### P25-GAP-OBS-CAP-001

Active deployment capital and binding capital constraint are not materialized.

- Severity: `CRITICAL`
- Classification: `NOT_MATERIALIZED`
- Runtime impact: Evidence cannot fully explain whether BUY size, no-BUY, idle cash, or exposure gap was caused by current equity, buying power, fixed evaluation capital, exposure cap, cash buffer, lot size, or submit guard.

### P25-GAP-OBS-GEN-001

Selected Accepted Generation and fallback usage are not fully proven by runtime evidence.

- Severity: `CRITICAL`
- Classification: `EVIDENCE_REQUIRED`
- Runtime impact: Evidence cannot prove across modes whether the intended business-date generation or a fallback/default generation was consumed.

### P25-GAP-OBS-RUNTIME-001

Old consumer, config, schema, and fallback usage are not materialized per runtime decision.

- Severity: `CRITICAL`
- Classification: `NOT_MATERIALIZED`
- Runtime impact: Evidence cannot prove old path zero for Production, Demo, and Historical decisions.

## High Observability Gaps

| Gap ID | Domain | Classification | Summary |
|---|---|---|---|
| `P25-GAP-OBS-PLAN-001` | Planning | `PARTIAL` | Binding constraint and candidate drop reason are incomplete |
| `P25-GAP-OBS-POS-001` | Position Count | `PARTIAL` | Requested/allowed/rejected count and authority source are incomplete |
| `P25-GAP-OBS-EXP-001` | Cash / Exposure | `PARTIAL` | Target/actual/difference can be observed, but reason is incomplete |
| `P25-GAP-OBS-CUR-001` | Current | `PARTIAL` | Broker/ledger/projection/current source precedence is incomplete |
| `P25-GAP-OBS-SUBMIT-001` | Submit | `PARTIAL` | Submit binding constraint and rejected constraint are incomplete |
| `P25-GAP-OBS-MODE-001` | Mode Parity | `EVIDENCE_REQUIRED` | Production/Demo/Historical authority deltas are incomplete |

## Medium Observability Gaps

| Gap ID | Domain | Classification | Summary |
|---|---|---|---|
| `P25-GAP-OBS-SAFE-001` | Safety | `PARTIAL` | Guard outcomes are observable, but selected guard priority is incomplete |
| `P25-GAP-OBS-OPP-001` | Opportunity Pipeline | `PARTIAL` | Funnel counts exist, but rejection attribution remains partial |

## Runtime Explainability

### Overall

`PARTIAL`

Runtime evidence can often answer what happened. It cannot yet answer all required why questions.

### BUY Did Not Happen

Required explanation:

- Authority
- Constraint
- Reason
- Evidence
- Old path zero

Current state: `PARTIAL`

Daily Evaluation Evidence can help explain opportunity funnel counts, but cannot always identify the binding constraint and old path absence.

### BUY Happened

Required explanation:

- selected authority
- selected quantity source
- selected notional source
- capital base
- buying power
- submit constraint
- old path zero

Current state: `PARTIAL`

The submitted order is visible, but the full decision chain is not always materialized.

### Accepted Generation

Current state: `EVIDENCE_REQUIRED`

Runtime must materialize selected generation, source path, business date, fallback flag, fallback reason, mode, and old generation path zero.

### Capital Deployment

Current state: `NOT_MATERIALIZED`

Runtime must materialize active deployment capital, binding capital constraint, selected capital source, rejected capital sources, and submit-side capital limit.

## Phase26 Materialization Requirements

Phase26 must materialize decision rationale, not only output artifacts.

Required artifacts:

- `daily/<business_date>/authority/selected_authority_trace.json`
- `daily/<business_date>/capital/capital_authority_trace.json`
- `daily/<business_date>/planning/planning_constraint_trace.json`
- `daily/<business_date>/planning/position_count_trace.json`
- `daily/<business_date>/evaluation/cash_exposure_reason_trace.json`
- `daily/<business_date>/generation/accepted_generation_trace.json`
- `daily/<business_date>/current/current_source_trace.json`
- `daily/<business_date>/submit/submit_decision_trace.json`
- `daily/<business_date>/safety/safety_guard_trace.json`
- `daily/<business_date>/runtime/legacy_usage_trace.json`
- `daily/<business_date>/runtime/mode_authority_trace.json`

Minimum common fields:

- component
- decision_id
- business_date
- runtime_mode
- selected_source
- selected_authority
- source_path
- source_hash
- binding_constraint
- decision_reason
- old_consumer_used
- old_config_used
- old_schema_used
- old_fallback_used
- observability_status

`UNKNOWN` or `NOT_OBSERVABLE` may be used only when the producer cannot determine the value from PIT-safe runtime evidence.

## Recommended Next Task

`Phase25-B7 Gap Severity and Phase26 Prioritization`

Recommended focus:

1. Rank B1-B6 gaps into Phase26 repair order.
2. Separate critical migration repairs from observability-only repairs.
3. Define Phase26 entry gate and completion gate.
4. Convert materialization requirements into concrete Phase26 Codex tasks.

## Created Files

- `docs/phase_reports/phase25_b6_full_observability_gap_inventory.md`
- `reports/phase_reports/phase25_b6_full_observability_gap_inventory.json`
- `reports/phase_reports/phase25_b6_observability_gap_inventory.json`
- `reports/phase25_b6_full_observability_gap_inventory/authority_observability.md`
- `reports/phase25_b6_full_observability_gap_inventory/planning_observability.md`
- `reports/phase25_b6_full_observability_gap_inventory/capital_observability.md`
- `reports/phase25_b6_full_observability_gap_inventory/accepted_generation_observability.md`
- `reports/phase25_b6_full_observability_gap_inventory/runtime_explainability.md`
- `reports/phase25_b6_full_observability_gap_inventory/phase26_materialization.md`
- `reports/phase25_b6_full_observability_gap_inventory/validation_results.md`

## Validation

Validation performed:

- JSON syntax validation for B6 summary
- JSON syntax validation for B6 observability gap inventory
- Required evidence file presence check

Runtime validation:

- Not executed

Historical tests:

- Not executed

Behavioral changes:

- Runtime changes: none
- Strategy changes: none
- Planning changes: none
- Submit changes: none
- Safety changes: none

