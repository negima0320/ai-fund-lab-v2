# Phase5-I Full History Expansion

## 1. Purpose

Phase5-I expands Phase5 validation from monthly snapshots to all label-available historical target dates.

The purpose is to verify whether the Phase5-H findings hold when Candidate Top50 is generated for the full historical label/feature overlap.

This phase does not run live trading, Paper Trading, Broker API, orders, capital allocation, promotion, or reader switching.

## 2. Inputs

Phase4 Candidate model:

- `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl`

Long-history feature table:

- `.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet`

Long-history label table:

- `.runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet`

Latest inference safety artifacts:

- `reports/opportunity_ai/phase5f/latest_opportunity_inference.parquet`
- `reports/opportunity_ai/phase5f/opportunity_inference_summary.json`
- `reports/opportunity_ai/phase5f/opportunity_inference_audit.json`

Monthly comparison source:

- `reports/opportunity_ai/phase5h/combined_validation_metrics.json`

## 3. Implementation

Added files:

- `src/ai_fund_lab_v2/opportunity_ai/full_history_expansion.py`
- `scripts/run_phase5i_full_history_expansion.py`
- `tests/opportunity_ai/test_phase5i_full_history_expansion.py`

Updated:

- `src/ai_fund_lab_v2/opportunity_ai/historical_candidates.py`
- `src/ai_fund_lab_v2/opportunity_ai/__init__.py`

The historical candidate builder was optimized to group selected target dates instead of repeatedly scanning the full feature table per date.

## 4. Generated Artifacts

Main Phase5-I outputs:

- `reports/opportunity_ai/phase5i/full_history_candidate_top50.parquet`
- `reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet`
- `reports/opportunity_ai/phase5i/full_history_training_metrics.json`
- `reports/opportunity_ai/phase5i/full_history_quality_metrics.json`
- `reports/opportunity_ai/phase5i/full_history_combined_validation_metrics.json`
- `reports/opportunity_ai/phase5i/full_history_audit.json`
- `reports/opportunity_ai/phase5i/full_history_expansion_summary.json`

Stage outputs are also preserved under:

- `reports/opportunity_ai/phase5i/candidate_build/`
- `reports/opportunity_ai/phase5i/dataset_build/`
- `reports/opportunity_ai/phase5i/training/`
- `reports/opportunity_ai/phase5i/quality/`
- `reports/opportunity_ai/phase5i/combined/`
- `reports/opportunity_ai/phase5i/models/`

## 5. Expansion Result

Coverage:

- target dates: 1,202
- candidate rows: 57,150
- opportunity dataset rows: 56,995
- train rows: 40,559
- validation rows: 12,106
- test rows: 4,330
- label join coverage: 0.997288

Audit:

- leakage status: OK
- forbidden feature columns: 0
- future feature columns: 0
- trade result feature columns: 0
- portfolio feature columns: 0
- model unique score count: 15,540
- all same score: false
- validation/test gap status: OK
- promotion ready: false

## 6. Full History Metrics

Validation:

| Selection | mean_future_return_20d | mean_future_max_return_20d | top_decile_rate_20d | downside_bad_rate_20d | mean_future_max_drawdown_20d | win_rate_20d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CandidateTop50 average | 0.039679 | 0.168854 | 0.100363 | 0.421940 | -0.102556 | 0.502974 |
| Model Top5 | 0.061718 | 0.198058 | 0.144033 | 0.397531 | -0.094117 | 0.533333 |
| Model Top10 | 0.048136 | 0.176844 | 0.119342 | 0.400000 | -0.095571 | 0.514403 |
| Model Top20 | 0.044093 | 0.167511 | 0.101646 | 0.396502 | -0.095119 | 0.511934 |

Test:

| Selection | mean_future_return_20d | mean_future_max_return_20d | top_decile_rate_20d | downside_bad_rate_20d | mean_future_max_drawdown_20d | win_rate_20d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CandidateTop50 average | 0.045847 | 0.193353 | 0.100462 | 0.458199 | -0.108387 | 0.488915 |
| Model Top5 | 0.044614 | 0.215406 | 0.121839 | 0.436782 | -0.094812 | 0.478161 |
| Model Top10 | 0.039344 | 0.199086 | 0.096552 | 0.432184 | -0.096932 | 0.485057 |
| Model Top20 | 0.050035 | 0.197042 | 0.095402 | 0.436782 | -0.101905 | 0.493103 |

## 7. Monthly vs Full History

Validation:

| Selection | monthly mean return | full history mean return | delta |
| --- | ---: | ---: | ---: |
| Top5 | 0.067688 | 0.061718 | -0.005970 |
| Top10 | 0.043377 | 0.048136 | 0.004759 |
| Top20 | 0.048660 | 0.044093 | -0.004567 |

Test:

| Selection | monthly mean return | full history mean return | delta |
| --- | ---: | ---: | ---: |
| Top5 | 0.033236 | 0.044614 | 0.011378 |
| Top10 | 0.001802 | 0.039344 | 0.037542 |
| Top20 | 0.020817 | 0.050035 | 0.029218 |

Compared with monthly snapshots, full history improved test Top5 / Top10 / Top20 absolute mean future return. However, CandidateTop50 test average also changed upward, so lift status must be judged against the full-history baseline.

## 8. Stability Assessment

Lift status versus CandidateTop50:

- Top5: MIXED
- Top10: MIXED
- Top20: CONFIRMED

Interpretation:

- Top5 is strong in validation but slightly below CandidateTop50 on test mean return.
- Top5 still improves test future max return, top decile rate, downside bad rate, and drawdown versus CandidateTop50.
- Top10 improves materially versus the monthly result but remains below CandidateTop50 average on test mean return.
- Top20 is confirmed across validation/test on mean future return.

## 9. Top10 Investigation

Full history Top10 status:

- `PERSISTENT_BUT_INVESTIGATED`

Observed:

- test Model Top10 mean future return: 0.039344
- test CandidateTop50 mean future return: 0.045847
- test candidate_score Top10 mean future return: 0.006279
- test Model Top10 downside bad rate: 0.432184
- test CandidateTop50 downside bad rate: 0.458199
- test candidate_score Top10 downside bad rate: 0.500000

Likely causes:

- underperformance is target-date-specific
- Top6-10 tail dilutes Top10 quality
- candidate_score baseline is not the test Top10 cause

The down-regime proxy explanation is weaker than in monthly validation because full history spreads the effect across more target dates. The Top6-10 tail remains a clear issue.

## 10. Readiness

Readiness status:

- `READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION`

Promotion:

- `promotion_ready=false`
- promotion performed: false
- reader switch performed: false

Recommendation:

- Proceed to Phase5-J model improvement or calibration.
- Do not promote the model.
- Focus Phase5-J on calibration of Top5/Top10 thresholds, especially the Top6-10 tail.
- Compare model ranking with the simple rule baseline, which remains strong in several full-history test metrics.
