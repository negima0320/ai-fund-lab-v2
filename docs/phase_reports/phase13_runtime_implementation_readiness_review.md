# Phase13-J Runtime v2 Implementation Readiness Review

作成日: 2026-07-07

判定: DESIGN_REVIEW

## 1. 目的

Runtime v2 を実装する前に、以下が無いか確認する。

- 設計漏れ
- 責務重複
- 矛盾
- 循環依存
- Current State 不足
- Component 不足
- Data Model 不足
- Transaction 不足
- Recovery 不足

Phase13-J は Implementation Readiness Review のみである。実装変更、Submit、Broker 注文、Demo / Production 注文、通知送信、`launchd` 再開、既存 plist 削除、新規 plist 作成、Backtest / Simulation 実行は行わない。

## 2. レビュー対象

| Area | Artifact | Review status |
| --- | --- | --- |
| Runtime Architecture | `docs/02_architecture/runtime_architecture_v2.md` | REVIEWED |
| Runtime Component Architecture | `docs/02_architecture/runtime_architecture_v2.md` Section 8 | REVIEWED |
| Implementation / Migration Plan | `docs/phase_reports/phase13_runtime_v2_implementation_migration_plan.md` | REVIEWED |
| Runtime Data Model | `docs/phase_reports/phase13_runtime_data_model_design.md` | REVIEWED |
| Current State Contract | `docs/phase_reports/phase13_current_state_contract_design.md` | REVIEWED |
| Runtime Transaction Design | `docs/phase_reports/phase13_runtime_transaction_design.md` | REVIEWED |
| Simulation / Backtest Compatibility Design | `docs/phase_reports/phase13_simulation_backtest_compatibility_design.md` | REVIEWED |

## 3. AI と Runtime 責務レビュー

| Check | Result | Notes |
| --- | --- | --- |
| AI が Runtime 責務を持っていないか | PASS | AI は判断結果を返す。Runtime state / Submit / Ledger / Report は Runtime 側責務 |
| Runtime が AI 判断を持っていないか | PASS | Candidate / Opportunity / Position / Capital Allocation / Safety logic は Runtime に再実装しない設計 |
| 責務が混在していないか | PASS | AI Execution Runtime は AI 呼び出しと結果受領に限定 |

結論: AI と Runtime の責務分離は実装可能な粒度で整理されている。

## 4. Component レビュー

| Check | Result | Notes |
| --- | --- | --- |
| 各 Component が単一責務になっているか | PASS | Orchestrator, Current State, Planning, Approval, Submit, Broker, Fill, Ledger, Asset, Report などに分離済み |
| 役割重複 | MINOR | Ledger Runtime と Asset Runtime の state rebuild 責務境界は実装時に module interface を明確化する必要あり |
| 責務不足 | PASS | Core runtime, guard, migration, recovery, audit まで定義済み |
| 循環依存 | PASS | Report / Audit / Recovery は横断参照するが Current 更新 owner ではない |
| 不要 Component | PASS | Optional components は optional と明記済み |
| 不足 Component | MINOR | Clock / Calendar は Simulation 設計で明示されたが Production Runtime Component 表では補助 Component として後続で具体化するとよい |
| Current Reader / Writer | PASS | Current Contract で reader / writer / 更新禁止が整理済み |
| 副作用 | PASS | Broker Submit は Submit Runtime、Notification Send は Notification Runtime に限定 |
| 再実行可否 | PASS | Transaction Design で可 / 非冪等 / 条件付きに分類済み |

結論: Component Architecture は実装可能。軽微な interface 明確化は Phase13-K 以降で扱えばよい。

## 5. Data Model レビュー

| Object group | Result | Notes |
| --- | --- | --- |
| Order | PASS | OrderPlan, PendingOrderPlan, SubmitAttempt, SubmittedOrder, BrokerOrder, LedgerOrderRecord が分離済み |
| Execution | PASS | BrokerExecution, ExecutionEvent, FillClassification, LedgerExecutionRecord が分離済み |
| Position | PASS | BrokerPosition, LedgerPositionRecord, CurrentAssetState が分離済み |
| Asset | PASS | CurrentAssetState が asset SoT として定義済み |
| Pending | PASS | Pending lifecycle と keys が定義済み |
| Approval | PASS | ApprovalRequest / ApprovalArtifact / pending linkage が分離済み |
| Report | PASS | ReportArtifact は Derived として定義済み |
| Notification | PASS | NotificationPayload と NotificationDeliveryRecord が分離済み |
| Review | PASS | ReviewRequiredEvent / RecoveryAction が定義済み |
| Migration | PASS | MigrationRecord が定義済み |
| Key 不足 | MINOR | account scope / broker account hash の扱いは schema 実装時に required / prohibited fields と合わせて確定が必要 |
| Lifecycle 不足 | PASS | Pending, Submit, BrokerOrder, Fill, Asset, Notification lifecycle が定義済み |

