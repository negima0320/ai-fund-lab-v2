# Phase12-K Operations Feature Freshness / Ledger Reconciliation Fix

## Final Status

```text
PHASE12K_OPERATIONS_FEATURE_FRESHNESS_AND_LEDGER_RECONCILIATION_COMPLETE
DEMO_ORDER_WIRE_EXECUTION_REMAINS_LOCKED
PRODUCTION_ORDER_EXECUTION_NOT_EXECUTED
LINE_SEND_NOT_EXECUTED
AI_RETRAINING_NOT_EXECUTED
BACKTEST_NOT_RERUN
```

Phase12-K fixed the two Phase12-J blockers:

1. Feature freshness now resolves `latest_available_market_date` instead of forcing features for the decision date.
2. Operations ledger artifacts are generated from Broker read-only artifacts, and Reconcile reads them.

No Demo order wire execution, `CLMKabuNewOrder`, Production order, LINE send, AI retraining, or Backtest was executed.

## Changed Files

- `src/ai_fund_lab_v2/operations/__init__.py`
- `src/ai_fund_lab_v2/operations/ledger.py`
- `src/ai_fund_lab_v2/operations/market_refresh.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/phase12/test_operations_feature_freshness_and_ledger.py`

## Feature Freshness Fix

`run_market_refresh.py` now separates:

```text
decision_for = 2026-06-29
latest_available_market_date = 2026-06-26
data_until = 2026-06-26
```

This avoids forcing feature generation against a same-day J-Quants daily quote that is not yet distributed.

Smoke result:

```text
run_market_refresh.py: PASS
jquants_api_fetch_executed=true
raw_daily_quotes_updated=true
canonical_normalized_updated=true
feature_refresh_executed=true
feature_freshness_status=FEATURE_READY
data_quality_status=PASS
candidate_feature_path=.runtime/operations/feature_artifacts/2026-06-26/candidate_features.parquet
```

The Operations feature refresh also writes a feature-local listed info artifact under a `jquants` path so source audits remain J-Quants-only while aligning listed info to the resolved feature date.

## BUY / SELL Result

`run_daily_plan.py` now records explicit zero reasons.

```text
run_daily_plan.py: PASS
BUY count: 0
BUY zero reason: candidate_no_universe_eligible_rows
SELL count: 0
SELL zero reason: no_valid_broker_positions
```

BUY is no longer 0 because features are missing. It is 0 because no candidate passed the current universe hard gate for `2026-06-26`.

SELL remains 0 because Tachibana Demo read-only returned 7 source position rows, but they were empty slots. The writer filtered them to `valid_positions_count=0`.

## Operations Ledger

Added Operations ledger artifacts:

```text
.runtime/operations/ledger/2026-06-29/ledger_state.json
.runtime/operations/ledger/2026-06-29/ledger_update_manifest.json
.runtime/operations/ledger/2026-06-29/ledger_summary.json
```

Ledger smoke result:

```text
status=PASS
source=broker_readonly_snapshot
positions_count=0
orders_count=0
executions_count=0
buying_power_available=true
buying_power=20000000
market_value_estimate=0
total_equity_estimate=20000000
empty_broker_state_handled=true
raw_response_saved=false
secret_saved=false
```

Empty broker state is now a valid classification:

```text
positions: NO_POSITIONS
orders: NO_ORDERS
executions: SKIPPED_NO_ORDERS
```

The ledger is explicitly not an AI training input.

## Reconciliation

`run_reconcile.py` now reads:

- broker snapshot
- broker positions
- broker orders
- broker executions
- broker buying power
- ledger state
- ledger update manifest
- fill monitor
- safety monitor
- daily plan
- approval
- daily report

Smoke result:

```text
run_reconcile.py: PASS
missing=[]
ledger_state.status=PASS
ledger_state.empty_broker_state=true
```

This closes the Phase12-J `ledger missing` gap.

## Daily Report / Audit

Daily Report now includes:

- market data status
- feature freshness status
- latest available market date
- decision_for
- BUY count / BUY zero reason
- SELL count / SELL zero reason
- ledger status
- broker positions / orders / executions counts
- buying power availability
- reconcile status

Operation Audit now records the same feature and ledger status.

Smoke result:

```text
run_operation_audit.py: PASS
no_production_order_audit=true
secret_audit=true
raw_response_audit=true
```

`run_daily_report.py` generated the report artifact, but returned `BLOCK` because the existing same-date daily manifest still contains an earlier `submit_status=BLOCK` from a previous approval-missing dry-run history. No order was sent.

## Safety Confirmation

```text
broker_order_api_called=false
demo_order_wire_execution=false
demo_order_executed=false
production_order_executed=false
production_unlock_executed=false
line_send_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_response_saved=false
secret_saved=false
```

AI contamination guard:

```text
broker_snapshot_used_for_ai_training=false
paper_ledger_used_for_ai_training=false
operations_ledger_used_for_ai_training=false
safety_result_used_for_ai_training=false
audit_result_used_for_ai_training=false
cash_portfolio_pnl_used_for_ai_training=false
```

Phase9 was not modified:

```text
phase9_artifact_modified=false
phase9_launchd_modified=false
phase9_cli_modified=false
```

## Tests

```text
PYTHONPYCACHEPREFIX=.runtime/operations/pycache_phase12k python3 -m py_compile ...
PASS

python3 -m pytest tests/phase12 -q
31 passed

JSON validation
PASS
```

## Smoke Commands

Executed:

```bash
python3 scripts/run_market_refresh.py --trade-date 2026-06-29 --from-date 2026-05-01 --fetch-mode per-date --allow-api-fetch --root .runtime/operations
python3 scripts/run_preflight.py --trade-date 2026-06-29 --root .runtime/operations --refresh-broker-readonly
python3 scripts/run_daily_plan.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_fill_monitor.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_safety_monitor.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_reconcile.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_operation_audit.py --root .runtime/operations
```

Not executed:

```text
run_demo_submit.py
CLMKabuNewOrder
Demo order wire execution
Production order
LINE send
AI retraining
Backtest
```

## Remaining Gaps

1. BUY remains 0 because no candidate passed the current universe hard gate for the resolved feature date.
2. SELL remains 0 because valid broker positions count is 0.
3. Preflight remains `REVIEW_REQUIRED` until second password file configuration is present for the later order-approval path.
4. Daily report CLI returned `BLOCK` due to earlier same-date `submit_status=BLOCK` history; report artifact generation succeeded.
5. Demo order wire execution remains locked and requires a separate design review.

## Next Phase

```text
PHASE12-L_DEMO_WIRE_UNLOCK_PREFLIGHT_DESIGN_REVIEW
```
