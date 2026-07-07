# Phase13 Runtime Architecture v2 Design

作成日: 2026-07-06

判定: DESIGN DRAFT

## Purpose

Phase13 は AI 層を変更せず、Runtime の状態管理を作り直す。

目的は以下の3点に絞る。

- `Current State` / `History` / `Derived` を分離する。
- `pending_order_plan` を Submit 唯一の Source of Truth として完成させる。
- `persistent_ledger` を保有・現金・注文・約定・lifecycle の共通 Current State として本線接続する。

Phase13 では Production 注文、AI再学習、銘柄選定モデル変更、launchd自動運用再開は行わない。

## Design Inputs

本設計は以下を前提にする。

- Phase12.5 は `REVIEW_REQUIRED / CLOSED_FOR_REDESIGN`。
- Submit read switch は完了済みで、Submit対象は `.runtime/operations/pending_order_plan/pending_order_plan.json` 固定。
- `pending_order_plan` は schema / writer / reader / hash / approval linkage / submit guard まで実装済み。
- `pending_order_plan` の consume lifecycle は未完成。
- `persistent_ledger` は writer / reader / state aggregation まで実装済み。
- `persistent_ledger` は Runtime 本線未接続。
- `demo_ledger` はまだ Submit / Fill Monitor / Reconcile / Report で現役。
- Broker Orders fallback は Demo 限定の review-required 補助経路としてだけ許可する。
- Production では Broker Positions / Broker Executions が正規 SoT であり、Broker Orders fallback で保有確定してはいけない。

## Artifact Classification

### Current State

Runtime が現在状態として読む固定パス。

| State | Fixed path | Owner |
| --- | --- | --- |
| Submit target | `.runtime/operations/pending_order_plan/pending_order_plan.json` | Pending Plan |
| Pending consumed archive | `.runtime/operations/pending_order_plan/consumed/YYYY-MM-DD/<pending_plan_id>.json` | Pending Plan |
| Current holdings | `.runtime/operations/persistent_ledger/state.json` | Persistent Ledger |
| Current cash / buying power | `.runtime/operations/persistent_ledger/state.json` | Persistent Ledger |
| Order history | `.runtime/operations/persistent_ledger/orders.jsonl` | Persistent Ledger |
| Execution history | `.runtime/operations/persistent_ledger/executions.jsonl` | Persistent Ledger |
| Position state history | `.runtime/operations/persistent_ledger/positions.jsonl` | Persistent Ledger |
| Cash history | `.runtime/operations/persistent_ledger/cash_history.jsonl` | Persistent Ledger |
| Lifecycle events | `.runtime/operations/persistent_ledger/events.jsonl` | Persistent Ledger |
| Runtime day status | `.runtime/operations/runtime_state/current.json` | Phase13 new thin state |

`runtime_state/current.json` is intentionally thin. It may point to the latest manifest, pending state, ledger state, and last completed operation, but it must not duplicate holdings or cash.

### History / Evidence

All date-keyed operation artifacts are History or Evidence unless explicitly promoted into Current State by a Phase13 writer.

Examples:

- `order_plan/YYYY-MM-DD/order_plan.json`
- `approval_request/YYYY-MM-DD/approval_request.json`
- `approval_artifact/YYYY-MM-DD/approval_artifact.json`
- `submitted_orders/YYYY-MM-DD/submitted_orders.json`
- `broker_orders/YYYY-MM-DD/orders.json`
- `broker_executions/YYYY-MM-DD/executions.json`
- `broker_positions/YYYY-MM-DD/positions.json`
- `broker_buying_power/YYYY-MM-DD/buying_power.json`
- `fill_events/YYYY-MM-DD/fill_events.json`
- `reconciliation_result/YYYY-MM-DD/reconciliation_result.json`
- `daily_manifest/YYYY-MM-DD/daily_manifest.json`

History may be read for hash verification, audit, display, or explicit ingestion. Runtime must not auto-select executable state from History.

### Derived

Derived artifacts never become operational SoT.

