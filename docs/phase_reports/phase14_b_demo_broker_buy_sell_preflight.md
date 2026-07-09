# Phase14-B Demo Broker Connectivity and BUY/SELL Scenario Preflight

作成日: 2026-07-07

## Status

```text
PHASE14B_PREFLIGHT_COMPLETE
```

本資料は Phase14-A で定義した Integrated Operation Acceptance Test に向けた Demo Broker 接続・環境・BUY/SELL テストシナリオの事前確認である。

本フェーズでは Demo Submit、Demo 注文、Production 注文、Broker API 呼び出し、通知送信、launchd / plist 変更、AI 再学習、Backtest / Simulation は実行していない。

## 1. 目的

Phase14-B の目的は、Phase14-C 以降で Runtime v2 の統合運用テストへ進む前に、以下を確認することである。

- 立花証券 API 設定が Demo 環境を向いていること。
- Production endpoint / production credential / real order path へ到達しないこと。
- Runtime v2 から Demo Broker へ接続する場合の入口が明確であること。
- BUY と SELL の両方を Phase14 の必須テスト対象として定義すること。
- Demo Submit 前に必要な guard を明確にすること。
- 異常系が REVIEW_REQUIRED または BLOCKED に止まる設計であること。
- Phase14-C 以降の実行順序を整理すること。

Phase14 では BUY だけでなく SELL を必ず検証対象に含める。過去フェーズで買い注文テストの準備や検証は進んでいるが、実運用では売却、縮小、手仕舞いまで Runtime が安全に制御できる必要がある。そのため SELL 系テストは Phase14 の必須対象である。

## 2. 今回許可したこと

Phase14-B では以下のみを許可した。

- Demo 環境の接続前提確認
- Demo credential / endpoint が demo を向いていることの確認
- ReadOnly capability 確認
- Submit capability の設計確認
- BUY / SELL テストシナリオ作成
- 必要最小限の静的確認
- ドキュメント作成
- JSON レポート作成

設定分類の確認では、秘密値は表示していない。Broker API 呼び出しも行っていない。

## 3. 今回禁止したこと

Phase14-B では以下を実行していない。

- Production 注文
- 本番 Broker API Write
- 実資金運用
- Demo Submit 実行
- Demo 注文実行
- Notification 実送信
- launchd / plist 変更
- AI 再学習
- Backtest / Simulation
- Legacy Runtime を正規フローとして復活させること
- Broker API 呼び出し

## 4. Demo Broker 環境確認

### 4.1 設定分類

Phase14-B では `load_broker_settings()` を使い、値を出さない形で設定分類のみ確認した。

確認結果:

```text
environment=demo
base_url_is_demo=true
base_url_is_production=false
auth_id_configured=true
private_key_file_configured=true
second_password_file_configured=true
readonly_smoke_enabled=true
readonly_allow_prod=false
session_cache_enabled=false
quote_symbol_limit=50
```

この確認は local config / environment の分類確認であり、Broker API への通信ではない。

### 4.2 Demo endpoint

Demo endpoint は次を正とする。

```text
https://demo-kabuka.e-shiten.jp/e_api_v4r9
```

Demo auth endpoint:

```text
https://demo-kabuka.e-shiten.jp/e_api_v4r9/auth/
```

Production endpoint は注文系では禁止する。

```text
https://kabuka.e-shiten.jp/e_api_v4r9
```

### 4.3 Production 到達禁止

Production endpoint / production credential / real order path への到達は禁止する。

確認すべき guard:

- `environment == "demo"`
- `base_url == DEMO_BASE_URL`
- `base_url != PROD_BASE_URL`
- `readonly_allow_prod == false`
- `production_order_allowed == false`
- Production endpoint では `CLMKabuNewOrder` を生成・送信しない
- Production credential を注文系処理に使わない

## 5. Runtime v2 から Demo Broker へ接続する入口

Runtime v2 から Demo Broker へ接続する場合の入口は、役割ごとに分離する。

### 5.1 ReadOnly 入口

ReadOnly では以下を確認する。

