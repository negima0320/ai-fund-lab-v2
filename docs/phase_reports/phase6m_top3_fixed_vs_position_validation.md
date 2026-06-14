# Phase6-M Top3 Fixed Hold vs Position AI Hold Validation

## 1. Purpose

Phase6-M validates the core Phase6 question:

```text
After buying Opportunity Top3,
is Position Management AI better than fixed holding?
```

Comparison:

```text
Fixed_10bd
Fixed_20bd
Position_Managed
```

Completion decision:

```text
PHASE6M_POSITION_AI_MIXED_RESULTS
```

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase6i_winner_holding_calibration.md`
- `docs/phase_reports/phase6k_expanded_random_validation.md`
- `docs/phase_reports/phase6l_top3_policy_validation.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/top3_fixed_vs_position_validation.py`
- `scripts/run_phase6m_top3_fixed_vs_position_validation.py`
- `tests/position_management_ai/test_phase6m_top3_fixed_vs_position_validation.py`
- `docs/phase_reports/phase6m_top3_fixed_vs_position_validation.md`

Generated outputs:

- `reports/position_management_ai/phase6m_top3_fixed_vs_position_validation.csv`
- `reports/position_management_ai/phase6m_top3_fixed_vs_position_validation.json`
- `reports/position_management_ai/phase6m_top3_fixed_vs_position_summary.json`
- `reports/position_management_ai/phase6m_top3_fixed_vs_position_yearly_summary.json`
- `reports/position_management_ai/phase6m_top3_position_action_statistics.json`

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

Phase6-Lと同じtarget_dateを使用。

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
code_count: 80
target_date_count: 30
```

## 6. Comparison Definitions

Fixed_10bd:

```text
Top3を買ったと仮定し、10営業日後まで固定保有。
return = future_return_10bd
```

Fixed_20bd:

```text
Top3を買ったと仮定し、20営業日後まで固定保有。
return = future_return_20bd
```

Position_Managed:

```text
Top3を買ったと仮定し、Phase6-I winner-holding calibrated baselineで
5bd / 10bd / 20bd checkpointごとにHOLD / EXIT / REDUCE / ADD候補判断。
```

REDUCE approximation:

```text
managed_return = 0.5 * reduce_checkpoint_return + 0.5 * future_return_20bd
```

ADD handling:

```text
ADD is not executed.
ADD = HOLD continuation + add_candidate_count only.
```

Price path:

```text
full daily path is not used.
Phase4 future labels at 5bd / 10bd / 20bd checkpoints are used for evaluation approximation.
```

## 7. Return Comparison

| strategy | mean_return | median_return | positive_return_rate | worst_return | best_return |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed_10bd | 0.118668 | 0.027847 | 0.544444 | -0.296534 | 1.807692 |
| Fixed_20bd | 0.169041 | 0.090624 | 0.644444 | -0.267263 | 2.835987 |
| Position_Managed | 0.165223 | 0.090624 | 0.644444 | -0.223912 | 2.835987 |

Finding:

```text
Position_Managed slightly underperforms Fixed_20bd on mean return,
but improves worst_return.
```

## 8. Risk Comparison

| strategy | mean_min_return_20bd | worst_min_return_20bd | drawdown_avoidance_rate |
| --- | ---: | ---: | ---: |
| Fixed_10bd | -0.068581 | -0.401476 | 0.000000 |
| Fixed_20bd | -0.068581 | -0.401476 | 0.000000 |
| Position_Managed | -0.068581 | -0.401476 | 0.342105 |

Finding:

```text
Position_Managed improves drawdown avoidance.
```

The future min return columns describe the same underlying 20bd path, so mean/worst min return is identical by construction. The actionable improvement is captured by `drawdown_avoidance_rate` and `worst_return`.

## 9. Profit Retention

| strategy | profit_retention_rate | profit_decay_before_exit | mean_max_return_20bd | captured_vs_max_return_rate |
| --- | ---: | ---: | ---: | ---: |
| Fixed_10bd | 0.072158 | 0.218161 | 0.347904 | 0.072158 |
| Fixed_20bd | 0.206640 | 0.168743 | 0.347904 | 0.206640 |
| Position_Managed | 0.192676 | 0.172163 | 0.347904 | 0.192676 |

