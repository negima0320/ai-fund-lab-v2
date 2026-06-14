# Phase5-K Policy Finalization

## 1. Purpose

Phase5-K finalizes the Phase5 Opportunity AI ranking policy candidates, output schema, risk guard requirements, and Phase5-L handoff.

This phase does not decide how many stocks to actually buy. It also does not perform promotion, reader switch, Paper Trading, Broker API access, order placement, or capital allocation.

## 2. Inputs

Phase5-J artifacts:

- `reports/opportunity_ai/phase5j/calibration_metrics.json`
- `reports/opportunity_ai/phase5j/calibration_audit.json`
- `reports/opportunity_ai/phase5j/calibration_by_strategy.csv`
- `reports/opportunity_ai/phase5j/recommended_policy.json`

Phase5-J status:

- readiness_status: `READY_FOR_PHASE5K_POLICY_FINALIZATION`
- promotion_ready: false
- leakage audit: OK
- strategy count: 29
- Top6-10 tail dilution: `TAIL_DILUTION_CONFIRMED`
- recommended policy candidate: `simple_rule_top5`

## 3. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/policy_finalization.py`
- `scripts/finalize_phase5k_opportunity_policy.py`
- `tests/opportunity_ai/test_phase5k_policy_finalization.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

Generated artifacts:

- `reports/opportunity_ai/phase5k/policy_finalization_summary.json`
- `reports/opportunity_ai/phase5k/policy_finalization_audit.json`
- `reports/opportunity_ai/phase5k/final_opportunity_output_schema.json`
- `reports/opportunity_ai/phase5k/final_policy_candidates.csv`

## 4. Final Policy Candidate Set

Phase5-K keeps policy candidates as ranking-policy candidates only. They are not purchase-count decisions.

| Policy | Phase5 position | Risk guard | Test mean return | Test max return | Downside delta | Test lift |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `current_model_top5` | candidate | recommended | 0.044614 | 0.215406 | -0.021417 | -0.001233 |
| `current_model_top10` | caution | required | 0.039344 | 0.199086 | -0.026015 | -0.006503 |
| `current_model_top20` | conservative fallback | recommended | 0.050035 | 0.197042 | -0.021417 | 0.004188 |
| `simple_rule_top5` | risk guard candidate | required | 0.143511 | 0.340287 | 0.075134 | 0.097664 |
| `top10_gap_threshold_policy` | candidate | recommended | 0.062318 | 0.226756 | -0.040454 | 0.016471 |
| `risk_adjusted_model_top5` | conservative candidate | built-in and recommended | 0.056016 | 0.221095 | -0.044406 | 0.010169 |
| `simple_rule_blend_model_top5` | balanced candidate | recommended | 0.096860 | 0.292643 | -0.003027 | 0.051013 |

## 5. simple_rule_top5 Handling

`simple_rule_top5` is the strongest return candidate:

- test mean future return: 0.143511
- test mean future max return: 0.340287
- test top-decile rate is strong
- test lift versus CandidateTop50: 0.097664

However:

- downside_bad_delta versus CandidateTop50: +0.075134
- downside_bad_rate worsens versus CandidateTop50

Conclusion:

- `simple_rule_top5` is not promotion-ready.
- It is a risk-guard-required ranking policy candidate.
- Any future use must emit and consume `risk_guard_status`, `downside_risk_score`, and `no_buy_reason`.

## 6. Top6-10 Tail Dilution

Phase5-J confirmed:

- `TAIL_DILUTION_CONFIRMED`

Phase5-K conclusion:

- fixed Top10 dilutes quality.
- Top10 must not be finalized as a fixed buy count in Phase5.
- Top10 should remain a ranking band or variable candidate set controlled by score gap, risk guard, or weak-tail filters.
- The actual number of names to buy belongs to downstream Capital Allocation / operational policy phases.

`top10_gap_threshold_policy` remains a Phase5 policy candidate because it improved test lift and downside metrics versus fixed Top10.

## 7. Final Output Schema

Phase5 Opportunity inference output schema is fixed as:

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

Notes:

- `is_top5`, `is_top10`, and `is_top20` are ranking-band flags, not buy-count instructions.
- `risk_guard_status` is required for all rows.
- `calibration_policy_name` records the policy context used for ranking or calibration interpretation.

## 8. Phase5 Recommendation

Phase5 final recommendation:

- Opportunity AI is a 20-business-day expected-value ranking AI.
- It ranks Candidate Top50 by expected opportunity and risk context.
- Top5 quality is promising, but not sufficient for promotion.
- Top10 needs tail dilution controls.
- `simple_rule_top5` is strong but requires risk guard.
- `risk_adjusted_model_top5` and `simple_rule_blend_model_top5` are useful conservative/balanced fallback candidates.
- promotion_ready remains false.
- downstream phases decide capital allocation, position management, and execution policy.

## 9. Safety / Source-of-Truth Rules

Confirmed rules:

- input features must come only from J-Quants API data or J-Quants-derived features.
- future columns are label/evaluation only.
- `future_return_*`, `future_max_return_*`, `future_max_drawdown_*`, `downside_bad_*`, and `top_decile_*` are not inference features.
- trade/backtest/portfolio/PM倍率/past AI judgment outputs are forbidden as features.
- Broker API, Paper Trading, orders, capital allocation, promotion, and reader switch are outside Phase5-K.

Audit result:

- leakage status: OK
- forbidden feature columns: 0
- future feature columns: 0
- trade result feature columns: 0
- portfolio feature columns: 0
- backtest feature columns: 0
- promotion_ready: false

## 10. Phase5-L Handoff

Phase5-K readiness:

- `READY_FOR_PHASE5L_COMPLETION_AUDIT`

Phase5-L should audit:

- Phase5 scope boundary
- final output schema consistency
- policy candidate documentation completeness
- leakage and forbidden-feature status
- promotion_ready=false
- no reader switch / no Paper Trading / no Broker API / no orders / no capital allocation

Handoff artifacts:

- `reports/opportunity_ai/phase5k/policy_finalization_summary.json`
- `reports/opportunity_ai/phase5k/policy_finalization_audit.json`
- `reports/opportunity_ai/phase5k/final_opportunity_output_schema.json`
- `reports/opportunity_ai/phase5k/final_policy_candidates.csv`
