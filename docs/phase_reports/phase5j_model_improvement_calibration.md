# Phase5-J Model Improvement / Calibration

## 1. Purpose

Phase5-J compares multiple Opportunity AI ranking and calibration strategies on the Phase5-I full-history dataset.

The goal is to improve or calibrate Candidate Top50 to Opportunity Top5 / Top10 / Top20 selection quality, especially the persistent Top6-10 tail dilution seen in Phase5-I.

This phase does not perform live trading, Paper Trading, Broker API access, order placement, capital allocation, promotion, or reader switching.

## 2. Inputs

Full-history dataset:

- `reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet`

Baseline Phase5-I model and metrics:

- `reports/opportunity_ai/phase5i/models/opportunity_model.pkl`
- `reports/opportunity_ai/phase5i/full_history_combined_validation_metrics.json`
- `reports/opportunity_ai/phase5i/full_history_audit.json`

Dataset scale:

- target dates: 1,143 joined dataset dates
- dataset rows: 56,995
- train / validation / test: 40,559 / 12,106 / 4,330
- leakage status: OK

The difference between 1,202 candidate target dates and 1,143 joined dataset target dates is expected after target_date + code label/feature join coverage.

## 3. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/model_calibration.py`
- `scripts/run_phase5j_model_improvement_calibration.py`
- `tests/opportunity_ai/test_phase5j_model_improvement_calibration.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

Generated artifacts:

- `reports/opportunity_ai/phase5j/calibration_metrics.json`
- `reports/opportunity_ai/phase5j/calibration_audit.json`
- `reports/opportunity_ai/phase5j/calibration_by_strategy.csv`
- `reports/opportunity_ai/phase5j/calibration_by_date.csv`
- `reports/opportunity_ai/phase5j/recommended_policy.json`

## 4. Compared Strategies

Phase5-J compares these strategy families:

- current model Top5 / Top10 / Top20
- candidate_score baseline Top5 / Top10 / Top20
- simple rule baseline Top5 / Top10 / Top20
- Top5 only policy
- Top10 with score threshold policy
- Top10 with gap threshold policy
- Top10 excluding weak Top6-10 tail policy
- adjusted sklearn HistGradientBoosting model Top5 / Top10 / Top20
- label-weight-adjusted model Top5 / Top10 / Top20
- candidate_score + expected_edge_score blend Top5 / Top10 / Top20
- expected_edge_score - downside_risk_proxy Top5 / Top10 / Top20
- simple_rule + expected_edge_score blend Top5 / Top10 / Top20

The adjusted models are evaluated as calibration candidates only. No model artifact is promoted.

## 5. Leakage / Safety Audit

Audit result:

- leakage status: OK
- feature columns: 16
- label columns: 14
- forbidden feature columns: 0
- future feature columns: 0
- trade result feature columns: 0
- portfolio feature columns: 0
- backtest feature columns: 0
- AI output feature columns: 0
- strategy count: 29
- model unique score count: 15,540
- all same score: false
- promotion_ready: false

Future columns were used only as labels/evaluation values. They were not used as model input features.

## 6. Key Results

Validation:

| Strategy | Selection | Mean return 20d | Mean max return 20d | Top decile rate | Downside bad rate | Mean max drawdown | Win rate | Lift vs CandidateTop50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CandidateTop50 | average | 0.039679 | 0.168854 | 0.100363 | 0.421940 | -0.102556 | 0.502974 | 0.000000 |
| Current model | Top5 | 0.061718 | 0.198058 | 0.144033 | 0.397531 | -0.094117 | 0.533333 | 0.022039 |
| Current model | Top10 | 0.048136 | 0.176844 | 0.119342 | 0.400000 | -0.095571 | 0.514403 | 0.008457 |
| Current model | Top20 | 0.044093 | 0.167511 | 0.101646 | 0.396502 | -0.095119 | 0.511934 | 0.004414 |
| Top10 score threshold | variable Top10 | 0.055815 | 0.184728 | 0.128086 | 0.399177 | -0.093752 | 0.529835 | 0.016136 |
| Top10 gap threshold | variable Top10 | 0.039325 | 0.170420 | 0.118890 | 0.413398 | -0.096755 | 0.495474 | -0.000354 |
| Top10 excluding weak tail | variable Top10 | 0.062351 | 0.189774 | 0.143240 | 0.384203 | -0.089896 | 0.546185 | 0.022672 |

Test:

| Strategy | Selection | Mean return 20d | Mean max return 20d | Top decile rate | Downside bad rate | Mean max drawdown | Win rate | Lift vs CandidateTop50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CandidateTop50 | average | 0.045847 | 0.193353 | 0.100462 | 0.458199 | -0.108387 | 0.488915 | 0.000000 |
| Current model | Top5 | 0.044614 | 0.215406 | 0.121839 | 0.436782 | -0.094812 | 0.478161 | -0.001233 |
| Current model | Top10 | 0.039344 | 0.199086 | 0.096552 | 0.432184 | -0.096932 | 0.485057 | -0.006503 |
| Current model | Top20 | 0.050035 | 0.197042 | 0.095402 | 0.436782 | -0.101905 | 0.493103 | 0.004188 |
| Top10 score threshold | variable Top10 | 0.036913 | 0.196097 | 0.097944 | 0.434099 | -0.096426 | 0.481258 | -0.008934 |
| Top10 gap threshold | variable Top10 | 0.062318 | 0.226756 | 0.101664 | 0.417745 | -0.091542 | 0.508318 | 0.016471 |
| Top10 excluding weak tail | variable Top10 | 0.042443 | 0.202131 | 0.113946 | 0.430272 | -0.094537 | 0.474490 | -0.003404 |

Simple rule baseline on test:

| Strategy | Selection | Mean return 20d | Mean max return 20d | Top decile rate | Downside bad rate | Win rate | Lift vs CandidateTop50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Simple rule | Top5 | 0.143511 | 0.340287 | 0.236782 | 0.533333 | 0.547126 | 0.097664 |
| Simple rule | Top10 | 0.124590 | 0.301654 | 0.196552 | 0.517241 | 0.511494 | 0.078743 |
| Simple rule | Top20 | 0.098516 | 0.255615 | 0.151149 | 0.485632 | 0.529310 | 0.052669 |

The simple rule baseline is very strong on return and top-decile capture, but its downside_bad_rate is worse than CandidateTop50. It should be treated as a calibration candidate that needs explicit risk guardrails, not as a promoted production policy.

## 7. Top6-10 Tail Dilution

Top6-10 tail analysis:

- status: `TAIL_DILUTION_CONFIRMED`
- validation tail mean return: 0.034553
- validation Top5 mean return: 0.061718
- validation tail minus Top5: -0.027165
- validation tail underperforming dates: 131
- test tail mean return: 0.034074
- test Top5 mean return: 0.044614
- test tail minus Top5: -0.010540
- test tail underperforming dates: 54

Conclusion:

- Fixed Top10 continues to dilute Top5 quality.
- Gap-threshold Top10 improved test lift and downside metrics versus fixed Top10.
- Weak-tail exclusion improved validation strongly but did not solve test mean return.
- Fixed Top20 remains more stable than fixed Top10, consistent with Phase5-I.

## 8. Recommended Policy Candidate

`recommended_policy.json` selected:

- policy_name: `simple_rule_top5`
- recommendation_type: `calibration_candidate_not_promoted`
- promotion_ready: false
- reader_switch_ready: false

Reason:

- Simple rule Top5 had the strongest combined validation/test policy score.
- It materially improves test mean future return and future max return.
- However, downside_bad_rate is worse than CandidateTop50, so it should not be promoted as-is.
- Phase5-K should evaluate whether simple-rule-style ranking can be blended with explicit downside risk guards.

Important:

- This is not a production adoption decision.
- No promotion was performed.
- No reader switch was performed.

## 9. Readiness

Readiness status:

- `READY_FOR_PHASE5K_POLICY_FINALIZATION`

Conditions satisfied:

- leakage audit OK
- multiple strategies compared
- Top5 / Top10 / Top20 policy candidates evaluated
- Top6-10 tail dilution investigated
- recommended policy candidate written
- promotion_ready=false

Recommended next phase:

- Proceed to Phase5-K Policy Finalization.
- Keep promotion disabled.
- Focus Phase5-K on deciding between:
  - Top5-only operation
  - variable Top10 with gap threshold
  - simple-rule-informed Top5 with risk guard
  - model/risk-adjusted blend as a conservative fallback
