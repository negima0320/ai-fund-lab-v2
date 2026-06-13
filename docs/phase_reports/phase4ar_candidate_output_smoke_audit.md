# Phase4-AR Candidate Output Audit Smoke

- status: complete
- readiness_status: `TECHNICAL_PHASE4_SMOKE_COMPLETE_WITH_MODEL_QUALITY_BLOCKED`
- summary: `reports/candidate_ai/full_range/phase4ar_candidate_output_smoke_summary.json`

## Summary

- status: OK
- readiness_status: TECHNICAL_PHASE4_SMOKE_COMPLETE_WITH_MODEL_QUALITY_BLOCKED
- candidate_count: 50
- scored_count: 3866
- candidate_score_min: 0.093605
- candidate_score_max: 0.093605
- candidate_score_mean: 0.093605
- candidate_score_std: 0.0
- unique_candidate_score_count: 1
- all_same_score: True
- ranking_effective: False
- responsibility_boundary_status: OK
- recommended_next_action: Phase4-AS Candidate Model Quality Root Cause Analysis before formal quality audit.

## Interpretation

- `TECHNICAL_PHASE4_SMOKE_COMPLETE_WITH_MODEL_QUALITY_BLOCKED` means the output pipeline is technically sound but model quality is blocked.
- All-same candidate scores indicate the current smoke model does not provide useful ranking information.
- This audit does not improve the model, change labels, run backtests, or perform trading.
