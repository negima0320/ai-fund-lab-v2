# Phase15-AE Decision Producer / Consumer Closure Audit

## Purpose

Phase15-AE audits whether major AI Fund Lab v2 decision components close the chain:

```text
Decision
↓
Authoritative Artifact
↓
Runtime Regular Consumer
↓
Runtime Control
↓
Evidence / Regression
```

This phase is audit-only. It does not implement fixes and does not execute Runtime jobs.

## Evidence Checked

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase15_f_ai_component_interface_blind_spot_audit.md`
- `docs/phase_reports/phase15_q_runtime_component_usage_audit.md`
- `docs/phase_reports/phase15_ac_runtime_safety_decision_producer_connection.md`
- `docs/phase_reports/phase15_ad_runtime_safety_evaluation_regular_path_connection.md`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/safety_decision.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/reconcile/reconciler.py`
- `src/ai_fund_lab_v2/runtime_v2/audit/auditor.py`
- `src/ai_fund_lab_v2/runtime_v2/report/`
- `src/ai_fund_lab_v2/runtime_v2/notification/`
- `src/ai_fund_lab_v2/candidate_ai/`
- `src/ai_fund_lab_v2/opportunity_ai/`
- `src/ai_fund_lab_v2/position_management_ai/`
- `src/ai_fund_lab_v2/capital_allocation_ai/`
- `tests/runtime_v2/test_phase15ac_runtime_safety_decision_producer.py`
- `tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py`

## Executive Summary

Safety is now the clearest closed chain after Phase15-AC and Phase15-AD:

```text
Runtime Evidence
↓
safety_evaluation
↓
Phase11 Safety Report
↓
safety_refresh
↓
RuntimeSafetyDecision
↓
Morning / SELL / Submit
```

However, the overall Decision Chain landscape is not fully closed. The largest remaining gaps are:

- Candidate AI / Opportunity AI are not closed as regular Runtime decision producers; Morning consumes feature rows and builds `AIPlanningSignal` internally.
- Position Management AI is not connected to SELL Planning; CLI currently derives `SellExitDecision` from Current positions.
- Capital Allocation AI is not the Runtime regular decision owner; Runtime uses explicit Capital Deployment Policy and constructs `CapitalAllocationSignal`.
- Broker ReadOnly is regular for Execution, but Broker available quantity producer/consumer closure for SELL Submit still needs real Acceptance evidence.
- Reconcile exists and is used inside Execution, but no independent Reconcile decision artifact/apply chain is fully closed.
- Audit exists, but the regular CLI records an audit stage through report generation rather than invoking `run_audit` as a Runtime control.
- Operator Review and Recovery apply paths remain planned/partial, not closed Runtime controls.

Final gate:

```text
DECISION_CHAIN_GAPS_FOUND
```

## Decision Closure Matrix

