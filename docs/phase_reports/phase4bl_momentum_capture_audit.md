# Phase4-BL Momentum Capture Audit

- status: `OK`
- readiness_status: `PHASE4_MOMENTUM_CAPTURE_AUDIT_COMPLETE`
- momentum_capture_pass: `True`
- sampled_date_count: `50`

## Core Capture

- Top50 vs FutureReturnTop50 capture: `157` / rate `0.0628`
- Top50 vs FutureReturnTop100 capture: `252` / rate `0.0504`
- Top50 vs FutureMaxTop50 capture: `180` / rate `0.072`
- Top50 vs FutureMaxTop100 capture: `335` / rate `0.067`
- random_capture_rate_top50_future_return_top50: `0.0128`
- random_capture_rate_top50_future_max_top50: `0.0096`
- market_expected_capture_rate_top50: `0.012297`

## Key Findings

- future_max_return_capture_is_stronger_than_future_return_capture
- candidate_top50_captures_future_return_top50_above_random
- candidate_top50_captures_future_max_top50_above_random
- candidate_top50_has_some_future_top100_enrichment

## Phase5 Implications

- Phase5 should distinguish temporary price spikes from sustained 20d returns.
- This audit is not backtest/trading; use only as Opportunity AI design evidence.

## Guardrails

- Candidate selection used feature-only inputs.
- Future/label data was used only after candidate lists were created for capture evaluation.
- This is not backtest, trading, Paper Trading, broker API, order execution, portfolio simulation, annual return, or final assets.
