# Phase15-T Runtime State Machine & State Transition Review

Date: 2026-07-09

Final judgment:

```text
PHASE15T_RUNTIME_STATE_MACHINE_REVIEW_COMPLETE
```

## Purpose

Phase15-T reviews Runtime v2 state reliability after Phase15-H through Phase15-S.

This phase does not implement fixes. It audits whether Runtime State itself, Current, History, Pending, Approval, Submit, Manifest, Report, and Notification are separated and transition coherently enough to proceed to Demo Runtime State review.

## Scope

Reviewed Runtime states:

```text
Policy State
Safety State
Morning State
OrderPlan State
Pending State
Approval State
Submit State
Broker State
Execution State
Ledger State
Current State
Manifest State
Report State
Notification State
```

Reviewed state machine target:

```text
Idle
↓
Market Refresh
↓
Feature Ready
↓
Morning Planning
↓
Pending Ready
↓
Approval Ready
↓
Submit Ready
↓
Broker Submit
↓
Execution Ready
↓
Ledger Updated
↓
Current Updated
↓
Report Ready
↓
Notification Ready
↓
Completed
```

## Evidence Checked

- `src/ai_fund_lab_v2/runtime_v2/state_machine/models.py`
- `src/ai_fund_lab_v2/runtime_v2/state_machine/transitions.py`
- `src/ai_fund_lab_v2/runtime_v2/orchestrator/orchestrator.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/contracts/current_state_contracts.py`
- `src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/current_state/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/current_state/writer.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/consume.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/payload.py`
- Phase15-H through Phase15-S reports and regressions

## State Inventory

| State | SoT | Producer | Consumer | Entry Condition | Exit Condition | Runtime Path | Evidence | Retry | Gap |
|---|---|---|---|---|---|---|---|---|---|
| Idle | `runtime_state/current_state.json` / CLI start manifest | Runtime State / CLI | CLI / Orchestrator | No active operation or new CLI invocation | Market refresh or preflight starts | `run_daily_operation` | manifest `cli_start`, state machine `IDLE` | Yes | Global RuntimeState is preflight-oriented, not updated after every job state. |
| Market Refresh | feature artifact output dir | Market Refresh pipeline | Feature consumers / Morning | `market_refresh` job starts | Feature artifacts generated or REVIEW_REQUIRED | CLI `market_refresh` | stage `runtime_v2_market_refresh_pipeline` | Yes | State table has `MARKET_DATA_READY`, but job evidence is manifest/artifact-driven. |
| Feature Ready | `.runtime/operations/feature_artifacts` | Market Refresh / Feature Refresh | Morning Planning | Feature artifacts exist and freshness contract resolves | Morning reads selected feature date | CLI `market_refresh` then `morning` | feature date contract, pending feature context | Yes | AI inference state is checkpoint/evidence, not direct RuntimeState update. |
| Morning Planning | OrderPlan artifact and Pending Current | Morning Planning pipeline | Pending / Approval / Submit | Policy + Safety + Current + feature evidence available | OrderPlan/Pending/Approval written or no-signal/review state written | CLI `morning` | Morning stage details, order_plan artifact, pending plan | Yes | Candidate/Opportunity AI direct state remains deferred. |
| OrderPlan State | order_plan artifact under runtime artifacts | Planner | Pending promotion / Approval | PlanningInput with policy/safety context | Pending promotion completes | Morning/SELL pipeline | order_plan JSON, safety/policy fields | Yes by regenerating plan | No hard global state transition from `DAILY_PLAN_CREATED` to artifact state. |
| Pending State | `.runtime/pending_order_plan/pending_order_plan.json` | Pending writer / promotion | Approval / Submit / Report | OrderPlan items promoted, or no-signal pending written | APPROVED, SUBMITTED, CONSUMED, REVIEW_REQUIRED, BLOCKED, EXPIRED | Planning and Submit | pending lifecycle and pending current | Controlled | Pending is overwritten by new planning; retention/history of prior pending is artifact-dependent. |
| Approval State | approval artifact and embedded Pending approval link | Approval Runtime / planning pipeline | Submit | Pending approval request exists | Pending linked as APPROVED or review/block | Morning/SELL pipeline | approval artifact, pending approval link | Yes before Submit | Approval artifact is derived from Pending for Submit and not Current. |
| Submit Ready | Pending state APPROVED with approval link, policy/safety/broker evidence | Pending + Approval + Policy + Safety | Submit pipeline | `can_submit_pending_plan` and `_pending_submit_guard` pass | Submit guard passes and broker adapter invoked, or BLOCKED/REVIEW_REQUIRED | CLI `submit` | submit manifest, guard evidence | Controlled; dedup blocks double submit | RuntimeState `SUBMITTING/SUBMITTED` exists but is not the primary submit SoT. |
| Broker Submit | Broker adapter result / order ledger record | Submit adapter | Execution / Ledger / Report | Submit guard and preflight pass | Broker accepted/rejected/unknown or blocked | Submit pipeline | ledger orders, item_results, manifest | Risky; unknown requires review | Broker write is only within explicit submit path; Demo/production acceptance separate. |
| Execution Ready | Broker ReadOnly snapshot | Execution ReadOnly provider | Ledger projection / Reconcile | Execution job starts and snapshot exists | Ledger append/reconcile/projection | CLI `execution` | broker_readonly snapshot/report | Yes | Snapshot producer operational evidence remains Demo review item. |
| Ledger Updated | `persistent_ledger/*.jsonl` | Submit / Execution / Ledger writer | Current Projection / Report / Reconcile | Submit or Broker ReadOnly evidence normalized | Append-only records written | Submit and Execution | orders/executions/positions/cash/events JSONL | Idempotence depends on dedup/source keys | Append-only boundary is clear; retry semantics need Demo evidence. |
| Current Updated | `persistent_ledger/state.json` | Asset Runtime / runtime-owned fill projection | Planning / Submit / Report | Execution acceptance PASS and runtime-owned projection passes | Current snapshot written | Execution pipeline projection | state.json, projection details | Careful; should be regular projection only | Current update occurs only after execution PASS; direct edit prohibited. |
| Manifest State | `runtime_state/run_manifest/<date>/*.json` | CLI manifest writer | Report / Operator / Audit | CLI run finishes | Manifest written | CLI all jobs | run manifest JSON | Yes per new run | Manifest can show PASS while artifact-level state still needs inspection. |
| Report State | `reports/runtime_v2/<date>/runtime_report.*` and public report | Report writer | Operator / Notification payload | Current fixed paths and optional latest manifest evidence readable | Reports written; redaction scan passes or REVIEW_REQUIRED | CLI report generation | runtime/public report files | Yes | Report is derived and not state authority. |
| Notification State | `notification_payload.json` | Report writer / notification payload builder | Operator / future queue/delivery | Report summary exists | Payload-only artifact written | CLI report generation | payload JSON | Yes | Queue/delivery/sender not connected for Phase15; payload-only only. |
| Completed | CLI manifest final state + report/payload artifacts | CLI | Operator / next job | Report/Notification payload stage completed | Next operation starts | CLI | manifest final_state/exit_code | Yes | No single explicit `COMPLETED` RuntimeState enum; completion is manifest-level. |

