# Phase4-BI Random Date Candidate Win-rate Audit

- status: `OK`
- readiness_status: `PHASE4_FINAL_CHECK_COMPLETE`
- random_seed: `99`
- sampled_dates: `[{'sampled_year': 2025, 'target_date': '2025-06-02'}, {'sampled_year': 2024, 'target_date': '2024-06-02'}]`

## Total

- total_win_rate_5d: `1.0`
- total_win_rate_10d: `1.0`
- total_win_rate_20d: `1.0`
- candidate_vs_market_win_rate_diff_20d: `0.5`
- candidate_vs_random_win_rate_diff_20d: `0.6`

## By Date

- 2025-06-02: win5/10/20 = `1.0` / `1.0` / `1.0`
- 2024-06-02: win5/10/20 = `1.0` / `1.0` / `1.0`

## Leakage Guard

- Candidate selection used feature table columns only.
- Label/future columns were used only after candidate selection for evaluation.
- This is not backtest, trading, Paper Trading, broker API, order execution, or portfolio simulation.
