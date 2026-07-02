# Phase12-D Operations Daily Runtime / CLI Responsibilities Design

作成日: 2026-06-29

## Status

```text
PHASE12D_OPERATIONS_DAILY_RUNTIME_DESIGN_COMPLETE
DESIGN_ONLY
IMPLEMENTATION_CHANGED_FALSE
RUNTIME_CHANGED_FALSE
DEMO_ORDER_EXECUTED_FALSE
PRODUCTION_ORDER_EXECUTED_FALSE
LINE_SEND_EXECUTED_FALSE
AI_RETRAINING_EXECUTED_FALSE
BACKTEST_RERUN_FALSE
```

## 1. Purpose

Phase12-D 前設計の目的は、Demo Full Operationを30営業日安定して回すために、Operations CLIの責務、実行タイミング、監視、約定確認、Phase11 Safety連携、異常時runbookを明文化することである。

今回は設計書作成のみであり、実装変更、Runtime変更、Broker API変更、Demo注文、Production注文、LINE実送信、AI再学習、Backtest再実行は行わない。

## 2. Read Materials / Code

確認した資料:

- `docs/phase_reports/phase12a_demo_full_operation_design.md`
- `docs/phase_reports/phase12b_demo_full_operation_minimal_implementation.md`
- `docs/phase_reports/phase12c_demo_order_wire_execution_unlock_design.md`
- `docs/phase_reports/phase11_final_summary_and_phase12_handoff.md`
- `docs/02_architecture/safety_layer_phase11_refined_design.md`
- `docs/02_architecture/phase9_daily_paper_trading_design.md`

確認したコード:

- `src/ai_fund_lab_v2/operations/`
- `scripts/run_preflight.py`
- `scripts/run_daily_plan.py`
- `scripts/run_approval_prepare.py`
- `scripts/run_demo_submit.py`
- `scripts/run_fill_monitor.py`
- `scripts/run_reconcile.py`
- `scripts/run_daily_report.py`
- `scripts/run_operation_audit.py`
- `tools/launchd/com.aifundlab.operations.*.plist`
- `src/ai_fund_lab_v2/paper_trading/market_data_refresh.py`
- `src/ai_fund_lab_v2/paper_trading/feature_refresh.py`
- `src/ai_fund_lab_v2/paper_trading/run_manifest.py`
- `src/ai_fund_lab_v2/paper_trading/run_lock.py`
- `src/ai_fund_lab_v2/safety_phase11/`

## 3. Operations CLI一覧

既存CLI:

| CLI | 現責務 | Phase12-D方針 |
|---|---|---|
| `run_preflight.py` | Runtime env / business day / broker snapshot summary / safety summary / secret audit | 寄付き前の発注可否ゲート。Broker snapshot失敗時はsubmit禁止 |
| `run_daily_plan.py` | AI feature contamination audit / Order Plan artifact | J-Quants refresh済みfeatureを前提に、AI推論とOrder Plan生成へ責務を限定 |
| `run_approval_prepare.py` | Approval request / approval artifact | 夜のapproval準備と寄付き前snapshot反映の両方に対応。ただし引数は増やしすぎない |
| `run_demo_submit.py` | Approval / Safety / MAX_EXPOSURE guard後のsubmit準備 | Phase12初期は手動実行。Operations層はBroker Adapterへ `broker.submit_order()` するだけに寄せる |
| `run_fill_monitor.py` | submitted ordersからfill event生成 | 注文受付、約定、部分約定、未約定、失効、拒否、positions反映を監視 |
| `run_reconcile.py` | artifact存在確認 | Order Plan / Approval / Submitted / Broker Orders / Executions / Positions / Ledger / Fill / Safety / Reportを照合 |
| `run_daily_report.py` | Safety / Blog / Public / LINE payload refs | market / fill / safety / reconcile状態を日次reportに集約。LINE実送信は禁止 |
| `run_operation_audit.py` | 30営業日監査材料 / leakage audit | no production order / no LINE send / secret / raw response / leakage / pass rate監査 |

