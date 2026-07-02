# Phase12-AB Demo Special Fill Simulation for 9000-series

## Status

```text
PHASE12AB_DEMO_SPECIAL_FILL_SIMULATION_9000_SERIES_COMPLETE
```

Phase12-AB implemented and executed a Demo-only special fill simulation for the 9000-series Tachibana Demo non-fill rule.

This is not a broker-confirmed fill. It is excluded from performance metrics, AI training, backtest results, and Production judgement.

## Guard

The simulation path requires:

```text
TACHIBANA_API_ENV=demo
demo_special_fill_simulation_enabled=true
production_order_allowed=false
broker_issue_code starts with 9
existing BUY order exists
existing BUY status is waiting fill / 未約定
broker_confirmed_fill=false
broker executions=0
broker positions=0
simulation_reason=demo_9000_series_non_fill_rule
```

Production and non-9000-series cases fail closed.

## Runtime Execution

Executed:

```bash
python3 scripts/run_demo_special_fill_simulation.py --trade-date 2026-06-29 --root .runtime/operations --enable-simulation
```

Result:

```text
status=PASS
demo_special_fill_simulation_used=true
production_enabled=false
broker_confirmed_buy_fill=false
simulated_buy_fill=true
simulated_sell_fill=true
performance_metrics_excluded=true
```

## Simulated BUY Fill

Artifact:

```text
.runtime/operations/demo_special_fill/2026-06-29/simulated_buy_fill.json
```

Content:

```text
internal_code=92560
broker_issue_code=9256
side=BUY
quantity=100
fill_price=5410
fill_notional=541000
lifecycle=SIMULATED_FILLED
broker_confirmed_fill=false
simulated_fill=true
demo_special_rule=true
simulation_reason=demo_9000_series_non_fill_rule
performance_metrics_excluded=true
raw_response_saved=false
secret_saved=false
```

## Simulated SELL Fill

Artifact:

```text
.runtime/operations/demo_special_fill/2026-06-29/simulated_sell_fill.json
```

Content:

```text
internal_code=92560
broker_issue_code=9256
side=SELL
quantity=100
fill_price=5410
fill_notional=541000
lifecycle=SIMULATED_FILLED
sell_reason=demo_special_fill_simulation_close
exit_source=demo_lifecycle_test
broker_confirmed_fill=false
simulated_fill=true
demo_special_rule=true
simulation_reason=demo_9000_series_non_fill_rule
performance_metrics_excluded=true
raw_response_saved=false
secret_saved=false
```

## Broker State

Broker read-only state remains unchanged:

```text
Broker Orders: 1
Broker Executions: 0
Broker Positions: 0
Existing BUY status: 未約定
```

This confirms the simulation did not create or claim a broker-confirmed execution.

## Persistent Demo Ledger

Persistent Demo Ledger was updated with simulation-only records:

```text
execution_history_count=2
position_history_count=1
simulated_execution_count=2
simulated_position_count=1
demo_special_fill_simulation_used=true
performance_metrics_excluded=true
broker_snapshot_overwrites_demo_ledger=false
raw_response_saved=false
secret_saved=false
```

The simulated position state is:

```text
OPENED_THEN_CLOSED_BY_SIMULATION
net_quantity=0
```

## Fill Monitor

Executed:

```bash
python3 scripts/run_fill_monitor.py --trade-date 2026-06-29 --root .runtime/operations
```

Result:

```text
status=PASS
BUY lifecycle=SIMULATED_FILLED
SELL lifecycle=SIMULATED_FILLED
broker_confirmed_fill=false
performance_metrics_excluded=true
```

The original broker BUY order remains visible as `ACCEPTED`; simulation events are separately labeled.

## Reconcile

Executed:

```bash
python3 scripts/run_reconcile.py --trade-date 2026-06-29 --root .runtime/operations
```

Result:

```text
status=PASS
reconcile_classification=DEMO_SPECIAL_SIMULATION_RECONCILED
broker_executions_count=0
broker_positions_count=0
simulated_buy_fill=true
simulated_sell_fill=true
broker_confirmed_fill=false
```

## Daily Report / Audit

Daily Report includes:

```text
Demo Special Fill Simulation
broker_confirmed_fill=false
performance_metrics_excluded=true
not production evidence
```

Operation Audit includes:

```text
demo_special_fill_simulation_used=true
production_enabled=false
performance_metrics_excluded=true
broker_confirmed_fill=false
raw_response_saved=false
secret_saved=false
```

## Tests

Executed:

```bash
python3 -m pytest tests/phase12/test_demo_special_fill_simulation.py tests/phase12/test_persistent_demo_ledger.py tests/phase12/test_operations_fill_monitor_states.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/operations/demo_ledger.py scripts/run_demo_special_fill_simulation.py tests/phase12/test_demo_special_fill_simulation.py
```

Results:

```text
pytest=9 passed
py_compile=PASS
```

## Safety Confirmation

```text
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

- Broker-confirmed fill remains unavailable for 9256 due to the Tachibana Demo 9000-series rule.
- This simulation must not be used as Production evidence.
- If network execution approval becomes available later, the Phase12-AA matched opposite Demo SELL path can still be used for real Demo matching confirmation.
