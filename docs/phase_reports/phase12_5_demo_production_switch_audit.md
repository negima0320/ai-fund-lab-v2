# Phase12.5 Demo / Production Switch Audit

## Status

`PHASE12_5_DEMO_PRODUCTION_SWITCH_AUDIT_COMPLETE`

今回はDemo/Production切替ロジックの見落とし監査のみ。実装変更、新規モジュール作成、artifact削除、artifact再生成、launchd変更、launchctl操作、実API発注、本番接続、通知新規送信、フルバックテスト、大規模テストは実施していない。

## 読んだコード / plist / artifact一覧

### Code

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/guards.py`
- `src/ai_fund_lab_v2/operations/market_refresh.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/demo_ledger.py`
- `src/ai_fund_lab_v2/operations/notifications.py`
- `src/ai_fund_lab_v2/operations/exit_adapter.py`
- `src/ai_fund_lab_v2/broker/settings.py`
- `src/ai_fund_lab_v2/broker/demo_order.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- `src/ai_fund_lab_v2/broker/allowlist.py`
- `src/ai_fund_lab_v2/runtime/order_executor.py`
- `src/ai_fund_lab_v2/runtime/order_authorization.py`
- `src/ai_fund_lab_v2/runtime/approval.py`
- `scripts/run_approval_prepare.py`
- `scripts/run_demo_submit.py`
- `scripts/run_demo_special_fill_simulation.py`
- `scripts/run_demo_daily_operation.py`
- `scripts/run_daily_report.py`

### plist

`tools/launchd/*.plist` 全件を確認した。

- `com.aifundlab.operations.preflight.plist`
- `com.aifundlab.operations.demo_submit.plist`
- `com.aifundlab.operations.fill_monitor.plist`
- `com.aifundlab.operations.safety_monitor.plist`
- `com.aifundlab.operations.reconcile.plist`
- `com.aifundlab.operations.demo_special_fill.plist`
- `com.aifundlab.operations.market_refresh.plist`
- `com.aifundlab.operations.daily_plan.plist`
- `com.aifundlab.operations.auto_approval.plist`
- `com.aifundlab.operations.operation_audit.plist`
- `com.aifundlab.operations.daily_report.plist`

### Artifact / report

- `.runtime/operations/order_plan/2026-07-02/order_plan.json`
- `.runtime/operations/approval_artifact/2026-07-02/approval_artifact.json`
- `.runtime/operations/submitted_orders/2026-07-02/submitted_orders.json`
- `.runtime/operations/daily_report_refs/2026-07-02/daily_report_refs.json`
- `.runtime/operations/audit_result/audit_result.json`
- `.runtime/operations/reconciliation_result/2026-07-02/reconciliation_result.json`
- `.runtime/operations/broker_orders/2026-07-02/orders.json`
- `.runtime/operations/broker_executions/2026-07-02/executions.json`
- `.runtime/operations/broker_positions/2026-07-02/positions.json`
- `.runtime/operations/notifications/2026-07-02/notification_result.json`

### rg棚卸し

以下の語で棚卸しした。

- `demo`
- `production`
- `TACHIBANA_API_ENV`
- `production_order_allowed`
- `SKIPPED_BY_DEMO`
- `dry_run`
- `mock`
- `simulate`
- `simulation`
- `RuntimeMode.DEMO`
- `RuntimeMode.PRODUCTION`
- `TachibanaDemoOrderAdapter`
- `DemoOrderExecutor`
- `ProductionOrderExecutor`

## Demo/Production切替方式の現在構造

現在の切替境界は主に以下。

1. `.env` / environment
   - `TACHIBANA_API_ENV`
   - `TACHIBANA_API_BASE_URL`
   - broker credential file env
   - notification env

2. `broker/settings.py`
   - `TACHIBANA_API_ENV` を読み、`demo` / `prod` 相当でbase URLを切り替える。
   - 注意: `TACHIBANA_API_ENV=prod` はProduction URLをdefaultにするが、`TACHIBANA_API_ENV=production` はsettings上のdefault URL判定ではProduction扱いにならない。Production切替時は `TACHIBANA_API_BASE_URL` 明示が必要。

3. `operations._resolve_runtime_environment`
   - `TACHIBANA_API_ENV` を必須扱いにし、`prod` は `production` に正規化する。
   - broker settings側のenvironmentとOperations側environmentの不一致をBLOCKする。

4. `guards.validate_runtime_environment`
   - envとbase URLの整合を確認する。
   - `production_order_allowed=True` はBLOCK。
   - Production envでDemo URLならBLOCK。

5. launchd
   - 全Operations plistが `TACHIBANA_API_ENV=demo` をEnvironmentVariablesに持つ。
   - Production用plistは存在しない。
   - `daily_report` だけ `--send-notifications` を持つ。
   - `auto_approval` に `--max-notional` はない。

## 設定だけで切替できるか

結論: 読み取り・市場データ・Daily Plan・Report・Notificationの多くは設定で切替可能な形に近い。一方、Submitは設定だけではProduction相当経路に切り替わらない。

理由:

- Submit CLIは `scripts/run_demo_submit.py` で、実装関数も `run_demo_submit`。
- `run_demo_submit` は `validate_demo_environment` を使い、envがdemoでない場合はBLOCKする。
- Command生成時に `RuntimeMode.DEMO` を固定している。
- 実送信adapterは `TachibanaDemoOrderAdapter` 固定。
- payloadは常に `production_order_submitted=false`。
- `ProductionOrderExecutor` は存在するが、現在のOperations本線Submitからは使われていない。

Phase12.5中はProduction order disabledが許容差分なので、Production注文しないこと自体は正しい。ただし「設定だけで本番運用相当へ切替」という観点では、Submit経路はまだDemo専用であり、Production切替可能な共通Submit runtimeにはなっていない。

## 新規Demo専用経路が存在するか

存在する。

許容されるもの:

- `demo_ledger.py`
  - Demo日次リセット対策として許容。
- `run_demo_special_fill_simulation`
  - 9000番台非約定制約への補正として許容。
- `TACHIBANA_API_ENV=demo`
  - Demo環境指定として許容。

見落としリスクがあるもの:

- `run_demo_submit`
  - Phase12.5中のProduction order disabledとしては許容可能。
  - ただし名前・環境guard・adapter・RuntimeModeがDemo固定で、Production EquivalentなSubmit抽象ではない。
- `refresh_demo_broker_readonly_artifacts`
  - read-onlyもDemo名の関数に寄っている。
  - Production read-onlyへ切替えるには別口の確認が必要。
- `auto_demo_approval`
  - Demo用自動承認。Productionでは別承認が必要なので存在自体は妥当。
  - ただし通常運用のApproval MaxはProduction EquivalentなDynamic計算であるべき。
- `demo_matched_opposite_order_fill_test`
  - テスト用/特殊検証経路。通常Runtime本線ではないが、Operations module内に存在するため混入監査対象。

## 許容Demo差分一覧

| 差分 | 現在の実装 | 判定 |
| --- | --- | --- |
| `TACHIBANA_API_ENV=demo` | `.env` / launchd / settings / runtime envで使用 | 許容 |
| Demo日次リセット対策 | `Persistent Demo Ledger`, `detect_demo_broker_daily_reset` | 許容 |
| 2,000万円口座に対する100万円評価資金 | `DEMO_OPERATION_INITIAL_EQUITY=1000000`, `demo_evaluation_equity` | 許容 |
| 9000番台非約定制約 | `run_demo_special_fill_simulation`, simulated fillはperformance excluded | 許容 |
| Persistent Demo Ledger | `.runtime/operations/demo_ledger/` | 許容 |
| Production order disabled | `production_order_allowed=false`, `ProductionOrderExecutor`もBLOCK | Phase12.5中は許容 |

## 非許容のDemo分岐・制限・省略候補

### 1. Submit経路がDemo固定

`run_demo_submit` はDemo専用の別Runtime経路であり、設定だけでProduction Submitに切り替わらない。

監査上の判定:

- Phase12.5中のProduction order disabledとしては許容。
- ただしProduction Equivalent Runtimeという観点では、Submit lifecycleの抽象がDemoに寄っているため、将来Production unlock前の最小修正候補。

### 2. Approvalに `manual_override / 600000` が残存

2026-07-02 Approval artifactは以下。

- `approval_max_notional=600000`
- `approval_max_notional_source=manual_override`
- `current_exposure=965200`
- `dynamic_approval_max_notional=0` はapproval_requestで確認済み

これはDemo固有制約ではなく、Production Equivalentを弱める挙動。通常launchd plistには `--max-notional` がないため、artifact生成経路の監査とガードが必要。

### 3. `auto_demo_approval` がProduction Equivalent監査をすり抜ける可能性

自動承認自体はDemo運用では必要だが、`auto_approval_policy.demo_only=true` で、Production承認とは明確に別物。

Phase12.5では「Demo自動承認でRuntime flowを回す」ことは許容できるが、Approval Max、Safety、Broker SoT、期限切れguardが本番相当であることを別途監査する必要がある。

### 4. ReportがBroker SoTとDemo補完を混ぜて表示

2026-07-02 Reportは、Broker Orders fallbackを「本日約定」として表示しつつ、Broker executions / positionsは0件と表示する。Runtime stateはReconcileで説明可能だが、Report表示ではSource of Truth混在に見える。

これはDemo固有制約ではなく、Report生成モデルの責務分離不足。

### 5. Notification parity監査に古い/別日artifactの影響がある

`audit_result.json` の `demo_production_parity_audit.notification_parity` は `notification_result_present=false`, `send_notifications_requested=false` を示す一方、2026-07-02 `daily_report_refs` と `notification_result` は送信成功。最新監査対象日とaudit artifactの参照タイミングが混ざっている可能性がある。

通知skip自体は確認されなかったが、監査表示の整合に見落としリスクがある。

## 本番相当テストを弱めていない点

確認できた範囲では以下はProduction Equivalent方針に沿っている。

- BUY候補数はDemoだけ1件に削減されていない。
  - 2026-07-02 `max_buy_orders_per_day=5`
  - `candidate_count_environment_specific=false`
