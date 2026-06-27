# Phase10-D2 Tachibana Demo Login / Logout Live Smoke Retry

作成日: 2026-06-27

## 1. Summary

Phase10-D2 では、Phase10-D で追加した response decode fallback 後に、立花証券 API demo 環境への login / logout live smoke を 1 回だけ再実行した。

今回の対象は demo login / session 正規化 / logout best-effort cleanup の再確認のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d2_tachibana_demo_login_default_smoke_result.json
```

default smoke では実 API 接続は行われていない。

## 3. Explicit Live Retry

明示フラグ付き demo live smoke を 1 回だけ実行した。

実行条件:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true
TACHIBANA_API_ENV=demo
--run-demo-login
```

結果:

```text
status=FAILED_CONFIGURATION
executed=true
environment=demo
failure_classification=login_ack_result_error
```

保存先:

```text
reports/phase_reports/phase10d2_tachibana_demo_login_live_smoke_result.json
```

decode fallback 後、前回の `response_decode_error` は再発していない。今回は login ack の結果判定で fail closed した。

session は未確定のため、logout は未実行。

raw login ack は保存していない。raw response も表示・保存していない。

## 4. Minimal Fix

失敗分類を `login_ack_result_error` として識別する最小修正を追加した。

live smoke は 1 回だけという条件を守るため、分類修正後の実 API 再実行は行っていない。

## 5. Safety Confirmation

確認結果:

- production 接続なし
- account API 呼び出しなし
- positions API 呼び出しなし
- orders API 呼び出しなし
- executions API 呼び出しなし
- realtime quote API 呼び出しなし
- 発注 API 呼び出しなし
- 訂正 API 呼び出しなし
- 取消 API 呼び出しなし
- 第二暗証番号 API 呼び出しなし
- `unlock_trade` 相当処理なし
- Paper Ledger 更新なし
- Broker Snapshot 更新なし
- AI 学習処理変更なし
- backtest 実行なし
- raw login ack 保存なし
- virtual URL 保存なし

## 6. Verification

対象テスト:

```text
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_mock_transport.py
```

結果:

```text
19 passed
```

JSON validation:

- `reports/phase_reports/phase10d2_tachibana_demo_login_live_smoke_retry.json`
- `reports/phase_reports/phase10d2_tachibana_demo_login_live_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 7. Phase10-D3 Handoff

Phase10-D3 は `login_ack_result_error` の原因を 1 つに絞る設計にする。

候補:

1. login ack の非秘密フィールドだけを保存する sanitized classifier を設計する。
2. `sResultCode` / `sResultText` を秘密情報と分離して扱えるか確認する。
3. raw login ack と仮想 URL は引き続き保存しない。
4. auth id / request shape / endpoint / p_no / p_sd_date のどれが原因か、mock と公開仕様だけで切り分けてから live 再実行を判断する。

Phase10-E account read-only live smoke にはまだ進まない。
