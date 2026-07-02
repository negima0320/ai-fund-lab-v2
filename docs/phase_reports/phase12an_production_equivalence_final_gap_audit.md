# Phase12-AN Production-equivalence Final Gap Audit / Source of Truth Fix

## Status

PHASE12AN_PRODUCTION_EQUIVALENCE_FINAL_GAP_AUDIT_COMPLETE

実注文、Production注文、LINE/Discord実送信、AI再学習、Backtestは実施していません。

## Source of Truth

Operations Runtimeでは、以下をSource of Truthとして固定しました。DemoとProductionでロジック層の解釈を変えず、Demo固有差分はDemo Special Fill Simulation、Persistent Demo Ledger、TACHIBANA_API_ENV=demo、Production order disabledに限定します。

- 本日Brokerへ送信した注文: `submitted_orders/YYYY-MM-DD/submitted_orders.json`
  - Order Planを本日注文扱いしない。
- Broker受付状態: `broker_orders/YYYY-MM-DD/orders.json`
  - Broker受付・注文状態の正。
- 約定: `broker_executions/YYYY-MM-DD/executions.json`
  - 無い場合のみ、`broker_orders` の `executed_quantity` / statusで補完する。
- 保有: `broker_positions/YYYY-MM-DD/positions.json`
  - Order PlanやSubmitted Ordersから保有を推定しない。
- Cash / buying power: `broker_buying_power/YYYY-MM-DD/buying_power.json` / `account_summary`
  - ProductionはBroker値優先。Demo評価表示は100万円基準のPersistent Demo Ledger評価を維持する。
- Persistent履歴: `.runtime/operations/demo_ledger/`
  - Tachibana Demoの日次リセットをまたぐ履歴。Broker Snapshotで全量上書きしない。
- 翌営業日候補: `order_plan/YYYY-MM-DD/order_plan.json`
  - 本日注文・本日約定として扱わない。
- Approval: `approval_artifact/YYYY-MM-DD/approval_artifact.json`
  - submit時に期限切れならBLOCKし、古いApprovalで発注しない。
- Safety: `safety_result` / `safety_monitor`
  - System Guardの正。投資判断やAI学習入力には使わない。
- Reconcile: `reconciliation_result/YYYY-MM-DD/reconciliation_result.json`
- Report: 上記SoTから派生生成
  - Order Planを本日約定扱いにしない。

コード上では `OPERATIONS_SOURCE_OF_TRUTH` を追加し、report writerの買付/売却実績欄は `fill_status in {FILLED, SIMULATED_FILLED}` のみを採用するよう修正しました。

## Date Resolution

- `run_market_refresh.py`: `--trade-date` 未指定時は当日。夜ジョブで当日market refreshを生成。
- `run_daily_plan.py`: 未指定時は当日。夜ジョブで当日Order Planを生成。
- `run_approval_prepare.py`: 未指定時は当日。夜ジョブで当日Approvalを生成。
- `run_preflight.py`: 未指定時は当日。朝ジョブで当日read-only/preflightを実行。
- `run_demo_submit.py`: submit_run_dateは当日。Order Plan / Approvalは同日が存在すれば同日、存在しなければprevious business dayを参照。
- `run_fill_monitor.py`: 未指定時は当日。当日注文・約定を監視。
- `run_demo_special_fill_simulation.py`: 未指定時は当日。対象外は正常no-op。
- `run_safety_monitor.py`: 未指定時は当日。
- `run_reconcile.py`: 未指定時は当日。
- `run_operation_audit.py`: `.runtime/operations` の最新manifest/artifactを監査。
- `run_daily_report.py`: 未指定時は当日。当日SoTからレポート生成。

2026-07-02朝のsubmit dry-runでは、`submit_run_date=2026-07-02`、`order_plan_source_date=2026-07-01`、`approval_source_date=2026-07-01` を確認しました。2026-06-30のOrder Planは参照されていません。

## Approval Expiry

