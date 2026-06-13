# Phase4-BK Winner / Loser Case Study

- status: `OK`
- readiness_status: `PHASE4_WINNER_LOSER_CASE_STUDY_COMPLETE`
- best_case_count: `50`
- worst_case_count: `50`
- leakage_audit_status: `OK`

## Score / Return Summary

- best_avg_candidate_score: `0.716188`
- worst_avg_candidate_score: `0.718102`
- best_avg_return_20d: `0.97158`
- worst_avg_return_20d: `-0.430872`
- best_avg_future_max_return_20d: `1.336325`
- worst_avg_future_max_return_20d: `0.016231`
- best_avg_future_max_drawdown_20d: `0.015987`
- worst_avg_future_max_drawdown_20d: `-0.494535`

## Best Preview

- 2021 2021-09-28 39360 rank=5 score=0.731184 return20d=2.023121
- 2021 2021-10-01 39360 rank=13 score=0.714473 return20d=3.184362
- 2021 2021-09-30 39360 rank=11 score=0.713518 return20d=2.952518
- 2021 2021-10-26 78090 rank=34 score=0.704015 return20d=0.88465
- 2021 2021-11-01 21580 rank=49 score=0.703789 return20d=0.117965
- 2021 2021-09-14 39360 rank=1 score=0.734163 return20d=1.042947
- 2021 2021-10-26 31210 rank=48 score=0.699795 return20d=0.962637
- 2021 2021-10-26 29830 rank=35 score=0.703907 return20d=0.754618
- 2021 2021-10-21 21580 rank=15 score=0.714373 return20d=0.88059
- 2021 2021-10-21 45820 rank=9 score=0.722611 return20d=0.840249

## Worst Preview

- 2021 2021-11-30 39360 rank=16 score=0.727431 return20d=-0.661538 drawdown20d=-0.664835
- 2021 2021-12-21 70490 rank=44 score=0.708362 return20d=-0.489372 drawdown20d=-0.509145
- 2021 2021-09-30 31330 rank=30 score=0.700959 return20d=-0.364764 drawdown20d=-0.473945
- 2021 2021-10-01 31330 rank=34 score=0.701392 return20d=-0.38191 drawdown20d=-0.467337
- 2021 2021-09-28 31330 rank=9 score=0.719249 return20d=-0.30402 drawdown20d=-0.467337
- 2021 2021-09-28 78680 rank=7 score=0.722642 return20d=-0.375985 drawdown20d=-0.39903
- 2021 2021-11-01 66980 rank=3 score=0.739616 return20d=-0.367081 drawdown20d=-0.367081
- 2021 2021-09-14 61950 rank=5 score=0.717447 return20d=-0.362934 drawdown20d=-0.362934
- 2021 2021-10-01 44270 rank=1 score=0.733898 return20d=-0.362336 drawdown20d=-0.362336
- 2021 2021-12-21 38560 rank=35 score=0.713533 return20d=-0.347727 drawdown20d=-0.354342

## Feature Compare

- liquidity_avg_volume_20d: best_mean=4981520.63 worst_mean=4125461.08 diff=856059.55
- price_momentum_return_5d: best_mean=0.058049 worst_mean=-0.008122 diff=0.066171
- price_momentum_return_20d: best_mean=0.16813 worst_mean=0.071457 diff=0.096673
- price_momentum_return_60d: best_mean=1.043382 worst_mean=0.422096 diff=0.621286
- volatility_return_std_20d: best_mean=0.055171 worst_mean=0.051299 diff=0.003872
- trend_close_over_ma_20d: best_mean=0.064366 worst_mean=0.004657 diff=0.059709
- trend_ma_5_20_ratio: best_mean=0.028958 worst_mean=0.01575 diff=0.013208
- trend_ma_20_60_ratio: best_mean=0.085365 worst_mean=0.025443 diff=0.059922
- volume_momentum_ratio_5d: best_mean=1.141517 worst_mean=1.190494 diff=-0.048977
- volume_momentum_ratio_1d_20d: best_mean=1.095755 worst_mean=1.180032 diff=-0.084277
- candidate_score: best_mean=0.716188 worst_mean=0.718102 diff=-0.001914

## Phase5 Hypotheses

- Treat Candidate score as an upstream prior, not a buy decision.
- Add downside and drawdown filters before opportunity ranking.
- Candidate score alone does not separate winners from losers in this sample; add confirmation features.
- Best cases show higher liquidity_avg_volume_20d; consider as Phase5 scoring/filter hypothesis.
- Best cases show higher price_momentum_return_60d; consider as Phase5 scoring/filter hypothesis.
- Best cases show higher price_momentum_return_20d; consider as Phase5 scoring/filter hypothesis.
- Best cases show lower volume_momentum_ratio_1d_20d; consider as Phase5 scoring/filter hypothesis.
- Best cases show higher price_momentum_return_5d; consider as Phase5 scoring/filter hypothesis.

## Guardrails

- Candidate selection was already completed in Phase4-BJ using feature-only inputs.
- Future/label columns are used here only for post-selection case analysis.
- No backtest, trading, Paper Trading, broker API, order, promotion, or reader switch is executed.