- Market Refresh / Daily PlanはJ-Quants featureを使用し、Broker snapshotやledgerをAI学習入力に使わない方針。
- launchdは平日運用で各jobを分割し、daily_reportに通知送信optionがある。
- `SKIPPED_BY_DEMO` はコード上、通知parity監査語としてのみ確認。現在の2026-07-02 notification artifactは `PASS`。
- Demo Special Fill Simulationは通常Fill/Reconcileでnon-blocking扱いされ、対象外で全体BLOCKにはしない方針。
- `order_plan` をSoTとして「本日注文/約定」に使わないルールは `OPERATIONS_SOURCE_OF_TRUTH` とReport guardに定義されている。

## 見落としリスク一覧

1. `TACHIBANA_API_ENV=production` と `prod` の扱い
   - Operationsは `prod` を `production` に正規化する。
   - Broker settingsはdefault base URL判定で `prod` のみProduction URLにする。
   - Production切替時は `TACHIBANA_API_BASE_URL` 明示が必要。

2. launchdはDemo固定
   - 全plistが `TACHIBANA_API_ENV=demo`。
   - Production用plistはなく、設定だけで登録済みlaunchdをProductionに切り替える構成ではない。
   - Phase12.5中は正しいが、Production切替手順では明示的なplist/env管理が必要。

3. SubmitだけDemo専用
   - `run_demo_submit`, `TachibanaDemoOrderAdapter`, `RuntimeMode.DEMO` 固定。
   - Production注文disabled中は安全だが、Production EquivalentのSubmit抽象ではない。

4. Approval artifactのmanual override
   - 通常plistには残っていないのにartifactには残っている。
   - Submit参照やReport/Auditで検出しきれていない。

5. Broker SoTとDemo Ledgerの表示責務
   - Demo ledgerは日次リセット横断履歴。
   - Broker executions/positionsが0でもbroker_orders fallbackで説明可能。
   - Reportでこれを「保有」「約定」と表示するとBroker SoTとの混同になる。

6. `dry_run=True` の意味
   - `DemoOrderExecutor().submit(..., dry_run=True)` はauthorization gate通過確認で、直後に `TachibanaDemoOrderAdapter` が実Broker APIを呼ぶ。
   - 変数名だけ見ると実API未送信に見えるため、監査時の誤読リスクがある。

7. Notification成功判定
   - artifact上のPASSはHTTP例外なしを意味し、配送到達確認ではない。
   - launchd環境と手動再実行のartifact時刻差がある。

8. Operation Auditの対象日
   - `run_operation_audit.py` はrootの最新/全体artifact監査寄り。
   - `daily_report_refs/2026-07-02` と `audit_result.json` のnotification parity表示にズレがある。

## 修正が必要な場合の最小修正方針

今回は修正しない。必要な最小修正方針は以下。

1. Submitの抽象化
   - すぐProduction発注可能にするのではなく、`run_submit` 的な共通入口でenvに応じてDemo adapter / Production disabled guardを選ぶ。
   - Phase12.5中はProduction disabledを維持する。

2. Approval manual override guard
   - launchd通常運用で `approval_max_notional_source=manual_override` が出たらReport/Auditを `REVIEW_REQUIRED` にする。
   - Submitがmanual override approvalを参照する場合も通常運用ではBLOCKまたはREVIEW_REQUIREDにする。

3. Production env validation
   - `TACHIBANA_API_ENV=production` と `prod` のdefault URL挙動を統一する。
   - Production切替には `TACHIBANA_API_BASE_URL` とProduction unlock承認を別途必須にする。

4. Report SoT分離
   - `order_plan` 由来の翌営業日候補と、`submitted_orders` / `fill_events` / `broker_orders` / `broker_executions` 由来の本日結果を別モデルに分ける。
   - `broker_orders` fallbackは「Broker Orders上の全部約定表示」と明記し、Broker executionsとは区別する。

5. Notification診断強化
   - 新規送信なしで、launchd実行時刻、artifact mtime、env key presence、HTTP status code相当を非secretで記録する。
   - token / webhook URL / raw request / raw responseは保存しない。

## 設定だけで切替できるかの最終判定

`PARTIAL`

- Market Refresh / Daily Plan / Report / Notification / Safety / Reconcileは、かなり設定切替に寄っている。
- Broker settingsはenv/base URL切替を持つが、`production` literalのdefault URL扱いに注意が必要。
- SubmitはDemo専用経路であり、設定だけでProduction相当Submit経路にはならない。
- Phase12.5中はProduction order disabledが許容差分なので、これは即時危険というより、Production Equivalent Acceptance上の明確な見落としリスク。

## 今回は修正していないこと

- 実装変更はしていない。
- 新規モジュール作成はしていない。
- artifact削除・artifact再生成はしていない。
- launchd変更・launchctl操作はしていない。
- Demo追加注文はしていない。
- Production接続・Production注文はしていない。
- LINE/Discord通知の新規送信はしていない。
- secret値、token値、webhook URL、raw request、raw responseは表示・保存していない。
- AI再学習、フルバックテスト、大規模テストはしていない。
