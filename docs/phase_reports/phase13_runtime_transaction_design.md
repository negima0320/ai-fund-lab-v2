# Phase13-H Runtime Transaction Design

作成日: 2026-07-07

判定: DESIGN_ONLY

## 1. 目的

Runtime は複数の Current State を更新する。

そのため、以下を定義する。

- どこまでを 1 回の更新単位とするか
- どこで Commit するか
- 途中失敗したらどこから再開するか
- Current が壊れないこと

Runtime v2 では Transaction Boundary を正式に定義する。

今回は Runtime Transaction Design のみであり、コード実装、Submit、Broker 注文、Demo / Production 注文、通知送信、`launchd` 再開、既存 plist 削除、新規 plist 作成は行わない。

## 2. Transaction 設計対象

各 Transaction について以下を定義する。

- Transaction 一覧
- Transaction 開始条件
- Transaction 終了条件
- Commit 条件
- Rollback 方針
- Recovery 開始位置
- Review Required 条件
- 副作用の境界
- Current 更新順序
- 再実行可否

## 3. Runtime Transaction 一覧

| ID | Transaction | Flow | Current 更新 | 副作用 | 再実行可否 | 重要原則 |
| --- | --- | --- | --- | --- | --- | --- |
| A | Market Refresh | Market Refresh -> Feature Refresh -> Commit | なし | 外部 data read | 可 | Current を書き換えない |
| B | AI Planning | Current Read -> AI Execution -> Planning -> Pending Promotion -> Commit | `pending_order_plan` | なし | 条件付き | pending promotion は重複防止 |
| C | Approval | Pending Read -> Approval -> Pending Update -> Commit | `pending_order_plan` | なし | 可 | approval artifact は History / Evidence |
| D | Submit | Pending Read -> Submit Attempt -> Broker Submit -> Orders Ledger -> Pending Update -> Commit | `persistent_ledger/orders.jsonl`, `pending_order_plan`, `events.jsonl` | Broker Order Submit | 不可 | 最重要。非冪等。再送禁止 |
| E | Execution Reflection | Broker ReadOnly -> Execution -> LedgerExecution -> LedgerPosition -> LedgerCash -> CurrentAsset -> Commit | `executions.jsonl`, `positions.jsonl`, `cash_history.jsonl`, `state.json`, `events.jsonl` | Broker ReadOnly | 条件付き | CurrentAsset は ledger 更新が揃ってから |
| F | Reconcile | Current Read -> Reconcile -> Review Event -> Commit | `events.jsonl` | なし | 可 | divergence を Review Required へ |
| G | Report | Current Read -> Report -> Notification Payload -> Commit | なし | なし | 可 | Derived のみ |
| H | Notification | Payload Read -> Delivery Ledger -> Notification Send -> Delivery Update -> Commit | `notification_delivery/delivery_ledger.jsonl` | External notification send | 非冪等 | Delivery Ledger で二重送信防止 |
| I | Audit | Current Read -> Audit -> Audit Result -> Commit | 必要時 `events.jsonl` | なし | 可 | Audit result を Submit source にしない |
| J | Recovery | Review Event -> Broker ReadOnly -> Ledger Repair -> Current Repair -> Commit | ledger records, `state.json`, `events.jsonl` | Broker ReadOnly, manual migration apply if approved | 条件付き | 自動再 Submit しない |

## 4. Transaction Boundary

