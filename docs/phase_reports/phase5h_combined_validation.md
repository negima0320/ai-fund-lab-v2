# Phase5-H Candidate + Opportunity Combined Validation

## 1. Purpose

Phase5-H validates the combined Candidate AI + Opportunity AI flow.

The question is:

```text
Given CandidateTop50, does Opportunity AI improve the quality of Top5 / Top10 / Top20 selections?
```

This phase is validation only. It does not run backtests, Paper Trading, Broker API, orders, capital allocation, promotion, or reader switching.

## 2. Inputs

Audited artifacts:

- dataset: `reports/opportunity_ai/phase5d/opportunity_dataset.parquet`
- model: `models/opportunity_ai/phase5e/opportunity_model.pkl`
- latest inference: `reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet`
- latest inference summary: `reports/opportunity_ai/phase5f/opportunity_inference_summary.json`
- latest inference audit: `reports/opportunity_ai/phase5f/opportunity_inference_audit.json`

Latest inference is checked only for schema, leakage, score distribution, and TopN sanity because latest target date has no future labels yet.

## 3. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/combined_validation.py`
- `scripts/validate_phase5h_candidate_opportunity_combined.py`
- `tests/opportunity_ai/test_phase5h_combined_validation.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

Generated artifacts:

- `reports/opportunity_ai/phase5h/combined_validation_metrics.json`
- `reports/opportunity_ai/phase5h/combined_validation_audit.json`
- `reports/opportunity_ai/phase5h/combined_validation_by_date.csv`
- `reports/opportunity_ai/phase5h/combined_validation_by_split.csv`

## 4. Validation Method

For validation and test splits:

1. Recompute `expected_edge_score` using the Phase5-E model.
2. Build CandidateTop50 average by `target_date`.
3. Build Opportunity model Top5 / Top10 / Top20 by `target_date`.
4. Build candidate_score baseline Top5 / Top10 / Top20 by `target_date`.
5. Aggregate by split and by date.
6. Investigate test Top10 underperformance.

Metrics:

- `mean_future_return_20d`
- `mean_future_max_return_20d`
- `top_decile_rate_20d`
- `downside_bad_rate_20d`
- `mean_future_max_drawdown_20d`
- `win_rate_20d`

Not evaluated:

- annual return
- final assets
- profit factor
- portfolio drawdown
- trade result
- trade profit

## 5. Audit Result

Audit:

- dataset rows: 2,846
- target dates: 57
- validation target dates: 12
- test target dates: 5
- leakage status: OK
- forbidden feature columns: 0
- future feature columns: 0
- trade result feature columns: 0
- portfolio feature columns: 0
- model score available: true
- model unique score count: 847
- model all same score: false
- latest inference schema: OK
- latest inference leakage audit: OK
- latest Top5 / Top10 / Top20 count: 5 / 10 / 20
- promotion ready: false

## 6. Split Metrics

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

## 7. Top10 Warning Investigation

Original warning:

- `test_model_top10_under_candidate_top50`

Observed test Top10:

- Model Top10 mean future return: 0.001802
- CandidateTop50 mean future return: 0.011373
- Candidate score Top10 mean future return: -0.043003
- Model Top10 downside bad rate: 0.520000
- CandidateTop50 downside bad rate: 0.520000
- Candidate score Top10 downside bad rate: 0.540000

Underperforming dates:

- all validation/test underperforming target dates: 10
- test underperforming target dates: 3
- test dates: `2026-01-30`, `2026-02-27`, `2026-05-15`

Down-regime proxy:

- underperformance in down-regime proxy dates: 5
- dates: `2025-08-29`, `2025-10-31`, `2025-11-28`, `2026-02-27`, `2026-05-15`

Top6-10 tail:

- Top6-10 tail underperforming dates: 12
- this indicates Top10 quality is diluted by ranks 6-10, while Top5 is stronger.

Likely causes:

- underperformance is target-date-specific
- underperformance is concentrated in down-regime proxy dates
- Top6-10 tail dilutes Top10 quality
- candidate_score baseline is not the test Top10 cause, because model Top10 beats candidate_score Top10 on test

Downside bad:

- Model Top10 does not increase downside bad versus CandidateTop50 on test.
- Therefore the Top10 warning is more about weak return contribution and date/regime concentration than a pure downside-bad increase.

## 8. Stability

Validation/test gap:

- Model Top5 test minus validation: -0.034452
- Model Top10 test minus validation: -0.041575
- Model Top20 test minus validation: -0.027843
- RMSE test minus validation: 0.038836
- gap status: OK

Interpretation:

- Top5 lift is confirmed in both validation and test.
- Top10 remains weaker and should be watched in Phase5-I.
- Top20 is positive versus CandidateTop50 on test but modest.

## 9. Readiness

Readiness status:

- `READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION`

Promotion:

- `promotion_ready=false`
- promotion performed: false
- reader switch performed: false

Recommendation:

- Proceed to Phase5-I Full History Expansion.
- Keep promotion disabled.
- In Phase5-I, expand historical snapshots and verify whether the Top10 issue persists across more dates.
- Consider Top5-focused inference thresholds or Top10 calibration only after larger-history validation.
