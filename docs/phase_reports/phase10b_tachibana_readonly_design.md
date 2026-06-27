# Phase10-B Tachibana Read-only Design

作成日: 2026-06-27

## 1. Summary

Phase10-B では、立花証券 e 支店 API v4r9 の demo 環境 read-only 接続設計を確定した。

成果物:

- `docs/02_architecture/tachibana_readonly_api_design.md`
- `docs/phase_reports/phase10b_tachibana_readonly_design.md`
- `reports/phase_reports/phase10b_tachibana_readonly_design.json`

今回実施していないこと:

- 実 API 接続
- login/logout 実行
- 発注 API 実行
- 取消 API 実行
- コード実装
- `.env` 実値表示
- 秘密情報ファイル内容の読み取り
- Paper Ledger / backtest / broker snapshot の AI 学習利用

## 2. References Checked

公開資料:

- `https://www.e-shiten.jp/e_api/`
- `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_sample.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_sample_board.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_com.js`
- `https://www.e-shiten.jp/e_api/mfds_json_api_request_post.js`

ローカル:

- ワークスペース内には追加の立花 API 仕様書は見つからなかった。
- ローカルの demo / prod 認証ID関連ファイルはファイル名レベルで存在確認した。
- 秘密情報の中身は読んでいない。

## 3. Confirmed Endpoint Model

Phase10 初期対象:

```text
environment:
  demo

base URL:
  https://demo-kabuka.e-shiten.jp/e_api_v4r9/

auth endpoint:
  https://demo-kabuka.e-shiten.jp/e_api_v4r9/auth/
```

認証成功時に返る仮想 URL:

```text
sUrlRequest
sUrlMaster
sUrlPrice
sUrlEvent
sUrlEventWebSocket
```

Phase10 初期利用:

- `REQUEST`: balance / positions / orders / order details
- `PRICE`: quote polling

Phase10 初期対象外:

- `MASTER`
- `EVENT`
- `EVENT-WebSocket`

## 4. Confirmed Read-only CLMIDs

Phase10-C 初期 allowlist:

```text
CLMAuthLoginRequest
CLMAuthLogoutRequest
CLMZanKaiSummary
CLMZanKaiKanougaku
CLMGenbutuKabuList
CLMShinyouTategyokuList
CLMOrderList
CLMOrderListDetail
CLMMfdsGetMarketPrice
CLMMfdsGetMarketPriceHistory
```

Response-only schema:

```text
CLMAuthLoginAck
```

注意:

- `CLMOrderListDetail` は `sOrderNumber` 指定で設計する。既存 skeleton の `issue_code/execution_day/order_status` 形は Phase10-C で修正対象。
- `CLMMfdsGetMarketPriceHistory` は market price history であり、Broker order history ではない。

## 5. Realtime Quote

Realtime quote の初期設計は `PRICE` 仮想 URL に対する `CLMMfdsGetMarketPrice` polling とする。

要求項目:

```text
sCLMID=CLMMfdsGetMarketPrice
sTargetIssueCode=comma-separated issue codes
sTargetColumn=comma-separated information codes
```

応答:

```text
aCLMMfdsMarketPrice
```

初期制約:

- 公式上は最大 120 銘柄。
- AI Fund Lab では初期上限 50 銘柄。
- 並列 polling しない。
- 秒 10 件制限を守るため、初期 rate limit は 5 req/sec 以下。
- EVENT / WebSocket は Phase10 初期対象外。

## 6. Session Handling

v4r9 の login は `sAuthId` を使い、仮想 URL は暗号化されて返る。ローカル秘密鍵で復号する必要がある。

Phase10-C 以降の方針:

- auth id は file 読みを推奨。
- private key file は path のみ設定管理し、内容は表示しない。
- session object は `request_url`, `price_url` 等を内部保持するが `repr=False`。
- session refresh endpoint は使わない。
- 仮想 URL 無効時は fail closed。
- 再 login は明示 live read-only run の先頭だけ。
- logout は best-effort cleanup。

## 7. Forbidden CLMIDs

Phase10 明示禁止:

```text
CLMKabuNewOrder
CLMKabuCorrectOrder
CLMKabuCancelOrder
CLMKabuCancelOrderAll
CLMAuthCheckSecondPassword
CLMAuthStkLoginRequest
```

未知 CLMID は deny by default。

`unlock_trade` は Tachibana v4r9 資料内の CLMID としては確認していないが、Phase10 source / CLI / report に存在したら audit failure とする。

## 8. Secrets / Env / Local Config

Phase10-C で `.env.example` に空値として追加する候補:

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

推奨ローカル配置:

```text
~/.config/aifundlab/tachibana/demo/
```

保存禁止:

- auth id value
- private key content
- virtual URL
- raw login ack
- account id plaintext
- token / cookie / second password

## 9. Phase10-C Implementation Plan

1. `.env.example` に空の Tachibana env を追加。
2. `BrokerSettings` を auth id file / private key file / demo-only guard 対応へ拡張。
3. allowlist / denylist を Phase10-B の確定リストへ更新。
4. request builder に `p_no`, `p_sd_date`, quote, order detail by `sOrderNumber` を追加。
5. session dataclass と login ack normalizer を追加。
6. pytest は mock only。
7. live smoke CLI は default `SKIPPED`。
8. no-live-order audit を追加。

## 10. Phase10-D and Later

Phase10-D:

- live transport skeleton
- session manager
- redaction tests

Phase10-E:

- account / balance / positions / orders / executions / quotes normalizer
- snapshot writer extension for quotes

Phase10-F:

- demo read-only smoke with explicit flag
- all-or-nothing snapshot write

Phase10-G:

- report-only reconciliation with Paper Ledger
- no Paper Ledger mutation

Phase10-H:

- no-live-order audit
- secret canary audit
- Phase11 handoff

## 11. Decision

```text
PHASE10B_TACHIBANA_READONLY_DESIGN_COMPLETE
```

Phase10-C に進む前提:

- まず settings / secrets / allowlist / builder / mock tests から実装する。
- live read-only smoke は明示フラグが入るまで必ず `SKIPPED`。
- demo 環境だけを対象にする。
- prod は Phase10 では default deny。
- 発注・訂正・取消・第二暗証番号・unlock_trade 相当処理は実装しない。
