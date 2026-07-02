# Phase12-H SELL Integrated Backtest Evaluation

- status: PHASE12H_SELL_INTEGRATED_BACKTEST_EVALUATION_COMPLETE
- judgement: SELL_INTEGRATION_NEEDS_CALIBRATION_BEFORE_PRODUCTION_REVENUE_CLAIM
- ai_retraining_executed: false
- demo_order_executed: false
- production_order_executed: false
- line_send_executed: false
- data_leakage_detected: false

## One Month Smoke

- status: PASS
- period: {"business_day_count": 21, "end_date": "2026-05-31", "start_date": "2026-05-01"}
- initial_equity: 1000000.0
- final_equity: 941590.0
- total_return: -0.05841
- annualized_return: -0.504487
- max_drawdown: -0.073091
- profit_factor: 0.204224
- trade_count: 33
- buy_count: 17
- sell_count: 16
- average_holding_days: 5.272727
- median_holding_days: 5
- win_rate: 0.272727
- average_win: 5934.285714
- average_loss: -11588.888889
- profit_retention_rate: 0.813206
- capital_turnover: 3.268332
- cash_ratio_average: 0.417588
- exposure_ratio_average: 0.580393
- output_dir: reports/safety/phase11/integrated_backtest/phase12h_sell_integrated_1m_smoke

## One Year Result

- status: PASS
- period: {"business_day_count": 260, "end_date": "2026-05-31", "start_date": "2025-06-01"}
- initial_equity: 1000000.0
- final_equity: 1188520.0
- total_return: 0.18852
- annualized_return: 0.176736
- max_drawdown: -0.247342
- profit_factor: 0.655658
- trade_count: 300
- buy_count: 108
- sell_count: 192
- average_holding_days: 16.307692
- median_holding_days: 8.0
- win_rate: 0.403846
- average_win: 9531.150442
- average_loss: -13308.076923
- profit_retention_rate: 0.638611
- capital_turnover: 24.754629
- cash_ratio_average: 0.322488
- exposure_ratio_average: 0.678653
- output_dir: reports/safety/phase11/integrated_backtest/phase12h_sell_integrated_1y

## Five Year Result

- status: PASS
- period: {"business_day_count": 1304, "end_date": "2026-05-31", "start_date": "2021-06-01"}
- initial_equity: 1000000.0
- final_equity: 9029850.0
- total_return: 8.02985
- annualized_return: 0.512017
- max_drawdown: -0.215802
- profit_factor: 0.936089
- trade_count: 1214
- buy_count: 368
- sell_count: 846
- average_holding_days: 21.32964
- median_holding_days: 10
- win_rate: 0.554017
- average_win: 28701.21643
- average_loss: -50300.585366
- profit_retention_rate: 0.684441
- capital_turnover: 102.366496
- cash_ratio_average: 0.355711
- exposure_ratio_average: 0.650591
- output_dir: reports/safety/phase11/integrated_backtest/phase12h_sell_integrated_5y

## Before / After

- one_year: {"after": {"annualized_return": 0.176736, "buy_fill_count": 108, "final_equity": 1188520.0, "max_drawdown": -0.247342, "profit_factor": 0.655658, "sell_fill_count": 192, "total_return": 0.18852, "trade_count": 300}, "before": {"annualized_return": 0.72588, "buy_fill_count": 159, "final_equity": 1784520.0, "max_drawdown": -0.121077, "profit_factor": 1.574577, "sell_fill_count": 151, "total_return": 0.78452, "trade_count": 310}, "delta": {"annualized_return": -0.549144, "buy_fill_count": -51.0, "final_equity": -596000.0, "max_drawdown": -0.126265, "profit_factor": -0.918919, "sell_fill_count": 41.0, "total_return": -0.596, "trade_count": -10.0}, "status": "PASS"}
- five_year: {"after": {"annualized_return": 0.512017, "buy_fill_count": 368, "final_equity": 9029850.0, "max_drawdown": -0.215802, "profit_factor": 0.936089, "sell_fill_count": 846, "total_return": 8.02985, "trade_count": 1214}, "before": {"annualized_return": 0.312197, "buy_fill_count": 300, "final_equity": 4246630.0, "max_drawdown": -0.251216, "profit_factor": 1.680506, "sell_fill_count": 298, "total_return": 3.24663, "trade_count": 598}, "delta": {"annualized_return": 0.19982, "buy_fill_count": 68.0, "final_equity": 4783220.0, "max_drawdown": 0.035414, "profit_factor": -0.744417, "sell_fill_count": 548.0, "total_return": 4.78322, "trade_count": 616.0}, "status": "PASS"}
- before_source: {"five_year": "reports/safety/phase11/integrated_backtest/fix_g_5y_refined_mainline_full/summary.json", "five_year_exit_source": "fallback", "one_year": "reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure/summary.json", "one_year_exit_source": "fallback"}
- after_exit_source: phase12_operations_exit_adapter

## SELL Integration Usage

