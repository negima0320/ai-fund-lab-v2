# Phase11 Safety Cap Investigation: MAX_EXPOSURE Impact Analysis

## Status

```text
MAX_EXPOSURE_IMPACT_ANALYSIS_COMPLETE
INVESTIGATION_ONLY
NO_BACKTEST_RERUN
NO_PARAMETER_CHANGE
NO_BROKER_CONNECTION_NO_ORDER_NO_AI_RETRAINING
```

## Conclusion

MAX_EXPOSUREによる収益差の直接原因は、`max_total_exposure=850000` が固定金額として5年間効き続けたことです。

これはSafety Guardとしては機械的に正しくBLOCKしていますが、資産が増えた後も85万円上限のままなので、portfolio risk ratioとしては厳しすぎます。市場下落やSystem Emergencyではありません。

## Observed Parameters

- max_positions: 8
- max_total_exposure: 850000 fixed absolute JPY
- cash_buffer_guard_amount: 50000 in Safety pre-order
- cap5_cash_buffer_rate: 0.05
- cap5_max_position_weight: 0.20

CAP5側は `cash_buffer=5%`、`max_position_weight=20%` ですが、Safety pre-order側のMAX_EXPOSUREは `850000円` 固定です。

## MAX_EXPOSURE Block Classification

- blocked_buy_orders: 4154
- blocked_sell_orders: 0
- unique_blocked_date_issue_pairs: 4154
- blocked_days_count: 1004
- blocked_reason_codes: {'MAX_EXPOSURE_EXCEEDED': 4154, 'CASH_BUFFER_VIOLATION': 3}

Top blocked issue codes:

- 58030: 89
- 70030: 83
- 33500: 82
- 13600: 81
- 65260: 63
- 67400: 62
- 14590: 62
- 89180: 61
- 70130: 61
- 95010: 55
- 70120: 53
- 36970: 53
- 67230: 51
- 70140: 45
- 91070: 43

Top blocked dates:

- 2022-06-27: 5
- 2022-11-09: 5
- 2022-11-14: 5
- 2022-11-18: 5
- 2022-11-28: 5
- 2022-12-13: 5
- 2022-12-23: 5
- 2023-01-04: 5
- 2023-01-06: 5
- 2023-01-10: 5
- 2023-01-26: 5
- 2023-01-27: 5
- 2023-02-09: 5
- 2023-02-10: 5
- 2023-02-13: 5

## Average Holding Context

- average_position_count: 3.40184
- median_position_count: 3.0
- max_position_count: 8
- average_cash_ratio: 0.564927
- median_cash_ratio: 0.598293
- average_exposure_ratio: 0.435073
- median_exposure_ratio: 0.401707
- max_exposure_ratio: 0.996948

## Context At MAX_EXPOSURE Blocks

- average_position_count_at_block: 2.656957
- median_position_count_at_block: 2.0
- max_position_count_at_block: 8
- average_cash_remaining: 2150362.09
- median_cash_remaining: 2254700.0
- average_cash_ratio: 0.625686
- median_cash_ratio: 0.683025
- average_exposure: 1149153.79
- median_exposure: 871300.0
- average_exposure_ratio: 0.374314
- median_exposure_ratio: 0.316975
- exposure_ge_850000_count: 2227
- exposure_lt_850000_count: 1927
- cash_gt_50000_count: 4154
- cash_gt_200000_count: 4117
- position_count_lt_8_count: 4113
- position_count_eq_8_count: 41
- position_count_lt_5_count: 3547

Position count distribution at block:

- 1 positions: 1356
- 2 positions: 886
- 3 positions: 792
- 4 positions: 513
- 5 positions: 322
- 6 positions: 165
- 7 positions: 79
- 8 positions: 41

Interpretation:

- `8銘柄保有 -> 9銘柄目を止めた` というより、中央値2銘柄・平均2.66銘柄でも固定85万円exposureに触れてBUYが止まっています。
- cash不足ではありません。MAX_EXPOSUREブロック4154件すべてでSafety cash buffer 5万円を超えるcashが残っていました。
- 4113件はposition_count < 8で発生しており、max_positions満杯による自然な停止ではありません。

## Follow-Up Returns Of Blocked BUY Candidates

### 1d

- count: 4154
- mean: 0.017038
- median: 0.0
- p10: -0.045455
- p90: 0.095471
- positive_count: 2046
- gain_ge_5pct_count: 702
- gain_ge_10pct_count: 400
- loss_le_minus_5pct_count: 350
- loss_le_minus_10pct_count: 68

### 5d

- count: 4154
- mean: 0.037409
- median: 0.009208
- p10: -0.090909
- p90: 0.185004
- positive_count: 2231
- gain_ge_5pct_count: 1320
- gain_ge_10pct_count: 796
- loss_le_minus_5pct_count: 873
- loss_le_minus_10pct_count: 354

### 20d

- count: 4154
- mean: 0.091047
- median: 0.03186
- p10: -0.172426
- p90: 0.401294
- positive_count: 2372
- gain_ge_5pct_count: 1896
- gain_ge_10pct_count: 1460
- loss_le_minus_5pct_count: 1260
- loss_le_minus_10pct_count: 837

### 45d

