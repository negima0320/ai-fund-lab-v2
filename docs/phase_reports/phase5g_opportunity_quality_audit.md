# Phase5-G Opportunity Quality Audit

## 1. Purpose

Phase5-G audits whether Opportunity AI improves expected-value quality when narrowing Candidate Top50 to Opportunity Top5 / Top10 / Top20.

This phase is quality evaluation only. It does not run backtests, Paper Trading, Broker API, orders, capital allocation, promotion, or reader switching.

Phase5-E training completed with warnings and Phase5-F `promotion_ready` is false, so Phase5-G must preserve `promotion_ready=false`.

## 2. Inputs

Audited artifacts:

- dataset: `reports/opportunity_ai/phase5d/opportunity_dataset.parquet`
- model: `models/opportunity_ai/phase5e/opportunity_model.pkl`
- latest inference: `reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet`
- latest inference summary: `reports/opportunity_ai/phase5f/opportunity_inference_summary.json`
- latest inference audit: `reports/opportunity_ai/phase5f/opportunity_inference_audit.json`

Latest inference is audited for schema, leakage, score distribution, and TopN sanity only. It is not used for actual quality metrics because future labels are not available for the latest target date.

## 3. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/quality_audit.py`
- `scripts/audit_phase5g_opportunity_quality.py`
- `tests/opportunity_ai/test_phase5g_opportunity_quality_audit.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

Generated artifacts:

- `reports/opportunity_ai/phase5g/opportunity_quality_audit.json`
- `reports/opportunity_ai/phase5g/opportunity_quality_metrics.json`
- `reports/opportunity_ai/phase5g/opportunity_quality_by_split.csv`

## 4. Audit Method

For validation and test split:

1. Load Phase5-D dataset.
2. Load Phase5-E model artifact.
3. Recompute `expected_edge_score` using only model `feature__*` columns.
4. Evaluate CandidateTop50 average.
5. Evaluate Opportunity model Top5 / Top10 / Top20.
6. Evaluate candidate_score baseline Top5 / Top10 / Top20.
7. Compare model versus baseline lift.
8. Check score distribution and score collapse.
9. Check validation/test gap.

Metrics:

- `mean_future_return_20d`
- `mean_future_max_return_20d`
- `top_decile_rate_20d`
- `downside_bad_rate_20d`
- `mean_future_max_drawdown_20d`
- `win_rate_20d`

Not evaluated in Phase5-G:

- annual return
- final assets
- profit factor
- portfolio drawdown
- trade result
- trade profit

## 5. Leakage Result

Dataset audit:

- dataset rows: 2,846
- validation rows: 598
- test rows: 250
- feature columns: 16
- label columns: 14
- leakage status: OK
- forbidden feature columns: 0
- future feature columns: 0

Latest inference audit:

- schema status: OK
- leakage audit status: OK
- label table read flag: false
- future feature columns: 0
- forbidden feature columns: 0
- Top5 / Top10 / Top20 count: 5 / 10 / 20
- unique score count: 50
- all same score: false

## 6. Quality Metrics

Validation:

| Selection | mean_future_return_20d | mean_future_max_return_20d | top_decile_rate_20d | downside_bad_rate_20d | mean_future_max_drawdown_20d | win_rate_20d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CandidateTop50 average | 0.036628 | 0.177288 | 0.100334 | 0.446488 | -0.104075 | 0.466555 |
| Model Top5 | 0.067688 | 0.239962 | 0.150000 | 0.483333 | -0.109737 | 0.466667 |
| Model Top10 | 0.043377 | 0.195708 | 0.141667 | 0.408333 | -0.100189 | 0.491667 |
| Model Top20 | 0.048660 | 0.197674 | 0.120833 | 0.404167 | -0.096187 | 0.508333 |
| Candidate score Top5 | 0.112356 | 0.303763 | 0.166667 | 0.400000 | -0.093337 | 0.533333 |
| Candidate score Top10 | 0.083016 | 0.249623 | 0.141667 | 0.466667 | -0.107963 | 0.475000 |
| Candidate score Top20 | 0.058938 | 0.222453 | 0.137500 | 0.437500 | -0.105351 | 0.462500 |

Test:

| Selection | mean_future_return_20d | mean_future_max_return_20d | top_decile_rate_20d | downside_bad_rate_20d | mean_future_max_drawdown_20d | win_rate_20d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CandidateTop50 average | 0.011373 | 0.196223 | 0.100000 | 0.520000 | -0.117236 | 0.400000 |
| Model Top5 | 0.033236 | 0.191934 | 0.160000 | 0.440000 | -0.102153 | 0.520000 |
| Model Top10 | 0.001802 | 0.182094 | 0.100000 | 0.520000 | -0.118335 | 0.440000 |
| Model Top20 | 0.020817 | 0.193435 | 0.110000 | 0.530000 | -0.115256 | 0.390000 |
| Candidate score Top5 | -0.034538 | 0.212345 | 0.120000 | 0.560000 | -0.148647 | 0.400000 |
| Candidate score Top10 | -0.043003 | 0.162755 | 0.100000 | 0.540000 | -0.130232 | 0.380000 |
| Candidate score Top20 | -0.027498 | 0.161471 | 0.100000 | 0.600000 | -0.135556 | 0.340000 |

## 7. Findings

Positive:

- Test Model Top5 improves mean future return over CandidateTop50 average: 0.033236 vs 0.011373.
- Test Model Top5 improves win rate: 0.520000 vs 0.400000.
- Test Model Top5 reduces downside bad rate: 0.440000 vs 0.520000.
- Test model beats candidate_score baseline on mean future return for Top5 / Top10 / Top20.
- Model scores did not collapse: 847 unique scores across validation/test.
- Latest inference artifact schema and leakage audit are OK.

Warnings:

- `test_model_top10_under_candidate_top50`: test Model Top10 mean future return is 0.001802, below CandidateTop50 average 0.011373.
- Validation candidate_score baseline is stronger than the model for Top5 / Top10 / Top20 mean future return.
- Phase5-E is still warning-grade training, so this is not promotion-ready.

Validation/test gap:

- Model Top5 test minus validation: -0.034452
- Model Top10 test minus validation: -0.041575
- Model Top20 test minus validation: -0.027843
- RMSE test minus validation: 0.038836
- gap status: OK

## 8. Readiness

Readiness status:

- `READY_FOR_PHASE5H_COMBINED_VALIDATION`

Promotion:

- `promotion_ready=false`
- promotion performed: false
- reader switch performed: false

Recommendation:

- Proceed to Phase5-H Candidate + Opportunity Combined Validation.
- Keep the Phase5-E/F artifacts as audit artifacts, not production artifacts.
- Phase5-H should explicitly inspect why Model Top10 underperforms CandidateTop50 on the test split while Model Top5 and Top20 are better.
