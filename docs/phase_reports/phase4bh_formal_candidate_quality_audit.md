# Phase4-BH Formal Candidate Quality Audit

- status: `OK`
- readiness_status: `PHASE4_COMPLETE`
- candidate_quality_pass: `True`

## Top K Quality

- validation_top50_top_decile_rate: `0.48`
- test_top50_top_decile_rate: `0.48`
- validation_top50_mean_future_max_return_20d: `0.12`
- test_top50_mean_future_max_return_20d: `0.12`
- validation_top50_downside_bad_rate: `0.0`
- test_top50_downside_bad_rate: `0.0`

## Baseline

- validation_market_baseline: `{'row_count': 240, 'top_decile_rate': 0.1, 'mean_future_return_5d': 0.005, 'mean_future_return_10d': 0.01, 'mean_future_return_20d': 0.015, 'mean_future_max_return_20d': 0.075, 'mean_future_max_drawdown_20d': -0.055, 'downside_bad_rate': 0.5, 'precision': 0.5}`
- test_market_baseline: `{'row_count': 240, 'top_decile_rate': 0.1, 'mean_future_return_5d': 0.005, 'mean_future_return_10d': 0.01, 'mean_future_return_20d': 0.015, 'mean_future_max_return_20d': 0.075, 'mean_future_max_drawdown_20d': -0.055, 'downside_bad_rate': 0.5, 'precision': 0.5}`

## Strengths

- top50_top_decile_rate_beats_market_in_validation_and_test
- top50_future_max_return_beats_market_in_validation_and_test
- top50_downside_bad_rate_not_worse_than_market
- score_monotonicity_is_acceptable

## Weaknesses


## Scope Guard

- Candidate Quality Audit only.
- No retraining, feature addition, label change, inference rerun, backtest, trading, Paper Trading, broker API, promotion, reader switch, or order execution.
