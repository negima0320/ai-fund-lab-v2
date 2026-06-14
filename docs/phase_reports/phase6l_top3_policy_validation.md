# Phase6-L Top3 Buy Policy Validation

## 1. Purpose

Phase6-L validates whether the Phase4 Candidate AI -> Phase5 Opportunity AI buy-candidate policy should narrow the primary buy target from Top5 to Top3.

The validation reuses the Phase6-K setup:

```text
2021-2026
5 random target_dates per year
seed = 42
Candidate Top50 artifact
Phase5 Opportunity model re-scoring
future outcome columns for evaluation only
```

Completion decision:

```text
PHASE6L_TOP3_POLICY_WITH_FINDINGS
```

## 2. Read Docs

- `docs/01_requirements/phase_roadmap.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase6j_random_yearly_e2e_smoke_test.md`
- `docs/phase_reports/phase6k_expanded_random_validation.md`
- `docs/phase_reports/phase5_final_handoff_for_phase6.md`
- `docs/phase_reports/phase5r_opportunity_ranking_quality_audit.md`

## 3. Created / Updated Files

- `src/ai_fund_lab_v2/end_to_end/top3_policy_validation.py`
- `scripts/run_phase6l_top3_policy_validation.py`
- `tests/end_to_end/test_phase6l_top3_policy_validation.py`
- `docs/phase_reports/phase6l_top3_policy_validation.md`

Generated outputs:

- `reports/end_to_end/phase6l_top3_policy_validation.csv`
- `reports/end_to_end/phase6l_top3_policy_validation.json`
- `reports/end_to_end/phase6l_top3_vs_top5_vs_top10.json`
- `reports/end_to_end/phase6l_yearly_top3_summary.json`
- `reports/end_to_end/phase6l_risk_guard_policy_comparison.json`
- `reports/end_to_end/phase6l_policy_recommendation.json`

## 4. Data

Candidate source:

```text
reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet
```

Opportunity source:

```text
reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet
reports/opportunity_ai/phase5i/models/opportunity_model.pkl
```

Future outcome source:

```text
.runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet
```

Future columns are evaluation-only and are not used for inference.

## 5. Target Dates

Target years:

```text
2021
2022
2023
2024
2025
2026
```

Seed:

```text
42
```

Phase6-Kと同じtarget_date:

| year | target_dates |
| --- | --- |
| 2021 | 2021-09-15, 2021-10-05, 2021-10-25, 2021-10-28, 2021-11-04 |
| 2022 | 2022-02-10, 2022-03-03, 2022-10-27, 2022-11-18, 2022-11-21 |
| 2023 | 2023-01-17, 2023-02-06, 2023-07-04, 2023-09-04, 2023-09-21 |
| 2024 | 2024-01-17, 2024-02-08, 2024-04-02, 2024-04-08, 2024-07-19 |
| 2025 | 2025-01-15, 2025-03-21, 2025-08-28, 2025-10-03, 2025-11-20 |
| 2026 | 2026-01-16, 2026-03-02, 2026-03-11, 2026-04-07, 2026-04-14 |

Row count:

```text
candidate_count: 1500
validation_row_count: 300
```

## 6. Top3 / Top5 / Top10 Comparison

| bucket | count | mean_5bd | mean_10bd | mean_20bd | median_20bd | mean_max_20bd | mean_min_20bd | positive_20bd_rate | worst_20bd | best_20bd |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top3 | 90 | 0.083803 | 0.118668 | 0.169041 | 0.090624 | 0.347904 | -0.068581 | 0.644444 | -0.267263 | 2.835987 |
| Top5 | 150 | 0.060365 | 0.078420 | 0.093449 | 0.010438 | 0.255847 | -0.089265 | 0.526667 | -0.503030 | 2.835987 |
| Top10 | 300 | 0.041046 | 0.048017 | 0.060414 | -0.003256 | 0.204788 | -0.095454 | 0.480000 | -0.885714 | 2.835987 |

Finding:

```text
Top3 advantage confirmed.
```

Top3 has the strongest mean return, median return, positive rate, and shallower average downside than Top5 / Top10.

## 7. Top4-5 / Top6-10 Comparison

| bucket | count | mean_20bd | median_20bd | mean_max_20bd | mean_min_20bd | positive_20bd_rate | worst_20bd | best_20bd |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top4-5 | 60 | -0.019940 | -0.044677 | 0.117762 | -0.120292 | 0.350000 | -0.503030 | 0.797005 |
| Top6-10 | 150 | 0.027379 | -0.022441 | 0.153729 | -0.101643 | 0.433333 | -0.885714 | 2.115538 |

Interpretation:

```text
Top4-5 is not strong enough to be primary buy target.
Top6-10 should be excluded from normal buy candidates.
```

