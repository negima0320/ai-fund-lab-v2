# Phase12.5 launchd / plist Acceptance Gate Audit

作成日: 2026-07-02  
目的: Phase12.5の日次自動運用前に、Mac launchd / plistがProduction Equivalent Runtime条件を満たしているか監査する。  
判定: **BLOCK**

今回は監査のみ。plist変更、launchctl bootstrap/bootout/kickstart、artifact削除/再生成、実API発注、Production接続、通知新規送信は行っていない。

## 1. Repo plist一覧

全11件。

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

## 2. Registered plist一覧

全11件。

- `~/Library/LaunchAgents/com.aifundlab.operations.auto_approval.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.daily_plan.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.daily_report.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.demo_special_fill.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.demo_submit.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.fill_monitor.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.market_refresh.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.operation_audit.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.preflight.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.reconcile.plist`
- `~/Library/LaunchAgents/com.aifundlab.operations.safety_monitor.plist`

## 3. Repo / Registered差分

`shasum -a 256` で全11件のrepo plistとregistered plistが一致していることを確認した。

判定: PASS

## 4. launchctl登録状態

読み取りのみで `launchctl print gui/501/com.aifundlab.operations.*` を確認した。全jobは登録済みで、stateはいずれも `not running`。

| Job | launchctl runs | last exit code | 判定 |
|---|---:|---|---|
| preflight | 2 | 0 | PASS |
| demo_submit | 1 | 2 | BLOCK |
| fill_monitor | 2 | 2 | BLOCK |
| safety_monitor | 2 | 2 | BLOCK |
| reconcile | 2 | 2 | BLOCK |
| demo_special_fill | 1 | 0 | PASS |
| market_refresh | 1 | 0 | PASS |
| daily_plan | 1 | 0 | PASS |
| auto_approval | 0 | never exited | REVIEW_REQUIRED |
| operation_audit | 1 | 0 | PASS |
| daily_report | 0 | never exited | REVIEW_REQUIRED |

`auto_approval` と `daily_report` は `/tmp` のログとartifactは存在するが、launchctl上は `runs=0`。launchd由来と断定できない。

## 5. 各jobの実行時刻 / ProgramArguments / WorkingDirectory / Env

全jobの `WorkingDirectory` は `/Users/negishi/work/ai-fund-lab-v2`。  
全jobに `TACHIBANA_API_ENV=demo` が設定されている。

| Job | Schedule | ProgramArguments | 判定 |
|---|---|---|---|
| preflight | Weekday 2-6 08:25 / 15:40 | `scripts/run_preflight.py --root .runtime/operations --refresh-broker-readonly` | PASS |
| demo_submit | Weekday 2-6 08:50 | `scripts/run_demo_submit.py --root .runtime/operations --execute-demo-order --second-password-present` | REVIEW_REQUIRED |
| fill_monitor | Weekday 2-6 09:05 / 15:45 | `scripts/run_fill_monitor.py --root .runtime/operations` | PASS |
| safety_monitor | Weekday 2-6 09:15 / 15:50 | `scripts/run_safety_monitor.py --root .runtime/operations` | PASS |
| reconcile | Weekday 2-6 09:20 / 15:55 | `scripts/run_reconcile.py --root .runtime/operations` | PASS |
| demo_special_fill | Weekday 2-6 15:35 | `scripts/run_demo_special_fill_simulation.py --root .runtime/operations --enable-simulation` | PASS |
| market_refresh | Weekday 2-6 16:30 | `scripts/run_market_refresh.py --root .runtime/operations --allow-api-fetch` | PASS |
| daily_plan | Weekday 2-6 19:00 | `scripts/run_daily_plan.py --root .runtime/operations` | PASS |
| auto_approval | Weekday 2-6 19:05 | `scripts/run_approval_prepare.py --root .runtime/operations --auto-demo-approval --approver-label launchd_demo_auto_approval` | PASS |
| operation_audit | Weekday 2-6 20:00 | `scripts/run_operation_audit.py --root .runtime/operations` | PASS |
| daily_report | Weekday 2-6 20:05 | `scripts/run_daily_report.py --root .runtime/operations --send-notifications` | PASS |

