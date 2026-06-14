# Phase6-O Exit Confirmation Validation

## 1. Purpose

Phase6-O validates whether Top3 positions should avoid immediate EXIT and instead require consecutive EXIT signals before selling.

Comparison:

```text
Fixed_20bd
Current Position Managed
Exit_Immediate
Exit_Confirm_2
Exit_Confirm_3
```

Completion decision:

```text
PHASE6O_EXIT_CONFIRMATION_NOT_VALIDATED
```

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase6m_top3_fixed_vs_position_validation.md`
- `docs/phase_reports/phase6n_danger_only_exit_validation.md`
- `docs/phase_reports/phase6l_top3_policy_validation.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/exit_confirmation_validation.py`
- `scripts/run_phase6o_exit_confirmation_validation.py`
- `tests/position_management_ai/test_phase6o_exit_confirmation_validation.py`
- `docs/phase_reports/phase6o_exit_confirmation_validation.md`

Generated outputs:

- `reports/position_management_ai/phase6o_exit_confirmation_validation.csv`
- `reports/position_management_ai/phase6o_exit_confirmation_validation.json`
- `reports/position_management_ai/phase6o_exit_confirmation_summary.json`
- `reports/position_management_ai/phase6o_exit_confirmation_yearly_summary.json`
- `reports/position_management_ai/phase6o_exit_confirmation_action_statistics.json`

## 4. Data

Target:

```text
2021-2026
5 target_dates per year
seed = 42
Top3 only
```

Sources:

```text
reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet
reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet
reports/opportunity_ai/phase5i/models/opportunity_model.pkl
.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet
.runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet
```

Future columns are evaluation-only and are not used for inference.

## 5. Target Dates

Phase6-L/M/Nと同じtarget_dateを使用。

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
Top3 fixed hold to 20bd.
return = future_return_20bd
```

Current Position Managed:

```text
Phase6-M current Position Managed.
EXIT / REDUCE / ADD signalを使用。
REDUCE = 0.5 * checkpoint_return + 0.5 * future_return_20bd
ADDは実行しない。
```

Exit_Immediate:

```text
1回でもEXIT signalが出たら売る。
REDUCE / ADD signalはHOLD扱い。
```

Exit_Confirm_2:

```text
EXIT signalが2回連続したら売る。
1回目のEXIT signalは警戒のみでHOLD。
REDUCE / ADD signalはHOLD扱い。
```

Exit_Confirm_3:

```text
EXIT signalが3回連続したら売る。
1-2回目のEXIT signalは警戒のみでHOLD。
REDUCE / ADD signalはHOLD扱い。
```

Checkpoint:

```text
5bd
10bd
20bd
```

Full daily path is not used. Phase4 future label checkpoints are used for evaluation approximation.

## 7. Return Comparison

| strategy | mean_return | median_return | positive_return_rate | worst_return | best_return |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed_20bd | 0.169041 | 0.090624 | 0.644444 | -0.267263 | 2.835987 |
| Current_Position_Managed | 0.165223 | 0.090624 | 0.644444 | -0.223912 | 2.835987 |
| Exit_Immediate | 0.164723 | 0.085470 | 0.633333 | -0.236967 | 2.835987 |
| Exit_Confirm_2 | 0.167902 | 0.090624 | 0.644444 | -0.296534 | 2.835987 |
| Exit_Confirm_3 | 0.169041 | 0.090624 | 0.644444 | -0.267263 | 2.835987 |

Finding:

```text
Exit_Confirm_3 restores mean_return to Fixed_20bd.
Exit_Confirm_2 improves over Current but worsens worst_return.
Exit_Immediate is not attractive.
```

## 8. Risk Comparison

| strategy | drawdown_avoidance_rate | mean_min_return_20bd | worst_min_return_20bd | worst_return |
| --- | ---: | ---: | ---: | ---: |
| Fixed_20bd | 0.000000 | -0.068581 | -0.401476 | -0.267263 |
| Current_Position_Managed | 0.342105 | -0.068581 | -0.401476 | -0.223912 |
| Exit_Immediate | 0.342105 | -0.068581 | -0.401476 | -0.236967 |
| Exit_Confirm_2 | 0.131579 | -0.068581 | -0.401476 | -0.296534 |
| Exit_Confirm_3 | 0.052632 | -0.068581 | -0.401476 | -0.267263 |

Finding:

```text
Confirmation reduces premature exits but also reduces drawdown avoidance.
```

Current Position Managed remains better on worst_return and drawdown avoidance.

## 9. Profit Retention

| strategy | profit_retention_rate | profit_decay_before_exit | captured_vs_max_return_rate |
| --- | ---: | ---: | ---: |
| Fixed_20bd | 0.206640 | 0.168743 | 0.206640 |
| Current_Position_Managed | 0.192676 | 0.172163 | 0.192676 |
| Exit_Immediate | 0.184417 | 0.172662 | 0.184417 |
| Exit_Confirm_2 | 0.206640 | 0.168743 | 0.206640 |
| Exit_Confirm_3 | 0.206640 | 0.168743 | 0.206640 |

Finding:

```text
Exit confirmation restores profit retention to Fixed_20bd.
```

## 10. Winner Holding

