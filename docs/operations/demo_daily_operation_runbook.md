# Demo Daily Operation Runbook

## Scope

This runbook starts Phase12 full automatic Demo daily operation on macOS launchd.

This is:

```text
Production-equivalent Operations flow on the Demo broker environment
```

Demo and Production differences are limited to:

```text
Demo Special Fill Simulation
Persistent Demo Ledger
TACHIBANA_API_ENV=demo
Production order disabled
```

Demo 9000-series fills may use Demo Special Fill Simulation, with:

```text
broker_confirmed_fill=false
performance_metrics_excluded=true
production_order_allowed=false
```

## Daily Schedule

Japan time, Monday to Friday only. Each launchd `StartCalendarInterval` entry uses `Weekday=2,3,4,5,6`.

```text
08:25  run_preflight.py --refresh-broker-readonly
08:50  run_demo_submit.py --execute-demo-order --second-password-present
09:05  run_fill_monitor.py
09:15  run_safety_monitor.py
09:20  run_reconcile.py
15:35  run_demo_special_fill_simulation.py --enable-simulation
15:40  run_preflight.py --refresh-broker-readonly
15:45  run_fill_monitor.py
15:50  run_safety_monitor.py
15:55  run_reconcile.py
16:30  run_market_refresh.py --allow-api-fetch
19:00  run_daily_plan.py
19:05  run_approval_prepare.py --auto-demo-approval
20:00  run_operation_audit.py
20:05  run_daily_report.py --send-notifications
```

## CLI Roles

```text
scripts/run_market_refresh.py
  Refresh J-Quants raw / normalized / feature artifacts. Broker data must not be used for AI training.

scripts/run_daily_plan.py
  Build BUY / SELL order plan from current feature, candidate, opportunity, and exit logic.

scripts/run_approval_prepare.py --auto-demo-approval
  Create Demo-only automatic approval when all gates pass.

scripts/run_preflight.py --refresh-broker-readonly
  Refresh Demo broker read-only snapshots and runtime preflight status.

scripts/run_demo_submit.py --execute-demo-order --second-password-present
  Submit approved Demo cash-equity orders only. Production remains fail closed.

scripts/run_fill_monitor.py
  Classify accepted, filled, waiting, and simulated lifecycle states.

scripts/run_demo_special_fill_simulation.py --enable-simulation
  Apply 9000-series Demo special fill simulation when the accepted order cannot broker-fill in Demo.

scripts/run_safety_monitor.py
  Run system guard checks. Safety remains a guard, not an investment decision.

scripts/run_reconcile.py
  Reconcile order plan, submitted orders, broker read-only state, persistent Demo ledger, and reports.

scripts/run_daily_report.py
  Generate Demo daily report references, public report inputs, and optional LINE / Discord notifications.

scripts/run_operation_audit.py
  Run operations audit, including Phase9 isolation and no-production-order checks.
```

## Market Closed Safe Skip

launchd runs Monday to Friday, but each Operations CLI also checks the market calendar.

Calendar priority:

```text
J-Quants trading_calendar under .runtime/operations
fallback Japanese market holiday calendar
```

Every artifact records:

```text
market_calendar.trade_date
market_calendar.is_business_day
market_calendar.market_closed
market_calendar.market_closed_reason
market_calendar.calendar_source
```

On a market closed day:

```text
run_market_refresh.py: SKIPPED_MARKET_CLOSED
run_daily_plan.py: SKIPPED_MARKET_CLOSED, buy_item_count=0, sell_item_count=0
run_approval_prepare.py: SKIPPED_MARKET_CLOSED, no approval artifact
run_demo_submit.py: SKIPPED_MARKET_CLOSED, clm_kabu_new_order_called=false
run_demo_special_fill_simulation.py: SKIPPED_MARKET_CLOSED, simulated_fill=false
run_preflight.py: PASS_MARKET_CLOSED_READONLY_ONLY
run_fill_monitor.py: PASS_MARKET_CLOSED_MONITOR_ONLY
run_safety_monitor.py: PASS_MARKET_CLOSED_SYSTEM_ONLY
run_reconcile.py: PASS_MARKET_CLOSED_RECONCILE_ONLY
run_operation_audit.py: PASS_MARKET_CLOSED when no market-closed order trace exists
run_daily_report.py: runs and marks Market Status: CLOSED
```

