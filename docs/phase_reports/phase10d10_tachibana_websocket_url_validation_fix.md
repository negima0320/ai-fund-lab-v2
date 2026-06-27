# Phase10-D10 Tachibana WebSocket URL Validation Fix

作成日: 2026-06-27

## 1. Summary

Phase10-D10 では、Phase10-D9 で残った `sUrlEventWebSocket` の validation failure を修正した。

今回の対象は login session 確定に必要な URL validation のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Official Check

公式 sample HTML は login 成功後、以下5つを復号して表示する。

```text
sUrlRequest
sUrlMaster
sUrlPrice
sUrlEvent
sUrlEventWebSocket
```

公式 `mfds_json_api_event.js` は `XMLHttpRequest` GET で `sUrlEvent` を使う。公式 sample 内では `sUrlEventWebSocket` は表示されるが、Phase10 初期の read-only login/logout smoke では使用されない。

## 3. Implemented

修正:

- URL validation を用途別に分離。
- `request_url / master_url / price_url / event_url` は `https://` のみ許可。
- `websocket_url` は `wss://` または `ws://` を許可。
- `websocket_url` は Phase10 初期では未使用のため、無効または空の場合は optional unavailable として session 確定を阻害しない。
- plaintext classifier に `wss/ws` の非値分類を追加。
- session repr / reports では URL 値を redaction 維持。

保存しないもの:

- raw response
- raw login ack
- raw virtual URL
- ciphertext value
- decrypted plaintext
- decrypted URL
- auth id value
- private key content

## 4. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d10_tachibana_demo_login_default_result.json
```

## 5. Explicit Live Smoke

明示フラグ付き demo login/logout smoke を 1 回だけ実行した。

結果:

```text
status=PASS
executed=true
environment=demo
```

保存先:

```text
reports/phase_reports/phase10d10_tachibana_demo_login_smoke_result.json
```

確認できたこと:

- login ack は正常。
- `sKinsyouhouMidokuFlg=0`。
- `sUrlRequest / sUrlMaster / sUrlPrice / sUrlEvent` は `https://` URL として validation passed。
- `sUrlEventWebSocket` は `wss://` URL として validation passed。
- demo login session が確定。
- logout cleanup が試行され、`PASS`。

## 6. Diagnosis Conclusion

D10 で `sUrlEventWebSocket` の validation failure は解消した。

原因は以下。

```text
sUrlEventWebSocket は HTTPS URL ではなく WebSocket URL 形式だった
```

Phase10-E では、account/balance read-only API の設計・mock・live smoke に進める。

## 7. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py -q
```

結果:

```text
53 passed
```

JSON validation:

- `reports/phase_reports/phase10d10_tachibana_websocket_url_validation_fix.json`
- `reports/phase_reports/phase10d10_tachibana_demo_login_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```