結論: Data Model は実装開始可能な粒度。account scope などの細部は schema 実装時の軽微課題。

## 6. Current State レビュー

| Check | Result | Notes |
| --- | --- | --- |
| Current 固定 Path | PASS | 9 Current Object が固定 Path で定義済み |
| Read Contract | PASS | History / Derived から推測しない方針あり |
| Write Contract | PASS | writer / reader / 更新禁止を整理済み |
| Validation | PASS | schema, required fields, hash, environment, source, timestamp など定義済み |
| Missing / Stale / Unknown | PASS | Missing / Stale / Unknown / Confirmed Empty が統一定義済み |
| Owner / Reader / Writer | PASS | Contract table で整理済み |
| History から Current 推測しない | PASS | 複数設計書で禁止明記 |
| Derived から Current 推測しない | PASS | Report / Notification は Current 入力禁止 |
| Current 更新順序 | PASS | Transaction Design と Current Dependency が一致 |

結論: Current State 設計は矛盾なし。実装時には schema validator と architecture tests が必須。

## 7. Transaction レビュー

| Check | Result | Notes |
| --- | --- | --- |
| Transaction Boundary | PASS | A-Market Refresh から J-Recovery まで定義済み |
| Commit | PASS | Current は commit 時のみ反映、CurrentAsset は ledger 完了後 |
| Recovery | PASS | rollback ではなく correction / recovery event 方針 |
| Restart | PASS | Current / Runtime State / Transaction 判定 / Dedup / Commit |
| Atomic Update | PASS | LedgerExecution -> LedgerPosition -> LedgerCash -> CurrentAsset |
| Dedup | PASS | execution_key, payload_hash, order hash など key 方針あり |
| 途中 Current が見えないか | PASS | Current は途中更新しない方針 |
| Report 先生成にならないか | PASS | Report は Current commit 後 |
| Notification 先送信にならないか | PASS | Notification は Report commit と Delivery Ledger 後 |

結論: Transaction 設計は Current Contract と整合している。

## 8. Recovery レビュー

| Failure / state | Result | Recovery design |
| --- | --- | --- |
| `POST_SEND_UNKNOWN` | PASS | Broker ReadOnly へ進み、自動再 Submit しない |
| `BROKER_DIVERGENCE` | PASS | Reconcile / Recovery / Review event |
| `LEDGER_DIVERGENCE` | PASS | Correction event / migration proposal |
| Current Unknown | PASS | BUY / Approval / Submit 禁止、Report は state_unknown |
| Current Missing | PASS | REVIEW_REQUIRED / BLOCKED。Empty 扱い禁止 |
| Current Stale | PASS | STALE / REVIEW_REQUIRED。Submit 禁止 |

結論: Recovery 方針は実装可能。POST_SEND_UNKNOWN の runbook は実装フェーズで具体化が必要。

## 9. Runtime Mode レビュー

| Mode | Separation review | Result |
| --- | --- | --- |
| production | real broker / production current / production report | PASS |
| demo | demo broker / demo current / production order prohibited | PASS |
| simulation | simulated broker / simulation current | PASS |
| backtest | simulation clock / simulated broker / backtest current | PASS |

混線レビュー:

- Current: mode root 分離案により混線防止可能。
- Storage: `.runtime/{mode}/...` 優先案で明確。
- Report: mode metadata と not_for_trading 表示で分離可能。
- Audit: production audit と backtest audit は分離。
- Notification: Backtest は原則 payload generation まで。
- Broker: Simulation Broker Adapter は実 Broker 接続を持たない。

結論: Runtime Mode 分離は成立している。

## 10. Storage レビュー

| Storage class | Result | Notes |
| --- | --- | --- |
| Current | PASS | fixed path, mode root separation |
| History | PASS | date-based path allowed, Current 推測禁止 |
| Evidence | PASS | audit / reconcile / broker evidence として保持 |
| Derived | PASS | Report / Notification payload は Current 入力禁止 |
| Simulation | PASS | `.runtime/simulation/` 分離案 |
| Backtest | PASS | `.runtime/backtest/` 分離案 |

結論: Storage 分離は成立。実装時は path resolver に mode explicit requirement を入れること。

## 11. Production 安全性レビュー

| Check | Result | Notes |
| --- | --- | --- |
| Production Current に Simulation が混ざらないか | PASS | Storage 分離と metadata 必須 |
| Production Broker に Backtest が混ざらないか | PASS | Simulated Broker Adapter は実 Broker 接続禁止 |
| Production Report に Backtest が混ざらないか | PASS | mode=backtest / not_for_trading 表示 |
| Production Notification に Backtest が混ざらないか | PASS | Backtest notification は原則 send しない |
| Demo が Production に混ざらないか | PASS | environment / production_equivalent metadata |
| Production Broker Orders fallback | PASS | 保有確定 SoT として禁止 |

