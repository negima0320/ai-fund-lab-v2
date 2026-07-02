# Phase12-D Operations Daily Runtime Minimal Implementation

作成日: 2026-06-29

## Status

```text
PHASE12D_OPERATIONS_DAILY_RUNTIME_IMPLEMENTATION_COMPLETE
IMPLEMENTATION_CHANGED_TRUE
RUNTIME_CHANGED_FALSE
DEMO_ORDER_WIRE_EXECUTION_FALSE
DEMO_ORDER_EXECUTED_FALSE
PRODUCTION_ORDER_EXECUTED_FALSE
PRODUCTION_UNLOCK_EXECUTED_FALSE
LINE_SEND_EXECUTED_FALSE
AI_RETRAINING_EXECUTED_FALSE
BACKTEST_RERUN_FALSE
```

## 1. Summary

Phase12-D前設計書に基づき、Operations Daily Runtimeの最小実装を追加した。

Demo注文wire executionは解禁していない。`run_demo_submit.py` は既存どおりstub / dry-run境界を維持している。

## 2. Added CLI

- `scripts/run_market_refresh.py`
  - `.runtime/operations/market_refresh/YYYY-MM-DD/market_refresh_manifest.json`
  - `.runtime/operations/feature_refresh/YYYY-MM-DD/feature_refresh_manifest.json`
  - `.runtime/operations/data_quality/YYYY-MM-DD/data_quality_result.json`
  - AI推論、Order Plan生成、Broker発注、Approval生成、LINE実送信、AI再学習、Backtestは行わない。
- `scripts/run_safety_monitor.py`
  - `.runtime/operations/safety_monitor/YYYY-MM-DD/safety_monitor_result.json`
  - `.runtime/operations/safety_events/YYYY-MM-DD/safety_events.json`
  - `.runtime/operations/human_review/YYYY-MM-DD/safety_review_queue.json`
  - `.runtime/operations/reports/YYYY-MM-DD/line_payload.json`
  - market stressは `NON_BLOCKING_REVIEW`、System / Broker異常は `BLOCK` / `SYSTEM_EMERGENCY_STOP`。

## 3. Updated Runtime Modules

- `src/ai_fund_lab_v2/operations/io.py`
  - `OperationPaths` に以下のartifact rootを追加。
    - `market_refresh`
    - `feature_refresh`
    - `data_quality`
    - `safety_monitor`
    - `safety_events`
    - `human_review`
    - `missed_jobs`
- `src/ai_fund_lab_v2/operations/operations.py`
  - `run_market_refresh()` 追加。
  - `run_safety_monitor()` 追加。
  - `run_daily_plan()` が market / feature refresh manifest missing でfail closed。
  - `run_fill_monitor()` が以下を分類。
    - `SUBMITTED`
    - `ACCEPTED`
    - `WAITING_FILL`
    - `PARTIALLY_FILLED`
    - `FILLED`
    - `REJECTED`
    - `EXPIRED`
    - `CANCELED`
    - `UNKNOWN_STATUS`
  - `UNKNOWN_STATUS` はfail closed / Human Review。
  - `run_reconcile()` の照合対象を拡張。
  - `run_daily_report()` が market / feature / plan / approval / submit / fill / safety / reconcile / missed jobsを集約。
  - daily manifestへPhase12-D必須statusを追加。

## 4. Daily Manifest

追加した主な項目:

- `market_refresh_status`
- `feature_refresh_status`
- `daily_plan_status`
- `approval_status`
- `preflight_status`
- `submit_status`
- `fill_monitor_status`
- `safety_monitor_status`
- `reconciliation_status`
- `daily_report_status`
- `operation_audit_status`
- `missed_jobs`
- `run_lock_status`
- `line_send_executed=false`
- `production_order_submitted=false`
- `ai_retraining_executed=false`
- `backtest_run=false`
- `raw_response_saved=false`
- `secret_saved=false`
- `phase9_parallel_running_allowed=true`
- `phase9_artifacts_modified_by_phase12=false`
- `phase9_launchd_modified_by_phase12=false`
- `phase12_artifact_root`

## 4.1 Phase9 Parallel Operation Protection

Phase9 Paper Tradingは現行運用として並行稼働する前提のため、Phase12-DではPhase9領域を変更しない。

保護対象:

- `.runtime/paper_trading/`
- `reports/public/phase9_daily/`
- `reports/phase9*`
- `docs/phase_reports/phase9*`
- `scripts/run_phase9_*.py`
- `src/ai_fund_lab_v2/paper_trading/`
- Phase9用launchd plist

Phase12-Dで追加したartifactは `.runtime/operations/` 配下に分離する。Phase9 CLI / module / launchd / reports / artifactsは変更・削除・移動していない。

