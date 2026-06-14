# Phase6-E Baseline Rule Calibration

## 1. Summary

Phase6-E calibrates the Phase6-A/B rule-based baseline using the Phase6-D baseline-vs-label alignment audit. No ML training was performed.

Readiness:

```text
READY_FOR_PHASE6F_POLICY_REVIEW
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

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/calibration.py`
- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `scripts/run_phase6e_baseline_calibration.py`
- `tests/position_management_ai/test_phase6e_baseline_calibration.py`
- `docs/phase_reports/phase6e_baseline_rule_calibration.md`

Generated outputs:

- `reports/position_management_ai/phase6e_calibrated_baseline_alignment.csv`
- `reports/position_management_ai/phase6e_calibrated_baseline_alignment.json`
- `reports/position_management_ai/phase6e_calibrated_baseline_mismatches.csv`
- `reports/position_management_ai/phase6e_calibrated_baseline_audit.json`
- `reports/position_management_ai/phase6e_old_vs_calibrated_comparison.json`

## 4. Phase6-D Issues

Phase6-D showed:

- safety was good
- no ADD on losing positions
- no ADD on `label_exit_before_drawdown=true`
- no EXIT on `label_continue_winner=true`
- no REDUCE on `label_continue_winner=true`
- mismatch count was high: `12 / 17`
- HOLD did not capture `label_continue_winner=true`
- ADD was safe but too broad relative to strict `label_add_candidate`
- REDUCE alignment was partial

## 5. Calibration Changes

ADD was narrowed:

- requires `unrealized_return > 0`
- requires strong Opportunity signal
- requires `buy_rank <= 5`
- requires low downside risk
- requires risk guard not bad
- avoids mature winner chasing by limiting the early-winner zone

HOLD was adjusted:

- allows strong winners to stay HOLD after early ADD window
- permits soft trend tolerance around moving averages
- keeps risk guard bad out of winner HOLD

EXIT was made stricter:

- risk guard bad alone is not enough
- requires loss plus trend/risk confirmation
- keeps `label_continue_winner=true` out of EXIT

REDUCE was refocused:

- keeps EXIT as the stronger action
- catches profit positions with downside risk deterioration
- catches future-drawdown-like risk as softer risk handling
- avoids reducing `label_continue_winner=true`

## 6. Old Baseline Result

Action distribution:

| action | count |
| --- | ---: |
| ADD | 3 |
| EXIT | 4 |
| HOLD | 5 |
| REDUCE | 5 |

Alignment metrics:

| metric | value |
| --- | ---: |
| `hold_continue_winner_rate` | 0.000000 |
| `hold_exit_label_rate` | 0.000000 |
| `exit_exit_label_rate` | 0.500000 |
| `exit_continue_winner_rate` | 0.000000 |
| `add_add_label_rate` | 0.333333 |
| `add_exit_label_rate` | 0.000000 |
| `reduce_reduce_label_rate` | 0.400000 |
| `reduce_continue_winner_rate` | 0.000000 |

Mismatch:

```text
old_mismatch_count: 12
```

## 7. Calibrated Baseline Result

Action distribution:

| action | count |
| --- | ---: |
| ADD | 1 |
| EXIT | 3 |
| HOLD | 7 |
| REDUCE | 6 |

Alignment metrics:

| metric | value |
| --- | ---: |
| `hold_continue_winner_rate` | 0.142857 |
| `hold_exit_label_rate` | 0.000000 |
| `exit_exit_label_rate` | 0.666667 |
| `exit_continue_winner_rate` | 0.000000 |
| `add_add_label_rate` | 1.000000 |
| `add_exit_label_rate` | 0.000000 |
| `reduce_reduce_label_rate` | 0.500000 |
| `reduce_continue_winner_rate` | 0.000000 |

Mismatch:

```text
calibrated_mismatch_count: 10
mismatch_delta: -2
```

## 8. Alignment Comparison

| metric | old | calibrated |
| --- | ---: | ---: |
| mismatch_count | 12 | 10 |
| hold_continue_winner_rate | 0.000000 | 0.142857 |
| hold_exit_label_rate | 0.000000 | 0.000000 |
| exit_exit_label_rate | 0.500000 | 0.666667 |
| exit_continue_winner_rate | 0.000000 | 0.000000 |
| add_add_label_rate | 0.333333 | 1.000000 |
| add_exit_label_rate | 0.000000 | 0.000000 |
| reduce_reduce_label_rate | 0.400000 | 0.500000 |
| reduce_continue_winner_rate | 0.000000 | 0.000000 |

## 9. Continue Winner Capture

Both old and calibrated baselines keep all `label_continue_winner=true` rows in HOLD or ADD:

```text
continue_winner_hold_or_add_old_count: 2
continue_winner_hold_or_add_calibrated_count: 2
```

The calibrated baseline improves HOLD capture:

```text
hold_continue_winner_rate: 0.000000 -> 0.142857
```

No `label_continue_winner=true` rows are sent to EXIT or REDUCE.

## 10. Exit Before Drawdown Capture

Rows with `label_exit_before_drawdown=true` remain routed to EXIT or REDUCE:

```text
exit_before_drawdown_exit_or_reduce_old_count: 4
exit_before_drawdown_exit_or_reduce_calibrated_count: 4
```

EXIT precision improved:

```text
exit_exit_label_rate: 0.500000 -> 0.666667
```

## 11. ADD Safety Check

ADD safety remained intact:

```text
calibrated_add_loss_position_count: 0
calibrated_add_exit_label_overlap_count: 0
```

ADD was narrowed from 3 rows to 1 row and now matches `label_add_candidate=true`:

```text
add_add_label_rate: 0.333333 -> 1.000000
```

## 12. Forbidden Feature Audit

Forbidden feature audit:

```text
forbidden_feature_audit_status: OK
feature_audit.forbidden_feature_column_count: 0
label_audit.forbidden_feature_column_count: 0
```

Future labels were not used as inference features.

## 13. Leakage Audit

Leakage audit:

```text
leakage_audit_status: OK
feature_audit.leakage_audit_status: OK
label_audit.label_leakage_audit_status: OK
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

## 14. Verification

```text
python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py tests/position_management_ai/test_phase6b_position_feature_builder.py tests/position_management_ai/test_phase6c_position_label_dataset.py tests/position_management_ai/test_phase6d_baseline_label_alignment.py tests/position_management_ai/test_phase6e_baseline_calibration.py
```

Result:

```text
26 passed
```

## 15. Phase6-F Tasks

- Review whether calibrated HOLD is still too broad for neutral rows.
- Decide whether neutral no-label rows should be a fifth internal audit state, while keeping external action schema unchanged.
- Revisit EXIT false positives caused by current damage but no future drawdown label.
- Separate current stop labels from future drawdown labels.
- Validate calibrated thresholds on a broader but still bounded historical sample.
- Keep ML training blocked until label and rule policy are accepted.
