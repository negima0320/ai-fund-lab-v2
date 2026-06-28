# Phase11-Z-Fix-D Mainline Paper Trading / CAP5 Order Flow Adapter

- status: PASS
- period: 2025-06-01 to 2025-08-31
- business_day_count: 60
- revenue_evaluation_eligible: true
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- ai_retraining_executed: false
- full_5y_executed: false

## Reuse Map

- allocation_source: CAP5:phase9_daily_inference_allocation_builder
- candidate_source: mainline_artifact:phase7_opportunity_ranked_daily
- exit_source: fallback
- fill_source: mainline_virtual_fill
- ledger_source: PaperTradingLedger
- metrics_source: mainline_ledger_plus_realized_trade_metrics
- opportunity_source: mainline_artifact:phase7_opportunity_ranked_daily
- order_plan_source: phase9_daily_inference_order_plan_builder
- price_source: mainline_artifact:phase9_canonical_normalized_daily_quotes

## Short Smoke Result

- status: PASS
- audit_profile: mainline_paper_adapter
- candidate_source: mainline_artifact:phase7_opportunity_ranked_daily
- allocation_source: CAP5:phase9_daily_inference_allocation_builder
- order_plan_source: phase9_daily_inference_order_plan_builder
- fill_source: mainline_virtual_fill
- ledger_source: PaperTradingLedger
- orders_generated: 190
- orders_allowed_by_safety: 138
- orders_blocked_by_safety: 7
- orders_emergency_stopped: 4
- buy_fill_count: 3
- sell_fill_count: 1
- trade_count: 4
- final_equity: 1170600.0
- total_return: 0.1706
- win_rate: 1.0
- profit_factor: Infinity
- revenue_evaluation_eligible: True

## Normal Stub Comparison

### normal_market_stub
- status: PASS
- audit_profile: normal_market
- candidate_source: deterministic_audit_stub
- allocation_source: deterministic_audit_stub
- order_plan_source: audit_stub_planned_orders
- fill_source: audit_stub_same_day_synthetic_fill
- ledger_source: audit_local_cash_positions
- orders_generated: 130
- orders_allowed_by_safety: 130
- orders_blocked_by_safety: 0
- orders_emergency_stopped: 0
- buy_fill_count: 15
- sell_fill_count: 10
- trade_count: 25
- final_equity: 999000.0
- total_return: -0.001
- win_rate: 0.5
- profit_factor: 2.222222
- revenue_evaluation_eligible: False

### mainline_paper_adapter_safety_on
- status: PASS
- audit_profile: mainline_paper_adapter
- candidate_source: mainline_artifact:phase7_opportunity_ranked_daily
- allocation_source: CAP5:phase9_daily_inference_allocation_builder
- order_plan_source: phase9_daily_inference_order_plan_builder
- fill_source: mainline_virtual_fill
- ledger_source: PaperTradingLedger
- orders_generated: 190
- orders_allowed_by_safety: 138
- orders_blocked_by_safety: 7
- orders_emergency_stopped: 4
- buy_fill_count: 3
- sell_fill_count: 1
- trade_count: 4
- final_equity: 1170600.0
- total_return: 0.1706
- win_rate: 1.0
- profit_factor: Infinity
- revenue_evaluation_eligible: True

### mainline_paper_adapter_safety_off
- status: PASS
- audit_profile: mainline_paper_adapter
- candidate_source: mainline_artifact:phase7_opportunity_ranked_daily
- allocation_source: CAP5:phase9_daily_inference_allocation_builder
- order_plan_source: phase9_daily_inference_order_plan_builder
- fill_source: mainline_virtual_fill
- ledger_source: PaperTradingLedger
- orders_generated: 152
- orders_allowed_by_safety: 152
- orders_blocked_by_safety: 4
- orders_emergency_stopped: 0
- buy_fill_count: 8
- sell_fill_count: 6
- trade_count: 14
- final_equity: 1038700.0
- total_return: 0.0387
- win_rate: 0.5
- profit_factor: 0.469085
- revenue_evaluation_eligible: True

## Safety ON/OFF Interpretation

Safety ON reduced fills and introduced emergency stops; Safety OFF confirms adapter order/fill/ledger path can recycle cash and close positions.

## Data Use

Safety and audit outputs remain prohibited for AI learning. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation are not AI training inputs.

## Judgement

```text
PHASE11Z_FIX_D_MAINLINE_PAPER_ADAPTER_SMOKE_PASS
PHASE11Z_FIX_E_1Y_MAINLINE_SMOKE_READY_FOR_REVIEW
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