| strategy | continue_winner_capture_rate | false_exit_rate | continue_winner_false_exit_count | over_reduce_count |
| --- | ---: | ---: | ---: | ---: |
| Fixed_20bd | 1.000000 | 0.000000 | 0 | 0 |
| Current_Position_Managed | 0.916667 | 0.611111 | 0 | 3 |
| Exit_Immediate | 1.000000 | 1.000000 | 0 | 0 |
| Exit_Confirm_2 | 1.000000 | 1.000000 | 0 | 0 |
| Exit_Confirm_3 | 1.000000 | 1.000000 | 0 | 0 |

Finding:

```text
Confirmation removes over-reduce and keeps continue_winner capture at 1.0.
```

However, every confirmed exit in this checkpoint approximation is still a false exit by the current definition. The denominator is small, but this means EXIT signal quality remains weak.

## 11. Action / Signal Distribution

Signals:

```text
exit_signal_count: 20
reduce_signal_count: 19
add_signal_count: 0
```

Actions:

| policy | actual_hold_count | actual_exit_count | hold_after_first_exit_count | hold_after_second_exit_count |
| --- | ---: | ---: | ---: | ---: |
| Exit_Immediate | 77 | 13 | 0 | 0 |
| Exit_Confirm_2 | 85 | 5 | 13 | 0 |
| Exit_Confirm_3 | 88 | 2 | 13 | 5 |

Current Position Managed terminal actions:

```text
HOLD: 72
EXIT: 11
REDUCE: 7
```

REDUCE / ADD actual execution:

```text
actual_reduce_count: 0
actual_add_count: 0
```

## 12. Yearly Comparison

Mean return:

| year | Fixed_20bd | Current | Immediate | Confirm2 | Confirm3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | -0.009691 | -0.010247 | -0.010247 | -0.013745 | -0.009691 |
| 2022 | 0.286794 | 0.317998 | 0.317998 | 0.317998 | 0.286794 |
| 2023 | 0.105541 | 0.111097 | 0.105541 | 0.105541 | 0.105541 |
| 2024 | 0.295353 | 0.251388 | 0.288332 | 0.290271 | 0.295353 |
| 2025 | 0.355268 | 0.331992 | 0.331992 | 0.355268 | 0.355268 |
| 2026 | -0.019017 | -0.010893 | -0.014072 | -0.016715 | -0.019017 |

Confirmed exits:

| year | Immediate | Confirm2 | Confirm3 |
| --- | ---: | ---: | ---: |
| 2021 | 4 | 2 | 0 |
| 2022 | 1 | 0 | 0 |
| 2023 | 1 | 0 | 0 |
| 2024 | 2 | 1 | 1 |
| 2025 | 2 | 1 | 0 |
| 2026 | 4 | 1 | 1 |

## 13. 2026 Analysis

2026 remains weak:

| strategy | mean_return | worst_return | drawdown_avoidance_rate | confirmed_exit_count |
| --- | ---: | ---: | ---: | ---: |
| Fixed_20bd | -0.019017 | -0.267263 | 0.000000 | 0 |
| Current_Position_Managed | -0.010893 | -0.193095 | 0.400000 | 3 |
| Exit_Immediate | -0.014072 | -0.236967 | 0.400000 | 4 |
| Exit_Confirm_2 | -0.016715 | -0.236967 | 0.100000 | 1 |
| Exit_Confirm_3 | -0.019017 | -0.267263 | 0.100000 | 1 |

Interpretation:

```text
2026 benefits from some early exit behavior,
but confirmation weakens defensive value.
```

Current Position Managed remains strongest defensively in 2026.

## 14. Was EXIT Confirmation Effective?

Overall:

```text
Not validated as a replacement policy.
```

Useful findings:

- Confirm3 restores mean_return and profit retention to Fixed_20bd.
- Confirm2/3 reduce confirmed exits versus immediate exit.
- Confirm2/3 remove actual REDUCE and ADD execution.
- Confirm3 is the most Top3-compatible confirmation policy.

Problems:

- Confirm3 does not improve risk versus Fixed_20bd.
- Confirm2 worsens worst_return in this sample.
- Confirmed exits still have high false_exit_rate.
- Current Position Managed remains better for drawdown avoidance and worst_return.

## 15. Recommended Policy

Recommended from this validation:

```text
Use Exit_Confirm_3 as a monitoring policy, not an automatic sell policy.
```

Practical interpretation:

```text
For Top3, one EXIT signal should never sell.
Two EXIT signals should still be warning/review.
Three EXIT signals may escalate to manual review or stronger risk handling,
but automatic EXIT is not yet validated.
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
python3 -m pytest tests/position_management_ai/test_phase6o_exit_confirmation_validation.py
python3 scripts/run_phase6o_exit_confirmation_validation.py
```

Result:

```text
8 passed
PHASE6O_EXIT_CONFIRMATION_NOT_VALIDATED
```

Runtime notes:

```text
pyarrow / joblib emitted CPU detection warnings under sandboxed execution.
The validation completed successfully.
```

## 18. Remaining Tasks

- Do not use EXIT confirmation as automatic sell yet.
- Treat Top3 EXIT signals as monitoring / review signals.
- Improve EXIT signal quality before allowing automatic execution.
- Separate "drawdown warning" from "sell now".
- Test real daily close path instead of only 5/10/20bd checkpoints.
- Keep Broker API, order placement, Paper Trading, Capital Allocation, live order, and real account updates out of validation phases.
