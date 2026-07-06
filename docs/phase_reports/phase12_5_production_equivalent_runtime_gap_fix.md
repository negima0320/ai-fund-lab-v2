# Phase12.5 Production Equivalent Runtime Gap Fix

作成日: 2026-07-02  
目的: Demo固有制約だけを吸収し、それ以外はProduction Runtimeと同じ運用検証になるよう、修正前監査のCritical / High不足を最小修正する。

## 修正概要

Production Equivalent Runtimeを壊していた以下を修正した。

- SubmitをDemo固定入口から共通Runtime入口へ移行
- `prod` / `production` の環境正規化とbase URL判定を統一
- 通常Runtimeでの `manual_override` Approval混入をReview/Block化
- broker read-only snapshotの `source: mock` をPASS扱いしないguardを追加
- SoT consistency guardを強化し、broker_orders fallback / accepted fill / broker_executions 0件の混同をReview化
- Notification artifactに「HTTP送信成功であり、端末到達確認ではない」ことを明記
- Report / Notification payloadが同じDaily Report sourceを参照する情報を追加

## 変更ファイル一覧

- `src/ai_fund_lab_v2/broker/settings.py`
- `src/ai_fund_lab_v2/operations/guards.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/notifications.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/__init__.py`
- `scripts/run_demo_submit.py`
- `tests/phase12/test_phase12_5_production_equivalent_guards.py`
- `tests/phase12/test_phase12_demo_submit_guard.py`
- `tests/phase12/test_phase12_approval.py`
- `tests/phase12/test_daily_report_writer_quality.py`
- `tests/phase12/test_operations_sell_integration.py`

## Critical修正内容

### 1. Submit共通Runtime化

新しい共通入口として `run_submit_operation()` を追加した。

- 既存 `run_demo_submit()` は後方互換ラッパーとして維持
- `scripts/run_demo_submit.py` は内部で `run_submit_operation()` を呼ぶ
- Demo / Production の切替は `TACHIBANA_API_ENV` / normalized runtime envで決定
- Demo時は `DemoOrderExecutor` と `TachibanaDemoOrderAdapter`
- Production時は `ProductionOrderExecutor` に入るが、Phase12.5では必ず `BLOCKED_PRODUCTION_PROHIBITED`
- `production_order_submitted=false` を維持
- Production接続・Production注文・実API発注は行っていない

### 2. manual_override / 600000 混入ガード

通常auto runtimeで `manual_override` が出た場合、Approvalを通さないようにした。

- `auto_demo_approval=True` かつ `max_notional` 明示時は `manual_override_not_allowed_in_auto_runtime`
- Submitが `approval_max_notional_source=manual_override` のApprovalを参照した場合は `manual_override_approval_not_allowed_for_runtime_submit`
- Daily Report / AuditのSoT guardでも `approval_manual_override_detected` をReview理由として出す

## High修正内容

### 3. broker read-only `source: mock` guard

`broker_readonly` artifact生成・読込時にmock sourceを検出するようにした。

- `source_classification`
- `mock_source_detected`
- `review_reasons`
- `broker_readonly_snapshot_source_mock`

mockが含まれる場合、Runtime acceptance上は `REVIEW_REQUIRED` になり、Daily Report / AuditのSoT guardにも伝播する。

### 4. `prod` / `production` 表記揺れ修正

`broker/settings.py` に `normalize_broker_environment()` を追加し、`prod` と `production` を同じProduction環境に正規化した。

- `TACHIBANA_API_ENV=prod` -> `production`
- `TACHIBANA_API_ENV=production` -> `production`
- Production既定base URLはProduction URL
- Demo env + Production URLはBLOCK
- Production env + Demo URLはBLOCK

### 5. Audit / Notification整合修正

Notification artifactに以下を追加した。

- `send_success_semantics`
- `delivery_confirmation=false`
- `report_source.daily_report_refs_path`
- `report_source.public_report`
- `report_source.blog_draft`

Audit parityでは、Daily ReportとNotificationのbusiness_date不一致、requested sendなのにnotification artifactがない状態をunexpected differenceにする。

