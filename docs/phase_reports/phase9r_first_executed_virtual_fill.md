# Phase9-R First Executed Virtual Fill

- audit_status: PASS
- status: FIRST_VIRTUAL_FILL_EXECUTED
- execution_date: 2026-06-16
- pending_orders_before: 5
- filled_order_count: 5
- no_fill_order_count: 0
- cash_before: 1000000
- cash_after: 283330.0
- positions_before: 0
- positions_after: 5
- realized_pnl: 0
- unrealized_pnl: 0.0
- trade_count: 5
- ledger_latest_updated: true

## Position List

- 15790 qty=200 avg=846.8 market_value=169360.0 unrealized_pnl=0.0
- 166A0 qty=100 avg=1091.0 market_value=109100.0 unrealized_pnl=0.0
- 213A0 qty=300 avg=544.7 market_value=163410.0 unrealized_pnl=0.0
- 221A0 qty=100 avg=1538.0 market_value=153800.0 unrealized_pnl=0.0
- 30630 qty=100 avg=1210.0 market_value=121000.0 unrealized_pnl=0.0

## Paths

- ledger_snapshot_dir: .runtime/phase9/ledger_runs/2026-06-16_first_virtual_fill
- execution_record_path: .runtime/phase9/ledger/executions/2026-06-16_executions.json

## Checks

- average_cost_matches_open_price: true
- broker_order_not_called: true
- cash_decreased_correctly: true
- dry_run_latest_not_updated_temp: true
- execute_latest_updated_reported: true
- execution_record_saved: true
- filled_no_fill_reported: true
- ledger_snapshots_saved: true
- no_fill_preserved_temp: true
- open_d_not_started: true
- pending_order_5_processed: true
- pending_orders_cleared: true
- performance_trade_count_5: true
- positions_created: true
- real_trade_not_executed: true
- realized_pnl_zero: true
- unlock_trade_not_called: true
- unrealized_pnl_zero: true

## Boundary

- broker_order_api_called: false
- open_d_started: false
- unlock_trade_called: false
- real_trade_executed: false

## Next Action

Proceed to Phase9-S daily report/tracker update for the first filled trading day.