- cash
- buying power
- positions
- orders
- executions

既存の Tachibana Demo ReadOnly / Broker Snapshot 系は、ReadOnly CLMID allowlist、secret redaction、raw response 非保存、atomic snapshot の前提を持つ。

Runtime v2 では ReadOnly payload を `BrokerReadOnlyBundle` へ正規化し、Broker Order / Execution / Position / Cash を分離して扱う。

### 5.2 Demo Submit 入口

Demo Submit は Phase14-D 以降の対象であり、Phase14-B では実行しない。

設計上の入口:

```text
Runtime v2 Submit Runtime
↓
Approved Pending Order Plan
↓
Demo-only Order Command
↓
Tachibana Demo Order Adapter
↓
DemoOrderBrokerTransport
```

Demo Submit は非冪等処理である。Runtime v2 では Submit Runtime だけが Broker Order Submit の外部副作用を持つ。

## 6. ReadOnly で確認すべき項目

ReadOnly sync では以下を最低限確認する。

| 項目 | 用途 | 異常時 |
| --- | --- | --- |
| cash | 現金 evidence | REVIEW_REQUIRED / BLOCKED |
| buying power | BUY 上限 guard | REVIEW_REQUIRED / BLOCKED |
| positions | SELL 数量 guard / Asset evidence | REVIEW_REQUIRED / BLOCKED |
| orders | 注文状態 sync / duplicate guard | REVIEW_REQUIRED / BLOCKED |
| executions | 約定反映 / Ledger projection | REVIEW_REQUIRED / BLOCKED |

ReadOnly は再実行可能である。Submit / Broker Write は ReadOnly とは別責務である。

## 7. Demo Submit 前に必要な guard

Demo Submit 前には以下を必須 guard とする。

### 7.1 environment guard

`environment == "demo"` であることを確認する。

### 7.2 demo-only guard

base URL が demo endpoint であり、Production endpoint ではないことを確認する。

### 7.3 approval guard

BUY / SELL ともに Approval を必須とする。

Approval は以下と一致する必要がある。

- pending_plan_id
- approved_item_ids
- business_date
- target_session_date
- environment
- approval_hash
- approval expiry

### 7.4 pending-only submit guard

Submit 対象は `pending_order_plan/pending_order_plan.json` のみとする。

`order_plan/YYYY-MM-DD`、`approval_artifact/YYYY-MM-DD`、Report、Audit、History、Derived artifact から直接 Submit してはならない。

### 7.5 duplicate submit guard

以下を確認し、二重 Submit を防止する。

- 同じ pending_plan_id の submitted record が存在しない。
- 同じ pending_item_id の submitted record が存在しない。
- Broker open orders に同一候補が重複していない。
- Pending が CONSUMED / POST_SEND_UNKNOWN / EXPIRED / BLOCKED / REVIEW_REQUIRED ではない。

### 7.6 max order amount guard

BUY では以下を確認する。

- estimated_amount が上限を超えない。
- buying_power を超えない。
- cash / buying_power が unknown ではない。
- Safety が system fault を出していない。

### 7.7 sell quantity guard

SELL では以下を確認する。

- Broker ReadOnly positions に対象銘柄の保有がある。
- Pending SELL quantity が broker position quantity を超えない。
- Current Asset State と Broker Position が重大に乖離していない。
- position quantity unknown の場合は Submit しない。
- 保有数量超過 SELL は BLOCKED とする。

SELL は保有状態が source of truth である Broker と一致していることを前提にする。Runtime 内部の Asset が売却可能数量を示していても、Broker Position が不足していれば Broker を正とし、Submit しない。

## 8. BUY テストシナリオ

Phase14-D 以降で実行する BUY シナリオは以下とする。

```text
1. Broker ReadOnly で cash / buying_power / positions / orders / executions を確認
2. Current State Read
3. AI inference / Capital Allocation / Safety input を取得
4. Planning で BUY Order Plan を作成
5. Pending BUY へ promotion
6. Approval Request 作成
7. Manual Approval
8. Pending BUY が APPROVED であることを確認
9. Demo Submit guard を全て確認
10. Demo BUY Submit
11. Demo Broker Order Status Sync
12. Execution Reflection
13. Ledger Update
14. Asset Update
15. Reconcile
16. Report
17. Notification Payload
18. Audit
19. Manual Review
```