| Component | Decision Owner | Input Evidence | Regular Producer | Authoritative Artifact | Regular Consumer | Runtime Action | CLI Connected | Evidence Present | Regression | Closure Status | Severity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Candidate AI | Candidate AI | Normalized market data / candidate features | Not found as Runtime v2 regular producer | Candidate feature artifacts / manifests, not proven AI decision artifact | Morning artifact reader / Runtime `AIPlanningSignal` builder | BUY candidate selection input | Partial via `market_refresh`; not direct AI execution | Feature artifact evidence exists | Feature/morning tests, not full AI decision chain | PARTIAL | HIGH |
| Opportunity AI | Opportunity AI | Candidate universe, opportunity model/features | Not found as Runtime v2 regular producer | Opportunity inference/ranking artifacts exist outside Runtime regular path | Morning indirectly consumes rows/scores | Prioritization of BUY candidates | Not directly connected | Historical/model artifacts exist | No regular Producer -> Consumer regression found | CONSUMER_MISSING | HIGH |
| Position Management AI | Position Management AI | Current positions / position features | Not found on Runtime v2 regular path | PM inference output exists outside Runtime path | SELL Planning should consume `SellExitDecision` | HOLD / REDUCE / EXIT into SELL plan | No | AI modules exist; Runtime chain absent | SELL tests cover Current-derived decisions | RUNTIME_SUBSTITUTES_DECISION | HIGH |
| Capital Allocation AI | Capital Allocation AI plus Capital Deployment Policy boundary | Opportunity rankings, positions, cash, policy | Runtime regular path loads Capital Deployment Policy; external AI producer not connected | `CapitalAllocationSignal` in OrderPlan/Pending, policy context | Planning / Pending / Submit Guard | Order sizing and capital deployment limits | Yes for policy, no for AI engine | Policy manifests and policy hash evidence present | Phase15-H/I/K/L tests | PARTIAL | MEDIUM |
| Safety | Safety Evaluation / Phase11 Safety | Current, Broker snapshot, market, orders, executions, runtime state, manual stop | `safety_evaluation` then `safety_refresh` | Phase11 Safety Report; `.runtime/runtime_state/safety/latest_safety_decision.json` | Morning / SELL / Submit / Report | REVIEW_REQUIRED / BLOCKED / HALT / side blocks | Yes | Manifest/report fields from AC/AD | Phase15-AC/AD/N/R retention tests | CLOSED | INFO |
| Market / Feature Refresh | Operations Market Refresh / Feature Refresh | Market data and feature artifact roots | `market_refresh` job | Feature date contract and generated feature artifacts | Morning Planning | Feature freshness gate and candidate rows | Yes | Manifest fields and feature contract | Phase14-E35/E36 style tests | CLOSED | LOW |
| Broker ReadOnly | Broker ReadOnly provider | Broker orders / executions / positions / cash | Execution job snapshot provider | `.runtime/runtime_state/broker_readonly/<date>/tachibana_snapshot.json` | Execution pipeline; Submit SELL quantity loader | ReadOnly ingestion, SELL guard evidence | Yes for execution; partial for submit | Snapshot path and ledger append evidence | Phase15-M / execution tests | PARTIAL | HIGH |
| Execution Classification | Execution ReadOnly pipeline | Broker ReadOnly orders/executions/positions/cash, pending/current | `execution` job | Ledger records and runtime-owned fill projection evidence | Ledger / Current projection / Report | Runtime-owned fill classification and Current update | Yes | Execution result fields, ledger counts, projection status | Phase14-E21/E23/E25 tests | CLOSED | MEDIUM |
| Reconcile | Reconcile Runtime | Pending, ledger, broker, asset state | Called inside Execution pipeline | `ReconciliationResult` in memory / stage details | Execution status, report/audit later | REVIEW_REQUIRED finding classification | Partial | Reconcile fields in execution stage | Phase13 reconcile tests, execution tests | PARTIAL | MEDIUM |
| Audit | Audit Runtime | Report, notification, delivery, reconcile, asset state | `run_audit` exists; regular CLI direct invocation not found | `AuditResult` model; generated audit artifact via report path | Operator / Recovery intended | Audit findings should drive review | Weak / stage only | Report generation emits audit-like artifact/stage | Component tests only | CLI_NOT_CONNECTED | HIGH |
| Operator Review | Operator | Manifest/report/notification/audit/review queue | No regular producer found | Operator decision artifact not fixed in Runtime v2 | Recovery / Pending / Runtime State should consume | Apply review decision | No | REVIEW_REQUIRED visible in artifacts | No apply-path regression found | PRODUCER_MISSING | HIGH |
| Recovery | Recovery Runtime / Safety Phase11 recovery evaluator | Operator decision, latest safety, failed state, broker/reconcile evidence | Phase11 dry-run/manual unlock only; Runtime v2 apply path not found | RecoveryDecision / manual unlock artifacts outside regular Runtime path | Runtime State / Pending / retry controls should consume | Safe rerun / unlock / dedup control | No | Phase11 components exist | No Runtime v2 regular apply regression found | LEGACY_ONLY | HIGH |
| Notification Delivery Decision | Notification policy / Operator policy | Report summary, notification payload, delivery ledger | Payload builder is regular; queue/sender are not regular | Payload JSON; queue/delivery models | Operator / external sender later | Payload-only explanation; no send | Payload yes, delivery no | `notification_sent=false`, `PAYLOAD_ONLY` | Phase15-R tests | PARTIAL | MEDIUM |

## Safety Chain Re-Judgment

Safety is judged `CLOSED` for Stepwise Acceptance scope.

Evidence:

- `run_runtime_safety_evaluation()` reads Runtime-owned evidence and writes Phase11 Safety Report.
- `produce_runtime_safety_decision()` normalizes Phase11 Safety Report into `RuntimeSafetyDecision`.
- CLI jobs exist: `safety_evaluation`, `safety_refresh`.
- `load_runtime_safety_decision()` is consumed by Morning, SELL Planning, and Submit.
- Missing/stale safety inputs become `REVIEW_REQUIRED`, not implicit `ALLOW`.
- Manual emergency lock maps to `HALT`.
- Regression exists in Phase15-AC and Phase15-AD.

Boundary note:

Safety closure is not a Full Runtime PASS. It is a Decision Chain closure suitable for stepwise Acceptance evidence gathering.

## Candidate AI Findings

Candidate AI owns the decision of which market names deserve attention. Runtime v2 currently does not prove a closed Candidate AI decision chain. `market_refresh` produces feature artifacts and Morning Planning reads candidate rows, but Morning builds `AIPlanningSignal` inside Runtime. No regular Runtime job was found that produces an authoritative Candidate AI decision artifact and then proves Morning consumed it.

Closure status:

```text
PARTIAL
```

