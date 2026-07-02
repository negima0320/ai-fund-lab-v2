# Phase12-AO Operation Flow Integrity Guard

## Status

PHASE12AO_OPERATION_FLOW_INTEGRITY_GUARD_COMPLETE

追加機能ではなく、Daily Report / Audit / Notification の運用フロー整合性ガードを追加しました。Demo注文、Production注文、LINE/Discord実送信、AI再学習、Backtestは実施していません。

## Implemented Guards

### Operation Day Type

Daily Reportの前に以下へ分類します。

- `NORMAL_OPERATION_DAY`
- `MARKET_CLOSED_DAY`
- `RECOVERY_DAY`
- `INCOMPLETE_OPERATION_DAY`
- `REVIEW_REQUIRED_DAY`

通常ブログを許可するのは `NORMAL_OPERATION_DAY` のみです。

### Daily Report Prerequisite Guard

以下を確認します。

- market calendar
- market_refresh
- daily_plan
- order_plan
- approval_artifact
- submitted_orders
- fill_events
- safety_monitor
- reconciliation_result
- operation_audit
- feature artifact
- artifact date consistency
- Source of Truth consistency

営業日なのに `SKIPPED_MARKET_CLOSED` / missing / stale / mixed date がある場合、通常ブログを出さず、専用レポートに切り替えます。

### Report Output Mode

- `NORMAL_OPERATION_DAY`: Phase9 v4形式の通常ブログ
- `MARKET_CLOSED_DAY`: 休場日専用レポート
- `INCOMPLETE_OPERATION_DAY`: 運用未完了レポート
- `RECOVERY_DAY`: リカバリ専用レポート
- `REVIEW_REQUIRED_DAY`: 要確認レポート

通常日以外では Candidate Top50 / 翌営業日の購入予定候補Top5 / 本日注文の通常章を出しません。

### Source of Truth Enforcement

ANで追加した `OPERATIONS_SOURCE_OF_TRUTH` を、Report / Auditの前提条件に接続しました。

- submitted_orders: Brokerへ送信した注文
- broker_orders: Broker受付状態
- broker_executions: 約定の優先Source of Truth
- broker_positions: 現在保有
- broker_buying_power / account_summary: cash / buying power
- demo_ledger: Demo日次リセットをまたぐ永続履歴
- order_plan: 翌営業日候補
- approval_artifact: Approval
- safety_monitor: System Guard
- reconciliation_result: 日次照合

`order_plan` を本日注文・本日約定として使うことは禁止です。

### Date Consistency

以下の日付を比較します。

- report_date
- market_refresh_date
- order_plan_date
- approval_date
- submit_run_date
- order_plan_source_date
- approval_source_date
- broker_snapshot_date
- fill_events_date
- reconcile_date

翌朝submitの `submit_run_date=D+1, order_plan_source_date=D, approval_source_date=D` は許容します。それ以外の混在はREVIEW_REQUIRED相当です。

### Notification Mode

通知payloadにもday typeを持たせました。

- `NORMAL_OPERATION_SUMMARY`
- `MARKET_CLOSED_NOTICE`
- `RECOVERY_COMPLETE_NOTICE`
- `INCOMPLETE_OPERATION_REVIEW`
- `REVIEW_REQUIRED_NOTICE`

非通常日では `buy_candidates` / `sell_candidates` を空にし、通常運用サマリと誤認しないpayloadにします。

### Operation Audit

Auditに以下を追加しました。

- operation_day_type
- report_prerequisite_pass
- artifact_date_consistency_pass
- source_of_truth_consistency_pass
- normal_report_allowed
- candidate_top50_allowed
- next_day_candidates_allowed
- notification_mode
- operation_flow_integrity_guard

営業日で通常運用が未完了の場合は `REVIEW_REQUIRED` とします。`run_operation_audit.py` は `REVIEW_REQUIRED` でexit code 2です。

## 2026-07-01 Regeneration

2026-07-01はMarket Calendar false closed bugからのRecovery Dayとして再生成しました。

- operation_day_type: `RECOVERY_DAY`
- report_mode: `RECOVERY_REPORT`
- notification_mode: `RECOVERY_COMPLETE_NOTICE`
- daily_report_refs.status: `REVIEW_REQUIRED`
- normal_report_allowed: `false`
- candidate_top50_allowed: `false`
- next_day_candidates_allowed: `false`
- artifact_date_consistency_pass: `true`

再生成対象:

- `.runtime/operations/reports/2026-07-01/blog_draft.md`
- `.runtime/operations/reports/2026-07-01/public_report.md`
- `.runtime/operations/reports/2026-07-01/safety_report.md`
- `.runtime/operations/reports/2026-07-01/line_payload.json`
- `.runtime/operations/reports/2026-07-01/discord_payload.json`
- `.runtime/operations/daily_report_refs/2026-07-01/daily_report_refs.json`
- `.runtime/operations/audit_result/audit_result.json`

`.runtime/operations/reports` はiCloud配下へのsymlinkのため、レポート再生成のみ権限昇格で実行しました。通知送信はしていません。

## 2026-07-02 Submit Dry-run

`python3 scripts/run_demo_submit.py --trade-date 2026-07-02 --root .runtime/operations` をdry-runで実行しました。

- status: `PASS`
- order_plan_source_date: `2026-07-01`
- approval_source_date: `2026-07-01`
- buy_item_count: `5`
- broker_order_api_called: `false`
- clm_kabu_new_order_called: `false`
- demo_order_submitted: `false`

## Audit Result

`python3 scripts/run_operation_audit.py --root .runtime/operations` は `REVIEW_REQUIRED` でした。

理由: 最新manifestが2026-07-02の朝submit dry-runであり、2026-07-02の日中/夜ジョブ artifactsはまだ未生成のため `INCOMPLETE_OPERATION_DAY` と判定されます。これはAOの方針通り、営業日に通常運用未完了をPASSにしない挙動です。

## Tests

- `python3 -m pytest tests/phase12/test_daily_report_prerequisite_guard.py tests/phase12/test_operation_day_type_classification.py tests/phase12/test_artifact_date_consistency.py tests/phase12/test_recovery_day_report.py tests/phase12/test_market_closed_day_report.py tests/phase12/test_daily_report_writer_quality.py -q`: 12 passed
- `python3 -m pytest tests/phase12 -q`: 88 passed
- `env PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py scripts/run_operation_audit.py scripts/run_daily_report.py scripts/run_demo_submit.py`: PASS

## Safety Confirmation

- Demo注文: 実行していない
- Production注文: 実行していない
- Production Unlock: 実行していない
- LINE/Discord実送信: 実行していない
- AI再学習: 実行していない
- Backtest: 実行していない
- raw request / raw response / secret保存: 実行していない
- Phase9変更: 実行していない
- launchctl bootstrap / bootout: 実行していない

## Remaining Gaps

- 2026-07-02は朝submit dry-runのみ完了しており、当日の日中/夜ジョブは未完了です。そのためAuditは `INCOMPLETE_OPERATION_DAY` / `REVIEW_REQUIRED` になります。
- 過去の2026-06-30 notification artifactには `line_send_executed=true` / `discord_send_executed=true` が残っています。今回のAOでは新規実送信していません。
