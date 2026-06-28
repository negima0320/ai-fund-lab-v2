# Phase11-Z-Fix-E2 Refined Safety Mainline Adapter Short Smoke

- status: PASS
- period: 2025-06-01 to 2025-08-31
- max_days: 60
- profile: mainline_paper_adapter
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- line_send_executed: false
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

- business_days: 60
- orders_generated: 362
- orders_allowed_by_safety: 14
- orders_blocked_by_safety: 72
- orders_review_required: 276
- orders_emergency_stopped: 0
- buy_fill_count: 10
- sell_fill_count: 4
- round_trip_count: 4
- position_open_count: 10
- position_close_count: 4
- final_position_count: 6
- trade_count: 14

### Safety OFF

- business_days: 60
- orders_generated: 102
- orders_allowed_by_safety: 102
- orders_blocked_by_safety: 0
- orders_review_required: 0
- orders_emergency_stopped: 0
- buy_fill_count: 52
- sell_fill_count: 44
- round_trip_count: 44
- position_open_count: 52
- position_close_count: 44
- final_position_count: 8
- trade_count: 96

## Safety Classification

- SYSTEM_EMERGENCY_STOP_count: 0
- MARKET_STRESS_count: 0
- BUY_REVIEW_REQUIRED_count: 74
- BUY_OPPORTUNITY_REVIEW_count: 0
- SELL_REVIEW_REQUIRED_count: 54
- HIGH_RISK_REVIEW_count: 327
- WARNING_count: 20
- BLOCK_count: 72
- REVIEW_REQUIRED_count: 332
- EMERGENCY_STOP_count: 0
- BUY_STOP_days: 0
- SYSTEM_EMERGENCY_STOP_days: 0

## Performance

### Safety ON

- initial_cash: 1000000.0
- final_equity: 1436040.0
- total_return: 0.43604
- annualized_return: 3.382918
- max_drawdown: -0.062316
- win_rate: 1.0
- profit_factor: Infinity
- average_holding_days: 19.75
- exposure_ratio: 0.588378

### Safety OFF

- initial_cash: 1000000.0
- final_equity: 1343190.0
- total_return: 0.34319
- annualized_return: 2.336014
- max_drawdown: -0.050099
- win_rate: 0.681818
- profit_factor: 2.434739
- average_holding_days: 12.181818
- exposure_ratio: 0.741367

## Notification / Blog

- public_report_path: reports/safety/phase11/integrated_backtest/fix_e2_refined_mainline_smoke/report_surfaces/2025-08-31_public_daily_report.md
- blog_report_path: reports/safety/phase11/integrated_backtest/fix_e2_refined_mainline_smoke/report_surfaces/2025-08-31_blog_draft.md
- blog_safety_market_review_section_present: true
- public_report_safety_market_review_section_present: true
- market_downturn_not_labeled_emergency: true
- system_emergency_only_stop_label: true
- line_notification_payload_generated: true
- line_notification_payload_path: reports/safety/phase11/notifications/2025-08-31_line_notification_payload.json
- line_send_executed: false
- notification_level: POSITION_REVIEW

## Safety ON/OFF Diff

- orders_generated_diff: 260
- buy_fill_count_diff: -42
- sell_fill_count_diff: -40
- final_equity_diff: 92850.0
- explanation: Safety ON reduced new buy flow through BUY_REVIEW_REQUIRED checks such as max exposure and quote freshness. Market/price drawdown produced review classifications only and did not become Emergency Stop. Safety OFF bypassed pre-order guard blocking for comparison, so fills and round trips increased.

## Checks

- short_smoke_completed: true
- safety_on_status_pass: true
- safety_off_status_pass: true
- market_price_not_emergency_stop: true
- system_emergency_only_stop_label: true
- line_notification_payload_generated: true
- line_send_executed_false: true
- blog_safety_market_review_section_present: true
- public_report_safety_market_review_section_present: true
- market_downturn_not_labeled_emergency: true
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
PHASE11Z_FIX_E2_REFINED_MAINLINE_SMOKE_PASS
REFINED_SAFETY_SHORT_MAINLINE_SMOKE_COMPLETE
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
