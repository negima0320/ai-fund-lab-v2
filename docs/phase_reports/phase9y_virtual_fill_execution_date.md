# Phase9-Y Virtual Fill Execution Date Audit

- status: PASS
- root_cause: Unified Runner detected due orders by virtual_execution_date <= run_date, but passed run_date as the fill execution_date. A delayed data retry could fill with the retry day's open instead of the original virtual_execution_date open.

## Existing Pending Orders

- pending_order_count: 1
- virtual_execution_dates: ['2026-06-25']

## Checks

- PASS: existing_ledger_read_only 76319adee0c9f0b011564920592cc7cd7f37598da7c8228770682ecccc3fc65b->76319adee0c9f0b011564920592cc7cd7f37598da7c8228770682ecccc3fc65b
- PASS: existing_ledger_pending_or_filled_state_valid {"ledger_exists": true, "pending_order_count": 1, "positions_count": 6, "cash": "163400.0", "trade_count": 6, "last_execution_date": "2026-06-24", "virtual_execution_dates": ["2026-06-25"], "orders": [{"order_id": "phase9_l2_order_4694bf6cb46149c080150d0d84e9fc8b", "code": "61810", "side": "BUY", "quantity": "200", "status": "APPROVED", "created_at": "2026-06-24T11:00:49.171324+00:00", "virtual_order_date": "2026-06-25", "virtual_execution_date": "2026-06-25"}]}
- PASS: run_date_2026_06_23_fills_2026_06_22_open 1000
- PASS: run_date_2026_06_23_does_not_use_2026_06_23_open 1000
- PASS: quotes_missing_keeps_pending {"status": "DATA_NOT_READY", "blocked_reasons": ["execution_date_quotes_missing"], "pending_orders_after": 1, "cash_after": "1000000"}
- PASS: mixed_execution_dates_grouped ['2026-06-22', '2026-06-23']
- PASS: mixed_execution_dates_use_own_open {"10010": "1000", "20020": "2000"}
- PASS: manifest_separates_run_and_fill_dates {"result_run_date": "2026-06-23", "result_fill_execution_date": "2026-06-22", "run_date": "2026-06-23", "execution_date": "2026-06-22", "fill_execution_date": "2026-06-22"}
- PASS: broker_order_not_called 
- PASS: open_d_not_started 
- PASS: unlock_trade_not_called 

## Forbidden Actions

- broker_order: False
- open_d: False
- unlock_trade: False
- real_trade: False
- ai_retraining: False
- full_backtest: False
- scheduler_change: False
- launchd_plist_change: False
- production_ledger_manual_mutation: False
