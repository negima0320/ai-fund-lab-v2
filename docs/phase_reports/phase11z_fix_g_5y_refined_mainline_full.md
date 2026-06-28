# Phase11-Z-Fix-G 5-Year Refined Mainline Full Audit

- status: PASS
- period: 2021-06-01 to 2026-05-31
- profile: mainline_paper_adapter
- broker_api_connected: false
- websocket_connected: false
- line_send_executed: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_training_data_mutated: false

## Reuse Map

- candidate_source: mainline_artifact:phase7_opportunity_ranked_daily
- opportunity_source: mainline_artifact:phase7_opportunity_ranked_daily
- allocation_source: CAP5:phase9_daily_inference_allocation_builder
- order_plan_source: phase9_daily_inference_order_plan_builder
- fill_source: mainline_virtual_fill
- ledger_source: PaperTradingLedger
- exit_source: fallback
- metrics_source: mainline_ledger_plus_realized_trade_metrics
- price_source: mainline_artifact:phase9_canonical_normalized_daily_quotes
- revenue_evaluation_eligible: true

## Daily Flow

### Safety ON

- business_days: 1304
- trade_count: 598
- orders_generated: 4795
- orders_allowed_by_safety: 639
- orders_blocked_by_safety: 4156
- orders_review_required: 0
- orders_emergency_stopped: 0
- non_blocking_review_order_count: 306
- blocking_review_order_count: 4156
- buy_fill_count: 300
- sell_fill_count: 298
- round_trip_count: 298
- position_open_count: 300
- position_close_count: 298
- final_position_count: 2

### Safety OFF

- business_days: 1304
- trade_count: 1502
- orders_generated: 1587
- orders_allowed_by_safety: 1587
- orders_blocked_by_safety: 0
- orders_review_required: 0
- orders_emergency_stopped: 0
- non_blocking_review_order_count: 0
- blocking_review_order_count: 0
- buy_fill_count: 755
- sell_fill_count: 747
- round_trip_count: 747
- position_open_count: 755
- position_close_count: 747
- final_position_count: 8

## Performance

### Safety ON

- initial_cash: 1000000.0
- final_equity: 4246630.0
- total_return: 3.24663
- annualized_return: 0.312197
- max_drawdown: -0.251216
- win_rate: 0.607383
- profit_factor: 1.680506
- realized_profit: 8102240.0
- realized_loss: -4821310.0
- average_holding_days: 20.61745
- exposure_ratio: 0.391006
- capital_utilization: 0.391006
- replacement_rate: 0.996875

### Safety OFF

- initial_cash: 1000000.0
- final_equity: 19921280.0
- total_return: 18.92128
- annualized_return: 0.754366
- max_drawdown: -0.268152
- win_rate: 0.64257
- profit_factor: 1.582853
- realized_profit: 53374540.0
- realized_loss: -33720460.0
- average_holding_days: 18.236948
- exposure_ratio: 0.778408
- capital_utilization: 0.778408
- replacement_rate: 0.986233

## Safety

- SYSTEM_EMERGENCY_STOP_count: 0
- EMERGENCY_STOP_count: 0
- BUY_STOP_days: 0
- MARKET_STRESS_count: 0
- BUY_REVIEW_REQUIRED_count: 4252
- BUY_OPPORTUNITY_REVIEW_count: 0
- SELL_REVIEW_REQUIRED_count: 725
- HIGH_RISK_REVIEW_count: 180
- WARNING_count: 1129
- BLOCK_count: 4156
- REVIEW_REQUIRED_count: 828

## Review / Block

- raw_review_occurrence_count: 5756
- aggregated_review_item_count: 5756
- review_compression_ratio: 1.0
- blocking_review_count: 4156
- non_blocking_review_count: 306
- info_only_count: 333
- review_per_business_day: 4.41411
- line_immediate_candidate_count: 5450
- line_daily_summary_candidate_count: 306
- block_count_by_reason: {'CASH_BUFFER_VIOLATION': 5, 'MAX_EXPOSURE_EXCEEDED': 4154}
- review_count_by_reason: {'HIGH_RISK_REVIEW': 147, 'INDIVIDUAL_DRAWDOWN_WARNING': 877, 'SELL_REVIEW_REQUIRED': 573}

