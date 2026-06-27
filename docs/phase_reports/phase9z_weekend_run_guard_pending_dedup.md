# Phase9-Z Weekend Run Guard + Pending Order Dedup Recovery

- status: PASS
- root_cause: launchd ran on Saturday, CLI rounded no-date paper-trading execution to the previous weekday, and pending order creation only deduped by order_id, so regenerated order_ids duplicated the same planned buys.

## Recovery

- before_pending_count: 10
- after_pending_count: 5
- removed_count: 5
- backup_path: .runtime/phase9/ledger/backups/phase9z_before_pending_dedup_20260620T212958.json

## Checks

- PASS: recovery_before_pending_10 10
- PASS: recovery_after_pending_5 5
- PASS: recovery_removed_5 5
- PASS: backup_exists .runtime/phase9/ledger/backups/phase9z_before_pending_dedup_20260620T212958.json
- PASS: current_state_valid_after_recovery_or_fill {"cash": "163400.0", "positions_count": 6, "pending_order_count": 1, "trade_count": 6, "last_execution_date": "2026-06-24", "virtual_execution_dates": ["2026-06-25"], "pending_orders": [{"order_id": "phase9_l2_order_4694bf6cb46149c080150d0d84e9fc8b", "code": "61810", "side": "BUY", "quantity": "200", "virtual_execution_date": "2026-06-25", "created_at": "2026-06-24T11:00:49.171324+00:00"}]}
- PASS: non_business_day_guard_skips NON_BUSINESS_DAY_SKIPPED
- PASS: weekend_guard_does_not_round_to_friday 2026-06-20
- PASS: holiday_guard_skips NON_BUSINESS_DAY_SKIPPED
- PASS: holiday_guard_uses_jquants_calendar {"calendar_path": ".runtime/phase9/audits/phase9z/holiday/calendar.parquet", "calendar_source": "jquants_trading_calendar", "date": "2026-09-21", "hol_div": "0", "is_business_day": false, "reason": "JQUANTS_NON_BUSINESS_DAY", "warning": ""}
- PASS: calendar_missing_fail_closed {"calendar_path": ".runtime/phase9/audits/phase9z/calendar_missing/missing.parquet", "calendar_source": "fail_closed", "date": "2026-09-24", "hol_div": null, "is_business_day": false, "reason": "TRADING_CALENDAR_MISSING", "warning": "trading_calendar_missing_fail_closed"}
- PASS: business_day_after_holiday_not_skipped FAKE_UNIFIED_RUNNER_COMPLETED
- PASS: same_decision_for_dedup {"first_status": "PENDING_ORDERS_CREATED", "first_pending_count": 5, "dedup_status": "PENDING_ORDERS_DEDUP_SKIPPED", "dedup_skipped_count": 5, "pending_count_after_second": 5}
- PASS: pytest_paper_trading_pass 199 passed in 3.36s
- PASS: phase9v_audit_pass }
- PASS: phase9w_audit_pass }
- PASS: phase9y_audit_pass }

## Forbidden Actions

- broker_order: False
- open_d: False
- unlock_trade: False
- real_trade: False
- ai_retraining: False
- full_backtest: False
- scheduler_change: False
- launchd_plist_change: False
- positions_change: False
- cash_change: False
- virtual_fill_execution: False
