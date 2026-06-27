# Phase10-A Tachibana API Connection Investigation

作成日: 2026-06-27

## 1. Scope

Phase10-A は、立花証券 e 支店 API の read-only 接続を本格実装する前の現状調査と実装計画である。

追加前提:

- 立花証券 e 支店の口座開設は完了済み
- デモ口座用の設定ファイルはローカルに作成済み
- 認証ID関連ファイルもローカルに存在する
- Phase10 初期接続対象はデモ環境 read-only
- 秘密情報の中身は表示、ログ出力、レポート出力、Git管理しない
- Phase10-A ではローカル秘密情報ファイルの中身を読まない

今回実施したこと:

- 指定資料と `broker` / `order_manager` / `tests/broker` 周辺の読み取り
- Phase10 の read-only 接続方針整理
- secrets / session / snapshot / reconciliation / smoke / audit の計画作成
- 調査レポート作成

今回実施していないこと:

- コード実装
- `.env.example` 変更
- 実 API 接続
- login / logout 実行
- 発注 API 呼び出し
- 取消 API 呼び出し
- `unlock_trade`
- 自動売買
- Paper Trading / Ledger / Backtest 結果の AI 学習利用

## 2. Current State

### 2.0 Updated Premises

ユーザー追加前提により、Phase10 の最初の実接続対象は `demo` 環境 read-only とする。口座開設、デモ口座設定、認証ID関連ファイルはローカル準備済みとして扱う。

ただし、調査・設計・実装・smoke の全段階で、秘密情報の実値は stdout / stderr / log / report / snapshot / Git 管理対象へ出さない。Phase10-B 以降で設定ファイル discovery を実装する場合も、存在確認と path policy だけを扱い、内容の表示や report 保存は禁止する。

### 2.1 Roadmap / Phase Boundary

`docs/01_requirements/phase_roadmap.md` では Phase10 が `Tachibana Securities API Connection` として定義されている。想定スコープは、認証情報管理、secrets 管理、login/session、read-only 疎通、account / positions / orders / history / realtime quote、Broker Snapshot、Tachibana Broker Adapter、Paper Ledger reconciliation、no-live-order audit である。

同時に、Phase10 中の本番発注は原則禁止、Safety Layer なしでの実売買は禁止とされている。

### 2.2 Phase9 Handoff

`docs/phase_reports/phase9_completion_summary_and_phase10_handoff.md` では、Phase9 の 30 営業日 Paper Trading は継続中だが、Phase10 の read-only Broker 接続へ進むための運用基盤は整っていると整理されている。

重要な制約:

- Phase9 Paper Ledger / Unified Daily Runner は継続運用中
- Phase10 は read-only / dry-run / no-live-order 境界を厳守
- Broker注文、`unlock_trade`、実売買は禁止
- no-live-order audit が完了するまで本番注文は禁止

### 2.3 Existing Tachibana Broker Foundation

`src/ai_fund_lab_v2/broker/` には Phase2-B の Tachibana foundation が残っている。

既存コンポーネント:

- `settings.py`: `TACHIBANA_API_AUTH_ID`, `TACHIBANA_API_ENV`, `TACHIBANA_API_BASE_URL`, `TACHIBANA_API_TIMEOUT_SECONDS` を読む skeleton
- `allowlist.py`: read-only CLMID allowlist と order CLMID denylist
- `request_builder.py`: Tachibana request payload builder
- `client.py`: `TachibanaReadOnlyClient`
- `transport.py`: `BrokerTransport` protocol と `MockBrokerTransport`
- `response.py`: response envelope と safe repr
- `normalizer.py`: balance / positions / orders の normalized snapshot 変換
- `models.py`: common broker snapshot dataclasses
- `snapshot_writer.py`: `.runtime/broker/snapshots/` への sanitized JSON writer
- `sync.py`: mock broker sync runner
- `sanitizer.py`: auth id, URL, account id, password, token, cookie, second password などの redaction

既存 read-only CLMID:

```text
CLMAuthLoginRequest
CLMAuthLogoutRequest
CLMZanKaiSummary
CLMZanKaiKanougaku
CLMGenbutuKabuList
CLMShinyouTategyokuList
CLMOrderList
CLMOrderListDetail
```

既存 forbidden order CLMID:

```text
CLMKabuNewOrder
CLMKabuCorrectOrder
CLMKabuCancelOrder
```

Phase10 では、この skeleton を削除せず、live transport / session / smoke / quote / history / adapter を追加する候補として扱う。