追加すべきCLI:

| CLI | 結論 | 理由 |
|---|---|---|
| `run_market_refresh.py` | 追加すべき | J-Quants取得、raw daily quotes、canonical normalized、feature refresh、data quality、manifest生成を `run_daily_plan.py` から分離するため |
| `run_safety_monitor.py` | 追加すべき | 保有銘柄、市場、Broker異常、duplicate risk、buying power hard violationを日中監視し、Fill Monitorと責務を分けるため |

Phase9参考から採用する構成:

- CLI scriptは薄く保つ。
- 実処理は `src/ai_fund_lab_v2/operations/` 配下moduleへ寄せる。
- market refresh manifest、feature refresh manifest、daily manifestを分ける。
- run lockで二重起動を止める。
- CLI引数は最小限にし、Runtime Config、現在時刻、schedule contextでモードを判断する。

## 4. `run_market_refresh.py` Design

`run_market_refresh.py` はJ-Quants由来データの更新とAI入力featureの鮮度確保だけを担当する。

責務:

```text
J-Quants API取得
raw daily quotes更新
listed info / trading calendar必要分更新
canonical normalized更新
feature refresh
data quality check
market refresh manifest生成
feature refresh manifest生成
```

禁止:

```text
AI推論
Order Plan生成
Broker発注
Approval生成
LINE実送信
AI再学習
Backtest
Broker SnapshotをAI入力へ使うこと
Paper Ledger / Safety / Audit / Cash / Portfolio / PnLをAI入力へ使うこと
```

Artifact案:

```text
.runtime/operations/market_refresh/YYYY-MM-DD/market_refresh_manifest.json
.runtime/operations/feature_refresh/YYYY-MM-DD/feature_refresh_manifest.json
.runtime/operations/data_quality/YYYY-MM-DD/data_quality_result.json
```

Manifestに含めるべき情報:

- target data_until
- J-Quants API fetch executed
- raw daily quotes path
- canonical normalized path
- feature artifact refs
- feature_schema_hash
- freshness status
- data quality status
- blocked reasons
- forbidden source contamination audit
- AI inference executed false
- order plan generated false
- broker order API called false
- line send executed false

`run_daily_plan.py` との責務分離:

- `run_market_refresh.py` はfeatureを作る。
- `run_daily_plan.py` は既に作られたfeatureを読む。
- J-Quants stale / feature staleなら `run_daily_plan.py` は fail closed。

Phase12-D実装では、Phase9の `market_data_refresh.py` と `feature_refresh.py` の設計を参考にする。ただしPhase9のPaper Trading固有pathやvirtual fill前提は移植しない。

## 5. `run_daily_plan.py` Design

`run_daily_plan.py` は、Market Refresh済みの最新featureを使ってAI推論とOrder Plan生成を行う。

責務:

```text
market_refresh manifest確認
feature_refresh manifest確認
latest feature存在確認
data_until / decision_for整合確認
AI inference
Order Plan生成
AI leakage audit
Order Plan artifact保存
```

禁止:

```text
J-Quants API取得
Broker発注
Approval確定
LINE実送信
AI再学習
Backtest
Broker SnapshotをAI入力へ使うこと
Paper Ledger / Safety / Audit / Cash / Portfolio / PnLをAI入力へ使うこと
```

Fail closed条件:

- market refresh manifest missing
- feature refresh manifest missing
- feature artifact missing
- feature data_untilが古い
- feature sourceにJ-Quants以外が混入
- AI leakage audit BLOCK
- runtime environment未設定 / 不正値 / 判定不能

Order Plan保存:

```text
.runtime/operations/order_plan/YYYY-MM-DD/order_plan.json
.runtime/operations/daily_plan/YYYY-MM-DD/daily_plan_result.json
```

Order PlanはApproval必須であり、`demo_order_allowed=false` / `production_order_allowed=false` を初期値にする。Approval artifactだけがsubmit可否を進める。

## 6. 注文送信タイミング