- `reports/YYYY-MM-DD/*`
- `daily_report_refs/YYYY-MM-DD/daily_report_refs.json`
- `notifications/YYYY-MM-DD/notification_result.json`
- public/blog/LINE/Discord payloads
- `audit_result/audit_result.json`

## Pending Plan Lifecycle

Phase13 completes Pending Plan Phase D.

Allowed states:

```text
PENDING_APPROVAL
APPROVED
SUBMITTING
SUBMITTED
CONSUMED
EXPIRED
BLOCKED
```

Required transition rules:

| From | To | Allowed when |
| --- | --- | --- |
| `PENDING_APPROVAL` | `APPROVED` | Approval linkage passes path/hash/item/expiry checks |
| `PENDING_APPROVAL` | `BLOCKED` | Approval linkage fails or approval blocks |
| `APPROVED` | `SUBMITTING` | Submit guard passes immediately before broker order loop starts |
| `SUBMITTING` | `SUBMITTED` | Submit artifact written and at least one order reached accepted/review/blocked terminal submit classification |
| `SUBMITTED` | `CONSUMED` | Submitted artifact path, counts, and consume metadata are persisted and archive copy is written |
| `APPROVED` | `EXPIRED` | Approval expiry or intended submit date is stale |
| `SUBMITTING` | `BLOCKED` | Only if no broker API call started and failure is pre-send |
| `SUBMITTING` | `REVIEW_REQUIRED` behavior | State file remains `SUBMITTING`; loader returns review when stale or in progress |

`SUBMITTED`, `CONSUMED`, and `EXPIRED` are terminal for Submit. They must block resubmit.

### Consume Metadata

`pending.consume` must be updated with:

- `submit_run_date`
- `submitted_orders_path`
- `submitted_order_count`
- `accepted_order_count`
- `blocked_item_count`
- `review_required_item_count`
- `broker_order_api_called`
- `demo_order_submitted`
- `production_order_submitted=false`
- `consume_status`
- `consumed_at`

The consumed archive must be written before the current pending can be replaced by a future plan.

## Persistent Ledger Ingestion

Persistent Ledger becomes the only durable Current State storage for Demo and Production.

### Ingestion Sources

| Source | Writes |
| --- | --- |
| Submit result | `orders.jsonl`, `events.jsonl` |
| Broker Orders | `orders.jsonl`, optionally Demo fallback executions/positions |
| Broker Executions | `executions.jsonl`, `positions.jsonl`, `events.jsonl` |
| Broker Positions | `positions.jsonl`, `events.jsonl` |
| Broker Buying Power / Account Summary | `cash_history.jsonl` |
| Fill Monitor | `events.jsonl` |
| Reconcile | `events.jsonl` |

All writes must keep:

- `environment`
- `source`
- `business_date`
- safe hashed broker IDs only
- `review_required`
- `production_equivalent`
- `raw_request_saved=false`
- `raw_response_saved=false`
- `secret_saved=false`
- `plain_broker_ids_saved=false`

### Broker Positions / Executions Priority

Production position state priority:

1. Broker Positions API
2. Broker Executions API
3. existing `persistent_ledger/state.json`
4. `REVIEW_REQUIRED`

Demo position state priority:

1. Broker Positions API
2. Broker Executions API
3. Broker Orders fallback projection
4. existing `persistent_ledger/state.json`

Demo fallback projection is allowed only when Broker Orders shows all of:

- filled status
- executed quantity greater than zero
- remaining quantity zero

Fallback projection must set:

```json
{
  "source": "broker_orders_fallback",
  "review_required": true,
  "production_equivalent": false,
  "broker_executions_api_confirmed": false,
  "broker_positions_api_confirmed": false
}
```

Production must not write Broker Orders fallback into `current_positions`.

## Mainline Read Switches

### Daily Plan

Daily Plan must read current holdings from `get_current_positions(root)` before generating SELL candidates, max position checks, and replacement capacity.

Rules:

- `state_missing=true` means current positions are unknown, not zero.
- Unknown positions should produce `REVIEW_REQUIRED` or `BLOCK`, not extra BUY capacity.
- Broker positions may refresh the ledger, but Daily Plan should then read the refreshed ledger state.
- Dated `broker_positions/YYYY-MM-DD` must not be the only current holding source.