Required follow-up:

- Define Candidate AI authoritative decision artifact.
- Include model/version, score, rank, confidence, feature_date, source artifact hash.
- Add regular Producer -> Morning Consumer regression.

## Opportunity AI Findings

Opportunity AI owns prioritization/ranking. The module exists, and inference/training artifacts exist outside Runtime v2, but the regular Runtime CLI does not directly invoke Opportunity AI nor clearly consume its authoritative ranking artifact. Morning selection may therefore be feature-row driven rather than Opportunity-decision driven.

Closure status:

```text
CONSUMER_MISSING
```

Required follow-up:

- Fix an Opportunity ranking artifact contract.
- Prove Morning Planning consumes that ranking rather than regenerating a Runtime-local score.

## Position Management AI Findings

This is the highest-risk non-Safety closure gap.

Expected:

```text
Current positions
↓
Position Management AI
↓
HOLD / REDUCE / EXIT
↓
SELL Planning
```

Observed:

```text
Current positions
↓
CLI _sell_exit_decisions_from_current
↓
SELL Planning
```

The current SELL chain is valid as a Current-owned liquidation/cleanup contract, but it is not a Position Management AI decision chain.

Closure status:

```text
RUNTIME_SUBSTITUTES_DECISION
```

Required follow-up:

- Separate `Current liquidation` from `AI-driven SELL`.
- Add PM AI authoritative output and `SellExitDecision` consumer contract.
- Do not call Current-derived liquidation a PM AI decision.

## Capital Allocation Findings

Phase15-H/K/L established explicit Capital Deployment Policy propagation. This protects Runtime from hidden allocation policy. However, Policy is not the same as Capital Allocation AI.

Observed:

- Runtime loads explicit Capital Deployment Policy.
- Morning/SELL build `CapitalAllocationSignal` from policy context and Runtime inputs.
- Submit validates policy hash/active policy.
- External `capital_allocation_ai.engine.run_capital_allocation_engine` is not regular CLI-connected.

Closure status:

```text
PARTIAL
```

Acceptance interpretation:

For Phase15 Demo Acceptance, policy-driven capital deployment can be accepted if explicitly scoped as `Capital Deployment Policy`, not `Capital Allocation AI`.

## Broker ReadOnly Findings

Execution has a regular Broker ReadOnly producer path through `execution` job and writes `.runtime/runtime_state/broker_readonly/<date>/tachibana_snapshot.json`.

Submit SELL guard can consume Broker available quantity evidence, but the full producer/consumer closure needs real Acceptance evidence:

- snapshot generated before Submit
- snapshot fresh
- available quantity present
- Submit manifest points to the snapshot
- insufficient quantity blocks/reviews

Closure status:

```text
PARTIAL
```

## Execution / Reconcile / Audit Findings

Execution Classification is materially connected:

```text
Broker ReadOnly
↓
Execution ReadOnly pipeline
↓
Ledger records
↓
Runtime-owned fill projection
↓
Current
```

Reconcile is partial: it is called inside Execution and produces findings, but it is not an independent CLI decision artifact with a closed Operator/Recovery consumer.

Audit is not closed: `run_audit` exists, but regular CLI direct invocation was not found. The CLI records an `audit` stage after report generation, which is not equivalent to a closed Audit decision chain.

## Fixture Dependency Matrix

| Component | Fixture / Mock Producer | Regular Producer Exists | Runtime Uses Fixture-like Behavior | Risk | Action |
|---|---|---:|---:|---|---|
| Candidate AI | Candidate mock feature builders exist | Partial feature producer only | Morning may treat rows as signals | HIGH | Define authoritative Candidate decision artifact |
| Opportunity AI | Historical/model inference artifacts exist | Not in Runtime CLI | Runtime can proceed without Opportunity artifact | HIGH | Add regular Opportunity producer/consumer contract |
| Position Management AI | Historical/dry-run PM outputs exist | No | SELL decisions are Current-derived | HIGH | Connect PM AI or label as Current liquidation |
| Capital Allocation AI | Phase7 reports/backtests | Policy producer exists, AI engine not CLI-connected | Runtime builds allocation signal | MEDIUM | Scope Phase15 to policy; defer AI engine connection |
| Safety | Phase11 dry-run exists but not used by AD | Yes | No fixture-like Runtime producer in AD path | LOW | Verify with stepwise Acceptance evidence |
| Broker ReadOnly | Tests inject snapshot providers | Yes for execution | Submit can depend on existing snapshot | HIGH | Acceptance must prove fresh snapshot before Submit |
| Execution Classification | Tests use fixture snapshots | Yes | Provider abstraction can hide real broker gap | MEDIUM | Demo Acceptance evidence required |
| Reconcile | Unit tests use object fixtures | Partial | Findings may remain in memory/stage only | MEDIUM | Add artifact/apply consumer later |
| Audit | Unit/component tests | Weak | CLI audit stage can be mistaken for `run_audit` | HIGH | Connect audit aggregator or document scope |
| Operator Review | Manual JSON possible in older safety paths | No | Human process outside Runtime | HIGH | Define operator decision artifact and apply path |
| Recovery | Phase11 dry-run/manual unlock | No Runtime v2 apply path | Recovery may be manual-only | HIGH | Defer with explicit prohibition on direct edits |
| Notification Delivery | Payload fixtures/tests | Payload yes, delivery no | Payload-only could be mistaken for sent | MEDIUM | Keep `PAYLOAD_ONLY` and require delivery phase later |

