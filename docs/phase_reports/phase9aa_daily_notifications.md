# Phase9-AA Daily Notification Integration

- status: PASS
- LINE env: AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN, AIFUNDLAB_LINE_TO_ID
- Discord env: AIFUNDLAB_DISCORD_WEBHOOK_URL

## Checks

- line_dry_run_sent: PASS SENT
- discord_dry_run_sent: PASS SENT
- non_fatal_failure_line: PASS FAILED_NON_FATAL
- non_fatal_failure_discord: PASS FAILED_NON_FATAL
- secrets_redacted: PASS 
- summary_contains_counts: PASS {"run_date": "2026-06-22", "runner_status": "UNIFIED_DAILY_RUNNER_COMPLETED", "status_label": "COMPLETED", "total_equity": "1010400", "total_equity_display": "1,010,400\u5186", "pnl": "10400", "pnl_display": "+10,400\u5186", "pnl_rate": "1.0400", "pnl_rate_display": "+1.04%", "positions_count": 1, "pending_orders_count": 0, "filled_order_count": 5, "next_candidate_count": 5}
- pytest_paper_trading: PASS 199 passed in 3.30s
- phase9v: PASS }
- phase9w: PASS }
- phase9y: PASS }
- phase9z: PASS }
- phase9z3: PASS }
- phase9z4: PASS }
