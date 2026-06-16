# Phase8-A moomoo Order Manager Design Report

## 1. Phase8-Aの目的

Phase8-Aでは、Broker API前提を以下へ変更する設計を作成した。

```text
旧:
  立花証券 API

新:
  moomoo証券
  moomoo OpenAPI
  OpenD
```

今回は実装しない。

```text
src配下の本格実装なし
moomoo SDK/API接続コードなし
実API呼び出しテストなし
live orderなし
auto orderなし
```

---

## 2. 読んだドキュメント

指定ドキュメント:

```text
docs/01_requirements/phase_roadmap.md
docs/phase_reports/phase7_final_summary_and_phase8_handoff.md
docs/02_architecture/broker_integration_design.md
docs/02_architecture/safety_guard_design.md
docs/02_architecture/safety_foundation_phase3_design.md
docs/02_architecture/safety_manual_review_flow.md
docs/02_architecture/safety_manual_unlock_flow.md
docs/02_architecture/safety_manual_unlock_apply_flow.md
docs/02_architecture/safety_operation_guard_lock_state_flow.md
```

補助確認:

```text
moomoo OpenAPI Introduction
moomoo Trade API Get Account List
moomoo Trade API Get Account Funds
moomoo Trade API Get Positions
moomoo Trade API Get open Orders
moomoo Trade API Get Historical Orders
```

---

## 3. 作成したドキュメント

```text
docs/02_architecture/moomoo_broker_integration_design.md
docs/02_architecture/order_manager_phase8_design.md
docs/phase_reports/phase8a_moomoo_order_manager_design.md
```

---

## 4. 既存ドキュメントからの重要前提

Phase roadmap:

```text
Phase8 = Order Manager
Phase9 = Paper Trading
Phase11 = Small Live Test
Phase12 = Full Automation
```

Phase7 handoff:

```text
Phase8は実売買ではない
Read-only Broker Sync
Paper Trading
Order Plan Generator
Human Review Gate
No live order
```

Safety:

```text
分からない時は止まる
Broker状態を正とする
Broker Sync不一致はHALT
自動復旧は禁止
復旧には人間承認が必要
locked時はbroker_sync / read_state / audit / reportのみ許可
```

Phase7 policy:

```text
Primary = CAP5
Shadow = CAP4 / POLICY_Y_CAP4_EDGE08_CONF5
SELL_FIRST_BUY_AFTER_FILL は必須
100株単位
T+2 conservative cash unavailable
cash buffer 5%
max position weight 20%
```

---

## 5. moomoo前提への設計変更

Phase8では、立花証券固有の以下を使わない。

```text
CLMID
CLMAuthLoginRequest
CLMAuthLogoutRequest
CLMZanKaiSummary
CLMZanKaiKanougaku
CLMGenbutuKabuList
CLMShinyouTategyokuList
CLMOrderList
CLMOrderListDetail
Tachibana allowlist
第二パスワード前提
```

代わりに、moomoo OpenD / OpenAPI をBroker adapter候補として扱う。

```text
Broker interface
  ↓
Broker adapter
  ├─ mock
  ├─ tachibana legacy isolated
  └─ moomoo readonly candidate
  ↓
normalized Broker snapshots
```

既存のnormalized snapshot設計は維持する。

```text
BrokerBalanceSnapshot
BrokerPositionSnapshot
BrokerOrderSnapshot
BrokerSyncResult
```

Phase8では追加候補として以下を定義した。

```text
BrokerAccountSnapshot
BrokerExecutionSnapshot
```

---

## 6. Read-only取得対象

Phase8-A設計上の取得対象:

```text
cash
buying power
holdings / positions
order history
executions
account snapshot
```

moomoo API候補:

```text
get_acc_list:
  account snapshot

accinfo_query:
  cash / buying power / total assets / risk status

position_list_query:
  holdings / positions

order_list_query:
  open orders / recent filled or cancelled orders

history_order_list_query:
  order history
```