- count: 4034
- mean: 0.098672
- median: 0.024777
- p10: -0.235489
- p90: 0.486062
- positive_count: 2221
- gain_ge_5pct_count: 1835
- gain_ge_10pct_count: 1522
- loss_le_minus_5pct_count: 1398
- loss_le_minus_10pct_count: 1070

### Within 45 Trading Days Path

- count: 4154
- max_gain_ge_8pct_count: 3013
- max_gain_ge_15pct_count: 2315
- max_gain_ge_30pct_count: 1378
- min_loss_le_minus_8pct_count: 2255
- min_loss_le_minus_15pct_count: 1501
- min_loss_le_minus_20pct_count: 1026
- missed_profit_candidate_count: 3013
- protected_loss_candidate_count: 2255
- both_profit_and_loss_path_count: 1236
- mean_max_45d_return: 0.350047
- mean_min_45d_return: -0.121881

Interpretation:

- 45営業日以内に+8%以上を一度でも付けたブロック候補は `3013` 件で、利益機会をかなり逃しています。
- 一方で45営業日以内に-8%以上を一度でも付けた候補も `2255` 件あり、損失回避効果もあります。
- ただしSafety OFFの最終損益・年率が大きく上回り、最大DD差は小さいため、今回の固定capは収益機会の抑制が優勢でした。

## MAX_POSITIONS Projection

現在のMAX_EXPOSUREブロックは `max_position_count` ではなく `max_total_exposure=850000` で発生しています。したがって、`max_positions` だけを8/10/12/15へ変更しても、固定exposure capを同時に見直さない限りBLOCK件数はほぼ減りません。

### max_positions=8

- blocked_orders_with_position_count_ge_limit: 41
- blocked_orders_below_position_limit: 4113
- estimated_block_reduction_from_position_limit_only: 0
- note: Current MaxExposureGuard block is max_total_exposure, not max_position_count; changing max_positions alone does not remove these exposure blocks.

### max_positions=10

- blocked_orders_with_position_count_ge_limit: 0
- blocked_orders_below_position_limit: 4154
- estimated_block_reduction_from_position_limit_only: 0
- note: Current MaxExposureGuard block is max_total_exposure, not max_position_count; changing max_positions alone does not remove these exposure blocks.

### max_positions=12

- blocked_orders_with_position_count_ge_limit: 0
- blocked_orders_below_position_limit: 4154
- estimated_block_reduction_from_position_limit_only: 0
- note: Current MaxExposureGuard block is max_total_exposure, not max_position_count; changing max_positions alone does not remove these exposure blocks.

### max_positions=15

- blocked_orders_with_position_count_ge_limit: 0
- blocked_orders_below_position_limit: 4154
- estimated_block_reduction_from_position_limit_only: 0
- note: Current MaxExposureGuard block is max_total_exposure, not max_position_count; changing max_positions alone does not remove these exposure blocks.

## Safety ON/OFF Impact

- orders_blocked_by_safety: 4156
- max_exposure_blocks: 4154
- cash_buffer_blocks: 5
- max_exposure_block_share_of_all_safety_blocks: 0.999519
- system_emergency_blocks: 0
- non_blocking_review_order_count: 306
- blocking_review_order_count: 4156
- trade_count_gap_vs_safety_off: 904
- buy_fill_gap_vs_safety_off: 455
- sell_fill_gap_vs_safety_off: 449

## Assessment

- direct_cause: MAX_EXPOSURE_EXCEEDED was caused by a fixed absolute max_total_exposure=850000 JPY in pre-order Safety checks. The cap did not scale with final/evolving equity.
- not_cash_shortage: All 4154 MAX_EXPOSURE-blocked BUY orders had cash above 50000 JPY; 4117 had cash above 200000 JPY.
- not_position_count_full: 4113 of 4154 MAX_EXPOSURE-blocked BUY orders occurred while position_count was below 8; median position_count at block was 2.
- actually_at_fixed_cap_count: 2227
- below_fixed_cap_but_proposed_would_exceed_count: 1927
- missed_profit_candidate_count: 3013
- protected_loss_candidate_count: 2255
- strictness_assessment: Too strict for a compounding paper account if intended as a portfolio risk ratio. It is mechanically valid as a hard absolute cap, but economically inconsistent with growing equity.
- tuning_recommendation: Keep Safety MAX_EXPOSURE, but tune it as a ratio of current equity/buying power and separately preserve per-position and cash-buffer controls. Candidate for Phase12 parameter review, not a system emergency condition.
- requires_fix_before_phase12: No for Demo operation mechanics; yes before treating long-run return as production-quality because exposure cap materially changes capital deployment.

## Data Use / Prohibitions

この調査は既存のPhase11-Z-Fix-G成果物と既存quote artifactの静的集計のみです。修正実装、パラメータ変更、1年/5年再実行、Broker API接続、Demo/Production発注、AI再学習、Safety結果のAI学習投入は行っていません。

## Result

```text
MAX_EXPOSURE_IMPACT_ANALYSIS_COMPLETE
MAX_EXPOSURE_FIXED_ABSOLUTE_CAP_IS_PRIMARY_RETURN_DRAG
MAX_EXPOSURE_TUNING_RECOMMENDED
NO_BROKER_CONNECTION_NO_ORDER_NO_AI_RETRAINING
```
