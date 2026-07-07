# Phase13-G Current State Contract Design

作成日: 2026-07-07

判定: DESIGN_ONLY

## 1. 目的

Runtime v2 が実行時に読む Current State を正式な Contract として固定する。

今回決めるもの:

- Current Object
- `schema_version`
- required fields
- optional fields
- state
- validation
- missing
- stale
- unknown
- confirmed empty
- read contract
- write contract
- owner component
- consumer component
- append policy
- snapshot policy
- version policy

今回は Schema 設計までであり、コード実装は行わない。

## 2. 対象 Current Object

対象 Current Object:

```text
runtime_state/current_state.json
pending_order_plan/pending_order_plan.json
persistent_ledger/state.json
persistent_ledger/orders.jsonl
persistent_ledger/executions.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/cash_history.jsonl
persistent_ledger/events.jsonl
notification_delivery/delivery_ledger.jsonl
```

## 3. Global Current Read Contract

Runtime 全体で Current を読む契約:

- Current は固定 Path から読む。
- History から Current を推測しない。
- Derived から Current を推測しない。
- Current が存在しない場合は Missing。
- Current が古い場合は Stale。
- Current が判定不能なら Unknown。
- Missing は Confirmed Empty ではない。
- Unknown は Empty ではない。
- 日付別 directory を Current 選択元にしない。
- Phase 番号を Current 選択元にしない。

Current read result は、少なくとも以下の flags を返す。

```text
state_missing
state_stale
state_unknown
current_state_confirmed_empty
current_positions_unknown
cash_unknown
buying_power_unknown
review_required
blocked
```

## 4. Global Current Write Contract

Current 更新ルール:

- Current 更新 Component を object ごとに限定する。
- 更新タイミングを state transition と対応させる。
- Snapshot object は atomic write を前提にする。
- JSONL object は append-only を前提にする。
- 同一 record の二重更新は禁止する。
- Dedup key を持つ object は再実行時に duplicate を無視する。
- `schema_version` は破壊的 schema 変更時に更新する。
- `review_required` 付与条件を object ごとに明示する。
- raw request、raw response、secret、session、URL、口座識別子を保存しない。

更新順序の原則:

```text
PendingOrderPlan
↓
SubmitAttempt / LedgerOrderRecord
↓
Broker ReadOnly Evidence
↓
LedgerExecutionRecord
↓
LedgerPositionRecord
↓
LedgerCashRecord
↓
CurrentAssetState
↓
Report / Notification / Audit
```

## 5. Current Object Contract

### 5.1 RuntimeState

| 項目 | Contract |
| --- | --- |
| Object 名 | RuntimeState |
| 保存 Path | `runtime_state/current_state.json` |
| Object 説明 | Runtime State Machine の現在状態 |
| Current 分類理由 | Orchestrator と各 Component が現在の実行状態を判断するため |
| Owner Component | Runtime State Machine Runtime |
| Writer Component | Runtime Orchestrator, Runtime State Machine Runtime, Operation Guard Runtime |
| Reader Component | All Runtime Components |
| Schema Version | `runtime_state_current_v1` |
| Required Fields | `schema_version`, `runtime_id`, `run_id`, `state`, `environment`, `updated_at`, `last_transition`, `review_required`, `blocked`, `halted` |
| Optional Fields | `business_date`, `target_session_date`, `last_completed_component`, `blocked_reason`, `review_required_reason`, `halt_reason`, `current_state_read_ref` |
| Primary Key | `runtime_id` |
| Reference Keys | `run_id`, `business_date`, `target_session_date` |
| State | `IDLE`, `MARKET_DATA_READY`, `FEATURE_READY`, `CURRENT_STATE_LOADED`, `AI_INFERENCE_DONE`, `DAILY_PLAN_CREATED`, `PENDING_PROMOTED`, `APPROVAL_PENDING`, `APPROVED`, `SUBMITTING`, `SUBMITTED`, `POST_SEND_UNKNOWN`, `MONITORING_FILL`, `LEDGER_UPDATED`, `RECONCILED`, `REPORT_READY`, `REVIEW_REQUIRED`, `BLOCKED`, `HALT` |
| Validation Rules | schema version match, required fields present, allowed state, timestamp format, boolean flags type |
| Missing 判定 | file missing, required field missing, schema mismatch |
| Stale 判定 | `updated_at` beyond runtime generation threshold, business_date mismatch when business_date is required |
| Unknown 判定 | state not allowed, transition unknown, missing referenced current object |
| Confirmed Empty 条件 | 該当なし。Runtime state は asset empty を表現しない |
| Append Only | no |
| Snapshot | yes |
| 更新タイミング | state transition ごと |
| 再実行時挙動 | current state を読み、外部副作用済み state では再実行入口を制限 |
| Review Required 条件 | unknown transition, stale SUBMITTING, POST_SEND_UNKNOWN, dependency divergence |
| Production 注意事項 | Production でも state 不明時は HALT / REVIEW_REQUIRED |

