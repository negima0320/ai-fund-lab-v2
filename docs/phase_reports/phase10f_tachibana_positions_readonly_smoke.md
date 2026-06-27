# Phase10-F Tachibana Positions Read-only Smoke

作成日: 2026-06-27

## 1. Summary

Phase10-F では、Phase10-D10 で確立した demo login/session/logout 基盤と Phase10-E の REQUEST URL 接続を使い、positions 系 read-only API を 1 回だけ実行した。

対象 CLMID:

```text
CLMGenbutuKabuList
CLMShinyouTategyokuList
```

orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Implemented

追加・修正:

- v4r9 codec に Phase10-F 対象 CLMID と positions list key mapping を追加。
- `TachibanaReadOnlyClient.get_positions()` を追加。
- positions read-only smoke runner を追加。
- demo positions smoke CLI を追加。
- cash / margin positions の normalized result serializer を追加。
- raw response を保存せず、CLMID / result summary / normalized position fields のみ保存。
- account/customer id らしき値は保存しない方針を test で固定。

## 3. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10f_tachibana_positions_default_result.json
```

## 4. Explicit Live Smoke

明示フラグ付き demo positions read-only smoke を 1 回だけ実行した。

実行フロー:

```text
login
session established
CLMGenbutuKabuList via request_url
CLMShinyouTategyokuList via request_url
logout
```

結果:

```text
status=PASS
executed=true
run_count=1
environment=demo
login=PASS
session_established=true
logout=PASS
```

保存先:

```text
reports/phase_reports/phase10f_tachibana_positions_smoke_result.json
```

## 5. Live Response Summary

保存した情報は normalized / sanitized summary のみ。

```text
positions_api_called=true
cash_positions_api_called=true
margin_positions_api_called=true
orders_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
paper_ledger_updated=false
broker_snapshot_updated=false
```

positions 件数:

```text
cash=0
margin=0
total=0
```

`CLMGenbutuKabuList` / `CLMShinyouTategyokuList` ともに response object は取得できた。今回の demo response では positions list は空で、normalized positions は空配列として保存した。raw response は保存していない。

## 6. Security Notes

保存していないもの:

- raw response
- raw login ack
- raw virtual URL
- auth id
- private key content
- account id / customer id values
- Paper Ledger
- Broker Snapshot

## 7. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_tachibana_request_builder.py tests/broker/test_broker_allowlist.py -q
```

結果:

```text
78 passed
```

JSON validation:

- `reports/phase_reports/phase10f_tachibana_positions_readonly_smoke.json`
- `reports/phase_reports/phase10f_tachibana_positions_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 8. Phase10-G Handoff

Phase10-G では orders read-only に進める。

進む前に継続する制約:

- live order / cancel / correction / second password / `unlock_trade` は引き続き禁止。
- raw response は保存しない。
- account/customer id は保存しない。
- Paper Ledger / Broker Snapshot は更新しない。
