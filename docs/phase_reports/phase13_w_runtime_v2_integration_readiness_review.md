# Phase13-W Runtime v2 Integration Readiness Review

## Status

SYSTEM_REVIEW

Phase13-LからPhase13-Vまでで作成されたRuntime v2 skeletonが、一つのRuntime systemとして統合可能な状態かをレビューした。

本レビューでは実装変更、Submit、Broker注文、Broker API呼び出し、Demo/Production注文、通知送信、Notification send実装、launchd/plist操作、Backtest/Simulation実行、既存Runtime entrypoint呼び出しは行っていない。

## Review Scope

- `src/ai_fund_lab_v2/runtime_v2/`
- Current State Runtime
- State Machine / Orchestrator
- Ledger Runtime
- Asset Runtime
- Pending Runtime
- Broker ReadOnly Runtime
- Execution Runtime
- Planning Runtime
- Approval Runtime
- Reconcile Runtime
- Report Runtime
- Notification Runtime
- Audit Runtime
- Architecture Tests
- Phase13-L through Phase13-V reports

## Component Integration Review

Runtime v2 components are integration-ready as skeleton components. Each component is shaped around a single responsibility:

| Component | Primary responsibility | Current writer role |
| --- | --- | --- |
| Current State Runtime | fixed-path Current read and classification | none |
| State Machine / Orchestrator | side-effect-free preflight and transition validation | future `runtime_state/current_state.json` owner |
| Ledger Runtime | append-only ledger records and dedup helpers | ledger append owner |
| Asset Runtime | build and write `persistent_ledger/state.json` through explicit writer | asset current writer skeleton |
| Pending Runtime | pending plan lifecycle, promotion, consume, read/write | pending current writer skeleton |
| Broker ReadOnly Runtime | normalize broker read-only snapshots | none |
| Execution Runtime | classify fills and project broker evidence to ledger records | none |
| Planning Runtime | transform AI-style inputs plus Current State into order plan candidates | none |
| Approval Runtime | approval policy and approval-to-pending linkage | none |
| Reconcile Runtime | compare Current, ledger, and broker evidence; emit findings | none in implementation |
| Report Runtime | generate derived report artifact | none |
| Notification Runtime | generate payload and delivery dedup model | delivery ledger owner; send not implemented |
| Audit Runtime | evidence checks and runtime guard findings | none |

Review result:

- Component responsibilities are separated well enough for integration.
- Runtime v2 imports are guarded by AST-based architecture tests.
- Current Reader and Writer roles are explicit in tests and skeleton modules.
- Submit Runtime is not implemented, and no non-Submit component imports a Submit path.
- Broker Submit and Broker API imports are absent from runtime_v2 skeleton.
- Notification send is not implemented; notification work is limited to payload and delivery ledger dedup.
- No component uses `demo_ledger` as a Runtime v2 SoT.

One integration metadata issue remains: `CURRENT_STATE_CONTRACTS["persistent_ledger_state"]` lists both `Persistent Ledger Runtime` and `Reconciliation Runtime` as writer components, while the current implementation keeps Reconcile read/compare-only. This is not an active side-effect bug, but the contract metadata should be clarified before real Current writes are enabled.

## Runtime Flow Review

The intended integration flow is structurally represented:

```text
Current State
↓
Planning
↓
Approval
↓
Pending
↓
Broker ReadOnly
↓
Execution
↓
Ledger
↓
Asset
↓
Reconcile
↓
Report
↓
Notification Payload
↓
Audit
```

Review result:

- Current State reads are fixed-path reads through `.runtime/<mode>/...`.
- Planning and Approval do not write Ledger or Submit.
- Pending can represent the Submit target, but does not perform Submit.
- Broker ReadOnly normalizes snapshots only and does not call Broker APIs.
- Execution projection creates ledger records from broker evidence; it does not create asset state directly from BrokerOrder alone.
- Ledger and Asset are separated: positions and cash are derived from ledger records before becoming `CurrentAssetState`.
- Reconcile emits findings and policy results; it does not call asset or pending writers.
- Report and Notification Payload are Derived outputs, not Runtime Current inputs.
- Audit is Evidence-only and not a Submit source.

## Current SoT Review

Runtime v2 Current SoT paths are fixed and unique by role.

