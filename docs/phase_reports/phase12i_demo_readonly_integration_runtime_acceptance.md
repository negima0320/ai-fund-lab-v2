# Phase12-I Demo Read-only Integration & Runtime Acceptance Test

## Final Status

```text
PHASE12I_DEMO_READONLY_INTEGRATION_RUNTIME_ACCEPTANCE_COMPLETE
PHASE12I_ACCEPTANCE_REVIEW_REQUIRED_NOT_READY_FOR_DEMO_WIRE_UNLOCK
DEMO_ORDER_EXECUTION_NOT_EXECUTED
PRODUCTION_ORDER_EXECUTION_NOT_EXECUTED
LINE_SEND_NOT_EXECUTED
AI_RETRAINING_NOT_EXECUTED
```

Phase12-I was executed for `2026-06-29` against `.runtime/operations`.

The important result is mixed:

- Tachibana Demo read-only snapshot succeeded as a standalone broker read-only integration.
- J-Quants real API connectivity was confirmed with a one-request read smoke.
- Operations daily runtime CLI sequence executed safely.
- Operations runtime is not yet accepted for Demo order wire unlock because the real J-Quants fetch and Tachibana Demo read-only snapshot are not wired into the Operations flow.

## Executed Flow

| Step | Command | Result |
|---|---|---|
| Demo read-only broker snapshot | `PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_broker_snapshot --run-demo-snapshot --skip-quotes ...` | `PASS_WITH_WARNINGS` |
| J-Quants read smoke | one-request `trading_calendar` read | `PASS` |
| Market Refresh | `python3 scripts/run_market_refresh.py --trade-date 2026-06-29 --root .runtime/operations` | `PASS` |
| Daily Plan | `python3 scripts/run_daily_plan.py --trade-date 2026-06-29 --root .runtime/operations` | `PASS` |
| Approval Prepare | `python3 scripts/run_approval_prepare.py --trade-date 2026-06-29 --root .runtime/operations` | `PASS`, approval `PENDING` |
| Preflight | `python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations` | `REVIEW_REQUIRED` |
| Demo Submit stub | `python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root .runtime/operations` | `BLOCK` |
| Fill Monitor | `python3 scripts/run_fill_monitor.py --trade-date 2026-06-29 --root .runtime/operations` | `PASS` |
| Safety Monitor | `python3 scripts/run_safety_monitor.py --trade-date 2026-06-29 --root .runtime/operations` | `PASS` |
| Reconcile | `python3 scripts/run_reconcile.py --trade-date 2026-06-29 --root .runtime/operations` | `REVIEW_REQUIRED` |
| Daily Report | `python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root .runtime/operations` | artifact generated; overall manifest remains `BLOCK` |
| Operation Audit | `python3 scripts/run_operation_audit.py --root .runtime/operations` | `PASS` |

`run_demo_submit.py` was executed without `--execute-demo-order`.

## J-Quants API

J-Quants connectivity was confirmed by a single read request:

```json
{
  "endpoint": "trading_calendar",
  "jquants_api_called": true,
  "record_count": 1,
  "raw_response_saved": false
}
```

However, `scripts/run_market_refresh.py` itself still writes Operations feature markers only:

```text
jquants_api_fetch_executed=false
raw_daily_quotes_updated=false
canonical_normalized_updated=false
feature_refresh_executed=true
```

Therefore Phase12-I cannot claim that the Operations Market Refresh CLI is already connected to real J-Quants fetch/normalize/feature refresh.

## Tachibana Demo Read-only Snapshot

Standalone Demo read-only broker snapshot:

| Item | Result |
|---|---:|
| status | `PASS_WITH_WARNINGS` |
| environment | `demo` |
| account | `PASS` |
| positions | `PASS` |
| orders | `PASS` |
| executions | `SKIPPED_NO_ORDERS` |
| quotes | `SKIPPED_NOT_REQUESTED` |
| logout | `PASS` |
| positions_count | `7` |
| orders_count | `0` |
| executions_count | `0` |
| buying_power present | `true` |
| raw broker response saved | `false` |
| secrets saved | `false` |

Artifacts:

- `reports/phase_reports/phase12i_tachibana_demo_readonly_snapshot_result.json`
- `.runtime/operations/broker_snapshot_readonly/2026-06-29/tachibana_demo_snapshot.json`

This confirms Demo read-only broker access works. The warning is acceptable because there were no orders, so executions were skipped.

## Operations Runtime Result