重要: `demo_submit` plistはまだ `scripts/run_demo_submit.py` を呼んでいる。現在のscript内部は共通Submit入口 `run_submit_operation()` を呼ぶよう修正済みだが、Acceptance Gateの「古いscript名、特に `run_demo_submit.py` 固定のままではないこと」という条件には合わない。よってPASSにしない。

## 6. stdout / stderr確認結果

全jobでstdout / stderr pathは存在する。stderrはいずれも0 bytes。

| Job | stdout mtime | stdout summary | stderr |
|---|---|---|---|
| preflight | 2026-07-02 15:40:04 +0900 | `REVIEW_REQUIRED` / `PASS` | 0 bytes |
| demo_submit | 2026-07-02 08:50:05 +0900 | `BLOCK` | 0 bytes |
| fill_monitor | 2026-07-02 15:45:03 +0900 | `BLOCK` | 0 bytes |
| safety_monitor | 2026-07-02 15:50:00 +0900 | `BLOCK` | 0 bytes |
| reconcile | 2026-07-02 15:55:00 +0900 | `SYSTEM_EMERGENCY_STOP` | 0 bytes |
| demo_special_fill | 2026-07-02 15:35:01 +0900 | `BLOCK` | 0 bytes |
| market_refresh | 2026-07-02 16:35:28 +0900 | `PASS` | 0 bytes |
| daily_plan | 2026-07-02 19:00:05 +0900 | `PASS` | 0 bytes |
| auto_approval | 2026-07-02 19:05:00 +0900 | `PASS` | 0 bytes |
| operation_audit | 2026-07-02 20:00:02 +0900 | `PASS` | 0 bytes |
| daily_report | 2026-07-02 20:05:03 +0900 | `PASS` | 0 bytes |

stderrに直近エラーはない。ただしstdout上でBLOCK/SYSTEM_EMERGENCY_STOPが出ているjobがあり、launchctl last exit codeも2になっている。

## 7. artifact更新時刻との対応

| Artifact | mtime | launchd logとの対応 |
|---|---|---|
| `preflight/2026-07-02/preflight_result.json` | 15:40:04 | 対応 |
| `submitted_orders/2026-07-02/submitted_orders.json` | 18:39:59 | 不一致。launchd logは08:50 |
| `fill_events/2026-07-02/fill_events.json` | 18:37:06 | 不一致。launchd logは15:45 |
| `safety_monitor/2026-07-02/safety_monitor_result.json` | 18:37:17 | 不一致。launchd logは15:50 |
| `reconciliation_result/2026-07-02/reconciliation_result.json` | 19:06:15 | 不一致。launchd logは15:55 |
| `demo_special_fill/2026-07-02/demo_special_fill_simulation_result.json` | 15:35:01 | 対応 |
| `market_refresh/2026-07-02/market_refresh_manifest.json` | 16:35:28 | 対応 |
| `daily_plan/2026-07-02/daily_plan_result.json` | 19:00:05 | 対応 |
| `approval_artifact/2026-07-02/approval_artifact.json` | 19:05:00 | ログとは対応。ただしlaunchctl runs=0 |
| `audit_result/audit_result.json` | 20:00:02 | 対応 |
| `daily_report_refs/2026-07-02/daily_report_refs.json` | 20:19:29 | 不一致。launchd logは20:05 |
| `notifications/2026-07-02/notification_result.json` | 20:19:29 | 不一致。launchd logは20:05 |
| `reports/2026-07-02/public_report.md` | 20:19:29 | 不一致。launchd logは20:05 |
| `reports/2026-07-02/blog_draft.md` | 20:19:29 | 不一致。launchd logは20:05 |
| `reports/2026-07-02/line_payload.json` | 20:19:29 | 不一致。launchd logは20:05 |
| `reports/2026-07-02/discord_payload.json` | 20:19:29 | 不一致。launchd logは20:05 |

手動再生成artifactとlaunchd生成artifactが混ざっている可能性が高い。特にSubmit/Fill/Safety/Reconcile/Daily Report/Notificationはlaunchd時刻と現在artifact時刻が一致しない。

## 8. Notification実行条件

daily_report plistには `--send-notifications` が入っている。これはPASS。