`run_operation_audit.py` に `phase9_isolation_audit` を追加した。

確認項目:

- `phase9_artifact_root_untouched`
- `phase9_launchd_untouched`
- `phase9_cli_untouched`
- `phase9_reports_untouched`
- `phase12_artifact_root_is_operations`
- `phase12_artifact_root_does_not_use_phase9`
- `phase12_launchd_prefix_is_operations`
- `phase9_parallel_running_allowed=true`
- `phase9_artifacts_modified_by_phase12=false`
- `phase9_launchd_modified_by_phase12=false`

## 5. launchd

追加:

- `tools/launchd/com.aifundlab.operations.market_refresh.plist`
- `tools/launchd/com.aifundlab.operations.safety_monitor.plist`

更新:

- `tools/launchd/com.aifundlab.operations.fill_monitor.plist`
  - 09:05 / 09:20 / 10:30 / 12:35 / 14:45 / 15:40
- `tools/launchd/com.aifundlab.operations.reconcile.plist`
  - 10:30 / 12:35 / 14:45 / 15:40

submit系のlaunchd自動実行は追加していない。

## 6. Tests

実施:

```text
python3 -m pytest tests/phase12
```

結果:

```text
19 passed
```

実施:

```text
PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m py_compile ...
```

結果:

```text
PASS
```

JSON validation:

```text
python3 -m json.tool reports/phase_reports/phase12d_operations_daily_runtime_design.json
python3 -m json.tool reports/phase_reports/phase12d_operations_daily_runtime_implementation.json
```

結果:

```text
PASS
```

## 7. CLI Smoke

専用tmp rootで実行:

```text
TACHIBANA_API_ENV=demo python3 scripts/run_market_refresh.py --trade-date 2026-06-29 --root /private/tmp/aifundlab_phase12d_smoke
TACHIBANA_API_ENV=demo python3 scripts/run_daily_plan.py --trade-date 2026-06-29 --root /private/tmp/aifundlab_phase12d_smoke
TACHIBANA_API_ENV=demo python3 scripts/run_safety_monitor.py --trade-date 2026-06-29 --root /private/tmp/aifundlab_phase12d_smoke
TACHIBANA_API_ENV=demo python3 scripts/run_fill_monitor.py --trade-date 2026-06-29 --root /private/tmp/aifundlab_phase12d_smoke
TACHIBANA_API_ENV=demo python3 scripts/run_reconcile.py --trade-date 2026-06-29 --root /private/tmp/aifundlab_phase12d_smoke
TACHIBANA_API_ENV=demo python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root /private/tmp/aifundlab_phase12d_smoke
```

結果:

- `run_market_refresh.py`: `PASS`
- `run_daily_plan.py`: `PASS`
- `run_safety_monitor.py`: `PASS`
- `run_fill_monitor.py`: `PASS`
- `run_reconcile.py`: `REVIEW_REQUIRED`
  - approval / submitted orders / broker ledger等がないため想定どおり。
- `run_daily_report.py`: `PASS`
- `run_operation_audit.py`: `PASS`

## 8. Safety / Prohibited Actions Confirmation

- Demo注文wire execution: 実施していない。
- Demo注文: 実施していない。
- Production注文: 実施していない。
- Production Unlock: 実施していない。
- LINE実送信: 実施していない。
- AI再学習: 実施していない。
- Backtest再実行: 実施していない。
- secrets平文保存: 実施していない。
- raw broker response保存: 実施していない。
- Phase9 artifact変更: 実施していない。
- Phase9 launchd変更: 実施していない。
- Phase9 CLI変更: 実施していない。
- Phase9 module破壊的変更: 実施していない。
- Phase12 artifact root: `.runtime/operations/` に分離。
- Phase9 / Phase12 並行稼働: 可能。

## 9. Remaining Gaps

- `run_market_refresh.py` はOperations manifest / feature markerの最小実装であり、今回のsmokeではJ-Quants実API取得を実行していない。ネットワーク取得はRuntime Configと資格情報が整った状態で、別途安全に有効化する。
- Demo注文wire executionはPhase12-C設計どおり未解禁。Phase12-Dでは対象外。

## 10. Final Judgement

```text
PHASE12D_OPERATIONS_DAILY_RUNTIME_IMPLEMENTATION_COMPLETE
MARKET_REFRESH_CLI_ADDED_TRUE
SAFETY_MONITOR_CLI_ADDED_TRUE
DAILY_MANIFEST_EXTENDED_TRUE
LAUNCHD_UPDATED_TRUE
DEMO_ORDER_WIRE_EXECUTION_FALSE
```