BUY Acceptance:

- Approval がない場合は BLOCKED。
- Pending 以外から Submit しない。
- buying_power 不足は BLOCKED。
- duplicate active order は REVIEW_REQUIRED または BLOCKED。
- BrokerOrder のみから Asset を作らない。
- Execution / Position / Cash evidence から Ledger / Asset へ反映する。

## 9. SELL テストシナリオ

Phase14 では SELL シナリオを必須対象とする。

```text
1. Broker ReadOnly で保有確認
2. Current State Read
3. Position Management AI / Safety input を取得
4. Planning で SELL Order Plan を作成
5. Pending SELL へ promotion
6. Approval Request 作成
7. Manual Approval
8. Pending SELL が APPROVED であることを確認
9. sell quantity guard を確認
10. Demo SELL Submit
11. Demo Broker Order Status Sync
12. Execution Reflection
13. position quantity reduction を Ledger / Asset に反映
14. cash update を Ledger / Asset に反映
15. realized PnL が Broker / execution evidence から取得可能なら記録
16. Reconcile
17. Report
18. Notification Payload
19. Audit
20. Manual Review
```

SELL Acceptance:

- Broker Position がない銘柄は SELL しない。
- SELL quantity は Broker Position quantity を超えない。
- position quantity unknown は BLOCKED。
- Approval がない場合は BLOCKED。
- Pending 以外から Submit しない。
- 二重 Submit しない。
- 約定後は position quantity reduction と cash update を確認する。
- BrokerOrder のみから Asset を作らない。
- Execution / Position / Cash evidence から Ledger / Asset へ反映する。

## 10. BUY / SELL 混在シナリオ

BUY / SELL 混在テストでは、同一 business date で次を確認する。

- BUY と SELL の Pending item が同じ plan に含まれても、item ごとの Approval が必要である。
- BUY と SELL の estimated amount / sell quantity guard が個別に評価される。
- SELL による cash increase を同一 run 内の BUY buying_power に即時利用する場合は、Broker evidence と Reconcile が必要である。
- 同一銘柄の BUY / SELL が同時に出る場合は REVIEW_REQUIRED とする。
- cross order、opposite side duplicate、wash-like pattern は REVIEW_REQUIRED とする。
- Ledger は BUY / SELL の order / execution / position / cash record を分離して記録する。
- Report は BUY と SELL を分離して表示する。

## 11. 異常系

Phase14-B で定義する異常系は以下である。

| 異常 | 期待状態 |
| --- | --- |
| insufficient cash | BLOCKED |
| insufficient buying power | BLOCKED |
| insufficient position quantity | BLOCKED |
| position quantity unknown | BLOCKED |
| stale pending | BLOCKED / REVIEW_REQUIRED |
| consumed pending | BLOCKED |
| post_send_unknown | REVIEW_REQUIRED |
| broker order status unknown | REVIEW_REQUIRED |
| broker snapshot stale | REVIEW_REQUIRED / BLOCKED |
| duplicate active order | REVIEW_REQUIRED / BLOCKED |
| approval mismatch | BLOCKED |
| production endpoint detected | BLOCKED |
| production credential in order path | BLOCKED |
| raw response / secret persistence suspicion | REVIEW_REQUIRED / BLOCKED |

異常系では、自動 Submit、自動再送、自動復旧を行わない。

## 12. Phase14-C 以降の実行順序案

Phase14-C 以降は、以下の順序で進める。

### Phase14-C: Runtime v2 Dry-run with Real Current State

- Demo Broker ReadOnly sync
- Current State Read
- BUY / SELL plan dry-run
- Pending promotion dry-run
- Approval prepare
- Submit preflight
- Reconcile / Report / Audit
- Demo Submit はしない