買い注文・売り注文は、基本的に翌営業日の寄付き前に送信する。

標準フロー:

```text
前営業日 16:30 run_market_refresh.py
前営業日 19:00 run_daily_plan.py
前営業日 20:00 run_approval_prepare.py
翌営業日 08:25 run_preflight.py
翌営業日 08:40 run_approval_prepare.py
翌営業日 08:50 run_demo_submit.py
翌営業日 09:00 market open
```

Phase12初期方針:

- `run_demo_submit.py` は初期5営業日は手動実行。
- launchdにはsubmitを登録しない、またはdisabled sampleに留める。
- 5営業日安定後も、approval済み注文のみ自動submit候補とする。
- Production submitはPhase12では禁止。

`run_demo_submit.py` の責務:

```text
Approval確認
Safety確認
MAX_EXPOSURE確認
Broker buying_power確認
duplicate active order確認
position mismatch確認
Request Build
broker.submit_order()
Response Normalize
redacted submitted order artifact保存
```

Operations層にはDemo/Production分岐を散らさず、Broker Factory / Broker Adapter生成時だけで吸収する。

## 7. Fill Monitor Design

注文送信時点では注文は確定ではない。`run_fill_monitor.py` は、注文と約定の状態監視を担当する。

責務:

```text
注文受付確認
約定確認
部分約定確認
未約定確認
失効確認
拒否確認
Broker positionsへの反映確認
fill event artifact生成
Human Review Queue材料生成
```

実行タイミング:

```text
09:05
09:20
10:30
12:35
14:45
15:40
```

状態分類:

| State | 意味 | 扱い |
|---|---|---|
| `SUBMITTED` | Runtimeが送信記録を持つ | Broker order確認へ進む |
| `ACCEPTED` | Brokerが注文受付 | fill待ち |
| `WAITING_FILL` | 未約定で有効注文 | 自動再注文なし |
| `PARTIALLY_FILLED` | 一部約定 | 約定数量だけBroker Source of Truthで反映 |
| `FILLED` | 全約定 | positions反映を確認 |
| `REJECTED` | Broker拒否 | redacted reason保存、Human Review |
| `EXPIRED` | 当日失効など | 次回Order Planで再判断 |
| `CANCELED` | 取消済み | Phase12-Dでは自動取消しない。Broker状態として読むだけ |
| `UNKNOWN_STATUS` | 判定不能 | fail closed / Human Review |

禁止:

- 自動再注文
- 自動取消
- 自動売却
- 同一注文の自動再送信
- 不明状態でのsubmit継続

Artifact案:

```text
.runtime/operations/fill_events/YYYY-MM-DD/fill_events.json
.runtime/operations/human_review/YYYY-MM-DD/fill_review_queue.json
```

## 8. 未約定 / 部分約定 / 失効 / 拒否 Runbook

未約定:

- 自動再注文しない。
- Human Reviewへ送る。
- 次回Order Planで扱う。
- ReconciliationでBroker active orderとRuntime submitted orderを照合する。

部分約定:

- 約定数量だけBroker Source of Truthとして反映する。
- 残数量はBroker order stateで管理する。
- 自動追加注文しない。
- Reconciliation対象にする。
- Ledger反映はBroker executions / positions一致後に行う。

失効:

- `EXPIRED` として記録する。
- 次回Order Planで再判断する。
- 自動再発注しない。
- 失効確認はBroker orders / executions / positionsで裏取りする。

拒否:

- Reject reasonをredacted normalizedで保存する。
- Human Reviewへ送る。
- 同一注文の自動再送信は禁止。
- Safety Event / Report材料に含める。

`UNKNOWN_STATUS`:

- fail closed。
- Human Reviewへ送る。
- submit / retry / cancel / sell は行わない。
- read-only broker sync、audit、reportのみ許可。

## 9. `run_safety_monitor.py` Design

保有銘柄・市場・Broker状態の監視は `run_fill_monitor.py` とは別CLIとして設計する。推奨名は `run_safety_monitor.py`。

責務:

```text
保有銘柄の現在値監視
個別急落検知
market stress検知
stale quote検知
position mismatch検知
broker divergence検知
duplicate active order risk検知
buying_power hard violation検知
Phase11 Safety Layerへ入力
Safety Event生成
Human Review Queue更新
LINE Payload生成
Safety Report材料生成
```

重要方針:

- 株価下落、個別下落、market stressは `NON_BLOCKING_REVIEW`。
- 自動売却しない。
- 自動停止しない。
- System / Broker / Order異常のみ `BLOCK` / `SYSTEM_EMERGENCY_STOP`。
- Safetyは投資判断ではなくSystem Guard。
- Safety Result / Audit Result / Broker Snapshot / cash / portfolio state / PnLはAI学習へ使わない。

実行タイミング:

```text
09:10
09:30
10:30
12:35
13:30
14:45
15:20
```

入力:

- Broker positions
- Broker orders
- Broker executions
- buying_power
- read-only quote / market summary
- latest submitted orders
- latest fill events
- latest reconciliation result

出力:

```text
.runtime/operations/safety_monitor/YYYY-MM-DD/safety_monitor_result.json
.runtime/operations/safety_events/YYYY-MM-DD/safety_events.json
.runtime/operations/human_review/YYYY-MM-DD/safety_review_queue.json
.runtime/operations/reports/YYYY-MM-DD/line_payload.json
```

LINE payloadは生成のみ。実送信は行わない。

可能なら、立花証券APIのread-only quoteを使って現在値監視を行う。quote取得失敗やcritical staleは、発注前であればsubmit禁止に接続する。

## 10. Fill Monitor / Safety Monitor / Reconciliation の違い

```text
run_fill_monitor.py
= 注文と約定の状態監視

run_safety_monitor.py
= 保有銘柄・市場・Broker異常の監視

run_reconcile.py
= Order Plan / Approval / Submitted Orders / Broker Orders / Executions / Positions / Ledger / Fill / Safety / Report の帳尻確認
```

`run_reconcile.py` は判断を新規に作るCLIではなく、各artifactとBroker Source of Truthの整合性を確認するCLIである。

## 11. Daily Manifest

Phase12-Dではdaily manifestに以下を追加する。

```text
market_refresh_status
feature_refresh_status
daily_plan_status
approval_status
preflight_status
submit_status
fill_monitor_status
safety_monitor_status
reconciliation_status
daily_report_status
operation_audit_status
missed_jobs
run_lock_status
line_send_executed=false
production_order_submitted=false
ai_retraining_executed=false
backtest_run=false
raw_response_saved=false
secret_saved=false
```

Daily manifest保存先:

```text
.runtime/operations/daily_manifest/YYYY-MM-DD/daily_manifest.json
```

Phase9の `DailyRunManifest` と同様に、必須項目欠落、live forbidden flag不整合、broker order unexpected flagはfail closedにする。

## 12. 日次スケジュール / launchd設計

Mac launchdで毎日回す前提の標準スケジュール:

