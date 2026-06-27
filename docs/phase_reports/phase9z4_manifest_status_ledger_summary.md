# Phase9-Z4 Manifest Status / Ledger Summary Metadata

- status: PASS
- backup_path: .runtime/phase9/ledger/backups/phase9z4_before_summary_metadata_fix_20260625_075828.json

## Manifest

- before: UNIFIED_DAILY_RUNNER_COMPLETED
- after: UNIFIED_DAILY_RUNNER_COMPLETED

## Ledger Summary

- before: `{"trade_count": 6, "realized_pnl": "0", "unrealized_pnl": "47100.0", "total_equity": "1047100.0", "cash": "163400.0", "market_value": "883700.0", "positions_count": 6, "pending_orders_count": 1, "last_execution_date": "2026-06-24", "last_valuation_date": "2026-06-24"}`
- after: `{"trade_count": 6, "realized_pnl": "0", "unrealized_pnl": "47100.0", "total_equity": "1047100.0", "cash": "163400.0", "market_value": "883700.0", "positions_count": 6, "pending_orders_count": 1, "last_execution_date": "2026-06-24", "last_valuation_date": "2026-06-24"}`

## Checks

- manifest_status_present: PASS UNIFIED_DAILY_RUNNER_COMPLETED
- ledger_summary_present: PASS {"cash": "163400.0", "last_execution_date": "2026-06-24", "last_valuation_date": "2026-06-24", "market_value": "883700.0", "pending_orders_count": 1, "positions_count": 6, "realized_pnl": "0", "total_equity": "1047100.0", "trade_count": 6, "unrealized_pnl": "47100.0"}
- top_level_trade_count_present: PASS 6
- top_level_realized_pnl_present: PASS 0
- top_level_unrealized_pnl_matches_positions: PASS 47100.0 vs 47100.0
- top_level_market_value_matches_positions: PASS 883700.0 vs 883700.0
- top_level_total_equity_matches_cash_market_value: PASS 1047100.0 vs 1047100.0
- positions_count_matches_positions: PASS 6
- pending_orders_count_matches_pending_orders: PASS 1
- last_execution_date_present: PASS 2026-06-24
- last_valuation_date_present: PASS 2026-06-24
- cash_unchanged: PASS 163400.0 -> 163400.0
- positions_unchanged: PASS 
- pending_orders_unchanged: PASS 
- pytest_paper_trading: PASS 199 passed in 3.31s
- phase9v: PASS }
- phase9w: PASS }
- phase9y: PASS }
- phase9z: PASS }
- phase9z3: PASS }
