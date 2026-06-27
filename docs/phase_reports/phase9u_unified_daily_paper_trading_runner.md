# Phase9-U Unified Daily Paper Trading Runner

- status: UNIFIED_DAILY_RUNNER_COMPLETED
- run_date: 2026-06-26
- mode: paper-trading
- launchd_command: `python3 scripts/run_aifundlab_daily_paper_trading.py --mode paper-trading --approval-mode auto_for_paper_trading --allow-api-fetch`

## Business Dates

- run_date: 2026-06-26
- business_date: 2026-06-26
- market_data_target_date: 2026-06-26
- data_target_date: 2026-06-26
- decision_for: 2026-06-26
- valuation_date: 2026-06-26
- latest_available_quote_date: 2026-06-26
- virtual_order_date: 2026-06-29
- virtual_execution_date: 2026-06-29

## Step Statuses

- run_lock: ACQUIRED
- business_date_resolve: {'run_date': '2026-06-26', 'business_date': '2026-06-26', 'market_data_target_date': '2026-06-26', 'data_target_date': '2026-06-26', 'decision_for': '2026-06-26', 'valuation_date': '2026-06-26', 'latest_available_quote_date': '2026-06-25', 'virtual_order_date': '2026-06-29', 'virtual_execution_date': '2026-06-29'}
- market_data_refresh: MARKET_DATA_READY_FOR_LATEST_AVAILABLE
- market_data_refresh_context: {'requested_from_date': '2026-06-26', 'requested_to_date': '2026-06-26', 'data_until': '2026-06-26', 'latest_successful_daily_quotes_date': '2026-06-26', 'latest_normalized_daily_quotes_date': '2026-06-26', 'jquants_api_fetch_executed': True}
- canonical_normalized_update: CANONICAL_NORMALIZED_UPDATED
- business_date_resolve_after_market_refresh: {'run_date': '2026-06-26', 'business_date': '2026-06-26', 'market_data_target_date': '2026-06-26', 'data_target_date': '2026-06-26', 'decision_for': '2026-06-26', 'valuation_date': '2026-06-26', 'latest_available_quote_date': '2026-06-26', 'virtual_order_date': '2026-06-29', 'virtual_execution_date': '2026-06-29'}
- feature_refresh_audit: FEATURE_REFRESH_REQUIRED
- feature_refresh_execute: FEATURES_READY
- feature_refresh: FEATURES_READY
- virtual_fill: NO_DUE_PENDING_ORDERS
- ledger_valuation: LEDGER_VALUATION_UPDATED
- valuation_context: {'run_date': '2026-06-26', 'decision_for': '2026-06-26', 'data_target_date': '2026-06-26', 'business_date': '2026-06-26', 'market_data_target_date': '2026-06-26', 'latest_available_quote_date': '2026-06-26', 'valuation_date': '2026-06-26', 'quote_source_path': '.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet', 'quote_source_max_date': '2026-06-26', 'stale_price_source': False, 'market_data_refresh_status': 'MARKET_DATA_READY_FOR_LATEST_AVAILABLE'}
- daily_inference: INFERENCE_READY
- auto_approval: CREATED
- pending_order_creation: 0
- pending_order_dedup_skipped_count: 0
- tracker_update: TRACKER_UPDATED
- blog_report_v2: BLOG_REPORT_V2_READY
- line_notification: SENT
- discord_notification: SENT
- notification_context: {'line_notification': 'SENT', 'discord_notification': 'SENT', 'summary': {'run_date': '2026-06-26', 'runner_status': 'UNIFIED_DAILY_RUNNER_COMPLETED', 'status_label': 'COMPLETED', 'total_equity': '995600.0', 'total_equity_display': '995,600円', 'pnl': '-4400.0', 'pnl_display': '-4,400円', 'pnl_rate': '-0.4400', 'pnl_rate_display': '-0.44%', 'positions_count': 7, 'pending_orders_count': 0, 'filled_order_count': 0, 'next_candidate_count': 5}, 'line': {'status': 'SENT', 'dry_run': False, 'http_status': 200, 'message_preview': 'AI Fund Lab 日次結果 2026-06-26\n\nstatus: COMPLETED\n資産: 995,600円\n損益: -4,400円 / -0.44%\n保有: 7\npending: 0\n本日約定: 0\n次回候補: 5\n\nReport:\nreports/public/phase9_daily/2026-0...', 'error_type': '', 'provider': 'line'}, 'discord': {'status': 'SENT', 'dry_run': False, 'http_status': 204, 'content_preview': 'AI Fund Lab 日次レポート 2026-06-26\nstatus: COMPLETED\n資産: 995,600円\n損益: -4,400円 / -0.44%\nReport: reports/public/phase9_daily/2026-06-26_blog_report_v4.md\n\n## 資産状況\n\n...', 'error_type': '', 'provider': 'discord'}, 'secrets_redacted': True, 'broker_order_api_called': False, 'open_d_started': False, 'unlock_trade_called': False, 'real_trade_executed': False, 'virtual_fill_executed': False, 'model_retraining_executed': False}

## Reports

- blog_report_v2: reports/public/phase9_daily/2026-06-26_blog_report_v4.md