### Phase14-D: Demo BUY Single-order Guarded Test

- Pending BUY
- Manual Approval
- Demo-only guard
- duplicate guard
- max order amount guard
- Demo BUY Submit
- Order Status Sync
- Execution Reflection
- Ledger / Asset / Reconcile / Report / Audit

### Phase14-E: Demo SELL Single-order Guarded Test

- Broker Position 確認
- Pending SELL
- Manual Approval
- sell quantity guard
- Demo SELL Submit
- Order Status Sync
- Execution Reflection
- position quantity reduction
- cash update
- realized PnL if available
- Ledger / Asset / Reconcile / Report / Audit

### Phase14-F: BUY / SELL Mixed Manual Rehearsal

- BUY / SELL mixed pending
- item-level Approval
- same-symbol opposite-side review
- Ledger / Asset 分離確認
- Report / Audit 確認

### Phase14-G: Multi-day Operation Rehearsal

- Day N order / execution / asset
- Day N+1 Current State Read
- consumed pending no-resubmit
- open order carry-over
- partial fill carry-over
- cash / position carry-over

### Phase14-H: Production Readiness Review

- Demo rehearsal 結果監査
- Production 禁止継続確認
- launchd 再開条件整理
- notification send 条件整理
- Production 注文解禁条件整理

Phase14-H でも Production 注文は実行しない。Production 解禁は別途明示的な承認と Acceptance が必要である。

## 13. Acceptance Criteria Review

| Criteria | Result |
| --- | --- |
| Demo 環境であることを確認する手順が明記されている | PASS |
| Production endpoint / production credential / real order path が禁止されている | PASS |
| BUY シナリオが定義されている | PASS |
| SELL シナリオが定義されている | PASS |
| SELL では保有数量超過を禁止する設計になっている | PASS |
| BUY / SELL 両方で Approval 必須になっている | PASS |
| BUY / SELL 両方で Pending のみ Submit 対象になっている | PASS |
| BUY / SELL 両方で二重 Submit 禁止になっている | PASS |
| BrokerOrder のみから Asset を作らない | PASS |
| Execution / Position / Cash evidence から Ledger / Asset へ反映する | PASS |
| 異常系は REVIEW_REQUIRED または BLOCKED に止める | PASS |
| Phase14-C 以降の実行順序が明記されている | PASS |
| 今回 Demo Submit は実行していない | PASS |

## 14. Phase14-B 実施内容

実施したこと:

- Phase14-A 設計の確認
- broker settings の静的分類確認
- demo / production endpoint guard の確認
- ReadOnly allowlist / forbidden CLMID / demo order CLMID guard の確認
- Runtime v2 Pending / Approval model の確認
- Demo Order Adapter / Transport の demo-only guard 確認
- BUY / SELL / mixed / abnormal scenario 設計
- Markdown 資料作成
- JSON レポート作成

実施していないこと:

- Broker API 呼び出し
- Demo Submit
- Demo 注文
- Production 注文
- 通知送信
- launchd / plist 変更
- AI 再学習
- Backtest / Simulation
- テストスイート実行

## 15. Final Decision

```text
PHASE14B_PREFLIGHT_COMPLETE
```

理由:

- 現在の設定分類では `environment=demo`、demo base URL、production base URL 不使用、`readonly_allow_prod=false` を確認した。
- Demo credential / key / second password file は設定済みとして分類できたが、秘密値は表示していない。
- Runtime v2 から Demo Broker へ接続する ReadOnly / Demo Submit の入口を整理した。
- BUY / SELL / BUY-SELL 混在シナリオを定義した。
- SELL では Broker Position を正とし、保有数量超過を BLOCKED にする設計を明記した。
- BUY / SELL ともに Approval、Pending-only Submit、duplicate submit guard を必須化した。
- 異常系を REVIEW_REQUIRED または BLOCKED に止める設計を明記した。
- Phase14-C 以降の実行順序を明記した。
- Phase14-B では Demo Submit、Broker API 呼び出し、注文、通知送信、launchd / plist 変更を行っていない。