### 5.2 PendingOrderPlan

| 項目 | Contract |
| --- | --- |
| Object 名 | PendingOrderPlan |
| 保存 Path | `pending_order_plan/pending_order_plan.json` |
| Object 説明 | Submit 可能性を持つ唯一の Current 注文計画 |
| Current 分類理由 | Submit Runtime が読む唯一の Submit source |
| Owner Component | Planning Runtime / Approval Runtime / Submit Runtime |
| Writer Component | Planning Runtime, Approval Runtime, Submit Runtime |
| Reader Component | Approval Runtime, Submit Runtime, Report Runtime, Audit Runtime, Reconcile Runtime |
| Schema Version | `pending_order_plan_v2` |
| Required Fields | `schema_version`, `pending_plan_id`, `state`, `environment`, `created_at`, `updated_at`, `plan_created_date`, `intended_submit_date`, `target_session_date`, `source_order_plan`, `items`, `promotion`, `raw_request_saved`, `raw_response_saved`, `secret_saved` |
| Optional Fields | `approval`, `approved_item_ids`, `approval_expires_at`, `submit_constraints`, `consume`, `review_required_reason`, `blocked_reason` |
| Primary Key | `pending_plan_id` |
| Reference Keys | `source_order_plan.path`, `source_order_plan.hash`, `approval.id`, `approval.hash`, `target_session_date` |
| State | `PENDING_APPROVAL`, `APPROVED`, `SUBMITTING`, `SUBMITTED`, `CONSUMED`, `EXPIRED`, `BLOCKED`, `REVIEW_REQUIRED` |
| Validation Rules | source hash present, item ids unique, approval linkage valid when approved, dates valid, raw flags false |
| Missing 判定 | file missing when Submit / Approval expects pending, schema mismatch, no pending_plan_id |
| Stale 判定 | approval expired, intended_submit_date stale, target_session_date mismatch |
| Unknown 判定 | unsupported state, approval linkage unreadable, source hash mismatch |
| Confirmed Empty 条件 | No-action pending may be explicit only when `items=[]`, `state=BLOCKED` or explicit no-order state, and current asset state is known. Missing pending is not empty |
| Append Only | no |
| Snapshot | yes |
| 更新タイミング | promotion, approval linkage, submit preflight, submit result, consume |
| 再実行時挙動 | same pending_plan_id and terminal state blocks resubmit. duplicate promotion blocked |
| Review Required 条件 | hash mismatch, stale approved pending, SUBMITTING stale, POST_SEND_UNKNOWN evidence |
| Production 注意事項 | Production Submit disabled until explicit future approval. Production order must not be inferred from history |

### 5.3 CurrentAssetState

