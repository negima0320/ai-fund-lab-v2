# Phase11-Z Integrated Safety Backtest Audit Full 5Y

- status: PASS
- period: 2025-06-01 to 2025-12-31
- business_day_count: 153
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false

## Performance

- initial_cash: 1000000.0
- final_equity: 1002900.0
- total_return: 0.0029
- annualized_return: 0.004648
- max_drawdown: -0.082879
- trade_count: 4
- win_rate: 0.0
- profit_factor: 0.0
- average_holding_days: 150.5
- exposure_ratio: 0.469241

## Safety

- safety_check_count: 153
- ALLOW_count: 269
- BLOCK_count: 13
- REVIEW_REQUIRED_count: 17
- EMERGENCY_STOP_count: 7
- BUY_STOP_days: 4
- RECOVERY_CANDIDATE_count: 173
- MANUAL_APPROVED_count: 0
- individual_warning_count: 4
- stop_loss_candidate_count: 4
- emergency_candidate_count: 2
- market_crash_guard_count: 6
- quote_stale_guard_count: 4
- duplicate_order_guard_count: 2
- cash_buffer_guard_count: 1
- max_exposure_guard_count: 2
- broker_divergence_guard_count: 2
- daily_loss_guard_count: 2

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
- emergency_blocked_order_flow: true
- quote_stale_blocked_inferred_trade: true
- broker_divergence_review_or_emergency: true

## Data Use

Phase11-Z audit result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_INTEGRATED_SAFETY_BACKTEST_FULL_5Y_PASS
PHASE11_COMPLETE_CANDIDATE
PHASE12_DEMO_FULL_OPERATION_READY_FOR_REVIEW
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
