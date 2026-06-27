# Phase10-J Tachibana Broker Snapshot Integration

作成日: 2026-06-27

## 1. Summary

Phase10-J では、Phase10-E から Phase10-I で確認した Tachibana demo read-only API を 1 つの Broker Snapshot に統合した。

統合対象:

```text
login/session/logout
account/balance
positions
orders
executions/history
realtime quote
broker health
```

発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理は実装・実行していない。Paper Ledger 更新、AI 学習処理、backtest も実行していない。

## 2. Implemented

追加・修正:

- Broker Snapshot schema `tachibana_broker_snapshot_v1` を追加。
- demo broker snapshot runner を追加。
- demo broker snapshot CLI を追加。
- account / positions / orders / executions / quotes の normalized payload を 1 snapshot に統合。
- broker health に各 API の status / latency_ms / count を記録。
- latest snapshot は一時ファイル経由で atomic replace する all-or-nothing write にした。
- raw response / virtual URL / secrets / account customer id / order number plaintext / execution id plaintext を保存しない redaction status を追加。

## 3. Snapshot Path

生成先:

```text
.runtime/broker/tachibana/demo/latest_broker_snapshot.json
```

Phase10-J では個別 snapshot writer の過去形式には書かず、Tachibana demo 統合 snapshot の latest JSON のみを生成した。

## 4. Default Run

明示フラグなしの default run を確認した。

結果:

```text
status=SKIPPED
executed=false
snapshot_written=false
```

保存先:

```text
reports/phase_reports/phase10j_tachibana_broker_snapshot_default_result.json
```

## 5. Explicit Demo Snapshot

明示フラグ付き demo broker snapshot integration を 1 回だけ実行した。

実行フロー:

```text
login
account/balance via REQUEST
positions via REQUEST
orders via REQUEST
executions/history skipped because order list was empty
realtime quote via PRICE
logout
atomic snapshot write
```

結果:

```text
status=PASS_WITH_WARNINGS
executed=true
run_count=1
environment=demo
snapshot_written=true
logout=PASS
```

`PASS_WITH_WARNINGS` の理由:

```text
executions=SKIPPED_NO_ORDERS
quotes=PASS_WITH_EMPTY_RESULT
```

## 6. Snapshot Summary

counts:

```text
positions=0
orders=0
executions=0
quotes=0
```

health:

```text
login=PASS
account=PASS
positions=PASS
orders=PASS
executions=SKIPPED_NO_ORDERS
quotes=PASS_WITH_EMPTY_RESULT
logout=PASS
```

## 7. Security Notes

保存していないもの:

- raw response
- raw login ack
- raw virtual URL
- auth identifier
- private secret
- account/customer id values
- order number plaintext
- execution id plaintext
- Paper Ledger
- AI learning artifacts

## 8. Verification

対象テスト:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_tachibana_request_builder.py tests/broker/test_broker_allowlist.py tests/broker/test_broker_normalizer.py -q
```

結果:

```text
102 passed
```

JSON validation:

- `reports/phase_reports/phase10j_tachibana_broker_snapshot_integration.json`
- `.runtime/broker/tachibana/demo/latest_broker_snapshot.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 9. Phase10-K Handoff

Phase10-K では no-live-order audit / Phase10 完了監査へ進める。

継続制約:

- live order / cancel / correction / second password / `unlock_trade` は引き続き禁止。
- Broker Snapshot を Paper Ledger 更新や AI 学習に使わない。
- raw response や秘密情報は保存しない。
