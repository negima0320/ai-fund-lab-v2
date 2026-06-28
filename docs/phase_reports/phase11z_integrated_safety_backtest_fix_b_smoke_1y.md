# Phase11-Z-Fix-B Integrated Safety Backtest Smoke 1Y

- status: PASS
- period: 2025-06-01 to 2026-05-31
- business_day_count: 260
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false

## Performance

- initial_cash: 1000000.0
- final_equity: 1005400.0
- total_return: 0.0054
- annualized_return: 0.005088
- max_drawdown: -0.088358
- trade_count: 49
- trade_count_definition: buy_fill_count + sell_fill_count
- buy_fill_count: 27
- sell_fill_count: 22
- round_trip_count: 22
- win_rate: 0.0
- profit_factor: 0.0
- average_holding_days: 2.2
- exposure_ratio: 0.450296

## Flow Counts

- ai_signal_days: 260
- candidate_generated_days: 260
- candidate_count_total: 1560
- order_plan_generated_days: 260
- orders_generated: 526
- orders_before_safety: 526
- orders_allowed_by_safety: 464
- orders_blocked_by_safety: 43
- orders_review_required: 24
- orders_emergency_stopped: 214
- buy_orders_submitted: 27
- sell_orders_submitted: 22
- buy_fill_count: 27
- sell_fill_count: 22
- round_trip_count: 22
- position_open_count: 27
- position_close_count: 22
- final_position_count: 5
- virtual_orders_submitted: 49
- virtual_fills: 49
- ledger_entry_count: 49
- candidate_universe_size: 60
- fixed_4_code_stub_used: false
- trade_count_definition: trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count
- recovery_candidate_count_definition: event/check count, not unique days; see state_residency_days for day count

## Safety

- safety_check_count: 260
- ALLOW_count: 695
- BLOCK_count: 33
- REVIEW_REQUIRED_count: 39
- EMERGENCY_STOP_count: 19
- BUY_STOP_days: 53
- RECOVERY_CANDIDATE_count: 18
- MANUAL_APPROVED_count: 18
- individual_warning_count: 10
- stop_loss_candidate_count: 6
- emergency_candidate_count: 8
- market_crash_guard_count: 12
- quote_stale_guard_count: 9
- duplicate_order_guard_count: 6
- cash_buffer_guard_count: 4
- max_exposure_guard_count: 7
- broker_divergence_guard_count: 6
- daily_loss_guard_count: 7

## State Residency Days

- NORMAL: 128
- WARNING: 8
- BUY_STOP: 8
- EMERGENCY_STOP: 110
- RECOVERY_CANDIDATE: 1
- MANUAL_APPROVED: 5

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

## Data Use

Phase11-Z audit result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_FIX_B_1Y_SMOKE_PASS
PHASE11Z_FIX_C_FULL_5Y_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
