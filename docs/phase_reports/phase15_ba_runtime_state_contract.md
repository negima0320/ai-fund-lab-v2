# Phase15-BA Runtime State Contract

## Purpose

Phase15-BA closes the Runtime State ambiguity identified by the Runtime Temporal / Freshness Contract.

The formal decision is:

```text
.runtime/runtime_state/current_state.json
= authoritative Runtime Operation State
```

It is not an Asset Current artifact.

## Decision

Runtime State is Option A from the Temporal Contract:

```text
AUTHORITATIVE_RUNTIME_OPERATION_STATE
```

Authoritative scope:

- Runtime state machine state
- Safety state
- business date
- generated timestamp
- runtime mode / environment
- producer identity

Explicitly not authoritative:

- positions
- cash
- buying power
- total equity
- active pending submit target
- approval source

Those remain owned by:

```text
persistent_ledger/state.json
pending_order_plan/pending_order_plan.json
runtime_state/safety/latest_safety_decision.json
```

## Implemented Files

Created:

- `src/ai_fund_lab_v2/runtime_v2/runtime_state/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/runtime_state/contract.py`
- `tests/runtime_v2/test_phase15ba_runtime_state_contract.py`

Updated:

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`

## CLI

Added:

```text
--job runtime_state_refresh
```

This job writes:

```text
.runtime/runtime_state/current_state.json
```

with:

```text
schema_version=runtime_v2_operation_state_v1
role=authoritative_runtime_operation_state
```

It performs no broker write, no notification send, no AI decision generation, and no asset mutation.

## Safety / Data Readiness Impact

Safety Evaluation now validates Runtime State through the same contract validator used by Data Readiness.

Data Readiness now emits:

```text
runtime_state_status
runtime_state_reason
runtime_state_artifact_path
components.runtime_state
effective_component_statuses.runtime_state
```

Missing or stale Runtime State is no longer an ambiguous warning. It is formal `REVIEW_REQUIRED`. Invalid JSON is `HALT`.

## Verification

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15ba_runtime_state_contract.py tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py tests/runtime_v2/test_phase15y_non_trading_day_demo_acceptance_override.py -q
```

Result:

```text
44 passed
```

Additional observation:

```text
python3 -m pytest tests/runtime_v2/test_phase15*.py -q
```

This broader suite still has pre-existing / adjacent fixture gaps where older Morning / SELL Planning tests lack Market Evidence or Broker ReadOnly evidence required by the Phase15 Data Readiness Gate. These are not Runtime State Contract failures; BA-specific and adjacent Safety/Data Readiness tests pass.

## Final Judgment

```text
PHASE15BA_RUNTIME_STATE_CONTRACT_COMPLETE
READY_FOR_ACCEPTANCE_STEP0_EVIDENCE_RETRY
```
