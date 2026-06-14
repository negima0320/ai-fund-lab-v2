# Phase6-B Position Feature Builder

## 1. Summary

Phase6-B extends Phase6-A from a 4-row baseline fixture to a small historical position fixture and position feature builder. It joins position-derived features with Opportunity AI-style signals, runs the Phase6-A rule-based baseline, and keeps forbidden feature / leakage audit active.

Readiness:

```text
READY_FOR_PHASE6C_VALIDATION_DESIGN
```

Not executed:

- full backtest
- Broker API
- order placement
- Paper Trading
- capital allocation
- model training

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase5_final_handoff_for_phase6.md`
- `docs/phase_reports/phase6a_position_management_schema_and_baseline.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/feature_builder.py`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `scripts/run_phase6b_position_feature_dry_run.py`
- `tests/position_management_ai/test_phase6b_position_feature_builder.py`
- `docs/phase_reports/phase6b_position_feature_builder.md`

Generated dry-run outputs:

- `reports/position_management_ai/phase6b_position_feature_dry_run.csv`
- `reports/position_management_ai/phase6b_position_feature_dry_run.json`

## 4. Feature Builder Spec

The Phase6-B feature builder creates one row per historical position snapshot.

Position fields:

- `target_date`
- `entry_date`
- `code`
- `entry_price`
- `current_price`
- `holding_days`
- `position_size`
- `unrealized_return`
- `current_return`
- `peak_return`
- `drawdown_from_peak`

Technical features:

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

Opportunity features:

- `expected_edge_score`
- `buy_rank`
- `downside_risk_score`
- `risk_guard_status`

The builder can accept normalized daily quotes and Opportunity-like output. For the Phase6-B dry-run, it uses a small deterministic historical fixture because the local normalized quote artifacts and latest Opportunity output do not cover the same target dates.

## 5. Used Data

Local data checked:

- `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet`
- `.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet`
- `reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet`
- `reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet`

Dry-run data used:

- 6 synthetic quote histories
- 6 historical position scenarios
- 6 Opportunity-style signal rows

The fixture includes:

- multiple symbols
- multiple `entry_date`
- multiple `holding_days`
- unrealized profit
- unrealized loss
- pullback from peak
- trend continuation
- trend breakdown
- strong and weak Opportunity ranks

## 6. Dry-Run Result

Command:

```text
python3 scripts/run_phase6b_position_feature_dry_run.py
```

Rows:

```text
dry_run_row_count: 6
missing_required_features: []
```

Action distribution:

| action | count |
| --- | ---: |
| HOLD | 2 |
| EXIT | 1 |
| ADD | 1 |
| REDUCE | 2 |

Example rows:

| code | unrealized_return | peak_return | drawdown_from_peak | buy_rank | action |
| --- | ---: | ---: | ---: | ---: | --- |
| `2001` | 0.104950 | 0.121525 | -0.016574 | 2 | ADD |
| `2002` | -0.123657 | 0.015000 | -0.138657 | 42 | EXIT |
| `2003` | -0.000518 | 0.103805 | -0.104322 | 7 | REDUCE |
| `2004` | 0.015102 | 0.030328 | -0.015227 | 14 | HOLD |
| `2005` | -0.014895 | 0.015000 | -0.029895 | 31 | REDUCE |
| `2006` | 0.019302 | 0.062732 | -0.043430 | 9 | HOLD |

## 7. ADD Loss Check

ADD is only an add-candidate signal, not a buy order. It must not be emitted for losing positions.

Dry-run result:

```text
add_candidate_count: 1
add_loss_position_count: 0
```

## 8. Forbidden Feature Audit

Forbidden inference features remain blocked:

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

Dry-run audit:

```text
forbidden_feature_column_count: 0
forbidden_input_column_count: 0
future_feature_column_count: 0
label_column_count: 0
```

Tests additionally verify that `feature__future_return_20d` blocks readiness with `BLOCKED_BY_LEAKAGE_AUDIT`.

## 9. Leakage Audit

Dry-run audit:

```text
leakage_audit_status: OK
as_of_date_violation_count: 0
join_success_rate: 1.0
```

Safety boundary:

```text
broker_api_executed: false
order_executed: false
paper_trading_executed: false
capital_allocation_executed: false
```

## 10. Verification

```text
python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py tests/position_management_ai/test_phase6b_position_feature_builder.py
```

Result:

```text
9 passed
```

## 11. Phase6-C Tasks

- Connect a real read-only holding snapshot source when available.
- Build a small historical validation design for profit retention without full backtesting.
- Calibrate thresholds for EXIT vs REDUCE using a bounded sample.
- Add Opportunity rank change features once historical Opportunity outputs are available.
- Improve `volume_ratio_20d` baseline once longer volume baseline windows are connected.
- Keep Broker API, order placement, Paper Trading, and capital allocation out of scope until later phases.
