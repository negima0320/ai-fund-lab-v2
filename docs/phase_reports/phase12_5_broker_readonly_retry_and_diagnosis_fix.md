# Phase12.5 Broker ReadOnly Retry / Safe Diagnosis Fix

作成日: 2026-07-03

## Root Cause

Day1ではSubmitのDemo注文APIは成功し、Web画面上も約定していた一方、08:25のBroker read-only snapshotが `FAILED_CONFIGURATION / login_session_error` で停止していた。

コード上の主因は次の2点。

- `run_tachibana_broker_snapshot()` がlogin/session取得失敗を短期retryせず、`BrokerConfigurationError` として `FAILED_CONFIGURATION` に畳んでいた。
- Fill Monitorは `submitted_orders` にaccepted注文がある状態でも、Broker read-only artifact bundleがmissing/incompleteのまま `fill_events` を生成でき、結果としてRuntime約定確認不能がPASS相当に見え得た。

実行環境のstatic config不足ではなく、login ack / session URL decrypt / session URL取得系の一時失敗をRuntimeが吸収・診断できない設計不足として修正した。

## 修正内容

### ReadOnly login/session retry

`src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py` にlogin/session専用の短期retryを追加した。

- default max attempts: 3
- default backoff: 2.0 seconds
- retry対象: `_classify_failure(...) == "login_session_error"` のみ
- static config不足やdemo guard違反はretryしない
- retry後成功時はsnapshot/reportを通常通り生成し、`health.login.retry_attempts` を記録
- retry全失敗時は `FAILED_LOGIN_SESSION`

### Safe Diagnosis保存

失敗時の `broker_readonly_snapshot_report.json` に `safe_diagnosis` を追加した。

保存する情報:

- `failure_stage`
- `safe_error_class`
- `login_result_code_present`
- `login_result_code_zero`
- `session_url_field_present`
- `decrypt_attempted`
- `decrypt_success`
- `retry_attempts`
- `final_failure_classification`
- `attempts`

保存しない情報:

- secret
- raw request
- raw response payload
- 認証ID
- 完全URL
- 復号後URL

### Classification変更

分類を次のように分離した。

- `FAILED_CONFIGURATION`: env/file missing, invalid config, demo guardなど
- `FAILED_LOGIN_SESSION`: login/session取得失敗
- `FAILED_BROKER_READONLY_FETCH`: snapshot取得・HTTP系失敗
- `FAILED_BROKER_READONLY_PARSE`: parse/normalize/decode系失敗

### Fill Monitor判定変更

`src/ai_fund_lab_v2/operations/operations.py` の `run_fill_monitor()` で、Demoかつsubmitted live orderがあり、Broker read-only bundleが不完全な場合にFill Monitor開始時点でread-only refreshを再試行するようにした。

再取得後も `broker_orders` / `broker_executions` / `broker_positions` がmissing/incompleteの場合:

- `status = REVIEW_REQUIRED`
- `classification = REVIEW_REQUIRED`
- `review_reasons = ["broker_readonly_artifact_missing_or_incomplete"]`

ただし、submitted order由来の `ACCEPTED` lifecycle eventは残す。

## 変更ファイル

- `src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/broker/test_tachibana_phase10c_session_foundation.py`
- `tests/phase12/test_operations_fill_monitor_states.py`
- `docs/phase_reports/phase12_5_broker_readonly_retry_and_diagnosis_fix.md`
- `reports/phase_reports/phase12_5_broker_readonly_retry_and_diagnosis_fix.json`

## 実施テスト

実行:

```bash
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py::test_tachibana_broker_snapshot_retries_login_session_failure_then_writes_snapshot tests/broker/test_tachibana_phase10c_session_foundation.py::test_tachibana_broker_snapshot_login_session_retry_failure_safe_diagnosis tests/phase12/test_operations_fill_monitor_states.py::test_fill_monitor_reviews_submitted_orders_when_broker_readonly_refresh_still_missing
python3 -m pytest tests/phase12/test_operations_fill_monitor_states.py tests/phase12/test_operations_jquants_broker_mainline_integration.py::test_broker_readonly_artifacts_are_redacted_and_feed_preflight_safety_fill_reconcile
python3 -m pytest tests/broker/test_tachibana_phase10c_session_foundation.py
```

結果:

- 3 passed
- 5 passed
- 90 passed

## Production接続・注文

今回の検証はmock/monkeypatch中心の単体テストのみ。

- Production接続なし
- Production注文なし
- 実Broker発注なし
- Submit再実行なし
- notification送信なし
- existing artifact削除なし
- raw request/response保存なし
- secret出力なし

## 残課題

- 次回実Runtimeで `FAILED_LOGIN_SESSION` が再発した場合、`safe_diagnosis.failure_stage` とattempt履歴で login ack / session URL missing / decrypt / fetch のどこかを確認する。
- Fill Monitor前refreshはDemo read-only再取得であり、Production注文経路には触れていない。Production read-only運用時の同等retry適用方針はPhase13前に明示する。
