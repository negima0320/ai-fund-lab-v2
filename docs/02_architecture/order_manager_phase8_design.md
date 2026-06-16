# AI Fund Lab vNext Phase8 Order Manager Design

---

# 1. このドキュメントの目的

本ドキュメントは、Phase8 Order Manager の設計を定義する。

重要:

```text
Phase8は実売買ではない
Phase8はread-only sync + paper trading + order plan + human review gateまで
Phase8ではlive order / auto order / 実発注を実装しない
```

Phase8のBroker前提は以下へ変更する。

```text
moomoo証券
moomoo OpenAPI
OpenD
```

---

# 2. Phase8の位置付け

`phase_roadmap.md` ではPhase8は `Order Manager` とされ、発注、売却、取消、約定確認が対象とされている。

ただし、Phase7引き継ぎでは以下が明確に指定されている。

```text
Read-only first
Paper next
Order plan only
Human review required
No live order
```

そのためPhase8では、Order Managerを以下に読み替える。

```text
実注文を出す管理器ではなく、
AI / Capital Allocationの結果を実Broker snapshotと突合し、
人間確認用の売買planを作り、
paper tradingに反映するplan manager
```

---

# 3. 入力

Order Manager Phase8は、以下を入力にする。

```text
Candidate AI output
Opportunity AI output
Position Management AI output
Capital Allocation decision
Broker snapshot
BrokerSyncResult
PortfolioState
SafetyReport
OperationGuard lock state
Paper ledger
market data / latest close / liquidity indicators
```

Phase8主policy:

```text
Primary:
  CAP5

Shadow:
  CAP4
  POLICY_Y_CAP4_EDGE08_CONF5

Reference:
  A_FIXED_20BD
  C3_MIN15_T2
```

---

# 4. 出力

Phase8で出力するもの。

```text
OrderPlan
OrderPlanItem
OrderPlanReviewReport
PaperTradeInstruction
PaperLedgerUpdate
BrokerSnapshotDiff
SafetyGateDecision
HumanReviewPackage
AuditRecord
```

出力先:

```text
.runtime/order_manager/plans/
.runtime/order_manager/review/
.runtime/order_manager/audit/
.runtime/order_manager/paper/
.runtime/order_manager/reconciliation/
reports/phase_reports/
```

OrderPlanは実注文ではない。必ず以下を含める。

```text
executable = false
live_order_allowed = false
requires_human_review = true
broker = moomoo
source = phase8_order_plan
```

---

# 5. Order Managerの責務

Phase8のOrder Managerは以下を行う。

```text
Candidate AI / Opportunity AI / Position Management AI / Capital Allocation の結果を受け取る
実口座snapshotと突合する
buy / sell / hold のorder planを生成する
paper tradingに反映する
human review用のplanを出力する
Safety Guardのlock stateを確認する
SELL_FIRST_BUY_AFTER_FILLを状態として管理する
監査用recordを保存する
```

Phase8のOrder Managerが行わないこと。

```text
実発注
自動発注
注文送信
注文訂正
注文取消
trade unlock
OpenD login/logout自動化
secret保存
PortfolioStateの勝手な正化
Broker snapshotを無視した買付
売却約定前の買付
```

---

# 6. OrderPlan schema案

最小schema案。

```text
OrderPlan:
  plan_id
  created_at
  broker
  broker_snapshot_id
  paper_ledger_id
  policy_id
  safety_status
  lock_state
  executable
  live_order_allowed
  requires_human_review
  plan_status
  items
  blocked_reasons
  warnings
  audit_refs
```

```text
OrderPlanItem:
  item_id
  issue_code
  issue_name
  side
  action
  quantity
  lot_size
  estimated_price
  estimated_value
  source_decision_id
  reason_code
  cash_required
  sell_first_group_id
  depends_on_fill_item_id
  broker_position_quantity
  paper_position_quantity
  status
  executable
  review_required
```

`side` 候補:

```text
BUY
SELL
HOLD
NOOP
```

`action` 候補:

```text
NEW_BUY_PLAN
SELL_PLAN
REPLACE_SELL_PLAN
REPLACE_BUY_AFTER_FILL_PLAN
HOLD_PLAN
EMERGENCY_EXIT_PLAN
DEFENSIVE_HOLD_PLAN
BLOCKED_BY_SAFETY
BLOCKED_BY_CASH
BLOCKED_BY_BROKER_MISMATCH
```

---

# 7. SELL_FIRST_BUY_AFTER_FILL

Phase7からの必須制約。

```text
現物株の乗り換えでは、売却約定前の買付余力を前提にしない
```

Phase8のOrderPlanでは、同じreplacementに属するsellとbuyを同日planへ含めてもよいが、buy側は以下にする。

```text
action = REPLACE_BUY_AFTER_FILL_PLAN
executable = false
depends_on_fill_item_id = sell item id
requires_broker_snapshot_refresh = true
```