Finding:

```text
Position_Managed is slightly worse than Fixed_20bd on profit retention.
```

This means Phase6-I winner holding is still somewhat too defensive for Top3 winners.

## 10. Winner Holding

| strategy | continue_winner_capture_rate | false_exit_rate | over_reduce_count |
| --- | ---: | ---: | ---: |
| Fixed_10bd | 0.916667 | 0.083333 | 0 |
| Fixed_20bd | 1.000000 | 0.000000 | 0 |
| Position_Managed | 0.916667 | 0.611111 | 3 |

Finding:

```text
Position_Managed still exits/reduces some winners too early.
```

The `false_exit_rate` is high because checkpoint EXIT/REDUCE sometimes occurs before later upside in the 20bd window.

## 11. Action Distribution

Checkpoint actions:

```text
HOLD: 228
EXIT: 11
REDUCE: 7
ADD: 0
```

Terminal actions:

```text
HOLD: 72
EXIT: 11
REDUCE: 7
```

ADD safety:

```text
add_loss_position_count: 0
add_exit_label_overlap_count: 0
```

## 12. Yearly Comparison

Mean return by year:

| year | Fixed_10bd | Fixed_20bd | Position_Managed |
| --- | ---: | ---: | ---: |
| 2021 | 0.040293 | -0.009691 | -0.010247 |
| 2022 | 0.349441 | 0.286794 | 0.317998 |
| 2023 | 0.043141 | 0.105541 | 0.111097 |
| 2024 | 0.162757 | 0.295353 | 0.251388 |
| 2025 | 0.095518 | 0.355268 | 0.331992 |
| 2026 | 0.020860 | -0.019017 | -0.010893 |

Improved major metric count vs Fixed_20bd:

| year | improved_major_metric_count |
| --- | ---: |
| 2021 | 1 |
| 2022 | 3 |
| 2023 | 5 |
| 2024 | 2 |
| 2025 | 1 |
| 2026 | 5 |

## 13. 2026 Analysis

2026 remains a weak regime, but Position_Managed improves several defensive metrics versus Fixed_20bd:

| metric | Fixed_20bd | Position_Managed |
| --- | ---: | ---: |
| mean_return | -0.019017 | -0.010893 |
| worst_return | -0.267263 | -0.193095 |
| profit_retention_rate | -0.207170 | -0.190162 |
| profit_decay_before_exit | 0.148395 | 0.145215 |
| drawdown_avoidance_rate | 0.000000 | 0.400000 |

Conclusion:

```text
Position AI is useful in weak regimes such as 2026, mainly by reducing damage.
```

## 14. Was Position AI Better Than Fixed Hold?

Overall:

```text
Mixed.
```

Position_Managed improves:

- worst_return
- drawdown_avoidance_rate
- 2026 weak-regime defensive behavior

Position_Managed does not improve:

- mean_return versus Fixed_20bd
- profit_retention_rate versus Fixed_20bd
- continue_winner_capture_rate versus Fixed_20bd

Interpretation:

```text
Phase6 currently adds defensive value,
but it does not yet beat Fixed_20bd as a profit-maximizing Top3 holding policy.
```

## 15. Audit

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

## 16. Verification

Commands:

```text
python3 -m pytest tests/position_management_ai/test_phase6m_top3_fixed_vs_position_validation.py
python3 scripts/run_phase6m_top3_fixed_vs_position_validation.py
```

Result:

```text
6 passed
PHASE6M_POSITION_AI_MIXED_RESULTS
```

Runtime notes:

```text
pyarrow / joblib emitted CPU detection warnings under sandboxed execution.
The validation completed successfully.
```

## 17. Remaining Tasks

- Reduce false exits for Top3 winners.
- Make REDUCE stricter when buy_rank <= 3 and expected_edge_score remains strong.
- Add a winner lock rule for Top3 unless hard-break conditions are confirmed.
- Compare checkpoint approximation with real daily close path when practical.
- Keep ADD as signal-only until Capital Allocation.
- Keep Broker API, order placement, Paper Trading, Capital Allocation, live order, and real account updates out of validation phases.