### 2.4 Existing Tests

`tests/broker/` には以下の安全境界テストが存在する。

- Tachibana request builder が read-only payload を作る
- forbidden CLMID を拒否する
- mock client が transport 履歴を sanitized 保存する
- response repr が URL / account id を漏らさない
- broker sync が mock read-only flow を実行し snapshot を保存する
- snapshot output に secret canary が残らない
- moomoo Phase8-C の read-only smoke は明示フラグなしでは SKIP する
- moomoo account id は hash 化される
- Phase8/9 の no-live-order audit が forbidden token を検査する

Phase10 では、これらを Tachibana live-readonly 用に拡張する。

### 2.5 Order Manager / Safety Boundary

`order_manager` 側には Broker Snapshot loader、Paper Ledger、reconciliation、OrderPlan schema、dry-run orchestrator がある。

注意点:

- `OrderPlan` は現状 `broker == "moomoo"` を前提にする validation がある
- `reconcile_broker_snapshot_with_paper()` も `broker.balance.broker != "moomoo"` を invalid として扱う
- Phase10 で Tachibana snapshot を直接既存 Order Manager に流すと Phase9 Paper Trading を壊すリスクがある

Phase10 では、Tachibana Adapter と snapshot 保存を先に分離し、Paper Ledger reconciliation は read-only report として段階接続する。Order Manager の live order 経路は追加しない。

## 3. Environment Variables Proposal

Phase10-B 以降で `.env.example` に追加する候補。Phase10-A では未変更。

```text
TACHIBANA_API_ENV=demo
TACHIBANA_API_BASE_URL=https://demo-kabuka.e-shiten.jp/e_api_v4r9
TACHIBANA_API_AUTH_ID=
TACHIBANA_API_PASSWORD=
TACHIBANA_API_ACCOUNT_ID=
TACHIBANA_API_TIMEOUT_SECONDS=30
TACHIBANA_API_RATE_LIMIT_PER_MINUTE=60
TACHIBANA_API_CONNECT_RETRIES=0
TACHIBANA_API_READONLY_SMOKE_ENABLED=false
TACHIBANA_API_SAVE_RAW_SCHEMA=false
TACHIBANA_API_SESSION_CACHE_ENABLED=false
TACHIBANA_API_SESSION_CACHE_PATH=.runtime/broker/tachibana/session.local.json
TACHIBANA_API_QUOTE_MODE=rest
TACHIBANA_API_QUOTE_SYMBOL_LIMIT=50
```

方針:

- `TACHIBANA_API_AUTH_ID`, password, account id, token, session URL は `repr`, stdout, stderr, log, report に出さない
- `.env` / `.env.*` は `.gitignore` により Git 管理外
- `.env.example` には空値のみ
- session cache を使う場合も `.runtime/` 配下に限定し、保存内容は必要最小限かつ sanitized manifest とは分離する

## 4. Secrets Policy

Secrets 保存方針:

- 実値は `.env` または OS 環境変数のみ
- Git 管理対象へ実値を書かない
- `.runtime/broker/` に保存する snapshot / report / manifest は sanitized 済みに限定
- session URL / request URL / cookie / token / account id は raw 保存しない
- account 識別が必要な場合は `acct_hash_<sha256 prefix>` 形式へ変換
- raw API payload の丸ごと保存はデフォルト禁止

実装時に追加するテスト:

- `repr(settings)` に secret が出ない
- request / response / exception / sync result / smoke report に secret canary が残らない
- `.runtime/broker/` の保存物全文検索で secret canary が検出されない
- account id は plain text ではなく hash 化される

## 5. Read-only Endpoint Candidates

既存設計と実装済み skeleton から、最初に扱う候補は以下。

| Purpose | Candidate CLMID | Status |
|---|---|---|
| login | `CLMAuthLoginRequest` | builder skeleton exists; Phase10-B で live session 設計後に明示 smoke のみ |
| logout | `CLMAuthLogoutRequest` | builder skeleton exists; session cleanup 用 |
| balance/account summary | `CLMZanKaiSummary` | normalizer exists |
| buying power | `CLMZanKaiKanougaku` | normalizer exists |
| cash positions | `CLMGenbutuKabuList` | normalizer exists |
| margin positions | `CLMShinyouTategyokuList` | normalizer exists |
| active/recent orders | `CLMOrderList` | normalizer exists |
| order details/history candidate | `CLMOrderListDetail` | builder exists; execution/history 正規化は拡張が必要 |

