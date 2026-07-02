# Phase12-AE launchd Schedule Hardening

## Status

```text
PHASE12AE_LAUNCHD_SCHEDULE_HARDENING_COMPLETE
```

Phase12-AE hardened the Operations launchd schedule before full weekday Demo operation.

Codex updated plist files only. `launchctl bootstrap` / `launchctl bootout`, Demo order, Production order, Production unlock, LINE actual send, AI retraining, backtest, raw request save, raw response save, secret save, and Phase9 launchd recovery work were not executed.

## Updated Plists

All Operations plists under `tools/launchd/` were updated to run Monday to Friday only:

```text
Weekday=2,3,4,5,6
```

Updated files:

```text
tools/launchd/com.aifundlab.operations.market_refresh.plist
tools/launchd/com.aifundlab.operations.daily_plan.plist
tools/launchd/com.aifundlab.operations.auto_approval.plist
tools/launchd/com.aifundlab.operations.preflight.plist
tools/launchd/com.aifundlab.operations.demo_submit.plist
tools/launchd/com.aifundlab.operations.fill_monitor.plist
tools/launchd/com.aifundlab.operations.demo_special_fill.plist
tools/launchd/com.aifundlab.operations.safety_monitor.plist
tools/launchd/com.aifundlab.operations.reconcile.plist
tools/launchd/com.aifundlab.operations.operation_audit.plist
tools/launchd/com.aifundlab.operations.daily_report.plist
```

## Schedule Changes

Demo Special Fill was moved later:

```text
before: 09:10
after:  15:35
```

Reason: avoid simulating a fill before the broker has had the trading day to fill non-9000-series Demo orders.

Operation Audit and Daily Report order was changed:

```text
before: 20:00 daily_report / 20:05 operation_audit
after:  20:00 operation_audit / 20:05 daily_report
```

Reason: allow Daily Report to include the latest Operation Audit result.

## Target Schedule

Japan time, Monday to Friday:

```text
08:25  preflight
08:50  demo_submit
09:05  fill_monitor
09:15  safety_monitor
09:20  reconcile
15:35  demo_special_fill
15:40  preflight
15:45  fill_monitor
15:50  safety_monitor
15:55  reconcile
16:30  market_refresh
19:00  daily_plan
19:05  auto_approval
20:00  operation_audit
20:05  daily_report
```

## Runbook Update

Updated:

```text
docs/operations/demo_daily_operation_runbook.md
```

Added / corrected:

```text
weekday-only operation
demo_special_fill at 15:35
operation_audit before daily_report
reload commands for already registered LaunchAgents
launchd status / time confirmation commands
```

## Validation

Plist validation confirmed:

```text
all Operations plists parse successfully
all StartCalendarInterval entries have Hour / Minute / Weekday
all Weekday values are in 2,3,4,5,6
demo_special_fill=15:35
operation_audit=20:00
daily_report=20:05
```

## User Reload Step

Codex did not run this. The user should run on the Mac:

```bash
cp tools/launchd/com.aifundlab.operations.*.plist ~/Library/LaunchAgents/

for plist in ~/Library/LaunchAgents/com.aifundlab.operations.*.plist; do
  launchctl bootout gui/$(id -u) "$plist" 2>/dev/null || true
  launchctl bootstrap gui/$(id -u) "$plist"
done
```

Then verify:

```bash
launchctl print gui/$(id -u)/com.aifundlab.operations.demo_special_fill
launchctl print gui/$(id -u)/com.aifundlab.operations.operation_audit
launchctl print gui/$(id -u)/com.aifundlab.operations.daily_report
```

## Remaining Gaps

```text
LaunchAgent reload is user action
first hardened weekday schedule execution not yet observed
Japanese exchange holidays are not explicitly encoded in launchd Weekday rules
```