| 時刻 | CLI | 責務 | 実行 |
|---|---|---|---|
| 15:40 | `run_reconcile.py` | 引け後の暫定照合 | launchd |
| 16:30 | `run_market_refresh.py` | J-Quants / normalized / feature refresh | launchd |
| 19:00 | `run_daily_plan.py` | AI推論 / Order Plan | launchd |
| 20:00 | `run_approval_prepare.py` | Approval package生成 | launchd |
| 20:30 | `run_daily_report.py` | Blog / Public Report / LINE Payload draft | launchd |
| 翌08:25 | `run_preflight.py` | business day / broker / safety preflight | launchd |
| 翌08:40 | `run_approval_prepare.py` | 寄付き前snapshot反映 / approval freshness確認 | launchd |
| 翌08:50 | `run_demo_submit.py` | Demo注文送信 | 初期5営業日は手動 |
| 翌09:05 | `run_fill_monitor.py` | 初回注文受付 / fill確認 | launchd |
| 翌09:10 | `run_safety_monitor.py` | 初回position / quote / broker異常監視 | launchd |
| 翌09:20 | `run_fill_monitor.py` | 追加fill確認 | launchd |
| 翌09:30 | `run_safety_monitor.py` | 日中Safety確認 | launchd |
| 翌10:30 | `run_fill_monitor.py` / `run_safety_monitor.py` / `run_reconcile.py` | mid-session確認 | launchd |
| 翌12:35 | `run_fill_monitor.py` / `run_safety_monitor.py` / `run_reconcile.py` | 後場前後確認 | launchd |
| 翌13:30 | `run_safety_monitor.py` | position / market stress確認 | launchd |
| 翌14:45 | `run_fill_monitor.py` / `run_safety_monitor.py` / `run_reconcile.py` | 大引け前確認 | launchd |
| 翌15:20 | `run_safety_monitor.py` | 引け前Safety確認 | launchd |
| 翌15:40 | `run_fill_monitor.py` / `run_reconcile.py` | 引け後fill / reconciliation | launchd |
| 翌20:00 | `run_daily_report.py` | Daily report確定 | launchd |

CLI引数方針:

- launchdは原則として引数なしCLIを実行する。
- `--trade-date` / `--root` は手動検証用に残してよい。
- 環境切替はCLI引数ではなくRuntime Config / `.env` で行う。
- schedule contextは現在時刻、business day、既存manifestから解決する。

## 13. launchd方針

必須ルール:

- `.plist` にsecret値を書かない。
- stdout / stderr にsecretやraw responseを出さない。
- run lockで二重起動を防止する。
- submit系は初期5営業日は手動。
- 5営業日安定後もapproval済み注文のみ自動submit検討。
- Production submitはPhase12では禁止。
- launchd jobは原則引数なしCLIを起動する。
- 環境判定はRuntime Config / Broker Environmentで行い、不正値はfail closed。

追加/更新すべきplist:

```text
tools/launchd/com.aifundlab.operations.market_refresh.plist
tools/launchd/com.aifundlab.operations.safety_monitor.plist
tools/launchd/com.aifundlab.operations.fill_monitor.plist
tools/launchd/com.aifundlab.operations.reconcile.plist
tools/launchd/com.aifundlab.operations.daily_plan.plist
tools/launchd/com.aifundlab.operations.daily_report.plist
tools/launchd/com.aifundlab.operations.preflight.plist
```

Macスリープ時:

- missed job manifestを作る。
- 次回起動時にcatch-up可否を判定する。
- 発注系はcatch-upしない。
- read-only系のみcatch-up可。
- 08:50 submit windowを逃した場合は、その日の自動submitは禁止しHuman Reviewへ送る。

ネットワーク断:

- Broker / J-Quants read-only retryは限定回数のみ。
- submit系はretryしない。
- raw responseを保存しない。
- network failureはmanifestへredacted reasonとして保存し、Human Reviewへ送る。

launchd失敗:

- missed job manifestへ記録する。
- `run_operation_audit.py` がmissed jobを集計する。
- market refresh失敗ならdaily planを止める。
- preflight失敗ならsubmitを止める。
- fill/safety/reconcile失敗ならread-only再実行可。ただしsubmitには進めない。

## 14. 異常時 Runbook

J-Quants取得失敗:

- `run_market_refresh.py` は `BLOCK` または `REVIEW_REQUIRED` を出す。
- raw / normalized / featureがstaleなら `run_daily_plan.py` はfail closed。
- stale featureでOrder Planを作らない。
- BacktestやAI再学習で補完しない。

Broker Snapshot取得失敗:

- 発注禁止。
- read-only retryのみ限定的に許可。
- Human Reviewへ送る。
- reportへredacted reasonを出す。

Preflight失敗:

- `run_demo_submit.py` 禁止。
- read-only sync、audit、reportのみ許可。
- fail closed。

Safety `BLOCK`:

- demo submit禁止。
- read-only sync / audit / reportのみ許可。
- Human Reviewへ送る。