If any order API call or Demo Special Fill simulation trace appears on a market closed day, Operation Audit blocks.

## Daily Report Prerequisite Guard

`run_daily_report.py` classifies the operation day before rendering a public report.

```text
NORMAL_OPERATION_DAY
MARKET_CLOSED_DAY
RECOVERY_DAY
INCOMPLETE_OPERATION_DAY
REVIEW_REQUIRED_DAY
```

Only `NORMAL_OPERATION_DAY` uses the Phase9 v4-style normal blog with Candidate Top50 and next-day Top5 sections.

`MARKET_CLOSED_DAY` produces a market-closed report and does not render Candidate Top50 / Top5.

`INCOMPLETE_OPERATION_DAY` means the market is open but required artifacts are missing, skipped, stale, or date-mixed. It produces an operation-incomplete report and does not render normal candidate sections.

`RECOVERY_DAY` is used when a broken day has been regenerated, such as after a Market Calendar false-closed correction. It produces a recovery report and explicitly states that normal performance evaluation should not include the mixed/recovered day.

Daily Report checks:

```text
market_refresh
daily_plan
order_plan
approval_artifact
submitted_orders
fill_events
safety_monitor
reconciliation_result
operation_audit
feature artifact
artifact date consistency
```

Source of Truth:

```text
submitted_orders = Brokerへ送信した注文
broker_orders = Broker受付状態
broker_executions = 約定の優先Source of Truth
broker_positions = 現在保有
broker_buying_power / account_summary = cash / buying power
demo_ledger = Demo日次リセットをまたぐ永続履歴
order_plan = 翌営業日候補
approval_artifact = Approval
safety_monitor = System Guard
reconciliation_result = 日次照合
```

`order_plan` must not be used as today's submitted orders or today's fills.

## BUY Candidate Count / Allocation Guard

Operations daily plan uses the same BUY candidate count for Demo and Production runtime logic.

Current default:

```text
max_buy_orders_per_day=5
max_new_positions_per_day=5
max_positions=5
max_total_exposure_ratio=0.85
```

The daily plan reads eligible candidate features, sorts them by:

```text
price_momentum_return_20d
price_momentum_return_5d
liquidity_avg_volume_20d
```

and emits up to `max_buy_orders_per_day` BUY items. Demo does not reduce this count to 1.

Submit processes approved items sequentially:

```text
remaining_approval_budget is decremented per accepted BUY item
projected_exposure is accumulated per accepted BUY item
projected_buying_power_usage is accumulated per accepted BUY item
duplicate active order blocks only the matching item
```

Capital Allocation AI is not fully connected to Operations daily plan yet. The Phase12-AH fix is the minimal Production-equivalent candidate-count correction; full capital allocation integration is deferred to Phase13 or the next design phase.

For a serial local rehearsal, the combined runner is available:

```bash
python3 scripts/run_demo_daily_operation.py --trade-date YYYY-MM-DD --root .runtime/operations --allow-api-fetch --refresh-broker-readonly --execute-demo-order --second-password-present --enable-special-fill-simulation
```

Use the combined runner only when a single serial process is preferred. The launchd setup uses individual jobs so each step has its own schedule and log.

## Approval Max Notional

Auto Approval does not use a fixed daily notional cap in normal operations.

Approval Max Notional is calculated from the 85% exposure rule:

```text
approval_max_notional =
min(
  equity_basis * max_total_exposure_ratio - current_exposure,
  available_buying_power_or_cash,
  capital_allocation_total_buy_budget if available
)
```

Demo operations must not use the Tachibana Demo account's large broker cash balance as evaluation equity. Demo uses the AI Fund Lab evaluation equity:

```text
equity_basis=1000000
equity_basis_source=demo_evaluation_equity
max_total_exposure_ratio=0.85
```

