# Phase15-AG Candidate AI / Opportunity AI Runtime Regular Path Connection

## Purpose

Phase15-AG connects the existing Candidate AI and Opportunity AI to the Runtime v2 regular BUY path.

The target decision chain is:

```text
Candidate AI
↓
Candidate Decision Artifact
↓
Opportunity AI
↓
Opportunity Ranking Artifact
↓
Morning Planning
↓
Runtime
```

This phase does not change AI models, training, features, scoring, or ranking logic. The change is limited to Producer, Artifact, Consumer, Runtime regular path, Manifest, Report, Notification, and Regression coverage.

## Runtime Contract

Runtime must not replace AI judgment.

Before Phase15-AG, Morning Planning read feature artifacts and generated `AIPlanningSignal` inside Runtime. That made Runtime act as a substitute AI decision maker.

Phase15-AG removes that regular BUY path. Morning now requires Opportunity AI ranking signals produced from Candidate AI and Opportunity AI artifacts. Runtime keeps only its control responsibilities:

- Policy
- Safety
- Capital Deployment
- price / lot / buying power constraints
- Pending
- Approval

Runtime may filter or stop by control contract, but it must not create Candidate rank, Opportunity rank, or Feature-derived AI judgment.

## Implementation Summary

### Producer

Added Runtime adapter:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

The adapter:

- reads Candidate feature input for the resolved feature date
- calls the existing Candidate AI inference helper from Phase4-BG
- writes a Runtime Candidate Decision Artifact
- calls the existing Opportunity AI inference entrypoint
- writes a Runtime Opportunity Ranking Artifact
- converts Opportunity rankings into Morning Planning `AIPlanningSignal`

### Candidate Artifact

Path:

```text
.runtime/runtime_state/buy_ai/<business_date>/candidate_decisions.json
```

Minimum fields:

```text
business_date
target_date
feature_date
runtime_id
model_version
generated_at
code
symbol
candidate_score
candidate_rank
candidate_reason
reason
confidence
```

### Opportunity Artifact

Path:

```text
.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json
```

Minimum fields:

```text
business_date
runtime_id
model_version
feature_date
symbol
opportunity_score
rank
expected_return
confidence
generated_at
```

## Runtime Consumer

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

For `--job morning`, Runtime now runs:

```text
Candidate / Opportunity AI producer
↓
Morning Planning
```

If BUY AI evidence is missing, Runtime returns `REVIEW_REQUIRED` and does not run Morning Planning from feature rows alone.

The old feature-derived BUY source:

```text
runtime_v2_morning_feature_inference
```

is removed from the implementation and remains only as a negative regression assertion.

## Manifest

Runtime manifest now emits:

```text
buy_ai_status
buy_ai_reason
candidate_model_version
candidate_artifact_path
candidate_count
opportunity_model_version
opportunity_artifact_path
opportunity_count
selected_rank_count
buy_ai_generated_at
```

## Report / Notification

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py
src/ai_fund_lab_v2/runtime_v2/notification/models.py
src/ai_fund_lab_v2/runtime_v2/notification/payload.py
```

Runtime report now includes:

- Candidate AI Summary
- Opportunity AI Summary
- Why Selected

Notification payload now includes:

```text
buy_ai_summary
selected_candidates
selected_top_rank
```

Notification remains payload-only in this phase.

## Boundary Clarification

| Boundary | Owner | Phase15-AG Result |
|---|---|---|
| Candidate score / rank | Candidate AI | Produced by Candidate AI artifact |
| Opportunity score / rank | Opportunity AI | Produced by Opportunity AI artifact |
| BUY intent | Opportunity artifact | Consumed by Morning Planning |
| Price / lot / buying power | Runtime | Preserved as control boundary |
| Capital Deployment | Runtime | Applies amount/position policy without changing AI rank |
| Safety | Runtime | May stop or review without changing AI judgment |
| Pending / Approval | Runtime | Generated after AI artifact and control checks |

## Regression

| Test | Coverage | Result |
|---|---|---|
| `tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py` | Candidate artifact generation, Opportunity artifact generation, Morning consumes AI artifact, feature-only substitution blocked, Report/Notification summary | PASS |
| `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py` | Existing Morning pending behavior retained with BUY AI artifacts | PASS |
| `tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py` | Policy max positions / no 100k cap retained with BUY AI artifacts | PASS |
| `tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py` | Feature date carryover retained with BUY AI artifact date resolution | PASS |
| Retention suite | Policy, Submit, SELL, Safety, Report, Notification, Execution, Current | PASS |

Commands run:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15ag_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py src/ai_fund_lab_v2/runtime_v2/buy_ai/__init__.py src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py src/ai_fund_lab_v2/runtime_v2/notification/models.py src/ai_fund_lab_v2/runtime_v2/notification/payload.py
```

Result: PASS

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15ag_pycache python3 -m pytest -q tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py
```

Result: `16 passed`

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15ag_pycache python3 -m pytest -q tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py tests/runtime_v2/test_phase15af_position_management_runtime_connection.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py
```

Result: `44 passed`

## Static Check

Search result:

```text
runtime_v2_morning_feature_inference
```

is present only in a negative regression assertion.

`SELL` Planning still has its own `_ai_signal` helper for Position Management SELL decisions. That is outside this BUY-side AG scope.

## Prohibited Actions Confirmation

Not performed:

- AI model improvement
- AI retraining
- AI ranking change
- AI feature change
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd change

## Acceptance Judgment

The Phase15-AG target chain is closed:

```text
Candidate AI
↓
Producer
↓
Artifact
↓
Opportunity AI
↓
Artifact
↓
Morning
↓
Runtime
```

Final judgment:

```text
PHASE15AG_CANDIDATE_OPPORTUNITY_AI_RUNTIME_REGULAR_PATH_CONNECTION_COMPLETE
```
