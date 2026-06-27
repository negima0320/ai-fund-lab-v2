# Phase10-C Tachibana Demo Login / Session Foundation

作成日: 2026-06-27

## 1. Summary

Phase10-C では、立花証券 e 支店 API demo 環境の login / session / logout 最小基盤を実装した。

今回の実装は demo read-only 接続基盤に限定し、account / positions / orders / quotes の取得、発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理は実装していない。

## 2. Implemented Scope

実装したもの:

- Tachibana settings 拡張
- demo/prod 分離
- demo-only guard
- local config path / auth id file / private key file 設定
- timeout / rate limit / read-only smoke flag / prod allow flag
- secret loader
- session dataclass
- login ack normalizer
- HTTP POST transport
- allowlist / denylist 更新
- demo login/logout smoke CLI
- mock tests

変更・追加した主なファイル:

- `src/ai_fund_lab_v2/broker/settings.py`
- `src/ai_fund_lab_v2/broker/secrets.py`
- `src/ai_fund_lab_v2/broker/session.py`
- `src/ai_fund_lab_v2/broker/crypto.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- `src/ai_fund_lab_v2/broker/client.py`
- `src/ai_fund_lab_v2/broker/allowlist.py`
- `src/ai_fund_lab_v2/cli/tachibana_demo_login_smoke.py`
- `tests/broker/test_tachibana_phase10c_session_foundation.py`
- `.env.example`

## 3. Secrets Handling

ローカル認証ファイル配置:

```text
/Users/negishi/.config/aifundlab/tachibana/demo
```

確認したファイル名:

```text
e_api_authid.txt
e_api_private_key.der
e_api_private_key.pem
e_api_public_key.pem
```

秘密情報の中身は表示していない。

Secret loader は以下を fail closed とする:

- auth id が env / file のどちらにも無い
- auth id file が存在しない
- auth id file が空
- private key file が存在しない
- private key file が読めない
- private key format が `der` / `pem` 以外

redact 対象:

- `sAuthId`
- auth id
- private key path / content related fields
- virtual URL fields
- request / price / event / websocket URL
- password / token / cookie / second password

## 4. Session Design

追加した session dataclass:

```text
TachibanaSession
```

保持する内部項目:

- `request_url`
- `master_url`
- `price_url`
- `event_url`
- `websocket_url`
- `login_at`
- `environment`

URL は `repr` に表示しない。report / CLI output / transport error でも保存しない。

session refresh は Phase10-C では未実装。仮想 URL 無効時は fail closed とし、再 login は明示 live smoke の開始時だけ行う設計とした。

## 5. Transport / Client

Transport:

- HTTP POST のみ担当
- mock transport と live HTTP transport を差し替え可能
- timeout 対応
- rate limit 対応
- JSON decode error / HTTP error は sanitized message に変換

Client:

- allowlist CLMID のみ実行
- unknown CLMID は deny by default
- forbidden CLMID は即 fail closed
- `login()` は `CLMAuthLoginRequest` だけを実行
- `logout()` は `CLMAuthLogoutRequest` だけを実行

## 6. Allowlist / Denylist

Phase10-C allowlist:

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

Phase10-C forbidden:

```text
CLMKabuNewOrder
CLMKabuCorrectOrder
CLMKabuCancelOrder
CLMKabuCancelOrderAll
CLMAuthCheckSecondPassword
CLMAuthStkLoginRequest
```

`unlock_trade` 相当処理は実装していない。

## 7. Live Smoke CLI

CLI:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_demo_login_smoke
```

default は `SKIPPED`。実 API 接続しない。

実行には以下が必要:

```text
--run-demo-login
TACHIBANA_API_READONLY_SMOKE_ENABLED=true
TACHIBANA_API_ENV=demo
demo base URL
```

CLI は account / positions / orders / quotes を取得しない。login と best-effort logout のみを対象とする。

## 8. Verification

対象テスト:

```text
python3 -m pytest tests/broker/test_broker_settings.py tests/broker/test_broker_allowlist.py tests/broker/test_broker_sanitizer.py tests/broker/test_tachibana_request_builder.py tests/broker/test_tachibana_client_mock.py tests/broker/test_mock_transport.py tests/broker/test_tachibana_phase10c_session_foundation.py
```

結果:

```text
40 passed
```

default smoke CLI:

```text
status=SKIPPED
executed=false
```

## 9. Not Done

Phase10-C で実施していないこと:

- 本番環境接続
- 実API login/logout 実行
- account 取得
- positions 取得
- orders 取得
- executions 取得
- realtime quote 取得
- 発注 API
- 訂正 API
- 取消 API
- 第二暗証番号 API
- `unlock_trade`
- Paper Ledger 更新
- Broker Snapshot 更新
- AI 学習処理変更
- backtest / Paper Ledger / broker snapshot / cash / portfolio / PnL の学習利用
- フルバックテスト
- フル pytest

## 10. Phase10-D Handoff

Phase10-D で進める候補:

1. read-only account API の mock fixture と normalizer を追加する。
2. demo account API smoke を default skipped のまま追加する。
3. session object を使った REQUEST virtual URL transport factory を整理する。
4. response schema の sanitized failure report を拡張する。
5. no-live-order audit をCI向けに独立テスト化する。
