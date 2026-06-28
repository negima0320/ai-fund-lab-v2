# Phase11-Safety-Refine-D1 Non-Blocking Review Policy

- status: PASS
- period: 2025-06-01 to 2025-11-30
- max_days: 120
- broker_api_connected: false
- websocket_connected: false
- line_send_executed: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_training_data_mutated: false
- one_year_full_backtest_executed: false
- five_year_full_backtest_executed: false

## Review Class Spec

- BLOCKING_REVIEW: System fault or hard risk gate; fill_allowed=false.
- NON_BLOCKING_REVIEW: Market/price/position review; fill_allowed=true and human review/reporting remains.
- INFO_ONLY: No human review required; fill_allowed=true.

## Daily Flow

### Safety ON

- business_days: 120
- trade_count: 135
- orders_generated: 227
- orders_allowed_by_safety: 138
- orders_blocked_by_safety: 89
- orders_review_required: 0
- orders_emergency_stopped: 0
- non_blocking_review_order_count: 98
- blocking_review_order_count: 89
- human_review_required_order_count: 187
- buy_fill_count: 71
- sell_fill_count: 64
- virtual_orders_submitted: 138
- virtual_fills: 135
- final_position_count: 7

### Safety OFF

- business_days: 120
- trade_count: 190
- orders_generated: 196
- orders_allowed_by_safety: 196
- orders_blocked_by_safety: 0
- orders_review_required: 0
- orders_emergency_stopped: 0
- non_blocking_review_order_count: 0
- blocking_review_order_count: 0
- human_review_required_order_count: 0
- buy_fill_count: 99
- sell_fill_count: 91
- virtual_orders_submitted: 196
- virtual_fills: 190
- final_position_count: 8

## Fill Reachability

- BLOCKING_REVIEW: {'orders': 89, 'fill_allowed_count': 0, 'submitted_count': 0, 'fill_count': 0}
- NON_BLOCKING_REVIEW: {'orders': 98, 'fill_allowed_count': 98, 'submitted_count': 98, 'fill_count': 95}
- INFO_ONLY: {'orders': 40, 'fill_allowed_count': 40, 'submitted_count': 40, 'fill_count': 40}

## Market / Price Review

- market_price_review_order_count: 165
- market_price_review_fill_allowed_count: 98
- market_price_review_filled_count: 95
- market_price_review_blocked_count: 67
- standalone_market_price_review_order_count: 98
- standalone_market_price_review_blocked_count: 0
- market_price_with_hard_gate_block_count: 67

## MAX Exposure

- max_exposure_blocked_buy_orders: 89
- max_exposure_blocked_sell_orders: 0
- max_exposure_allowed_sell_orders: 66
- max_exposure_allowed_exposure_reducing_orders: 66

## Review Aggregation

- raw_review_occurrence_count: 257
- aggregated_review_item_count: 257
- review_compression_ratio: 1.0
- blocking_review_count: 89
- non_blocking_review_count: 98
- info_only_count: 40

## Notification / Blog

- public_report_path: reports/safety/phase11/integrated_backtest/refine_d1_non_blocking_review_medium_smoke/report_surfaces/2025-11-30_public_daily_report.md
- blog_report_path: reports/safety/phase11/integrated_backtest/refine_d1_non_blocking_review_medium_smoke/report_surfaces/2025-11-30_blog_draft.md
- blog_safety_market_review_section_present: true
- public_report_safety_market_review_section_present: true
- market_downturn_not_labeled_emergency: true
- system_emergency_only_stop_label: true
- line_notification_payload_generated: true
- line_notification_payload_path: reports/safety/phase11/notifications/2025-11-30_line_notification_payload.json
- line_send_executed: false
- notification_level: POSITION_REVIEW
- line_sections_count: 3

## Safety ON/OFF Diff

- trade_count_on: 135
- trade_count_off: 190
- trade_count_gap: 55
- final_equity_on: 975230.0
- final_equity_off: 1177300.0

## Checks

- medium_smoke_completed: true
- market_price_review_not_fill_stopping: true
- non_blocking_review_reaches_fill: true
- system_hard_gate_blocks: true
- max_exposure_buy_only: true
- sell_exposure_reducing_passes: true
- aggregated_review_queue_present: true
- review_compression_ratio_present: true
- line_payload_daily_summary: true
- blog_public_safety_section_present: true
- emergency_stop_system_only_or_zero: true
- auto_sell_executed_false: true
- auto_recovery_executed_false: true
- live_order_executed_false: true
- secret_raw_response_absent: true
- broker_api_connected_false: true
- ai_training_data_mutated_false: true
- one_year_full_not_run: true
- five_year_full_not_run: true

## Data Use

Safety result and audit result are not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11_SAFETY_REFINE_D1_NON_BLOCKING_REVIEW_POLICY_PASS
PHASE11_REFINED_1Y_MAINLINE_SMOKE_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
