# Phase2 Broker Foundation Plan

---

# 1. 目的

Phase2 Broker Foundation の目的は、将来の立花証券 API 接続に備えた Broker interface、request/response stub、mock transport、正規化snapshot保存形式を作り、Broker Sync と Portfolio State の入力土台を整えることである。

現時点では立花証券の契約が未完了のため、Phase2では実API接続を行わない。新規注文、売却注文、取消注文、訂正注文、実売買、AI判断との接続、Backtest、Paper Trading は行わない。

---

# 2. 参照資料

- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/broker_integration_design.md`
- `docs/02_architecture/safety_guard_design.md`
- 立花証券 e支店 API リファレンス  
  `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`

公式リファレンスは `e_api_v4r9` の記述を確認した。ただしPhase2では本番・デモいずれにも接続しない。URLや認証情報は将来差し替え用のstub設定としてのみ扱う。

---

# 3. Phase2 最小スコープ

実装対象:

```text
Broker interface設計
Tachibana API request/response stub
mock transport
read-only client skeleton
残高・可能額stub responseの正規化
現物保有株・信用建玉stub responseの正規化
注文一覧stub responseの正規化
normalized broker snapshot保存
Broker Sync snapshot保存
Portfolio State更新前inputの形式定義
```

実装しないこと:

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
Candidate AI / Opportunity AI / Position Management AI との統合
Backtest
Paper Trading
```

---

# 4. 立花証券APIで必要なエンドポイント候補

立花証券 API は `sCLMID` で機能を指定する REQUEST I/F 形式で扱う。

| 用途 | CLMID | Phase2での扱い | 備考 |
| --- | --- | --- | --- |
| ログインstub | `CLMAuthLoginRequest` | payload builderのみ | 実loginはしない。将来接続時のrequest形だけ固定する |
| ログアウトstub | `CLMAuthLogoutRequest` | payload builderのみ | 実logoutはしない。将来接続時のrequest形だけ固定する |
| 可能額サマリー | `CLMZanKaiSummary` | mock正規化対象 | 現物株式買付可能額、信用新規建可能額、出金可能額など |
| 買余力 | `CLMZanKaiKanougaku` | mock正規化補助候補 | 株式現物買付可能額など |
| 現物保有銘柄一覧 | `CLMGenbutuKabuList` | mock正規化対象 | `sIssueCode=""` で全保有銘柄取得想定 |
| 信用建玉一覧 | `CLMShinyouTategyokuList` | mock正規化対象 | 信用口座を使わない場合でも空配列として扱える設計にする |
| 注文一覧 | `CLMOrderList` | mock正規化対象 | `sIssueCode`, `sSikkouDay`, `sOrderSyoukaiStatus` は任意指定 |
| 注文約定一覧詳細 | `CLMOrderListDetail` | stub調査候補 | Phase2最小では注文一覧優先 |

注文入力系の `CLMKabuNewOrder`, `CLMKabuCorrectOrder`, `CLMKabuCancelOrder` は Phase2 では実装しない。

---

# 5. 認証方式の整理

## 5.1 ログインstub

`CLMAuthLoginRequest` のpayload builderを作る。ただしPhase2では実loginを実行しない。

```json
{
  "sCLMID": "CLMAuthLoginRequest",
  "sAuthId": "<secret>"
}
```

応答には REQUEST I/F 用の URL、MASTER/PRICE/EVENT 用 URL などが含まれる想定だが、Phase2ではfixture responseだけを扱う。

## 5.2 セッション情報

ログイン応答の URL やセッションに相当する値は秘密情報として扱う。

```text
ログ出力しない
manifest/reportに出さない
stdout/stderrに出さない
.runtime/cache/broker/ 配下に保存する場合も平文永続化を避ける
```

Phase2では実セッションを作らない。セッション相当値はfixture内でも秘密情報として扱い、sanitizer対象にする。

## 5.3 ログアウトstub

`CLMAuthLogoutRequest` のpayload builderを作る。ただしPhase2では実logoutを実行しない。

```json
{
  "sCLMID": "CLMAuthLogoutRequest"
}
```

---

# 6. 残高取得の設計

## 6.1 使用候補

主候補:

```text
CLMZanKaiSummary
```

補助候補:

```text
CLMZanKaiKanougaku
CLMZanKaiKanougakuSuii
```

## 6.2 正規化モデル案

`BrokerBalanceSnapshot`

```text
fetched_at
source=broker_tachibana
account_id_hash
cash_available
stock_buying_power
margin_buying_power
withdrawable_cash
nisa_growth_available
shortage_flag
raw_response_ref
```

## 6.3 保存先

```text
.runtime/broker/snapshots/balance/
```