| 項目 | Contract |
| --- | --- |
| Object 名 | CurrentAssetState |
| 保存 Path | `persistent_ledger/state.json` |
| Object 説明 | 現在保有、現金、買付余力、総資産の中心 Current snapshot |
| Current 分類理由 | Planning / Approval / Submit / Report / Audit の asset SoT |
| Owner Component | Ledger Runtime / Asset Runtime |
| Writer Component | Ledger Runtime, Asset Runtime |
| Reader Component | Planning Runtime, Approval Runtime, Submit Runtime, Asset Runtime, Reconcile Runtime, Report Runtime, Audit Runtime |
| Schema Version | `persistent_ledger_state_v1` |
| Required Fields | `schema_version`, `asset_state_id`, `environment`, `updated_at`, `positions`, `cash`, `buying_power`, `total_equity`, `market_value`, `sources`, `review_required`, `production_equivalent` |
| Optional Fields | `business_date`, `position_count`, `unrealized_pnl`, `state_status`, `state_missing`, `state_stale`, `state_unknown`, `current_state_confirmed_empty`, `source_summary` |
| Primary Key | `asset_state_id` |
| Reference Keys | `position_key`, `cash_snapshot_key`, `ledger_record_id`, `execution_key` |
| State | `UNKNOWN`, `CONFIRMED_EMPTY`, `CONFIRMED`, `STALE`, `REVIEW_REQUIRED`, `DIVERGED` |
| Validation Rules | positions list type, cash numeric or unknown flag, buying_power numeric or unknown flag, source present, review flags boolean, production_equivalent boolean |
| Missing 判定 | file missing, required asset fields missing, schema mismatch |
| Stale 判定 | updated_at expired, source business_date older than required, broker snapshot stale |
| Unknown 判定 | source unknown, positions cannot be built, cash unknown, migration in progress, broker confirmation unavailable |
| Confirmed Empty 条件 | Broker Positions confirmed empty, Broker Cash confirmed, or approved migration confirmed empty. Missing / stale / unknown never means empty |
| Append Only | no |
| Snapshot | yes, derived from ledger append records |
| 更新タイミング | ledger ingestion, broker readonly ingestion, manual migration apply |
| 再実行時挙動 | deterministic rebuild allowed from ledger records; no duplicate append |
| Review Required 条件 | broker divergence, ledger divergence, unknown source, production_equivalent false in production |
| Production 注意事項 | Production asset confirmation must use Broker Positions / Executions / Cash. Broker Orders fallback prohibited |

### 5.4 LedgerOrderRecord

| 項目 | Contract |
| --- | --- |
| Object 名 | LedgerOrderRecord |
| 保存 Path | `persistent_ledger/orders.jsonl` |
| Object 説明 | 正規化された注文 ledger record |
| Current 分類理由 | Submit 重複防止と注文履歴 Current |
| Owner Component | Ledger Runtime |
| Writer Component | Submit Runtime, Ledger Runtime |
| Reader Component | Submit Runtime, Broker Runtime, Reconcile Runtime, Report Runtime, Audit Runtime |
| Schema Version | `ledger_order_record_v1` |
| Required Fields | `schema_version`, `ledger_record_id`, `recorded_at`, `environment`, `source`, `order_hash`, `review_required`, `production_equivalent` |
| Optional Fields | `pending_plan_id`, `pending_item_id`, `submit_attempt_id`, `submitted_order_id`, `broker_order_ref_hash`, `side`, `symbol`, `quantity`, `status` |
| Primary Key | `ledger_record_id` |
| Reference Keys | `pending_plan_id`, `pending_item_id`, `submit_attempt_id`, `broker_order_ref_hash` |
| State | `APPENDED`, `DEDUPED`, `REVIEW_REQUIRED` |
| Validation Rules | no raw broker id, hash present if broker ref exists, booleans typed, source allowed |
| Missing 判定 | file missing is empty ledger only before first write; missing required field in any record is invalid |
| Stale 判定 | not generally stale; specific submitted order unresolved beyond threshold can create review event |
| Unknown 判定 | order status unknown after submit, source unknown |
| Confirmed Empty 条件 | empty file can mean no ledger order records only when initialized with valid ledger metadata |
| Append Only | yes |
| Snapshot | no |
| 更新タイミング | submit attempt, broker readonly ingestion |
| 再実行時挙動 | dedup by order_hash / pending_item_id / broker_order_ref_hash |
| Review Required 条件 | duplicate conflict, post-send unknown, hash mismatch |
| Production 注意事項 | records do not imply positions or assets |

### 5.5 LedgerExecutionRecord

