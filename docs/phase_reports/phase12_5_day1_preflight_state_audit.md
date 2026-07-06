# Phase12.5 Day1 Preflight State Audit

## Summary

Phase12.5 Day1開始前の状態を確認した。今回は確認のみで、Submit、Broker注文、Fill/Reconcile、Report再生成、Notification送信、artifact削除、demo_ledger再作成・改変は行っていない。

判定: **BLOCK**

主因は、`2026-07-03` の `order_plan` / `approval_artifact` が既に存在しており、Submit実装が当日Plan/Approvalを優先するため、明日朝のSubmitが `2026-07-02` の5銘柄Planではなく、`2026-07-03` のBLOCK/0件Planを参照する可能性が高いこと。

## Checked Artifacts

- `.runtime/operations/demo_ledger/`
- `.runtime/operations/positions/`
- `.runtime/operations/broker_positions/`
- `.runtime/operations/broker_buying_power/`
- `.runtime/operations/broker_account_summary/`
- `.runtime/operations/order_plan/2026-07-02/order_plan.json`
- `.runtime/operations/approval_artifact/2026-07-02/approval_artifact.json`
- `.runtime/operations/approval_request/2026-07-02/approval_request.json`
- `.runtime/operations/market_refresh/2026-07-02/market_refresh_manifest.json`
- `.runtime/operations/feature_artifacts/2026-07-02/`
- `.runtime/operations/feature_refresh/2026-07-02/`
- `tools/launchd/*.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.*.plist`
- `/tmp/aifundlab.operations.*.out.log`
- `/tmp/aifundlab.operations.*.err.log`
- `.runtime/operations/reports/`
- `.runtime/operations/daily_report_refs/`
- `.runtime/operations/notifications/`

## Cash / Buying Power / Equity

Demo ledger:

- `.runtime/operations/demo_ledger/` は存在しない。
- Persistent Demo Ledger上の保有は、現時点ではゼロ扱い。
- demo ledger stateもないため、Day1開始時点の永続保有履歴は空として扱われる。

Broker state:

- `broker_positions` は `2026-07-01` まで存在し、直近の保有は0件。
- `positions` も `2026-07-01` まで存在し、直近の保有は0件。
- `broker_buying_power/2026-07-01/buying_power.json`: `buying_power=20000000`, `cash_available=20000000`
- `broker_account_summary/2026-07-01/account_summary.json`: `buying_power=20000000`, `cash_available=17903720`
- `broker_snapshot_summary/2026-07-01/broker_snapshot_summary.json`: `broker_actual_equity=20000000`, `buying_power=20000000`, `current_exposure=0`, `positions_count=0`

Day1のSource of Truth:

- ProductionではBroker stateが正。
- Demoでは、日次リセット対策としてPersistent Demo LedgerとBroker当日状態の責務を分ける設計。
- ただし現時点ではdemo ledgerが削除済みで、7/2 broker stateもまだないため、明日朝Submit時はPreflightが当日Broker read-onlyを取得できることが前提。
- 取得前の現時点だけを見ると、買付余力の直近実績は7/1のBroker snapshot / buying_powerが根拠。

## Current Holdings

現時点の保有扱い:

- Persistent Demo Ledger: なし、保有0扱い
- Broker positions latest: 2026-07-01、0件
- Operations positions latest: 2026-07-01、0件

したがって、Day1開始前状態としては保有0銘柄扱い。

## 2026-07-02 Purchase Plan

`order_plan/2026-07-02/order_plan.json`:

- status: `PASS`
- buy_item_count: `5`
- sell_item_count: `0`
- plan_id: `operation_plan_2026-07-02_763bad512682`
- feature candidate audit: `PASS`
- candidate_count: `3700`
- selected_buy_count: `5`

予定5銘柄:

| code | name | side | quantity | limit_price | estimated / expected notional |
| --- | --- | --- | ---: | ---: | ---: |
| 65220 | アスタリスク | BUY | 100 | 0 | 0 |
| 78780 | 光・彩 | BUY | 100 | 0 | 0 |
| 63270 | 北川精機 | BUY | 100 | 0 | 0 |
| 61660 | 中村超硬 | BUY | 100 | 0 | 0 |
| 23930 | 日本ケアサプライ | BUY | 100 | 0 | 0 |