2026-07-01 Approvalは `APPROVED` です。

- approval_id: `operation_approval_2026-07-01_d28a4d34e9c4`
- approval_expires_at: `2026-07-02T04:38:45.563582+00:00`
- JST換算: 2026-07-02 13:38:45

2026-07-02朝のsubmit windowをカバーします。期限切れ時はsubmit側でBLOCKし、古いApprovalでは発注しない方針です。

## Next Morning Dry-run

`python3 scripts/run_demo_submit.py --trade-date 2026-07-02 --root .runtime/operations` をdry-runで実行しました。

- status: PASS
- order_plan_source_date: 2026-07-01
- approval_source_date: 2026-07-01
- uses_previous_business_day_order_plan: true
- buy_item_count: 5
- broker_order_api_called: false
- clm_kabu_new_order_called: false
- demo_order_submitted: false
- production_order_submitted: false

BUY候補:

1. 42650 / 4265 / Institution for a Global Society / 100株
2. 41790 / 4179 / ジーネクスト / 100株
3. 29620 / 2962 / テクニスコ / 100株
4. 23930 / 2393 / 日本ケアサプライ / 100株
5. 61660 / 6166 / 中村超硬 / 100株

## Report Consistency

修正した漏れ:

- 本日約定欄がsubmitted/dry-runを拾い得る判定を廃止。
- 本日約定欄はFill SoTだけを見るよう修正。
- 翌営業日候補Top5はOrder Plan由来のまま維持。
- 保有銘柄はBroker Positions由来。
- 資産状況はDemo 100万円基準を維持。

2026-07-01の `public_report.md` は再生成済みです。`.runtime/operations/reports` はiCloud配下へのsymlinkのため、workspace sandbox外書き込みとして権限昇格で再生成しました。通知送信はしていません。

残ギャップ:

- 2026-07-01のCandidate Top50は空出力のままです。これは今回のSoT混同修正とは別問題で、feature/candidate detail mappingの追加修正対象です。
- `daily_report` の集約statusがBLOCK表示になるケースがあります。今回の再生成では本文生成は完了していますが、Reconcile REVIEW_REQUIREDやstale submit扱いの集約判定は次フェーズで整理余地があります。

## Notification

`tools/launchd/com.aifundlab.operations.daily_report.plist` は `--send-notifications` を含みます。

今回の確認では、LINE/Discord設定は未設定でした。

- line_config_present: false
- discord_config_present: false
- expected status when requested: `SKIPPED_NOT_CONFIGURED`
- token / webhook / hash / length / raw request / raw responseは保存しない
- 今回は実送信していない

## Exit Code

想定内skip/no-opをlaunchdで異常扱いしないようCLIを調整しました。

- market closed skip: exit 0
- preflight market closed readonly-only: exit 0
- demo_special_fill not applicable / market closed: exit 0
- fill monitor market closed monitor-only: exit 0
- safety monitor market closed system-only: exit 0
- reconcile market closed reconcile-only: exit 0
- daily_report generated: exit 0
- notification not configured: daily_report上は非致命
- BLOCKや実異常: non-zero

## Tests

- `python3 -m pytest tests/phase12/test_daily_report_writer_quality.py tests/phase12/test_phase12_demo_submit_guard.py tests/phase12/test_market_closed_safe_skip.py -q`: 14 passed
- `python3 -m pytest tests/phase12 -q`: 79 passed
- `env PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m py_compile ...`: PASS
- `python3 scripts/run_demo_submit.py --trade-date 2026-07-02 --root .runtime/operations`: PASS dry-run
- `python3 scripts/run_operation_audit.py --root .runtime/operations`: PASS

## Safety Confirmation

- Demo注文: 実行していない
- Production注文: 実行していない
- Production Unlock: 実行していない
- LINE/Discord実送信: 実行していない
- AI再学習: 実行していない
- Backtest: 実行していない
- raw request / raw response / secret保存: 実行していない
- Phase9変更: 実行していない
