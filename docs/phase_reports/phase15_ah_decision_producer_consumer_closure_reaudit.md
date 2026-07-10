# Phase15-AH Decision Producer / Consumer Closure Re-Audit

## Purpose

Phase15-AH re-audits the Decision Producer / Consumer closure originally reviewed in Phase15-AE.

This re-audit uses the current implementation after:

- Phase15-AC: Runtime Safety Decision Producer
- Phase15-AD: Runtime Safety Evaluation Regular Path
- Phase15-AF: Position Management AI -> Runtime SELL
- Phase15-AG: Candidate AI -> Opportunity AI -> Morning Planning

This phase is static review only. It does not modify implementation and does not execute Morning, Submit, Execution, Broker Write, orders, notification real send, launchd, or Current edits.

## Evidence Checked

- `docs/phase_reports/phase15_ae_decision_producer_consumer_closure_audit.md`
- `docs/phase_reports/phase15_ac_runtime_safety_decision_producer_connection.md`
- `docs/phase_reports/phase15_ad_runtime_safety_evaluation_regular_path_connection.md`
- `docs/phase_reports/phase15_af_position_management_ai_runtime_regular_path_connection.md`
- `docs/phase_reports/phase15_ag_candidate_opportunity_ai_runtime_regular_path_connection.md`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/safety_decision.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/reconcile/`
- `src/ai_fund_lab_v2/runtime_v2/audit/`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/`
- Phase15-AC/AD/AF/AG regression reports and tests referenced in those reports

## Executive Summary

The Phase15-AE `DECISION_CHAIN_GAPS_FOUND` result is no longer accurate for the core AI / Safety decision chains.

Closed since AE:

- Candidate AI -> Opportunity AI -> Morning Planning
- Position Management AI -> SELL Planning
- Runtime Safety Evaluation -> Phase11 Safety Report -> Runtime Safety Decision
- Capital Deployment Policy -> Morning / Pending / Approval / Submit
- Execution ReadOnly -> Ledger -> Runtime-owned Current Projection
- Report / Notification payload reason propagation

Still not fully closed:

- Audit aggregator as a Runtime control decision
- Operator Review apply path
- Recovery apply path
- Real notification delivery
- Production readiness

These remaining items are important, but they are not Step0 Preflight blockers if explicitly scoped as deferred or evidence-needed-later.

Runtime Acceptance impact:

```text
READY_FOR_STEP0_RETRY
```

## Decision Closure Matrix

| Component | Closure Status | Previous Status | Changed? | Remaining Gap | Severity |
|---|---|---|---|---|---|
| Candidate AI | CLOSED | PARTIAL | Yes | Requires Acceptance evidence with real model/artifact paths before Morning PASS, but Producer -> Artifact -> Consumer is implemented. | LOW |
| Opportunity AI | CLOSED | CONSUMER_MISSING | Yes | Requires Acceptance evidence that the intended Opportunity model/artifact is active. Runtime no longer ranks from feature rows. | LOW |
| Position Management AI | CLOSED | RUNTIME_SUBSTITUTES_DECISION | Yes | REDUCE remains recorded but not converted to SELL until explicit quantity contract exists; EXIT/HOLD chain is closed. | MEDIUM |
| Capital Deployment Policy | CLOSED | PARTIAL | Yes | Capital Allocation AI engine remains deferred; Phase15 uses explicit Capital Deployment Policy contract. | LOW |
| Safety | CLOSED | CLOSED | No, strengthened | Requires fresh Step0 Safety evidence. Missing/stale evidence fails closed. | LOW |
| Broker ReadOnly | PARTIAL | PARTIAL | Partial | Execution ReadOnly producer exists; Submit SELL available quantity consumption exists. Stepwise Acceptance still must prove fresh broker snapshot before Submit. | MEDIUM |
| Execution | CLOSED | CLOSED | No | Demo evidence still required in Acceptance; static chain is closed. | LOW |
| Reconcile | PARTIAL | PARTIAL | No | Reconcile runs inside Execution and produces findings, but no independent apply/control consumer is closed. | MEDIUM |
| Audit | PARTIAL | CLI_NOT_CONNECTED | Partial | Report path emits audit artifact/stage, but `run_audit` is not a first-class Runtime control gate. | MEDIUM |
| Operator Review | DEFERRED | PRODUCER_MISSING | Scoped | REVIEW_REQUIRED is visible in Manifest/Report/Notification; Operator decision apply path remains future work. | MEDIUM |
| Recovery | DEFERRED | LEGACY_ONLY | Scoped | Runtime v2 recovery apply path is not closed; controlled rerun remains manual procedure. | MEDIUM |
| Notification Delivery | DEFERRED | PARTIAL | Scoped | Payload is closed; real send/queue/delivery acceptance is deferred. | LOW |
| Production Readiness | DEFERRED | PARTIAL | Scoped | Production broker write, production notification send, account mapping, fees/taxes, launchd automation remain outside Phase15 Acceptance. | INFO |

