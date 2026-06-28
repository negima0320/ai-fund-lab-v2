# Phase11-D Safety Report / Human Review Report

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: Safety Report / Human Review Queue writers for Phase11
- broker_api_connected: false
- login_logout_executed: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- clm_kabu_new_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- runtime_behavior_changed: false
- broker_snapshot_updated: false
- paper_ledger_updated: false
- cron_or_launchagent_registered: false
- ai_learning_updated: false

## 1. Summary

Phase11-D では、Phase11-B/C で作成した Safety Runtime と Hourly Position Monitor の結果を、人間が確認できる Safety Report / Human Review Queue として出力する仕組みを追加した。

今回の実装は report / review artifact writer のみであり、Broker API、WebSocket、Demo / Production 発注、自動売却、自動復帰、Runtime 本体の大規模変更は行っていない。

Safety Report / Human Review Queue は AI 学習データではない。運用監査、人間確認、安全停止判断のための成果物である。

## 2. Implemented Files

追加:

```text
src/ai_fund_lab_v2/safety_phase11/report_schema.py
src/ai_fund_lab_v2/safety_phase11/review_queue_writer.py
tests/safety_phase11/test_safety_report_writer.py
tests/safety_phase11/test_review_queue_writer.py
reports/phase_reports/phase11d_safety_report_and_human_review.json
```

更新:

```text
src/ai_fund_lab_v2/safety_phase11/report_writer.py
src/ai_fund_lab_v2/safety_phase11/__init__.py
```

## 3. Safety Report Output

出力先:

```text
reports/safety/phase11/
reports/safety/phase11/hourly_monitor/
```

出力内容:

- report_id
- business_date
- generated_at
- environment
- runtime_id
- current safety state
- overall decision
- next recommended safety state
- triggered guards
- blocked orders
- review required items
- emergency candidates
- individual crash summary
- market crash status
- recovery candidate status
- broker snapshot freshness
- quote freshness
- divergence summary
- duplicate order summary
- daily loss summary
- recommended human actions
- allowed actions
- blocked actions
- no-live-order confirmation
- auto_sell_executed=false
- auto_recovery_executed=false
- secret / raw payload persistence confirmation

Markdown 版も出力可能にした。

```text
reports/safety/phase11/YYYY-MM-DD_safety_report.json
reports/safety/phase11/YYYY-MM-DD_safety_report.md
```

## 4. Human Review Queue

出力先:

```text
reports/safety/phase11/review_queue/
.runtime/safety/phase11/review_queue/
```

Review Queue 項目:

- review_id
- event_id
- business_date
- environment
- runtime_id
- guard
- severity
- decision
- affected issue code
- reason_code
- message
- recommended human action
- allowed actions
- blocked actions
- safety report path
- requires manual approval
- auto_trade_executed=false
- raw_response_saved=false

Review対象:

- STOP_LOSS_CANDIDATE
- EMERGENCY_CANDIDATE
- BUY_STOP transition
- RECOVERY_CANDIDATE
- Broker divergence
- duplicate order risk
- stale quote
- stale broker snapshot
- rejected / expired / canceled / unknown order state
- position mismatch

## 5. Sanitizer

Report / Review Queue / Event 保存前に Phase11 sanitizer を通す。

保存禁止:

```text
raw request
raw response
plaintext account id
plaintext order id
plaintext execution id
auth id
private key
virtual URL
second password
```

Safety Report では禁止キー名自体も極力残さないようにし、Review Queue で仕様上必要な `raw_response_saved=false` のみ明示する。

## 6. Test Coverage

実行した軽量テスト:

```text
PYTHONPATH=src python3 -m pytest tests/safety_phase11 -q
```

結果:

```text
33 passed
```

確認したこと:

- Safety Report JSON が生成される。
- Safety Report Markdown が生成される。
- Review Queue JSON が生成される。
- STOP_LOSS_CANDIDATE が Review 対象になる。
- EMERGENCY_CANDIDATE が Review 対象になる。
- RECOVERY_CANDIDATE が Review 対象になる。
- no-live-order confirmation が含まれる。
- auto_sell_executed=false。
- auto_recovery_executed=false。
- raw request / response や秘密情報が保存されない。
- blocked actions に BUY_STOP 時の新規買い禁止が含まれる。

## 7. Safety Confirmation

今回行っていないこと:

- Broker API接続
- Login / Logout
- WebSocket接続
- `CLMKabuNewOrder`
- Demo発注
- Production発注
- 自動売却
- 自動復帰
- Runtime本体への大規模変更
- Broker Snapshot更新
- Paper Ledger更新
- 長時間バックテスト
- フルテスト
- AI学習処理変更
- cron / LaunchAgent 登録

## 8. Result

判定:

```text
PHASE11D_SAFETY_REPORT_AND_HUMAN_REVIEW_COMPLETE
PHASE11E_READY_FOR_EMERGENCY_STOP
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