- phase12h_sell_integrated_1m_smoke: {"exit_adapter_called": true, "fill_ledger_report_reflected": true, "order_plan_sell_items": 17, "sell_filled": 16, "sell_items_with_exit_source": 17, "sell_items_with_position_id": 17, "sell_items_with_sell_reason": 17}
- phase12h_sell_integrated_1y: {"exit_adapter_called": true, "fill_ledger_report_reflected": true, "order_plan_sell_items": 202, "sell_filled": 192, "sell_items_with_exit_source": 202, "sell_items_with_position_id": 202, "sell_items_with_sell_reason": 202}
- phase12h_sell_integrated_5y: {"exit_adapter_called": true, "fill_ledger_report_reflected": true, "order_plan_sell_items": 901, "sell_filled": 846, "sell_items_with_exit_source": 901, "sell_items_with_position_id": 901, "sell_items_with_sell_reason": 901}

## SELL Reason Analysis

- pm_loss_cut_exit: {"count": 74, "pnl": -1018430.0}
- pm_max_holding_days_exit: {"count": 25, "pnl": 332580.0}
- pm_profit_protection_reduce: {"count": 93, "pnl": 724840.0}

## Early Sell Analysis

- evaluated_sell_count: 192
- future_return_5d_average: -0.008933
- future_return_20d_average: -0.017132
- future_return_45d_average: -0.04697
- large_up_after_sell_count_20d_gt_5pct: 60
- early_sell_opportunity_loss: 20.25859
- largest_up_after_sell: [{"business_date": "2025-12-17", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": -0.119266, "future_drawdown_45d": -0.119266, "future_drawdown_5d": -0.119266, "future_return_20d": 1.522936, "future_return_45d": 0.46789, "future_return_5d": 0.146789, "issue_code": "57210", "notional": 95920.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2025-12-16", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": -0.135135, "future_drawdown_45d": -0.135135, "future_drawdown_5d": -0.135135, "future_return_20d": 1.387387, "future_return_45d": 0.373874, "future_return_5d": 0.013514, "issue_code": "57210", "notional": 186480.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2025-10-24", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": -0.055556, "future_drawdown_45d": -0.055556, "future_drawdown_5d": -0.055556, "future_return_20d": 1.222222, "future_return_45d": 2.083333, "future_return_5d": 0.111111, "issue_code": "69930", "notional": 7200.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2025-10-27", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": -0.028571, "future_drawdown_45d": -0.028571, "future_drawdown_5d": -0.028571, "future_return_20d": 1.171429, "future_return_45d": 2.742857, "future_return_5d": 0.142857, "issue_code": "69930", "notional": 3500.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2025-12-18", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": 0.081218, "future_drawdown_45d": 0.081218, "future_drawdown_5d": 0.13198, "future_return_20d": 1.005076, "future_return_45d": 0.624365, "future_return_5d": 0.208122, "issue_code": "57210", "notional": 39400.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2025-12-19", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": 0.086735, "future_drawdown_45d": 0.086735, "future_drawdown_5d": 0.147959, "future_return_20d": 0.887755, "future_return_45d": 0.581633, "future_return_5d": 0.173469, "issue_code": "57210", "notional": 23520.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2026-02-17", "exit_action": "EXIT", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": 0.263158, "future_drawdown_45d": 0.263158, "future_drawdown_5d": 0.421053, "future_return_20d": 0.789474, "future_return_45d": 0.526316, "future_return_5d": 0.473684, "issue_code": "93990", "notional": 190000.0, "sell_reason": "pm_loss_cut_exit"}, {"business_date": "2025-10-22", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": -0.055556, "future_drawdown_45d": -0.055556, "future_drawdown_5d": -0.055556, "future_return_20d": 0.722222, "future_return_45d": 0.861111, "future_return_5d": -0.055556, "issue_code": "69930", "notional": 25200.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2026-02-09", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": 0.076596, "future_drawdown_45d": -0.112766, "future_drawdown_5d": 0.076596, "future_return_20d": 0.634043, "future_return_45d": 0.134043, "future_return_5d": 0.231915, "issue_code": "77770", "notional": 141000.0, "sell_reason": "pm_profit_protection_reduce"}, {"business_date": "2025-10-23", "exit_action": "REDUCE", "exit_source": "phase12_operations_exit_adapter", "future_drawdown_20d": -0.081081, "future_drawdown_45d": -0.081081, "future_drawdown_5d": -0.081081, "future_return_20d": 0.621622, "future_return_45d": 1.189189, "future_return_5d": 0.0, "issue_code": "69930", "notional": 14800.0, "sell_reason": "pm_profit_protection_reduce"}]

## Loss Cut Analysis

- evaluated_sell_count: 192
- future_drawdown_5d_average: -0.069508
- future_drawdown_20d_average: -0.162872
- future_drawdown_45d_average: -0.259516
- loss_expansion_prevented_count_20d_lt_minus_5pct: 143
- loss_cut_avoided_loss: 1146749.84075

## Safety Analysis

- orders_generated: 397
- orders_allowed_by_safety: 313
- orders_blocked_by_safety: 84
- MAX_EXPOSURE_blocks: 84
- NON_BLOCKING_REVIEW_count: 177
- BLOCK_count: 84
- SYSTEM_EMERGENCY_STOP_count: 0

## Blocking Issues

- blocking_issues: []

## Recommended Next Tasks

- recommended_next_tasks: ["Tune Phase12 Exit Adapter thresholds; current integrated exit underperforms fallback on annualized return.", "Review early-sell cases with >5% 20-day post-sell return and add confirmation logic if needed.", "Keep Demo/Production order wire locked until backtest and Demo operation review pass."]
