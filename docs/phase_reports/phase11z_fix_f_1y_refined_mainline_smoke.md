# Phase11-Z-Fix-F 1-Year Refined Mainline Smoke

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

- business_days: 260
- trade_count: 265
- orders_generated: 587
- orders_allowed_by_safety: 280
- orders_blocked_by_safety: 307
- orders_review_required: 0
- orders_emergency_stopped: 0
- non_blocking_review_order_count: 202
- blocking_review_order_count: 307
- buy_fill_count: 135
- sell_fill_count: 130
- round_trip_count: 130
- position_open_count: 135
- position_close_count: 130
- final_position_count: 5

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

## Review / Block

- raw_review_occurrence_count: 719
- aggregated_review_item_count: 719
- review_compression_ratio: 1.0
- blocking_review_count: 307
- non_blocking_review_count: 202
- info_only_count: 78
- review_per_business_day: 2.765385
- line_immediate_candidate_count: 517
- line_daily_summary_candidate_count: 202
- block_count_by_reason: {'CASH_BUFFER_VIOLATION': 3, 'MAX_EXPOSURE_EXCEEDED': 307}
- review_count_by_reason: {'HIGH_RISK_REVIEW': 68, 'INDIVIDUAL_DRAWDOWN_WARNING': 177, 'SELL_REVIEW_REQUIRED': 164}

## Safety Classification

- SYSTEM_EMERGENCY_STOP_count: 0
- EMERGENCY_STOP_count: 0
- BUY_STOP_days: 0
- MARKET_STRESS_count: 0
- BUY_REVIEW_REQUIRED_count: 326
- BUY_OPPORTUNITY_REVIEW_count: 0
- SELL_REVIEW_REQUIRED_count: 225
- HIGH_RISK_REVIEW_count: 86
- WARNING_count: 264
- BLOCK_count: 307
- REVIEW_REQUIRED_count: 386

## Performance

### Safety ON

- initial_cash: 1000000.0
- final_equity: 1462120.0
- total_return: 0.46212
- annualized_return: 0.430424
- max_drawdown: -0.200055
- win_rate: 0.530769
- profit_factor: 1.455886
- realized_profit: 1605930.0
- realized_loss: -1103060.0
- average_holding_days: 17.4
- exposure_ratio: 0.690424
- capital_utilization: 0.690424
- replacement_rate: 0.958042

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

- safety_on: {'orders_generated': 587, 'orders_allowed_by_safety': 280, 'orders_blocked_by_safety': 307, 'non_blocking_review_order_count': 202, 'blocking_review_order_count': 307, 'buy_fill_count': 135, 'sell_fill_count': 130, 'trade_count': 265, 'final_equity': 1462120.0, 'total_return': 0.46212, 'max_drawdown': -0.200055, 'win_rate': 0.530769, 'profit_factor': 1.455886}
- safety_off: {'orders_generated': 397, 'orders_allowed_by_safety': 397, 'orders_blocked_by_safety': 0, 'non_blocking_review_order_count': 0, 'blocking_review_order_count': 0, 'buy_fill_count': 193, 'sell_fill_count': 185, 'trade_count': 378, 'final_equity': 1426090.0, 'total_return': 0.42609, 'max_drawdown': -0.214177, 'win_rate': 0.540541, 'profit_factor': 1.262163}
- trade_count_gap: 113

## Non-Blocking Review

- BLOCKING_REVIEW: {'orders': 307, 'fill_allowed_count': 0, 'submitted_count': 0, 'fill_count': 0, 'fill_rate': 0.0}
- NON_BLOCKING_REVIEW: {'orders': 202, 'fill_allowed_count': 202, 'submitted_count': 202, 'fill_count': 187, 'fill_rate': 0.925743}
- INFO_ONLY: {'orders': 78, 'fill_allowed_count': 78, 'submitted_count': 78, 'fill_count': 78, 'fill_rate': 1.0}

## MAX Exposure

- max_exposure_blocked_buy_orders: 307
- max_exposure_blocked_sell_orders: 0
- max_exposure_allowed_sell_orders: 137
- max_exposure_allowed_exposure_reducing_orders: 137

## Notification / Blog

- public_report_path: reports/safety/phase11/integrated_backtest/fix_f_1y_refined_mainline_smoke/report_surfaces/2026-05-31_public_daily_report.md
- blog_report_path: reports/safety/phase11/integrated_backtest/fix_f_1y_refined_mainline_smoke/report_surfaces/2026-05-31_blog_draft.md
- blog_safety_market_review_section_present: true
- public_report_safety_market_review_section_present: true
- market_downturn_not_labeled_emergency: true
- system_emergency_only_stop_label: true
- line_notification_payload_generated: true
- line_notification_payload_path: reports/safety/phase11/notifications/2026-05-31_line_notification_payload.json
- line_send_executed: false
- notification_level: POSITION_REVIEW
- line_sections_count: 3

## 5Y Readiness

- ready_for_5y_full: true
- revenue_evaluation_eligible: true
- exit_source: fallback
- exit_source_fallback_impact: Exit source is still fallback, so 5y full is useful as Safety/runtime audit but not final revenue-quality evaluation.
- review_load_operable: true
- review_per_business_day: 2.765385
- block_ratio: 0.522998
- safety_on_off_explainable: true

## Checks

- one_year_completed: true
- market_price_review_not_fill_stopping: true
- non_blocking_review_order_count_gt_0: true
- non_blocking_review_fill_rate_gt_0: true
- system_hard_gate_blocks: true
- max_exposure_buy_only: true
- sell_exposure_reducing_passes: true
- review_aggregation_present: true
- line_payload_daily_summary: true
- blog_public_safety_section_present: true
- emergency_stop_system_only_or_zero: true
- auto_sell_executed_false: true
- auto_recovery_executed_false: true
- live_order_executed_false: true
- secret_raw_response_absent: true
- broker_api_connected_false: true
- ai_training_data_mutated_false: true
- five_year_full_not_run: true

## Data Use

Safety result and audit result are not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_FIX_F_1Y_REFINED_MAINLINE_SMOKE_PASS
PHASE11Z_FIX_G_5Y_REFINED_MAINLINE_FULL_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
