# Tachibana Read-only API Design

作成日: 2026-06-27

## 1. Purpose

本書は Phase10-B の設計成果物として、立花証券 e 支店 API v4r9 の demo 環境 read-only 接続方針を確定する。

Phase10-B では実 API 接続、login/logout 実行、コード実装、`.env` 実値表示は行わない。

## 2. Confirmed References

確認した公開資料:

- `https://www.e-shiten.jp/e_api/`
- `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_sample.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_sample_board.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_com.js`
- `https://www.e-shiten.jp/e_api/mfds_json_api_request_post.js`

確認できた公式前提:

- v4r9 は 2026-05-16 リリース版。
- demo 環境 URL は `https://demo-kabuka.e-shiten.jp/e_api_v4r9/`。
- 本番環境 URL は `https://kabuka.e-shiten.jp/e_api_v4r9/`。
- 認証 I/F と REQUEST I/F は HTTPS GET / POST + JSON。
- 認証成功時に `REQUEST`, `MASTER`, `PRICE`, `EVENT`, `EVENT-WebSocket` の仮想 URL が返る。
- 業務機能は `REQUEST` 仮想 URL、時価情報機能は `PRICE` 仮想 URL、EVENT は `EVENT` 仮想 URL を使う。
- v4r9 認証は `sAuthId` を使い、サンプルでは `e_api_authid.txt` と秘密鍵で仮想 URL を復号する。
- REQUEST I/F は一問一答方式として扱う。
- 流量制限は秒 10 件。
- 注文入力機能には第二暗証番号が必要。

ローカル確認:

- demo / prod の認証ID関連ファイルはローカルに存在することをファイル名レベルで確認した。
- 秘密情報ファイルの中身は読んでいない。
- Phase10 初期対象は demo 環境のみ。

## 3. Non-goals

Phase10 read-only 設計では以下を行わない。

- 実買い
- 実売り
- 信用取引
- 発注 API 呼び出し
- 訂正 API 呼び出し
- 取消 API 呼び出し
- 一括取消 API 呼び出し
- 第二暗証番号検証
- `unlock_trade` 相当処理
- 自動売買
- live order CLI
- 秘密情報のログ出力
- `.env` 実値の Git 管理
- Paper Ledger / backtest / broker snapshot の AI 学習利用

## 4. Endpoint Model

### 4.1 Fixed Base URLs

Phase10 初期実装は demo のみ許可する。

```text
demo base:
  https://demo-kabuka.e-shiten.jp/e_api_v4r9/

demo auth endpoint:
  https://demo-kabuka.e-shiten.jp/e_api_v4r9/auth/
```

prod は設定値として表現可能にしても、Phase10 の live smoke では default deny とする。

```text
prod base:
  https://kabuka.e-shiten.jp/e_api_v4r9/
```

### 4.2 Virtual URLs

`CLMAuthLoginRequest` の正常応答から以下が返る。これらは秘密情報として扱う。

```text
sUrlRequest
sUrlMaster
sUrlPrice
sUrlEvent
sUrlEventWebSocket
```

Phase10 初期で使う仮想 URL:

```text
REQUEST:
  balance / positions / orders / order details

PRICE:
  realtime quote polling
```

Phase10 初期で使わない仮想 URL:

```text
MASTER:
  initial smoke対象外。必要なら Phase10 後半で銘柄名補完などに限定。

EVENT:
  初期実装対象外。常時接続・配信制御が必要なため Phase11 以降で再検討。

EVENT-WebSocket:
  初期実装対象外。
```

仮想 URL は snapshot / report / log / repr に保存しない。必要な内部保持は `repr=False` の session object のみに限定する。

## 5. Confirmed Read-only CLMIDs

### 5.1 Phase10 Initial Allowlist

Phase10-C 以降の初期 allowlist は以下に確定する。

| Category | CLMID | Virtual URL | Purpose |
|---|---|---|---|
| Auth | `CLMAuthLoginRequest` | auth endpoint | demo read-only session 開始 |
| Auth | `CLMAuthLogoutRequest` | REQUEST | best-effort session cleanup |
| Account | `CLMAuthLoginAck` | response only | account capability flags; response model only |
| Balance | `CLMZanKaiSummary` | REQUEST | 可能額サマリー |
| Balance | `CLMZanKaiKanougaku` | REQUEST | 買余力 |
| Positions | `CLMGenbutuKabuList` | REQUEST | 現物保有銘柄一覧 |
| Positions | `CLMShinyouTategyokuList` | REQUEST | 信用建玉一覧 read-only |
| Orders | `CLMOrderList` | REQUEST | 注文一覧 |
| Order details / executions | `CLMOrderListDetail` | REQUEST | 注文約定一覧詳細 |
| Realtime quote polling | `CLMMfdsGetMarketPrice` | PRICE | 時価情報問合取得 |
| Market price history | `CLMMfdsGetMarketPriceHistory` | PRICE | 蓄積情報問合取得 |

