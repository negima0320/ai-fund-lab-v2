# Phase6 Position Management Completion Audit

## 1. Summary

Phase6-G performed the final completion audit for Position Management AI vNext across Phase6-A through Phase6-F.

Completion decision:

```text
PHASE6_COMPLETE_WITH_DOCUMENTED_LIMITATIONS
```

This means Phase6 is complete enough to hand off to Phase7 Capital Allocation Engine, with the limitations below explicitly documented.

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase6a_position_management_schema_and_baseline.md`
- `docs/phase_reports/phase6b_position_feature_builder.md`
- `docs/phase_reports/phase6c_position_label_dataset_audit.md`
- `docs/phase_reports/phase6d_baseline_label_alignment_audit.md`
- `docs/phase_reports/phase6e_baseline_rule_calibration.md`
- `docs/phase_reports/phase6f_realdata_position_dry_run.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/calibration.py`
- `scripts/audit_phase6_position_management_completion.py`
- `tests/position_management_ai/test_phase6_completion_audit.py`
- `docs/phase_reports/phase6_position_management_completion_audit.md`

Generated output:

- `reports/position_management_ai/phase6_completion_audit.json`

## 4. Responsibility Boundary Audit

Phase6 remained inside the intended responsibility boundary.

Not executed:

- ML training
- full backtest
- Broker API
- order placement
- Paper Trading
- capital allocation
- Capital Allocation

Audit result:

```text
responsibility_boundary_audit: OK
```

Position Management AI only decides how to treat existing positions:

```text
HOLD
EXIT
ADD
REDUCE
```

## 5. Output Schema Audit

The calibrated Position Management output now satisfies the Phase6-A / Phase7 handoff schema:

```text
code
target_date
action
hold_score
exit_score
add_score
reduce_score
continue_holding
exit_candidate
add_candidate
reduce_candidate
action_reason
exit_reason
risk_guard_status
feature_version
model_version
created_at
```

Audit result:

```text
output_schema_audit: OK
missing_required_columns: []
```

`calibration.py` was updated so the calibrated baseline output includes `risk_guard_status` and `feature_version` in addition to the action and score fields.

## 6. Feature Safety Audit

Forbidden inference features were not found in the Phase6-F feature dataset.

Forbidden patterns checked include:

- `future_return_*`
- `future_max_return_*`
- `future_max_drawdown_*`
- `future_min_return_*`
- `future_profit*`
- `future_sell_price`
- `future_best_price`
- `top_decile_*`
- `downside_bad_*`
- `trade_result`
- `sold`
- `bought`
- `cash`
- `portfolio`
- `final_assets`

Audit result:

```text
feature_safety_audit: OK
forbidden_feature_column_count: 0
```

## 7. Label Separation Audit

Future outcome columns exist only as `label__*` columns.

Feature / label separation:

```text
feature_column_count: 21
label_column_count: 11
future_feature_column_count: 0
unprefixed_label_column_count: 0
label_separation_audit: OK
```

This confirms future labels are evaluation / label candidates only and are not mixed into inference features.

## 8. ADD Safety Audit

ADD remains a candidate signal only. It is not a buy order and does not decide final purchase permission, purchase amount, or position limits.

Safety result:

```text
add_loss_position_count_total: 0
add_exit_label_overlap_count_total: 0
add_safety_audit: OK
```

Phase7 must decide whether an ADD candidate can actually receive capital.

## 9. HOLD / EXIT / REDUCE Safety Audit

Safety result:

```text
continue_winner_exit_count_total: 0
continue_winner_reduce_count_total: 0
phase6e_hold_exit_label_rate: 0.0
phase6f_hold_exit_label_rate: 0.0
hold_exit_safety_audit: OK
```

Phase6-E improved rule calibration while preserving safety:

- no `label_continue_winner=true` rows were sent to EXIT
- no `label_continue_winner=true` rows were sent to REDUCE
- ADD did not overlap with `label_exit_before_drawdown=true`
- ADD did not fire on losing positions

## 10. Phase6-F Limitations

Phase6-F validated the real-data plumbing, but it is not enough to evaluate action diversity.

Important limitations:

- Phase5 formal Opportunity output was not used
- `proxy_from_normalized_quotes` was used
- row count was 36
- code count was 12
- target date count was 3
- action distribution was all HOLD
- `label_continue_winner` was all true

Phase6-F result:

```text
row_count: 36
code_count: 12
target_date_count: 3
action_distribution: {"HOLD": 36}
label_continue_winner: true 36 / false 0
```

Interpretation:

Phase6-F is acceptable as a small real-data connection check. It proves normalized quote input, feature generation, label dataset generation, calibrated inference, action-label alignment, forbidden feature audit, and leakage audit can run together. It does not prove robust behavior across downside / drawdown / rank-deterioration regimes.

## 11. Phase7 Handoff

Phase7 Capital Allocation Engine should consume:

- `action`
- `hold_score`
- `exit_score`
- `add_score`
- `reduce_score`
- `risk_guard_status`
- `feature_version`
- `model_version`
- `created_at`

Action semantics:

| action | handoff meaning |
| --- | --- |
| HOLD | Hold-continuation candidate. |
| EXIT | Exit candidate. Final order is handled in Broker / Paper phase. |
| ADD | Add candidate signal only. Final purchase permission, amount, and holding cap checks belong to Phase7. |
| REDUCE | Reduce candidate. Actual sell quantity belongs to Phase7 or later execution phases. |

## 12. Completion Audit Output

Command:

```text
python3 scripts/audit_phase6_position_management_completion.py
```

Result:

```text
completion_status: PHASE6_COMPLETE_WITH_DOCUMENTED_LIMITATIONS
ready_for_phase7: true
```

Output:

```text
reports/position_management_ai/phase6_completion_audit.json
```

## 13. Verification

Lightweight pytest:

```text
python3 -m pytest \
  tests/position_management_ai/test_phase6a_position_management_baseline.py \
  tests/position_management_ai/test_phase6b_position_feature_builder.py \
  tests/position_management_ai/test_phase6c_position_label_dataset.py \
  tests/position_management_ai/test_phase6d_baseline_label_alignment.py \
  tests/position_management_ai/test_phase6e_baseline_calibration.py \
  tests/position_management_ai/test_phase6f_realdata_dry_run.py \
  tests/position_management_ai/test_phase6_completion_audit.py
```

Result:

```text
38 passed
```

## 14. Phase7 Tasks

- Treat ADD as a candidate signal, not an execution command.
- Use action score fields for capital allocation ranking / gating.
- Decide final purchase amount, reduce amount, and position limits in Phase7.
- Keep Broker API, actual orders, and Paper Trading outside Phase7 unless a later phase explicitly enables them.
- Replace Phase6-F proxy opportunity signals with official Phase5 Opportunity outputs once date coverage overlaps.
- Broaden real-data samples to include downside, drawdown, rank deterioration, and volatile regimes before using Position Management output in trading simulation.