Top6-10 contains occasional upside outliers, but median return is negative and worst outcome is much deeper.

## 8. Yearly Top3 Result

| year | count | mean_20bd | median_20bd | mean_max_20bd | mean_min_20bd | positive_20bd_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2021 | 15 | -0.009691 | 0.012346 | 0.135143 | -0.068349 | 0.533333 |
| 2022 | 15 | 0.286794 | 0.180596 | 0.615224 | -0.026351 | 0.800000 |
| 2023 | 15 | 0.105541 | 0.091390 | 0.205108 | -0.025853 | 0.733333 |
| 2024 | 15 | 0.295353 | 0.142787 | 0.485375 | -0.091600 | 0.600000 |
| 2025 | 15 | 0.355268 | 0.137255 | 0.485240 | -0.077622 | 0.866667 |
| 2026 | 15 | -0.019017 | -0.059004 | 0.161333 | -0.121710 | 0.333333 |

## 9. 2022 Analysis

Top3 in 2022 is strong:

```text
mean_future_return_20bd: 0.286794
median_future_return_20bd: 0.180596
positive_return_20bd_rate: 0.800000
mean_future_max_return_20bd: 0.615224
```

Conclusion:

```text
2022 weakness observed in the one-day Phase6-J sample does not hold in the expanded Top3 sample.
```

## 10. 2026 Analysis

Top3 in 2026 remains weak:

```text
mean_future_return_20bd: -0.019017
median_future_return_20bd: -0.059004
positive_return_20bd_rate: 0.333333
mean_future_min_return_20bd: -0.121710
```

Conclusion:

```text
2026 weakness remains even when narrowed to Top3.
```

This suggests regime sensitivity rather than simple tail dilution from Top4-10.

## 11. Risk Guard SKIP vs LOW_PRIORITY

| policy | included_count | skip_count | low_priority_count | mean_20bd | mean_max_20bd | mean_min_20bd | positive_20bd_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top3_BUY_ONLY | 83 | 7 | 0 | 0.146235 | 0.277661 | -0.068154 | 0.650602 |
| Top3_WITH_LOW_PRIORITY | 90 | 0 | 7 | 0.169041 | 0.347904 | -0.068581 | 0.644444 |
| Top5_BUY_ONLY | 141 | 9 | 0 | 0.079213 | 0.214154 | -0.088722 | 0.531915 |
| Top5_WITH_LOW_PRIORITY | 150 | 0 | 9 | 0.093449 | 0.255847 | -0.089265 | 0.526667 |

Finding:

```text
LOW_PRIORITY improves mean return and max return, but slightly lowers positive rate and keeps downside cost.
```

Recommendation:

```text
risk_guard bad should not be automatic BUY.
risk_guard bad should not be permanently discarded either.
Treat it as LOW_PRIORITY_REVIEW.
```

## 12. Recommended Buy Policy

Recommended policy:

```text
Primary buy target: Top3
Backup watchlist: Top4-5
Avoid / no buy: Top6-10
Risk Guard bad: LOW_PRIORITY_REVIEW
```

Rationale:

- Top3 is materially stronger than Top5 and Top10.
- Top4-5 is weak enough that it should not be primary.
- Top6-10 has tail dilution and deeper worst-case outcomes.
- Risk Guard bad contains upside outliers, but also downside cost.
- 2026 remains a weak regime and needs additional monitoring.

## 13. Audit

Forbidden feature audit:

```text
forbidden_feature_audit_status: OK
forbidden_feature_column_count: 0
```

Leakage audit:

```text
leakage_audit_status: OK
future_columns_not_used_for_inference: true
future_feature_columns: []
```

Execution boundary:

```text
broker_api_executed: false
order_executed: false
paper_trading_executed: false
capital_allocation_executed: false
live_order_executed: false
real_account_updated: false
full_backtest_executed: false
```

## 14. Verification

Commands:

```text
python3 -m pytest tests/end_to_end/test_phase6l_top3_policy_validation.py
python3 scripts/run_phase6l_top3_policy_validation.py
```

Result:

```text
7 passed
PHASE6L_TOP3_POLICY_WITH_FINDINGS
```

Runtime notes:

```text
pyarrow / joblib emitted CPU detection warnings under sandboxed execution.
The validation completed successfully.
```

## 15. Next Tasks

- Carry Top3-first policy into Phase7 planning.
- Keep Top4-5 as watchlist / backup, not equal-priority buy candidates.
- Exclude Top6-10 from normal buy candidates unless a later rule explicitly overrides it.
- Design a LOW_PRIORITY_REVIEW handling path for risk_guard bad candidates.
- Add regime-aware controls for weak periods such as 2026.
- Keep future outcome columns evaluation-only.
- Continue to prohibit Broker API, order placement, Paper Trading, Capital Allocation, live order, and real account updates in validation phases.