結論: Production 安全性は設計上確保されている。

## 12. Migration レビュー

| Target | Result | Notes |
| --- | --- | --- |
| legacy runtime | PASS | v2 正規フローとして継承しない |
| `demo_ledger` | PASS | 削除ではなく legacy isolation |
| `launchd` | PASS | Acceptance / Manual Rehearsal まで再開禁止 |
| plist | PASS | 既存 plist は継承せず、legacy 保持不要。ただし Phase13-E では削除 / 新規作成禁止 |
| History artifact | PASS | History / Evidence として保持。Current 推測禁止 |

結論: Migration 方針は安全。破壊的 cleanup を後回しにしている点も妥当。

## 13. Implementation 順序レビュー

指定順序:

```text
Current Contract
↓
State Machine
↓
Ledger
↓
Pending
↓
Broker
↓
Report
↓
Notification
↓
Acceptance Test
```

レビュー:

| Step | Result | Notes |
| --- | --- | --- |
| Current Contract | PASS | 最初に固定すべき。妥当 |
| State Machine | PASS | Current Contract 後に skeleton 実装が妥当 |
| Ledger | PASS | Asset / Report の前提 |
| Pending | PASS | Submit source の lifecycle 完成が必要 |
| Broker | PASS | ReadOnly ingestion から始めるべき |
| Report | PASS | Current commit 後に再配線 |
| Notification | PASS | Report / Delivery Ledger 後 |
| Acceptance Test | PASS | launchd 再開前に必須 |

結論: 実装順序は妥当。Broker は必ず ReadOnly ingestion から始め、Submit は最後まで禁止を維持する。

## 14. 未解決事項一覧

### Must Resolve Before Implementation

- Current State schema validator の配置方針。
- Runtime v2 path resolver が mode / environment を明示必須にする方針。
- Current Contract architecture tests のファイル配置。
- Existing runtime entrypoint を v2 実装から誤って呼ばないための isolation plan。

### Can Resolve During Implementation

- Ledger Runtime と Asset Runtime の module interface 境界。
- account scope / account hash の field policy。
- RuntimeState transition history の保存粒度。
- Recovery event の severity taxonomy。
- Broker ReadOnly ingestion の adapter interface 詳細。

### Future Enhancement

- Intraday / event-driven Simulation Clock。
- Advanced simulated fill models such as volume constrained partial fill.
- Corporate action simulation.
- Performance analytics for backtest reports.

### Out of Scope

- AI 再学習。
- Full backtest execution。
- Production order enablement。
- Existing plist deletion / new plist creation。
- Launchd restart。

## 15. Go / No-Go 判定

判定: `GO_WITH_MINOR_FIXES`

理由:

- Runtime Architecture、Component、Data Model、Current State Contract、Transaction、Simulation / Backtest compatibility は相互に矛盾していない。
- Production 安全性、Current / History / Derived 分離、注文 / 約定 / 保有 / 資産分離は一貫している。
- 実装順序も妥当であり、Current Contract から進める準備がある。
- 重大な設計課題は見つからない。
- ただし、実装直前に path resolver、schema validator 配置、legacy entrypoint isolation、Ledger / Asset module interface の軽微な設計補足が必要。

## 16. 修正提案

### 重大

なし。

### 中

なし。

### 軽微

- Phase13-K または実装開始前に、Current State schema validator の module placement を決める。
- Runtime v2 path resolver は `mode` / `environment` 明示なしでは動かない contract にする。
- Ledger Runtime と Asset Runtime の interface を小さな ADR または implementation note に落とす。
- legacy runtime entrypoint isolation list を作る。
- account scope / account hash の保存可否と hash policy を schema 実装時に確定する。

## 17. Acceptance Criteria

- 設計全体レビューが完了している。
- 責務重複が無い。
- Current State 設計が矛盾していない。
- Transaction 設計が矛盾していない。
- Runtime Mode 分離が成立している。
- Storage 分離が成立している。
- Production 安全性が確認されている。
- Migration 方針が確認されている。
- Go / No-Go 判定が行われている。

## 18. 禁止事項

Phase13-J では以下を禁止する。

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
- Backtest 実行
- Simulation 実行

## 19. 完了条件

- Runtime v2 設計全体レビューが完了している。
- 未解決事項が整理されている。
- Go / No-Go 判定が出ている。
- 重大な設計課題があれば一覧化されている。
- 実装開始可否が判断されている。
- 実装変更は一切行われていない。

