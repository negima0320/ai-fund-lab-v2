# Phase11-Safety-Cap-Fix: Equity-Linked MAX_EXPOSURE

## Status

```text
PHASE11_SAFETY_CAP_FIX_EQUITY_LINKED_EXPOSURE_PASS
MAX_EXPOSURE_FIXED_CAP_REMOVED_FROM_DEFAULT_PATH
MEDIUM_SMOKE_PASS
ONE_YEAR_REFINED_MAINLINE_SMOKE_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```

## Read Materials

- `docs/phase_reports/phase11_max_exposure_investigation.md`
- `reports/phase_reports/phase11_max_exposure_investigation.json`
- `docs/phase_reports/phase11z_fix_g_5y_refined_mainline_full.md`
- `reports/phase_reports/phase11z_fix_g_5y_refined_mainline_full.json`
- `docs/phase_reports/phase11_safety_refine_d1_non_blocking_review_policy.md`
- `reports/phase_reports/phase11_safety_refine_d1_non_blocking_review_policy.json`
- `src/ai_fund_lab_v2/safety_phase11/guards.py`
- `src/ai_fund_lab_v2/safety_phase11/models.py`
- `src/ai_fund_lab_v2/safety_phase11/safety_manager.py`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py`
- `tests/safety_phase11/`

## Updated Files

- `src/ai_fund_lab_v2/safety_phase11/guards.py`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py`
- `tests/safety_phase11/test_guards_and_manager.py`
- `docs/phase_reports/phase11_safety_cap_fix_equity_linked_exposure.md`
- `reports/phase_reports/phase11_safety_cap_fix_equity_linked_exposure.json`

## Old Fixed Cap Problem

- old_config: max_total_exposure=850000 fixed absolute JPY
- impact: Fixed cap stayed at 850000 JPY after equity growth, blocking BUY while cash and position slots remained available.
- phase11_fix_g_max_exposure_blocked_buy_orders: 4154

## New Ratio Cap Spec

- max_total_exposure_ratio_default: 0.85
- max_total_exposure_absolute_cap: optional/null by default
- legacy_max_total_exposure: treated as explicit optional absolute cap when configured
- exposure_basis_default: equity
- exposure_basis_options: ['equity', 'buying_power', 'min_equity_buying_power']

## Base Equity / Exposure Basis

- paper_backtest: current_total_equity / base_equity from Paper ledger, falling back to cash + current position market value
- demo_production_design: broker actual equity / buying_power basis via broker_snapshot/config without connecting in this phase

## MAX_EXPOSURE Formula

- current_exposure: sum(position.market_value)
- projected_exposure: current_exposure + new BUY notional
- max_allowed_exposure: base_equity * max_total_exposure_ratio, optionally min with explicit absolute cap
- block_condition: side == BUY and projected_exposure > max_allowed_exposure
- sell_rule: SELL / exposure reducing order is ALLOW even when cap is exceeded

## Debug Fields

- current_exposure
- projected_exposure
- base_equity
- max_total_exposure_ratio
- max_allowed_exposure
- cash_available
- position_count
- side
- issue_code
- reason_code

## Medium Smoke

- period: 2025-06-01 to 2025-11-30
- max_days: 120
- profile: mainline_paper_adapter

### Safety ON

- orders_generated: 223
- orders_allowed_by_safety: 167
- orders_blocked_by_safety: 56
- non_blocking_review_order_count: 107
- blocking_review_order_count: 56
- buy_fill_count: 86
- sell_fill_count: 78
- trade_count: 164
- final_equity: 1275660.0
- total_return: 0.27566
- annualized_return: 0.6439
- max_drawdown: -0.121077
- exposure_ratio: 0.756622
- capital_utilization: 0.756622

### Safety OFF

- orders_generated: 196
- orders_allowed_by_safety: 196
- orders_blocked_by_safety: 0
- buy_fill_count: 99
- sell_fill_count: 91
- trade_count: 190
- final_equity: 1177300.0
- total_return: 0.1773
- annualized_return: 0.395494
- max_drawdown: -0.137515
- exposure_ratio: 0.76497
- capital_utilization: 0.76497

### MAX_EXPOSURE

- max_exposure_blocked_buy_orders: 56
- max_exposure_blocked_sell_orders: 0
- sell_orders_with_max_exposure_block: 0
- old_d1_medium_max_exposure_blocked_buy_orders: 89
- max_exposure_block_reduction_vs_old_d1_medium: 33

Sample debug:

- base_equity: 1036500.0
- cash_available: 101800.0
- current_exposure: 934700.0
- exposure_basis: equity
- issue_code: 67400
- max_allowed_exposure: 881025.000
- max_total_exposure_absolute_cap: None
- max_total_exposure_ratio: 0.85
- position_count: 5
- projected_exposure: 943700.0
- refined_classification: BUY_REVIEW_REQUIRED
- side: BUY
- system_fault: False

## Tests

- guard_tests: `PYTHONPATH=src python3 -m pytest tests/safety_phase11/test_guards_and_manager.py -q -> 14 passed`
- non_blocking_policy_tests: `PYTHONPATH=src python3 -m pytest tests/safety_phase11/test_non_blocking_review_policy.py -q -> 2 passed`
- lightweight_suite: `PYTHONPATH=src python3 -m pytest tests/safety_phase11 tests/paper_trading/test_safety_report_blog_section.py -q -> 88 passed`

## Integrity

- broker_api_connected: false
- websocket_connected: false
- line_send_executed: false
- demo_order_executed: false
- production_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_retraining_executed: false
- safety_results_used_for_ai_training: false
- one_year_full_executed: false
- five_year_full_executed: false
- parameters_changed_at_runtime: false

## Data Use

Safety result and audit result remain forbidden for AI training. This phase did not run AI retraining, Broker access, live sending, or live orders.

## Result

```text
PHASE11_SAFETY_CAP_FIX_EQUITY_LINKED_EXPOSURE_PASS
MAX_EXPOSURE_FIXED_CAP_REMOVED_FROM_DEFAULT_PATH
MEDIUM_SMOKE_PASS
ONE_YEAR_REFINED_MAINLINE_SMOKE_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