Safety `SYSTEM_EMERGENCY_STOP`:

- 新規買い禁止。
- 自動売却禁止。
- retry / resubmit / cancel / modify禁止。
- 復旧はHuman Approvalが必要。

`NON_BLOCKING_REVIEW`:

- 単独では注文を止めない。
- Human Review / Blog / LINE Payloadへ出す。
- Approval artifactに明示して人間が把握した状態で進める。

Macスリープ / ネット断:

- missed job manifestを作る。
- 次回起動時にcatch-up可能か判定する。
- 発注系はcatch-upしない。
- read-only系のみcatch-up可。

launchd二重起動:

- run lockで拒否する。
- 古いlockは自動破棄しない。
- Human Reviewまたは手動auditで解除判断する。

Raw response / secret persistence疑い:

- `SYSTEM_EMERGENCY_STOP`。
- submit禁止。
- operation auditを実行。
- artifactを隔離対象として扱い、AI入力へ使わない。

## 15. Phase12-D Implementation Tasks

優先順位付き最小タスク:

1. `run_market_refresh.py`
   - J-Quants API取得、raw daily quotes、canonical normalized、feature refresh、data quality、manifest生成。
   - AI推論、Order Plan、Broker発注は禁止。
2. `run_safety_monitor.py`
   - position / market / quote / broker divergence / duplicate risk / buying_power hard violationを監視。
   - Safety Event、Human Review Queue、LINE Payload材料を生成。
3. `OperationPaths` 拡張
   - `market_refresh`
   - `feature_refresh`
   - `data_quality`
   - `safety_monitor`
   - `safety_events`
   - `human_review`
   - `missed_jobs`
4. daily manifest拡張
   - market refresh / feature refresh / fill monitor / safety monitor / missed job / run lock状態を追加。
5. `run_daily_plan.py` 更新
   - market_refresh manifestとfeature_refresh manifestを確認。
   - stale featureはfail closed。
   - J-Quants取得は行わない。
6. `run_fill_monitor.py` 状態分類強化
   - `SUBMITTED`
   - `ACCEPTED`
   - `WAITING_FILL`
   - `PARTIALLY_FILLED`
   - `FILLED`
   - `REJECTED`
   - `EXPIRED`
   - `CANCELED`
   - `UNKNOWN_STATUS`
7. `run_reconcile.py` 拡張
   - fill monitor結果、safety monitor結果、Broker orders、executions、positions、ledger、report refsを照合。
8. `run_daily_report.py` 拡張
   - market refresh、daily plan、approval、submit、fill、safety、reconcile、missed jobsを表示。
   - LINE Payload生成のみ、実送信なし。
9. launchd plist追加 / 更新
   - market refresh / safety monitor追加。
   - fill monitor / reconcileの複数時刻対応。
   - submitは初期手動。
10. missed job / run lock / schedule context設計
    - missed job manifest。
    - read-only catch-up可否。
    - submit catch-up禁止。
11. Broker Adapter境界の維持
    - Operations層へDemo/Production分岐を散らさない。
    - 環境差分はRuntime Config、Broker Factory、Broker Adapter、Transportへ閉じる。
12. 軽量テスト
    - JSON validation。
    - py_compile。
    - targeted pytest。
    - Demo注文、Production注文、LINE実送信、AI再学習、Backtestは実施しない。

## 16. Final Judgement

```text
PHASE12D_OPERATIONS_DAILY_RUNTIME_DESIGN_COMPLETE
RUN_MARKET_REFRESH_SHOULD_BE_ADDED_TRUE
RUN_SAFETY_MONITOR_SHOULD_BE_ADDED_TRUE
IMPLEMENTATION_CHANGED_FALSE
RUNTIME_CHANGED_FALSE
DEMO_ORDER_EXECUTED_FALSE
PRODUCTION_ORDER_EXECUTED_FALSE
LINE_SEND_EXECUTED_FALSE
AI_RETRAINING_EXECUTED_FALSE
BACKTEST_RERUN_FALSE
```
