# Phase11-Z Integrated Safety Backtest Audit Full 5Y

- status: PASS
- audit_profile: stress_injection
- period: 2025-06-01 to 2025-12-31
- business_day_count: 153
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false

## Performance

- initial_cash: 1000000.0
- final_equity: 1002100.0
- total_return: 0.0021
- annualized_return: 0.003365
- max_drawdown: -0.088358
- trade_count: 26
- trade_count_definition: buy_fill_count + sell_fill_count
- buy_fill_count: 16
- sell_fill_count: 10
- round_trip_count: 10
- closed_trades_count: 10
- winning_closed_trades: 5
- losing_closed_trades: 5
- breakeven_closed_trades: 0
- realized_profit: 6000.0
- realized_loss: -6400.0
- win_rate: 0.5
- profit_factor: 0.9375
- average_realized_pnl: -40.0
- average_holding_days: 80.6
- performance_metrics_placeholder: false
- exposure_ratio: 0.508644

## Flow Counts

- ai_signal_days: 153
- candidate_generated_days: 153
- candidate_count_total: 918
- order_plan_generated_days: 153
- orders_generated: 299
- orders_before_safety: 299
- orders_allowed_by_safety: 260
- orders_blocked_by_safety: 28
- orders_review_required: 16
- orders_emergency_stopped: 80
- buy_orders_submitted: 16
- sell_orders_submitted: 10
- buy_fill_count: 16
- sell_fill_count: 10
- round_trip_count: 10
- position_open_count: 16
- position_close_count: 10
- final_position_count: 6
- virtual_orders_submitted: 26
- virtual_fills: 26
- ledger_entry_count: 26
- candidate_universe_size: 60
- fixed_4_code_stub_used: false
- periodic_mock_emergency_injection_enabled: true
- normal_market_profile: false
- stress_injection_profile: true
- trade_count_definition: trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count
- recovery_candidate_count_definition: event/check count, not unique days; see state_residency_days for day count

## Safety

- safety_check_count: 153
- ALLOW_count: 395
- BLOCK_count: 19
- REVIEW_REQUIRED_count: 25
- EMERGENCY_STOP_count: 13
- BUY_STOP_days: 37
- RECOVERY_CANDIDATE_count: 11
- MANUAL_APPROVED_count: 28
- individual_warning_count: 7
- stop_loss_candidate_count: 6
- emergency_candidate_count: 5
- market_crash_guard_count: 9
- quote_stale_guard_count: 6
- duplicate_order_guard_count: 3
- cash_buffer_guard_count: 2
- max_exposure_guard_count: 3
- broker_divergence_guard_count: 3
- daily_loss_guard_count: 3

## State Residency Days

- NORMAL: 84
- WARNING: 8
- BUY_STOP: 6
- EMERGENCY_STOP: 45
- RECOVERY_CANDIDATE: 1
- MANUAL_APPROVED: 9

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

- market_crash_became_buy_stop: true
- buy_stop_blocked_new_buy: true
- recovery_candidate_did_not_auto_normal: true
- manual_approval_required_for_normal: true
- manual_approval_simulated: true
- emergency_blocked_order_flow: true
- quote_stale_blocked_inferred_trade: true
- broker_divergence_review_or_emergency: true
- fixed_4_code_stub_used: false
- audit_profile: stress_injection
- periodic_mock_emergency_injection_enabled: true
- normal_market_mock_boolean_crash_triggered: false
- recovery_candidate_to_normal_bypass: false
- performance_metrics_placeholder: false
- stress_results_separated_from_normal_performance: true

## Market Crash Input

- market_crash_source: synthetic_stress_injection
- index_return: profile_generated
- candidate_universe_drawdown: profile_generated
- extreme_down_ratio: profile_generated
- stop_limit_candidate_ratio: profile_generated
- is_synthetic: true
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
- stress_profile_enabled: true
- stress_injection_triggered_safety: true

## Data Use

Phase11-Z audit result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_STRESS_INJECTION_AUDIT_PASS
PHASE11Z_NORMAL_MARKET_RESULT_REQUIRED_FOR_FULL_5Y
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
