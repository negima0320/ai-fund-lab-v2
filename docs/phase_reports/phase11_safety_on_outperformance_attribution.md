# Phase11 Post-Audit Analysis: Safety ON Outperformance Attribution

## Status

```text
PHASE11_SAFETY_ON_OUTPERFORMANCE_ATTRIBUTION_COMPLETE
CONCLUSION_A
NO_BACKTEST_RERUN_NO_BROKER_NO_ORDER_NO_AI_RETRAINING
```

## Scope

Fix-H 1年 refined mainline smoke の既存出力だけを使い、Safety ON が Safety OFF を上回った理由を調査した。修正実装、1年/5年backtest再実行、Broker接続、発注、LINE実送信、AI再学習は行っていない。

## Read Materials

- `docs/phase_reports/phase11_completion_audit.md`
- `reports/phase_reports/phase11_completion_audit.json`
- `docs/phase_reports/phase11z_fix_h_1y_equity_linked_exposure.md`
- `reports/phase_reports/phase11z_fix_h_1y_equity_linked_exposure.json`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py`

## Source Artifacts

- `reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure/order_decisions.json`
- `reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure/virtual_trades.json`
- `reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure/daily_audit.json`
- `reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure_safety_off/order_decisions.json`
- `reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure_safety_off/virtual_trades.json`
- `reports/safety/phase11/integrated_backtest/fix_h_1y_equity_linked_exposure_safety_off/daily_audit.json`
- `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet`
- `reports/phase7_prestudy/opportunity_ranked_daily.parquet`

## Fix-H Baseline

### Safety ON

- final_equity: 1784520.0
- total_return: 0.78452
- max_drawdown: -0.121077
- trade_count: 310
- buy_fill_count: 159
- sell_fill_count: 151
- orders_blocked_by_safety: 120

### Safety OFF

- final_equity: 1426090.0
- total_return: 0.42609
- max_drawdown: -0.214177
- trade_count: 378
- buy_fill_count: 193
- sell_fill_count: 185
- orders_blocked_by_safety: 0

- final_equity_difference_on_minus_off: 358430.0
- drawdown_improvement_points: -0.0931

## Blocked BUY After-Performance

- blocked_buy_count: 120
- blocked_order_value_total: 19406930.0
- blocked_order_value_mean: 161724.42
- blocked_order_value_median: 159600.0
- candidate_rank_available_count: 114
- candidate_rank_mean: 3.140351
- blocked_score_mean: 96.859649

### Future Return 5bd

- count: 120
- mean: 0.005228
- median: -0.013713
- positive_rate: 0.4

### Future Return 10bd

- count: 120
- mean: -0.018588
- median: -0.050125
- positive_rate: 0.341667

### Future Return 20bd

- count: 120
- mean: -0.042473
- median: -0.077618
- positive_rate: 0.316667

### Future Return 45bd

- count: 101
- mean: 0.084591
- median: -0.045228
- positive_rate: 0.386139

- max_up_over_15pct_count: 52
- max_up_over_30pct_count: 36
- max_down_over_8pct_count: 89
- max_down_over_15pct_count: 75

Top blocked issue codes:

- 57210: 12
- 33500: 7
- 67400: 6
- 45960: 6
- 21340: 5
- 45970: 4
- 69930: 4
- 14590: 4
- 55950: 3
- 37770: 3
- 45940: 2
- 25860: 2
- 13600: 2
- 77460: 2
- 82670: 2

Top blocked dates:

- 2025-06-24: 2
- 2025-07-22: 2
- 2025-08-19: 2
- 2025-08-22: 2
- 2025-09-18: 2
- 2025-09-29: 2
- 2025-10-01: 2
- 2025-10-22: 2
- 2025-10-29: 2
- 2025-11-05: 2
- 2025-11-12: 2
- 2026-01-15: 2
- 2026-03-25: 2
- 2026-04-08: 2
- 2026-04-22: 2

## Safety OFF Actual Buy Check

- blocked_in_on_bought_in_off_count: 35
- blocked_in_on_not_bought_in_off_count: 85
- blocked_in_on_bought_in_off_realized_pnl: -103690.0
- blocked_in_on_bought_in_off_closed_lot_count: 35
- blocked_in_on_bought_in_off_win_rate: 0.428571
- blocked_in_on_bought_in_off_profit_factor: 0.747375
- matching_method: matched by ON blocked order decision_date + issue_code to OFF filled BUY order decision; realized PnL approximated by FIFO lots because virtual_trades order_id is redacted.

## Difference Decomposition

- final_equity_difference_on_minus_off: 358430.0
- trade_count_difference_on_minus_off: -68
- missed_winners_by_safety_endpoint_45bd: 39
- avoided_losers_by_safety_endpoint_45bd: 59
- missed_large_upside_path_45bd_ge_15pct: 52
- avoided_large_drawdown_path_45bd_le_minus_8pct: 89
- position_sizing_effect: Safety ON used fewer trades but profit_factor was higher and realized_loss was lower; MAX_EXPOSURE reduced marginal buys near high exposure.
- cash_timing_effect: Safety ON preserved more cash at block points and avoided additional exposure during vulnerable periods.
- replacement_timing_effect: Safety ON had fewer buy/sell replacements, avoiding some churn; exact attribution limited because artifact lacks full candidate trace per rejected replacement.
- drawdown_reduction_effect: Safety ON maximum drawdown improved by about 9.31 percentage points with fewer exposure-increasing buys during OFF drawdown period.

## MAX_EXPOSURE Timing

- average_base_equity_at_block: 1431061.333333
- average_exposure_at_block: 1131826.583333
- average_cash_at_block: 299234.75
- average_position_count_at_block: 7.508333

Block count by month:

- 2025-06: 6
- 2025-07: 9
- 2025-08: 13
- 2025-09: 10
- 2025-10: 13
- 2025-11: 8
- 2025-12: 11
- 2026-01: 11
- 2026-02: 6
- 2026-03: 8
- 2026-04: 12
- 2026-05: 13

Block count by market regime:

- flat: 106
- up: 6
- down: 8

Monthly market regimes:

- 2025-06: flat avg_return=0.033803 dispersion=0.131638
- 2025-07: flat avg_return=0.046213 dispersion=0.102429
- 2025-08: flat avg_return=0.04773 dispersion=0.220308
- 2025-09: flat avg_return=0.00947 dispersion=0.091209
- 2025-10: flat avg_return=0.013453 dispersion=0.103357
- 2025-11: flat avg_return=0.025194 dispersion=0.135502
- 2025-12: flat avg_return=0.016303 dispersion=0.104774
- 2026-01: flat avg_return=0.027158 dispersion=0.107352
- 2026-02: up avg_return=0.075982 dispersion=0.169569
- 2026-03: down avg_return=-0.074061 dispersion=0.099891
- 2026-04: flat avg_return=0.002743 dispersion=0.119218
- 2026-05: flat avg_return=0.010886 dispersion=0.16805

## Drawdown Analysis

- drawdown_period_on: {'peak_date': '2025-09-02', 'trough_date': '2025-09-26', 'max_drawdown': -0.121077}
- drawdown_period_off: {'peak_date': '2026-03-11', 'trough_date': '2026-05-27', 'max_drawdown': -0.214177}
- positions_during_drawdown_on: {'average_position_count': 7.526316, 'top_position_codes': [['17730', 19], ['65380', 19], ['95010', 17], ['52550', 17], ['69930', 13], ['99730', 11], ['45060', 8], ['33500', 8], ['45630', 7], ['89180', 5], ['45940', 5], ['48380', 5], ['81050', 5], ['45640', 2], ['48330', 2]]}
- positions_during_drawdown_off: {'average_position_count': 8, 'top_position_codes': [['83030', 42], ['50200', 38], ['45960', 37], ['48110', 32], ['79850', 28], ['36970', 26], ['77460', 19], ['67720', 18], ['13600', 17], ['61400', 17], ['67230', 15], ['33500', 15], ['76030', 15], ['37770', 14], ['74260', 14], ['46910', 12], ['45060', 11], ['67400', 11], ['71830', 10], ['71380', 9]]}
- blocked_buys_during_off_drawdown: 32
- cash_ratio_during_drawdown_on: 0.220799
- cash_ratio_during_drawdown_off: 0.246498
- average_position_count_during_drawdown_on: 7.526316
- average_position_count_during_drawdown_off: 8.0

## Conclusion

- label: A
- text: MAX_EXPOSUREが悪いBUYを止めたため、Safety ONが実力で良化した可能性が高い
- rationale: Blocked candidates had mixed standalone future returns, but OFF-matched blocked buys produced realized PnL evidence and Safety ON reduced drawdown. Causality is limited by redacted order ids and missing blocked-order trace fields.

## Artifact Limitations

- virtual_trades order_id is redacted, so blocked-to-OFF-realized-PnL matching uses date/code and FIFO approximation.
- order_decisions does not persist quantity/candidate rank directly; rank was joined from Phase7 ranked_daily where available.
- daily_audit has position_count/cash/equity but not full position snapshots; positions during drawdown were reconstructed from virtual_trades.

## Recommended Future Artifacts

- `blocked_order_trace.json`
- `order_decision_trace.json`
- `candidate_rank_at_block`
- `would_have_bought_in_safety_off`
- `future_return_after_block`
- `unredacted_internal_order_join_key_or_stable_hash`
- `position_snapshot_by_day`

## Forbidden Actions Confirmation

- implementation_changed: false
- one_year_backtest_rerun: false
- five_year_backtest_rerun: false
- broker_api_connected: false
- websocket_connected: false
- line_send_executed: false
- demo_order_executed: false
- production_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_retraining_executed: false
- safety_results_used_for_ai_training: false

## Result

```text
PHASE11_SAFETY_ON_OUTPERFORMANCE_ATTRIBUTION_COMPLETE
CONCLUSION_A
NO_BACKTEST_RERUN_NO_BROKER_NO_ORDER_NO_AI_RETRAINING
```
