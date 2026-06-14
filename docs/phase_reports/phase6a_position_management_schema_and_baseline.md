# Phase6-A Position Management Schema and Baseline

## 1. Summary

Phase6-A fixed the initial Position Management AI responsibility boundary, output schema, forbidden feature audit, leakage audit, and a small explainable rule-based baseline.

Readiness:

```text
READY_FOR_PHASE6_VALIDATION
```

Phase6-A did not perform:

- purchase size decision
- capital allocation
- Broker API access
- order placement
- Paper Trading
- live trading
- model promotion
- reader switch

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase5_final_handoff_for_phase6.md`
- `docs/phase_reports/phase5r_opportunity_ranking_quality_audit.md`
- `docs/phase_reports/phase5n_design_deviation_decision_record.md`
- `docs/phase_reports/phase5k_policy_finalization.md`
- `docs/phase_reports/phase5o2_expanded_random_date_outcome_check.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `scripts/run_phase6a_position_management_dry_run.py`
- `tests/position_management_ai/test_phase6a_position_management_baseline.py`
- `docs/phase_reports/phase6a_position_management_schema_and_baseline.md`

Generated dry-run artifacts:

- `reports/position_management_ai/phase6a/fixture_inputs/holdings.parquet`
- `reports/position_management_ai/phase6a/fixture_inputs/opportunity.parquet`
- `reports/position_management_ai/phase6a/fixture_inputs/features.parquet`
- `reports/position_management_ai/phase6a/position_management_inference.parquet`
- `reports/position_management_ai/phase6a/position_management_actions.csv`
- `reports/position_management_ai/phase6a/position_management_inference_summary.json`
- `reports/position_management_ai/phase6a/position_management_inference_audit.json`

## 4. Responsibility Boundary

Position Management AI only judges how to treat existing holdings:

```text
HOLD
EXIT
ADD
REDUCE
```

`ADD` is not a buy order. It is only an add-candidate signal. Final purchase permission, amount, and position limit checks belong to Phase7 Capital Allocation Engine. Averaging down losing positions is prohibited.

## 5. Input Schema

Holding snapshot:

- `target_date`
- `code`
- `entry_price`
- `current_price`
- `holding_days`
- `position_size`
- `current_return`
- `peak_return`

Opportunity signal:

- `expected_edge_score`
- `buy_rank`
- `downside_risk_score`
- `risk_guard_status`
- `candidate_score`
- `candidate_rank`
- `buy_reason`
- `no_buy_reason`
- `calibration_policy_name`

J-Quants-derived technical features:

- `price_momentum_return_5d`
- `price_momentum_return_20d`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `volatility_return_std_20d`
- `volume_momentum_ratio_5d`

## 6. Output Schema

Phase6-A output schema:

```text
target_date
code
action
hold_score
exit_score
add_score
reduce_score
continue_holding
add_candidate
reduce_candidate
exit_candidate
action_reason
exit_reason
risk_guard_status
feature_version
model_version
created_at
```

## 7. Forbidden Feature Audit

Forbidden inference features:

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

Audit behavior:

- forbidden feature columns are not silently ignored
- forbidden feature columns block readiness with `BLOCKED_BY_LEAKAGE_AUDIT`
- tests cover `future_return_20d` and `portfolio_weight`

Dry-run audit result:

```text
forbidden_feature_column_count: 0
forbidden_input_column_count: 0
future_feature_column_count: 0
label_column_count: 0
```

## 8. Leakage Audit

Dry-run audit result:

```text
leakage_audit_status: OK
as_of_date_violation_count: 0
join_success_rate: 1.0
```

Safety boundary flags:

```text
broker_api_executed: false
order_executed: false
paper_trading_executed: false
capital_allocation_executed: false
promotion_performed: false
reader_switch_performed: false
```

## 9. Rule-Based Baseline

Phase6-A uses an explainable rule-based baseline. No AI model training is performed.

HOLD:

- trend continues
- `close_over_ma_20d` is above moving average
- `ma_5_20_ratio` is above 1
- drawdown from peak is small

EXIT:

- trend breaks
- `ma_5_20_ratio < 1`
- `close_over_ma_20d < 1`
- drawdown from peak worsens
- `risk_guard_status` is bad

ADD:

- unrealized return is positive
- trend is strong
- `expected_edge_score` is high
- `buy_rank` remains high
- `downside_risk_score` is low
- losing positions are never ADD candidates

REDUCE:

- trend has not fully broken
- volatility, drawdown from peak, or downside risk has worsened

## 10. Small Dry-Run Result

Command:

```text
python3 scripts/run_phase6a_position_management_dry_run.py --use-fixture
```

Dry-run input:

```text
4 holding rows
4 opportunity rows
4 feature rows
```

Dry-run output:

| action | count |
| --- | ---: |
| HOLD | 1 |
| EXIT | 1 |
| ADD | 1 |
| REDUCE | 1 |

Dry-run examples:

| code | action | reason |
| --- | --- | --- |
| `1001` | ADD | `strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging` |
| `1002` | EXIT | `hard_stop_current_return|profit_retention_break|trend_and_opportunity_broken|risk_guard_status_bad` |
| `1003` | REDUCE | `peak_drawdown_warning` |
| `1004` | HOLD | `trend_continuation|positive_expected_edge|downside_risk_contained` |

## 11. Verification

```text
python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py
```

Result:

```text
4 passed
```

## 12. Next Phase6-B

Recommended Phase6-B work:

- define historical position snapshot generation for validation only
- design profit_retention metrics
- evaluate rule thresholds on a small historical sample
- separate REDUCE vs EXIT calibration more carefully
- connect real latest holdings only as read-only input
- keep Broker API, order placement, Paper Trading, and capital allocation out of scope