## Phase15 Remaining Runtime Gaps

The following are the only Runtime connection gaps that still matter for Phase15 stepwise Acceptance.

| Gap | Why It Matters | Phase15 Action |
|---|---|---|
| Broker ReadOnly freshness before Submit | SELL Submit acceptance depends on broker available quantity evidence. | Verify during Step0/Submit Guard Review; do not claim Submit PASS without fresh snapshot evidence. |
| Audit as control gate | Audit artifact exists, but Audit is not yet a blocking Runtime decision producer/consumer. | Do not treat Audit as Acceptance gate unless explicitly invoked later. |
| Operator Review apply | REVIEW_REQUIRED can be explained, but no automatic apply path exists. | Use manual operator procedure; no Current/Pending direct edits. |
| Recovery apply | Retry/rerun semantics are not fully automated. | Controlled step rerun only; defer full recovery implementation. |

No additional AI connection fix is required before returning to Step0.

## Deferred Scope

| Deferred Item | Reason | Required Later |
|---|---|---|
| Capital Allocation AI engine integration | Phase15 established explicit Capital Deployment Policy; connecting the AI engine would be a separate decision-owner change. | Define Producer -> Artifact -> Runtime consumer contract for Capital Allocation AI. |
| REDUCE quantity execution | Phase15-AF records REDUCE but avoids inventing a quantity contract. | Define explicit REDUCE sizing/liquidation policy. |
| Audit apply/control gate | Current audit output is evidence-oriented. | Add regular CLI audit job or gate consumer if Audit should block Runtime. |
| Operator Review apply | Manual review evidence exists; apply path is not implemented. | Define operator decision artifact and consumer. |
| Recovery apply | Safe rerun/retry remains procedural. | Define recovery decision artifact, idempotency, and state transition consumer. |
| Notification delivery | Phase15 remains payload-only. | Queue/sender/delivery ledger acceptance and real-send policy. |
| Production readiness | Demo Acceptance is not Production launch. | Production endpoint gates, account mapping, fees/taxes, production unlock, launchd readiness. |

## Runtime Decision Coverage

