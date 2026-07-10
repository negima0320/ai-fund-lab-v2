# Phase15-AF Position Management AI Runtime Regular Path Connection

## Purpose

Phase15-AF connects the existing Position Management AI to the Runtime v2 regular SELL path.

The goal is to close this decision chain:

```text
Position Management AI
↓
Decision Artifact
↓
SELL Planning
↓
Runtime
```

This phase does not change AI model logic, model training, features, or HOLD/EXIT/ADD/REDUCE thresholds. The change is limited to Producer, Artifact, Consumer, Runtime regular path, Manifest, Report, Notification, and Regression coverage.

## Runtime Contract

Runtime must not replace AI judgment.

Before Phase15-AF, the Runtime SELL path could derive `SellExitDecision` directly from Runtime-owned Current positions. That made Runtime act as the decision maker. Phase15-AF changes the regular CLI path so SELL intent is produced by Position Management AI evidence, while Current remains the asset state and quantity source.

Current is still required, but only for:

- Runtime-owned position scope
- Runtime-owned quantity
- SELL quantity boundary
- cleanup / emergency / operational liquidation boundary

Profit taking, stop loss, HOLD, EXIT, REDUCE, and ADD judgment belong to Position Management AI.

## Implementation Summary

### Producer

Added Runtime adapter:

```text
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
```

The adapter:

- reads Runtime-owned Current positions from `persistent_ledger/state.json`
- writes a Runtime holdings snapshot for the existing Position Management AI
- calls the existing Position Management inference entrypoint
- normalizes the AI output into an authoritative Runtime decision artifact
- converts only `EXIT` decisions into SELL Planning `SellExitDecision`

No Position Management AI scoring logic or threshold was changed.

### Authoritative Artifact

The Runtime artifact is written under:

```text
.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json
```

It includes:

```text
business_date
runtime_id
environment
model_version
inference_version
feature_date
generated_at
symbol
decision
reason
confidence
runtime_position_quantity
runtime_sell_quantity
runtime_action
```

`ADD` is recorded but not converted into SELL Planning because ADD is outside SELL Planning scope. `REDUCE` is recorded but not automatically converted into a SELL order until an explicit REDUCE quantity contract is defined.

### Runtime Consumer

Updated Runtime CLI:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

For `--job sell_planning`, Runtime now runs:

```text
Position Management AI producer
↓
SELL Planning pending pipeline
```

If Position Management evidence is required but missing, Runtime returns `REVIEW_REQUIRED` and does not run SELL Planning from Current alone.

### Manifest

The Runtime manifest now emits:

```text
pm_status
pm_reason
pm_model_version
pm_inference_version
pm_feature_date
pm_artifact_path
pm_decision_count
pm_exit_count
pm_hold_count
pm_reduce_count
pm_add_count
pm_generated_at
```

### Report / Notification

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py
src/ai_fund_lab_v2/runtime_v2/notification/models.py
src/ai_fund_lab_v2/runtime_v2/notification/payload.py
```

Runtime report now includes:

- Position Management Decision
- Why HOLD
- Why EXIT

Notification payload includes a compact `position_management_summary`, for example:

```text
EXIT 1, HOLD 0, REDUCE 0, ADD 0
```

Notification remains payload-only in this phase.

## Boundary Clarification

| Boundary | Owner | Phase15-AF Result |
|---|---|---|
| HOLD / EXIT / REDUCE / ADD judgment | Position Management AI | Connected to Runtime regular path |
| Runtime-owned quantity | Current SoT | Preserved as quantity boundary |
| Broker-only position | Broker evidence | Not treated as Runtime-owned SELL source |
| Current cleanup | Runtime | Kept separate from PM AI decision |
| Emergency liquidation | Safety / Operation Guard / Runtime | Kept separate from PM AI decision |
| SELL Planning intent | PM artifact | Current-only SELL decision removed from CLI regular path |

## Regression

| Test | Coverage | Result |
|---|---|---|
| `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py` | PM artifact generation, PM artifact consumption, Current-only block, EXIT to Pending, HOLD no SELL, Report/Notification summary | PASS |
| `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py` | SELL Planning CLI writes SELL pending from PM AI artifact, broker-only position excluded | PASS |
| Phase15 retention suite | Policy, Submit Guard, Morning Policy, Policy Hash, SELL Broker Quantity, Safety, Runtime Safety Producer/Evaluator, Report/Notification, Submit/Execution/Current | PASS |

Commands run:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15af_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/position_management/producer.py src/ai_fund_lab_v2/runtime_v2/position_management/__init__.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py src/ai_fund_lab_v2/runtime_v2/notification/models.py src/ai_fund_lab_v2/runtime_v2/notification/payload.py
```

Result: PASS

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15af_pycache python3 -m pytest -q tests/runtime_v2/test_phase15af_position_management_runtime_connection.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py
```

Result: `21 passed`

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15af_pycache python3 -m pytest -q tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15ac_runtime_safety_decision_producer.py tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py
```

Result: `58 passed`

## Static Check

Search confirmed that the legacy Current-only SELL reason is not present in Runtime implementation. It remains only in regression assertions that verify it does not reappear:

```text
runtime_v2_sell_planning_current_position_exit
```

## Prohibited Actions Confirmation

Not performed:

- AI model improvement
- AI retraining
- AI logic change
- HOLD / EXIT threshold change
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd change

## Acceptance Judgment

The Phase15-AF target chain is closed:

```text
Position Management AI
↓
Producer
↓
Artifact
↓
SELL Planning
↓
Runtime
```

Final judgment:

```text
PHASE15AF_POSITION_MANAGEMENT_AI_RUNTIME_REGULAR_PATH_CONNECTION_COMPLETE
```
