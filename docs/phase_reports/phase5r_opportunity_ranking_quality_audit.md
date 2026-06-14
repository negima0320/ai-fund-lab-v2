# Phase5-R Opportunity Ranking Quality Audit

## Summary

- readiness_status: `RANKING_QUALITY_CONFIRMED`
- promotion_ready: `False`
- best test NDCG@20 risk-adjusted: `{'strategy': 'simple_rule_baseline', 'metric': 'ndcg@20_risk_adjusted_future_return_20d', 'value': 0.601076}`
- best test Spearman risk-adjusted: `{'strategy': 'simple_rule_baseline', 'metric': 'spearman_risk_adjusted_future_return_20d', 'value': 0.09572}`
- sector_master_snapshot_proxy_warning: `True`

## Test Strategy Metrics

| strategy | spearman_risk_adjusted_future_return_20d | kendall_risk_adjusted_future_return_20d | ndcg@20_risk_adjusted_future_return_20d | precision@20_future_return_20d | top_decile_capture@20 | downside_bad_top20_rate |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.008697 | 0.006422 | 0.570633 | 0.406322 | 0.095402 | 0.436782 |
| candidate_score_baseline | -0.05768 | -0.039574 | 0.528635 | 0.375862 | 0.092529 | 0.487931 |
| market_only | 0.00133 | 0.000142 | 0.561783 | 0.399425 | 0.105747 | 0.445402 |
| market_sector | -0.052238 | -0.034468 | 0.558837 | 0.388506 | 0.105172 | 0.45977 |
| sector_only | -0.050418 | -0.033571 | 0.551751 | 0.376437 | 0.095977 | 0.46092 |
| simple_rule_baseline | 0.09572 | 0.069038 | 0.601076 | 0.447701 | 0.151149 | 0.485632 |

## Rank Bucket Summary

| strategy | split | bucket | mean_future_return_20d | downside_bad_rate |
| --- | --- | --- | --- | --- |
| baseline | test | rank_11_20 | 0.060726 | 0.441379 |
| baseline | test | rank_1_5 | 0.044614 | 0.436782 |
| baseline | test | rank_21_50 | 0.043239 | 0.472516 |
| baseline | test | rank_6_10 | 0.034074 | 0.427586 |
| candidate_score_baseline | test | rank_11_20 | 0.040834 | 0.475862 |
| candidate_score_baseline | test | rank_1_5 | -0.003456 | 0.531034 |
| candidate_score_baseline | test | rank_21_50 | 0.061085 | 0.43784 |
| candidate_score_baseline | test | rank_6_10 | 0.016014 | 0.468966 |
| market_only | test | rank_11_20 | 0.057667 | 0.451724 |
| market_only | test | rank_1_5 | 0.028852 | 0.441379 |
| market_only | test | rank_21_50 | 0.04428 | 0.466687 |
| market_only | test | rank_6_10 | 0.049489 | 0.436782 |
| market_sector | test | rank_11_20 | 0.042449 | 0.470115 |
| market_sector | test | rank_1_5 | 0.030964 | 0.445977 |
| market_sector | test | rank_21_50 | 0.053044 | 0.45691 |
| market_sector | test | rank_6_10 | 0.026146 | 0.452874 |
| sector_only | test | rank_11_20 | 0.051158 | 0.475862 |
| sector_only | test | rank_1_5 | 0.011757 | 0.436782 |
| sector_only | test | rank_21_50 | 0.05508 | 0.45609 |
| sector_only | test | rank_6_10 | 0.015307 | 0.455172 |
| simple_rule_baseline | test | rank_11_20 | 0.072442 | 0.454023 |
| simple_rule_baseline | test | rank_1_5 | 0.143511 | 0.533333 |
| simple_rule_baseline | test | rank_21_50 | 0.01034 | 0.440015 |
| simple_rule_baseline | test | rank_6_10 | 0.105669 | 0.501149 |

## Safety

- No Broker API, Paper Trading, order placement, capital allocation, promotion, or reader switch was performed.
- Future returns, max returns, drawdowns, and downside labels are evaluation-only.