Phase2実装では、raw response は `.runtime/broker/raw/` に保存し、normalized snapshot は `.runtime/broker/snapshots/` に保存する案とする。どちらも `.runtime` 配下でGit管理しない。

---

# 7. 保有株取得の設計

## 7.1 使用候補

現物:

```text
CLMGenbutuKabuList
```

信用:

```text
CLMShinyouTategyokuList
```

## 7.2 正規化モデル案

`BrokerPositionSnapshot`

```text
fetched_at
source=broker_tachibana
account_id_hash
position_type=cash_or_margin
code
market
quantity
sellable_quantity
book_price
valuation_price
market_value
unrealized_pnl
unrealized_pnl_rate
tax_account_type
raw_response_ref
```

信用建玉では以下も追加する。

```text
position_id
side
open_date
due_date
margin_type
repayable_quantity
```

## 7.3 Portfolio State への反映

Broker Sync Manager が取得した snapshot を唯一の更新元にする。システム内の保有状態とbroker snapshotが不一致の場合、Phase3 Safety Foundation で HALT 判定に接続する。

---

# 8. 注文一覧取得の設計

## 8.1 使用候補

```text
CLMOrderList
```

要求例:

```json
{
  "sCLMID": "CLMOrderList",
  "sIssueCode": "",
  "sSikkouDay": "",
  "sOrderSyoukaiStatus": ""
}
```

`sOrderSyoukaiStatus` 候補:

```text
"" 指定なし
1 未約定
2 全部約定
3 一部約定
4 訂正取消可能な注文
5 未約定 + 一部約定
```

## 8.2 正規化モデル案

`BrokerOrderSnapshot`

```text
fetched_at
source=broker_tachibana
account_id_hash
order_id
code
market
side
cash_or_margin
order_quantity
current_quantity
executed_quantity
order_price
order_price_type
condition
status_code
status_text
order_datetime
expire_day
raw_response_ref
```

## 8.3 注意

注文一覧は参照のみ。Phase2では注文作成・訂正・取消を呼ぶコードパスを作らない。

---

# 9. APIキー・ログイン情報の安全な扱い

環境変数案:

```text
TACHIBANA_API_AUTH_ID
TACHIBANA_API_BASE_URL
TACHIBANA_API_ENV=demo_or_prod
TACHIBANA_API_TIMEOUT_SECONDS
```

安全方針:

```text
.env に保存しGit管理しない
.env.example には空値のみ置く
ログに出さない
stdout/stderrに出さない
report/manifestに出さない
例外メッセージに含めない
HTTP request payloadを丸ごとログしない
ログイン応答URLを秘密情報扱いにする
account id はhash化する
```

禁止:

```text
second password をPhase2で扱わない
注文系CLMIDを実装しない
```

---

# 10. mock / stub 方針

通常テスト:

```text
実APIを呼ばない
mock transportを使う
立花証券のsample JSONをfixture化する
ログイン応答URLやauth idはダミー値のみ使う
```

stub preview:

```text
実APIを呼ばない
ログインしない
実口座情報を取得しない
live CLIを作らない
request payload、fixture response、snapshot schemaをテストで確認する
secret値は表示しない
```

Phase2で作らないもの:

```text
実API read smoke
live接続CLI
実login/logout
実口座情報取得
```

将来live接続する場合は、Phase2で作る `BrokerTransport` interface を差し替えポイントにする。Phase2の成果物は、live transportなしでも Broker Sync の流れを再現できることを優先する。

---

# 11. src/broker 最小構成案

正式実装時は既存packageに合わせ、以下のどちらかを採用する。

推奨:

```text
src/ai_fund_lab_v2/broker/
  __init__.py
  tachibana/
    __init__.py
    client.py
    models.py
    settings.py
    sanitizer.py
    transport.py
  sync/
    __init__.py
    broker_sync.py
    portfolio_state.py
```

ユーザー指示の `src/broker/` は、Python packageの一貫性を優先して `src/ai_fund_lab_v2/broker/` に読み替える案とする。どうしても独立packageにする必要がある場合は、Phase2実装前に再判断する。

---

# 12. tests/broker テスト方針

推奨:

```text
tests/broker/
  test_tachibana_settings.py
  test_tachibana_client_readonly.py
  test_tachibana_sanitizer.py
  test_broker_sync.py
  test_portfolio_state.py
```

必須テスト:

```text
認証情報不足時の分かりやすい例外
secretが例外・ログ・stdoutに出ない
login requestの組み立て
logout requestの組み立て
balance requestのCLMIDがCLMZanKaiSummaryである
positions requestのCLMIDがCLMGenbutuKabuList / CLMShinyouTategyokuListである
orders requestのCLMIDがCLMOrderListである
注文系CLMIDを呼べない
mock responseをnormalized snapshotへ変換できる
保存先が .runtime/broker/ 配下である
通常pytestで実APIを呼ばない
```

