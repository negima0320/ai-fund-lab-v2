# Phase12-J J-Quants / Demo Broker Read-only Mainline Integration

## Final Status

```text
PHASE12J_JQUANTS_BROKER_READONLY_MAINLINE_INTEGRATION_COMPLETE
DEMO_ORDER_WIRE_EXECUTION_REMAINS_LOCKED
PRODUCTION_ORDER_EXECUTION_NOT_EXECUTED
LINE_SEND_NOT_EXECUTED
AI_RETRAINING_NOT_EXECUTED
BACKTEST_NOT_RERUN
```

Phase12-J connected the Operations mainline to:

- J-Quants market refresh under `.runtime/operations`.
- Tachibana Demo read-only broker artifact writer.
- Preflight / Safety Monitor / Fill Monitor / Reconcile / Daily Report / Operation Audit broker read-only inputs.
- Daily Plan feature BUY input and broker position SELL input checks.

No Demo order wire execution, `CLMKabuNewOrder`, Production order, LINE send, AI retraining, or Backtest was executed.

## Changed Files

- `scripts/run_market_refresh.py`
- `scripts/run_preflight.py`
- `src/ai_fund_lab_v2/operations/__init__.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/market_refresh.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/phase12/test_operations_jquants_broker_mainline_integration.py`

## J-Quants Mainline

`run_market_refresh.py` now supports Operations-scoped real J-Quants refresh:

```bash
python3 scripts/run_market_refresh.py \
  --trade-date 2026-06-29 \
  --from-date 2026-06-01 \
  --fetch-mode per-date \
  --allow-api-fetch \
  --root .runtime/operations
```

Smoke result:

```text
status=PASS
jquants_api_fetch_executed=true
raw_daily_quotes_updated=true
canonical_normalized_updated=true
feature_refresh_executed=true
data_quality_status=REVIEW_REQUIRED
```

The data path is isolated from Phase9:

```text
.runtime/operations/jquants/raw/
.runtime/operations/jquants/raw_normalized/
.runtime/operations/feature_artifacts/
.runtime/operations/market_refresh/YYYY-MM-DD/
.runtime/operations/feature_refresh/YYYY-MM-DD/
.runtime/operations/data_quality/YYYY-MM-DD/
```

Same-day feature freshness was not fully satisfied during the smoke. J-Quants read succeeded, but candidate feature generation remained `FEATURE_REFRESH_REQUIRED` because the 2026-06-29 normalized daily quotes were not yet fresh enough for the feature builder.

## Broker Read-only Mainline

`run_preflight.py` now supports Demo broker read-only refresh:

```bash
python3 scripts/run_preflight.py \
  --trade-date 2026-06-29 \
  --root .runtime/operations \
  --refresh-broker-readonly
```

Smoke result:

```text
preflight_status=REVIEW_REQUIRED
reason=TACHIBANA_API_SECOND_PASSWORD_FILE missing
broker_demo_readonly_api_called=true
raw_response_saved=false
secret_saved=false
```

Artifacts written:

```text
.runtime/operations/broker_readonly_source/2026-06-29/tachibana_demo_snapshot.json
.runtime/operations/broker_snapshot/2026-06-29/broker_snapshot.json
.runtime/operations/broker_positions/2026-06-29/positions.json
.runtime/operations/broker_orders/2026-06-29/orders.json
.runtime/operations/broker_executions/2026-06-29/executions.json
.runtime/operations/broker_buying_power/2026-06-29/buying_power.json
.runtime/operations/broker_account_summary/2026-06-29/account_summary.json
.runtime/operations/broker_quotes/2026-06-29/quotes.json
.runtime/operations/broker_snapshot_summary/2026-06-29/broker_snapshot_summary.json
```

Broker snapshot summary:

```text
source_positions_count=7
valid_positions_count=0
orders_count=0
executions_count=0
executions_classification=SKIPPED_NO_ORDERS
buying_power_available=true
buying_power=20000000
```

The source snapshot contained 7 position rows, but they were empty broker slots with no issue code and zero quantity. The artifact writer filters those out before feeding Operations positions / SELL logic.

## Daily Plan

`run_daily_plan.py` now checks:

- market refresh manifest
- feature refresh manifest
- feature BUY candidate artifact
- broker read-only positions artifact
- Exit Adapter SELL generation

Smoke result:

```text
status=PASS
buy_item_count=0
sell_item_count=0
feature_buy_adapter.status=NO_FEATURE_ARTIFACT
feature_buy_adapter.reason=candidate_feature_path_missing
exit_adapter.status=PASS
exit_adapter.exit_source=broker_readonly
```

BUY stayed 0 because same-day candidate feature artifact was not generated. SELL stayed 0 because valid broker positions count was 0.

## Monitor / Reconcile / Report / Audit

| Step | Result |
|---|---|
| Fill Monitor | `PASS`, `SKIPPED_NO_ORDERS` |
| Safety Monitor | `PASS` |
| Reconcile | `REVIEW_REQUIRED`, missing `ledger` |
| Daily Report | artifact generated, daily manifest remained `BLOCK` from earlier approval-missing submit history |
| Operation Audit | `PASS` |

Reconcile now reads broker snapshot, positions, orders, executions, and buying power artifacts. Ledger is still not connected, so `REVIEW_REQUIRED` is expected.

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

AI contamination guards remain:

```text
broker_snapshot_used_for_ai_training=false
paper_ledger_used_for_ai_training=false
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
PYTHONPYCACHEPREFIX=.runtime/operations/pycache_phase12j python3 -m py_compile ...
PASS

python3 -m pytest tests/phase12 -q
28 passed

JSON validation
PASS
```

## Remaining Gaps

1. J-Quants same-day feature freshness can still be `REVIEW_REQUIRED` before daily quotes are distributed.
2. BUY item generation is connected, but remained 0 in the live smoke because candidate features were not available for 2026-06-29.
3. SELL item generation is connected, but remained 0 because valid Demo broker positions were 0 after empty slot filtering.
4. Ledger artifact is still not connected to Operations reconciliation.
5. Demo order wire execution remains locked and requires a separate unlock phase.

## Next Phase

```text
PHASE12-K_OPERATIONS_FEATURE_FRESHNESS_AND_LEDGER_RECONCILIATION
```
