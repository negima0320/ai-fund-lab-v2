# Phase9-P First Virtual Fill

- audit_status: PASS
- status: DATA_NOT_READY
- execution_date: 2026-06-16
- data_readiness: DATA_NOT_READY
- pending_orders_before: 5
- filled_order_count: 0
- no_fill_order_count: 0
- cash_before: 1000000
- cash_after: 1000000
- positions_before: 0
- positions_after: 0
- ledger_latest_updated: false

## Checks

- actual_missing_data_ledger_unchanged: true
- actual_missing_data_returns_data_not_ready: true
- broker_order_not_called: true
- cash_updates_when_filled: true
- dry_run_ledger_unchanged_with_data: true
- execute_filled_or_no_fill_records_saved: true
- execute_updates_ledger_with_data: true
- no_fill_reason_preserved: true
- open_d_not_started: true
- pending_orders_updated: true
- pnl_snapshot_available: true
- position_created_when_filled: true
- real_trade_not_executed: true
- unlock_trade_not_called: true

## Blocked Reasons

- execution_date_quotes_missing

## Boundary

- broker_order_api_called: false
- open_d_started: false
- unlock_trade_called: false
- real_trade_executed: false