### Approval

Approval must read exposure and cash from `persistent_ledger/state.json`.

Rules:

- Current exposure comes from `current_positions.market_value`.
- Cash / buying power comes from `current_cash`.
- `submitted_orders` fallback is only same-run evidence and should not be normal current exposure.
- Missing current cash or unknown current positions returns `REVIEW_REQUIRED`.

### Submit

Submit remains pending-only.

Phase13 adds:

- transition `APPROVED -> SUBMITTING` before submit loop
- persistent ledger order writes after submitted artifact creation
- transition to `SUBMITTED` / `CONSUMED`
- consumed archive
- stale `SUBMITTING` runbook metadata

POST_SEND_UNKNOWN must not be retried. It must go to Broker ReadOnly confirmation and then `ACCEPTED` or `REVIEW_REQUIRED`.

### Fill Monitor

Fill Monitor writes lifecycle events into `persistent_ledger/events.jsonl`.

When broker executions or broker positions exist, Fill Monitor or Broker ReadOnly ingestion updates executions/positions/cash in persistent ledger. Demo fallback projection is allowed only with review-required metadata.

### Reconcile

Reconcile must explicitly separate:

- submitted order evidence
- broker order state
- broker execution state
- persistent current holdings
- pending consume state

`ledger/YYYY-MM-DD` remains a daily derived broker summary, not the durable ledger.

### Report / Notification

Report and notification must display four separate sections:

1. Today's Submit result: `submitted_orders/YYYY-MM-DD`
2. Execution confirmation: Broker Executions, or Demo fallback review
3. Current holdings / cash: `persistent_ledger/state.json`
4. Next candidates: `order_plan/YYYY-MM-DD`

Report must show source and review flags for current positions.

## demo_ledger Legacy Policy

`demo_ledger/` becomes legacy-only.

Phase13 steps:

1. Stop adding new feature dependencies on `demo_ledger`.
2. Replace `record_demo_submit_result` and `record_demo_readonly_monitoring` call sites with persistent ledger writes.
3. Keep old `demo_ledger` reader only for bounded migration fallback.
4. When fallback is used, write `legacy_demo_ledger_used=true` into report/audit metadata.
5. New runtime runs should not write to `.runtime/operations/demo_ledger/`.

No existing demo ledger artifacts are deleted in Phase13 design or early implementation.

## Implementation Order

### Phase13-A: Classification and Guard Rails

- Add code-level constants or helper predicates for Current / History / Derived classification.
- Add architecture tests that fail if Submit reads dated order plan fallback.
- Add tests that `persistent_ledger/state_missing` is not treated as confirmed empty.
- Document `demo_ledger` as legacy in runbook.

Exit criteria:

- Classification table exists in docs and tests.
- No behavior change that can submit orders.

### Phase13-B: Pending Consume Lifecycle

- Implement pending state transition helper.
- Mark pending `SUBMITTING` before submit loop.
- Write submit result metadata into pending.
- Mark `SUBMITTED` then `CONSUMED`.
- Write consumed archive.
- Block terminal pending resubmit.
- Preserve stale `SUBMITTING` fail-closed behavior.

Exit criteria:

- Unit tests cover success, partial item blocks, all-blocked, review-required, stale submitting, terminal resubmit block, and archive path.
- No Production order enabled.

### Phase13-C: Persistent Ledger Ingestion Layer

- Add ingestion helpers from submitted orders, broker orders, broker executions, broker positions, buying power, and fill events.
- Connect Submit to append order records.
- Connect Fill Monitor / Broker ReadOnly path to append execution, position, cash, and lifecycle records.
- Demo fallback projection writes review-required execution/position records.
- Production fallback projection writes event only and returns review-required.

Exit criteria:

- 2026-07-03 equivalent fixture with filled broker orders but missing executions/positions produces Demo current positions with review flag.
- Production fixture does not produce current positions from broker orders fallback.

### Phase13-D: Daily Plan and Approval Read Switch

