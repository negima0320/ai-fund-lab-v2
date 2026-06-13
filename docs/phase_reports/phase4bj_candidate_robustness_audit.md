# Phase4-BJ Candidate AI Robustness Audit

- status: `OK`
- readiness_status: `PHASE4_ROBUSTNESS_TEST_COMPLETE_WITH_WEAKNESSES`
- sampled_date_count: `50`
- total_candidate_count_top50: `2500`

## Top50 Totals

- win_rate_5d/10d/20d: `0.41` / `0.4336` / `0.4156`
- avg_return_20d: `-0.003581`
- avg_future_max_return_20d: `0.137238`
- downside_bad_rate_20d: `0.470522`
- top_decile_rate_20d: `0.24369`

## Analysis Status

- score_decile_analysis_status: `OK`
- score_monotonicity_status: `OK`
- market_regime_analysis_status: `SKIPPED`
- sector_analysis_status: `SKIPPED`

## Leakage Guard

- Candidate selection used feature table columns only.
- Label/future data was joined only after candidate lists were created for evaluation.
- This is not backtest, trading, Paper Trading, broker API, order execution, portfolio simulation, annual return, or final assets.

## Key Findings

- top50_future_max_return_beats_market_on_sampled_dates
- top50_20d_win_rate_lags_market
- top50_downside_bad_rate_is_above_market
- top50_top_decile_rate_beats_market

## Phase5 Implications

- Phase5 should add downside and confirmation filters before any opportunity ranking.
- Phase5 should penalize downside_bad and drawdown-prone candidates.
