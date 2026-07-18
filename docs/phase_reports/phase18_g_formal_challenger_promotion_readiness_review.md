# Phase18-G — Formal Challenger Promotion Readiness Review

- Run ID: `phase18g-promotion-readiness-review-20260717T000000Z`
- Final judgment: `PHASE18_G_NOT_PROMOTION_READY`
- Promotion recommendation: `NOT_PROMOTION_READY`
- Generalization: `MILD_OVERFIT`

## Summary

Test/generalization or monotonicity gaps prevent Promotion Candidate submission.

Safety / Integrity is `FAIL` because the selected Opportunity artifact does not materialize its fitted calibration payload for Runtime-compatible reproduction. Operational Utility is `PASS`, but Predictive Validity is `FAIL` because test/generalization and monotonicity gates remain unresolved.

## Key Evidence

- Safety / Integrity: `FAIL`
- Predictive Validity: `FAIL`; hard failures `['test_spearman_nonnegative', 'test_bucket_monotonic', 'validation_bucket_monotonic']`
- Operational Utility: `PASS`
- Test Spearman: `-0.071424`
- Test bucket monotonic: `False`
- Validation bucket monotonic: `False`
- Recent Top5 mean: `0.109683`
- NO BUY ratio: `0.0`

## Promotion Criteria Matrix

| Category | Status | Evidence | Promotion Impact |
|----------|--------|----------|------------------|
| Dataset | `PASS` | `"Candidate/Opportunity dataset status/hash/PIT/leakage PASS"` | Blocks promotion on failure |
| Training | `FAIL` | `{"candidate_status": "PASS", "opportunity_calibration_materialized": false, "opportunity_calibration_name": "platt_like", "opportunity_status": "FAIL"}` | Blocks promotion on failure |
| Validation | `FAIL` | `{"calibration": {"bucket_monotonic": false, "calibration_error": 0.209775, "positive_sign_consistency": 0.559794}, "hit_rate_top20": 0.502928, "hit_rate_top5": 0.508108, "no_buy...` | Review gate; monotonicity failed blocks READY |
| Test | `FAIL` | `{"calibration": {"bucket_monotonic": false, "calibration_error": 0.234045, "positive_sign_consistency": 0.48299}, "hit_rate_top20": 0.525641, "hit_rate_top5": 0.553846, "no_buy_...` | Blocks PROMOTION_READY |
| Recent Holdout | `PASS` | `{"calibration": {"bucket_monotonic": true, "calibration_error": 0.255966, "positive_sign_consistency": 0.541667}, "hit_rate_top20": 0.52931, "hit_rate_top5": 0.489655, "no_buy_d...` | Passes recent gate |
| Calibration | `PASS` | `{"bucket_monotonic": true, "calibration_error": 0.255966, "positive_sign_consistency": 0.541667}` | Review gate across splits |
| Regime | `PASS` | `{"recent_holdout": {"bearish": {"bucket_monotonic": true, "spearman": 0.191315, "top5_mean": 0.121658}, "bullish_or_neutral": {"bucket_monotonic": false, "spearman": 0.231064, "...` | Review gate |
| Operational Utility | `PASS` | `{"cash_stagnation_risk": "LOW", "concentration": 0.267241, "cost_adjusted_edge": 0.087403, "expected_opportunity_frequency": 1.0, "negative_expected_edge_buy_allowed": false, "n...` | Passes BV15 operational review |
| Reproducibility | `PASS` | `"Phase18-D Candidate and Phase18-F Opportunity reproducibility PASS"` | Blocks promotion on failure |
| Runtime Compatibility | `FAIL` | `{"candidate_dataset_reference": {"component": "Candidate", "dataset_dir": ".runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d", "dataset_hash": "0afd...` | Bundle info ready; no Runtime switch performed |

## Atomic BUY AI Bundle Readiness

- Status: `REVIEW_REQUIRED`
- Joint bundle hash preview: `1f16d26de8380320b9a87dfb60c665c8aa79c7bd80e5df08cc025a0497d4730f`
- Candidate and Opportunity training bundle references are present.
- Rollback references are present.
- No accepted event was written.

## Non-Mutation

- Registry accepted update: `False`
- Runtime switch: `False`
- BUY restart: `False`
- Broker write: `False`
- Production change: `False`

## Final

`PHASE18_G_NOT_PROMOTION_READY`