## Current / History Boundary

Current SoT:

```text
persistent_ledger/state.json
```

History:

```text
persistent_ledger/orders.jsonl
persistent_ledger/executions.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/cash.jsonl
persistent_ledger/events.jsonl
```

Boundary review:

| Boundary | Writer | Reader | Finding | Status |
|---|---|---|---|---|
| Current only update | Asset Runtime / runtime-owned fill projection | Planning, Submit, Report | `state.json` is snapshot SoT and is not written by Report/Notification. | PASS |
| History only update | Ledger Runtime / Submit / Execution | Reconcile, Report, Audit | JSONL files are append-only history by contract. | PASS |
| Both update | Execution pipeline | Report / next Planning | Execution appends history and updates Current only after acceptance/projection. | PASS |
| Report only update | Report writer | Operator / Notification | Reports are derived under `reports/`; no Current write. | PASS |
| Manifest only update | CLI manifest writer | Report / Operator | Manifest is evidence, not Current or Pending SoT. | PASS |

Conclusion:

```text
CURRENT_HISTORY_BOUNDARY_PASS
```

## Pending State Review

Pending lifecycle implementation:

```text
PENDING_APPROVAL
↓
APPROVED
↓
SUBMITTING
↓
SUBMITTED / POST_SEND_UNKNOWN / REVIEW_REQUIRED
↓
CONSUMED / REVIEW_REQUIRED
```

Findings:

- Pending generation writes the canonical pending path.
- Approval linkage embeds approval evidence into Pending.
- Submit rejects dangerous pending states including `SUBMITTING`, `SUBMITTED`, `POST_SEND_UNKNOWN`, `CONSUMED`, `BLOCKED`, and `REVIEW_REQUIRED`.
- Submit requires `APPROVED`, approval link, target session date, matching approved item IDs, and not consumed.
- Pending is consumed only after ledger order records are appended for submitted records.
- If Submit is blocked before broker boundary, ledger records are not appended and Pending is not consumed.
- If submitted records exist, Pending moves to `SUBMITTED` then `CONSUMED`.

Risks:

- Pending is a snapshot and can be overwritten by later planning; historical pending state retention depends on artifacts/manifests rather than a pending history ledger.
- Retry after partial submit/unknown still requires operator evidence; apply/recovery path is out of scope.

Status:

```text
PENDING_STATE_PASS_WITH_RETRY_REVIEW_GAP
```