Realtime quote は repo 内に Tachibana quote CLMID が未定義である。Phase10-B の設計 doc で e_api_v4r9 公式リファレンスを再確認し、正確な quote endpoint / CLMID / response schema を確定してから allowlist に追加する。

Quote 方針:

- 最初は polling 型 read-only quote として扱う
- 発注判断には接続しない
- Phase11 Safety Layer の入力候補として snapshot / report に保存する
- API の push / callback / streaming が存在しても Phase10 初期では対象外
- quote 取得対象は保有銘柄 + Paper Ledger positions + pending candidates の限定リストから開始する

## 6. Session Design

Phase10-B の設計案:

1. `TachibanaSessionManager` を追加する
2. `login()` は明示 smoke または read-only sync の内部だけで呼ぶ
3. login response から session/request URL 等を受け取る場合、オブジェクト内では `repr=False`
4. snapshot / report には session material を保存しない
5. `logout()` は best-effort だが、失敗しても secret を出さず fail closed report にする
6. session cache は初期実装では default off
7. session cache を有効化する場合も `.runtime/broker/tachibana/*.local.json` のみ

Fail closed:

- auth id 不足: 実 API を呼ばず設定エラー
- login 失敗: read-only sync 中止、snapshot 書き込みなし
- read endpoint 失敗: 原則 sync 全体を `FAILED_READONLY_METHOD` とし、部分 snapshot は保存しない
- logout 失敗: warning report のみ。次の発注許可にはつながらない

## 7. Broker Adapter Design

Phase10 では以下の階層に分離する。

```text
Tachibana settings / secrets loader
  ↓
Tachibana live read-only transport
  ↓
Tachibana session manager
  ↓
Tachibana read-only client
  ↓
Tachibana normalizer
  ↓
Common Broker Snapshot
  ↓
Tachibana Broker Adapter report
  ↓
Reconciliation read-only report
```

Adapter は `BrokerSnapshot` 共通 dataclass に変換する。Tachibana raw response は common model へ混入させない。

保存先:

```text
.runtime/broker/snapshots/accounts/
.runtime/broker/snapshots/balance/
.runtime/broker/snapshots/positions/
.runtime/broker/snapshots/orders/
.runtime/broker/snapshots/executions/
.runtime/broker/sync_results/
.runtime/broker/logs/
reports/phase_reports/
```

## 8. Reconciliation Design

Phase10 の reconciliation は「実Brokerを正」とするが、Phase9 Paper Trading を壊さないため、初期は report-only とする。

比較対象:

- Tachibana Broker Snapshot: account / balance / positions / orders / executions
- Phase9 Paper Ledger: cash / positions / pending orders / executions

判定:

- `OK`: 差分なし
- `WARNING`: Paper と Broker が性質上違う、または history 不足
- `HALT_CANDIDATE`: Broker snapshot 不正、認証失敗、positions 不整合、想定外 open order、snapshot freshness 不明

重要:

- reconciliation 結果は OrderPlan を executable にしない
- Paper Ledger を Tachibana snapshot で上書きしない
- Paper Trading / Ledger / Backtest 結果を AI 学習に使わない
- Phase9 tracker / ledger / launchd は変更しない

## 9. Mock Test Policy

通常 `pytest` は mock 中心とする。

追加テスト候補:

- settings: required env missing / demo-prod base URL / repr redaction
- allowlist: Phase10 read-only CLMID exact set / forbidden order CLMID deny
- transport: payload sanitizer / timeout / non-2xx / malformed JSON
- session manager: login success / login failure / logout best-effort / no secret repr
- normalizer: account / balance / cash positions / margin positions / order detail / execution history
- snapshot writer: no raw payload / no secret canary / account hash
- smoke runner: explicit flagなしで `SKIPPED`
- no-live-order audit: forbidden tokens absent

Mock fixture は実 API response を直接保存せず、必要フィールドだけを最小 synthetic fixture として作る。

## 10. Live Smoke Test Policy

実 API smoke は通常 pytest から分離する。

想定 CLI:

```bash
PYTHONPATH=src python3 scripts/smoke_tachibana_readonly_phase10.py --runtime-dir .runtime --reports-dir reports/phase_reports
```

デフォルト挙動:

- 明示フラグなしでは `SKIPPED`
- 外部接続しない
- login しない
- snapshot を書かない

実行時の明示フラグ候補:

