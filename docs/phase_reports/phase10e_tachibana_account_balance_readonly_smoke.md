# Phase10-E Tachibana Account / Balance Read-only Smoke

作成日: 2026-06-27

## 1. Summary

Phase10-E では、Phase10-D10 で確立した demo login/session/logout 基盤を使い、REQUEST URL 経由で account / balance 系 read-only API を 1 回だけ実行した。

対象 CLMID:

```text
CLMZanKaiSummary
CLMZanKaiKanougaku
```

positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Implemented

追加・修正:

- v4r9 codec に Phase10-E 対象 CLMID と最小 balance field mapping を追加。
- `TachibanaReadOnlyClient.get_account_summary()` を追加。
- `TachibanaReadOnlyClient.get_available_cash()` alias を追加。
- account/balance read-only smoke runner を追加。
- demo account/balance smoke CLI を追加。
- normalized result serializer を追加。
- raw response を保存せず、CLMID / result summary / normalized money fields のみ保存。
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
reports/phase_reports/phase10e_tachibana_account_balance_default_result.json
```

## 4. Explicit Live Smoke

明示フラグ付き demo account/balance read-only smoke を 1 回だけ実行した。

実行フロー:

```text
login
session established
CLMZanKaiSummary via request_url
CLMZanKaiKanougaku via request_url
logout
```

結果:

```text
status=PASS
executed=true
environment=demo
login=PASS
logout=PASS
```

保存先:

```text
reports/phase_reports/phase10e_tachibana_account_balance_smoke_result.json
```

## 5. Live Response Summary

保存した情報は normalized / sanitized summary のみ。

```text
account_api_called=true
balance_api_called=true
positions_api_called=false
orders_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
paper_ledger_updated=false
broker_snapshot_updated=false
```

`CLMZanKaiSummary` / `CLMZanKaiKanougaku` ともに response object は取得できた。

今回の response では、既存 normalizer が認識する金額 field は出現せず、normalized money fields は `0` になった。raw response は保存していないため、次フェーズ以降で必要に応じて公式 field mapping を追加する。

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
74 passed
```

JSON validation:

- `reports/phase_reports/phase10e_tachibana_account_balance_readonly_smoke.json`
- `reports/phase_reports/phase10e_tachibana_account_balance_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 8. Phase10-F Handoff

Phase10-F では positions read-only に進める。

進む前に検討すること:

- `CLMZanKaiSummary` / `CLMZanKaiKanougaku` の公式 response field mapping を拡張するか。
- account/balance normalized money fields が 0 の理由を、raw値を保存しない形で key-level diagnosis するか。
- positions でも raw response 保存禁止と account/customer id redaction を継続する。
