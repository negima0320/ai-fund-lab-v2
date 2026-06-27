# Phase10-G Tachibana Orders Read-only Smoke

作成日: 2026-06-27

## 1. Summary

Phase10-G では、demo login/session/logout 基盤を使い、orders 系 read-only API を 1 回だけ実行した。

対象 CLMID:

```text
CLMOrderList
CLMOrderListDetail
```

今回の demo response は注文 0 件だったため、`CLMOrderListDetail` は実行せず `SKIPPED_NO_ORDERS` として正常扱いにした。

executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Implemented

追加・修正:

- v4r9 codec に Phase10-G 対象 CLMID と orders field mapping を追加。
- `TachibanaReadOnlyClient.get_orders()` を追加。
- `TachibanaReadOnlyClient.get_order_detail(order_number)` を追加。
- order normalizer の `sOrder*` field 候補を拡張。
- orders read-only smoke runner を追加。
- demo orders smoke CLI を追加。
- order number はレポート保存時に hash 化し、平文保存しない方針を test で固定。
- raw response を保存せず、CLMID / result summary / normalized order fields のみ保存。

## 3. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10g_tachibana_orders_default_result.json
```

## 4. Explicit Live Smoke

明示フラグ付き demo orders read-only smoke を 1 回だけ実行した。

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
status=PASS
executed=true
run_count=1
environment=demo
login=PASS
session_established=true
logout=PASS
order_detail_status=SKIPPED_NO_ORDERS
```

保存先:

```text
reports/phase_reports/phase10g_tachibana_orders_smoke_result.json
```

## 5. Live Response Summary

保存した情報は normalized / sanitized summary のみ。

```text
orders_api_called=true
order_list_api_called=true
order_detail_api_called=false
positions_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
paper_ledger_updated=false
broker_snapshot_updated=false
```

orders 件数:

```text
list=0
detail=0
```

`CLMOrderList` の response object は取得できた。注文 0 件のため detail request は呼び出していない。raw response は保存していない。

## 6. Security Notes

保存していないもの:

- raw response
- raw login ack
- raw virtual URL
- auth id
- private key content
- order number plaintext
- account id / customer id values
- Paper Ledger
- Broker Snapshot

## 7. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_tachibana_request_builder.py tests/broker/test_broker_allowlist.py tests/broker/test_broker_normalizer.py -q
```

結果:

```text
86 passed
```

JSON validation:

- `reports/phase_reports/phase10g_tachibana_orders_readonly_smoke.json`
- `reports/phase_reports/phase10g_tachibana_orders_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 8. Phase10-H Handoff

Phase10-H では executions/history read-only に進める。

進む前に継続する制約:

- live order / cancel / correction / second password / `unlock_trade` は引き続き禁止。
- raw response は保存しない。
- order number plaintext は保存しない。
- Paper Ledger / Broker Snapshot は更新しない。
