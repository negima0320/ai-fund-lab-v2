# Phase11-Z-Fix-B2 Integrated Audit Runner Quality Fix

- status: PHASE11Z_FIX_B2_INTEGRATED_AUDIT_RUNNER_QUALITY_FIX_COMPLETE
- created_at: 2026-06-28
- implementation_changed: true
- full_5y_backtest_rerun: false
- broker_api_connected: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_retraining_executed: false

## Summary

Fix-B anomaly investigationで判明したnormal smokeとstress injectionの混線を分離した。`normal_market` profileでは周期的なEmergency注入を無効化し、Market Crash入力を `synthetic_none` として明示する。`stress_injection` profileではduplicate / stale / divergence / manual emergency / market stressを意図的に注入し、Safety停止を確認する。

## Updated Files

- src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py
- scripts/run_phase11z_integrated_safety_backtest_audit.py
- tests/safety_phase11/test_integrated_backtest_audit.py


## Audit Profiles

- normal_market: periodic duplicate/manual emergency/broker divergence/stale quote/severe market crash injection disabled. Normal performance is evaluated here.
- stress_injection: intentional anomaly injection enabled. Stress result is not mixed into normal performance.

## Market Crash Input

normal_market:

```json
{
  "market_crash_source": "synthetic_none",
  "index_return": "0.00",
  "candidate_universe_drawdown": "0.00",
  "extreme_down_ratio": "0.00",
  "stop_limit_candidate_ratio": "0.00",
  "is_synthetic": true,
  "market_crash": false,
  "severe_crash": false,
  "stress_results_mixed_into_normal_performance": false
}
```

stress_injection:

```json
{
  "market_crash_source": "synthetic_stress_injection",
  "index_return": "profile_generated",
  "candidate_universe_drawdown": "profile_generated",
  "extreme_down_ratio": "profile_generated",
  "stop_limit_candidate_ratio": "profile_generated",
  "is_synthetic": true,
  "stress_results_mixed_into_normal_performance": false
}
```

## Normal Market 1Y Result