Notes:

- `CLMAuthLoginAck` は要求 CLMID ではなく login response の schema として扱う。
- `CLMOrderListDetail` の要求は `sOrderNumber` を使う。既存 skeleton の `issue_code/execution_day/order_status` 形式は Phase10-C で修正する。
- `CLMMfdsGetMarketPriceHistory` は Broker order history ではなく market price history である。Phase10 初期の Broker sync 必須 endpoint には含めず、quote validation 用の optional read-only とする。

### 5.2 Deferred Read-only Candidates

初期 smoke には含めないが、将来 read-only として検討可能な CLMID。

```text
CLMZanUriKanousuu
CLMZanKaiKanougakuSuii
CLMZanRealHosyoukinRitu
CLMZanShinkiKanoIjiritu
CLMMfdsGetMasterData
CLMSystemStatus
CLMDateZyouhou
CLMUnyouStatus
CLMUnyouStatusKabu
CLMMfdsGetIssueDetail
CLMMfdsGetSyoukinZan
CLMMfdsGetShinyouZan
CLMMfdsGetHibuInfo
```

これらは Phase10-C の初期 allowlist には入れない。必要になった時点で、用途、仮想 URL、保存項目、テストを追加してから allowlist に入れる。

## 6. Realtime Quote Design

### 6.1 Initial Design

Phase10 初期の realtime quote は `PRICE` 仮想 URL に対する `CLMMfdsGetMarketPrice` polling とする。

要求例の形:

```json
{
  "sCLMID": "CLMMfdsGetMarketPrice",
  "sTargetIssueCode": "6501,6502,6503",
  "sTargetColumn": "pDPP,tDPP:T,pPRP"
}
```

応答は `aCLMMfdsMarketPrice` 配列。

```json
{
  "sCLMID": "CLMMfdsGetMarketPrice",
  "aCLMMfdsMarketPrice": [
    {
      "sIssueCode": "6501",
      "pDPP": "value",
      "pPRP": "value",
      "tDPP:T": "value"
    }
  ]
}
```

Phase10-C では `sTargetColumn` を設定化する。初期値候補:

```text
pDPP,tDPP:T,pDOP,pDHP,pDLP,pDV,pPRP
```

実際に使う情報コードは Phase10-C の mock fixture で固定し、公式 EVENT I/F 資料に合わせて名称を注記する。

### 6.2 Limits

- 1 request 最大 120 銘柄。
- Phase10 初期の上限は安全側に 50 銘柄以下。
- REQUEST I/F と同様に一問一答として扱い、並列 quote polling は行わない。
- 秒 10 件の流量制限を超えない。

### 6.3 EVENT I/F

EVENT / WebSocket によるリアルタイム配信は Phase10 初期実装対象外。

理由:

- 常時接続である。
- 先要求は切断される仕様がある。
- 受信遅延や間引き処理が明記されている。
- Phase11 Safety Layer で扱う前に polling quote の正規化と freshness 判定を安定させるべき。

## 7. Login / Logout / Session Design

### 7.1 Login

`CLMAuthLoginRequest` は auth endpoint に送る。

要求:

```json
{
  "sCLMID": "CLMAuthLoginRequest",
  "sAuthId": "<redacted>"
}
```

実装時は v4r9 サンプルに合わせて以下共通項目も builder/transport が付与する。

```text
p_no
p_sd_date
```

認証成功時の virtual URL は登録済み公開鍵で暗号化されて返り、ローカル秘密鍵で復号して利用する設計とする。

### 7.2 Session Object

内部 session object は以下を保持するが、`repr`, log, report, snapshot には出さない。

```text
request_url
master_url
price_url
event_url
event_websocket_url
login_ack_metadata
created_at
environment
```

保存してよい session metadata:

```text
environment=demo
created_at
has_request_url=true/false
has_price_url=true/false
result_code
document_unread_flag
```

保存禁止:

```text
actual virtual URLs
auth id
private key
account id
token
cookie
second password
raw login ack
```

### 7.3 Session Refresh

公式仕様上、Phase10 では dedicated refresh endpoint は使わない。

方針:

