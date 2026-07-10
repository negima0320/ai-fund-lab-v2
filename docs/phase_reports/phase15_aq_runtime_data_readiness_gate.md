# Phase15-AQ Runtime Data Readiness Gate

Date: 2026-07-10

## Final Judgment

```text
PHASE15AQ_RUNTIME_DATA_READINESS_GATE_COMPLETE
```

Phase15-AQ implemented a read-only Runtime Data Readiness Gate before Morning and SELL Planning.  The gate aggregates Runtime input evidence and stops the regular path before AI Producer / Planning when the evidence is not executable.

This phase did not change AI models, AI scoring, PM decision logic, Pending state, Current state, Submit, Broker Write, orders, launchd, or notification real send.

## Objective

Phase15-AN through AP strengthened individual consumer contracts.  Phase15-AQ adds the first-layer gate:

```text
Data Readiness Gate
↓
READY
↓
Morning / SELL Planning
```

or:

```text
Data Readiness Gate
↓
REVIEW_REQUIRED / HALT
↓
do not run AI Producer / Planning
```

Component-local validation remains in place.  The gate is not the only validation layer.

## Implementation Summary

### New Runtime Data Readiness Module

Added:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py
```

Main API:

```text
evaluate_runtime_data_readiness(...)
```

The module writes the authoritative fixed artifact:

```text
.runtime/runtime_state/data_readiness/<business_date>/data_readiness.json
```

Allowed statuses:

```text
READY
REVIEW_REQUIRED
HALT
```

### CLI Job

Added Runtime v2 regular CLI job:

```text
--job data_readiness
```

Added scope argument:

```text
--readiness-scope morning|sell_planning|submit|execution
```

Example:

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job data_readiness \
  --readiness-scope morning \
  --business-date <date> \
  --runtime-root .runtime \
  --capital-deployment-policy configs/runtime_v2/capital_deployment.json
```

### Morning / SELL Planning Integration

The regular CLI now runs the Data Readiness Gate before:

```text
morning
sell_planning
```

If the gate returns `REVIEW_REQUIRED` or `HALT`, the CLI does not run:

```text
Candidate / Opportunity AI Producer
Position Management AI Producer
Morning Planning
SELL Planning
```

Submit / Execution are modeled as scopes in the gate, but mandatory CLI blocking for those jobs remains staged to avoid changing their existing runtime contract in this phase.

## Scope-Based Evidence Contract

The gate avoids one-size-fits-all evidence requirements.

| Evidence | Morning | SELL Planning | Submit | Execution |
|---|---:|---:|---:|---:|
| Current | Required | Required | Required | Required |
| Safety | Required | Required | Required | Required |
| Feature Consumer Readiness | Required | Not globally required | Not globally required | Not globally required |
| Candidate model/schema | Pre-inference required | Not required | Not required | Not required |
| Opportunity model/schema | Pre-inference required | PM dependency only | Not required | Not required |
| PM input contract | Not required | Required | SELL evidence only | Not required |
| Broker ReadOnly snapshot | Not required by gate | Required | Required | Required |
| Pending lifecycle | Checked | Checked | Checked | Checked |
| Runtime environment | Checked | Checked | Checked | Checked |

## Artifact Fields

The fixed readiness artifact includes:

```text
schema_version
business_date
generated_at
runtime_mode
readiness_scope
overall_status
review_required
halt_required
market_status
feature_status
candidate_status
opportunity_status
pm_status
current_status
broker_status
safety_status
pending_status
runtime_environment_status
missing_columns
missing_evidence
stale_artifacts
mismatched_dates
source_paths
review_reasons
halt_reasons
next_operator_action
current_expected_as_of
current_actual_as_of
current_freshness_policy
non_trading_day_demo_override
production_equivalent
acceptance_scope
```

## Non-Trading-Day Demo Override

Phase15-Y behavior is incorporated.

Allowed only when:

```text
runtime_mode=demo
non_trading_day_demo_override=true
current.as_of=latest_expected_trading_date
production_equivalent=false
acceptance_scope=demo_acceptance_only
```

Production override returns `HALT`.

Older-than-expected Current returns `REVIEW_REQUIRED`.

## Feature / BUY AI Readiness

Morning scope verifies:

```text
Feature Consumer Readiness
Candidate model path
Candidate schema status
Opportunity model path
Opportunity schema status
Feature date
```

The gate does not generate Candidate decisions, Opportunity rankings, AIPlanningSignal, or BUY rank.

## PM / SELL Readiness

SELL Planning scope reuses the Phase15-AP PM input contract through a read-only public API:

```text
validate_position_management_input_contract(...)
```

It checks:

```text
Current freshness
Current required fields
PM feature row coverage
Opportunity dependency readiness
derived/defaulted field evidence
```

The gate does not run PM inference or generate SELL decisions.

## Manifest / Report / Notification

Runtime manifest now includes:

```text
data_readiness_status
data_readiness_scope
data_readiness_artifact_path
data_readiness_review_reasons
data_readiness_halt_reasons
data_readiness_next_operator_action
```

Report summary includes:

```text
data_readiness
```

Notification payload includes:

```text
data_readiness_status
data_readiness_reason
```

Notification remains payload-only.

## Regression Coverage

Added:

```text
tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py
```

Coverage:

- `data_readiness` CLI writes fixed READY artifact.
- Schema mismatch returns `REVIEW_REQUIRED`.
- Stale Current returns `REVIEW_REQUIRED`.
- Non-trading-day Demo override accepts the expected latest trading date Current.
- Non-trading-day Demo override rejects older Current.
- Production override returns `HALT`.
- SELL Planning scope does not require Candidate evidence.
- Stale approved Pending returns `REVIEW_REQUIRED`.
- Gate stops Morning before AI Producer / Planning.
- Gate does not generate AI decisions.
- Consumer validations remain in AN/AO/AP tests.

Updated existing tests to reflect the new first-layer gate behavior:

- BUY schema failure now stops at `runtime_data_readiness_gate` before Candidate / Opportunity Producer.
- PM input mismatch now stops at `runtime_data_readiness_gate` before PM Producer / SELL Planning.
- Safety missing now stops at `runtime_data_readiness_gate` before Morning Planning.
- SELL success fixtures now include Broker ReadOnly evidence required by the SELL readiness scope.

## Verification

```text
python3 -m pytest \
  tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py \
  tests/runtime_v2/test_phase15an_feature_consumer_readiness.py \
  tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py \
  tests/runtime_v2/test_phase15ap_position_management_input_contract.py \
  tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py \
  tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py \
  tests/runtime_v2/test_phase15h_capital_deployment_policy.py
```

Result:

```text
40 passed
```

```text
python3 -m pytest \
  tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py \
  tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py \
  tests/runtime_v2/test_phase15y_non_trading_day_demo_acceptance_override.py
```

Result:

```text
25 passed
```

## Prohibited Actions Confirmation

Not performed:

- AI model change
- AI retraining
- missing data default supplementation
- Pending mutation / deletion / expiration
- Morning real operation
- SELL real operation
- Submit
- Execution
- Broker Write
- Order placement
- Notification real send
- launchd change
- Current direct edit

## Completion

```text
PHASE15AQ_RUNTIME_DATA_READINESS_GATE_COMPLETE
```