```json
{
  "period": [
    "2025-06-01",
    "2026-05-31"
  ],
  "business_days": 260,
  "status": "PASS",
  "summary_path": "reports/safety/phase11/integrated_backtest/fix_b2_normal_market_1y/summary.json",
  "output_dir": "reports/safety/phase11/integrated_backtest/fix_b2_normal_market_1y",
  "performance": {
    "initial_cash": 1000000.0,
    "final_equity": 1014500.0,
    "total_return": 0.0145,
    "annualized_return": 0.013658,
    "max_drawdown": -0.017423,
    "trade_count": 59,
    "trade_count_definition": "buy_fill_count + sell_fill_count",
    "buy_fill_count": 32,
    "sell_fill_count": 27,
    "round_trip_count": 27,
    "closed_trades_count": 27,
    "winning_closed_trades": 16,
    "losing_closed_trades": 11,
    "breakeven_closed_trades": 0,
    "realized_profit": 25600.0,
    "realized_loss": -14300.0,
    "win_rate": 0.592593,
    "profit_factor": 1.79021,
    "average_realized_pnl": 418.518519,
    "average_holding_days": 63.0,
    "performance_metrics_placeholder": false,
    "exposure_ratio": 0.5132
  },
  "flow_counts": {
    "ai_signal_days": 260,
    "candidate_generated_days": 260,
    "candidate_count_total": 1560,
    "order_plan_generated_days": 260,
    "orders_generated": 538,
    "orders_before_safety": 538,
    "orders_allowed_by_safety": 538,
    "orders_blocked_by_safety": 0,
    "orders_review_required": 0,
    "orders_emergency_stopped": 0,
    "buy_orders_submitted": 32,
    "sell_orders_submitted": 27,
    "buy_fill_count": 32,
    "sell_fill_count": 27,
    "round_trip_count": 27,
    "position_open_count": 32,
    "position_close_count": 27,
    "final_position_count": 5,
    "virtual_orders_submitted": 59,
    "virtual_fills": 59,
    "ledger_entry_count": 59,
    "candidate_universe_size": 60,
    "fixed_4_code_stub_used": false,
    "periodic_mock_emergency_injection_enabled": false,
    "normal_market_profile": true,
    "stress_injection_profile": false,
    "trade_count_definition": "trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count",
    "recovery_candidate_count_definition": "event/check count, not unique days; see state_residency_days for day count"
  },
  "safety": {
    "safety_check_count": 260,
    "ALLOW_count": 798,
    "BLOCK_count": 0,
    "REVIEW_REQUIRED_count": 0,
    "EMERGENCY_STOP_count": 0,
    "BUY_STOP_days": 0,
    "RECOVERY_CANDIDATE_count": 0,
    "MANUAL_APPROVED_count": 0,
    "individual_warning_count": 0,
    "stop_loss_candidate_count": 0,
    "emergency_candidate_count": 0,
    "market_crash_guard_count": 0,
    "quote_stale_guard_count": 0,
    "duplicate_order_guard_count": 0,
    "cash_buffer_guard_count": 0,
    "max_exposure_guard_count": 0,
    "broker_divergence_guard_count": 0,
    "daily_loss_guard_count": 0
  },
  "state_residency_days": {
    "NORMAL": 260,
    "WARNING": 0,
    "BUY_STOP": 0,
    "EMERGENCY_STOP": 0,
    "RECOVERY_CANDIDATE": 0,
    "MANUAL_APPROVED": 0
  },
  "pass_conditions": {
    "orders_generated_gt_0": true,
    "orders_before_safety_gt_0": true,
    "buy_fill_count_gt_0": true,
    "sell_fill_count_gt_0": true,
    "position_open_count_gt_0": true,
    "position_close_count_gt_0": true,
    "trade_count_not_extremely_low": true,
    "fixed_4_code_stub_not_used": true,
    "candidate_universe_broad_enough": true,
    "manual_approval_simulation_available": true,
    "recovery_does_not_auto_normal": true,
    "docs_output_isolated_for_tests": true,
    "win_rate_profit_factor_not_placeholder": true,
    "recovery_candidate_to_normal_bypass_absent": true,
    "stress_results_separated_from_normal_performance": true,
    "normal_market_profile_enabled": true,
    "emergency_stop_days_ratio_within_threshold": true,
    "normal_market_mock_boolean_crash_absent": true,
    "periodic_mock_emergency_injection_disabled": true
  },
  "market_crash_input": {
    "market_crash_source": "synthetic_none",
    "index_return": "0.00",
    "candidate_universe_drawdown": "0.00",
    "extreme_down_ratio": "0.00",
    "stop_limit_candidate_ratio": "0.00",
    "is_synthetic": true,
    "market_crash": false,
    "severe_crash": false,
    "stress_results_mixed_into_normal_performance": false
  }
}
```

## Stress Injection Result

