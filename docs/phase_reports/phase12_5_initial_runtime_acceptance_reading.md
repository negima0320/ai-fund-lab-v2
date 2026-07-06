# Phase12.5 Initial Runtime Acceptance Reading

## Status

`PHASE12_5_INITIAL_RUNTIME_ACCEPTANCE_READING_COMPLETE`

今回は読み込みと現状整理のみ。実装変更、artifact削除、launchd変更、実API発注、本番接続、フルバックテスト、大規模テストは実施していない。

## 読んだ資料一覧

- `docs/phase_reports/phase12_final_summary_and_phase13_handoff.md`
- `docs/operations/demo_daily_operation_runbook.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase12ao_operation_flow_integrity_guard.md`
- `docs/phase_reports/phase12an_production_equivalence_final_gap_audit.md`
- `docs/phase_reports/phase12aq_reconcile_review_required_root_cause_fix.md`
- `docs/phase_reports/phase12as_dynamic_approval_max_notional_fix.md`

## 読んだコード一覧

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/market_calendar.py`
- `src/ai_fund_lab_v2/operations/notifications.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/demo_ledger.py`
- `src/ai_fund_lab_v2/operations/guards.py`
- `src/ai_fund_lab_v2/operations/market_refresh.py`
- `src/ai_fund_lab_v2/operations/io.py`
- `src/ai_fund_lab_v2/operations/ledger.py`
- `src/ai_fund_lab_v2/operations/exit_adapter.py`

launchdは `tools/launchd/*.plist` 全件を確認した。

## Phase12.5目的の理解

Phase12.5はPhase13の新機能追加ではなく、Demo環境でProduction Equivalent Runtime Acceptance Testを行うための入口監査である。

確認すべき中心は、Demo固有制約だけを最小限吸収しつつ、Market Refresh、Daily Plan、Approval、Submit、Fill、Safety、Reconcile、Audit、Daily Report、Notificationが本番相当の運用フローとしてつながっているかである。

## Demo固有制約とProduction Equivalent方針

許容されるDemo固有制約は以下。

- Tachibana Demoは毎日リセットされる。
- Demo口座は2,000万円スタートだが、AI Fund Lab評価資金は100万円基準にする。
- 9000番台銘柄はDemoで約定しないため、対象のみDemo Special Fill Simulationでライフサイクル確認する。

Production Equivalent方針は以下。

- BUY候補数、Daily Plan、Approval、Safety、Reconcile、ReportのロジックはDemoだから減らさない。
- Demo差分は `TACHIBANA_API_ENV=demo`、Production order disabled、Persistent Demo Ledger、Demo Special Fill Simulationに閉じる。
- Production注文はPhase12.5でも無効のまま維持する。

## Demo / Production差分一覧

| 差分 | 現在の扱い | 判定 |
| --- | --- | --- |
| `TACHIBANA_API_ENV=demo` | launchd全plistでDemo環境を指定 | 許容 |
| Production order disabled | code/artifactで `production_order_allowed=false` / `production_order_submitted=false` | 許容 |
| Persistent Demo Ledger | `.runtime/operations/demo_ledger/` に日次リセット横断履歴を保持 | 許容 |
| Demo Special Fill Simulation | 9000番台などDemo非約定制約のライフサイクル確認用 | 許容 |
| Demo評価資金100万円 | Approval equity basisはDemoで `demo_evaluation_equity` | 許容 |
| BUY候補をDemoだけ1件化 | 現在は `max_buy_orders_per_day=5` | 差分なし |
| Approval固定60万円 | 通常launchdからは削除済み。ただし2026-07-02 artifactに `manual_override` / `600000` が残る | 監査要 |
| 通知のDemo skip | コード上は設定があれば送信、未設定なら `SKIPPED_NOT_CONFIGURED` | 監査要 |

## Source of Truth整理

Operations RuntimeのSource of Truthは `OPERATIONS_SOURCE_OF_TRUTH` とPhase12-AN/AOで固定されている。

| 対象 | Source of Truth |
| --- | --- |
| 本日Brokerへ送信した注文 | `.runtime/operations/submitted_orders/YYYY-MM-DD/submitted_orders.json` |
| Broker受付状態 | `.runtime/operations/broker_orders/YYYY-MM-DD/orders.json` |
| 約定 | `.runtime/operations/broker_executions/YYYY-MM-DD/executions.json`、無い場合のみ `broker_orders` の約定数量/statusで補完 |
| 現在保有 | `.runtime/operations/broker_positions/YYYY-MM-DD/positions.json` |
| Cash / buying power | `.runtime/operations/broker_buying_power/YYYY-MM-DD/buying_power.json` / account summary |
| Demo横断履歴 | `.runtime/operations/demo_ledger/` |
| 翌営業日候補 | `.runtime/operations/order_plan/YYYY-MM-DD/order_plan.json` |
| Approval | `.runtime/operations/approval_artifact/YYYY-MM-DD/approval_artifact.json` |
| Safety | `.runtime/operations/safety_monitor/YYYY-MM-DD/safety_monitor_result.json` / `safety_result` |
| Reconcile | `.runtime/operations/reconciliation_result/YYYY-MM-DD/reconciliation_result.json` |
| Report | 上記SoTから派生生成 |

重要な禁止事項は、`order_plan` を本日注文・本日約定・現在保有として扱わないこと。

## Report / Notification生成元整理

Daily Reportは `run_daily_report` が生成する。

- `daily_report_refs/YYYY-MM-DD/daily_report_refs.json` がレポート生成の参照manifest。
- `reports/YYYY-MM-DD/public_report.md`
- `reports/YYYY-MM-DD/blog_draft.md`
- `reports/YYYY-MM-DD/safety_report.md`
- `reports/YYYY-MM-DD/line_payload.json`
- `reports/YYYY-MM-DD/discord_payload.json`

`.runtime/operations/reports` はiCloud配下へのsymlinkで、`find -L` では2026-06-29から2026-07-02までのレポート実体を確認できた。

通知は `run_operation_notifications` が生成・送信する。

- `.runtime/operations/notifications/YYYY-MM-DD/notification_result.json`
- LINEは `AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN` などと宛先IDが必要。
- Discordは `AIFUNDLAB_DISCORD_WEBHOOK_URL` などが必要。
- 設定未配置時は `SKIPPED_NOT_CONFIGURED`。
- raw request / raw response / secretは保存しない設計。

launchd上は `com.aifundlab.operations.daily_report.plist` に `--send-notifications` が含まれている。

## Runtime Artifact現況

2026-07-02時点の主要artifact確認結果。

| Artifact | 状態 |
| --- | --- |
| market_refresh | `PASS` |
| order_plan | `PASS`, `buy_item_count=5`, `sell_item_count=0` |
| approval_artifact | `APPROVED`, ただし2026-07-02は `approval_max_notional=600000`, `approval_max_notional_source=manual_override` |
| submitted_orders | `PARTIAL_PASS_WITH_ITEM_BLOCKS`, `accepted_order_count=4`, `blocked_item_count=1` |
| fill_events | `PASS`, `classification=AVAILABLE` |
| safety_monitor | `PASS`, Safety stateはレポート上 `ALLOW` |
| reconciliation_result | `PASS_WITH_BLOCKED_ITEMS` |
| daily_report_refs | `PASS`, `NORMAL_OPERATION_DAY`, `NORMAL_BLOG`, notification `PASS` |
| daily_manifest | `PASS`, notification `PASS` |
| notifications | 2026-07-02はLINE/Discordとも `PASS`, send attempted/executed true |
| audit_result | `PASS` |

2026-07-02のSubmitは `submit_run_date=2026-07-02`、`order_plan_source_date=2026-07-01`、`approval_source_date=2026-07-01` で、朝Submitとして前営業日のPlan/Approvalを参照している。

## 現時点の懸念点

1. 2026-07-02のApproval artifactに固定60万円由来の痕跡がある。
   - Phase12-ASでは通常運用から固定 `600000` を外し、2026-07-01 Approvalは `dynamic_max_exposure` / `850000`。
   - 一方で2026-07-02 Approvalは `manual_override` / `600000`、`current_exposure=965200`。
   - 2026-07-02朝Submitは2026-07-01 Approvalを使っているため直接の発注原因ではないが、夜ジョブや次営業日運用のProduction-equivalent性として監査対象。

2. 最新public reportにSoT表示の違和感がある。
   - 2026-07-02 `public_report.md` は「本日約定した銘柄」として6166を表示する。
   - 同じレポート末尾ではBroker約定0件、Broker保有0件と表示する。
   - `broker_executions` が空のとき `broker_orders.executed_quantity/status` fallbackを使う方針自体はPhase12-AQで許容されたが、ブログ上の「約定」表現がDemo仕様・Broker-confirmed fill・fallback fillを読者に誤認させる可能性がある。

3. Daily ReportのSafety / Market ReviewにPhase9由来の `Safety State: UNKNOWN` が残っている。
   - 末尾のOperations appendixでは `Safety: PASS / ALLOW` と表示される。
   - Phase9 v4 writer復元の副作用として、同一レポート内で安全状態表現が分裂している可能性がある。

4. Notificationは2026-07-02 artifact上は送信済みだが、ユーザー実感として「通知が来ない」がある場合は配送後段の確認が必要。
   - artifactでは `line_config_present=true`, `discord_config_present=true`, `send_attempted=true`, `send_executed=true`。
   - 実端末/チャンネル未着なら、LINE宛先ID、Discord webhook先、launchdの実登録状態、環境変数のlaunchd反映、通知時刻のログを監査する必要がある。

5. `.runtime/operations/reports` はsymlink。
   - workspace内の通常findでは0件に見える。
   - launchd実行ユーザー、iCloud同期状態、権限、リンク先存在がレポート生成/確認の運用リスクになる。

6. `submit` がDaily Manifest上 `STALE_IGNORED`。
   - Flow guard上は朝Submitの前営業日source参照として許容され、Daily ReportはPASS。
   - ただし通知payloadにも `Submit: STALE_IGNORED` と出るため、運用者が正常/異常を判断しづらい可能性がある。

## 既知問題の原因候補

### 通知が来ない

- launchdに最新plistがcopy/bootstrapされていない。
- launchd環境にLINE/Discord envが渡っていない。
- `.env` はコード上読むが、launchdのWorkingDirectoryや実行時ユーザーが想定と違う。
- artifactでは送信成功だが、LINE宛先IDやDiscord webhook先が想定と違う。
- `daily_report` が非通常日判定になり、通知内容が通常サマリではなくレビュー通知へ切り替わっている。
- `notifications/YYYY-MM-DD/notification_result.json` が存在しない日は `--send-notifications` が動いていない、またはdaily_report自体が未実行。

### ブログレポートがおかしい

- Phase9 v4 writer由来の文言とOperations SoT文言が同一markdown内で混在している。
- `broker_orders` fallbackを「約定」として表示している箇所と、Broker executions/positionsを0件として表示する箇所が同居している。
- `order_plan` 由来の翌営業日候補と、`submitted_orders` / `fill_events` 由来の本日結果が読者向けに十分分離されていない可能性がある。
- Candidate Top50 / Top5は復元済みだが、価格位置など一部featureが未取得文言になっている。

## 次に実施すべき監査候補

1. 2026-07-02 `public_report.md` の「本日約定」表示が、`broker_executions` / `broker_orders fallback` / `fill_events` のどれを根拠にしているか行単位で追う。
2. `approval_artifact/2026-07-02` の `manual_override=600000` が通常launchd経路で生成されたのか、手動再生成artifactなのかを履歴・ログで確認する。
3. `daily_report_refs`、`line_payload.json`、`discord_payload.json`、`notification_result.json` の整合を日別に比較し、通知未着日の有無を確認する。
4. launchd実登録状態と `tools/launchd` の差分を、変更なしの読み取りだけで確認する。
5. `.runtime/operations/reports` symlink先への書き込み・読み取り・iCloud同期状態を確認する。
6. `STALE_IGNORED` が正常な朝Submit履歴として扱われるケースと、本当に古いsubmitを隠すケースを分ける監査を行う。
7. Demo Special Fill Simulation対象外日の `BLOCK` / no-op 表現が、Daily Manifest全体を誤ってBLOCK化していないか継続確認する。
8. Production Equivalentの観点で、Demo固有以外の `demo` 分岐、`SKIPPED_BY_DEMO`、候補数削減、通知skipが残っていないか `rg` で棚卸しする。

## まだ修正していないこと

- 実装変更はしていない。
- runtime artifact削除はしていない。
- launchd plist変更はしていない。
- launchctl操作はしていない。
- Demo追加注文はしていない。
- Production接続・Production注文はしていない。
- LINE/Discord通知の新規送信はしていない。
- AI再学習、フルバックテスト、大規模テストはしていない。
