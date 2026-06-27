# Phase10-D Tachibana Demo Login / Logout Live Smoke

作成日: 2026-06-27

## 1. Summary

Phase10-D では、Phase10-C の login / session / logout 基盤を使い、立花証券 API demo 環境への明示フラグ付き live smoke を 1 回だけ実行した。

今回の対象は demo login / session 正規化 / logout best-effort cleanup の疎通確認のみ。

account / positions / orders / executions / quotes は取得していない。発注、訂正、取消、第二暗証番号、`unlock_trade` 相当処理も実装・実行していない。

## 2. Pre-check

Phase10-C の実装差分を確認した。

主な確認対象:

- `src/ai_fund_lab_v2/broker/settings.py`
- `src/ai_fund_lab_v2/broker/secrets.py`
- `src/ai_fund_lab_v2/broker/session.py`
- `src/ai_fund_lab_v2/broker/crypto.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- `src/ai_fund_lab_v2/broker/client.py`
- `src/ai_fund_lab_v2/broker/tachibana_smoke.py`
- `src/ai_fund_lab_v2/cli/tachibana_demo_login_smoke.py`

ローカル認証ファイルはファイル名と存在のみ確認し、中身は表示していない。

## 3. Default Smoke

明示フラグなしの default smoke を確認した。

結果:

```text
status=SKIPPED
executed=false
```

保存先:

```text
reports/phase_reports/phase10d_tachibana_demo_login_default_smoke_result.json
```

default smoke では実 API 接続は行われていない。

## 4. Explicit Live Smoke

明示フラグ付き demo live smoke を 1 回だけ実行した。

実行条件:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true
TACHIBANA_API_ENV=demo
--run-demo-login
```

結果:

```text
status=FAILED_LOGIN_SESSION
executed=true
environment=demo
failure_classification=response_decode_error
```

保存先:

```text
reports/phase_reports/phase10d_tachibana_demo_login_live_smoke_result.json
```

login/session は fail closed したため、使用可能な session は確認できていない。logout は session 未確定のため未実行。

失敗分類:

```text
response_decode_error
```

分類内容:

```text
HTTP response body decode stage failed before JSON parse / session normalization.
```

raw login ack は保存していない。raw response も表示・保存していない。

## 5. Minimal Fix

live smoke の失敗分類を受け、transport に response decode fallback を追加した。

対応:

- `utf-8`
- `cp932`
- `shift_jis`

live smoke は 1 回だけという条件を守るため、修正後の実 API 再実行は行っていない。

## 6. Safety Confirmation

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

## 7. Verification

対象テスト:

```text
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_tachibana_client_mock.py tests/broker/test_mock_transport.py
```

結果:

```text
18 passed
```

JSON validation:

- `reports/phase_reports/phase10d_tachibana_demo_login_live_smoke.json`
- `reports/phase_reports/phase10d_tachibana_demo_login_live_smoke_result.json`
- `reports/phase_reports/phase10d_tachibana_demo_login_default_smoke_result.json`

secret canary:

```text
PASS
```

no forbidden CLMID audit:

```text
PASS
```

## 8. Phase10-E Handoff

Phase10-E に進む前に、Phase10-D live smoke をもう一度だけ手動で再実行し、decode fallback 後に login/session/logout が通るか確認するのが安全。

今回の Phase10-D run では session 未確定のため、account read-only API の live smoke はまだ開始しない。
