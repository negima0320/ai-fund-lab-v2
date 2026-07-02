# Phase12-AC Full Automatic Demo Daily Operation launchd Setup

## Status

```text
PHASE12AC_FULL_AUTOMATIC_DEMO_DAILY_OPERATION_LAUNCHD_SETUP_COMPLETE
```

Phase12-AC prepared Full Automatic Demo Daily Operation for macOS launchd.

This is:

```text
Demo operation equivalence with simulated fill, not Production equivalence
```

Production order, Production unlock, LINE actual send, AI retraining, backtest, raw request save, raw response save, secret save, and Phase9 changes were not executed.

`launchctl bootstrap` was not executed by Codex.

## Implementation Summary

Added a serial runner:

```text
scripts/run_demo_daily_operation.py
```

Updated Demo approval and submit flow:

```text
run_approval_prepare(auto_demo_approval=true)
run_demo_submit duplicate active same-code guard
run_demo_special_fill_simulation double-run guard
```

Auto approval artifacts now record:

```text
approval_source=demo_auto_approval
manual_approval_required=false
production_order_allowed=false
demo_order_allowed=true
```

Production remains fail closed for automatic approval.

## launchd Plists

Created / updated:

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
tools/launchd/com.aifundlab.operations.daily_report.plist
tools/launchd/com.aifundlab.operations.operation_audit.plist
```

All Operations launchd samples set:

```text
TACHIBANA_API_ENV=demo
```

No plist contains Production unlock, Production order enablement, raw secret values, or a second-password file path.

## Schedule

Japan time:

```text
16:30  market_refresh
19:00  daily_plan
19:05  auto_approval
08:25  preflight
08:50  demo_submit
09:05  fill_monitor
09:10  demo_special_fill
09:15  safety_monitor
09:20  reconcile
15:40  preflight
15:45  fill_monitor
15:50  safety_monitor
15:55  reconcile
20:00  daily_report
20:05  operation_audit
```

## Auto Demo Approval Policy

Auto approval is allowed only when:

```text
TACHIBANA_API_ENV=demo
production_order_allowed=false
demo_order_wire_execution=true
order_type=CASH_EQUITY
credit / margin disabled
BUY notional <= demo_auto_approval_max_notional
SELL quantity has position_id and remains scoped to tracked position
Safety ALLOW
MAX_EXPOSURE PASS
buying_power PASS
no SYSTEM_EMERGENCY_STOP
no BLOCKING_REVIEW
```

If environment is Production, unset, invalid, or ambiguous, auto approval blocks.

## Auto Demo Submit Policy

Auto submit requires:

```text
approval_source=demo_auto_approval or explicit approved Demo artifact
demo_order_allowed=true
production_order_allowed=false
Safety ALLOW
MAX_EXPOSURE PASS
buying_power PASS
second password presence PASS
Broker issue code normalization PASS
request codec validation PASS
duplicate active same-side same-code Broker order not found
```

Existing unfilled same-code Broker orders block resubmission.

## Demo Special Fill Policy

Demo Special Fill Simulation is automatic-ready for 9000-series Demo constraints.

It requires:

```text
TACHIBANA_API_ENV=demo
demo_special_fill_simulation_enabled=true
accepted order exists
broker_issue_code starts with 9
broker executions=0
broker positions=0
already_simulated_for_same_order=false
```

It records:

```text
broker_confirmed_fill=false
simulated_fill=true
performance_metrics_excluded=true
not_production_evidence=true
```

If the same order/date was already simulated, the second run fails closed and does not create another simulation event.

## Persistent Demo Ledger

Demo broker snapshot is same-day observation.

Persistent Demo Ledger is cumulative Demo operations history:

```text
.runtime/operations/demo_ledger/
```

Policy:

```text
broker_snapshot_overwrites_demo_ledger=false
persistent_demo_ledger_used_for_multiday_history=true
broker_snapshot_used_for_same_day_execution_confirmation=true
broker_reset_detected recorded when applicable
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

Broker positions/orders/executions resetting to zero in Demo must not erase accumulated Demo ledger history.

## Runbook

Created:

```text
docs/operations/demo_daily_operation_runbook.md
```

It includes daily schedule, CLI responsibilities, launchd registration/removal steps, log locations, failure triage, Daily Report interpretation, Persistent Demo Ledger inspection, Demo Special Fill caveats, and Production prohibitions.

## 30 Business Day Demo Start Conditions

Current readiness:

```text
launchd plist作成済み: PASS
auto approval demo-only: PASS
auto submit demo-only: PASS
production fail closed: PASS
second password secret protected: PASS
J-Quants refresh path: READY
Broker read-only path: READY
Demo submit path: READY
Demo special fill path: READY
Persistent Demo Ledger: READY
Daily Report: READY
Operation Audit: READY
Phase9 isolation: PASS
launchctl registration: USER ACTION REQUIRED
first unattended launchd day: NOT YET OBSERVED
```

Therefore:

```text
full_auto_demo_operation_ready=false
```

The system is ready for user-side LaunchAgent registration and first unattended Demo day observation.

## Tests

Targeted lightweight checks cover:

```text
auto approval demo-only
production auto approval fail closed
duplicate active same-code submit guard
Demo Special Fill 9000-series only
Demo Special Fill no double simulation
launchd plist Demo-only / no Production unlock
```

No Demo order, Production order, Production unlock, LINE send, AI retraining, or backtest was executed by Phase12-AC tests.

## Remaining Gaps

```text
launchctl bootstrap not executed by Codex
first unattended launchd run not yet observed
launchd environment must be verified on the user's Mac
Broker-confirmed 9000-series fill remains unavailable in Demo
Production equivalence still requires broker-confirmed fill and separate Production unlock design
```

