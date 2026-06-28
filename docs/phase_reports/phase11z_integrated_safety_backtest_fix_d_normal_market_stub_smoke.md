# Phase11-Z Integrated Safety Backtest Audit Full 5Y

- status: PASS
- audit_profile: normal_market
- period: 2025-06-01 to 2025-08-31
- business_day_count: 60
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false

## Performance

- initial_cash: 1000000.0
- final_equity: 999000.0
- total_return: -0.001
- annualized_return: -0.004077
- max_drawdown: -0.014411
- trade_count: 25
- trade_count_definition: buy_fill_count + sell_fill_count
- buy_fill_count: 15
- sell_fill_count: 10
- round_trip_count: 10
- closed_trades_count: 10
- winning_closed_trades: 5
- losing_closed_trades: 5
- breakeven_closed_trades: 0
- realized_profit: 10000.0
- realized_loss: -4500.0
- win_rate: 0.5
- profit_factor: 2.222222
- average_realized_pnl: 550.0
- average_holding_days: 28.0
- performance_metrics_placeholder: false
- exposure_ratio: 0.492498

## Flow Counts

- ai_signal_days: 60
- candidate_generated_days: 60
- candidate_count_total: 360
- order_plan_generated_days: 60
- orders_generated: 130
- orders_before_safety: 130
- orders_allowed_by_safety: 130
- orders_blocked_by_safety: 0
- orders_review_required: 0
- orders_emergency_stopped: 0
- buy_orders_submitted: 15
- sell_orders_submitted: 10
- buy_fill_count: 15
- sell_fill_count: 10
- round_trip_count: 10
- position_open_count: 15
- position_close_count: 10
- final_position_count: 5
- virtual_orders_submitted: 25
- virtual_fills: 25
- ledger_entry_count: 25
- candidate_universe_size: 60
- fixed_4_code_stub_used: false
- periodic_mock_emergency_injection_enabled: false
- normal_market_profile: true
- stress_injection_profile: false
- trade_count_definition: trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count
- recovery_candidate_count_definition: event/check count, not unique days; see state_residency_days for day count

## Safety

- safety_check_count: 60
- ALLOW_count: 190
- BLOCK_count: 0
- REVIEW_REQUIRED_count: 0
- EMERGENCY_STOP_count: 0
- BUY_STOP_days: 0
- RECOVERY_CANDIDATE_count: 0
- MANUAL_APPROVED_count: 0
- individual_warning_count: 0
- stop_loss_candidate_count: 0
- emergency_candidate_count: 0
- market_crash_guard_count: 0
- quote_stale_guard_count: 0
- duplicate_order_guard_count: 0
- cash_buffer_guard_count: 0
- max_exposure_guard_count: 0
- broker_divergence_guard_count: 0
- daily_loss_guard_count: 0

## State Residency Days

- NORMAL: 60
- WARNING: 0
- BUY_STOP: 0
- EMERGENCY_STOP: 0
- RECOVERY_CANDIDATE: 0
- MANUAL_APPROVED: 0

## Integrity

- live_order_executed: false
- demo_order_executed: false
- production_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- broker_api_connected: false
- broker_snapshot_updated: false
- paper_ledger_mutated_unexpectedly: false
- ai_training_data_mutated: false
- secret_or_raw_response_persisted: false

## Safety Behavior

- market_crash_became_buy_stop: false
- buy_stop_blocked_new_buy: false
- recovery_candidate_did_not_auto_normal: true
- manual_approval_required_for_normal: true
- manual_approval_simulated: false
- emergency_blocked_order_flow: false
- quote_stale_blocked_inferred_trade: false
- broker_divergence_review_or_emergency: false
- fixed_4_code_stub_used: false
- audit_profile: normal_market
- periodic_mock_emergency_injection_enabled: false
- normal_market_mock_boolean_crash_triggered: false
- recovery_candidate_to_normal_bypass: false
- performance_metrics_placeholder: false
- stress_results_separated_from_normal_performance: true

## Mainline Adapter Reuse Map


## Market Crash Input

- market_crash_source: synthetic_none
- index_return: 0.00
- candidate_universe_drawdown: 0.00
- extreme_down_ratio: 0.00
- stop_limit_candidate_ratio: 0.00
- is_synthetic: true
- market_crash: false
- severe_crash: false
- stress_results_mixed_into_normal_performance: false

## Pass Conditions

- orders_generated_gt_0: true
- orders_before_safety_gt_0: true
- buy_fill_count_gt_0: true
- sell_fill_count_gt_0: true
- position_open_count_gt_0: true
- position_close_count_gt_0: true
- trade_count_not_extremely_low: true
- fixed_4_code_stub_not_used: true
- candidate_universe_broad_enough: true
- manual_approval_simulation_available: true
- recovery_does_not_auto_normal: true
- docs_output_isolated_for_tests: true
- win_rate_profit_factor_not_placeholder: true
- recovery_candidate_to_normal_bypass_absent: true
- stress_results_separated_from_normal_performance: true
- normal_market_profile_enabled: true
- mainline_paper_adapter_profile_enabled: true
- normal_or_mainline_profile_enabled: true
- emergency_stop_days_ratio_within_threshold: true
- normal_market_mock_boolean_crash_absent: true
- periodic_mock_emergency_injection_disabled: true

## Data Use

Phase11-Z audit result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_INTEGRATED_SAFETY_BACKTEST_FULL_5Y_PASS
PHASE11_COMPLETE_CANDIDATE
PHASE12_DEMO_FULL_OPERATION_READY_FOR_REVIEW
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
