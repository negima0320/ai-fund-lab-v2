# Phase4-AT Candidate Feature Quality Audit

## Result

- status: OK
- readiness_status: `READY_FOR_FEATURE_EXPANSION_PLAN`
- feature_count: 4
- constant_feature_count: 4
- near_constant_feature_count: 4
- high_null_feature_count: 2
- all_null_feature_count: 2

## Likely Root Cause

Training-period features are mostly missing or constant because Phase4-AO labels cover early target_dates where 60-day lookback features cannot be calculated from the current 60-business-day real_runtime history.

## Constant Features

- feature__missing_flags_insufficient_history
- feature__missing_flags_price
- feature__price_momentum_return_5d
- feature__volume_momentum_ratio_5d

## High Null Features

- feature__price_momentum_return_5d
- feature__volume_momentum_ratio_5d

## Missing Design Features

- fundamental_disclosed_days_ago
- fundamental_equity_ratio
- fundamental_freshness_flag
- fundamental_operating_margin
- fundamental_operating_profit_growth_rate
- fundamental_roe
- fundamental_sales_growth_rate
- liquidity_avg_turnover_20d
- liquidity_avg_volume_20d
- liquidity_low_liquidity_flag
- market_regime_label
- market_regime_risk_flag
- market_regime_topix_ma_5_20_ratio
- market_regime_topix_return_20d
- market_regime_topix_return_5d
- missing_flags_fundamental
- missing_flags_market
- missing_flags_sector
- missing_flags_volume
- price_momentum_return_20d
- price_momentum_return_60d
- relative_strength_stock_vs_market_20d
- sector_relative_momentum_flag
- sector_relative_rank_20d
- sector_relative_return_20d
- sector_relative_stock_vs_sector_return_20d
- trend_breakout_strength
- trend_close_to_20d_high
- trend_close_to_60d_high
- trend_ma_20_60_ratio
- trend_ma_5_20_ratio
- trend_new_20d_high_flag
- trend_new_60d_high_flag
- universe_eligibility_delisting_risk_flag
- universe_eligibility_insufficient_history_flag
- universe_eligibility_listed_flag
- universe_eligibility_supervision_flag
- volatility_20d
- volume_momentum_ratio_1d_20d
- volume_momentum_ratio_5d_20d
- volume_momentum_surge_flag
- volume_momentum_trend_20d

## Recommended Fix Plan

- Plan Phase4-AU Candidate Feature Expansion before retraining.
- Extend normalized history so each label target_date has enough prior lookback rows.
- Generate historical features only for target_dates with sufficient lookback, or mark early dates out of training.
- Add catalog-defined missing features such as high-breakout, liquidity turnover, market regime, sector relative, and quality features.
- Add feature quality gates before training: non-null rate, unique value count, variance, and target_date coverage.
- Keep label, training, inference, backtest, and trading unchanged until feature quality is fixed.

## Scope Guard

- This phase audits feature quality only.
- It does not add features, change labels, retrain, run inference, backtest, or trade.