| 項目 | Contract |
| --- | --- |
| Object 名 | LedgerExecutionRecord |
| 保存 Path | `persistent_ledger/executions.jsonl` |
| Object 説明 | 正規化された約定 record |
| Current 分類理由 | 約定二重反映防止と position / cash 更新根拠 |
| Owner Component | Ledger Runtime |
| Writer Component | Ledger Runtime |
| Reader Component | Asset Runtime, Reconcile Runtime, Report Runtime, Audit Runtime |
| Schema Version | `ledger_execution_record_v1` |
| Required Fields | `schema_version`, `ledger_record_id`, `execution_key`, `recorded_at`, `environment`, `source`, `side`, `symbol`, `quantity`, `price`, `review_required`, `production_equivalent` |
| Optional Fields | `broker_execution_ref_hash`, `broker_order_ref_hash`, `executed_at`, `fees`, `taxes`, `currency` |
| Primary Key | `ledger_record_id` |
| Reference Keys | `execution_key`, `broker_execution_ref_hash`, `broker_order_ref_hash` |
| State | `APPENDED`, `DEDUPED`, `REVIEW_REQUIRED` |
| Validation Rules | execution_key present, quantity positive, price non-negative, source allowed, no raw broker id |
| Missing 判定 | file missing is no execution ledger only before initialization; invalid record blocks ingestion |
| Stale 判定 | broker executions not refreshed for target session may make asset state stale |
| Unknown 判定 | execution source unknown, broker confirmation unavailable |
| Confirmed Empty 条件 | no executions confirmed only when broker execution read succeeded and ledger initialized |
| Append Only | yes |
| Snapshot | no |
| 更新タイミング | Broker Executions ingestion |
| 再実行時挙動 | dedup by execution_key / execution hash |
| Review Required 条件 | duplicate conflict, missing price / qty, source mismatch |
| Production 注意事項 | Production execution records must come from Broker Executions or approved migration |

### 5.6 LedgerPositionRecord

| 項目 | Contract |
| --- | --- |
| Object 名 | LedgerPositionRecord |
| 保存 Path | `persistent_ledger/positions.jsonl` |
| Object 説明 | 正規化された保有 record |
| Current 分類理由 | CurrentAssetState の position source |
| Owner Component | Ledger Runtime |
| Writer Component | Ledger Runtime, Asset Runtime for projection metadata |
| Reader Component | Asset Runtime, Planning Runtime, Approval Runtime, Report Runtime, Audit Runtime |
| Schema Version | `ledger_position_record_v1` |
| Required Fields | `schema_version`, `ledger_record_id`, `position_key`, `recorded_at`, `environment`, `source`, `symbol`, `quantity`, `review_required`, `production_equivalent` |
| Optional Fields | `average_price`, `market_value`, `unrealized_pnl`, `broker_position_snapshot_id`, `execution_key` |
| Primary Key | `ledger_record_id` |
| Reference Keys | `position_key`, `execution_key`, `broker_position_snapshot_id` |
| State | `APPENDED`, `SUPERSEDED`, `REVIEW_REQUIRED` |
| Validation Rules | quantity numeric, symbol present, source allowed, production flags typed |
| Missing 判定 | file missing or invalid required field |
| Stale 判定 | latest position older than business_date / source freshness threshold |
| Unknown 判定 | position source unknown, conflicting broker / ledger position |
| Confirmed Empty 条件 | explicit zero positions from Broker Positions or approved migration, with cash confirmed |
| Append Only | yes |
| Snapshot | latest projection consumed by state snapshot |
| 更新タイミング | Broker Positions ingestion, execution projection, migration apply |
| 再実行時挙動 | dedup by position_key / position hash |
| Review Required 条件 | broker divergence, negative unexpected quantity, production_equivalent false in production |
| Production 注意事項 | Broker Orders fallback prohibited for confirmed holdings |

### 5.7 LedgerCashRecord

| 項目 | Contract |
| --- | --- |
| Object 名 | LedgerCashRecord |
| 保存 Path | `persistent_ledger/cash_history.jsonl` |
| Object 説明 | 正規化された現金 / 買付余力 record |
| Current 分類理由 | CurrentAssetState の cash / buying_power source |
| Owner Component | Ledger Runtime |
| Writer Component | Ledger Runtime |
| Reader Component | Asset Runtime, Planning Runtime, Approval Runtime, Report Runtime, Audit Runtime |
| Schema Version | `ledger_cash_record_v1` |
| Required Fields | `schema_version`, `ledger_record_id`, `cash_snapshot_key`, `recorded_at`, `environment`, `source`, `cash`, `buying_power`, `currency`, `review_required`, `production_equivalent` |
| Optional Fields | `broker_cash_ref_hash`, `settlement_cash`, `reserved_notional`, `source_business_date` |
| Primary Key | `ledger_record_id` |
| Reference Keys | `cash_snapshot_key`, `broker_cash_ref_hash` |
| State | `APPENDED`, `SUPERSEDED`, `REVIEW_REQUIRED` |
| Validation Rules | cash numeric, buying_power numeric, currency present, source allowed |
| Missing 判定 | file missing or required field missing |
| Stale 判定 | cash snapshot older than freshness threshold / business_date mismatch |
| Unknown 判定 | broker cash unavailable, source unknown, migration in progress |
| Confirmed Empty 条件 | cash can be 0 only when Broker Cash or approved migration confirms it |
| Append Only | yes |
| Snapshot | latest projection consumed by state snapshot |
| 更新タイミング | Broker Cash / Buying Power ingestion, migration apply |
| 再実行時挙動 | dedup by cash_snapshot_key / cash hash |
| Review Required 条件 | cash unknown, buying_power unknown, source mismatch |
| Production 注意事項 | Production cash must use Broker Cash / Buying Power or approved migration |

