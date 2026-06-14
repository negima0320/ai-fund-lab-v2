# Phase6-C Position Label Dataset Audit

## 1. Summary

Phase6-C adds a small historical position dataset builder and candidate label design audit for Position Management AI. No AI model training was performed.

Readiness:

```text
READY_FOR_PHASE6D_LABEL_VALIDATION
```

Not executed:

- model training
- full backtest
- Broker API
- order placement
- Paper Trading
- capital allocation

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase5_final_handoff_for_phase6.md`
- `docs/phase_reports/phase6a_position_management_schema_and_baseline.md`
- `docs/phase_reports/phase6b_position_feature_builder.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/label_dataset.py`
- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `scripts/run_phase6c_position_label_dataset_dry_run.py`
- `tests/position_management_ai/test_phase6c_position_label_dataset.py`
- `docs/phase_reports/phase6c_position_label_dataset_audit.md`

Generated outputs:

- `reports/position_management_ai/phase6c_position_label_dataset.csv`
- `reports/position_management_ai/phase6c_position_label_dataset.json`
- `reports/position_management_ai/phase6c_position_label_audit.json`

## 4. Dataset Builder Spec

The Phase6-C builder creates a label dataset from:

- historical position snapshots
- J-Quants-style daily quote history
- Opportunity-style ranking signals

Dataset columns are separated into:

- metadata columns
- `feature__*` inference feature candidates
- `label__*` future label candidates

Feature columns:

```text
feature__entry_price
feature__current_price
feature__holding_days
feature__unrealized_return
feature__peak_return
feature__drawdown_from_peak
feature__return_1d
feature__return_5d
feature__return_20d
feature__volume_ratio_5d
feature__volume_ratio_20d
feature__close_over_ma_5d
feature__close_over_ma_20d
feature__ma_5_20_ratio
feature__ma_20_60_ratio
feature__volatility_20d
feature__trend_strength_score
feature__expected_edge_score
feature__buy_rank
feature__downside_risk_score
feature__risk_guard_status
```

## 5. Label Definition

Future outcome labels are created only as `label__*` columns.

Raw future labels:

```text
label__future_return_5bd
label__future_return_10bd
label__future_return_20bd
label__future_max_return_20bd
label__future_min_return_20bd
label__future_drawdown_20bd
label__future_profit_retention_20bd
```

Candidate decision labels:

```text
label__label_continue_winner
label__label_exit_before_drawdown
label__label_add_candidate
label__label_reduce_candidate
```

Temporary definitions:

- `label_continue_winner`
  - current unrealized return is positive
  - future max return over 20 business days is positive enough
  - future drawdown is not deep
- `label_exit_before_drawdown`
  - future min return is below `-0.05`
  - or future drawdown is below `-0.08`
- `label_add_candidate`
  - current unrealized return is positive
  - expected edge is high
  - buy rank is top 5
  - future max return is strong
  - future drawdown is not severe
- `label_reduce_candidate`
  - current unrealized return is positive
  - future upside is small
  - future drawdown is meaningfully negative

These definitions are label design candidates only. They are not final trading rules.

## 6. Dry-Run Scope

Command:

```text
python3 scripts/run_phase6c_position_label_dataset_dry_run.py
```

Dry-run data:

- 6 synthetic quote histories
- 6 symbols
- 3 target dates
- 17 dataset rows

Target dates:

```text
2026-05-22
2026-05-29
2026-06-05
```

Rows by target date:

| target_date | rows |
| --- | ---: |
| 2026-05-22 | 5 |
| 2026-05-29 | 6 |
| 2026-06-05 | 6 |

The expected maximum was 18 rows, but one `2026-05-22` scenario was excluded because its entry date was after the target date.

## 7. Label Distribution

| label | true | false |
| --- | ---: | ---: |
| `label__label_continue_winner` | 2 | 15 |
| `label__label_exit_before_drawdown` | 4 | 13 |
| `label__label_add_candidate` | 1 | 16 |
| `label__label_reduce_candidate` | 3 | 14 |

## 8. Forbidden Feature Audit

Forbidden inference feature audit result:

```text
forbidden_feature_audit_status: OK
forbidden_feature_column_count: 0
future_feature_column_count: 0
```

Confirmed forbidden values are not feature columns:

- `future_return_*`
- `future_max_return_*`
- `future_max_drawdown_*`
- `top_decile_*`
- `downside_bad_*`
- `trade_result`
- `future_profit`
- `future_sell_price`
- `future_best_price`
- `sold`
- `bought`
- `cash`
- `portfolio`
- `final_assets`

## 9. Label Leakage Audit

Label leakage audit result:

```text
label_leakage_audit_status: OK
feature_label_columns_separated: true
unprefixed_label_column_count: 0
label_column_count: 11
feature_column_count: 21
```

The dataset keeps inference features under `feature__*` and future labels under `label__*`.

## 10. Verification

```text
python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py tests/position_management_ai/test_phase6b_position_feature_builder.py tests/position_management_ai/test_phase6c_position_label_dataset.py
```

Result:

```text
14 passed
```

## 11. Phase6-D Tasks

- Review whether label definitions match the actual Position Management philosophy.
- Calibrate label thresholds on a slightly broader but still bounded sample.
- Add rank-change features and labels once historical Opportunity outputs are available.
- Decide whether `future_profit_retention_20bd` should be a regression label, an audit metric, or both.
- Validate conflict cases where multiple labels are true.
- Keep future labels out of inference features.
- Continue to avoid Broker API, order placement, Paper Trading, capital allocation, and full backtesting.