- session refresh は in-place 更新しない。
- 仮想 URL が無効、閉局、認証失敗、logout 済み、多重認証疑いの場合は fail closed。
- 再ログインは明示的な live read-only smoke / sync run の先頭でのみ許可。
- 再ログインは既存仮想 URL を無効化し得るため、並行実行は禁止。

### 7.4 Logout

`CLMAuthLogoutRequest` は best-effort cleanup とする。

方針:

- read-only sync の最後に実行する。
- logout 失敗は secret を出さず warning 化。
- logout 失敗を理由に発注可能状態へ進めない。
- logout request/response は sanitized summary のみ保存する。

## 8. Forbidden CLMIDs / Operations

### 8.1 Explicit Denylist

Phase10 で明示禁止する CLMID:

```text
CLMKabuNewOrder
CLMKabuCorrectOrder
CLMKabuCancelOrder
CLMKabuCancelOrderAll
CLMAuthCheckSecondPassword
CLMAuthStkLoginRequest
```

理由:

- `CLMKabuNewOrder`: 新規注文。
- `CLMKabuCorrectOrder`: 訂正注文。
- `CLMKabuCancelOrder`: 取消注文。
- `CLMKabuCancelOrderAll`: 一括取消。
- `CLMAuthCheckSecondPassword`: 第二暗証番号確認であり、発注可能状態へ近づくため Phase10 read-only 外。
- `CLMAuthStkLoginRequest`: stock login 系であり Phase10 read-only 初期対象外。

### 8.2 Deny by Default

Phase10-C 以降の builder / transport は allowlist 方式とし、未定義 CLMID はすべて拒否する。

禁止 token 監査:

```text
new_order
correct_order
cancel_order
cancel_all
second_password
unlock_trade
place_order
submit_order
modify_order
trade_unlock
```

Tachibana 公式資料に `unlock_trade` という CLMID は確認していない。ただし、他 broker 用語としても Phase10 source / CLI / report に存在したら audit failure とする。

## 9. Secrets / Env / Local Config

### 9.1 Environment Variables

Phase10-C で `.env.example` に空値として追加する。

```text
TACHIBANA_API_ENV=demo
TACHIBANA_API_BASE_URL=https://demo-kabuka.e-shiten.jp/e_api_v4r9
TACHIBANA_API_AUTH_ID=
TACHIBANA_API_AUTH_ID_FILE=
TACHIBANA_API_PRIVATE_KEY_FILE=
TACHIBANA_API_PRIVATE_KEY_FORMAT=der
TACHIBANA_API_LOCAL_CONFIG_PATH=
TACHIBANA_API_TIMEOUT_SECONDS=30
TACHIBANA_API_RATE_LIMIT_PER_SECOND=5
TACHIBANA_API_READONLY_SMOKE_ENABLED=false
TACHIBANA_API_READONLY_ALLOW_PROD=false
TACHIBANA_API_SESSION_CACHE_ENABLED=false
TACHIBANA_API_QUOTE_SYMBOL_LIMIT=50
TACHIBANA_API_QUOTE_COLUMNS=pDPP,tDPP:T,pDOP,pDHP,pDLP,pDV,pPRP
```

`TACHIBANA_API_AUTH_ID` は直接指定可能にしてもよいが、推奨は `TACHIBANA_API_AUTH_ID_FILE` である。

### 9.2 Local Config

推奨配置:

```text
~/.config/aifundlab/tachibana/demo/
  e_api_authid.txt
  e_api_private_key.der
  tachibana_demo.local.json
```

`tachibana_demo.local.json` には path と environment だけを置く。認証IDや秘密鍵本文は入れない。

```json
{
  "environment": "demo",
  "base_url": "https://demo-kabuka.e-shiten.jp/e_api_v4r9",
  "auth_id_file": "~/.config/aifundlab/tachibana/demo/e_api_authid.txt",
  "private_key_file": "~/.config/aifundlab/tachibana/demo/e_api_private_key.der",
  "private_key_format": "der"
}
```

Phase10-B ではこのファイルの中身を作成・変更しない。

### 9.3 Secret Handling

読み取り許可は実装時の内部 loader のみ。

禁止:

- file content の print
- auth id の report 保存
- private key の report 保存
- virtual URL の report 保存
- raw login ack の保存
- raw request URL の保存
- `.env` 実値の commit

必須:

- `repr(settings)` は secret を出さない。
- exception message は `sanitize_text()` を通す。
- saved artifacts は `sanitize_mapping()` を通す。
- account ref が必要な場合は hash 化する。

## 10. Smoke / Test Policy

### 10.1 Pytest

通常 pytest は mock only。

追加するテスト:

- Phase10 allowlist exact set
- forbidden CLMID exact set
- `CLMOrderListDetail` request shape uses `sOrderNumber`
- `CLMMfdsGetMarketPrice` request shape
- `CLMMfdsGetMarketPriceHistory` request shape
- session object repr redaction
- auth id file loader redaction
- private key path loader redaction
- virtual URL redaction
- smoke default `SKIPPED`
- saved output secret canary scan

### 10.2 Live Read-only Smoke

CLI は Phase10-C 以降に追加するが、デフォルトは外部接続しない。

```bash
PYTHONPATH=src python3 scripts/smoke_tachibana_readonly_phase10.py \
  --runtime-dir .runtime \
  --reports-dir reports/phase_reports
```

期待結果:

```text
status=SKIPPED
executed=false
login_executed=false
logout_executed=false
snapshot_written=false
```

live demo read-only 実行には明示フラグを必須にする。

```bash
PYTHONPATH=src python3 scripts/smoke_tachibana_readonly_phase10.py \
  --run-live-readonly \
  --environment demo \
  --runtime-dir .runtime \
  --reports-dir reports/phase_reports
```

prod 実行は Phase10 では禁止。将来も `--allow-prod-readonly` のような別フラグを要求する。

## 11. Snapshot / Reconciliation Policy

Phase10 read-only sync は以下を保存する。

```text
.runtime/broker/snapshots/accounts/
.runtime/broker/snapshots/balance/
.runtime/broker/snapshots/positions/
.runtime/broker/snapshots/orders/
.runtime/broker/snapshots/executions/
.runtime/broker/snapshots/quotes/
.runtime/broker/sync_results/
```

保存は normalized snapshot のみ。raw payload はデフォルト保存しない。

Reconciliation は report-only:

- Tachibana snapshot と Paper Ledger を比較する。
- Broker を正とする。
- mismatch は `WARNING` または `HALT_CANDIDATE`。
- Paper Ledger は変更しない。
- OrderPlan は executable にしない。
- AI 学習入力に使わない。

## 12. Phase10-C and Later Implementation Order

### Phase10-C: Settings / Secrets / Allowlist

1. `.env.example` に空の Tachibana env を追加。
2. `BrokerSettings` を v4r9 auth id file / private key file 対応へ拡張。
3. allowlist に Phase10 initial read-only CLMID を追加。
4. denylist に Phase10 forbidden CLMID を追加。
5. sanitizer に virtual URL / private key path / auth file key の canary を追加。
6. pytest mock only。

### Phase10-D: Request Builder / Session Model

1. `p_no`, `p_sd_date` を付与する builder を追加。
2. `CLMOrderListDetail(sOrderNumber)` に修正。
3. quote request builder を追加。
4. session dataclass を追加し `repr` redaction を徹底。
5. login ack normalizer を追加。

### Phase10-E: Transport Mock and Live Transport Skeleton

1. mock transport で compressed/uncompressed response を扱える境界を作る。
2. live transport skeleton を追加するが、pytest では使わない。
3. live smoke CLI は default `SKIPPED`。
4. actual network call は explicit flag のみ。

### Phase10-F: Normalizers / Snapshot Writer

1. account capability snapshot。
2. balance snapshot。
3. cash / margin positions。
4. orders / order details / executions。
5. quote snapshot。
6. all-or-nothing write policy。

### Phase10-G: Demo Read-only Smoke

1. 明示フラグで demo login。
2. read-only endpoints を順次実行。
3. quote は少数銘柄で確認。
4. logout best effort。
5. sanitized report のみ保存。

### Phase10-H: Reconciliation Report

1. Tachibana snapshot bundle loader。
2. Paper Ledger との report-only comparison。
3. mismatch classification。
4. Phase9 artifact は変更しない。

### Phase10-I: No-live-order Audit

1. forbidden CLMID audit。
2. forbidden token audit。
3. live order CLI absence audit。
4. secret canary audit。
5. smoke default skip audit。

## 13. Acceptance Criteria

Phase10-C へ進む条件:

- 本書が作成済み。
- Phase10-B report が作成済み。
- JSON report が `python3 -m json.tool` で検証済み。
- secret canary 簡易検索済み。
- 実 API 接続、login/logout、発注、取消、実装が行われていない。

Phase10 全体完了条件:

- demo read-only login / logout PASS。
- account / balance / positions / orders / order detail snapshot PASS。
- quote polling PASS。
- secret redaction PASS。
- no-live-order audit PASS。
- Paper Ledger reconciliation は report-only で完了。
- Phase11 Safety Layer に進める。