### 5.8 LedgerEventRecord

| 項目 | Contract |
| --- | --- |
| Object 名 | LedgerEventRecord |
| 保存 Path | `persistent_ledger/events.jsonl` |
| Object 説明 | Runtime event, review, divergence, migration event |
| Current 分類理由 | Runtime review / recovery state の Current event stream |
| Owner Component | Ledger Runtime |
| Writer Component | Runtime Orchestrator, Submit Runtime, Fill Runtime, Ledger Runtime, Reconcile Runtime, Audit Runtime, Recovery Runtime |
| Reader Component | Runtime Orchestrator, Recovery Runtime, Report Runtime, Audit Runtime |
| Schema Version | `ledger_event_record_v1` |
| Required Fields | `schema_version`, `event_id`, `recorded_at`, `environment`, `event_type`, `severity`, `review_required` |
| Optional Fields | `run_id`, `runtime_id`, `pending_plan_id`, `ledger_record_id`, `message`, `resolved_at`, `resolution` |
| Primary Key | `event_id` |
| Reference Keys | `run_id`, `pending_plan_id`, `ledger_record_id`, `review_event_id` |
| State | `APPENDED`, `OPEN`, `RESOLVED`, `UNRESOLVED` |
| Validation Rules | event_type allowed, severity allowed, no raw payload, review flag boolean |
| Missing 判定 | file missing before initialization; invalid record blocks audit |
| Stale 判定 | unresolved critical event beyond threshold |
| Unknown 判定 | event type unknown, referenced object missing |
| Confirmed Empty 条件 | no open events only when event ledger initialized and scanned |
| Append Only | yes |
| Snapshot | no |
| 更新タイミング | any review / audit / transition event |
| 再実行時挙動 | dedup by event_id / event hash |
| Review Required 条件 | critical severity, unresolved POST_SEND_UNKNOWN, divergence |
| Production 注意事項 | Production critical event should block Submit |

### 5.9 NotificationDeliveryRecord

| 項目 | Contract |
| --- | --- |
| Object 名 | NotificationDeliveryRecord |
| 保存 Path | `notification_delivery/delivery_ledger.jsonl` |
| Object 説明 | Notification Send の二重送信防止 ledger |
| Current 分類理由 | 外部通知送信の idempotency guard |
| Owner Component | Notification Runtime |
| Writer Component | Notification Runtime |
| Reader Component | Notification Runtime, Audit Runtime, Recovery Runtime |
| Schema Version | `notification_delivery_record_v1` |
| Required Fields | `schema_version`, `delivery_id`, `payload_hash`, `channel`, `target_date`, `recorded_at`, `status`, `retry_allowed`, `review_required` |
| Optional Fields | `sent_at`, `failure_reason`, `post_send_unknown_reason`, `report_id`, `operator` |
| Primary Key | `delivery_id` |
| Reference Keys | `payload_hash`, `channel`, `target_date`, `report_id` |
| State | `PAYLOAD_CREATED`, `READY_TO_SEND`, `SENDING`, `SENT`, `FAILED`, `POST_SEND_UNKNOWN`, `REVIEW_REQUIRED` |
| Validation Rules | payload_hash present, channel allowed, target_date present, retry_allowed boolean |
| Missing 判定 | file missing before notification subsystem initialization |
| Stale 判定 | SENDING beyond threshold, READY_TO_SEND expired |
| Unknown 判定 | send result unknown, delivery state unsupported |
| Confirmed Empty 条件 | no delivery records only when initialized ledger has no matching payload_hash / channel / target_date |
| Append Only | yes |
| Snapshot | no |
| 更新タイミング | payload creation, send attempt, send result, recovery |
| 再実行時挙動 | dedup by payload_hash / channel / target_date |
| Review Required 条件 | POST_SEND_UNKNOWN, duplicate conflict, retry requested without allowed flag |
| Production 注意事項 | Notification Send is external side effect. No duplicate send |