With zero current exposure, this gives:

```text
approval_max_notional=850000
approval_max_notional_source=dynamic_max_exposure
```

Production uses broker actual equity or broker buying power through the same approval calculation. Production order submission remains disabled until a separate Production unlock is approved.

`scripts/run_approval_prepare.py --max-notional` is a manual override only. Normal launchd operation does not pass this option. When an override is used, the approval artifact records:

```text
approval_max_notional_source=manual_override
```

The submit step consumes `approval_max_notional` from the approval artifact and does not recalculate its own independent fixed cap.

## launchd Registration

Codex does not register launchd jobs automatically. Register them manually on the Mac after reviewing the plist files.

Copy plist files:

```bash
mkdir -p ~/Library/LaunchAgents
cp tools/launchd/com.aifundlab.operations.*.plist ~/Library/LaunchAgents/
```

Register each job:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.market_refresh.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.daily_plan.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.auto_approval.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.preflight.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.demo_submit.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.fill_monitor.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.demo_special_fill.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.safety_monitor.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.reconcile.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.daily_report.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.operation_audit.plist
```

When updating already registered jobs, recopy and reload:

```bash
cp tools/launchd/com.aifundlab.operations.*.plist ~/Library/LaunchAgents/

for plist in ~/Library/LaunchAgents/com.aifundlab.operations.*.plist; do
  launchctl bootout gui/$(id -u) "$plist" 2>/dev/null || true
  launchctl bootstrap gui/$(id -u) "$plist"
done
```

LaunchAgents do not inherit an interactive shell environment. Before enabling live daily operation, verify that Runtime Config / `.env` / launchctl environment provides the required Demo credentials and paths without writing secret values to plist files.

## launchd Removal

Unload jobs:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.market_refresh.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.daily_plan.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.auto_approval.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.preflight.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.demo_submit.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.fill_monitor.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.demo_special_fill.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.safety_monitor.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.reconcile.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.daily_report.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.aifundlab.operations.operation_audit.plist
```

Remove copied files if needed:

```bash
rm ~/Library/LaunchAgents/com.aifundlab.operations.*.plist
```

## Logs

launchd stdout / stderr logs are written under `/tmp`:

```text
/tmp/aifundlab.operations.market_refresh.log
/tmp/aifundlab.operations.market_refresh.err
/tmp/aifundlab.operations.daily_plan.log
/tmp/aifundlab.operations.daily_plan.err
/tmp/aifundlab.operations.auto_approval.log
/tmp/aifundlab.operations.auto_approval.err
/tmp/aifundlab.operations.preflight.log
/tmp/aifundlab.operations.preflight.err
/tmp/aifundlab.operations.demo_submit.log
/tmp/aifundlab.operations.demo_submit.err
/tmp/aifundlab.operations.fill_monitor.log
/tmp/aifundlab.operations.fill_monitor.err
/tmp/aifundlab.operations.demo_special_fill.log
/tmp/aifundlab.operations.demo_special_fill.err
/tmp/aifundlab.operations.safety_monitor.log
/tmp/aifundlab.operations.safety_monitor.err
/tmp/aifundlab.operations.reconcile.log
/tmp/aifundlab.operations.reconcile.err
/tmp/aifundlab.operations.daily_report.log
/tmp/aifundlab.operations.daily_report.err
/tmp/aifundlab.operations.operation_audit.log
/tmp/aifundlab.operations.operation_audit.err
```

Inspect job state:

```bash
launchctl print gui/$(id -u)/com.aifundlab.operations.demo_submit
launchctl print gui/$(id -u)/com.aifundlab.operations.operation_audit
```

Confirm registered calendar intervals:

```bash
launchctl print gui/$(id -u)/com.aifundlab.operations.demo_special_fill
launchctl print gui/$(id -u)/com.aifundlab.operations.operation_audit
launchctl print gui/$(id -u)/com.aifundlab.operations.daily_report
```

Expected:

```text
demo_special_fill: Weekday 2-6 at 15:35
operation_audit: Weekday 2-6 at 20:00
daily_report: Weekday 2-6 at 20:05
```