## Safety ON/OFF Comparison

- safety_on: {'orders_generated': 4795, 'orders_allowed_by_safety': 639, 'orders_blocked_by_safety': 4156, 'non_blocking_review_order_count': 306, 'blocking_review_order_count': 4156, 'buy_fill_count': 300, 'sell_fill_count': 298, 'trade_count': 598, 'final_equity': 4246630.0, 'total_return': 3.24663, 'max_drawdown': -0.251216, 'win_rate': 0.607383, 'profit_factor': 1.680506}
- safety_off: {'orders_generated': 1587, 'orders_allowed_by_safety': 1587, 'orders_blocked_by_safety': 0, 'non_blocking_review_order_count': 0, 'blocking_review_order_count': 0, 'buy_fill_count': 755, 'sell_fill_count': 747, 'trade_count': 1502, 'final_equity': 19921280.0, 'total_return': 18.92128, 'max_drawdown': -0.268152, 'win_rate': 0.64257, 'profit_factor': 1.582853}
- trade_count_gap: 904

## Exit Source Evaluation

- exit_source: fallback
- revenue_evaluation_eligible: true
- revenue_evaluation_usage: Safety/runtime audit and approximate revenue smoke only; not final Production-equivalent revenue proof.
- fallback_impact: Exit fallback can materially change sell timing, turnover, drawdown, and realized PnL. Phase12 can proceed for demo operation readiness, but exit integration should be closed before final production revenue claims.
- exit_integration_required_before_phase12: false
- exit_integration_required_before_production_revenue_claim: true

## Phase11 / Phase12 Readiness

- phase11_complete_candidate: true
- phase12_ready_for_review: true
- revenue_evaluation_eligible: true
- review_per_business_day: 4.41411
- block_ratio: 0.866736
- safety_on_off_explainable: true
- exit_fallback_caveat: exit_source=fallback; close before production revenue-quality evaluation.

## Notification / Blog

- public_report_path: reports/safety/phase11/integrated_backtest/fix_g_5y_refined_mainline_full/report_surfaces/2026-05-31_public_daily_report.md
- blog_report_path: reports/safety/phase11/integrated_backtest/fix_g_5y_refined_mainline_full/report_surfaces/2026-05-31_blog_draft.md
- blog_safety_market_review_section_present: true
- public_report_safety_market_review_section_present: true
- market_downturn_not_labeled_emergency: true
- system_emergency_only_stop_label: true
- line_notification_payload_generated: true
- line_notification_payload_path: reports/safety/phase11/notifications/2026-05-31_line_notification_payload.json
- line_send_executed: false
- notification_level: POSITION_REVIEW
- line_sections_count: 3

## Checks

- five_year_completed: true
- market_price_review_not_fill_stopping: true
- non_blocking_review_order_count_gt_0: true
- non_blocking_review_fill_rate_gt_0: true
- system_hard_gate_blocks: true
- max_exposure_buy_only: true
- sell_exposure_reducing_passes: true
- safety_on_off_explainable: true
- blog_public_safety_section_present: true
- line_payload_daily_summary: true
- emergency_stop_system_only_or_zero: true
- auto_sell_executed_false: true
- auto_recovery_executed_false: true
- live_order_executed_false: true
- secret_raw_response_absent: true
- broker_api_connected_false: true
- ai_training_data_mutated_false: true

## Data Use

Safety result and audit result are not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_FIX_G_5Y_REFINED_MAINLINE_FULL_PASS
PHASE11_COMPLETE_CANDIDATE
PHASE12_DEMO_FULL_OPERATION_READY_FOR_REVIEW
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
