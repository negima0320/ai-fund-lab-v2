# AI Fund Lab vNext moomoo Broker Integration Design

---

# 1. このドキュメントの目的

本ドキュメントは、Phase8以降のBroker連携を以下へ変更するための設計を定義する。

```text
moomoo証券
moomoo OpenAPI
OpenD
```

これまでの `docs/02_architecture/broker_integration_design.md` は立花証券 API 前提を含むため、Phase8では本ドキュメントをmoomoo前提の追加設計として扱う。

Phase8では実装しない。

```text
live order
auto order
order submit API
cancel / modify order API
login/logout自動化
secret保存
```

---

# 2. 参照した前提

既存設計:

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

moomoo公式ドキュメント確認:

```text
https://openapi.moomoo.com/moomoo-api-doc/en/intro/intro.html
https://openapi.moomoo.com/moomoo-api-doc/en/trade/get-acc-list.html
https://openapi.moomoo.com/moomoo-api-doc/en/trade/get-funds.html
https://openapi.moomoo.com/moomoo-api-doc/en/trade/get-position-list.html
https://openapi.moomoo.com/moomoo-api-doc/en/trade/get-order-list.html
https://openapi.moomoo.com/moomoo-api-doc/en/trade/get-history-order-list.html
```

公式ドキュメント上、moomoo OpenAPIはOpenDをゲートウェイとして使い、SDKからTrade APIを呼び出す構成である。Trade APIには資金、建玉、注文照会のread-only系と、発注、訂正、取消のwrite系が同じ領域に存在する。Phase8ではread-only系のみを設計対象とし、write系は実装・接続・テスト対象外とする。

---

# 3. 基本方針

最重要原則。

```text
Broker状態を正とする
システム内部状態は参考
Phase8ではread-only first
Phase8ではno live order
```

moomoo連携は、既存Broker Foundationの正規化snapshot設計を壊さず、証券会社固有adapterを差し替える方針とする。

```text
Broker interface
  ↓
Broker adapter
  ├─ mock adapter
  ├─ tachibana adapter legacy / isolated
  └─ moomoo adapter phase8 candidate
  ↓
normalized BrokerState
  ↓
Safety / Reconciliation / Order Manager
```

Phase8-Aでは `moomoo adapter phase8 candidate` を実装しない。必要なinterface案、保存形式、禁止境界、監査観点だけを定義する。

---

# 4. Tachibana依存の隔離方針

Phase8では、以下をmoomoo設計に持ち込まない。

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
Tachibana request / response stub
Tachibana allowlist
第二パスワード前提
```

既存のPhase2 Broker Foundationは削除しない。扱いを以下に変更する。

```text
既存Broker interface:
  継続利用候補

既存normalized snapshot:
  継続利用

Tachibana stub:
  legacy adapter候補として隔離

Phase8 moomoo設計:
  新規ドキュメントで上書き方針を定義
```

Phase8実装時に既存コードへ手を入れる場合も、Tachibana固有名を共通modelへ漏らしてはならない。

---

# 5. moomoo OpenD / OpenAPI抽象化

## 5.1 OpenD境界

OpenDはmoomooサーバーとの通信を中継するゲートウェイである。Phase8ではOpenD接続を設計対象にするが、自動起動、自動ログイン、自動logoutは行わない。

Phase8-Aで許可する設計対象:

```text
OpenD host / port を外部設定として扱う案
read-only Trade API method map
response normalizer方針
snapshot保存方針
secret非保存方針
```

Phase8-Aで禁止:

```text
OpenDプロセス起動
OpenDログイン自動化
OpenD logout自動化
実API接続テスト
実口座取得
trade unlock
```

## 5.2 Read-only method候補

公式ドキュメント上のread-only候補を、Phase8では以下のように扱う。

```text
get_acc_list:
  account snapshot候補。
  acc_id確認に使えるが、Phase8では実account idをrepoへ保存しない。

accinfo_query:
  cash / buying power / total assets / risk status候補。

position_list_query:
  holdings / positions候補。

order_list_query:
  open ordersおよび直近24hのfilled/cancelled order候補。

history_order_list_query:
  order history候補。
