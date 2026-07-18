# Phase18-H — Promotion Blocking Issues Resolution

- Run ID: `phase18h-promotion-blocking-resolution-20260717T000000Z`
- Final judgment: `PHASE18_H_PROMOTION_READY_WITH_REVIEW`
- Promotion recommendation: `PROMOTION_READY_WITH_REVIEW`
- Selected challenger: `{'model_name': 'hist_gradient_boosting', 'window_name': 'rolling_3y', 'calibration_name': 'isotonic_materialized'}`
- Formal Challenger bundle: `.runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b`

## Fixed Contracts

- Target: `label__expected_edge_label_20d`
- Feature contract: `32 feature contract`
- Candidate connection: `candidate_source_ref`
- BV15: unchanged

## Blocking Matrix

| Item | Before | After | Status |
|------|--------|-------|--------|
| Calibration Artifact | `False` | `True` | `PASS` |
| Validation Spearman | `0.057727` | `0.094918` | `PASS` |
| Test Spearman | `-0.071424` | `0.050572` | `PASS` |
| Validation Monotonicity | `False` | `True` | `PASS` |
| Test Monotonicity | `False` | `True` | `PASS` |
| Runtime Compatibility | `False` | `True` | `PASS` |

## Readiness Reassessment

- Safety / Integrity: `PASS`
- Predictive Validity: `PASS`
- Operational Utility: `REVIEW_REQUIRED`

## Selected Metrics

- Validation Spearman: `0.094918`
- Test Spearman: `0.050572`
- Recent Spearman: `0.105714`
- Validation bucket monotonicity: `True`
- Test bucket monotonicity: `True`
- Recent bucket monotonicity: `True`
- Recent positive coverage: `0.092361`
- Recent NO BUY ratio: `0.62069`

## Calibration Artifact

- Calibration hash: `9a092c2dd0466b41b4e1d8b5c63ae5cbb3065e908d27df3f7493f758762af542`
- Calibration model hash: `7966d0d30a24e5248b51d9aac0507fa93aedae8541806dd50320ff2d5c309250`
- Runtime-compatible reproduction: `PASS`

## Non-Mutation

- Registry accepted update: `False`
- Runtime switch: `False`
- BUY restart: `False`
- Broker write: `False`

## Final

`PHASE18_H_PROMOTION_READY_WITH_REVIEW`
