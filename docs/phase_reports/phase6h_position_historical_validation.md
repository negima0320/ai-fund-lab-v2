# Phase6-H Position Historical Validation

## 1. Summary

Phase6-H validates whether adding Position Management AI improves historical outcomes compared with Opportunity AI alone.

Completion decision:

```text
PHASE6_VALIDATED
```

Reason:

Position Management improved at least one major metric. In this run it improved four major aggregate metrics:

- average return
- profit retention rate
- profit decay before exit
- winner to loser rate

Important caveat:

The calibrated Position Management rule is still too aggressive for winner holding. `continue_winner_capture_rate` declined materially and the audit found continue-winner EXIT / REDUCE cases. Phase6 is validated for risk / profit-retention behavior, but Phase6-I should recalibrate winner-holding behavior before Phase7 uses these actions for capital allocation.

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase5_final_handoff_for_phase6.md`
- `docs/phase_reports/phase6_position_management_completion_audit.md`
- `docs/phase_reports/phase6e_baseline_rule_calibration.md`
- `docs/phase_reports/phase6f_realdata_position_dry_run.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/historical_validation.py`
- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `scripts/run_phase6h_historical_validation.py`
- `tests/position_management_ai/test_phase6h_historical_validation.py`
- `docs/phase_reports/phase6h_position_historical_validation.md`

Generated outputs:

- `reports/position_management_ai/phase6h_historical_validation.json`
- `reports/position_management_ai/phase6h_historical_validation.csv`
- `reports/position_management_ai/phase6h_baseline_vs_position_comparison.json`
- `reports/position_management_ai/phase6h_position_action_statistics.json`

## 4. Used Data

Opportunity source:

```text
reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet
reports/opportunity_ai/phase5i/models/opportunity_model.pkl
```

Technical feature source:

```text
.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet
```

Opportunity signal:

```text
Phase5 formal Opportunity model re-scoring
```

Price path limitation:

The full 2025 daily quote path for all selected symbols was not available as normalized close prices in the local normalized quote artifact. Therefore Phase6-H uses Phase5 future labels as evaluation-only data and approximates 5 / 10 / 20 business-day validation checkpoints from:

- `label__future_return_20d`
- `label__future_max_return_20d`
- `label__future_max_drawdown_20d`

These labels are not used as inference features. They are used only to evaluate the historical validation outcome.

## 5. Validation Scope

Target period:

```text
2025
```

Scope:

```text
target_date_count: 80
top_n_per_date: 5
row_count: 400
code_count: 164
```

The validation is medium-sized, not a full backtest. It does not execute Broker API, orders, Paper Trading, live order, real account updates, or Capital Allocation.

## 6. Baseline Definition

Baseline:

```text
Opportunity AI only
```

Rule:

```text
Phase5 formal Opportunity model top5
fixed 20 business-day hold
```

Reason:

Phase5 Opportunity AI targets a 20 business-day expected edge horizon, so the fixed 20 business-day hold is the most direct baseline.

## 7. Position Managed Definition

Position Managed:

```text
Opportunity AI
+
Phase6-E calibrated Position Management AI
```

Rule:

- enter the same Opportunity top5 candidates as the baseline
- evaluate Position Management checkpoints at 5 / 10 / 20 business days
- apply `HOLD`, `EXIT`, `ADD`, `REDUCE`
- `EXIT` closes the validation position at the checkpoint return
- `REDUCE` is treated as half protected at checkpoint and half held to 20bd for validation only
- `ADD` is counted as a signal only and does not add capital

No capital allocation is performed.

## 8. Profit Retention Comparison

| metric | Opportunity only | Opportunity + Position |
| --- | ---: | ---: |
| average_return | 0.052786 | 0.081954 |
| profit_retention_rate | 0.130009 | 0.146715 |
| profit_decay_before_exit | 0.103081 | 0.089230 |
| avg_hold_days | 20.000000 | 5.500000 |
| winner_hold_days | 20.000000 | 5.000000 |
| loser_hold_days | 20.000000 | 6.111111 |

Interpretation:

Position Management improved profit retention and reduced profit decay. The improvement comes largely from shortening loser holding periods.

## 9. Winner To Loser Comparison

| metric | Opportunity only | Opportunity + Position |
| --- | ---: | ---: |
| winner_to_loser_rate | 0.226190 | 0.206349 |

Interpretation:

The Position Managed version reduced the rate at which trades with meaningful upside became losers by the 20bd endpoint.

## 10. Continue Winner Capture

| metric | Opportunity only | Opportunity + Position |
| --- | ---: | ---: |
| continue_winner_capture_rate | 0.899471 | 0.021164 |

Interpretation:

This is the biggest weakness. Position Management improved risk / retention metrics, but it does not yet preserve enough continuing winners. The calibrated rule is still too eager to EXIT or REDUCE under the label-based checkpoint validation.

## 11. EXIT Quality

| metric | Opportunity + Position |
| --- | ---: |
| exit_before_drawdown_rate | 0.431472 |
| false_exit_rate | 0.258883 |
| average_exit_return | -0.056925 |

Interpretation:

The engine exits before meaningful drawdown in many cases, but false exits are still too high. This supports validation as a risk filter, not yet as a fully acceptable winner-retention policy.

## 12. Position Action Statistics

Checkpoint action counts:

| action | count |
| --- | ---: |
| HOLD | 35 |
| EXIT | 156 |
| ADD | 0 |
| REDUCE | 238 |

Terminal action counts:

| action | count |
| --- | ---: |
| HOLD | 6 |
| EXIT | 156 |
| REDUCE | 238 |

Interpretation:

The current policy is risk-heavy. ADD did not occur in this validation because the Phase6-E ADD rule is intentionally narrow and this simulation does not allocate capital.

## 13. ADD Safety

```text
add_loss_position_count: 0
add_exit_label_overlap_count: 0
add_safety_status: OK
```

ADD remains a candidate signal only. No averaging down was detected.

## 14. HOLD / EXIT Safety

```text
continue_winner_wrong_exit_count: 7
continue_winner_over_reduce_count: 178
hold_exit_safety_status: WARN
```

Interpretation:

This is a Phase6-I blocker for policy quality, not for implementation safety. The Position AI is effective at avoiding some loser decay, but it is too aggressive for continuing winners.

## 15. Forbidden / Leakage Audit

```text
forbidden_feature_audit_status: OK
forbidden_feature_column_count: 0
feature_label_separation_status: OK
leakage_audit_status: OK
```

Future labels are used only for validation outcomes and are not included in inference features.

Execution boundary:

```text
broker_api_executed: false
order_executed: false
paper_trading_executed: false
capital_allocation_executed: false
full_backtest_executed: false
```

## 16. Is Position AI Effective?

Yes, but with documented limitations.

Position AI is effective on the requested completion criterion because at least one major metric improved. In this run, four major metrics improved:

- `average_return`
- `profit_retention_rate`
- `profit_decay_before_exit`
- `winner_to_loser_rate`

However, the winner-retention behavior is not yet good enough:

- `continue_winner_capture_rate` fell sharply
- false exits remain high
- REDUCE is overused on continuing winners

Recommended interpretation:

```text
PHASE6_VALIDATED_FOR_RISK_AND_PROFIT_RETENTION
NOT_YET_VALIDATED_FOR_WINNER_HOLDING_QUALITY
```

The formal completion status remains:

```text
PHASE6_VALIDATED
```

because the user-defined success condition is at least one improved major metric.

## 17. Verification

Command:

```text
python3 -m pytest tests/position_management_ai/test_phase6h_historical_validation.py
```

Result:

```text
5 passed
```

## 18. Next Tasks

- Phase6-I should recalibrate REDUCE / EXIT so continuing winners are held longer.
- Add a direct target for `continue_winner_capture_rate`.
- Separate `risk_exit` from `profit_protection_reduce`.
- Require stronger confirmation before REDUCE on high expected-edge winners.
- Add official daily quote path validation when normalized historical prices are available for the full Opportunity universe.
- Keep Broker API, order placement, Paper Trading, Capital Allocation, live order, and real account updates out of scope until explicitly enabled.