```

約定はmoomooのDeals系APIまたはorder list内の `dealt_qty` / `dealt_avg_price` の扱いを別途確認する。Phase8-Aでは、実約定照会コードを書かず、`executions snapshot` の正規化modelだけを設計する。

## 5.3 Explicit denylist

Phase8では以下を実装しない。

```text
place_order
place_combo_order
modify_order
cancel_order
unlock_trade
order push callback subscription
transaction push subscription
```

注意:

```text
unlock_trade は発注可能状態へ近づく操作であり、Phase8-Aのread-only境界外とする。
push subscription は実口座イベント処理を複雑化するため、Phase8-Aでは対象外とする。
```

---

# 6. Read-onlyで取得する情報

Phase8-AのBroker Syncは、以下を取得できる設計にする。

```text
cash
buying power
holdings / positions
order history
executions
account snapshot
```

最小正規化model:

```text
MoomooAccountSnapshot
MoomooBalanceSnapshot
MoomooPositionSnapshot
MoomooOrderSnapshot
MoomooExecutionSnapshot
MoomooBrokerSyncResult
```

ただし、Safety / Order Managerへ渡す共通形式は既存名に寄せる。

```text
BrokerAccountSnapshot
BrokerBalanceSnapshot
BrokerPositionSnapshot
BrokerOrderSnapshot
BrokerExecutionSnapshot
BrokerSyncResult
```

moomoo固有のraw responseを共通modelへ混入させない。

---

# 7. Snapshot保存方針

保存先:

```text
.runtime/broker/snapshots/accounts/
.runtime/broker/snapshots/balance/
.runtime/broker/snapshots/positions/
.runtime/broker/snapshots/orders/
.runtime/broker/snapshots/executions/
.runtime/broker/sync_results/
```

保存してよいもの:

```text
snapshot_id
broker = moomoo
environment = design / mock / paper / readonly_candidate
as_of
currency
cash
buying_power
positions
orders
executions
normalized_status
warning codes
source_method_name
schema_version
```

保存してはいけないもの:

```text
moomoo ID
account number
full acc_id
uni_card_num
card_num
login password
trade password
token
cookie
OpenD auth material
raw response whole payload
API endpoint with secret
```

実account識別が必要な場合は、Phase8では以下に限定する。

```text
account_ref = masked or hash
account_label = manually assigned alias
```

---

# 8. Broker Syncのread-only流れ

Phase8-Aの設計上の流れ。

```text
1. 人間がOpenDとログイン状態を別途準備する
2. Broker Syncがread-only設定を読む
3. account snapshot候補を取得
4. balance snapshot候補を取得
5. position snapshot候補を取得
6. order snapshot候補を取得
7. execution snapshot候補を取得
8. 正規化snapshotを書き出す
9. BrokerSyncResultを書き出す
10. Safety / Reconciliationのinputにする
```

Phase8では、上記のうち設計とmock/stub案までに留める。実API呼び出しはしない。

---

# 9. Safety Guard接続

Safety Guardは既存方針を維持する。

```text
分からない時は止まる
Broker状態を正とする
Broker Sync不一致はHALT
自動復旧は禁止
復旧には人間承認が必要
```

moomoo Broker Syncが失敗、破損、不明、またはsnapshot欠損になった場合は、fail-closedで `HALT` 候補とする。

Phase8では、Safety Guardが `locked` の場合:

```text
broker_sync:
  許可

read_state:
  許可

audit:
  許可

report:
  許可

order_plan_generation:
  原則停止
  例外的にreview-only診断を出す場合も executable=false を必須にする
```

---

# 10. 監査観点

Phase8-Aの監査では、最低限以下を確認する。

```text
moomoo実API発注処理が存在しない
place_order / modify_order / cancel_order が存在しない
unlock_trade が存在しない
read-only境界が守られている
secretがrepoに保存されない
account idが平文保存されない
paper tradingと実口座snapshotが分離されている
order planがhuman review前提である
Tachibana CLMIDがPhase8 moomoo設計に混入していない
```

---

# 11. Phase8-Bへの引き継ぎ

Phase8-Bで実装する場合の順序。

```text
1. common Broker snapshot schemaをmoomoo向けに拡張
2. moomoo read-only adapter interfaceだけ作る
3. moomoo mock response fixtureを作る
4. normalizerをmockで検証
5. .runtime/broker/へsnapshot保存
6. Safety Reconciliationへ接続
7. 実API接続はまだ行わない
8. Paper Trading ledgerと実Broker snapshotを分離して比較する
```

Phase8-Bでも、live order、auto order、order submit、cancel、modify、login/logout自動化は禁止する。

