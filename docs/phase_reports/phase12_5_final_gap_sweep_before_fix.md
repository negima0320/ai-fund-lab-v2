# Phase12.5 Final Gap Sweep Before Fix

作成日: 2026-07-02  
目的: 修正前に、Production Equivalent Runtime Acceptance Testを壊している漏れを横断監査する。  
結論: 今回は調査のみ。実装、artifact、launchd、API発注、通知送信、本番接続は行っていない。

## 1. 読んだ資料 / コード / artifact

### 資料

- `docs/phase_reports/phase12_final_summary_and_phase13_handoff.md`
- `docs/operations/demo_daily_operation_runbook.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase12ao_operation_flow_integrity_guard.md`
- `docs/phase_reports/phase12an_production_equivalence_final_gap_audit.md`
- `docs/phase_reports/phase12aq_reconcile_review_required_root_cause_fix.md`
- `docs/phase_reports/phase12as_dynamic_approval_max_notional_fix.md`
- `docs/phase_reports/phase12_5_initial_runtime_acceptance_reading.md`
- `docs/phase_reports/phase12_5_initial_concern_audit.md`
- `docs/phase_reports/phase12_5_demo_production_switch_audit.md`

### コード

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/market_calendar.py`
- `src/ai_fund_lab_v2/operations/notifications.py`
- `src/ai_fund_lab_v2/broker/settings.py`
- `src/ai_fund_lab_v2/broker/tachibana_demo_order.py`
- `src/ai_fund_lab_v2/broker/tachibana_demo_order_smoke.py`
- `src/ai_fund_lab_v2/runtime/order_executor.py`
- `src/ai_fund_lab_v2/runtime/order_authorization.py`
- `src/ai_fund_lab_v2/runtime/approval.py`
- `scripts/run_market_refresh.py`
- `scripts/run_daily_plan.py`
- `scripts/run_approval_prepare.py`
- `scripts/run_demo_submit.py`
- `scripts/run_fill_monitor.py`
- `scripts/run_reconcile.py`
- `scripts/run_safety_monitor.py`
- `scripts/run_daily_report.py`
- `scripts/run_operation_audit.py`
- `scripts/run_preflight.py`
- `scripts/run_demo_special_fill_simulation.py`

### launchd plist

全11件を確認した。

- `tools/launchd/com.aifundlab.operations.auto_approval.plist`
- `tools/launchd/com.aifundlab.operations.daily_plan.plist`
- `tools/launchd/com.aifundlab.operations.daily_report.plist`
- `tools/launchd/com.aifundlab.operations.demo_special_fill.plist`
- `tools/launchd/com.aifundlab.operations.demo_submit.plist`
- `tools/launchd/com.aifundlab.operations.fill_monitor.plist`
- `tools/launchd/com.aifundlab.operations.market_refresh.plist`
- `tools/launchd/com.aifundlab.operations.operation_audit.plist`
- `tools/launchd/com.aifundlab.operations.preflight.plist`
- `tools/launchd/com.aifundlab.operations.reconcile.plist`
- `tools/launchd/com.aifundlab.operations.safety_monitor.plist`

### Runtime artifact

`.runtime/operations` 配下753ファイルを対象に、主要ディレクトリを確認した。

- `market_refresh/`
- `daily_plan/`
- `order_plan/`
- `approval_request/`
- `approval_artifact/`
- `submitted_orders/`
- `broker_readonly_source/`
- `broker_snapshot_readonly/`
- `broker_orders/`
- `broker_executions/`
- `broker_positions/`
- `broker_buying_power/`
- `fill_events/`
- `safety_monitor/`
- `reconciliation_result/`
- `audit_result/`
- `daily_report_refs/`
- `daily_manifest/`
- `reports/`
- `notifications/`
- `demo_ledger/`

## 2. `rg` 棚卸し結果

対象:

- `src/ai_fund_lab_v2/operations/`
- `src/ai_fund_lab_v2/broker/`
- `src/ai_fund_lab_v2/runtime/`
- `scripts/`
- `tools/launchd/`
- `.runtime/operations/`
- `docs/phase_reports/`
- `docs/operations/`

キーワード:

`demo`, `production`, `prod`, `TACHIBANA_API_ENV`, `TACHIBANA_API_BASE_URL`, `RuntimeMode.DEMO`, `RuntimeMode.PRODUCTION`, `run_demo`, `validate_demo`, `auto_demo`, `TachibanaDemo`, `DemoOrder`, `ProductionOrder`, `production_order_allowed`, `production_order_submitted`, `dry_run`, `mock`, `simulate`, `simulation`, `fallback`, `SKIPPED_BY_DEMO`, `SKIPPED`, `STALE_IGNORED`, `manual_override`, `max_notional`, `approval_max_notional`, `source_of_truth`, `broker_orders_used_as_execution_fallback`

実行結果概要:

- 891 files searched
- 615 files contained matches
- 6,451 matches
- 5,486 matched lines
- 重点一致箇所:
  - `operations.py`: demo/prod切替、approval、submit、fill、reconcile、report、audit、SoT guard
  - `broker/settings.py`: `TACHIBANA_API_ENV` / base URL解決
  - `runtime/order_executor.py`: `DemoOrderExecutor` / `ProductionOrderExecutor`
  - `operations/notifications.py`: notification dry-run / send result
  - `tools/launchd/*.plist`: 全plistが `TACHIBANA_API_ENV=demo`
  - `.runtime/operations/*`: `manual_override`, `STALE_IGNORED`, `source: mock`, `broker_orders_used_as_execution_fallback`

## 3. Demo / Production切替方式の現在構造

### 現在成立している切替

- `operations._resolve_runtime_environment()` は `TACHIBANA_API_ENV` を必須扱いし、`demo`, `prod`, `production` を解釈する。
- `TACHIBANA_API_BASE_URL` がある場合、環境名とDemo/Production URLの矛盾を検出する。
- `TACHIBANA_API_ENV=demo` はPhase12.5中の許容差分。
- `production_order_allowed=false` / `production_order_submitted=false` はPhase12.5中の許容差分。

### 成立していない、または弱い切替

- Submit入口が `run_demo_submit.py` / `run_demo_submit()` / `validate_demo_environment()` / `RuntimeMode.DEMO` / `TachibanaDemoOrderAdapter` に固定されている。
- launchdは全11 plistが `TACHIBANA_API_ENV=demo` 固定で、登録済みplist単体ではProduction相当の切替検証にならない。
- `broker/settings.py` は `environment == "prod"` のときだけProduction base URLを既定にし、`production` 文字列では明示base URLがない限りDemo URL側に倒れる。
- `ProductionOrderExecutor` は存在するが、Operations RuntimeのSubmit入口からは使われていない。

## 4. Runtimeモジュール実行実態

| モジュール | 実行入口 | 主入力 | 主出力 | launchd | PASS判定の意味 | 懸念 |
|---|---|---|---|---|---|---|
| Market Refresh | `scripts/run_market_refresh.py` | market data / feature inputs | `market_refresh/`, `feature_refresh/` | あり | market/feature refreshが完了 | 大きなDemo専用弱化は未検出 |
| Daily Plan | `scripts/run_daily_plan.py` | feature artifacts, broker/ledger inputs | `daily_plan/`, `order_plan/` | あり | 候補・注文計画生成 | `capital_allocation_connected=false` が残る |
| Approval | `scripts/run_approval_prepare.py --auto-demo-approval` | `order_plan`, safety, buying power, ledger | `approval_request/`, `approval_artifact/` | あり | auto approvalが通過 | 最新2026-07-02が `manual_override / 600000` |
| Submit | `scripts/run_demo_submit.py --execute-demo-order` | order plan, approval, safety, broker snapshot | `submitted_orders/`, `demo_ledger/` | あり | Demo broker order送信またはブロック分類 | Demo専用経路固定。最重要漏れ |
| Broker Read-only | `scripts/run_preflight.py --refresh-broker-readonly` | Tachibana read-only snapshot | broker orders/executions/positions/buying power | あり | read-only取得・保存 | 2026-07-02 snapshotに `source: mock` が残る |
| Fill | `scripts/run_fill_monitor.py` | submitted orders, broker bundle, demo special | `fill_events/` | あり | fill classification完了 | `ACCEPTED` と実約定表示の表現差 |
| Safety | `scripts/run_safety_monitor.py` | broker/snapshot/fill/submit | `safety_monitor/` | あり | safety ALLOW/BLOCK判定 | 大きなDemo専用弱化は未検出 |
| Reconcile | `scripts/run_reconcile.py` | submitted, broker bundle, fill, ledger | `reconciliation_result/` | あり | 照合分類完了 | broker_orders fallbackを約定代替扱い |
| Audit | `scripts/run_operation_audit.py` | latest/runtime artifacts | `audit_result/` | あり | parity/flow guard PASS | notification parityがdaily report refsと不一致 |
| Daily Report | `scripts/run_daily_report.py --send-notifications` | plan, approval, submit, fill, broker, reconcile, audit | `reports/`, `daily_report_refs/`, `daily_manifest/` | あり | report生成完了 | SoT混在を見逃す可能性 |
| Notification | daily report内 | report payload, webhook/credentials | `notifications/` | daily_report経由 | HTTP POST例外なし | 実配送確認ではない |

## 5. Source of Truth監査

### 現在定義されているSoT

`audit_result` と `daily_report_refs` には以下のSoT定義がある。

- Approval: `approval_artifact/YYYY-MM-DD/approval_artifact.json`
- Submitted orders: `submitted_orders/YYYY-MM-DD/submitted_orders.json`
- Broker acceptance: `broker_orders/YYYY-MM-DD/orders.json`
- Executions: `broker_executions/YYYY-MM-DD/executions.json`、fallbackとして `broker_orders` の executed quantity/status
- Positions: `broker_positions/YYYY-MM-DD/positions.json`
- Persistent history: `demo_ledger/`
- Report: 上記SoTから派生生成

### 混在リスク

- `reconciliation_result/2026-07-02` は `broker_executions_count=0`, `broker_positions_count=0` の一方で、`broker_orders_used_as_execution_fallback=true` として `broker_orders` から実行状態を補完している。
- `fill_events/2026-07-02` は4件を `ACCEPTED` として扱うが、これはBroker注文受付・状態確認であり、`broker_executions` の実約定0件と同義ではない。
- Public/Daily report側で「本日約定」相当の表現が出る場合、`broker_orders` fallback由来なのか、`broker_executions` 由来なのかを明示しないと、本番相当の約定SoTとして誤読される。
- `source_of_truth_consistency_pass=true` が出ているが、現在の実装はReport表現とBroker execution/positionの不一致を十分にFAIL/REVIEWへ持ち上げていない。

## 6. 追加で見つかった漏れ

### Critical

1. Submit経路がDemo固定
   - `run_demo_submit.py`, `run_demo_submit()`, `validate_demo_environment()`, `RuntimeMode.DEMO`, `TachibanaDemoOrderAdapter` に固定。
   - 設定値だけでProduction Runtime経路へ切り替わらない。
   - Phase12.5中のProduction order disabledは許容だが、Runtime経路までDemo専用になるのはProduction Equivalentを壊す。

2. 2026-07-02のApprovalが `manual_override / 600000`
   - `approval_artifact/2026-07-02/approval_artifact.json`
   - `approval_request/2026-07-02/approval_request.json`
   - `approval_max_notional_source=manual_override`
   - `current_exposure=965200`, `current_exposure_source=persistent_demo_ledger`
   - 次営業日SubmitがこのApprovalを参照する場合、通常launchd経路に手動上限が混入する。

### High

3. Broker read-only snapshotが `source: mock`
   - `.runtime/operations/broker_readonly_source/2026-07-02/tachibana_demo_snapshot.json`
   - `.runtime/operations/broker_snapshot_readonly/2026-06-29/tachibana_demo_snapshot.json` などにも存在。
   - 最新日付にも `source: mock` があり、単なる古いartifactだけの問題ではない可能性がある。
   - 実API read-onlyを検証しているつもりでmock artifactをSoTにしているならProduction Equivalentを壊す。

4. `prod` / `production` とbase URL既定値の非対称
   - `operations`側は `prod` を `production` に正規化する。
   - `broker/settings.py` 側は `environment == "prod"` のときのみProduction base URLを既定採用する。
   - `TACHIBANA_API_ENV=production` かつ `TACHIBANA_API_BASE_URL` 未設定だと、設定解決だけを見る限りDemo base URLに倒れる余地がある。

5. AuditとDaily Reportのnotification parityが不一致
   - `audit_result/audit_result.json` は `notification_result_present=false`, `line_send_attempted=false`, `discord_send_attempted=false`, `send_notifications_requested=false`。
   - 同日の `daily_report_refs/2026-07-02/daily_report_refs.json` は `notification_status=PASS`, `line_send_executed=true`, `discord_send_executed=true`。
   - Audit PASSが最新Daily Report/Notification実態を反映していない可能性がある。

6. SoT consistency PASSが実態の混在を見逃す
   - `source_of_truth_consistency_pass=true`。
   - ただし、reconcileでは `broker_orders_used_as_execution_fallback=true`。
   - Report表現が「Broker executions 0件」と「本日約定相当」を同時に出せるなら、PASSの意味が弱い。

### Medium

7. `STALE_IGNORED` が正常/異常を区別しづらい
   - `daily_report_refs/2026-07-02` と `daily_manifest/2026-07-02` で submitが `STALE_IGNORED`。
   - 朝Submitが前営業日Plan/Approvalを使う構造はあり得るが、異常な古いSubmitを無害化しているのか、正常な時系列分類なのか、Reportだけでは判断しづらい。

8. Notification PASSの意味が実配送成功ではない
   - `notifications.py` はHTTP POST例外なしで `send_executed=true`, `status=PASS`。
   - `dry_run=True` でも `send_executed=true` になるコードパスがある。
   - 実通知未着の切り分けでは、artifact PASSを配送成功と読まない運用表現が必要。

9. Demo Special Fill SimulationのBLOCKが非ブロッキング
   - `reconciliation_result/2026-07-02` で `demo_special_fill_simulation.status=BLOCK`, `used=false`。
   - 9000番台非約定対策としては許容されるが、非対象時のBLOCKがReport/Auditで正常扱いされる意味を明確にする必要がある。

10. Capital Allocation未接続がPASS checklist内に残る
   - `daily_report_refs/2026-07-02` のProduction Equivalence checklistでは `Capital Allocation接続状況=REVIEW_REQUIRED`。
   - ただしchecklist全体は `PASS`。
   - Phase12.5のRuntime受入では許容可能だが、Phase13前には未接続を明示的な未完了項目にするべき。

### Low

11. launchd plistがすべてDemo固定
   - Phase12.5中は許容差分。
   - ただし「設定だけでProductionへ切替できる」検証には、別plistまたは環境注入手順が必要。

12. `dry_run=True` の用語が誤解を誘う
   - Submitでは `DemoOrderExecutor(... dry_run=True)` の後に `--execute-demo-order` でDemo broker adapterが呼ばれる。
   - コード上はauthorization gate確認のdry-runだが、運用者には「発注していない」と誤読され得る。

## 7. 既知漏れの再整理

| 項目 | 現在状態 | 重大度 | 判断 |
|---|---|---:|---|
| Submit Demo固定 | 残存 | Critical | 修正前に必ず直す |
| `manual_override / 600000` | 2026-07-02最新Approvalに残存 | Critical | 修正前に必ず直す |
| Public/Daily Reportの約定表現 | broker_orders fallbackとexecutions 0件が混在 | High | 修正前に必ず直す |
| Notification未着疑い | artifact PASSは配送確認ではない | Medium | 表現と監査強化が必要 |
| Audit notification parity不一致 | auditとdaily_report_refsが不一致 | High | 修正前に確認・修正対象 |
| `STALE_IGNORED` | Report/manifestに残存 | Medium | 異常/正常の判定基準を明示 |
| Demo Special Fill BLOCK | used=falseで非ブロッキング | Medium | 許容条件を明示 |
| Capital Allocation未接続 | REVIEW_REQUIREDだが全体PASS | Medium | Phase13前に整理 |

## 8. 修正前に必ず直すべき項目

1. Submit入口をDemo専用からRuntime共通入口へ寄せる。
   - Phase12.5中はProduction order disabledを維持する。
   - ただしRuntime modeとexecutor選択は設定値で決まる構造にする。

2. `approval_max_notional_source=manual_override` の通常運用混入を止める。
   - launchd通常経路でmanual overrideが生成されないことを保証する。
   - Submitが参照するApprovalにmanual overrideがあれば、少なくともReview Requiredにする。

3. `TACHIBANA_API_ENV=production` / `prod` / base URL解決を一貫させる。
   - env名とbase URLが矛盾しないことを、settings層とoperations層の両方で保証する。

4. Broker read-only snapshotの `source: mock` を監査する。
   - 実API read-only artifactなのか、mock fixture由来なのかを明確化する。
   - Runtime SoTにmockが混ざる場合はProduction EquivalentとしてFAIL/REVIEWにする。

5. Reportの約定・保有表現をSoT別に分離する。
   - `broker_executions=0` と `broker_orders fallback` を同じ「約定」と読ませない。
   - `order_plan` を本日注文・本日約定・現在保有として扱わない。

6. Auditが同一対象日のDaily Report / Notification / Reconcileを見ていることを保証する。
   - notification parity不一致をPASSにしない。
   - `source_of_truth_consistency_pass=true` の意味を実チェックに合わせる。

## 9. Phase12.5中は許容してよい項目

- `TACHIBANA_API_ENV=demo`
- Demo口座の日次リセット対策
- 2,000万円スタートに対する100万円評価資金基準
- 9000番台銘柄が約定しない制約へのDemo Special Fill Simulation
- Persistent Demo Ledger
- Phase12.5中のProduction order disabled
- Demo Special Fill Simulationが対象外で `used=false` になること

ただし、上記はReport/Audit上で「許容Demo差分」と明示される必要がある。

## 10. Phase13前までに直す項目

- Capital Allocation AI接続をRuntime order sizingへ接続する。
- Production Runtime用のlaunchd/env切替手順を明文化またはplist分離する。
- Notification artifactの `PASS` を「送信API呼び出し成功」と「実配送確認」に分ける。
- Audit artifactを日付スコープ付きにし、古いまたは別タイミングの状態を最新日次レポートへ混ぜない。
- `dry_run`, `execute-demo-order`, `production_order_submitted` の運用表示を誤読しない名称・監査項目に整理する。

## 11. 今回は修正していないこと

今回は修正前の最終漏れ監査のみを実施した。

- 実装変更なし
- 新規Runtimeモジュール作成なし
- artifact削除なし
- artifact再生成なし
- launchd変更なし
- launchctl操作なし
- 実API発注なし
- 本番接続なし
- 通知新規送信なし
- AI再学習なし
- フルバックテストなし
- 大規模テストなし

