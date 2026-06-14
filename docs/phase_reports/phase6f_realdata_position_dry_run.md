# Phase6-F Real-Data Position Dry-Run

## 1. Summary

Phase6-F connects Position Management AI to local normalized daily quotes for a small historical real-data dry-run. It generates position features, label dataset, calibrated baseline actions, and action-label alignment.

Readiness:

```text
READY_FOR_PHASE6G_POLICY_EXPANSION
```

Not executed:

- ML training
- full backtest
- Broker API
- order placement
- Paper Trading
- capital allocation

## 2. Read Docs

- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase6a_position_management_schema_and_baseline.md`
- `docs/phase_reports/phase6b_position_feature_builder.md`
- `docs/phase_reports/phase6c_position_label_dataset_audit.md`
- `docs/phase_reports/phase6d_baseline_label_alignment_audit.md`
- `docs/phase_reports/phase6e_baseline_rule_calibration.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/realdata_dry_run.py`
- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `scripts/run_phase6f_realdata_position_dry_run.py`
- `tests/position_management_ai/test_phase6f_realdata_dry_run.py`
- `docs/phase_reports/phase6f_realdata_position_dry_run.md`

Generated outputs:

- `reports/position_management_ai/phase6f_realdata_position_features.csv`
- `reports/position_management_ai/phase6f_realdata_label_dataset.csv`
- `reports/position_management_ai/phase6f_realdata_alignment.csv`
- `reports/position_management_ai/phase6f_realdata_audit.json`

## 4. Used Data

Normalized daily quote source:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Available local range:

```text
quote_date_min: 2026-03-02
quote_date_max: 2026-06-01
quote_row_count: 1980
quote_code_count: 30
```

Phase5 formal latest Opportunity output was not used because it targets `2026-06-12`, while the usable normalized quote history ends on `2026-06-01`.

Opportunity signal source:

```text
proxy_from_normalized_quotes
```

The proxy is derived from local quote momentum, trend, and volatility. It is not Phase5 official Opportunity AI output and must not be treated as such.

## 5. Target Scope

Target dates:

```text
2026-04-21
2026-05-01
2026-05-13
```

Scope:

```text
code_count: 12
scenario_row_count: 36
feature_row_count: 36
label_row_count: 36
```

Codes:

```text
10010
10020
10030
10040
10050
10060
10070
10080
10090
10100
10110
10120
```

## 6. Feature Generation

Feature builder ran on real normalized quotes and generated:

- `entry_price`
- `current_price`
- `holding_days`
- `unrealized_return`
- `peak_return`
- `drawdown_from_peak`
- `return_1d`
- `return_5d`
- `return_20d`
- `volume_ratio_5d`
- `volume_ratio_20d`
- `close_over_ma_5d`
- `close_over_ma_20d`
- `ma_5_20_ratio`
- `ma_20_60_ratio`
- `volatility_20d`
- `trend_strength_score`
- proxy `expected_edge_score`
- proxy `buy_rank`
- proxy `downside_risk_score`
- proxy `risk_guard_status`

## 7. Label Distribution

| label | true | false |
| --- | ---: | ---: |
| `label__label_continue_winner` | 36 | 0 |
| `label__label_exit_before_drawdown` | 0 | 36 |
| `label__label_add_candidate` | 10 | 26 |
| `label__label_reduce_candidate` | 0 | 36 |

Interpretation:

- This local quote slice is a mostly upward / benign fixture-like real-data range.
- It is useful for plumbing and audit checks, but not enough for downside calibration.

## 8. Action Distribution

Calibrated baseline result:

| action | count |
| --- | ---: |
| HOLD | 36 |

Interpretation:

- The calibrated rule correctly avoids EXIT / REDUCE in a dataset where all rows are labeled `continue_winner=true` and no rows are labeled future drawdown / reduce.
- ADD did not fire because the calibrated ADD rule is intentionally stricter than generic continue-winner behavior.

## 9. Alignment Result

Alignment metrics:

```text
hold_continue_winner_rate: 1.0
hold_exit_label_rate: 0.0
exit_continue_winner_rate: 0.0
exit_exit_label_rate: 0.0
add_add_label_rate: 0.0
add_exit_label_rate: 0.0
reduce_reduce_label_rate: 0.0
reduce_continue_winner_rate: 0.0
```

Mismatch count:

```text
mismatch_count: 0
```

## 10. Safety Checks

```text
add_loss_position_count: 0
add_exit_label_overlap_count: 0
exit_continue_winner_count: 0
```

Safety boundary:

```text
training_executed: false
backtest_executed: false
paper_trading_executed: false
broker_api_executed: false
order_executed: false
capital_allocation_executed: false
```

## 11. Forbidden Feature Audit

```text
forbidden_feature_audit_status: OK
feature_audit.forbidden_feature_column_count: 0
feature_audit.future_feature_column_count: 0
label_audit.forbidden_feature_column_count: 0
```

Future labels were not used as inference features.

## 12. Leakage Audit

```text
leakage_audit_status: OK
feature_audit.leakage_audit_status: OK
label_audit.label_leakage_audit_status: OK
```

The dataset keeps `feature__*` and `label__*` separated.

## 13. Verification

```text
python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py tests/position_management_ai/test_phase6b_position_feature_builder.py tests/position_management_ai/test_phase6c_position_label_dataset.py tests/position_management_ai/test_phase6d_baseline_label_alignment.py tests/position_management_ai/test_phase6e_baseline_calibration.py tests/position_management_ai/test_phase6f_realdata_dry_run.py
```

Result:

```text
31 passed
```

## 14. Phase6-G Tasks

- Add a more diverse real-data slice with downside / drawdown regimes.
- Connect historical Opportunity outputs when target dates overlap normalized quote history.
- Replace proxy Opportunity signal with official Phase5 output when available.
- Expand target dates while keeping runtime bounded.
- Confirm ADD behavior on real data where proxy / official Opportunity rank is truly strong.
- Keep ML training, full backtest, Broker API, order placement, Paper Trading, and capital allocation out of scope until explicitly approved.