| Runtime Decision | Producer | Artifact | Consumer | Closure |
|---|---|---|---|---|
| BUY Decision | `produce_buy_ai_decisions()` using Candidate AI + Opportunity AI | `.runtime/runtime_state/buy_ai/<business_date>/candidate_decisions.json`; `opportunity_rankings.json` | Morning Planning via `ai_signals` | CLOSED |
| SELL Decision | `produce_position_management_decisions()` using Position Management AI | `.runtime/runtime_state/position_management/<business_date>/position_management_decisions.json` | SELL Planning via `SellExitDecision` | CLOSED |
| Safety Decision | `run_runtime_safety_evaluation()` then `produce_runtime_safety_decision()` | `reports/safety/phase11/<business_date>_safety_report.json`; `.runtime/runtime_state/safety/latest_safety_decision.json` | Morning / SELL / Submit / Report | CLOSED |
| Capital Deployment | `load_capital_deployment_policy()` | `configs/runtime_v2/capital_deployment.json` and manifest policy/hash fields | Morning / Pending / Approval / Submit Guard | CLOSED |
| Broker Decision | Broker ReadOnly snapshot producer/normalizer | `.runtime/runtime_state/broker_readonly/<business_date>/*.json` | Execution; Submit SELL quantity evidence | PARTIAL |
| Execution Decision | `run_execution_readonly_pipeline()` | ledger records, execution stage details, runtime-owned projection evidence | Ledger / Current Projection / Report | CLOSED |
| Current Projection | Runtime-owned fill projection | `persistent_ledger/state.json` | Report / next Planning / Acceptance review | CLOSED |
| Reconcile Decision | `run_reconciliation()` inside Execution | Reconciliation result/stage details | Execution status / Report evidence | PARTIAL |
| Report Decision | `generate_public_report_from_current()` | runtime report, public report, reason evidence | Operator / Notification payload | CLOSED |
| Notification Decision | `build_notification_payload_from_summary()` / report writer payload | `notification_payload.json` with `PAYLOAD_ONLY`, `notification_sent=false` | Operator; future delivery path | CLOSED for payload, DEFERRED for real delivery |
| Audit Decision | report-side audit artifact and `run_audit` component | `audit_result.json` / `AuditResult` component | Operator evidence only | PARTIAL |
| Operator Review | Human review procedure | Manifest / Report / Notification evidence | Manual next step; no apply consumer | DEFERRED |
| Recovery | Manual controlled rerun discipline | no closed Runtime v2 recovery decision artifact | no closed apply consumer | DEFERRED |

## Re-Audit Notes By Component

### Candidate AI / Opportunity AI

Phase15-AG closes the previous BUY gap.

Current chain:

```text
Candidate AI
↓
candidate_decisions.json
↓
Opportunity AI
↓
opportunity_rankings.json
↓
Morning Planning
```

Runtime no longer generates BUY `AIPlanningSignal` from feature rows in the regular Morning path. Missing BUY AI evidence stops as `REVIEW_REQUIRED`.

### Position Management AI

Phase15-AF closes the previous SELL gap.

Current chain:

```text
Position Management AI
↓
position_management_decisions.json
↓
SELL Planning
```

Current remains a quantity / Runtime-owned position boundary, not the SELL intent producer.

### Safety

Phase15-AC and Phase15-AD close the Safety chain:

```text
Runtime Evidence
↓
Safety Evaluation
↓
Phase11 Safety Report
↓
Runtime Safety Decision
↓
Morning / SELL / Submit
```

Missing or stale Safety evidence is not converted to implicit `ALLOW`.

### Capital Deployment

Capital Deployment Policy is closed for Phase15 scope.

This is not a claim that Capital Allocation AI engine is connected. It is a scoped Phase15 contract:

```text
Capital Deployment Policy
↓
Policy source / version / hash
↓
Morning / Pending / Approval / Submit Guard
```

### Broker ReadOnly / Execution / Current

Execution and Current Projection are closed statically. Broker ReadOnly remains `PARTIAL` because Acceptance still must prove fresh broker evidence at the broker boundary, especially for SELL Submit available quantity.

### Reconcile / Audit / Operator / Recovery

These remain scoped, not blocking Step0 retry:

- Reconcile is evidence-connected inside Execution, but not an independent apply controller.
- Audit exists, but should not be treated as a Runtime control gate yet.
- Operator Review explains next action but has no apply path.
- Recovery remains manual controlled procedure.

## Runtime Acceptance Impact

Step0 is a preflight evidence review. The core Decision Producer / Consumer blockers from AE are now sufficiently closed to retry Step0.

Important limitation:

`READY_FOR_STEP0_RETRY` does not mean Phase15 Complete, Full Runtime PASS, Demo order approval, Submit approval, Broker Write approval, notification send approval, or launchd approval.

Final Acceptance impact:

```text
READY_FOR_STEP0_RETRY
```

## Prohibited Actions Confirmation

This phase did not perform:

- Runtime implementation change
- Morning execution
- Submit execution
- Execution run
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd change
- Current edit

## Final Judgment

```text
PHASE15AH_DECISION_PRODUCER_CONSUMER_CLOSURE_REAUDIT_COMPLETE
```
