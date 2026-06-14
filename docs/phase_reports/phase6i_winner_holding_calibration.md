# Phase6-I Winner Holding Calibration

## 1. Summary

Phase6-I recalibrated the Phase6-E Position Management baseline to improve winner holding quality after Phase6-H found excessive EXIT / REDUCE on continuing winners.

Completion decision:

```text
PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT
```

The new rule improves winner holding while preserving the core profit-retention / risk-control behavior within acceptable tolerance.

## 2. Read Docs

- `docs/03_ai_design/position_management_ai_design.md`
- `docs/phase_reports/phase6h_position_historical_validation.md`
- `docs/phase_reports/phase6e_baseline_rule_calibration.md`
- `docs/phase_reports/phase6f_realdata_position_dry_run.md`
- `docs/phase_reports/phase6_position_management_completion_audit.md`
- `docs/phase_reports/phase5_final_handoff_for_phase6.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/position_management_ai/winner_holding_calibration.py`
- `src/ai_fund_lab_v2/position_management_ai/historical_validation.py`
- `src/ai_fund_lab_v2/position_management_ai/__init__.py`
- `scripts/run_phase6i_winner_holding_calibration.py`
- `tests/position_management_ai/test_phase6i_winner_holding_calibration.py`
- `docs/phase_reports/phase6i_winner_holding_calibration.md`

Generated outputs:

- `reports/position_management_ai/phase6i_winner_holding_calibration.json`
- `reports/position_management_ai/phase6i_winner_holding_calibration.csv`
- `reports/position_management_ai/phase6i_old_vs_winner_holding_comparison.json`
- `reports/position_management_ai/phase6i_winner_holding_action_statistics.json`
- `reports/position_management_ai/phase6i_winner_holding_mismatch_cases.csv`

## 4. Phase6-H Issue

Phase6-H showed that the Phase6-E calibrated baseline improved risk and profit-retention metrics, but it was too aggressive for winner holding:

```text
continue_winner_capture_rate: 0.021164
continue_winner_wrong_exit_count: 7
continue_winner_over_reduce_count: 178
false_exit_rate: 0.258883
```

Root cause:

- REDUCE fired too often from positive-return positions when downside risk was elevated.
- Some risk-guard cases EXITed mild temporary losses even when future upside remained.
- Winner protection was not evaluated before REDUCE in enough cases.

## 5. Calibration Changes

Added Winner Protection Guard:

- `current_return > 0`
- `expected_edge_score >= 0.035`
- `buy_rank <= 5`
- `risk_guard_status != bad`
- `drawdown_from_peak > -0.09`
- `close_over_ma_20d >= 0.94`
- `ma_5_20_ratio >= 0.94`

Hard EXIT was preserved but tightened:

- risk guard bad now requires a deeper loss or stronger confirmation
- severe trend break still exits
- deep current loss plus trend break still exits

REDUCE was made stricter:

- profit position alone is not enough
- downside risk must be paired with drawdown, trend break plus volatility, or short-term deterioration
- strong top-rank winners are protected from REDUCE unless risk is confirmed

ADD safety was unchanged:

- no ADD on losing positions
- ADD remains a candidate signal, not a buy order
- no capital allocation is performed

## 6. Old vs New Comparison

Validation scope:

```text
year: 2025
target_date_count: 80
top_n_per_date: 5
row_count: 400
code_count: 164
```

Opportunity signal:

```text
Phase5 formal Opportunity model re-scoring
```

Price path:

```text
Phase5 future labels approximated into 5 / 10 / 20bd checkpoints for validation only
```

| metric | old Phase6-E | new Phase6-I | delta |
| --- | ---: | ---: | ---: |
| average_return | 0.081954 | 0.081044 | -0.000910 |
| profit_retention_rate | 0.146715 | 0.138255 | -0.008460 |
| profit_decay_before_exit | 0.089230 | 0.088080 | -0.001150 |
| winner_to_loser_rate | 0.206349 | 0.206349 | 0.000000 |
| continue_winner_capture_rate | 0.021164 | 0.433862 | 0.412698 |
| false_exit_rate | 0.258883 | 0.221453 | -0.037430 |
| exit_before_drawdown_rate | 0.431472 | 0.546713 | 0.115241 |

## 7. Winner Holding Improvement

Continue winner capture improved materially:

```text
0.021164 -> 0.433862
```

Continue winner false EXIT improved:

```text
7 -> 0
```

Continue winner over REDUCE improved:

```text
178 -> 107
```

False exit rate improved:

```text
0.258883 -> 0.221453
```

## 8. Action Distribution

Old checkpoint actions:

| action | count |
| --- | ---: |
| HOLD | 35 |
| EXIT | 156 |
| REDUCE | 238 |
| ADD | 0 |

New checkpoint actions:

| action | count |
| --- | ---: |
| HOLD | 450 |
| EXIT | 79 |
| REDUCE | 210 |
| ADD | 0 |

New terminal actions:

| action | count |
| --- | ---: |
| HOLD | 111 |
| EXIT | 79 |
| REDUCE | 210 |

Interpretation:

The policy shifted meaningfully from immediate risk actions into HOLD, while still preserving REDUCE for confirmed risk cases.

## 9. Improved Metrics

Improved:

- `continue_winner_capture_rate`
- `continue_winner_wrong_exit_count`
- `continue_winner_over_reduce_count`
- `false_exit_rate`
- `exit_before_drawdown_rate`
- `profit_decay_before_exit`

Maintained:

- `winner_to_loser_rate`

Slightly worsened but within tolerance:

- `average_return`: down by `0.000910`
- `profit_retention_rate`: down by `0.008460`

## 10. ADD Safety

```text
add_loss_position_count: 0
add_exit_label_overlap_count: 0
add_safety_status: OK
```

ADD did not fire in this validation run. The rule remains safe and remains only a candidate signal.

## 11. Forbidden / Leakage Audit

```text
forbidden_feature_audit_status: OK
forbidden_feature_column_count: 0
feature_label_separation_status: OK
leakage_audit_status: OK
```

Future labels are used only for validation outcomes. They are not inference features.

Execution boundary:

```text
broker_api_executed: false
order_executed: false
paper_trading_executed: false
capital_allocation_executed: false
full_backtest_executed: false
```

## 12. Phase6 Completion Impact

Phase6-H established:

```text
PHASE6_VALIDATED
```

Phase6-I upgrades the qualitative conclusion:

```text
PHASE6_VALIDATED_WITH_WINNER_HOLDING_IMPROVEMENT
```

This does not mean the policy is final for production trading. It means the Position Management AI is no longer only a loss-suppression AI; it now shows measurable improvement in holding continuing winners while preserving the prior risk-control benefits within tolerance.

## 13. Verification

Command:

```text
python3 -m pytest \
  tests/position_management_ai/test_phase6h_historical_validation.py \
  tests/position_management_ai/test_phase6i_winner_holding_calibration.py
```

Result:

```text
11 passed
```

## 14. Next Tasks

- Re-test Phase6-I on broader date slices beyond 2025.
- Replace label-approximated checkpoints with true normalized daily price paths once available for the full Opportunity universe.
- Tune ADD behavior separately, since ADD did not fire in this validation.
- Keep Broker API, order placement, Paper Trading, Capital Allocation, live order, and real account updates out of scope until explicitly enabled.
