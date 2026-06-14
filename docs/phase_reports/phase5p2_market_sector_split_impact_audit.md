# Phase5-P2 Market / Sector Split Impact Audit

## Summary

- readiness_status: `MARKET_AND_SECTOR_IMPROVES`
- promotion_ready: `False`
- sector_master_snapshot_proxy_warning: `True`
- likely cause: Full-history test degradation is strongest in `sector_only` by average TopN return delta, while random-date failure-day improvement is strongest in `market_sector`. This suggests market/sector context helps specific adverse dates but may dilute broad test ranking.

## Strategy Summary

| strategy | split | selection | mean_return_20d | future_max_return_20d | downside_bad_rate | max_drawdown_20d | win_rate_20d | delta_mean_return_20d_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | validation | top5 | 0.061718 | 0.198058 | 0.397531 | -0.094117 | 0.533333 | 0.0 |
| baseline | validation | top10 | 0.048136 | 0.176844 | 0.4 | -0.095571 | 0.514403 | 0.0 |
| baseline | validation | top20 | 0.044093 | 0.167511 | 0.396502 | -0.095119 | 0.511934 | 0.0 |
| baseline | test | top5 | 0.044614 | 0.215406 | 0.436782 | -0.094812 | 0.478161 | 0.0 |
| baseline | test | top10 | 0.039344 | 0.199086 | 0.432184 | -0.096932 | 0.485057 | 0.0 |
| baseline | test | top20 | 0.050035 | 0.197042 | 0.436782 | -0.101905 | 0.493103 | 0.0 |
| market_only | validation | top5 | 0.066714 | 0.208865 | 0.421399 | -0.098951 | 0.493004 | 0.004996 |
| market_only | validation | top10 | 0.060448 | 0.191005 | 0.403292 | -0.09708 | 0.509877 | 0.012312 |
| market_only | validation | top20 | 0.048941 | 0.174483 | 0.399588 | -0.096673 | 0.508848 | 0.004848 |
| market_only | test | top5 | 0.028852 | 0.18687 | 0.441379 | -0.102332 | 0.48046 | -0.015762 |
| market_only | test | top10 | 0.039171 | 0.192334 | 0.43908 | -0.1046 | 0.498851 | -0.000173 |
| market_only | test | top20 | 0.048419 | 0.198311 | 0.445402 | -0.107273 | 0.494253 | -0.001616 |
| sector_only | validation | top5 | 0.064394 | 0.198302 | 0.403292 | -0.098191 | 0.522634 | 0.002676 |
| sector_only | validation | top10 | 0.057524 | 0.188198 | 0.407819 | -0.097442 | 0.515226 | 0.009388 |
| sector_only | validation | top20 | 0.051829 | 0.180002 | 0.401646 | -0.096907 | 0.515021 | 0.007736 |
| sector_only | test | top5 | 0.011757 | 0.167531 | 0.436782 | -0.106846 | 0.475862 | -0.032857 |
| sector_only | test | top10 | 0.013532 | 0.165255 | 0.445977 | -0.110754 | 0.465517 | -0.025812 |
| sector_only | test | top20 | 0.032345 | 0.181241 | 0.46092 | -0.109921 | 0.466667 | -0.01769 |
| market_sector | validation | top5 | 0.044607 | 0.181967 | 0.403292 | -0.096245 | 0.503704 | -0.017111 |
| market_sector | validation | top10 | 0.04885 | 0.178372 | 0.395885 | -0.097042 | 0.514403 | 0.000714 |
| market_sector | validation | top20 | 0.045836 | 0.171003 | 0.396914 | -0.097294 | 0.512757 | 0.001743 |
| market_sector | test | top5 | 0.030964 | 0.18775 | 0.445977 | -0.105656 | 0.487356 | -0.01365 |
| market_sector | test | top10 | 0.028555 | 0.181466 | 0.449425 | -0.109558 | 0.482759 | -0.010789 |
| market_sector | test | top20 | 0.035502 | 0.187302 | 0.45977 | -0.111401 | 0.477586 | -0.014533 |

## Random Date Comparison

| strategy | sampled_target_dates | effective_date_count | effective_dates | newly_effective_dates_vs_baseline | opportunity_top5_2022_01_13_mean_return_20bd | delta_2022_01_13_vs_baseline | date_2022_01_13_improved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2021-09-30\|2022-01-13\|2023-10-10\|2024-04-17\|2025-04-08 | 4 | 2021-09-30\|2023-10-10\|2024-04-17\|2025-04-08 |  | -0.14451 | 0.0 | False |
| market_only | 2021-09-30\|2022-01-13\|2023-10-10\|2024-04-17\|2025-04-08 | 3 | 2021-09-30\|2023-10-10\|2024-04-17 |  | -0.103994 | 0.040516 | True |
| sector_only | 2021-09-30\|2022-01-13\|2023-10-10\|2024-04-17\|2025-04-08 | 4 | 2021-09-30\|2023-10-10\|2024-04-17\|2025-04-08 |  | -0.126065 | 0.018445 | True |
| market_sector | 2021-09-30\|2022-01-13\|2023-10-10\|2024-04-17\|2025-04-08 | 5 | 2021-09-30\|2022-01-13\|2023-10-10\|2024-04-17\|2025-04-08 | 2022-01-13 | -0.079166 | 0.065344 | True |

## Safety

- No Broker API, Paper Trading, order placement, capital allocation, promotion, or reader switch was performed.
- Future outcomes remain evaluation-only and are not feature columns.
- Sector strength uses the local J-Quants listed issue master snapshot proxy, so sector-only results should be treated cautiously.
