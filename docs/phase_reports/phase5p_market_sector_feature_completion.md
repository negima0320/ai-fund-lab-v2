# Phase5-P Market / Sector Feature Completion

## Summary

- readiness_status: `PHASE5P_MARKET_SECTOR_IMPROVED`
- promotion_ready: `False`
- feature count before / after: `16` / `32`
- added market / sector feature count: `8` / `8`
- leakage_status: `OK`
- full history rows: `56995`
- sector master snapshot proxy warning: `True`

## Added Features

- market: `feature__market_breadth_20d`, `feature__market_breadth_5d`, `feature__market_downtrend_flag`, `feature__market_ma_5_20_ratio`, `feature__market_return_20d`, `feature__market_return_5d`, `feature__market_risk_flag`, `feature__market_volatility_20d`
- sector: `feature__market_downtrend_context`, `feature__sector_breadth_20d`, `feature__sector_momentum_flag`, `feature__sector_rank_20d`, `feature__sector_return_20d`, `feature__sector_return_5d`, `feature__sector_weak_flag`, `feature__stock_vs_sector_return_20d`

## Baseline Comparison

{
  "any_topn_improved": true,
  "combined_validation": {
    "test": {
      "top10": {
        "baseline_mean_future_return_20d": 0.039344,
        "delta": -0.010789,
        "improved": false,
        "phase5p_mean_future_return_20d": 0.028555
      },
      "top20": {
        "baseline_mean_future_return_20d": 0.050035,
        "delta": -0.014533,
        "improved": false,
        "phase5p_mean_future_return_20d": 0.035502
      },
      "top5": {
        "baseline_mean_future_return_20d": 0.044614,
        "delta": -0.01365,
        "improved": false,
        "phase5p_mean_future_return_20d": 0.030964
      }
    },
    "validation": {
      "top10": {
        "baseline_mean_future_return_20d": 0.048136,
        "delta": 0.000714,
        "improved": true,
        "phase5p_mean_future_return_20d": 0.04885
      },
      "top20": {
        "baseline_mean_future_return_20d": 0.044093,
        "delta": 0.001743,
        "improved": true,
        "phase5p_mean_future_return_20d": 0.045836
      },
      "top5": {
        "baseline_mean_future_return_20d": 0.061718,
        "delta": -0.017111,
        "improved": false,
        "phase5p_mean_future_return_20d": 0.044607
      }
    }
  },
  "failure_date_2022_01_13_improved": true,
  "phase": "Phase5-P",
  "random_date_outcome": {
    "baseline_2022_01_13_opportunity_top5_mean_return_20bd": -0.14451,
    "baseline_effective_dates": [
      "2021-09-30",
      "2023-10-10",
      "2024-04-17",
      "2025-04-08"
    ],
    "date_2022_01_13_improved": true,
    "phase5p_2022_01_13_opportunity_top5_mean_return_20bd": -0.079166,
    "phase5p_effective_dates": [
      "2021-09-30",
      "2022-01-13",
      "2023-10-10",
      "2024-04-17",
      "2025-04-08"
    ],
    "phase5p_minus_baseline_2022_01_13": 0.065344
  }
}

## Safety

- No Broker API, Paper Trading, order placement, capital allocation, promotion, or reader switch was performed.
- Future outcomes remain evaluation-only and are not feature columns.
- Fundamental features remain outside Phase5-P scope.
- Sector strength uses the local J-Quants listed issue master snapshot available in artifacts; historical listed-master snapshots were not present, so this is recorded as a source limitation.
