# Phase6-D Baseline Label Alignment Audit

## 1. Summary

Phase6-D audits how well the Phase6-A/B rule-based baseline aligns with the Phase6-C candidate labels. No ML training, full backtest, Broker API, order placement, Paper Trading, or capital allocation was executed.

Readiness:

```text
READY_FOR_PHASE6E_BASELINE_REVIEW
```

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase6a_position_management_schema_and_baseline.md`
- `docs/phase_reports/phase6b_position_feature_builder.md`
- `docs/phase_reports/phase6c_position_label_dataset_audit.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/alignment_audit.py`
- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `scripts/run_phase6d_baseline_label_alignment_audit.py`
- `tests/position_management_ai/test_phase6d_baseline_label_alignment.py`
- `docs/phase_reports/phase6d_baseline_label_alignment_audit.md`

Generated outputs:

- `reports/position_management_ai/phase6d_baseline_label_alignment.csv`
- `reports/position_management_ai/phase6d_baseline_label_alignment.json`
- `reports/position_management_ai/phase6d_baseline_label_mismatches.csv`
- `reports/position_management_ai/phase6d_baseline_label_audit.json`

## 4. Used Dataset

Input dataset:

```text
reports/position_management_ai/phase6c_position_label_dataset.csv
```

Rows:

```text
row_count: 17
```

The audit re-applies the Phase6-A/B baseline to the Phase6-C label dataset by converting `feature__*` columns back to the baseline inference frame. Future `label__*` columns are used only for alignment evaluation.

## 5. Action Distribution

| action | count |
| --- | ---: |
| ADD | 3 |
| EXIT | 4 |
| HOLD | 5 |
| REDUCE | 5 |

## 6. Label Distribution

| label | true | false |
| --- | ---: | ---: |
| `label__label_continue_winner` | 2 | 15 |
| `label__label_exit_before_drawdown` | 4 | 13 |
| `label__label_add_candidate` | 1 | 16 |
| `label__label_reduce_candidate` | 3 | 14 |

## 7. Action x Label Alignment

| action | rows | continue_winner true rate | exit_before_drawdown true rate | add_candidate true rate | reduce_candidate true rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| ADD | 3 | 0.666667 | 0.000000 | 0.333333 | 0.000000 |
| EXIT | 4 | 0.000000 | 0.500000 | 0.000000 | 0.000000 |
| HOLD | 5 | 0.000000 | 0.000000 | 0.000000 | 0.200000 |
| REDUCE | 5 | 0.000000 | 0.400000 | 0.000000 | 0.400000 |

## 8. Mismatch Summary

Total mismatch rows:

```text
mismatch_count: 12
```

Mismatch reasons:

| mismatch_reason | count |
| --- | ---: |
| `hold_without_continue_winner` | 5 |
| `reduce_without_reduce_label` | 3 |
| `exit_without_exit_label` | 2 |
| `add_without_add_label` | 2 |

## 9. HOLD Audit

HOLD rows:

```text
count: 5
label_continue_winner true rate: 0.000000
label_exit_before_drawdown true rate: 0.000000
```

Interpretation:

- HOLD did not hold any rows labeled future drawdown danger.
- HOLD also did not capture `label_continue_winner=true` rows.
- This suggests the current HOLD baseline may be too permissive for neutral positions but not specifically tuned to continuing winners.

HOLD false-positive proxy:

```text
hold_without_continue_winner: 5
```

HOLD false-negative proxy:

```text
continue_winner rows not action=HOLD: 2
```

## 10. EXIT Audit

EXIT rows:

```text
count: 4
label_exit_before_drawdown true rate: 0.500000
label_continue_winner true rate: 0.000000
```

Interpretation:

- EXIT did not mistakenly exit any `label_continue_winner=true` rows.
- Only half of EXIT rows matched `label_exit_before_drawdown=true`.
- Some EXIT decisions are driven by current loss / current risk, while the label is future drawdown-oriented.

EXIT false-positive proxy:

```text
exit_without_exit_label: 2
```

EXIT false-negative proxy:

```text
exit_before_drawdown rows not action=EXIT: 2
```

## 11. ADD Safety Check

ADD rows:

```text
count: 3
label_add_candidate true rate: 0.333333
label_exit_before_drawdown true rate: 0.000000
add_loss_position_count: 0
```

Interpretation:

- ADD never fired on a losing position.
- ADD never overlapped with `label_exit_before_drawdown=true`.
- ADD often captured `label_continue_winner=true`, but the stricter `label_add_candidate` only matched one row.

Safety result:

```text
PASS
```

## 12. REDUCE Safety Check

REDUCE rows:

```text
count: 5
label_reduce_candidate true rate: 0.400000
label_continue_winner true rate: 0.000000
```

Interpretation:

- REDUCE did not over-reduce any `label_continue_winner=true` rows.
- REDUCE also captured some `label_exit_before_drawdown=true` rows, suggesting it may be acting as a softer EXIT in risk cases.
- REDUCE label alignment is partial and needs threshold review.

REDUCE false-positive proxy:

```text
reduce_without_reduce_label: 3
```

## 13. Forbidden Feature Audit

Forbidden feature audit:

```text
forbidden_feature_audit_status: OK
label_audit.forbidden_feature_column_count: 0
feature_audit.forbidden_feature_column_count: 0
feature_audit.future_feature_column_count: 0
```

The baseline inference frame did not consume future labels as features.

## 14. Leakage Audit

Leakage audit:

```text
leakage_audit_status: OK
label_audit.label_leakage_audit_status: OK
feature_audit.leakage_audit_status: OK
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

## 15. Verification

```text
python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py tests/position_management_ai/test_phase6b_position_feature_builder.py tests/position_management_ai/test_phase6c_position_label_dataset.py tests/position_management_ai/test_phase6d_baseline_label_alignment.py
```

Result:

```text
20 passed
```

## 16. Phase6-E Tasks

- Review whether `label_continue_winner` is too strict for HOLD or whether HOLD baseline is too broad.
- Revisit ADD threshold: current ADD is safe, but stricter label alignment is low.
- Split EXIT into current-damage stop and future-drawdown label alignment; these may need separate labels.
- Decide whether REDUCE should absorb future drawdown warnings or remain profit-retention-only.
- Add rank deterioration features once historical Opportunity output is available.
- Keep ML training blocked until label design is accepted.
