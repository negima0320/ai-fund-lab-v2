# Phase11-Z-Fix-H 1-Year Equity-Linked MAX_EXPOSURE Smoke

- status: PASS
- period: 2025-06-01 to 2026-05-31
- profile: mainline_paper_adapter
- broker_api_connected: false
- websocket_connected: false
- line_send_executed: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_training_data_mutated: false
- five_year_full_backtest_executed: false

## Daily Flow

### Safety ON

- business_days: 260
- trade_count: 310
- orders_generated: 436
- orders_allowed_by_safety: 316
- orders_blocked_by_safety: 120
- orders_review_required: 0
- orders_emergency_stopped: 0
- non_blocking_review_order_count: 223
- blocking_review_order_count: 120
- buy_fill_count: 159
- sell_fill_count: 151
- round_trip_count: 151
- position_open_count: 159
- position_close_count: 151
- final_position_count: 8

### Safety OFF

- business_days: 260
- trade_count: 378
- orders_generated: 397
- orders_allowed_by_safety: 397
- orders_blocked_by_safety: 0
- orders_review_required: 0
- orders_emergency_stopped: 0
- non_blocking_review_order_count: 0
- blocking_review_order_count: 0
- buy_fill_count: 193
- sell_fill_count: 185
- round_trip_count: 185
- position_open_count: 193
- position_close_count: 185
- final_position_count: 8

## MAX_EXPOSURE

- max_exposure_blocked_buy_orders: 120
- max_exposure_blocked_sell_orders: 0
- max_exposure_allowed_sell_orders: 156
- max_exposure_allowed_exposure_reducing_orders: 156
- average_base_equity: 1431061.333333
- average_max_allowed_exposure: 1216402.133333
- average_current_exposure: 1131826.583333
- average_projected_exposure_at_block: 1293551.0
- average_cash_ratio: 0.24326
- average_cash_remaining_at_block: 299234.75
- average_position_count_at_block: 7.508333
- position_count_lt_8_block_count: 55
- fixed_absolute_cap_used: false
- max_total_exposure_ratio: 0.85
- max_total_exposure_absolute_cap: None
- exposure_basis: equity
- sell_orders_with_max_exposure_block: 0
- equity_linked_samples: [{'base_equity': '1036500.0', 'max_total_exposure_ratio': '0.85', 'max_allowed_exposure': '881025.000', 'expected_max_allowed_exposure': '881025.000', 'formula_valid': True, 'current_exposure': '934700.0', 'projected_exposure': '943700.0', 'cash_available': '101800.0', 'position_count': 5, 'issue_code': '67400'}, {'base_equity': '1056100.0', 'max_total_exposure_ratio': '0.85', 'max_allowed_exposure': '897685.000', 'expected_max_allowed_exposure': '897685.000', 'formula_valid': True, 'current_exposure': '974900.0', 'projected_exposure': '997900.0', 'cash_available': '81200.0', 'position_count': 8, 'issue_code': '24590'}, {'base_equity': '1079830.0', 'max_total_exposure_ratio': '0.85', 'max_allowed_exposure': '917855.500', 'expected_max_allowed_exposure': '917855.500', 'formula_valid': True, 'current_exposure': '735630.0', 'projected_exposure': '921230.0', 'cash_available': '344200.0', 'position_count': 8, 'issue_code': '40750'}, {'base_equity': '1092000.0', 'max_total_exposure_ratio': '0.85', 'max_allowed_exposure': '928200.000', 'expected_max_allowed_exposure': '928200.000', 'formula_valid': True, 'current_exposure': '841100.0', 'projected_exposure': '1037100.0', 'cash_available': '250900.0', 'position_count': 8, 'issue_code': '89180'}, {'base_equity': '1105270.0', 'max_total_exposure_ratio': '0.85', 'max_allowed_exposure': '939479.500', 'expected_max_allowed_exposure': '939479.500', 'formula_valid': True, 'current_exposure': '913600.0', 'projected_exposure': '978800.0', 'cash_available': '191670.0', 'position_count': 8, 'issue_code': '57210'}]
- equity_linked_samples_valid: true

## Performance

### Safety ON

- initial_cash: 1000000.0
- final_equity: 1784520.0
- total_return: 0.78452
- annualized_return: 0.72588
- max_drawdown: -0.121077
- win_rate: 0.536424
- profit_factor: 1.574577
- realized_profit: 2188410.0
- realized_loss: -1389840.0
- average_holding_days: 16.993377
- exposure_ratio: 0.759138
- capital_utilization: 0.759138
- replacement_rate: 0.975

### Safety OFF

