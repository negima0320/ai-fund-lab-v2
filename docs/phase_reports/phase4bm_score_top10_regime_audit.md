# Phase4-BM Candidate Score / Top10 Capture / Regime Proxy Audit

- status: `OK`
- readiness_status: `PHASE4_SCORE_TOP10_REGIME_AUDIT_COMPLETE`
- score_rank_monotonicity_status: `PARTIAL`
- candidate_top50_future_return_top10_capture_rate: `0.076`
- candidate_top50_future_max_top10_capture_rate: `0.072`
- regime_proxy_status: `OK`

## Key Findings

- score_rank_monotonicity_partial
- candidate_top50_captures_future_return_top10_above_random
- candidate_top50_captures_future_max_top10_above_random
- higher_score_has_positive_downside_bad_correlation

## Phase5 Implications

- Phase5 should not rely on Candidate score rank alone; add confirmation and risk filters.
- Regime proxy is post-selection evaluation only and must not become a selection feature.

## Guardrails

- Candidate selection used feature-only inputs.
- Future/label/regime proxy data was used only after candidate lists were created for evaluation.
- This is not backtest, trading, Paper Trading, broker API, order execution, final assets, or annual return.
