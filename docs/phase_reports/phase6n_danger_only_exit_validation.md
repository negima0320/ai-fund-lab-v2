# Phase6-N Danger-Only Exit Validation

## 1. Purpose

Phase6-N tests whether Top3 positions should mostly be held until 20bd and exited only under hard danger conditions.

Comparison:

```text
Fixed_20bd
Current Position Managed
Danger-Only Exit
```

Completion decision:

```text
PHASE6N_DANGER_ONLY_EXIT_NOT_VALIDATED
```

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase6i_winner_holding_calibration.md`
- `docs/phase_reports/phase6m_top3_fixed_vs_position_validation.md`
- `docs/phase_reports/phase6l_top3_policy_validation.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/danger_only_exit_validation.py`
- `scripts/run_phase6n_danger_only_exit_validation.py`
- `tests/position_management_ai/test_phase6n_danger_only_exit_validation.py`
- `docs/phase_reports/phase6n_danger_only_exit_validation.md`

Generated outputs:

- `reports/position_management_ai/phase6n_danger_only_exit_validation.csv`
- `reports/position_management_ai/phase6n_danger_only_exit_validation.json`
- `reports/position_management_ai/phase6n_danger_only_exit_summary.json`
- `reports/position_management_ai/phase6n_danger_only_exit_yearly_summary.json`
- `reports/position_management_ai/phase6n_danger_only_exit_action_statistics.json`

## 4. Data

Target:

```text
2021-2026
5 target_dates per year
seed = 42
Top3 only
```

Candidate source:

```text
reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet
```

Opportunity source:

```text
reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet
reports/opportunity_ai/phase5i/models/opportunity_model.pkl
```

Position feature source:

```text
.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet
```

Future outcome source:

```text
.runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet
```

Future columns are evaluation-only and are not used for inference.

## 5. Target Dates

Phase6-L/Mと同じtarget_dateを使用。

| year | target_dates |
| --- | --- |
| 2021 | 2021-09-15, 2021-10-05, 2021-10-25, 2021-10-28, 2021-11-04 |
| 2022 | 2022-02-10, 2022-03-03, 2022-10-27, 2022-11-18, 2022-11-21 |
| 2023 | 2023-01-17, 2023-02-06, 2023-07-04, 2023-09-04, 2023-09-21 |
| 2024 | 2024-01-17, 2024-02-08, 2024-04-02, 2024-04-08, 2024-07-19 |
| 2025 | 2025-01-15, 2025-03-21, 2025-08-28, 2025-10-03, 2025-11-20 |
| 2026 | 2026-01-16, 2026-03-02, 2026-03-11, 2026-04-07, 2026-04-14 |

Row count:

```text
candidate_count: 1500
Top3 validation rows: 90
target_date_count: 30
code_count: 80
```

## 6. Comparison Definitions

Fixed_20bd:

```text
Top3を買ったと仮定し、20営業日後まで固定保有。
return = future_return_20bd
```

Current Position Managed:

```text
Phase6-Mと同じ既存Position Managed。
EXIT / REDUCE / ADD signalを使用。
REDUCE = 0.5 * checkpoint_return + 0.5 * future_return_20bd
ADDは実行しない。
```

Danger-Only Exit:

```text
Top3は基本20bdまでHOLD。
hard_break または danger_score >= 3 の場合のみ実EXIT。
REDUCE / ADD signalは記録のみで、実actionはHOLD。
```

Price path:

```text
full daily path is not used.
Phase4 future labels at 5bd / 10bd / 20bd checkpoints are used for evaluation approximation.
```

## 7. Danger Score / Hard Break

Exit rule:

```text
EXIT only when hard_break is true or danger_score >= 3
```

Danger score components:

```text
risk_guard_status bad and downside_risk_score >= 0.72
drawdown_from_peak <= -0.12
close_over_ma_20d < 0.94 and ma_5_20_ratio < 0.94
return_5d <= -0.08
volatility_20d >= 0.08 and current_return < 0
```

Hard break:

```text
current_return <= -0.14
and close_over_ma_20d < 0.96
and ma_5_20_ratio < 0.96
```

or

```text
risk_guard bad
and current_return <= -0.08
and deep drawdown or sharp 5d decline
```

## 8. Return Comparison

| strategy | mean_return | median_return | positive_return_rate | worst_return | best_return |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed_20bd | 0.169041 | 0.090624 | 0.644444 | -0.267263 | 2.835987 |
| Current_Position_Managed | 0.165223 | 0.090624 | 0.644444 | -0.223912 | 2.835987 |
| Danger_Only_Exit | 0.166162 | 0.079128 | 0.633333 | -0.236967 | 2.835987 |

Finding:

```text
Danger-Only Exit improves mean_return slightly vs Current Position Managed,
but remains below Fixed_20bd.
```

## 9. Risk Comparison

| strategy | drawdown_avoidance_rate | mean_min_return_20bd | worst_min_return_20bd | worst_return |
| --- | ---: | ---: | ---: | ---: |
| Fixed_20bd | 0.000000 | -0.068581 | -0.401476 | -0.267263 |
| Current_Position_Managed | 0.342105 | -0.068581 | -0.401476 | -0.223912 |
| Danger_Only_Exit | 0.421053 | -0.068581 | -0.401476 | -0.236967 |

Finding:

```text
Danger-Only Exit improves drawdown avoidance versus both Fixed_20bd and Current Position Managed.
```

However, worst_return is better than Fixed_20bd but worse than Current Position Managed.

## 10. Profit Retention

| strategy | profit_retention_rate | profit_decay_before_exit | captured_vs_max_return_rate |
| --- | ---: | ---: | ---: |
| Fixed_20bd | 0.206640 | 0.168743 | 0.206640 |
| Current_Position_Managed | 0.192676 | 0.172163 | 0.192676 |
| Danger_Only_Exit | 0.187656 | 0.171853 | 0.187656 |

Finding:

```text
Danger-Only Exit does not improve profit retention.
```

It is slightly worse than Current Position Managed on captured_vs_max_return_rate.

## 11. Winner Holding

| strategy | continue_winner_capture_rate | false_exit_rate | continue_winner_false_exit_count | over_reduce_count |
| --- | ---: | ---: | ---: | ---: |
| Fixed_20bd | 1.000000 | 0.000000 | 0 | 0 |
| Current_Position_Managed | 0.916667 | 0.611111 | 0 | 3 |
| Danger_Only_Exit | 0.805556 | 1.000000 | 7 | 0 |

Finding:

```text
Danger-Only removes over-reduce,
but false exits become worse.
```

This means the current danger definition still fires on positions that later recover or continue upward.

## 12. Action Distribution

Current Position Managed terminal actions:

```text
HOLD: 72
EXIT: 11
REDUCE: 7
```

Danger-Only actual actions:

```text
actual_hold_count: 66
actual_exit_count: 24
actual_reduce_count: 0
actual_add_count: 0
```

Danger-Only signal counts:

```text
HOLD signal: 225
EXIT signal: 11
REDUCE signal: 17
ADD signal: 0
```

Max danger score distribution:

```text
1: 51
2: 15
3: 11
4: 9
5: 3
6: 1
```

## 13. Yearly Comparison

Mean return:

| year | Fixed_20bd | Current_Position_Managed | Danger_Only_Exit |
| --- | ---: | ---: | ---: |
| 2021 | -0.009691 | -0.010247 | 0.001441 |
| 2022 | 0.286794 | 0.317998 | 0.322426 |
| 2023 | 0.105541 | 0.111097 | 0.105541 |
| 2024 | 0.295353 | 0.251388 | 0.292882 |
| 2025 | 0.355268 | 0.331992 | 0.288751 |
| 2026 | -0.019017 | -0.010893 | -0.014072 |

Worst return:

| year | Fixed_20bd | Current_Position_Managed | Danger_Only_Exit |
| --- | ---: | ---: | ---: |
| 2021 | -0.219818 | -0.219818 | -0.219818 |
| 2022 | -0.084871 | -0.084871 | -0.084871 |
| 2023 | -0.148148 | -0.111111 | -0.148148 |
| 2024 | -0.220315 | -0.216303 | -0.216303 |
| 2025 | -0.162349 | -0.223912 | -0.223912 |
| 2026 | -0.267263 | -0.193095 | -0.236967 |

Drawdown avoidance:

| year | Fixed_20bd | Current_Position_Managed | Danger_Only_Exit |
| --- | ---: | ---: | ---: |
| 2021 | 0.000000 | 0.666667 | 0.833333 |
| 2022 | 0.000000 | 0.000000 | 0.200000 |
| 2023 | 0.000000 | 0.200000 | 0.200000 |
| 2024 | 0.000000 | 0.400000 | 0.400000 |
| 2025 | 0.000000 | 0.285714 | 0.428571 |
| 2026 | 0.000000 | 0.400000 | 0.400000 |

## 14. 2026 Analysis

2026 remains weak. Danger-Only improves over Fixed_20bd, but not over Current Position Managed:

| metric | Fixed_20bd | Current_Position_Managed | Danger_Only_Exit |
| --- | ---: | ---: | ---: |
| mean_return | -0.019017 | -0.010893 | -0.014072 |
| worst_return | -0.267263 | -0.193095 | -0.236967 |
| drawdown_avoidance_rate | 0.000000 | 0.400000 | 0.400000 |
| profit_retention_rate | -0.207170 | -0.190162 | -0.207170 |

Interpretation:

```text
Danger-Only helps versus Fixed_20bd in 2026,
but Current Position Managed remains better defensively.
```

## 15. Was Danger-Only Exit Effective?

Overall:

```text
Not validated.
```

Danger-Only improved:

- mean_return vs Current Position Managed by a very small amount: `+0.000939`
- worst_return vs Fixed_20bd: `+0.030296`
- drawdown_avoidance_rate vs Fixed_20bd: `+0.421053`
- over_reduce_count vs Current Position Managed: `3 -> 0`

Danger-Only failed:

- mean_return remains below Fixed_20bd: `-0.002879`
- false_exit_rate worsens vs Current Position Managed: `+0.388889`
- continue_winner_capture_rate falls to `0.805556`
- profit_retention_rate falls below both Fixed_20bd and Current Position Managed

Conclusion:

```text
The idea is directionally useful for removing REDUCE,
but the danger trigger is still too noisy as an EXIT rule.
```

## 16. Audit

Forbidden feature audit:

```text
forbidden_feature_audit_status: OK
forbidden_feature_column_count: 0
```

Leakage audit:

```text
leakage_audit_status: OK
future_columns_not_used_for_inference: true
future_feature_columns: []
```

Execution boundary:

```text
broker_api_executed: false
order_executed: false
paper_trading_executed: false
capital_allocation_executed: false
live_order_executed: false
real_account_updated: false
full_backtest_executed: false
```

## 17. Verification

Commands:

```text
python3 -m pytest tests/position_management_ai/test_phase6n_danger_only_exit_validation.py
python3 scripts/run_phase6n_danger_only_exit_validation.py
```

Result:

```text
7 passed
PHASE6N_DANGER_ONLY_EXIT_NOT_VALIDATED
```

Runtime notes:

```text
pyarrow / joblib emitted CPU detection warnings under sandboxed execution.
The validation completed successfully.
```

## 18. Remaining Tasks

- Do not adopt the current Danger-Only EXIT rule as-is.
- Keep the useful part: REDUCE should not be actual execution for Top3 before Capital Allocation.
- Make EXIT even harder for Top3 winners.
- Split danger into review signal vs actual exit signal.
- Require persistent danger across multiple checkpoints before EXIT.
- Consider a Top3 winner lock unless current_return is negative and trend break is confirmed.
- Keep Broker API, order placement, Paper Trading, Capital Allocation, live order, and real account updates out of validation phases.