| Current SoT | Fixed path | Owner | Writer status |
| --- | --- | --- | --- |
| Runtime State | `runtime_state/current_state.json` | Runtime State Machine | contract owner defined; skeleton preflight reads only |
| Pending Order Plan | `pending_order_plan/pending_order_plan.json` | Pending Plan Runtime | writer skeleton exists |
| Asset State | `persistent_ledger/state.json` | Persistent Ledger / Asset Runtime | asset writer skeleton exists |
| Notification Delivery Ledger | `notification_delivery/delivery_ledger.jsonl` | Notification Runtime | dedup model exists; send not implemented |

Current Reader examples:

- Current State Reader reads fixed Current paths.
- Orchestrator reads `persistent_ledger_state`, `runtime_state`, and `pending_order_plan`.
- Planning reads asset/current state by model input.
- Approval reads pending/approval linkage by model input.
- Report reads Current refs as source references but remains Derived.
- Audit reads evidence and Current-shaped inputs for checks only.

Current Writer examples:

- `asset.writer.write_current_asset_state` writes `persistent_ledger/state.json` only when explicitly called and blocks production runtime paths in skeleton phase.
- `pending.writer.write_pending_order_plan` writes `pending_order_plan/pending_order_plan.json` only when explicitly called and blocks production runtime paths in skeleton phase.
- Notification delivery ledger currently models dedup records; notification send and actual delivery write path are not implemented.

Review result:

- Current SoT is one per role.
- No date-based Current resolution was found.
- No History or Derived fallback is used for Current.
- Active implementation has no writer conflict.
- Contract metadata for `persistent_ledger_state` should be tightened so Reconciliation Runtime is not interpreted as a direct writer of asset current.

## Transaction Review

The transaction design can be integrated in the expected order:

```text
Current Read
↓
Planning
↓
Pending
↓
Broker ReadOnly
↓
Ledger
↓
Asset
↓
Reconcile
↓
Report
↓
Notification Payload
```

Review result:

- Current Read is fixed-path and mode/environment validated.
- Planning is side-effect-free and can be retried.
- Pending lifecycle distinguishes approved, submitted, consumed, post-send unknown, and review-required states.
- Ledger append and dedup helpers support idempotent append-style transaction points.
- Asset state is built from ledger positions/cash, not BrokerOrder alone.
- Reconcile can be a recovery/checkpoint step without mutating Current.
- Report and Notification Payload are generated after Current/ledger evidence and are not commit inputs.
- Delivery dedup exists at model/helper level for notification payload hash/channel/date.

Remaining integration details for later phases:

- Atomic write strategy for production Current files is not yet implemented in the skeleton.
- Restart point persistence for full orchestration is not yet implemented.
- Submit transaction boundary remains out of scope because Submit Runtime is not implemented.

## Runtime Data Flow Review

The Runtime Data Model flow is preserved:

```text
AI Signal
↓
Planning
↓
OrderPlan
↓
Pending
↓
BrokerOrder
↓
BrokerExecution
↓
LedgerExecution
↓
LedgerPosition
↓
CurrentAssetState
↓
Report
↓
Notification Payload
```

Review result:

- BrokerOrder alone is not used to create Asset SoT.
- BrokerExecution and ledger projection exist as the path toward positions/assets.
- Report is marked `derived=true` and `not_current_state=true`.
- NotificationPayload is marked `derived=true` and `not_current_state=true`.
- AuditResult is marked `evidence_only=true` and `not_submit_source=true`.
- ReconciliationResult is marked evidence/non-current/non-submit-source in Phase13-V.

## Runtime Safety Review

Safety states are represented by readers, classifiers, lifecycle guards, and reconciliation findings.

| Condition | Review result |
| --- | --- |
| Current Missing | classified and causes review/blocking behavior in preflight |
| Current Unknown | not treated as confirmed empty |
| Current Stale | contract/test coverage exists at skeleton level |
| Review Required | propagated by pending, reconcile, report, audit |
| POST_SEND_UNKNOWN | cannot auto-resubmit |
| BROKER_DIVERGENCE | represented by reconcile findings |
| LEDGER_DIVERGENCE | represented by reconcile findings |
| broker_orders_fallback | integrated into `run_reconciliation`; production fallback halts |