| Transaction | 開始条件 | 終了条件 | Current 更新対象 | History 更新対象 | Derived 更新対象 | Commit 条件 | 副作用有無 | 再実行可否 | Recovery 開始位置 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A Market Refresh | business_date / market source が決まっている | market / feature artifacts 生成完了 | なし | market refresh, feature artifacts | refresh summary | artifacts と manifest が整合 | 外部 read | 可 | Market Refresh から再実行 |
| B AI Planning | Current Read が `READ_OK` または review-safe、features ready | pending promotion candidate 生成 | `pending_order_plan` | AI inference, daily_plan, order_plan | planning summary | source hashes と pending_plan_id が確定 | なし | 条件付き | Current Read から再実行 |
| C Approval | pending が `PENDING_APPROVAL`、approval policy 有効 | approval linkage 更新 | `pending_order_plan` | approval_request, approval_artifact | approval summary | approval hash / source hash / approved ids が一致 | なし | 可 | Pending Read から再実行 |
| D Submit | pending が `APPROVED`、preflight / guard pass | order ledger と pending state が commit | orders ledger, pending state, events | submitted_orders | submit summary | Broker submit result または POST_SEND_UNKNOWN event が記録される | Broker Order Submit | 不可 | Broker ReadOnly から。再 Submit しない |
| E Execution Reflection | submitted order または Broker ReadOnly request がある | CurrentAssetState commit | executions, positions, cash, state, events | broker read evidence, fill evidence | execution summary | LedgerExecution / LedgerPosition / LedgerCash が dedup 済みで state rebuild 成功 | Broker ReadOnly | 条件付き | LedgerRuntime 再実行。dedup 後 CurrentAsset 更新 |
| F Reconcile | CurrentAssetState が存在し、broker / ledger evidence が読める | reconciliation result / review event | events | reconciliation_result | reconcile summary | divergence 判定が保存される | なし | 可 | Current Read から再実行 |
| G Report | Current commit 後、report inputs が読める | report / payload 生成 | なし | report refs | reports, notification payload | report が CurrentAssetState と review flags を表示 | なし | 可 | Report generation から再実行 |
| H Notification | payload ready、delivery ledger readable | delivery update commit | delivery ledger | notification result | sent summary | pre-send delivery record と post-send result が記録される | Notification Send | 非冪等 | Delivery Ledger 確認から。二重送信しない |
| I Audit | Current / History / Derived が読める | audit result / event commit | 必要時 events | audit_result | audit summary | findings と review_required が保存される | なし | 可 | Audit から再実行 |
| J Recovery | review event open | recovery action / repair commit | ledger records, state, events | recovery record, migration record | recovery summary | resolved / unresolved status が記録される | 条件付き | 条件付き | review event から再開 |

## 5. Commit Rule

Runtime 全体の Commit Rule:

- Current は途中更新しない。
- Commit 時のみ Current へ反映する。
- Snapshot Current は atomic write で置き換える。
- JSONL Current は append-only で追記する。
- Commit 前の work-in-progress は History / Evidence または transaction-local artifact に閉じ込める。
- CurrentAssetState は LedgerExecution、LedgerPosition、LedgerCash が揃ってから更新する。
- Report は Current Commit 後のみ生成する。
- Notification は Report Commit 後のみ送信できる。
- Contract validation に失敗した Current は Commit しない。
- Commit 成功後は transaction record / event を残す。

Commit ordering:

```text
LedgerExecution
↓
LedgerPosition
↓
LedgerCash
↓
CurrentAsset
↓
Report
↓
Notification
```

禁止:

- CurrentAsset 先更新
- Report 先生成
- Notification 先送信
- History artifact から Current を復元して Commit
- Derived artifact を Current として Commit

## 6. Rollback 方針

Runtime v2 では Database Rollback ではなく Recovery を基本とする。

方針:

- 途中更新を戻さない。
- append-only を基本とする。
- 補正 event を書く。
- Recovery event を書く。
- Review Required を書く。
- raw request / raw response / secret は保存しない。
- 破壊的削除で整合性を戻さない。

Rollback ではなく Recovery を選ぶ理由:

- Broker Submit や Notification Send は外部副作用であり、ローカル rollback できない。
- JSONL ledger は append-only で監査可能性を保つ。
- 誤りは correction / migration / review event で補正する。

## 7. Recovery Point

| Transaction | Failure point | Recovery start | Recovery rule |
| --- | --- | --- | --- |
| A Market Refresh | market fetch failed | Market Refresh | 再実行可能。Current は未更新 |
| B AI Planning | AI / planning failed before promotion | Current Read | 再実行可能。pending 未更新なら promotion しない |
| B AI Planning | pending promotion conflict | Pending validation | existing pending を上書きせず REVIEW_REQUIRED |
| C Approval | approval artifact mismatch | Pending Read | approval linkage を更新せず REVIEW_REQUIRED |
| D Submit | preflight failed before Broker Submit | Pending Read | Broker API 未呼び出しなら BLOCKED |
| D Submit | Broker Submit 中に失敗 | Broker ReadOnly | Submit 再送しない。POST_SEND_UNKNOWN / REVIEW_REQUIRED |
| D Submit | order ledger written, pending update failed | Current State Runtime | ledger を削除せず pending を review / consume 補正 |
| E Execution Reflection | LedgerExecution 更新済、LedgerPosition 未更新 | LedgerRuntime 再実行 | dedup して position / cash / state を続行 |
| E Execution Reflection | position 更新済、cash 未更新 | LedgerRuntime 再実行 | dedup して cash / state を続行。CurrentAsset は未確定 |
| E Execution Reflection | state rebuild failed | Asset Runtime | ledger records から state rebuild。失敗なら REVIEW_REQUIRED |
| F Reconcile | divergence detected | Recovery / Review | divergence event を開く |
| G Report | report generation failed | Report Runtime | Current は変更しない。再生成可能 |
| H Notification | send before result unknown | Delivery Ledger | POST_SEND_UNKNOWN。自動再送しない |
| I Audit | audit failed | Audit Runtime | Current は変更しない。review event only |
| J Recovery | repair proposal failed | Review Event | unresolved のまま残す |

