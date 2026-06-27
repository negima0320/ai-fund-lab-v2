# Phase10-I Tachibana Realtime Quote Read-only Smoke

作成日: 2026-06-27

## 1. Summary

Phase10-I では、demo login/session/logout 基盤を使い、PRICE URL 経由で realtime quote read-only API を 1 回だけ実行した。

対象 CLMID:

```text
CLMMfdsGetMarketPrice
```

EVENT / WebSocket は使っていない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

今回の demo response は quote 0 件だったため、live result は `PASS_WITH_EMPTY_RESULT` とした。

## 2. Implemented

追加・修正:

- v4r9 codec に quote request / response key mapping を追加。
- `normalize_market_quotes()` を追加。
- `TachibanaReadOnlyClient.get_market_price()` を追加。
- `TachibanaReadOnlyClient.get_quotes()` を追加。
- realtime quote read-only smoke runner を追加。
- demo quote smoke CLI を追加。
- quote smoke の rate limit を 5 req/sec 以下に制限。
- raw response を保存せず、CLMID / result summary / normalized quote fields のみ保存。

## 3. Request Design

要求:

```text
sCLMID=CLMMfdsGetMarketPrice
sTargetIssueCode=7203,6758,9984
sTargetColumn=pDPP,tDPP:T,pDOP,pDHP,pDLP,pDV,pPRP
```

使用 transport:

```text
PRICE
```

Phase10-I では REQUEST / EVENT / WebSocket を quote 取得に使わない。

## 4. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10i_tachibana_realtime_quote_default_result.json
```

## 5. Explicit Live Smoke

明示フラグ付き demo realtime quote read-only smoke を 1 回だけ実行した。

実行フロー:

```text
login
session established
CLMMfdsGetMarketPrice via PRICE
logout
```

結果:

```text
status=PASS_WITH_EMPTY_RESULT
executed=true
run_count=1
environment=demo
login=PASS
session_established=true
logout=PASS
quote_count=0
```

保存先:

```text
reports/phase_reports/phase10i_tachibana_realtime_quote_smoke_result.json
```

## 6. Live Response Summary

保存した情報は normalized / sanitized summary のみ。

```text
quotes_api_called=true
quote_transport=PRICE
account_api_called=false
positions_api_called=false
orders_api_called=false
executions_api_called=false
websocket_used=false
raw_response_saved=false
paper_ledger_updated=false
broker_snapshot_updated=false
```

quote 件数:

```text
quote_count=0
```

`CLMMfdsGetMarketPrice` の response object は取得できた。今回の demo response は quote list が空で、normalized quotes は空配列として保存した。raw response は保存していない。

## 7. Security Notes

保存していないもの:

- raw response
- raw login ack
- raw virtual URL
- auth id
- private key content
- account id / customer id values
- Paper Ledger
- Broker Snapshot

## 8. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_tachibana_request_builder.py tests/broker/test_broker_allowlist.py tests/broker/test_broker_normalizer.py -q
```

結果:

```text
97 passed
```

JSON validation:

- `reports/phase_reports/phase10i_tachibana_realtime_quote_readonly_smoke.json`
- `reports/phase_reports/phase10i_tachibana_realtime_quote_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 9. Phase10-J Handoff

Phase10-J では Broker Snapshot 統合へ進める。

進む前に継続する制約:

- live order / cancel / correction / second password / `unlock_trade` は引き続き禁止。
- raw response は保存しない。
- Paper Ledger / Broker Snapshot への統合は Phase10-J で設計・実装する。
- realtime quote の AI 学習利用は禁止を継続する。