- initial_cash: 1000000.0
- final_equity: 1426090.0
- total_return: 0.42609
- annualized_return: 0.397185
- max_drawdown: -0.214177
- win_rate: 0.540541
- profit_factor: 1.262163
- realized_profit: 2170290.0
- realized_loss: -1719500.0
- average_holding_days: 14.794595
- exposure_ratio: 0.779228
- capital_utilization: 0.779228
- replacement_rate: 0.955665

## Safety ON/OFF Comparison

- safety_on: {'orders_generated': 436, 'orders_allowed_by_safety': 316, 'orders_blocked_by_safety': 120, 'non_blocking_review_order_count': 223, 'blocking_review_order_count': 120, 'buy_fill_count': 159, 'sell_fill_count': 151, 'trade_count': 310, 'final_equity': 1784520.0, 'total_return': 0.78452, 'max_drawdown': -0.121077, 'win_rate': 0.536424, 'profit_factor': 1.574577, 'max_exposure_block_count': 120}
- safety_off: {'orders_generated': 397, 'orders_allowed_by_safety': 397, 'orders_blocked_by_safety': 0, 'non_blocking_review_order_count': 0, 'blocking_review_order_count': 0, 'buy_fill_count': 193, 'sell_fill_count': 185, 'trade_count': 378, 'final_equity': 1426090.0, 'total_return': 0.42609, 'max_drawdown': -0.214177, 'win_rate': 0.540541, 'profit_factor': 1.262163, 'max_exposure_block_count': 0}
- trade_count_gap: 68

## Previous 1Y Safety ON Comparison

- previous: {'final_equity': 1462120.0, 'total_return': 0.46212, 'annualized_return': 0.430424, 'max_drawdown': -0.200055, 'buy_fill_count': 135, 'sell_fill_count': 130, 'trade_count': 265, 'orders_blocked_by_safety': 307, 'max_exposure_blocked_buy_orders': 307}
- current: {'final_equity': 1784520.0, 'total_return': 0.78452, 'annualized_return': 0.72588, 'max_drawdown': -0.121077, 'buy_fill_count': 159, 'sell_fill_count': 151, 'trade_count': 310, 'orders_blocked_by_safety': 120}
- delta: {'final_equity': 322400.0, 'total_return': 0.3224, 'max_drawdown': 0.078978, 'buy_fill_count': 24, 'sell_fill_count': 21, 'trade_count': 45, 'orders_blocked_by_safety': -187}

## Review / Block

- raw_review_occurrence_count: 437
- aggregated_review_item_count: 437
- review_compression_ratio: 1.0
- blocking_review_count: 120
- non_blocking_review_count: 223
- info_only_count: 93
- review_per_business_day: 1.680769
- line_immediate_candidate_count: 214
- line_daily_summary_candidate_count: 223
- block_count_by_reason: {'MAX_EXPOSURE_EXCEEDED': 120}
- review_count_by_reason: {'HIGH_RISK_REVIEW': 84, 'INDIVIDUAL_DRAWDOWN_WARNING': 70, 'SELL_REVIEW_REQUIRED': 163}

## Readiness

- ready_for_fix_i_5y_full: true
- block_ratio: 0.275229
- review_per_business_day: 1.680769
- safety_on_off_explainable: true
- five_year_full_not_executed_in_fix_h: true
- exit_source: fallback
- exit_source_caveat: exit_source=fallback remains a revenue-quality caveat; Fix-I is a Safety/runtime full audit, not final Production revenue proof.

## Checks

- one_year_completed: true
- fixed_absolute_cap_disabled: true
- equity_linked_ratio_cap_used: true
- max_allowed_exposure_scales_with_base_equity: true
- sell_not_blocked_by_max_exposure: true
- sell_exposure_reducing_passes: true
- max_exposure_blocks_rationalized_vs_previous: true
- market_price_review_not_fill_stopping: true
- system_hard_gate_blocks: true
- non_blocking_review_reaches_fill: true
- line_payload_not_sent: true
- blog_public_safety_section_present: true
- auto_sell_executed_false: true
- auto_recovery_executed_false: true
- live_order_executed_false: true
- secret_raw_response_absent: true
- broker_api_connected_false: true
- ai_training_data_mutated_false: true
- five_year_full_not_run: true

## Data Use

Safety result and audit result remain forbidden for AI training. Broker API, WebSocket, LINE send, Demo/Production orders, auto-sell, auto-recovery, AI retraining, and 5-year full were not executed in Fix-H.

## Result

```text
PHASE11Z_FIX_H_1Y_EQUITY_LINKED_EXPOSURE_PASS
PHASE11Z_FIX_I_5Y_REFINED_MAINLINE_FULL_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
