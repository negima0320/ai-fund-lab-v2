# Phase15-AS Data Readiness Semantic Consistency Audit / Fix

## Purpose

Phase15-AS fixed semantic inconsistencies in the Runtime v2 Data Readiness Gate before resuming Acceptance.

The target issue was not whether artifacts exist, but whether Data Readiness status, Safety reasons, model readiness, pending lifecycle, and Demo / Production evidence describe the same Runtime reality.

Final judgment:

```text
PHASE15AS_DATA_READINESS_SEMANTIC_CONSISTENCY_FIX_COMPLETE
```

## Semantic Consistency Matrix

| Area | Before Risk | Fix | Acceptance Semantics |
|---|---|---|---|
| Market / Quote | `market_status=READY` could coexist with Safety reasons such as `QUOTE_MISSING_FOR_MONITOR` or `BROKER_SNAPSHOT_MISSING`. | Split market readiness into calendar, market data, quote, market summary, and safety market input statuses. Effective market status now includes Safety quote dependencies. | Market cannot be READY when Safety evidence says required quote/market inputs are missing. |
| Broker dependency | Broker direct scope and Safety-required broker evidence were mixed. | Added direct broker status and Safety dependency broker status, then derive `broker_effective_status`. | Submit/Sell evidence can distinguish scope-not-required from Safety-required missing broker evidence. |
| BUY AI model paths | Data Readiness could emit empty Candidate / Opportunity model paths while Runtime BUY AI used formal defaults. | Added shared BUY AI model resolver and used it in both BUY AI producer and Data Readiness. | Data Readiness reports the same canonical model paths used by Runtime BUY AI. |
| Model readiness | Model path existence could be treated too weakly. | Added pickle payload validation for readable payload, dict shape, `model`, `feature_columns`, and `model_version` or explicit unknown. Corrupt artifact HALTs. | Broken model artifact is not hidden by path existence. |
| EMPTY Pending | Explicit `EMPTY` slot could be warned as `pending_order_plan MISSING`. | Data Readiness now distinguishes slot missing from explicit EMPTY. Orchestrator warning suppression treats EMPTY as normal. | No old Pending is required before Morning; missing slot remains REVIEW_REQUIRED. |
| Runtime state warning | Optional legacy `runtime_state` warning could confuse Preflight. | Suppressed non-blocking `runtime_state MISSING` warning in preflight warnings. | Optional/legacy runtime_state is not escalated as readiness blocker. |
| Demo production equivalence | Demo evidence could look production-equivalent. | Split `runtime_core_production_baseline`, `broker_environment`, `broker_environment_production`, `evidence_production_equivalent`, `acceptance_production_equivalent`, `runtime_execution_path`, and `acceptance_scope`. | Demo keeps Production Reality design, but evidence/acceptance are not production equivalent. |
| Component reasons | Reasons were flat and could not explain component-specific status. | Added `component_reasons` and `effective_component_statuses` with precedence `HALT > REVIEW_REQUIRED > READY > NOT_REQUIRED`. | Operator can see why each component is READY / REVIEW_REQUIRED / HALT. |

## Files Updated

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/orchestrator/orchestrator.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py`
- Existing nearby regression fixtures were updated to include explicit Market Evidence where they expect regular Runtime progression.

## Runtime Contract Updates

### Market / Quote

Data Readiness now emits:

```text
market_calendar_status
market_data_status
quote_status
market_summary_status
safety_market_input_status
market_status
```

`market_status` is an effective status. It is not allowed to stay READY when Safety indicates missing quote or market evidence.

### Broker

Data Readiness now emits:

```text
broker_direct_scope_status
broker_safety_dependency_status
broker_effective_status
broker_status
```

This separates direct job requirements from Safety-driven broker snapshot requirements.

### BUY AI Model Readiness

Data Readiness uses the same resolver as BUY AI producer:

```text
resolve_buy_ai_model_paths
```

Readiness validates model artifacts beyond path presence:

- readable pickle payload
- dictionary payload
- model object exists
- feature columns exist
- model version exists or is explicitly `unknown`

### Pending Lifecycle

Pending states are now differentiated:

```text
pending_slot_status=MISSING
pending_slot_status=EMPTY
pending_active=false
```

Explicit EMPTY is normal. Missing slot remains REVIEW_REQUIRED.

### Production Equivalence Split

Demo acceptance now reports:

```text
runtime_core_production_baseline=true
broker_environment=demo
broker_environment_production=false
evidence_production_equivalent=false
acceptance_production_equivalent=false
runtime_execution_path=regular_runtime
acceptance_scope=demo_acceptance_only
```

This preserves Phase15-X Runtime Reality Rule without pretending Demo evidence is Production equivalent.

## Regression Added

Added `tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py` covering:

- market open but market evidence missing
- Safety quote/broker missing reason drives effective market/broker REVIEW_REQUIRED
- market evidence READY plus Safety ALLOW can pass
- canonical BUY AI model paths when CLI paths are omitted
- corrupt model artifact HALT
- explicit EMPTY pending slot is READY and warning-free
- missing pending slot is not EMPTY
- Demo / Production equivalence split
- structured component reasons

## Verification

Passed:

```text
python3 -m pytest tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py
python3 -m pytest tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py
python3 -m pytest tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py
env PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15as python3 -m compileall src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py src/ai_fund_lab_v2/runtime_v2/orchestrator/orchestrator.py src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py
```

## Prohibited Actions Confirmation

Not executed:

- Market Refresh
- Feature Refresh
- Broker Refresh
- Safety Evaluation
- Morning
- SELL Planning
- Submit
- Execution
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd / plist change
- Current direct edit
- Pending direct edit against real runtime