### 6. SoT consistency PASS強化

`_source_of_truth_consistency_guard()` を追加した。

Review対象:

- Approvalがmanual_override
- broker readonly sourceがmock
- submitted ordersのapproval/order_plan source date不一致
- `broker_orders_used_as_execution_fallback=true`
- `fill_events` が `ACCEPTED` だが `broker_executions_count=0`

Reportでは `source_of_truth_consistency_pass=false` と具体理由を残す。

## Broker / Demo Ledger責務整理

### Production

ProductionではBroker stateを正とする。

- `broker_orders`
- `broker_executions`
- `broker_positions`
- `broker_buying_power`
- `broker_account_summary`

### Demo

Demoでは責務を分離する。

- 当日Broker state: 当日の受付・状態確認
- Persistent Demo Ledger: 日次リセットをまたぐ保有・評価・履歴の正
- Demo Special Fill: 9000番台などDemo非約定制約だけの補正

今回の修正では、broker_orders fallbackを「確定約定」として断定しないようにし、Report上では `BROKER_ORDER_FALLBACK` として扱う。

## Report / Blog / Notification修正内容

- `broker_orders` fallbackだけでは `FILLED` と断定しない
- 実Fill eventが `FILLED` / `SIMULATED_FILLED` の場合のみReport上の約定計算に使う
- Notification dry-runは `send_executed=false`
- Notification PASSは端末到達成功ではなく、HTTP requestがローカル例外なく完了したことを意味する
- LINE / Discord payloadに同じreport sourceを残す
- secret / token / webhook URL / raw request / raw responseは保存しない

## 実施テスト

### 構文確認

```text
PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m compileall -q src/ai_fund_lab_v2/operations src/ai_fund_lab_v2/broker src/ai_fund_lab_v2/runtime scripts/run_demo_submit.py
```

結果: PASS

### affected tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m pytest tests/phase12/test_phase12_5_production_equivalent_guards.py tests/phase12/test_phase12_demo_submit_guard.py tests/phase12/test_phase12_approval.py tests/phase12/test_phase12_audit.py tests/phase12/test_daily_report_writer_quality.py tests/runtime/test_order_executor_interface.py -q
```

結果: 42 passed

```text
PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m pytest tests/phase12/test_operations_launchd.py tests/phase12/test_market_closed_safe_skip.py tests/phase12/test_operations_sell_integration.py tests/phase12/test_operations_phase12l_report_and_candidate_audit.py tests/phase12/test_recovery_day_report.py tests/phase12/test_operations_daily_manifest.py tests/phase12/test_operations_fill_monitor_states.py tests/phase12/test_demo_special_fill_simulation.py tests/phase12/test_demo_order_wire_unlock_guards.py -q
```

結果: 30 passed

### 検証観点カバー

- unit / affected tests: 実施
- env切替テスト: 実施
- Submit共通入口テスト: 実施
- Production envでSubmit BLOCK確認: 実施
- no production order submitted確認: 実施
- manual_override guard確認: 実施
- mock broker snapshot guard確認: 実施
- Report SoT整合確認: 実施
- Notification SoT整合確認: 実施
- JSON validation: 実施
- secret canary: 実施。実secret出力なし。テスト内のダミー値と環境変数名のみ。

## 残課題

- launchd plist名はまだ `demo_submit` のまま。内部入口は共通化済みだが、Phase13前に名称を `submit_operation` へ寄せる余地がある。
- Capital Allocation AI接続は引き続きPhase13以降の課題。
- 実配送確認はLINE/Discordの下流仕様上artifactだけでは確認できないため、Notification artifactではHTTP送信成功と端末到達成功を分離して扱う。
- `.runtime/operations` 既存artifactの再生成・削除は今回行っていない。既存のmock/manual_override artifactは、次回Runtime実行時にReview/Blockとして見える化される。

## 禁止事項遵守

今回、以下は行っていない。

- Production接続
- Production注文
- 実API発注
- artifact削除
- artifact改ざん
- 新しいDemo専用Runtime追加
- フルバックテスト
- AI再学習
- secret出力
- token / webhook URL / raw request / raw response 保存