Paper Tradingでも同じ順序を守る。

```text
1. sell planをpaper ledgerへ予約
2. paper fillを仮定する場合もfill時刻と価格を記録
3. buying powerを再計算
4. buy planを再評価
5. buy paper executionを記録
```

実Broker snapshotとは別にpaper ledgerを保存する。

---

# 8. Broker Syncとの接続

Order Managerは、moomoo Broker Syncから正規化されたsnapshotを読む。

```text
BrokerAccountSnapshot
BrokerBalanceSnapshot
BrokerPositionSnapshot
BrokerOrderSnapshot
BrokerExecutionSnapshot
BrokerSyncResult
```

突合対象:

```text
cash
buying_power
holdings / positions
available_quantity
open_orders
recent filled / cancelled orders
executions
```

Broker snapshotが欠損、古い、破損、またはSafetyでHALTなら、通常のorder plan生成は停止する。

---

# 9. Paper Trading設計

Phase8のPaper Tradingは、実口座とは分離する。

保存先:

```text
.runtime/order_manager/paper/ledgers/
.runtime/order_manager/paper/trades/
.runtime/order_manager/paper/daily_snapshots/
.runtime/order_manager/paper/diffs/
```

Paper ledgerに含めるもの。

```text
paper_cash
paper_buying_power
paper_positions
paper_open_orders
paper_executions
unsettled_cash
settlement_date
trade_date
policy_id
```

Phase7の会計前提を引き継ぐ。

```text
100株単位
cash buffer 5%
max position weight 20%
T+2 conservative cash unavailable
transaction cost / slippage scenario
SELL_FIRST_BUY_AFTER_FILL
```

Broker snapshotとの比較では、paper ledgerを実口座状態として扱わない。比較結果は `BrokerSnapshotDiff` として保存する。

---

# 10. Human Review Gate

Phase8ではHuman Reviewが必須。

OrderPlanReviewReportには以下を含める。

```text
plan summary
policy
buy candidates
sell candidates
hold positions
cash impact
buying power impact
replacement dependency
SELL_FIRST_BUY_AFTER_FILL status
safety status
broker snapshot refs
paper ledger refs
blocked reasons
warnings
manual checklist
```

Human Review Gateは、Phase8では実注文許可を出さない。

```text
承認しても実発注しない
承認はpaper反映または次ステップ検討の記録に限る
```

---

# 11. Safety Guardとの接続

OperationGuard lock stateを必ず読む。

locked時:

```text
broker_sync:
  許可

read_state:
  許可

audit:
  許可

report:
  許可

normal_order_plan_generation:
  禁止

paper_execution_update:
  原則禁止

review_only_diagnostic_plan:
  許可候補
  ただし executable=false / plan_status=REVIEW_ONLY_LOCKED を必須にする
```

unlocked時:

```text
order plan生成は可能
paper trading反映は可能
live orderは不可
```

Crash Guard / Emergency Exit:

```text
Phase8ではplan生成まで
実売却注文は出さない
Emergencyは損失上限ではなく危険検知として扱う
ストップ安 / 特売り / 流動性不足はplan warningに出す
```

---

# 12. 保存先

Broker:

```text
.runtime/broker/
```

Order Manager:

```text
.runtime/order_manager/
.runtime/order_manager/plans/
.runtime/order_manager/review/
.runtime/order_manager/audit/
.runtime/order_manager/paper/
.runtime/order_manager/reconciliation/
```

Reports:

```text
reports/phase_reports/
docs/phase_reports/
```

Phase8-Aの設計報告は `docs/phase_reports/` に保存する。

---

# 13. 監査観点

Phase8 Order Manager監査では、以下を確認する。

```text
moomoo実API発注処理が存在しない
order submit APIが存在しない
cancel / modify order APIが存在しない
trade unlockが存在しない
login/logout自動化が存在しない
read-only境界が守られている
secretがrepoに保存されない
paper tradingと実口座snapshotが分離されている
order planがhuman review前提である
locked時に通常plan生成が止まる
review-only診断はexecutable=falseである
SELL_FIRST_BUY_AFTER_FILLがplan dependencyとして表現されている
Tachibana CLMID/API名/allowlistがPhase8設計へ混入していない
```

---

# 14. Phase8-B実装順序

推奨順序。

```text
1. OrderPlan / OrderPlanItem schemaを実装
2. moomoo read-only snapshot schemaをmockで用意
3. Broker snapshot loaderを作る
4. Safety lock state readerをOrder Managerへ接続
5. Capital Allocation decision loaderを作る
6. Broker snapshotとpaper ledgerの突合を実装
7. Order Plan Generatorを実装
8. Human Review report writerを実装
9. Paper ledger writerを実装
10. 監査テストを追加
```

禁止順序。

```text
moomoo SDK接続から始めない
OpenD live接続から始めない
place_order stubから始めない
cancel / modifyから始めない
secret設定から始めない
```