ただし最新 `notification_result.json` は以下の状態。

- `status=PASS`
- `line_send_attempted=true`
- `line_send_executed=true`
- `discord_send_attempted=true`
- `discord_send_executed=true`
- `secret_saved=false`
- `raw_request_saved=false`
- `raw_response_saved=false`
- `send_success_semantics` は未記録
- `delivery_confirmation` は未記録
- `report_source` は未記録
- mtimeは20:19:29で、launchd daily_report logの20:05:03と一致しない

したがって、通知artifactがlaunchd由来と判断できない。Phase12.5修正後のNotification metadataもまだ反映されていない古いartifactである。

## 9. reports symlink確認

`.runtime/operations/reports` はiCloud配下へのsymlink。

```text
.runtime/operations/reports -> /Users/negishi/Library/Mobile Documents/com~apple~CloudDocs/AIFundLab/operations_reports
```

確認結果:

- symlink target exists: yes
- Codex sandbox内の `test -w` では target_writable: no
- 既存report artifactは存在し、mtimeは2026-07-02 20:19:29

ただしartifact mtimeがlaunchd daily_report logと一致しないため、「launchdからiCloud symlink先へ書けた」とは今回の監査だけでは断定できない。

## 10. Production注文無効

確認したartifact上、`production_order_submitted=false`。

ただし最新 `submitted_orders/2026-07-02/submitted_orders.json` は以下の状態。

- `artifact_type=demo_submit`
- `runtime_submit_entry=null`
- `executor_kind=null`
- `adapter_kind=null`
- `approval_manual_override_detected=null`
- `broker_order_api_called=true`

これはSubmit共通化後のartifactではなく、古いRuntime artifactである。Production注文は無効だが、Submit共通化後のlaunchd実行確認にはなっていない。

## 11. 不備一覧

### BLOCK

1. `demo_submit` launchctl last exit codeが2。
2. `fill_monitor` launchctl last exit codeが2。
3. `safety_monitor` launchctl last exit codeが2。
4. `reconcile` launchctl last exit codeが2。
5. `submitted_orders`, `fill_events`, `safety_monitor`, `reconciliation_result`, `daily_report_refs`, `notification_result`, reports系artifactのmtimeがlaunchd log時刻と一致しない。
6. notification artifactがlaunchd由来と判断できない。
7. latest Submit artifactが共通Submit化後のmetadataを持たない。
8. reports symlink先へのlaunchd書き込み成功をartifact時刻から断定できない。

### REVIEW_REQUIRED

1. `demo_submit` plistがまだ `scripts/run_demo_submit.py` を呼ぶ。内部は共通入口に変わっているが、Acceptance Gate条件上は古いscript名固定として扱う。
2. `auto_approval` はstdout/artifactがある一方、launchctl上は `runs=0`。
3. `daily_report` はstdout/artifactがある一方、launchctl上は `runs=0`。
4. 最新Approval artifactに `approval_max_notional_source=manual_override`, `approval_max_notional=600000` が残っている。
5. 最新Notification artifactにPhase12.5修正後の `send_success_semantics`, `delivery_confirmation`, `report_source` がない。

## 12. Acceptance Gate判定

判定: **BLOCK**

理由:

- repo plistとregistered plistは一致している。
- 全jobはlaunchctl上で確認できる。
- daily_reportに `--send-notifications` は入っている。
- stderrは0 bytes。

しかし、以下のGate条件を満たさない。

- ProgramArgumentsが最新Runtime入口を向いているとは判定できない。`run_demo_submit.py` 固定が残る。
- launchctl last exit codeが複数jobで2。
- launchdログとartifact更新時刻が複数箇所で不一致。
- notification artifactがlaunchd由来と判断できない。
- reports symlink先へlaunchdから書き込めたことを今回artifactから断定できない。
- latest runtime artifactsが修正後の共通Submit/Notification metadataを持っていない。

## 13. 今回は修正していないこと

- plist変更なし
- launchctl bootstrapなし
- launchctl bootoutなし
- launchctl kickstartなし
- artifact削除なし
- artifact再生成なし
- 実API発注なし
- Production接続なし
- 通知新規送信なし
- secret出力なし