Notes:

- 銘柄名はOrder Plan自体には入っていないが、`listed_info_for_feature.parquet` から照合できる。
- `limit_price=0` / `expected_notional=0` はPlan段階の値。Submit時に `_normalize_item_for_demo_wire()` がJ-Quants latest closeで正規化する設計。

## Approval State

`approval_artifact/2026-07-02/approval_artifact.json`:

- status: `APPROVED`
- approved_item_count: `5`
- approved_item_ids: 7/2 Order Planの5件
- demo_order_allowed: `true`
- production_order_allowed: `false`
- approval_max_notional: `266000`
- approval_max_notional_source: `dynamic_max_exposure`
- approval_blocks: `[]`
- manual_override: なし

この7/2 Approval単体はDay1 Submitに使える状態。

## Feature Artifact State

`feature_artifacts/2026-07-02/`:

- `candidate_features.parquet`: 4371 rows
- `opportunity_feature_input.parquet`: 4371 rows
- `position_feature_input.parquet`: 0 rows
- `capital_policy_input.parquet`: 1 row

`feature_refresh/2026-07-02/latest_features.json`:

- candidate_feature_path: `.runtime/operations/feature_artifacts/2026-07-02/candidate_features.parquet`
- feature_freshness_status: `FEATURE_READY`
- latest_available_market_date: `2026-07-02`

`market_refresh/2026-07-02/market_refresh_manifest.json`:

- status: `PASS`
- feature_refresh_executed: `true`
- data_quality_status: `PASS`
- candidate_feature_path: `.runtime/operations/feature_artifacts/2026-07-02/candidate_features.parquet`

Feature側は7/2分として復旧済み。

## Critical Finding: 2026-07-03 Artifacts Exist

以下の `2026-07-03` artifactが存在する。

- `.runtime/operations/order_plan/2026-07-03/order_plan.json`
- `.runtime/operations/approval_artifact/2026-07-03/approval_artifact.json`
- `.runtime/operations/approval_request/2026-07-03/approval_request.json`
- `.runtime/operations/daily_plan/2026-07-03/daily_plan_result.json`
- `.runtime/operations/feature_candidate_audit/2026-07-03/feature_candidate_audit.json`
- `.runtime/operations/daily_manifest/2026-07-03/daily_manifest.json`

内容:

- `order_plan/2026-07-03`: status `BLOCK`, buy_item_count `0`
- `daily_plan/2026-07-03`: status `BLOCK`
- `feature_candidate_audit/2026-07-03`: `NO_FEATURE_MARKER`, `feature_marker_missing`
- `approval_artifact/2026-07-03`: status `APPROVED`, approved_item_count `0`, approval_max_notional `850000`, source `dynamic_max_exposure`

Submit実装の `_resolve_submit_order_plan_date()` は以下の順序で参照日を決める。

1. Submit実行日の `order_plan` と `approval_artifact` が両方存在すれば当日を使う。
2. なければ前営業日のPlan/Approvalを使う。

したがって、2026-07-03朝のSubmitは、期待される `2026-07-02` Plan/Approvalではなく、存在している `2026-07-03` Plan/Approvalを優先する。これはDay1自然運用の開始条件を壊す。

## Launchd / Plist State

Repo plistとregistered plist:

- `tools/launchd/*.plist` と `~/Library/LaunchAgents/com.aifundlab.operations.*.plist` は一致。

Submit plist:

- `scripts/run_submit_operation.py` を呼ぶ。
- 古い `scripts/run_demo_submit.py` 固定ではない。
- `TACHIBANA_API_ENV=demo`
- `--execute-demo-order`
- `--second-password-present`

Registered jobs:

- preflight: registered, last exit code `0`
- demo_submit: registered, last exit code `0`
- fill_monitor: registered, last exit code `0`
- safety_monitor: registered, last exit code `0`
- reconcile: registered, last exit code `0`
- demo_special_fill: registered, last exit code `0`
- market_refresh: registered, last exit code `0`
- daily_plan: registered, last exit code `0`
- auto_approval: registered, not yet run under current registration
- operation_audit: registered, last exit code `0`
- daily_report: registered, not yet run under current registration