## Approval State Review

Approval state findings:

- Approval is created from Pending/OrderPlan context.
- Submit reconstructs approval from Pending link rather than treating approval artifact as Current.
- Policy hash / policy source / safety context are preserved in Approval/Pending.
- Approval artifact is not mixed into Current.

Risks:

- Human Operator approval semantics and apply path remain outside Phase15-T.

Status:

```text
APPROVAL_STATE_PASS
```

## Submit State Review

Submit requires:

- Pending
- Approval
- Active Policy
- Policy hash consistency
- Runtime Safety
- Submit Guard
- Broker preflight / adapter evidence
- SELL broker available quantity evidence for SELL

Failure behavior:

- Policy mismatch returns REVIEW_REQUIRED without broker write.
- Safety HALT/BLOCKED/REVIEW_REQUIRED stops before broker boundary.
- Submit guard BLOCKED prevents adapter submit.
- Preflight failure creates item result and does not append ledger order.
- Adapter blocked/not ready does not append ledger order.
- Ledger orders append only for submitted results.
- Pending consume occurs only if ledger records exist.

Status:

```text
SUBMIT_STATE_PASS_FOR_GUARDED_DEMO_REVIEW
```

Gap:

```text
Actual broker write/fill lifecycle remains Demo evidence, not Phase15-T proof.
```

## Broker Boundary Review

Broker transition:

```text
Broker Write preflight
↓
Broker Accepted / Rejected / Unknown
↓
Execution ReadOnly
↓
Ledger
↓
Current Projection
```

Findings:

- Broker write is behind Submit Guard and explicit submit-enabled CLI.
- Accepted/unknown/rejected are represented in Submit item results and ledger order records when submitted.
- Execution ReadOnly reads broker snapshot later and does not overwrite Current from broker cash/positions directly.
- Runtime-owned fill projection updates Current only after execution acceptance.

Gaps:

- Broker available quantity snapshot producer evidence remains a Demo review item.
- Unknown/retry/recovery needs Operator/Recovery path outside Phase15-T.

Status:

```text
BROKER_STATE_PARTIAL
```

## Current Projection Review

Execution to Current:

```text
Execution
↓
Ledger
↓
Runtime-owned fill projection
↓
Current
```

Findings:

- Execution ReadOnly appends ledger evidence first.
- Current projection is runtime-owned and excludes broker-only positions.
- Current remains the only Asset SoT.
- Report and Notification do not update Current.

Status:

```text
CURRENT_PROJECTION_PASS
```

## Report State Review

Report state findings:

- Report is Derived only.
- Report reads fixed Current paths.
- Report reads latest Manifest as explanation evidence only.
- Report does not update Current.
- Report does not recalculate Policy, Safety, or Submit Guard.
- Report is not a Submit source.

Status:

```text
REPORT_STATE_PASS
```

## Notification State Review

Notification state model:

```text
Payload
↓
Queue
↓
Delivery
↓
Sender
↓
Real Send
```

Phase15-T finding:

- Payload is generated.
- Payload carries reason summary and severity.
- Queue/Delivery/Sender/Real Send are not part of Phase15 acceptance.
- Payload explicitly records:

```text
notification_delivery_status=PAYLOAD_ONLY
notification_sent=false
```

Status:

```text
NOTIFICATION_STATE_PAYLOAD_ONLY_PASS
```

## Runtime State Invariants

| Invariant | Finding | Status |
|---|---|---|
| Current is updated only by Current/Asset projection paths | Execution projection writes Current after PASS; Report/Notification do not write Current. | PASS |
| Pending writes only Pending | Pending writer owns canonical pending path. | PASS |
| Approval remains Approval/Pending-linked evidence | Approval does not become Current. | PASS |
| Report never writes Current | Phase15-R tests confirm no Current mutation. | PASS |
| Manifest is evidence only | Manifest is read by Report for reason evidence, not used as Current. | PASS |
| Notification is payload only in Phase15 | Payload-only fields enforced; real send not executed. | PASS |
| History is append-only | Ledger JSONL contracts mark append-only. | PASS |
| Pending double submit is blocked | `CONSUMED`, `SUBMITTED`, `POST_SEND_UNKNOWN`, etc. are blocked by Submit guard. | PASS |

## Hidden State Review

| Hidden State Risk | Finding | Status |
|---|---|---|
| hidden Current | Fixed path resolver rejects mode-rooted Current; Report/CLI guard against forbidden paths. | PASS |
| hidden Pending | Canonical pending path exists; no alternate regular pending source found. | PASS |
| hidden Approval | Approval is linked to Pending; standalone artifact is not Submit SoT. | PASS |
| hidden Runtime cache | No in-memory/global state cache observed in regular Runtime path; CLI writes manifest per run. | PASS |
| hidden global variable | No mutable global state controlling state transition found in reviewed modules. | PASS |
| hidden fallback state | Some fallback statuses are `unknown` for report display, but not used as Current or Submit state. | PASS |
| hidden temporary state | Broker snapshots and artifacts are evidence paths, not Current SoT. | PASS |