- Daily Plan holdings, SELL candidates, max positions, and exposure read persistent ledger reader.
- Approval current exposure, cash, and buying power read persistent ledger reader.
- Missing ledger state blocks or review-requires rather than assuming zero holdings.

Exit criteria:

- Empty/missing broker positions no longer erase ledger holdings.
- Missing ledger state cannot create extra BUY capacity.
- Approval no longer uses `demo_ledger` or stale `submitted_orders` as normal exposure source.

### Phase13-E: Report / Notification / Reconcile Read Switch

- Report holdings/cash sections read persistent ledger.
- Notification payload includes current position source and review flags.
- Reconcile includes pending consume status and persistent ledger state.
- `ledger/YYYY-MM-DD` is labeled derived daily broker summary.

Exit criteria:

- Report separates Submit result, execution confirmation, current holdings, and next candidates.
- Report displays Demo fallback as review-required.
- Reconcile can explain pending consumed state.

### Phase13-F: demo_ledger Legacy Cutover

- Stop new mainline writes to `demo_ledger`.
- Keep migration/fallback reader with explicit metadata.
- Update runbook and audit output.

Exit criteria:

- New tests assert normal Submit / Fill Monitor paths write persistent ledger, not demo ledger.
- Existing demo ledger remains readable only as legacy evidence.

### Phase13-G: Acceptance Test Design and Dry Run

Do not restart launchd automation until this phase passes.

Acceptance must prove:

- Pending created after close and approved for next session.
- Morning Submit consumes pending only.
- Dated same-day order plan cannot hijack Submit.
- Persistent ledger holds current positions and cash.
- Demo fallback is review-required.
- Production fallback cannot confirm positions.
- Report / Notification remain SoT-separated.
- POST_SEND_UNKNOWN is not retried.

## Test Matrix

Minimum tests:

- Friday evening pending, Monday morning submit.
- Morning manual plan does not promote pending.
- Missing pending blocks Submit.
- Terminal pending blocks resubmit.
- Stale `SUBMITTING` returns `REVIEW_REQUIRED`.
- Consumed archive is written.
- Pending hash mismatch blocks Submit.
- Ledger missing state is unknown, not confirmed empty.
- Daily Plan blocks or reviews unknown positions.
- Approval exposure uses persistent ledger current positions.
- Demo broker orders fallback writes review-required positions.
- Production broker orders fallback does not write current positions.
- Report separates submitted orders from next order plan.
- Reconcile includes pending and persistent ledger source summaries.
- No raw request, raw response, secrets, or plain broker IDs are written.

## Open Decisions

1. Whether `runtime_state/current.json` should be implemented in Phase13-A or delayed until after pending and ledger are connected.
2. Whether old `demo_ledger` records should be migrated into `persistent_ledger/migrations.jsonl` during Phase13-F or left as read-only evidence.
3. Whether Broker Positions safe diagnosis must reach a successful live read before Demo fallback projection is enabled in mainline, or whether fixture-tested fallback can land behind an explicit Demo-only guard.
4. Whether Approval with zero approved items should remain `APPROVED` history or become `REVIEW_REQUIRED` when no pending exists.

## Non Goals

Phase13 does not include:

- Production order unlock
- launchd auto-operation restart
- AI model changes
- Candidate / Opportunity / Position AI redesign
- Safety investment judgement changes
- replacement policy / portfolio rotation implementation
- full backtest
- artifact deletion

## Completion Criteria

Phase13 can close only when:

- Current / History / Derived classification is encoded in docs and tests.
- Submit cannot use anything except `pending_order_plan`.
- Pending consume lifecycle is complete.
- `persistent_ledger/state.json` is the normal current holdings/cash source.
- Daily Plan / Approval / Report / Notification / Reconcile / Audit state their Current State source.
- `demo_ledger` is legacy-only.
- Demo fallback projection always carries review-required metadata.
- Production never confirms holdings from Broker Orders fallback.
- Broker Positions / Executions diagnostic status is visible.
- Report / Notification do not mix Submit result, execution confirmation, current holdings, and next candidates.
- launchd acceptance test plan passes before automation resumes.