Schedule order:

- 08:25 Preflight
- 08:50 Submit
- 09:05 Fill Monitor
- 09:15 Safety Monitor
- 09:20 Reconcile
- 15:35 Demo Special Fill
- 15:40 Preflight
- 15:45 Fill Monitor
- 15:50 Safety Monitor
- 15:55 Reconcile
- 16:30 Market Refresh
- 19:00 Daily Plan
- 19:05 Auto Approval
- 20:00 Operation Audit
- 20:05 Daily Report + Notification

stderr:

- `/tmp/aifundlab.operations.*.err.log` は全て0 bytes。

Launchd経路自体は概ね整っているが、Submit参照対象が7/3 artifactに吸われるため、Day1開始可否はBLOCK。

## Runtime Flow Outlook

自然実行順序は存在する。

Expected Day1 flow:

- Submit
- Broker Orders
- Fill Monitor
- Safety Monitor
- Reconcile
- Daily Report
- Notification

Blocking risk:

- 2026-07-03の当日Plan/Approvalが存在するため、Submitは7/2の5銘柄ではなく7/3の0件/BLOCK Planを参照する見込み。
- その場合、期待された5銘柄のSubmit/Broker Ordersは発生しない。
- 後続のFill/Safety/Reconcile/Report/Notificationは走っても、Day1の受入テストとして意味が弱くなる。

## Notification State

daily_report plist:

- `--send-notifications` あり。
- `TACHIBANA_API_ENV=demo` あり。

Notification config:

- LINE token key: present
- LINE destination key: present
- Discord webhook key: present
- Secret値はレポートに記載しない。

Notification design:

- `notification_result.json` は `send_success_semantics` として「HTTP request completed without local exception; downstream device delivery is not confirmed.」を記録する設計。
- `delivery_confirmation=false` により、HTTP送信成功と端末到達成功は区別される。
- LINE/Discord payloadは同じ `report_refs` / `notification_summary_text` から生成される。
- Demoだから通知skipする分岐は確認されず、`--send-notifications` があれば送信経路に入る。

## Blog / Report Logic Concerns

確認できた設計:

- Source of Truth定義では、`order_plan` は翌営業日候補の正であり、本日注文・本日約定として扱わないルール。
- `manual_override` は `_source_of_truth_consistency_guard()` でReview理由になる。
- `mock_source_detected` もReview理由になる。
- `broker_orders_used_as_execution_fallback` はReview理由になる。
- `accepted_fill_events` があるが `broker_executions_count=0` の場合、Review理由になる。

懸念:

- 既存レンダラには `broker_orders` fallbackを表示行へ反映する経路が残っている。確定約定として断定しないガードは強化されているが、Report表示が誤解を生まないかはDay1実データで再確認が必要。
- 2026-07-03のBLOCK Planが残ったままDaily Reportまで流れると、正常なDay1ブログではなく、0件/BLOCK前提のReportになる可能性が高い。

## Day1 Start Judgment

判定: **BLOCK**

Blocking reasons:

1. `2026-07-03` の `order_plan` と `approval_artifact` が存在し、Submitが当日Plan/Approvalを優先するため、7/2の5銘柄PlanをSubmitしない見込み。
2. `2026-07-03/order_plan.json` は `BLOCK` / `buy_item_count=0` で、Day1自然運用の期待入力として不適切。
3. `2026-07-03/feature_candidate_audit.json` は `NO_FEATURE_MARKER` / `feature_marker_missing` であり、当日Planが壊れている。

Non-blocking observations:

- 7/2 Market Refresh / Feature / Daily Plan / Approvalは復旧済み。
- 7/2 Approvalにmanual_overrideはない。
- launchd plistはrepo/registered一致。
- Submit plistは共通Submit入口を呼ぶ。
- Notification設定とdaily_report `--send-notifications` は存在する。
- 現在の保有は0扱いで整合。

## Not Changed

今回は以下を実施していない。

- Submit実行
- Broker注文
- Production接続
- Production注文
- Fill/Reconcile再実行
- Report再生成
- Notification送信
- artifact削除
- demo_ledger再作成・改変
- launchd変更
- secret出力
