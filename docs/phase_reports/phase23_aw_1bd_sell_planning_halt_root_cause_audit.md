# Phase23-AW 1BD Sell Planning HALT Root Cause Audit

## Primary Judgment

```text
PHASE23_AW_SELL_PLANNING_HALT_ROOT_CAUSE_AUDIT_COMPLETE
```

## Scope

Read-only audit only. Production code, tests, fixtures, existing runtime run artifacts, Broker state, J-Quants data, and Runtime state were not modified.

Target run:

```text
runtime-test-historical-smoke-20260730T030213466506Z
```

Business date:

```text
2026-07-06
```

Stage:

```text
sell_planning
```

## Primary Findings

The 1BD run halted before sell planning execution. The inner Runtime CLI returned exit code `20`; the Runtime Test runner aggregated this to exit code `30`.

The direct Runtime reason was:

```text
historical_safety_temporal_authority_missing
```

The deepest concrete reason was:

```text
historical_pending_safety_authority_mismatch
```

The first invalid artifact is the active pending current slot:

```text
.runtime/pending_order_plan/pending_order_plan.json
```

The run-scoped Data Readiness artifact embedded the pending payload and showed:

```text
state = APPROVED
active pending = true
target_session_date = 2026-07-06
safety_context = null
approval.safety_decision_id = ""
approval.safety_policy_version = ""
```

Data Readiness therefore reported:

```text
pending_safety_evidence_missing
historical_safety_temporal_authority_missing
```

## Root Cause

Morning Data Readiness resolved historical neutral safety as ready:

```text
safety_status = PASS
safety_decision = NEUTRAL
safety_reason = historical_neutral_no_event_safety_ready
safety_policy_version = historical_replay_neutral_safety_v1
```

However, pending safety authority materialization only attaches historical `safety_context` when the safety decision is `ALLOW`.

Implementation evidence:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1056
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:787
```

Data Readiness then validates active historical pending against a contract that expects an ALLOW-shaped safety context:

```text
safety_context.safety_authority = historical_initial_no_external_effect
safety_context.safety_decision = ALLOW
safety_context.safety_policy_version = historical_replay_neutral_safety_v1
safety_context.safety_source = data_readiness_historical_temporal_authority
safety_context.safety_business_date = 2026-07-06
safety_context.runtime_test_run_id = runtime-test-historical-smoke-20260730T030213466506Z
safety_context.runtime_test_profile_id = historical-smoke
safety_context.runtime_test_evidence_root = reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T030213466506Z
```

Implementation evidence:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2099
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2138
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2178
```

Therefore the producer and consumer contracts disagree on historical neutral safety semantics for active pending:

```text
Producer observed decision: NEUTRAL
Producer attach condition: ALLOW only
Consumer expected safety_context.safety_decision: ALLOW
Observed pending safety_context: null
```

## Classification

```text
SCHEMA_MISMATCH
AUTHORITY_UNRESOLVED
MISSING_PRODUCER
EXPECTED_FAIL_CLOSED
```

This is not a Reference Price, Trading Unit, Position Sizing, Portfolio Policy, Portfolio Construction, or Runtime Planning root cause.

## Execution Trace

```text
Current Position
  position_count = 0
  current_state_confirmed_empty = true

Position Management
  producer_result_status = PASS
  position_count = 0

Runtime Planning
  plan_count = 50
  BUY_NEW = 9
  RESOLVED_EXECUTABLE quantity = 9

Morning Pending
  pending_item_count = 9
  side = BUY
  pending state = APPROVED
  safety_context = null

Sell Planning Data Readiness
  pending = REVIEW_REQUIRED
  safety = REVIEW_REQUIRED
  reason = historical_safety_temporal_authority_missing

Sell Planning
  NOT_EXECUTED
```

## Previous Blocker Recurrence

Not recurred:

```text
target_weight_authority_unresolved
invalid_quality_score
review_required_quantity_authority
REVIEW_REQUIRED_MISSING_PRICE
strategy_plan_quantity_unresolved
historical_trading_calendar_authority_missing
current_valuation_previous_trading_date_missing
```

Recurred / related:

```text
historical_safety_temporal_authority_missing
```

This recurrence is not the Phase23-AV calendar issue. Calendar and Current Valuation were READY.

## Production Contract Review

The resolver failed closed correctly. Active pending with missing Safety Authority must not proceed into sell planning or submit-adjacent flow.

The issue surfaces in historical mode because the historical neutral authority is represented as `NEUTRAL`, while the pending consumer expects an `ALLOW` safety context. The affected boundary is still Runtime-common Pending Safety Authority / Data Readiness gating, not a Strategy module.

Canonical owner:

```text
Runtime Pending Safety Authority / Data Readiness Historical Safety Temporal Authority
```

Producer / consumer boundary:

```text
Morning Strategy Planning Authority pending producer
↓
pending_order_plan current slot
↓
Sell Planning Data Readiness consumer
```

## Repair Direction

Repair is required before another 1BD rerun.

Recommended next task:

```text
Phase23-AX Historical Neutral Safety Authority Pending Binding Repair
```

Repair should unify historical neutral safety authority semantics for active pending. Either produce an ALLOW-compatible `safety_context` for `historical_initial_no_external_effect`, or update the common historical pending authority contract to accept the canonical `NEUTRAL` decision with explicit authority metadata.

Do not bypass Data Readiness, do not add latest/current fallback, and do not mutate existing run artifacts.

## Evidence

```text
reports/phase23_aw_1bd_sell_planning_halt_root_cause_audit/
```

## Machine Report

```text
reports/phase_reports/phase23_aw_1bd_sell_planning_halt_root_cause_audit.json
```

## 1BD Rerun Gate

```text
READY_FOR_1BD_RERUN = NO
```
