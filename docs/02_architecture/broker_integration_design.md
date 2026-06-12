# AI Fund Lab vNext 証券会社連携設計

---

# 1. このドキュメントの目的

本ドキュメントは、

```text id="gbz5j5"
立花証券 API
```

との連携方式を定義する。

---

目的は、

```text id="kgjlwm"
安全に自動売買を行う
```

ことである。

---

# 2. 基本方針

## 証券会社を正とする

最重要原則。

---

常に、

```text id="zz4n3r"
立花証券の状態
```

を正とする。

---

システム内部状態は、

```text id="my7nzs"
参考
```

に過ぎない。

---

例

```text id="u6nh5c"
システム:
100株保有

証券会社:
0株
```

---

この場合、

```text id="ib6pnj"
証券会社が正
```

とする。

---

# 3. 全体フロー

```text
New Buy:

Opportunity AI

↓

Capital Allocation Engine

↓

Order Plan

---

Sell / Reduce:

Position Management AI

↓

Order Plan

---

Common Execution:

Order Manager

↓

立花証券 API

↓

Broker Sync Manager

↓

Portfolio State Manager
```

---

# 4. Order Managerの責務

Order Managerは、

```text id="jwsx4j"
注文管理のみ
```

を行う。

---

判断は禁止。

---

実施すること

```text id="m4r6ie"
新規注文

売却注文

注文取消

約定確認

注文状態管理
```

---

実施しないこと

```text id="opjv9u"
銘柄選定

購入判断

売却判断
```

---

# 5. Broker Sync Manager

## 目的

```text id="lg1mwu"
証券口座同期
```

---

## 定期取得

取得対象

```text id="a6n6j6"
現金残高

保有銘柄

注文一覧

約定一覧
```

---

## Phase2 Broker Foundation の範囲

Phase2 Broker Foundation では、将来の立花証券 API 接続に備えた Broker interface、Tachibana request/response stub、mock transport、read-only client skeleton、正規化snapshot保存形式を作る。

現時点では立花証券の契約が未完了のため、Phase2では実API接続を行わない。

対象:

```text
Broker interface設計

Tachibana API request/response stub

mock transport

read-only client skeleton

balance / positions / orders の正規化model設計

broker snapshot保存形式

将来live接続するための安全ガード
```

禁止:

```text
実API login

実API logout

実API read smoke

live接続CLI

新規注文

売却注文

取消注文

訂正注文

実売買

第二パスワード利用

実口座情報取得

AI判断との接続
```

Phase2 の完了条件は、実APIなしで broker sync の流れをmockで再現でき、balance / positions / orders のstub responseを正規化し、normalized snapshotを `.runtime/broker/` に保存できることとする。Portfolio Stateは更新せず、その直前のinputとして使える形までをPhase2範囲にする。

## 立花証券 API 候補

公式リファレンス `e_api_v4r9` で確認する Phase2 候補は以下。

```text
CLMAuthLoginRequest:
  ログインstub。sAuthIdを含むpayload形を固定するが、Phase2では実loginしない。

CLMAuthLogoutRequest:
  ログアウトstub。payload形を固定するが、Phase2では実logoutしない。

CLMZanKaiSummary:
  可能額サマリー。現物株式買付可能額、信用新規建可能額、出金可能額などを取得する候補。

CLMZanKaiKanougaku:
  買余力。株式現物買付可能額などを取得する候補。

CLMGenbutuKabuList:
  現物保有銘柄一覧。指定なしで全保有銘柄を取得する。

CLMShinyouTategyokuList:
  信用建玉一覧。指定なしで全信用建玉を取得する。

CLMOrderList:
  注文一覧。銘柄コード、注文執行予定日、注文照会状態で任意絞り込み可能。

CLMOrderListDetail:
  注文約定一覧詳細。Phase2では必要に応じて調査対象に留める。
```

Phase2 最小実装では `CLMZanKaiSummary`, `CLMGenbutuKabuList`, `CLMShinyouTategyokuList`, `CLMOrderList` のstub responseを中心に扱う。注文入力系の `CLMKabuNewOrder`, `CLMKabuCorrectOrder`, `CLMKabuCancelOrder` は実装しない。

## 正規化snapshot

Phase2-B4では、mock responseを以下の中間形式へ正規化する。

```text
BrokerBalanceSnapshot
BrokerPositionSnapshot
BrokerOrderSnapshot
```

正規化modelには raw response そのものを混入させない。保持するのは `raw_clmid`, `raw_result_code`, warning などの最小メタ情報に限定する。account id、URL、token、password、auth id、第二パスワードは保存しない。

保存先は以下に限定する。