```json
{
  "period": [
    "2025-06-01",
    "2025-12-31"
  ],
  "business_days": 153,
  "status": "PASS",
  "summary_path": "reports/safety/phase11/integrated_backtest/fix_b2_stress_injection/summary.json",
  "output_dir": "reports/safety/phase11/integrated_backtest/fix_b2_stress_injection",
  "performance": {
    "initial_cash": 1000000.0,
    "final_equity": 1002100.0,
    "total_return": 0.0021,
    "annualized_return": 0.003365,
    "max_drawdown": -0.088358,
    "trade_count": 26,
    "trade_count_definition": "buy_fill_count + sell_fill_count",
    "buy_fill_count": 16,
    "sell_fill_count": 10,
    "round_trip_count": 10,
    "closed_trades_count": 10,
    "winning_closed_trades": 5,
    "losing_closed_trades": 5,
    "breakeven_closed_trades": 0,
    "realized_profit": 6000.0,
    "realized_loss": -6400.0,
    "win_rate": 0.5,
    "profit_factor": 0.9375,
    "average_realized_pnl": -40.0,
    "average_holding_days": 80.6,
    "performance_metrics_placeholder": false,
    "exposure_ratio": 0.508644
  },
  "flow_counts": {
    "ai_signal_days": 153,
    "candidate_generated_days": 153,
    "candidate_count_total": 918,
    "order_plan_generated_days": 153,
    "orders_generated": 299,
    "orders_before_safety": 299,
    "orders_allowed_by_safety": 260,
    "orders_blocked_by_safety": 28,
    "orders_review_required": 16,
    "orders_emergency_stopped": 80,
    "buy_orders_submitted": 16,
    "sell_orders_submitted": 10,
    "buy_fill_count": 16,
    "sell_fill_count": 10,
    "round_trip_count": 10,
    "position_open_count": 16,
    "position_close_count": 10,
    "final_position_count": 6,
    "virtual_orders_submitted": 26,
    "virtual_fills": 26,
    "ledger_entry_count": 26,
    "candidate_universe_size": 60,
    "fixed_4_code_stub_used": false,
    "periodic_mock_emergency_injection_enabled": true,
    "normal_market_profile": false,
    "stress_injection_profile": true,
    "trade_count_definition": "trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count",
    "recovery_candidate_count_definition": "event/check count, not unique days; see state_residency_days for day count"
  },
  "safety": {
    "safety_check_count": 153,
    "ALLOW_count": 395,
    "BLOCK_count": 19,
    "REVIEW_REQUIRED_count": 25,
    "EMERGENCY_STOP_count": 13,
    "BUY_STOP_days": 37,
    "RECOVERY_CANDIDATE_count": 11,
    "MANUAL_APPROVED_count": 28,
    "individual_warning_count": 7,
    "stop_loss_candidate_count": 6,
    "emergency_candidate_count": 5,
    "market_crash_guard_count": 9,
    "quote_stale_guard_count": 6,
    "duplicate_order_guard_count": 3,
    "cash_buffer_guard_count": 2,
    "max_exposure_guard_count": 3,
    "broker_divergence_guard_count": 3,
    "daily_loss_guard_count": 3
  },
  "state_residency_days": {
    "NORMAL": 84,
    "WARNING": 8,
    "BUY_STOP": 6,
    "EMERGENCY_STOP": 45,
    "RECOVERY_CANDIDATE": 1,
    "MANUAL_APPROVED": 9
  },
  "pass_conditions": {
    "orders_generated_gt_0": true,
    "orders_before_safety_gt_0": true,
    "buy_fill_count_gt_0": true,
    "sell_fill_count_gt_0": true,
    "position_open_count_gt_0": true,
    "position_close_count_gt_0": true,
    "trade_count_not_extremely_low": true,
    "fixed_4_code_stub_not_used": true,
    "candidate_universe_broad_enough": true,
    "manual_approval_simulation_available": true,
    "recovery_does_not_auto_normal": true,
    "docs_output_isolated_for_tests": true,
    "win_rate_profit_factor_not_placeholder": true,
    "recovery_candidate_to_normal_bypass_absent": true,
    "stress_results_separated_from_normal_performance": true,
    "stress_profile_enabled": true,
    "stress_injection_triggered_safety": true
  },
  "market_crash_input": {
    "market_crash_source": "synthetic_stress_injection",
    "index_return": "profile_generated",
    "candidate_universe_drawdown": "profile_generated",
    "extreme_down_ratio": "profile_generated",
    "stop_limit_candidate_ratio": "profile_generated",
    "is_synthetic": true,
    "stress_results_mixed_into_normal_performance": false
  }
}
```

## Data Use

Fix-B2 audit result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_FIX_B2_NORMAL_MARKET_SMOKE_PASS
PHASE11Z_FIX_B2_STRESS_INJECTION_PASS
PHASE11Z_FIX_C_FULL_5Y_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