## Runtime Substitution Matrix

| Decision | Expected Owner | Actual Owner | Substitution Reason | Accepted Contract? | Severity | Required Follow-up |
|---|---|---|---|---|---|---|
| Candidate selection | Candidate AI | Runtime Morning from feature rows | Runtime needs candidates for Morning | Not as AI decision | HIGH | Candidate artifact contract |
| Opportunity ranking | Opportunity AI | Runtime / feature artifact selection | Opportunity output not consumed directly | No | HIGH | Opportunity ranking consumer |
| SELL HOLD/REDUCE/EXIT | Position Management AI | Runtime CLI Current-derived `SellExitDecision` | Current liquidation implemented first | Only for liquidation scope | HIGH | PM AI -> SELL Planning |
| Capital allocation | Capital Allocation AI | Capital Deployment Policy + Runtime signal | Phase15 focused on policy/hidden cap removal | Yes for Phase15 policy scope, no for AI | MEDIUM | Explicitly defer AI allocation |
| Audit stop/review | Audit Runtime | CLI report/audit stage | Report generation bundled artifacts | No | HIGH | Invoke/consume `run_audit` or defer |
| Operator apply | Operator Review Runtime | Manual process | Apply path not implemented | No | HIGH | Operator decision artifact |
| Recovery | Recovery Runtime | Manual rerun discipline / Phase11 dry-run | Runtime v2 recovery path absent | No | HIGH | Recovery apply contract |

## Phase15 Mandatory Fix List

Before Phase15 Acceptance can claim all decision chains closed:

- Position Management AI chain must either be connected or explicitly excluded from Phase15 Acceptance as not part of Demo SELL decision.
- Candidate / Opportunity AI chain must be scoped: either connect authoritative AI artifacts or state that Phase15 Acceptance validates Runtime Control only with artifact-based planning inputs.
- Audit must not be called closed unless `run_audit` is invoked and its findings have a consumer.
- Operator Review / Recovery must be excluded from Full Runtime PASS or implemented as a controlled apply path.

These do not all need to block Stepwise Acceptance kickoff if the Acceptance scope is clearly limited. They do block broad claims such as `all decision chains closed` or `Full Runtime Operation PASS`.

## Evidence Needed During Acceptance

Stepwise Acceptance should gather:

- Safety: real `safety_evaluation` report then `safety_refresh` decision.
- Broker ReadOnly: fresh snapshot path, snapshot time, mode, available quantity.
- Submit: manifest evidence that SELL guard consumed Broker available quantity, not Current quantity alone.
- Execution: snapshot -> ledger -> Current projection evidence.
- Report/Notification: reason propagation from policy, safety, and guard into operator-facing artifacts.
- AI Planning: explicit source artifact refs for candidate/opportunity inputs used by Morning.
- SELL: declare whether the demo SELL is PM AI-driven or Current liquidation.

## Explicit Deferred Scope

Can be deferred if documented before Acceptance judgment:

- Production notification send.
- Production broker write.
- Advanced PM AI replacement / reduction logic.
- Capital Allocation AI engine integration, if Phase15 Demo uses explicit Capital Deployment Policy instead.
- Full Operator Review apply path, if Demo Acceptance stops at REVIEW_REQUIRED and uses manual evidence refresh without direct Current/Pending edits.
- Recovery apply path, if retry/rerun remains prohibited except controlled step re-execution.

Deferral impact:

These deferrals mean Phase15 can only claim Runtime Control Acceptance for the scoped regular paths. It cannot claim that every AI decision component is fully production-connected.

## Final Recommendation

Proceed to Stepwise Acceptance only with a narrowed claim:

```text
Runtime Core Safety / Policy / Submit / Execution control can be evidence-reviewed.
AI decision closure, Operator apply, Recovery, and Audit closure remain gaps or deferred scope.
```

Do not declare Full Runtime PASS from Component PASS, payload generation, report generation, or broker snapshot presence alone.

## Final Judgment

```text
DECISION_CHAIN_GAPS_FOUND
```

## Completion String

```text
PHASE15AE_DECISION_PRODUCER_CONSUMER_CLOSURE_AUDIT_COMPLETE
```