---

# 13. Phase2 詳細タスク分解

## Phase2-B1 設計固定

- このplanをレビューする
- `broker_integration_design.md` のPhase2範囲を確定する
- read-only CLMID allowlist を確定する
- `.runtime/broker/` 保存方針を確定する

## Phase2-B2 設定・安全基盤

- Tachibana settings 追加
- secret sanitizer 追加
- read-only allowlist 追加
- runtime broker paths 追加
- logging 方針追加

実装対象:

```text
src/ai_fund_lab_v2/broker/settings.py
src/ai_fund_lab_v2/broker/sanitizer.py
src/ai_fund_lab_v2/broker/allowlist.py
src/ai_fund_lab_v2/broker/transport.py
src/ai_fund_lab_v2/broker/runtime_paths.py
```

B2では実HTTP transportを作らず、`MockBrokerTransport` のみを提供する。`MockBrokerTransport` は request payload の `sCLMID` を read-only allowlist で検査し、登録済みfixture responseだけを返す。注文系CLMIDは例外にする。

## Phase2-B3 Client Mock実装

- transport interface
- login/logout request builder
- request I/F caller
- mock transport tests
- 注文系CLMID禁止テスト

実装対象:

```text
src/ai_fund_lab_v2/broker/request_builder.py
src/ai_fund_lab_v2/broker/client.py
src/ai_fund_lab_v2/broker/response.py
src/ai_fund_lab_v2/broker/errors.py
```

B3では `TachibanaRequestBuilder` が read-only CLMID の payload を作り、`TachibanaReadOnlyClient` が `MockBrokerTransport` 経由で fixture response を `BrokerResponseEnvelope` として返す。実HTTP transport、実login/logout、snapshot保存、Portfolio State更新はまだ実装しない。

## Phase2-B4 Stub Response Normalization

- `BrokerBalanceSnapshot` model
- `BrokerPositionSnapshot` model
- `BrokerOrderSnapshot` model
- `CLMZanKaiSummary` fixture responseの正規化
- `CLMZanKaiKanougaku` fixture responseの正規化
- `CLMGenbutuKabuList` / `CLMShinyouTategyokuList` fixture responseの正規化
- `CLMOrderList` / `CLMOrderListDetail` fixture responseの正規化
- normalized balance snapshot保存
- normalized positions snapshot保存
- normalized orders snapshot保存
- `.runtime/broker/snapshots/` 配下のみを保存先にする
- snapshot data JSON と簡易 manifest JSON を同時保存する
- raw responseそのものはnormalized modelへ混入しない
- secret値、account id、URL、token、passwordをsnapshotへ保存しない
- 正規化結果はPortfolio State更新前のinputとして扱い、Portfolio Stateそのものは更新しない

実装対象:

```text
src/ai_fund_lab_v2/broker/models.py
src/ai_fund_lab_v2/broker/normalizer.py
src/ai_fund_lab_v2/broker/snapshot_writer.py
```

## Phase2-B5 Mock Broker Sync

- mock transportから balance / positions / orders のfixture responseを取得
- response envelopeを正規化
- B4のsnapshot writerで保存
- sync result summaryを返す
- 実API、live CLI、Portfolio State更新は行わない

実装対象:

```text
src/ai_fund_lab_v2/broker/sync.py
src/ai_fund_lab_v2/broker/sync_result.py
src/ai_fund_lab_v2/cli/broker_sync.py
```

mock sync CLI:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.broker_sync --mode mock --runtime-dir .runtime
```

Phase2-B5 CLI は `--mode mock` のみを受け付ける。実API接続、login/logout、live smoke、発注系、Portfolio State更新は行わない。

`BrokerSyncResult` は以下を返す。

```text
sync_id
broker
source=mock
started_at
finished_at
status
balance_snapshot_count
position_snapshot_count
order_snapshot_count
snapshot_paths
manifest_paths
warnings
errors
```

## Phase2-B6 Completion Audit

- 実APIなしで broker sync の流れをmock再現できる
- balance / positions / orders のstub responseを正規化できる
- normalized snapshotを `.runtime/broker/` に保存できる
- Portfolio State更新前のinputとして使える形になっている
- 実APIに切り替える時の差し替えポイントが明確
- AI統合・発注系未実装を監査

---

# 14. Phase2 完了判定

Phase2は以下を満たしたら完了。

```text
実APIなしで broker sync の流れをmockで再現できる
balance / positions / orders のstub responseを正規化できる
normalized snapshotを .runtime/broker/ に保存できる
Portfolio State更新前のinputとして使える形になっている
実APIに切り替える時の差し替えポイントが明確
通常pytestで実APIを呼ばない
secret leakがない
注文系CLMIDが実装されていない
AI判断と接続されていない
```