The system tends toward review-required, blocked, or halt states instead of assuming empty holdings or successful side effects.

## Architecture Test Review

`tests/runtime_v2/` was executed as the lightweight Runtime v2 test suite.

```text
python3 -m pytest -q tests/runtime_v2/
232 passed in 0.60s
```

Coverage by area:

| Area | Representative coverage |
| --- | --- |
| Current | contracts, path resolver, fixed-path reader, missing/unknown/invalid classification |
| Pending | model, lifecycle, promotion, consume, read/write, no fallback |
| Ledger | append, dedup, order/execution/position/cash models |
| Asset | asset builder, writer skeleton, no BrokerOrder-only asset SoT |
| Broker | read-only snapshot models and normalizer |
| Execution | fill classifier and ledger projection |
| Planning | planning models, Current guard, order plan builder, no side effects |
| Approval | approval models, policy, approval-to-pending linkage |
| Reconcile | pending/order/execution/position/cash checks, fallback policy integration |
| Report | derived report artifact and report builder |
| Notification | payload generation, delivery ledger dedup |
| Audit | report/payload checks, evidence-only result |
| Import Guard | no legacy runtime import, no obvious cycles, no forbidden component imports |
| No Side Effects | orchestrator, ledger/asset, pending, broker/execution, reconcile, planning/approval, report/notification/audit |

Potential test additions for later phases:

- Atomic production Current write tests.
- Full orchestration restart point tests.
- Contract metadata test enforcing single direct writer for `persistent_ledger_state`.
- Legacy isolation tests after Phase13-X changes are introduced.

## Legacy Runtime Isolation Readiness

Runtime v2 is ready to proceed to Legacy Runtime Isolation planning/work.

Review result:

- `runtime_v2` exists as a separate package.
- Runtime v2 tests guard against importing legacy runtime, operations, and broker modules.
- Current SoT paths are defined inside Runtime v2 path resolver and contracts.
- Existing Runtime workflow is not used as the Runtime v2 normal flow.
- Legacy entrypoint isolation can proceed without needing Submit, Broker API, notification send, launchd, or plist changes in this phase.

## Findings

### Major

None.

No issue was found that breaks Runtime v2 safety, Current SoT, side-effect sealing, or legacy isolation readiness.

### Medium

- `persistent_ledger_state` contract metadata lists `Reconciliation Runtime` as a writer, while implementation and architecture guard tests keep Reconcile read/compare-only. Before production Current writes are enabled, the contract should distinguish direct Current writer from evidence/finding producer, or remove Reconciliation Runtime from the direct writer list.

### Minor

- Atomic write and restart point tests are still future integration work.
- Notification delivery ledger has dedup model coverage, but actual send/write integration remains intentionally unimplemented.
- Full orchestration integration remains skeleton-level because Submit Runtime is intentionally absent.

## Go / No-Go

GO_WITH_MINOR_FIXES

Reason:

- Runtime v2 skeleton components are separable, testable, and integration-ready.
- Current SoT paths are fixed and not inferred from History or Derived artifacts.
- Broker Submit, Broker API, notification send, launchd/plist, Backtest, and Simulation remain sealed.
- Runtime v2 test suite passes.
- One contract metadata issue should be clarified before real Current write integration, but it does not block Legacy Runtime Isolation readiness.

## Phase13-X Handoff

GO_TO_PHASE13_X

Phase13-X can proceed toward Legacy Runtime Isolation with the following guardrails:

- Do not enable production Current writes yet.
- Do not introduce Submit Runtime or Broker API calls.
- Keep legacy runtime entrypoints isolated rather than reused.
- Add/adjust contract tests if `persistent_ledger_state` writer metadata is clarified during isolation work.

## Acceptance Criteria Review

- Runtime v2 integration review is complete.
- Component Integration Review is complete.
- Runtime Flow Review is complete.
- Current SoT Review is complete.
- Transaction Review is complete.
- Architecture Test Review is complete.
- Legacy Runtime Isolation Readiness is confirmed.
- GO / GO_WITH_MINOR_FIXES / REVIEW_REQUIRED / NO_GO judgement is defined.
- Phase13-X handoff judgement is defined.
- Implementation was not changed.