## 6. Current Validation Policy

共通 validation:

- `schema_version` が存在する。
- `schema_version` が expected version と一致する。
- required fields が存在する。
- timestamp fields が ISO-8601 互換である。
- `environment` が `demo` または `production`。
- `source` が許可リスト内。
- `review_required` が boolean。
- `production_equivalent` が boolean。
- hash fields が期待される format。
- business_date / target_session_date が必要な object では整合する。
- raw request / raw response / secret / session / URL / 口座識別子が存在しない。

Validation 失敗時の分類:

| Failure | Runtime behavior |
| --- | --- |
| schema_version missing / mismatch | `BLOCKED` |
| required field missing | `BLOCKED` |
| hash mismatch | `REVIEW_REQUIRED` |
| business_date mismatch | `STALE` |
| environment mismatch | `BLOCKED` or `REVIEW_REQUIRED` |
| source unknown | `REVIEW_REQUIRED` |
| review_required type invalid | `BLOCKED` |
| production_equivalent false in Production asset state | `REVIEW_REQUIRED` |
| timestamp invalid | `BLOCKED` |
| raw secret / raw response detected | `HALT` |

## 7. Missing / Stale / Unknown / Confirmed Empty

### Missing

Missing は以下。

- Current file が存在しない。
- Current 必須項目が欠落している。
- `schema_version` が不一致。
- JSON / JSONL parse ができない。

Missing の場合、Current State を Empty と扱わない。

### Stale

Stale は以下。

- 更新期限切れ。
- business_date 不一致。
- runtime generation 期限超過。
- open state が許容時間を超過。
- Broker ReadOnly source が freshness threshold を超過。

Stale の場合、BUY / Approval / Submit は block または review に寄せる。

### Unknown

Unknown は以下。

- source 不明。
- Current 構築不能。
- Broker 確認不能。
- migration 途中。
- state value が許可リスト外。
- Current dependency が欠落。

Unknown の場合:

```text
BUY 禁止
Approval 禁止
Submit 禁止
Report は state_unknown を明示
```

### Confirmed Empty

Confirmed Empty は以下のみ。

- Broker Positions 確認済。
- Broker Cash 確認済。
- Migration 確認済。
- 保有無し確認済。

禁止:

- Current 無いから Empty。
- Current 古いから Empty。
- Current Unknown だから Empty。

## 8. Current Dependency

Current 同士の依存:

```text
BrokerExecution
↓
LedgerExecutionRecord
↓
LedgerPositionRecord
↓
LedgerCashRecord
↓
CurrentAssetState
↓
Report
```

Current 更新順序:

```text
1. PendingOrderPlan is approved
2. SubmitAttempt starts
3. LedgerOrderRecord is appended
4. Broker ReadOnly evidence is fetched
5. LedgerExecutionRecord is appended
6. LedgerPositionRecord is appended or projected
7. LedgerCashRecord is appended
8. CurrentAssetState snapshot is rebuilt
9. Reconcile / Report / Notification / Audit read CurrentAssetState
```

Dependency rules:

- LedgerExecutionRecord なしに execution-based position を作らない。
- LedgerPositionRecord と LedgerCashRecord が揃わない場合、CurrentAssetState は `UNKNOWN` または `REVIEW_REQUIRED`。
- BrokerOrder は dependency evidence であり、Production asset confirmation dependency ではない。
- Report は CurrentAssetState と review flags を読むが、Report 自身は Current dependency にならない。

## 9. Component Read / Write Responsibility