```text
.runtime/broker/snapshots/balance/
.runtime/broker/snapshots/positions/
.runtime/broker/snapshots/orders/
```

snapshot は JSON で保存し、同時に簡易 manifest JSON を保存する。この出力は Portfolio State 更新前の input として扱い、Phase2 では Portfolio State を更新しない。

## Mock Broker Sync

Phase2-B5では、mock clientから以下を順番に取得し、normalizerとsnapshot writerへ接続する。

```text
CLMZanKaiSummary
CLMZanKaiKanougaku
CLMGenbutuKabuList
CLMShinyouTategyokuList
CLMOrderList
```

sync結果は `BrokerSyncResult` として返す。これは Portfolio State 更新前のinputであり、Phase2ではPortfolio Stateを変更しない。

mock sync CLI は以下のみを許可する。

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.broker_sync --mode mock --runtime-dir .runtime
```

`--mode live` は提供しない。実API接続、login/logout実行、live smoke CLI、発注系APIはPhase2範囲外とする。

---

## 更新タイミング

最低

```text id="n1m3c8"
起動時

注文前

注文後

定期実行
```

---

# 6. Portfolio State Manager

目的

```text id="ocfcq8"
システム状態管理
```

---

管理対象

```text id="yzvf1v"
現金

保有銘柄

取得単価

保有日数

評価損益
```

---

更新元

```text id="zk9vqm"
Broker Sync Manager
```

のみ。

---

# 7. 注文フロー

## 新規買い

```text
Opportunity AI

↓

Capital Allocation Engine

↓

Order Manager

↓

立花証券

↓

約定

↓

Broker Sync Manager

↓

Portfolio State Manager
```

---

## 売却

```text
Position Management AI

↓

Order Manager

↓

立花証券

↓

約定

↓

Broker Sync Manager

↓

Portfolio State Manager
```

---

# 8. 約定確認

重要。

---

注文発行だけでは、

```text id="zrnzzn"
購入成功
```

としない。

---

必ず、

```text id="bzf0kj"
約定確認
```

を行う。

---

状態

```text id="psnqef"
PENDING

PARTIAL

FILLED

CANCELLED

REJECTED
```

---

# 9. 二重注文防止

禁止。

```text id="4md7qb"
同一銘柄

同一方向

未約定
```

で複数注文。

---

Order Managerは、

```text id="dn72j9"
既存注文確認
```

を行う。

---

# 10. 不整合検知

比較する。

---

## システム状態

```text id="7xfij0"
cash

positions
```

---

## 証券会社状態

```text id="mg9s1t"
cash

positions
```

---

一致しない場合

```text id="fdw2zv"
Safety Guard
```

へ通知。

---

# 11. 自動停止条件

以下で停止。

---

## APIエラー

```text id="5vy7v8"
連続失敗
```

---

## 残高不一致

---

## 保有株不一致

---

## 約定不一致

---

## 二重注文疑い

---

## 想定外ポジション

---

結果

```text id="dzj1zr"
HALT
```

---

# 12. Safety Guard連携

Safety Guardは、

以下を監視する。

```text id="78eqw8"
API状態

同期状態

注文状態

損失状態
```

---

状態

```text id="bqt9kn"
OK

WARNING

HALT
```

---

# 13. ログ

必須。

---

保存対象

```text id="5j43zv"
送信注文

注文結果

約定結果

APIレスポンス

同期結果

停止理由
```

---

# 14. 復旧方針

起動時、

必ず

```text id="slgv3w"
Broker Sync
```

を実施。

---

証券会社状態から復元する。

---

復元対象

```text id="jnh1nq"
現金

保有株

注文状態
```

---

# 15. テスト方針

順番。

---

## Stage1

```text id="o65a03"
残高取得
```

---

## Stage2

```text id="b5f7mq"
保有株取得
```

---

## Stage3

```text id="vghscl"
注文照会
```

---

## Stage4

```text id="ncb8pd"
少額注文
```

---

## Stage5

```text id="naxy8x"
完全自動売買
```

---

# 16. 禁止事項

禁止。

---

```text id="cv49ar"
約定確認なしで保有更新

証券会社状態無視

二重注文許可

Broker Sync省略

Safety Guard無視
```

---

# 17. 最終原則

AI Fund Lab は、

```text id="vwzzr0"
AIが株を選ぶシステム
```

ではない。

---

最終的には、

```text id="s8s19w"
安全に運用できる
自動売買システム
```

である。

---

AIが正しくても、

```text id="fhhj4z"
注文

約定

同期
```

が壊れていたら失敗。

---

したがって、

```text id="mjlwmq"
Broker Integration
```

は

```text id="7jzt8q"
AIと同じくらい重要
```

である。
