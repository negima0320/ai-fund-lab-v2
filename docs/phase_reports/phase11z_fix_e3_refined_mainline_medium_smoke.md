# Phase11-Z-Fix-E3 Refined Safety Mainline Medium Smoke

- status: PASS
- period: 2025-06-01 to 2025-11-30
- max_days: 120
- profile: mainline_paper_adapter
- broker_api_connected: false
- websocket_connected: false
- line_send_executed: false
- live_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_training_data_mutated: false
- one_year_full_backtest_executed: false
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

- business_days: 120
- orders_generated: 922
- orders_allowed_by_safety: 14
- orders_blocked_by_safety: 330
- orders_review_required: 578
- orders_emergency_stopped: 0
- buy_fill_count: 10
- sell_fill_count: 4
- round_trip_count: 4
- position_open_count: 10
- position_close_count: 4
- final_position_count: 6
- trade_count: 14

### Safety OFF

- business_days: 120
- orders_generated: 196
- orders_allowed_by_safety: 196
- orders_blocked_by_safety: 0
- orders_review_required: 0
- orders_emergency_stopped: 0
- buy_fill_count: 99
- sell_fill_count: 91
- round_trip_count: 91
- position_open_count: 99
- position_close_count: 91
- final_position_count: 8
- trade_count: 190

## Review / Block Breakdown

- review_required_count_by_reason: {'HIGH_RISK_REVIEW': 943, 'INDIVIDUAL_DRAWDOWN_WARNING': 20, 'QUOTE_MISSING_FOR_MONITOR': 6, 'SELL_REVIEW_REQUIRED': 54}
- block_count_by_reason: {'MAX_EXPOSURE_EXCEEDED': 330}
- review_required_count_by_guard: {'INDIVIDUAL_CRASH': 1017, 'QUOTE_STALE': 6}
- block_count_by_guard: {'MAX_EXPOSURE': 330}
- top_10_review_reasons: [('HIGH_RISK_REVIEW', 943), ('SELL_REVIEW_REQUIRED', 54), ('INDIVIDUAL_DRAWDOWN_WARNING', 20), ('QUOTE_MISSING_FOR_MONITOR', 6)]
- top_10_block_reasons: [('MAX_EXPOSURE_EXCEEDED', 330)]
- review_per_business_day: 8.525
- block_per_business_day: 2.75
- unique_review_days: 116
- unique_block_days: 84
- max_reviews_per_day: 11
- max_blocks_per_day: 5
- median_reviews_per_day: 11.0
- median_blocks_per_day: 4.0
- orders_review_required: 578
- review_event_count: 1023
- review_event_to_order_review_ratio: 1.769896
- likely_duplicate_review_counting: false
- review_load_assessment: {'review_volume': 'HIGH', 'high_risk_review_count': 943, 'high_risk_review_too_many': True, 'sell_review_required_count': 54, 'sell_review_required_too_many': False, 'buy_review_required_proxy_count': 330, 'buy_review_required_too_many': True, 'quote_freshness_over_review': False, 'max_exposure_over_block': True, 'review_should_block_fill': False, 'market_price_review_should_be_notification_only': True, 'recommendations': ['同一銘柄/同一理由を日次集約してHuman Review件数を圧縮する。', 'HIGH_RISK_REVIEWは通知、INDIVIDUAL_DRAWDOWN_WARNINGはレポートのみへ分離する。', 'BUY_REVIEW_REQUIREDとBLOCKを分離し、market/price reviewだけではfillを止めない設計を検討する。', 'MAX_EXPOSURE_EXCEEDEDは新規BUYの上限制御として残しつつ、日次1件へ集約する。']}

## Safety Classification

- SYSTEM_EMERGENCY_STOP_count: 0
- EMERGENCY_STOP_count: 0
- BUY_STOP_days: 0
- MARKET_STRESS_count: 0
- BUY_REVIEW_REQUIRED_count: 336
- BUY_OPPORTUNITY_REVIEW_count: 0
- SELL_REVIEW_REQUIRED_count: 54
- HIGH_RISK_REVIEW_count: 943
- WARNING_count: 20
- BLOCK_count: 330
- REVIEW_REQUIRED_count: 694

## Performance

### Safety ON

- initial_cash: 1000000.0
- final_equity: 1539380.0
- total_return: 0.53938
- annualized_return: 1.412669
- max_drawdown: -0.094707
- win_rate: 1.0
- profit_factor: Infinity
- average_holding_days: 19.75
- exposure_ratio: 0.559037

### Safety OFF

- initial_cash: 1000000.0
- final_equity: 1177300.0
- total_return: 0.1773
- annualized_return: 0.395494
- max_drawdown: -0.137515
- win_rate: 0.56044
- profit_factor: 1.370804
- average_holding_days: 13.274725
- exposure_ratio: 0.76497

## Safety ON/OFF Diff

- orders_generated_diff: 726
- buy_fill_count_diff: -89
- sell_fill_count_diff: -87
- final_equity_diff: 362080.0
- explanation: Safety ON primarily blocked BUY orders that breached max exposure and routed market/price drawdown to Human Review. Review-classified market/price issues did not become Emergency Stop. The large ON/OFF fill gap indicates Review handling is currently too close to fill blocking and should be separated for market/price review before longer smoke.

## Review Fill Policy

- review_handling_blocks_fill_today: true
- review_orders_not_submitted: 578
- fill_gap_vs_safety_off: 176
- assessment: Review is currently stopping too much fill flow for a refined Safety role.
- recommendation: Separate system BLOCK from market/price REVIEW: market/price review should notify and aggregate, while only system faults and hard risk limits block order submission.
- one_year_ready: false

## Notification / Blog

- public_report_path: reports/safety/phase11/integrated_backtest/fix_e3_refined_mainline_medium_smoke/report_surfaces/2025-11-30_public_daily_report.md
- blog_report_path: reports/safety/phase11/integrated_backtest/fix_e3_refined_mainline_medium_smoke/report_surfaces/2025-11-30_blog_draft.md
- blog_safety_market_review_section_present: true
- public_report_safety_market_review_section_present: true
- market_downturn_not_labeled_emergency: true
- system_emergency_only_stop_label: true
- line_notification_payload_generated: true
- line_notification_payload_path: reports/safety/phase11/notifications/2025-11-30_line_notification_payload.json
- line_send_executed: false
- notification_level: POSITION_REVIEW

## Checks

- medium_smoke_completed: true
- safety_on_status_pass: true
- safety_off_status_pass: true
- emergency_stop_system_only_or_zero: true
- market_price_not_emergency_stop: true
- review_block_breakdown_present: true
- review_volume_evaluated: true
- safety_on_off_diff_explained: true
- line_notification_payload_generated: true
- line_send_executed_false: true
- blog_safety_market_review_section_present: true
- public_report_safety_market_review_section_present: true
- market_downturn_not_labeled_emergency: true
- system_emergency_only_stop_label: true
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
PHASE11Z_FIX_E3_REFINED_MAINLINE_MEDIUM_SMOKE_PASS
REVIEW_LOAD_REQUIRES_REFINEMENT_BEFORE_1Y
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