Daily manifest:

```text
status=BLOCK
market_refresh_status=PASS
feature_refresh_status=PASS
daily_plan_status=PASS
approval_status=PENDING
preflight_status=REVIEW_REQUIRED
submit_status=BLOCK
fill_monitor_status=PASS
safety_monitor_status=PASS
reconciliation_status=REVIEW_REQUIRED
daily_report_status=PASS
```

Preflight was `REVIEW_REQUIRED` because `TACHIBANA_API_SECOND_PASSWORD_FILE` was not configured. No secret value was printed.

`run_demo_submit.py` blocked safely:

```text
blocks=["approval_missing_or_not_demo_allowed"]
broker_order_api_called=false
demo_order_submitted=false
production_order_submitted=false
```

Reconciliation was `REVIEW_REQUIRED` because Operations did not have broker-backed `positions`, `ledger`, or pre-report reconciliation artifacts at that point.

## BUY / SELL Plan

Order Plan:

```text
item_count=0
buy_count=0
sell_count=0
exit_adapter_called=true
exit_source=fallback
positions_artifact_exists=false
```

SELL integration was invoked, but no Operations positions artifact existed, so no SELL item was generated.

This must not be interpreted as a valid no-trade investment decision. It is a runtime wiring gap: BUY inference/capital allocation input and broker-backed position input are not yet connected to Operations `daily_plan`.

## Acceptance Checks

| Check | Result |
|---|---|
| J-Quants read API smoke | PASS |
| Operations Market Refresh CLI | PASS |
| Market Refresh uses real J-Quants fetch | FAIL / gap |
| Demo broker read-only snapshot | PASS_WITH_WARNINGS |
| Operations Preflight uses Demo broker snapshot | FAIL / gap |
| Daily Plan generated BUY/SELL evidence | FAIL / gap |
| Approval remains human-gated | PASS |
| Demo Submit blocks without approval | PASS |
| Fill Monitor | PASS |
| Safety Monitor | PASS |
| Reconciliation | REVIEW_REQUIRED |
| Operation Audit | PASS |
| Phase9 isolation | PASS |
| Demo order sent | NO |
| Production order sent | NO |
| LINE sent | NO |
| AI retraining | NO |
| Backtest | NO |

## Blocking Issues

1. Operations `market_refresh` is not connected to the real J-Quants fetch path.
2. Operations `preflight` does not consume the successful Tachibana Demo read-only snapshot.
3. Broker read-only positions/orders/executions/buying_power are not converted into `.runtime/operations` artifacts used by plan/reconcile.
4. Daily Plan produced zero BUY and zero SELL items; the CLI path has no evidence-backed BUY/SELL runtime decision.
5. SELL generation was called, but no Operations positions artifact existed.
6. Approval stayed `PENDING` and Demo Submit correctly blocked, so this run is not a Demo wire unlock acceptance.

## Safety / Prohibition Confirmation

```text
AI retraining executed: false
Backtest executed: false
Demo order executed: false
Production order executed: false
Production unlock executed: false
LINE send executed: false
Raw broker response saved: false
Secret plaintext saved: false
Data leakage detected: false
Phase9 artifacts modified: false
Phase9 launchd modified: false
Phase9 CLI modified: false
```

Operation audit confirmed:

```text
no_production_order_audit=true
secret_audit=true
raw_response_audit=true
phase9_isolation_status=PASS
```

## Lightweight Verification

```text
PYTHONPYCACHEPREFIX=.runtime/operations/pycache_phase12i python3 -m py_compile ...
PASS

python3 -m pytest tests/phase12 -q
25 passed

python3 -m json.tool reports/phase_reports/phase12i_tachibana_demo_readonly_snapshot_result.json
PASS
```

## Recommended Next Tasks

1. Phase12-J: Connect Operations Market Refresh to controlled J-Quants fetch/normalize/feature refresh under `.runtime/operations`.
2. Phase12-J: Add Operations Broker Read-only Adapter integration for Demo snapshot import.
3. Phase12-J: Write broker-backed `positions`, `broker_orders`, `executions`, and `buying_power` artifacts from the Demo snapshot.
4. Phase12-J: Make Preflight fail closed when broker snapshot is missing or stale instead of using default equity.
5. Phase12-J: Connect BUY inference/order plan input to Operations `daily_plan` with J-Quants-only features.
6. Phase12-J: Require explicit `NO_SIGNAL` / `NO_POSITION` evidence when BUY or SELL count is zero.
