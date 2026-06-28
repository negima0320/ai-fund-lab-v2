# Phase11-Z Integrated Safety Backtest Audit Full 5Y

- status: PASS
- audit_profile: mainline_paper_adapter
- period: 2025-06-01 to 2025-11-30
- business_day_count: 120
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false

## Performance

- initial_cash: 1000000.0
- final_equity: 1177300.0
- total_return: 0.1773
- annualized_return: 0.395494
- max_drawdown: -0.137515
- trade_count: 190
- trade_count_definition: buy_fill_count + sell_fill_count
- buy_fill_count: 99
- sell_fill_count: 91
- round_trip_count: 91
- closed_trades_count: 91
- winning_closed_trades: 51
- losing_closed_trades: 39
- breakeven_closed_trades: 1
- realized_profit: 889090.0
- realized_loss: -648590.0
- win_rate: 0.56044
- profit_factor: 1.370804
- average_realized_pnl: 2642.857143
- average_holding_days: 13.274725
- performance_metrics_placeholder: false
- exposure_ratio: 0.76497
- capital_utilization: 0.76497
- replacement_rate: 0.921569
- revenue_evaluation_eligible: true

## Flow Counts

- ai_signal_days: 120
- candidate_generated_days: 120
- candidate_count_total: 2400
- order_plan_generated_days: 120
- orders_generated: 196
- orders_before_safety: 196
- orders_allowed_by_safety: 196
- orders_blocked_by_safety: 0
- orders_review_required: 0
- orders_emergency_stopped: 0
- buy_orders_submitted: 102
- sell_orders_submitted: 94
- buy_fill_count: 99
- sell_fill_count: 91
- round_trip_count: 91
- position_open_count: 99
- position_close_count: 91
- final_position_count: 8
- virtual_orders_submitted: 196
- virtual_fills: 190
- ledger_entry_count: 190
- non_blocking_review_order_count: 0
- blocking_review_order_count: 0
- human_review_required_order_count: 0
- order_decision_count: 196
- raw_review_occurrence_count: 0
- aggregated_review_item_count: 0
- review_compression_ratio: 0
- blocking_review_count: 0
- non_blocking_review_count: 0
- info_only_count: 196
- order_decisions_path: reports/safety/phase11/integrated_backtest/refine_d1_non_blocking_review_medium_safety_off_smoke/order_decisions.json
- aggregated_review_queue_path: reports/safety/phase11/integrated_backtest/refine_d1_non_blocking_review_medium_safety_off_smoke/aggregated_review_queue.json
- candidate_universe_size: 2323
- fixed_4_code_stub_used: false
- periodic_mock_emergency_injection_enabled: false
- normal_market_profile: false
- stress_injection_profile: false
- trade_count_definition: trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count
- recovery_candidate_count_definition: event/check count, not unique days; see state_residency_days for day count
- mainline_paper_adapter_profile: true
- mainline_reuse_map: {'candidate_source': 'mainline_artifact:phase7_opportunity_ranked_daily', 'opportunity_source': 'mainline_artifact:phase7_opportunity_ranked_daily', 'allocation_source': 'CAP5:phase9_daily_inference_allocation_builder', 'order_plan_source': 'phase9_daily_inference_order_plan_builder', 'fill_source': 'mainline_virtual_fill', 'ledger_source': 'PaperTradingLedger', 'exit_source': 'fallback', 'metrics_source': 'mainline_ledger_plus_realized_trade_metrics', 'price_source': 'mainline_artifact:phase9_canonical_normalized_daily_quotes'}
- revenue_evaluation_eligible: true

## Safety

- safety_check_count: 120
- ALLOW_count: 229
- BLOCK_count: 0
- REVIEW_REQUIRED_count: 87
- EMERGENCY_STOP_count: 0
- BUY_STOP_days: 0
- RECOVERY_CANDIDATE_count: 0
- MANUAL_APPROVED_count: 0
- individual_warning_count: 26
- stop_loss_candidate_count: 42
- emergency_candidate_count: 13
- market_crash_guard_count: 0
- quote_stale_guard_count: 6
- duplicate_order_guard_count: 0
- cash_buffer_guard_count: 0
- max_exposure_guard_count: 0
- broker_divergence_guard_count: 0
- daily_loss_guard_count: 0

## State Residency Days

- NORMAL: 2
- WARNING: 34
- MARKET_STRESS: 0
- BUY_REVIEW_REQUIRED: 84
- BUY_OPPORTUNITY_REVIEW: 0
- BUY_STOP: 0
- SYSTEM_EMERGENCY_STOP: 0
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
- audit_profile: mainline_paper_adapter
- periodic_mock_emergency_injection_enabled: false
- normal_market_mock_boolean_crash_triggered: false
- recovery_candidate_to_normal_bypass: false
- performance_metrics_placeholder: false
- stress_results_separated_from_normal_performance: true
- mainline_reuse_map: {'candidate_source': 'mainline_artifact:phase7_opportunity_ranked_daily', 'opportunity_source': 'mainline_artifact:phase7_opportunity_ranked_daily', 'allocation_source': 'CAP5:phase9_daily_inference_allocation_builder', 'order_plan_source': 'phase9_daily_inference_order_plan_builder', 'fill_source': 'mainline_virtual_fill', 'ledger_source': 'PaperTradingLedger', 'exit_source': 'fallback', 'metrics_source': 'mainline_ledger_plus_realized_trade_metrics', 'price_source': 'mainline_artifact:phase9_canonical_normalized_daily_quotes'}
- revenue_evaluation_eligible: true
- safety_enabled: false

## Mainline Adapter Reuse Map

- candidate_source: mainline_artifact:phase7_opportunity_ranked_daily
- opportunity_source: mainline_artifact:phase7_opportunity_ranked_daily
- allocation_source: CAP5:phase9_daily_inference_allocation_builder
- order_plan_source: phase9_daily_inference_order_plan_builder
- fill_source: mainline_virtual_fill
- ledger_source: PaperTradingLedger
- exit_source: fallback
- metrics_source: mainline_ledger_plus_realized_trade_metrics
- price_source: mainline_artifact:phase9_canonical_normalized_daily_quotes

## Market Crash Input

- market_crash_source: canonical_quotes_phase7_ranked_daily
- index_return: 0.00
- candidate_universe_drawdown: 0.00
- extreme_down_ratio: 0.00
- stop_limit_candidate_ratio: 0.00
- is_synthetic: false
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
- mainline_reuse_map_present: true
- paper_ledger_used: true
- virtual_fill_processor_used: true

## Data Use

Phase11-Z audit result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_FIX_D_MAINLINE_PAPER_ADAPTER_SMOKE_PASS
PHASE11Z_FIX_E_1Y_MAINLINE_SMOKE_READY_FOR_REVIEW
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
