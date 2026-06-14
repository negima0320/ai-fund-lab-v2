# Phase5-M Design Compliance Review

## 1. Purpose

Phase5-M reviews whether Phase5 Opportunity AI was implemented according to the original Opportunity AI design.

This review does not reopen Phase5. It documents compliance and known gaps before moving to Phase6.

## 2. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/design_compliance.py`
- `scripts/audit_phase5m_design_compliance.py`
- `tests/opportunity_ai/test_phase5m_design_compliance.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

Generated artifacts:

- `reports/opportunity_ai/phase5m/design_compliance_review.json`
- `reports/opportunity_ai/phase5m/design_compliance_feature_coverage.csv`
- `reports/opportunity_ai/phase5m/design_compliance_audit.json`

## 3. Judgment

Readiness:

- `PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS`

Promotion:

- `promotion_ready=false`

Conclusion:

- Phase5 is design-compliant as an Opportunity AI ranking phase.
- Known feature coverage gaps exist and are documented.
- The known gaps are future improvement items, not Phase5 completion blockers.
- Phase6 can proceed with these gaps visible.

## 4. Role Compliance

Confirmed:

- Opportunity AI is implemented as a Candidate Top50 expected-value ranking AI.
- The main horizon is 20 business days.
- Candidate AI candidate extraction responsibility is not invaded.
- Position Management responsibility is not invaded.
- Capital Allocation responsibility is not invaded.
- Broker / Order responsibility is not invaded.
- Phase5 does not decide the actual number of stocks to buy.

Role compliance:

- `role_compliant=true`

## 5. Actual Training Features

Actual `feature__*` columns used in the full-history Opportunity model:

```text
feature__candidate_rank
feature__candidate_reason
feature__candidate_score
feature__liquidity_avg_volume_20d
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
feature__price_momentum_return_20d
feature__price_momentum_return_5d
feature__price_momentum_return_60d
feature__trend_close_over_ma_20d
feature__trend_ma_20_60_ratio
feature__trend_ma_5_20_ratio
feature__volatility_return_std_20d
feature__volume_momentum_ratio_1d_20d
feature__volume_momentum_ratio_5d
```

Feature count:

- actual feature columns: 16

## 6. Category Coverage

| Category | Designed | Used design features | Actual feature columns | Unused |
| --- | ---: | ---: | ---: | ---: |
| Candidate AI output | 3 | 3 | 3 | 0 |
| Data quality | 3 | 3 | 3 | 0 |
| Fundamental | 7 | 0 | 0 | 7 |
| Liquidity | 2 | 1 | 1 | 1 |
| Market data | 4 | 0 | 0 | 4 |
| Market environment | 2 | 0 | 0 | 2 |
| Sector strength | 1 | 0 | 0 | 1 |
| Technical: price momentum | 3 | 3 | 3 | 0 |
| Technical: trend | 3 | 3 | 3 | 0 |
| Technical: volatility | 3 | 1 | 1 | 2 |
| Technical: volume momentum | 2 | 2 | 2 | 0 |

Interpretation:

- Candidate, momentum, volume momentum, trend, volatility, and liquidity were implemented.
- Data quality flags were included as additional implemented features.
- Raw OHLCV direct features were not used directly; derived momentum/trend/liquidity features were used instead.
- Fundamental, market environment, and sector strength features remain known gaps.

## 7. Designed But Unused Features

Unused designed features:

- close
- high
- low
- volume
- return_std_60d
- high_low_range
- avg_trading_value_20d
- sales_growth_rate
- operating_profit_growth_rate
- ordinary_profit_growth_rate
- net_income_growth_rate
- roe
- equity_ratio
- operating_margin
- TOPIX
- market_trend
- sector_strength

Unused count:

- 17

Reason categories:

- Phase5-C candidate but not connected in implementation
- raw OHLCV represented indirectly through derived features
- J-Quants fins/as_of_date join not connected
- J-Quants index / market environment join not connected
- sector strength join not connected

Completion impact:

- `known_gap_future_improvement`

These are not compliance blockers because Phase5-C allowed feature expansion candidates, and Phase5 completed with leakage-free J-Quants-derived features. They should be considered Phase6 or future Opportunity AI improvement items.

## 8. J-Quants Source-of-Truth Compliance

Result:

- source_of_truth_compliant: true

Confirmed:

- Training features are J-Quants-derived features plus allowed current Candidate AI outputs.
- Candidate allowed inputs are `candidate_score`, `candidate_rank`, and `candidate_reason`.
- No backtest result, trading result, portfolio result, PM multiplier, Paper Trading output, or previous AI output is used as a feature.

## 9. Forbidden Data Compliance

Result:

- forbidden_feature_compliant: true
- forbidden feature columns: 0
- future feature columns: 0
- trade result feature columns: 0
- portfolio feature columns: 0
- backtest feature columns: 0

Confirmed absent as features:

- `future_return_*`
- `future_max_return_*`
- `future_max_drawdown_*`
- `downside_bad_*`
- `top_decile_*`
- `trade_result`
- `trade_profit`
- `selected`
- `bought`
- `sold`
- `cash`
- `portfolio`
- `annual_return`
- `final_assets`
- backtest result
- PM multiplier
- previous AI output

## 10. Label Compliance

Required 20-business-day labels are present:

- `label__expected_edge_label_20d`
- `label__future_return_20d`
- `label__future_max_return_20d`
- `label__future_max_drawdown_20d`
- `label__downside_bad_20d`
- `label__top_decile_20d`

Result:

- expected_edge_label_20d present: true
- future labels limited to label prefix: true
- horizon 20d compliant: true
- label compliant: true

No 5d or 60d Opportunity model horizon was mixed into the Phase5 training target.

## 11. Output Schema Compliance

Final schema is compliant with Phase5-K.

Required output columns:

```text
target_date
code
expected_edge_score
buy_rank
expected_return_horizon
downside_risk_score
buy_reason
no_buy_reason
candidate_score
candidate_rank
model_version
feature_version
inference_run_id
created_at
is_top5
is_top10
is_top20
risk_guard_status
calibration_policy_name
```

Result:

- missing columns: none
- `risk_guard_status`: present
- `calibration_policy_name`: present
- schema compliant: true

## 12. Full History Compliance

Phase5-I full history expansion was executed.

Metrics:

- target dates: 1,202
- candidate rows: 57,150
- dataset rows: 56,995
- train rows: 40,559
- validation rows: 12,106
- test rows: 4,330
- leakage status: OK
- model unique score count: 15,540
- all same score: false

Result:

- full_history_compliant: true
- monthly_only_completion: false

Phase5 was not completed using monthly samples alone.

## 13. Quality / Calibration Compliance

Confirmed:

- Phase5-G/H/I/J evaluation artifacts exist.
- Phase5-J compared 29 strategies.
- Phase5-K documented 7 policy candidates.
- Top6-10 tail dilution was recorded as `TAIL_DILUTION_CONFIRMED`.
- `simple_rule_top5` is documented as risk-guard-required.
- fixed Top10 was not finalized as a buy-count decision.

Result:

- quality_calibration_compliant: true

## 14. Safety Compliance

Confirmed false:

- Broker API executed
- Paper Trading executed
- order executed
- capital allocation executed
- promotion performed
- reader switch performed
- Phase4 artifact destroyed flag
- mock path overwrite flag

Result:

- safety_compliant: true

## 15. Known Gaps For Phase6

Known gaps:

- Fundamental features are designed but not connected.
- TOPIX / market trend features are designed but not connected.
- Sector strength features are designed but not connected.
- Trading value and high-low range features are designed but not connected.
- Raw OHLCV columns are not directly present, though derived price/volume/trend/liquidity features are used.

Recommended Phase6 or future improvement direction:

- connect J-Quants fins with strict `disclosure_date <= as_of_date`
- add TOPIX / market trend features with no future regime leakage
- add sector strength from J-Quants-listed issue master and quote-derived sector aggregation
- evaluate whether raw OHLCV-derived range/trading-value features improve Top5/Top10 stability
- keep all future columns label/evaluation-only

## 16. Final Conclusion

Phase5-M judgment:

- `PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS`

Phase5 Opportunity AI was implemented according to its core design:

- Candidate Top50 ranking
- 20-business-day expected edge target
- leakage-free feature/label separation
- final output schema fixed
- full-history validation completed
- calibration policy documented
- safety boundaries preserved

Phase6 can proceed with the known feature coverage gaps documented.
