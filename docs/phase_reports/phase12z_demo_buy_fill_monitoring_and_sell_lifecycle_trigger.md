# Phase12-Z Demo BUY Fill Monitoring & SELL Lifecycle Trigger

## Status

```text
PHASE12Z_BUY_WAITING_FILL_SELL_SKIPPED
```

Phase12-Z tracked the existing Phase12-Y Demo BUY order with broker read-only refresh only.

No BUY reorder, no BUY `CLMKabuNewOrder` retry, no auto cancel, and no SELL order were executed in Phase12-Z.

## Existing BUY Order

Phase12-Y accepted BUY order:

```text
internal_code=92560
broker_issue_code=9256
side=BUY
quantity=100
limit_price=5410
expected_notional=541000
status=ORDER_ACCEPTED
```

Phase12-Z did not call `run_demo_submit.py` and did not re-submit the BUY item.

## Read-only Broker Refresh

Executed:

```bash
python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations --refresh-broker-readonly
```

Result:

```text
Preflight: PASS
Broker Orders: 1
Broker Executions: 0
Broker Positions: 0
Buying Power: 19,458,494 JPY
```

Current broker order:

```text
issue_code=9256
side=3
quantity=100
price=5410.0000
executed_quantity=0
remaining_quantity=100
status=未約定
```

## Fill Monitor

Executed:

```bash
python3 scripts/run_fill_monitor.py --trade-date 2026-06-29 --root .runtime/operations
```

Result:

```text
Fill Monitor: PASS
classification=AVAILABLE
BUY lifecycle=ACCEPTED
broker_orders_count=1
broker_executions_count=0
```

The existing BUY order remains accepted / waiting fill. It is not filled because broker executions and broker positions are still zero.

## Persistent Demo Ledger

Added a minimal read-only monitoring ledger update:

```text
demo_order_status_history
demo_cash_history
demo_lifecycle_event=demo_readonly_fill_monitoring
```

Updated ledger state:

```text
order_history_count=4
order_status_history_count=1
accepted_order_count=1
rejected_order_count=3
execution_history_count=0
position_history_count=0
cash_history_count=1
lifecycle_event_count=5
broker_snapshot_overwrites_demo_ledger=false
persistent_demo_ledger_used_for_multiday_history=true
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

The ledger recorded:

```text
buy_fill_status=WAITING_FILL
sell_order_attempted=false
auto_resubmit=false
auto_cancel=false
```

## SELL Lifecycle Decision

SELL was not attempted.

Reason:

```text
BUY_NOT_FILLED
```

Required SELL conditions were not met:

```text
Broker executions reflected: false
Broker positions reflected: false
SELL quantity <= Broker position quantity: not applicable
```

Therefore:

```text
sell_order_attempted=false
sell_order_executed=false
sell_fill_status=NOT_ATTEMPTED_BUY_NOT_FILLED
```

## Operations Results

Executed after read-only monitoring:

```bash
python3 scripts/run_safety_monitor.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_reconcile.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_operation_audit.py --root .runtime/operations
```

Results:

```text
Safety Monitor: PASS / ALLOW
Reconcile: PASS
Daily Report: PASS
Operation Audit: PASS
```

Audit:

```text
no_production_order_audit=true
leakage_audit=PASS
```

## Tests

Executed:

```bash
python3 -m pytest tests/phase12/test_persistent_demo_ledger.py tests/phase12/test_operations_fill_monitor_states.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/operations/demo_ledger.py src/ai_fund_lab_v2/operations/operations.py tests/phase12/test_persistent_demo_ledger.py
```

Results:

```text
pytest: 4 passed
py_compile: PASS
```

## Prohibited Actions Confirmation

```text
buy_reorder_executed=false
buy_clm_kabu_new_order_called=false
sell_order_attempted=false
sell_order_executed=false
production_order_executed=false
production_unlock_executed=false
line_send_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
phase9_changed=false
```

## Remaining Gaps

- Existing BUY order is still waiting fill.
- SELL lifecycle remains pending until broker executions and positions confirm a fill.
- Continue read-only monitoring; do not reorder or auto-cancel.