```bash
PYTHONPATH=src python3 scripts/smoke_tachibana_readonly_phase10.py \
  --run-live-readonly \
  --runtime-dir .runtime \
  --reports-dir reports/phase_reports \
  --continue-on-failure
```

Smoke report 方針:

- `status`, `executed`, `method_results`, `counts`, `snapshot_paths`, `manifest_paths` を保存
- secret / session / account id / raw payload は保存しない
- 1 endpoint でも失敗したら原則 `FAILED_READONLY_METHOD`
- 部分成功時に snapshot を書くかは Phase10-B の設計 doc で固定する。初期は「全部成功時のみ snapshot 保存」を推奨

## 11. No-live-order Audit Policy

Phase10 の audit は最低限以下を確認する。

- `CLMKabuNewOrder`, `CLMKabuCorrectOrder`, `CLMKabuCancelOrder` が denylist にある
- read-only allowlist が意図した CLMID のみ
- live order CLI が存在しない
- `unlock_trade` が存在しない
- order submit / cancel / modify 相当の関数名が Tachibana live-readonly source に存在しない
- smoke は明示フラグなしで `SKIPPED`
- `OrderPlan.live_order_allowed` は false
- approval は live order 許可にならない
- saved artifacts に secret canary が残らない
- `.env` 実値が Git 管理対象にならない

## 12. Phase10-B and Later Implementation Steps

### Phase10-B: Design Doc Update

- `docs/02_architecture/broker_integration_design.md` または新規 Tachibana Phase10 design を更新
- e_api_v4r9 公式リファレンスで read-only endpoint と quote endpoint を確定
- request / response schema、session material、保存禁止項目を固定

### Phase10-C: Settings / Secrets / Sanitizer

- `.env.example` に空の Tachibana env を追加
- settings model 拡張
- sanitizer canary 追加
- secret leak tests 追加

### Phase10-D: Live Read-only Transport / Session

- HTTP transport 実装
- session manager 実装
- login/logout は explicit smoke 内のみに限定
- pytest は fake transport のみ

### Phase10-E: Account / Balance / Positions / Orders / History

- account snapshot model mapping
- balance / positions / orders / order detail / executions normalizer 拡張
- all-or-nothing snapshot write policy
- sync result 保存

### Phase10-F: Realtime Quote Read-only

- 公式 quote endpoint 確定後に allowlist 追加
- quote snapshot model 追加、または separate quote report として保存
- Phase11 Safety Layer 入力候補として freshness / stale 判定を設計

### Phase10-G: Tachibana Broker Adapter

- common Broker Snapshot へ変換
- moomoo / Tachibana の adapter 境界整理
- Order Manager への直接 live order 接続は追加しない

### Phase10-H: Reconciliation Report

- Tachibana snapshot と Paper Ledger の report-only reconciliation
- mismatch は HALT_CANDIDATE へ寄せる
- Paper Ledger は変更しない

### Phase10-I: Live Read-only Smoke

- 明示フラグ付き CLI のみ
- 通常 pytest から分離
- smoke report は sanitized JSON のみ
- raw payload 保存はデフォルト禁止

### Phase10-J: No-live-order Audit

- forbidden token scan
- allowlist / denylist audit
- smoke skip audit
- saved artifact secret canary audit
- Phase11 へ進む判定資料作成

## 13. Risks / Open Questions

- Tachibana quote endpoint / CLMID は repo 内に未定義のため、実装前に公式リファレンスで確定が必要
- login response の session URL / token / cookie 仕様を確認するまで session cache は default off
- `OrderPlan` と reconciliation の moomoo 前提を Tachibana へ広げる際、Phase9 Paper Trading を壊さない段階設計が必要
- `CLMOrderListDetail` を history / executions としてどこまで扱えるかは response schema 確認が必要
- API rate limit / retry / logout best-effort の運用ルールは実 smoke 前に固定が必要

## 14. Decision

Phase10-A の結論:

```text
PHASE10A_INVESTIGATION_COMPLETE
```

理由:

- 既存 Tachibana skeleton は read-only foundation として再利用可能
- secrets redaction / snapshot writer / mock transport / allowlist は既に土台がある
- Phase10 では live transport と session manager を追加する前に設計 doc を更新すべき
- realtime quote は公式 endpoint 確認後に allowlist へ追加すべき
- no-live-order audit は Phase2 / Phase8 / Phase9 の既存監査方針を踏襲できる
- Phase9 Paper Trading は壊さず、Tachibana read-only は独立 adapter と report-only reconciliation から開始する
