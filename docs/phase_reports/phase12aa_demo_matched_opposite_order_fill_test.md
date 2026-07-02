# Phase12-AA Demo Matched Opposite Order Fill Test

## Status

```text
PHASE12AA_BLOCKED_BEFORE_SELL_BY_EXECUTION_APPROVAL_UNAVAILABLE
```

Phase12-AA implemented the guarded Demo matched opposite order fill test path and confirmed the existing Phase12-Y BUY order by read-only broker refresh.

The planned Demo SELL market order was not executed because the required network escalation for the SELL `CLMKabuNewOrder` call was rejected by the execution environment usage limit. Per policy, no workaround or alternate path was used.

## Existing BUY Confirmation

Read-only refresh before SELL:

```bash
python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations --refresh-broker-readonly
```

Result:

```text
Preflight: PASS
Existing BUY order found: true
Broker issue code: 9256
Side: 3 / BUY
Quantity: 100
Limit price: 5410.0000
Executed quantity: 0
Remaining quantity: 100
Status: 未約定
```

BUY was not reordered.

```text
buy_reorder_executed=false
buy_clm_kabu_new_order_called=false
```

## Implemented Guarded SELL Path

Added:

```text
scripts/run_demo_matched_opposite_fill_test.py
```

Added operation function:

```text
run_demo_matched_opposite_order_fill_test()
```

The path creates a dedicated approval scope:

```text
approval_scope=DEMO_MATCHED_OPPOSITE_ORDER_FILL_TEST
approved_side=SELL
approved_code=92560
approved_broker_issue_code=9256
approved_quantity=100
approved_price_type=MARKET
approved_reason=demo_matched_opposite_order_fill_test
demo_order_allowed=true only when execute flag and guards pass
production_order_allowed=false
```

The planned SELL is explicitly labeled:

```text
sell_reason=demo_matched_opposite_order_fill_test
exit_source=demo_lifecycle_test
order_type=CASH_EQUITY
price_type=MARKET
```

## SELL Execution Result

Dry guard:

```bash
python3 scripts/run_demo_matched_opposite_fill_test.py --trade-date 2026-06-29 --root .runtime/operations
```

Result:

```text
PASS
existing_buy_order_found=true
existing_buy_fill_status_before_sell=WAITING_FILL
sell_order_attempted=false
```

SELL wire execution command was prepared but not completed:

```bash
python3 scripts/run_demo_matched_opposite_fill_test.py --trade-date 2026-06-29 --root .runtime/operations --execute-sell-order --second-password-present
```

Result:

```text
not executed
reason=execution_environment_usage_limit_rejected_network_escalation
```

Therefore:

```text
sell_order_attempted=false
sell_order_executed=false
sell_fill_status=NOT_ATTEMPTED_EXECUTION_APPROVAL_UNAVAILABLE
```

## Post-checks Without SELL

Executed after the blocked SELL attempt:

```bash
python3 scripts/run_fill_monitor.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_safety_monitor.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_reconcile.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_operation_audit.py --root .runtime/operations
```

Results:

```text
Fill Monitor: PASS
Safety Monitor: PASS / ALLOW
Reconcile: PASS
Daily Report: PASS
Operation Audit: PASS
```

Current broker state remains:

```text
Broker Orders: 1
Broker Executions: 0
Broker Positions: 0
Buying Power: 19,458,494
BUY fill status: WAITING_FILL
SELL fill status: NOT_ATTEMPTED
```

## Persistent Demo Ledger

Persistent Demo Ledger was updated by read-only monitoring, not by a SELL execution.

Current state:

```text
order_history_count=4
order_status_history_count=2
accepted_order_count=1
rejected_order_count=3
execution_history_count=0
position_history_count=0
cash_history_count=2
lifecycle_event_count=6
broker_snapshot_overwrites_demo_ledger=false
persistent_demo_ledger_used_for_multiday_history=true
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

No SELL order history was added because no SELL broker API call was executed.

## Tests

Executed:

```bash
python3 -m pytest tests/phase12/test_demo_matched_opposite_order_fill_test.py tests/phase12/test_persistent_demo_ledger.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/operations/demo_ledger.py scripts/run_demo_matched_opposite_fill_test.py tests/phase12/test_demo_matched_opposite_order_fill_test.py
```

Result:

```text
pytest: 6 passed
py_compile: PASS
```

## Safety Confirmation

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

- Demo SELL market order was not executed because network escalation was unavailable.
- Existing BUY remains waiting fill.
- BUY/SELL matched execution confirmation is still pending.
- Next run should execute the same guarded SELL path once network execution approval is available.