## Failure Triage

Primary runtime artifacts:

```text
.runtime/operations/daily_manifest/YYYY-MM-DD/daily_manifest.json
.runtime/operations/order_plan/YYYY-MM-DD/order_plan.json
.runtime/operations/approval_artifact/YYYY-MM-DD/approval_artifact.json
.runtime/operations/submitted_orders/YYYY-MM-DD/submitted_orders.json
.runtime/operations/fill_monitor/YYYY-MM-DD/fill_monitor.json
.runtime/operations/reconcile/YYYY-MM-DD/reconcile.json
.runtime/operations/daily_report_refs/YYYY-MM-DD/daily_report_refs.json
.runtime/operations/operation_audit/operation_audit.json
```

If Demo submit blocks, check:

```text
approval_source
demo_order_allowed
production_order_allowed
safety_decision
max_exposure
buying_power
second_password_present
broker_issue_code_normalization
duplicate_active_broker_order_exists
```

If a launchd step fails but manual CLI succeeds, verify launchd environment separately from shell environment.

## Daily Report

Daily report references live at:

```text
.runtime/operations/daily_report_refs/YYYY-MM-DD/daily_report_refs.json
```

Demo Special Fill entries must be read as Demo-only lifecycle evidence:

```text
broker_confirmed_fill=false
simulated_fill=true
performance_metrics_excluded=true
not_production_evidence=true
```

LINE / Discord notification result lives at:

```text
.runtime/operations/notifications/YYYY-MM-DD/notification_result.json
```

launchd daily_report runs with:

```bash
python3 scripts/run_daily_report.py --root .runtime/operations --send-notifications
```

Notification secrets must not be written to plist files or artifacts. The sender loads configuration at the final send boundary from `.env` or process environment.

LINE Messaging API configuration names:

```text
AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN
AIFUNDLAB_LINE_TO_ID
```

Also accepted:

```text
LINE_CHANNEL_ACCESS_TOKEN
LINE_MESSAGING_API_TOKEN
LINE_USER_ID
LINE_TO
```

`LINE_NOTIFY_TOKEN` alone is not enough for the current Operations sender because it uses LINE Messaging API push delivery.

Discord configuration names:

```text
AIFUNDLAB_DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK_URL
```

`notification_result.json` records only redacted booleans and classifications:

```text
line.config_present
line.send_attempted
line.send_executed
line.status
discord.config_present
discord.send_attempted
discord.send_executed
discord.status
secret_saved=false
raw_request_saved=false
raw_response_saved=false
```

If notification does not arrive:

```text
1. Check .runtime/operations/notifications/YYYY-MM-DD/notification_result.json
2. Check line.config_present / discord.config_present
3. Check line.status / discord.status
4. Check /tmp/aifundlab.operations.daily_report.out.log
5. Check /tmp/aifundlab.operations.daily_report.err.log
6. Confirm launchd job includes --send-notifications
7. Confirm launchd environment can read .env or has launchctl-set environment values
```

Notification failure is non-fatal to ordering, reconciliation, and audit. Daily Report records `notification_status=FAILED_NON_FATAL` when delivery fails.

## Demo / Production Parity

Demo and Production Operations should differ only in these expected places:

```text
Demo Special Fill Simulation for Demo 9000-series non-fill behavior
Persistent Demo Ledger for Tachibana Demo daily reset behavior
TACHIBANA_API_ENV=demo
Production order disabled
```

Notifications, Daily Report, Audit, Approval, Submit gates, Safety, Reconcile, and report generation should use the same Operations flow. `run_operation_audit.py` records `demo_production_parity_audit` and should show no unexpected differences.

## Production Equivalence Checklist

`run_daily_report.py` writes a `production_equivalence_checklist` section to:

```text
.runtime/operations/daily_report_refs/YYYY-MM-DD/daily_report_refs.json
.runtime/operations/reports/YYYY-MM-DD/blog_draft.md
.runtime/operations/reports/YYYY-MM-DD/public_report.md
```