## 8. Atomic Update Rule

Atomic update の最小単位:

- Snapshot Current: temp artifact / validation / atomic replace。
- JSONL Current: single append record / fsync equivalent policy / dedup key。
- Multi-object transaction: dependency order を守り、最後に state / event を commit。

Execution Reflection の atomic sequence:

```text
1. Broker ReadOnly evidence acquired
2. LedgerExecution append
3. LedgerPosition append / projection
4. LedgerCash append
5. CurrentAssetState rebuild
6. LedgerEvent commit
7. Reconcile / Report allowed
```

Atomicity の注意:

- CurrentAssetState は LedgerExecution / LedgerPosition / LedgerCash の一部だけを反映してはならない。
- Report は CurrentAssetState の commit 前に生成してはならない。
- Notification Send は Delivery Ledger の pre-send guard なしに実行してはならない。

## 9. Runtime Restart Rule

途中停止後の再開手順:

```text
Current State
↓
Runtime State
↓
Transaction 判定
↓
途中 Transaction 再実行
↓
Dedup
↓
Commit
```

重要原則:

- 途中 Transaction だけ再開する。
- 全部最初からやり直さない。
- 外部副作用済み Transaction は再送しない。
- Broker Submit 後の不明状態は Broker ReadOnly から再開する。
- Ledger append 済み record は dedup して続行する。
- Report / Audit は Current commit 後なら再生成できる。
- Notification は Delivery Ledger から再開し、二重送信しない。

Restart 判定に使う Current:

- `runtime_state/current_state.json`
- `pending_order_plan/pending_order_plan.json`
- `persistent_ledger/orders.jsonl`
- `persistent_ledger/events.jsonl`
- `notification_delivery/delivery_ledger.jsonl`

## 10. Transaction と State Machine 対応

| Transaction | State Machine states |
| --- | --- |
| A Market Refresh | `IDLE` -> `MARKET_DATA_READY` -> `FEATURE_READY` |
| B AI Planning | `CURRENT_STATE_LOADED` -> `AI_INFERENCE_DONE` -> `DAILY_PLAN_CREATED` -> `PENDING_PROMOTED` |
| C Approval | `APPROVAL_PENDING` -> `APPROVED` or `REVIEW_REQUIRED` |
| D Submit | `APPROVED` -> `SUBMITTING` -> `SUBMITTED` or `POST_SEND_UNKNOWN` / `REVIEW_REQUIRED` |
| E Execution Reflection | `MONITORING_FILL` -> `LEDGER_UPDATED` |
| F Reconcile | `LEDGER_UPDATED` -> `RECONCILED` or `REVIEW_REQUIRED` |
| G Report | `RECONCILED` -> `REPORT_READY` |
| H Notification | `REPORT_READY` -> notification delivery state, no core state advancement required |
| I Audit | any committed state -> `REVIEW_REQUIRED` if findings |
| J Recovery | `REVIEW_REQUIRED` / `POST_SEND_UNKNOWN` / `BLOCKED` -> resolved state or `HALT` |

## 11. Current Contract との整合

確認:

- Transaction が Current Contract を破らない。
- Current 更新順序が Current Dependency と一致する。
- Current Reader が途中 Current を読まない。
- Commit 後だけ Current を読む。
- Missing / Stale / Unknown / Confirmed Empty の定義と矛盾しない。
- BrokerOrder を Production asset SoT にしない。
- Report / Notification を Current 入力にしない。
- append-only ledger は correction event で回復する。

## 12. Architecture Test 対象

Phase13-H ではテストは作らない。Transaction Design で必要になる Architecture Test 対象だけ整理する。

- Transaction Boundary Test
- Commit Order Test
- Recovery Test
- Atomic Update Test
- Restart Test
- No Partial Current Test
- Dedup Test
- Submit Transaction Test
- Execution Transaction Test
- Notification Transaction Test
- CurrentAsset After Ledger Complete Test
- Report After Current Commit Test
- Notification After Delivery Guard Test

## 13. 禁止事項

Phase13-H では以下を禁止する。

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

- Runtime Transaction 一覧が定義されている。
- Transaction Boundary が定義されている。
- Commit Rule が定義されている。
- Recovery Rule が定義されている。
- Restart Rule が定義されている。
- Atomic Update Rule が定義されている。
- Current Contract との整合が確認されている。
- Architecture Test 対象が整理されている。
- 実装変更は一切行われていない。