## State Transition Gaps

| Transition | Status | Evidence | Severity | Required Fix |
|---|---|---|---|---|
| `IDLE -> MARKET_DATA_READY -> FEATURE_READY -> CURRENT_STATE_LOADED` | IMPLEMENTED_FOR_PREFLIGHT | State machine transitions and `RuntimeOrchestrator.run_preflight`. | LOW | None before Demo State review. |
| `CURRENT_STATE_LOADED -> AI_INFERENCE_DONE -> DAILY_PLAN_CREATED` | PARTIAL | CLI has checkpoints; Morning creates internal AIPlanningSignal from artifacts. | MEDIUM | Define AI artifact/direct execution state contract later. |
| `DAILY_PLAN_CREATED -> PENDING_PROMOTED` | IMPLEMENTED_BY_ARTIFACT | OrderPlan and Pending promotion in Morning/SELL pipelines. | LOW | Optional: connect explicit RuntimeState update in future. |
| `PENDING_PROMOTED -> APPROVAL_PENDING -> APPROVED` | IMPLEMENTED_BY_PENDING_APPROVAL | Approval artifact and Pending approval link. | LOW | None for Phase15-T. |
| `APPROVED -> SUBMITTING -> SUBMITTED` | PARTIAL | Submit pipeline updates ledger/Pending consume for submitted records; global RuntimeState not updated. | MEDIUM | Future explicit RuntimeState write per submit lifecycle. |
| `SUBMITTING -> REVIEW_REQUIRED/BLOCKED/HALT` | IMPLEMENTED_BY_RESULT_MANIFEST | Submit result status and manifest evidence. | LOW | None for Demo State review. |
| `SUBMITTED -> MONITORING_FILL` | PARTIAL | Execution ReadOnly job is separate CLI job after Submit. | MEDIUM | Demo review should verify operational handoff. |
| `MONITORING_FILL -> LEDGER_UPDATED` | IMPLEMENTED | Execution pipeline appends ledger records. | LOW | None for Phase15-T. |
| `LEDGER_UPDATED -> RECONCILED` | IMPLEMENTED | Execution pipeline runs reconciliation. | LOW | None for Phase15-T. |
| `RECONCILED -> CURRENT_UPDATED` | IMPLEMENTED_BY_PROJECTION | Runtime-owned fill projection writes Current on PASS. | LOW | None for Phase15-T. |
| `CURRENT_UPDATED -> REPORT_READY` | IMPLEMENTED | CLI report generation reads Current and writes reports. | LOW | None for Phase15-T. |
| `REPORT_READY -> NOTIFICATION_READY` | IMPLEMENTED_PAYLOAD_ONLY | Notification payload JSON generated. | LOW | Queue/delivery later. |
| `NOTIFICATION_READY -> COMPLETED` | PARTIAL | CLI manifest final_state/exit_code records completion; no `COMPLETED` enum. | MEDIUM | Optional explicit Completed state in later Runtime State work. |
| Failure retry / recovery | GAP | Operator Review/Recovery apply path out of scope. | HIGH | Defer to Operator/Recovery phase before full autonomous operation. |

## Runtime State Trust

| State | Trust |
|---|---|
| Policy State | PASS |
| Safety State | PASS |
| Planning State | PASS |
| Pending State | PASS |
| Approval State | PASS |
| Submit State | PASS |
| Broker State | PARTIAL |
| Execution State | PASS |
| Ledger State | PASS |
| Current State | PASS |
| Manifest State | PARTIAL |
| Report State | PASS |
| Notification State | PASS |

Trust interpretation:

- `PASS`: state boundary is clear enough for Demo State review.
- `PARTIAL`: state boundary is acceptable for Demo State review but not enough for Full Runtime PASS.
- `GAP`: must be fixed before Demo State review.

No GAP was found inside the Phase15-T Demo State review entry boundary.

## Runtime State Gate

Phase15-T gate decision:

```text
READY_FOR_DEMO_RUNTIME_STATE_REVIEW
```

Meaning:

- Runtime state boundaries are coherent enough to proceed to Demo Runtime State review.
- This does not execute Demo.
- This does not declare Full Runtime PASS.
- Broker/Recovery/Operator state gaps remain for later acceptance.

## Prohibited Actions Confirmation

This phase did not perform:

- Runtime implementation changes
- Broker Write
- Demo orders
- Production orders
- Notification real send
- launchd/plist changes
- Current edits
- Runtime bypass creation

## Final Judgment

```text
PHASE15T_RUNTIME_STATE_MACHINE_REVIEW_COMPLETE
```