Checklist classifications:

```text
PASS
FIXED
REVIEW_REQUIRED
INTENTIONAL_DEMO_DIFFERENCE
BLOCKING_GAP
```

Required checklist points:

```text
AI判断
BUY候補数
SELL AI
Capital Allocation接続状況
Approval
Submit
Broker read-only
Broker order
Fill
Ledger
Persistent Demo Ledger
Safety
Reconcile
Daily Report
Blog
LINE通知
Discord通知
Operation Audit
launchd
Market Calendar
Secret Redaction
raw request / response保存禁止
Production注文禁止
```

Only these Demo differences may appear as `INTENTIONAL_DEMO_DIFFERENCE`:

```text
Demo Special Fill Simulation
Persistent Demo Ledger
TACHIBANA_API_ENV=demo
Production order disabled
```

Any other `BLOCKING_GAP` or unexpected Demo difference must be reviewed before Production unlock design.

## Daily Report Regeneration

Regenerate today's report without sending notifications:

```bash
python3 scripts/run_daily_report.py --trade-date YYYY-MM-DD --root .runtime/operations
```

Regenerate and send LINE / Discord notifications:

```bash
python3 scripts/run_daily_report.py --trade-date YYYY-MM-DD --root .runtime/operations --send-notifications
```

Generated report files:

```text
.runtime/operations/reports/YYYY-MM-DD/blog_draft.md
.runtime/operations/reports/YYYY-MM-DD/public_report.md
.runtime/operations/reports/YYYY-MM-DD/safety_report.md
.runtime/operations/reports/YYYY-MM-DD/line_payload.json
.runtime/operations/reports/YYYY-MM-DD/discord_payload.json
.runtime/operations/daily_report_refs/YYYY-MM-DD/daily_report_refs.json
```

Regenerated reports include metadata:

```text
regenerated=true
regenerated_reason=phase12aj_blog_report_v4_quality_restoration
```

## Blog Report v4 Quality

Daily Report output must read as a daily operations blog, not as an internal artifact dump.

Required public sections:

```text
資産状況
現在保有中の銘柄
本日注文・約定した銘柄
本日の売却銘柄
Candidate Top50
翌営業日の購入予定候補 Top5
なぜこの5銘柄が購入候補なのか
Broker / Demo運用状況
Safety / Reconcile / Audit
AIの総括
注意書き
```

Forbidden report output:

```text
statuses: {...}
sell_summary: {...}
Demo Special Fill Simulation: {...}
Python dict / repr dumps
JSON dumps pasted into Markdown
BUY reason shown only as "-"
```

Candidate Top50 and Top5 explanation use J-Quants-derived Operations feature artifacts. Public confidence scores are explanation scores based on displayed rank; they are not win probabilities or future return probabilities.

## Exit Code Policy

Expected safe skip / no-op conditions exit with code 0:

```text
market closed safe skip
daily_report generated successfully
demo_special_fill not applicable
demo_special_fill already simulated for the same order
```

Real failures remain non-zero:

```text
secret leak detected
raw request / raw response saved
production order executed unexpectedly
report generation failed
JSON invalid
runtime environment fail closed
```

## Persistent Demo Ledger

Persistent Demo Ledger is the cumulative Demo operations history:

```text
.runtime/operations/demo_ledger/orders.jsonl
.runtime/operations/demo_ledger/executions.jsonl
.runtime/operations/demo_ledger/positions.jsonl
.runtime/operations/demo_ledger/cash.jsonl
.runtime/operations/demo_ledger/events.jsonl
```

Demo broker snapshot is same-day observation only. Broker daily reset must not delete historical Demo ledger records.

Policy:

```text
broker_snapshot_overwrites_demo_ledger=false
persistent_demo_ledger_continues=true
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

## Production Prohibitions

The automatic jobs are Demo-only:

```text
TACHIBANA_API_ENV=demo
production_order_allowed=false
production_unlock=false
credit_margin_disabled=true
```

Do not use these plist files to place Production orders. Production order integration requires a separate approval and unlock design.