| Current Object | Writer | Reader | 更新禁止 |
| --- | --- | --- | --- |
| RuntimeState | Runtime Orchestrator, Runtime State Machine Runtime, Operation Guard Runtime | All Runtime Components | Report Runtime, Notification Runtime, AI Execution Runtime |
| PendingOrderPlan | Planning Runtime, Approval Runtime, Submit Runtime | Approval, Submit, Reconcile, Report, Audit | Report Runtime, Notification Runtime, Broker Runtime |
| CurrentAssetState | Ledger Runtime, Asset Runtime | Planning, Approval, Submit, Asset, Reconcile, Report, Audit | Planning Runtime, Approval Runtime, Submit Runtime, Report Runtime, Notification Runtime |
| LedgerOrderRecord | Submit Runtime, Ledger Runtime | Submit, Broker, Reconcile, Report, Audit | Report Runtime, Notification Runtime, Planning Runtime |
| LedgerExecutionRecord | Ledger Runtime | Asset, Reconcile, Report, Audit | Submit Runtime, Report Runtime, Notification Runtime |
| LedgerPositionRecord | Ledger Runtime, Asset Runtime | Asset, Planning, Approval, Report, Audit | Planning Runtime, Approval Runtime, Report Runtime, Notification Runtime |
| LedgerCashRecord | Ledger Runtime | Asset, Planning, Approval, Report, Audit | Planning Runtime, Approval Runtime, Report Runtime, Notification Runtime |
| LedgerEventRecord | Runtime Orchestrator, Submit, Fill, Ledger, Reconcile, Audit, Recovery | Orchestrator, Recovery, Report, Audit | Notification Runtime except delivery events |
| NotificationDeliveryRecord | Notification Runtime | Notification, Audit, Recovery | Report Runtime, Planning Runtime, Submit Runtime |

## 10. Contract 違反時の Runtime 挙動

| Contract violation | Runtime behavior |
| --- | --- |
| schema 違反 | `BLOCKED` |
| hash 不一致 | `REVIEW_REQUIRED` |
| business_date 不一致 | `STALE` |
| Current 欠損 | `REVIEW_REQUIRED` |
| Current Unknown | BUY 禁止、Approval 禁止、Submit 禁止 |
| raw secret / raw response 保存検知 | `HALT` |
| BrokerOrder を Production asset SoT にしようとした | `BLOCKED` |
| Report を Current 入力にしようとした | `BLOCKED` |
| Notification duplicate delivery | `BLOCKED` or `REVIEW_REQUIRED` |
| append-only record duplicate exact match | duplicate ignored |
| append-only record duplicate conflict | `REVIEW_REQUIRED` |

## 11. Architecture Test 対象

Phase13-G ではテストは作らない。Current Contract で必要になる Architecture Test 対象だけ整理する。

- Current Fixed Path Test
- No Date Resolver Test
- No Phase Resolver Test
- Schema Validation Test
- Required Field Test
- Unknown Test
- Missing Test
- Stale Test
- Confirmed Empty Test
- Read Contract Test
- Write Contract Test
- Current Dependency Test
- Writer Restriction Test
- Production Broker Orders Fallback Prohibition Test
- Report Not Current Input Test
- Notification Delivery Dedup Contract Test
- Raw Secret / Raw Response Prohibition Test

## 12. Runtime Design との整合確認

- Runtime Data Model と矛盾しない。
- Runtime Component Architecture と矛盾しない。
- Runtime State Machine と矛盾しない。
- Pending Lifecycle と矛盾しない。
- Report Runtime と矛盾しない。
- Current / History / Derived 分類と矛盾しない。
- 注文・約定・保有・資産分離と矛盾しない。
- Production で Broker Orders fallback を保有確定に使わない原則と矛盾しない。

## 13. 禁止事項

Phase13-G では以下を禁止する。

- 実装変更
- Submit
- Broker 注文
- Demo 注文
- Production 注文
- 通知送信
- `launchd` 再開
- 既存 plist 削除
- 新規 plist 作成
- artifact 削除
- AI 再学習
- フルバックテスト

## 14. 完了条件

- Current Object 全ての Contract が定義されている。
- Read Contract が定義されている。
- Write Contract が定義されている。
- Missing / Stale / Unknown / Confirmed Empty が定義されている。
- Validation Policy が定義されている。
- Current Dependency が定義されている。
- Component との Read / Write 責務が定義されている。
- Architecture Test 対象が整理されている。
- 実装変更は一切行われていない。

