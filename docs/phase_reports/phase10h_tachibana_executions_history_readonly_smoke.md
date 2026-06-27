# Phase10-H Tachibana Executions / History Read-only Smoke

作成日: 2026-06-27

## 1. Summary

Phase10-H では、公式リファレンスを確認したうえで、executions / history 系 read-only API の扱いを確定した。

結論:

```text
execution/history source CLMID = CLMOrderListDetail
prerequisite CLMID = CLMOrderList
standalone broker trade-history CLMID = not confirmed for Phase10 initial allowlist
CLMMfdsGetMarketPriceHistory = price history, not broker order/execution history
```

今回の demo response は注文 0 件だったため、`CLMOrderListDetail` は実行せず `SKIPPED_NO_ORDERS` とした。Phase10-H の live result は `PASS_WITH_EMPTY_RESULT` で完了した。

quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Official Reference Review

公式リファレンスで確認した対象:

- `CLMOrderList`: 注文一覧。
- `CLMOrderListDetail`: 注文約定一覧（詳細）。
- `aYakuzyouSikkouList`: 約定失効リスト。`CLMOrderListDetail` response 内の execution-like detail source。
- `aKessaiOrderTategyokuList`: 決済注文建株指定リスト。`CLMOrderListDetail` response 内の settlement-like detail source。
- `CLMMfdsGetMarketPriceHistory`: 蓄積情報問合取得。market price history であり、broker order/execution history ではない。

Phase10-H では、新規 CLMID を allowlist に追加しない。`CLMOrderListDetail` を、注文番号 `sOrderNumber` がある場合のみ execution/history detail source として使う。

## 3. Implemented

追加・修正:

- `normalize_order_detail_executions()` を追加。
- `TachibanaReadOnlyClient.get_executions_history(order_number)` を追加。
- executions/history read-only smoke runner を追加。
- demo executions/history smoke CLI を追加。
- order number / execution id はレポート保存時に hash 化し、平文保存しない方針を test で固定。
- raw response を保存せず、CLMID / result summary / normalized execution fields のみ保存。

## 4. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10h_tachibana_executions_history_default_result.json
```

## 5. Explicit Live Smoke

明示フラグ付き demo executions/history read-only smoke を 1 回だけ実行した。

実行フロー:

```text
login
session established
CLMOrderList via request_url
CLMOrderListDetail skipped because order list was empty
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
executions_detail_status=SKIPPED_NO_ORDERS
```

保存先:

```text
reports/phase_reports/phase10h_tachibana_executions_history_smoke_result.json
```

## 6. Live Response Summary

保存した情報は normalized / sanitized summary のみ。

```text
orders_api_called=true
order_list_api_called=true
order_detail_api_called=false
executions_api_called=false
positions_api_called=false
quotes_api_called=false
raw_response_saved=false
paper_ledger_updated=false
broker_snapshot_updated=false
```

counts:

```text
orders=0
executions=0
```

注文 0 件のため execution/history detail request は呼び出していない。raw response は保存していない。

## 7. Security Notes

保存していないもの:

- raw response
- raw login ack
- raw virtual URL
- auth id
- private key content
- order number plaintext
- execution id plaintext
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
91 passed
```

JSON validation:

- `reports/phase_reports/phase10h_tachibana_executions_history_readonly_smoke.json`
- `reports/phase_reports/phase10h_tachibana_executions_history_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 9. Phase10-I Handoff

Phase10-I では realtime quote read-only に進める。

進む前に継続する制約:

- live order / cancel / correction / second password / `unlock_trade` は引き続き禁止。
- raw response は保存しない。
- order number / execution id plaintext は保存しない。
- Paper Ledger / Broker Snapshot は更新しない。