executionsは、Deals系APIまたはorder listのfilled fieldsをPhase8-Bで再確認する。

---

## 7. Phase8で禁止するもの

Phase8では以下を禁止する。

```text
live order
auto order
order submit API
cancel / modify order API
place_order
place_combo_order
modify_order
cancel_order
unlock_trade
login/logout実行の自動化
OpenDプロセス自動起動
秘密情報の保存
実口座番号の平文保存
実API呼び出しテスト
```

Phase8のOrderPlanは、必ず以下を持つ。

```text
executable = false
live_order_allowed = false
requires_human_review = true
```

---

## 8. Order Manager責務

Phase8 Order Managerは以下を行う。

```text
Candidate AI / Opportunity AI / Position Management AI / Capital Allocation の結果を受け取る
実口座snapshotと突合する
buy / sell / holdのorder planを生成する
paper tradingに反映する
human review用のplanを出力する
Safety Guard lock stateを確認する
監査recordを保存する
```

ただし、実注文は出さない。

---

## 9. Safety Guard接続

locked時の方針:

```text
normal order plan generation:
  停止

review-only diagnostic plan:
  許可候補
  executable=false
  plan_status=REVIEW_ONLY_LOCKED

paper execution update:
  原則停止
```

Crash Guard / Emergency Exit:

```text
Phase8ではplan生成まで
実売却注文は出さない
Emergencyは損失上限ではなく危険検知
```

---

## 10. 保存先

Broker:

```text
.runtime/broker/snapshots/accounts/
.runtime/broker/snapshots/balance/
.runtime/broker/snapshots/positions/
.runtime/broker/snapshots/orders/
.runtime/broker/snapshots/executions/
.runtime/broker/sync_results/
```

Order Manager:

```text
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

---

## 11. 監査観点

Phase8-A以降で確認すること。

```text
moomoo実API発注処理が存在しないこと
read-only境界が守られていること
secretがrepoに保存されないこと
account idが平文保存されないこと
paper tradingと実口座snapshotが分離されていること
order planがhuman review前提であること
locked時に通常plan生成が止まること
Tachibana CLMID/API名/allowlistがPhase8設計へ混入していないこと
```

---

## 12. Phase8-Bで実装すべき順序

推奨順序:

```text
1. OrderPlan / OrderPlanItem schema
2. moomoo read-only snapshot schema
3. moomoo mock response fixture
4. normalizer mock test
5. Broker snapshot loader
6. Safety lock state reader connection
7. Capital Allocation decision loader
8. Broker snapshotとpaper ledgerの分離突合
9. Order Plan Generator
10. Human Review report writer
11. Paper ledger writer
12. 禁止API不在の監査テスト
```

まだやらないこと:

```text
moomoo SDK接続
OpenD live接続
実API smoke test
place_order stub
cancel / modify stub
login/logout自動化
secret設定
```

---

## 13. 注意点

立花証券前提からmoomoo前提へ変更する際の注意:

```text
1. CLMID中心のAPI名を共通interfaceへ持ち込まない
2. Tachibana allowlistをmoomooに流用しない
3. moomoo Trade APIにはread/writeが同居するため、read-only境界をmethod単位で監査する
4. unlock_tradeはPhase8では禁止する
5. acc_id / card_num / uni_card_numをrepoへ平文保存しない
6. OpenDの起動・ログイン状態は人間管理とし、自動化しない
7. paper ledgerと実Broker snapshotを混ぜない
8. SELL_FIRST_BUY_AFTER_FILLをplan dependencyとして表現する
9. Phase8のhuman review承認は実発注許可ではない
10. Small Live TestはPhase11以降で再承認する
```

---

## 14. Phase8-A完了判定

判定:

```text
PHASE8A_MOOMOO_ORDER_MANAGER_DESIGN_COMPLETED
```

実装・実API・実発注は未実施。

