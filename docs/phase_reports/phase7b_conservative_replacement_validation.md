# Phase7-B Conservative Replacement Validation

## 1. Summary

Phase7-Bでは、Phase7-A Capital Allocation Engine の Conservative Replacement / Emergency Exit / Position sizing が、Phase5 Opportunity Top3 fixed hold の強さを壊さないかを軽量validationした。

判定。

```text
PHASE7B_CONSERVATIVE_REPLACEMENT_VALIDATION_COMPLETE
```

結論。

```text
Phase7-A default conservative replacement は、現状では Top3 fixed 20bd hold を壊している。
理由は replacement_count / replacement_rate が高く、平均保有日数が短くなりすぎるため。
```

今回のvalidationは、本格フルバックテストではない。

```text
Phase5-I forward label を使った軽量validation
full daily close path ではない
Emergency Exit は future_max_drawdown_20d による近似
```

以下は行っていない。

```text
Broker API接続
Paper Trading
実発注
live order
立花証券API呼び出し
AIによる資金配分
Kelly基準
レバレッジ
信用取引
ナンピン
Phase6 EXIT単発での自動売却
固定利確
単純なTop3脱落Replacementの本採用
REPLACE_SELL / REPLACE_BUY の同時live実行
```

## 2. Source Data

使用データ。

| item | value |
| --- | --- |
| ranked_daily | `reports/phase7_prestudy/opportunity_ranked_daily.parquet` |
| opportunity_dataset | `reports/opportunity_ai/phase5i/full_history_opportunity_dataset.parquet` |
| start_date | 2021-09-08 |
| end_date | 2026-05-15 |
| target_date_count | 1,143 |
| row_count | 56,995 |

使用した主なlabel。

```text
label__future_return_20d
label__future_max_return_20d
label__future_max_drawdown_20d
label__downside_bad_20d
```

制約。

```text
日次close pathを直接使ったexit判定ではない。
Replacementの途中売却returnは20bd forward returnの線形近似。
Emergency Exitは20bd期間内のfuture max drawdownに閾値到達があったかの近似。
したがって、結果はPhase7-C以降のfull daily path validationで再検証する必要がある。
```

## 3. Replacement Execution Constraint

Phase7-B validationでは、dry-run / validation 比較のため、論理上 same-day replacement として扱った。

ただし、実運用では必ず以下の二段階にする。

```text
SELL_FIRST_BUY_AFTER_FILL
```

実運用順序。

```text
1. REPLACE_SELL
2. 売り約定確認
3. broker snapshot / buying power / cash 再取得
4. REPLACE_BUY 再評価
5. 買付可能額・ロット・価格確認
6. 買い注文
```

Phase7-Bでは、実注文・Paper Trading・Broker連携は行っていない。

Audit flags。

| flag | value |
| --- | --- |
| replacement_same_time_live_execution_enabled | false |
| replacement_requires_sell_fill_before_buy | true |

## 4. Implemented Artifacts

作成した実装。

```text
src/ai_fund_lab_v2/capital_allocation_ai/phase7b_validation.py
scripts/run_phase7b_conservative_replacement_validation.py
tests/capital_allocation_ai/test_phase7b_conservative_replacement_validation.py
```

出力。

```text
reports/capital_allocation_ai/phase7b/validation_summary.json
reports/capital_allocation_ai/phase7b/policy_comparison.csv
reports/capital_allocation_ai/phase7b/parameter_grid_summary.csv
reports/capital_allocation_ai/phase7b/annual_summary.csv
reports/capital_allocation_ai/phase7b/trade_level_decisions.csv
reports/capital_allocation_ai/phase7b/equity_curve.csv
```

## 5. Policy Comparison

主要policy結果。

| policy | cumulative_return | annualized_return | max_drawdown | trade_count | turnover | avg_holding_days | replacement_count | replacement_rate | emergency_exit_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 90.772 | 1.635 | -0.083 | 1,236 | 264.9 | 19.66 | 0 | 0.000 | 0 |
| B_PHASE7A_DEFAULT | 58.693 | 1.403 | -0.167 | 1,521 | 326.0 | 10.02 | 1,431 | 0.941 | 0 |
| C_EMERGENCY_10 | -0.522 | -0.146 | -0.854 | 1,508 | 323.2 | 4.78 | 834 | 0.553 | 646 |
| C_EMERGENCY_12 | -0.518 | -0.145 | -0.855 | 1,365 | 292.6 | 5.26 | 838 | 0.614 | 498 |
| C_EMERGENCY_15 | -0.010 | -0.002 | -0.806 | 1,581 | 338.9 | 6.13 | 1,104 | 0.698 | 437 |
| C_EMERGENCY_20 | 3.345 | 0.370 | -0.607 | 1,663 | 356.5 | 7.64 | 1,313 | 0.790 | 284 |
| C_EMERGENCY_25 | 6.652 | 0.547 | -0.543 | 1,603 | 343.6 | 8.34 | 1,349 | 0.842 | 178 |
| D_DEFENSIVE_REVIEW | -0.010 | -0.002 | -0.806 | 1,581 | 338.9 | 6.13 | 1,104 | 0.698 | 437 |
| E_DAILY_TOP3_SYNC | 17.346 | 0.866 | -0.055 | 2,316 | 496.4 | 1.48 | 2,313 | 0.999 | 0 |

Interpretation。

```text
Baseline A が最も強い。
Phase7-A default は利益を残しているが、Baseline A から大きく劣後した。
Daily Top3 Sync は平均保有1.48営業日、replacement_rate 99.9%で高回転リスクが明確。
Emergency Exitは今回の近似ではDDを抑えず、むしろ利益と資産曲線を大きく毀損した。
```

## 6. Parameter Findings

主要パラメータ比較。

| policy | cumulative_return | max_drawdown | turnover | avg_holding_days | replacement_count | replacement_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GRID_MIN_HOLD_5 | 58.693 | -0.167 | 326.0 | 10.02 | 1,431 | 0.941 |
| GRID_MIN_HOLD_10 | 71.948 | -0.144 | 298.8 | 14.11 | 1,237 | 0.887 |
| GRID_MIN_HOLD_20 | 90.772 | -0.083 | 264.9 | 19.66 | 0 | 0.000 |
| GRID_CONFIRM_3 | 60.225 | -0.216 | 312.9 | 11.18 | 1,324 | 0.907 |
| GRID_RANK_GT_50 | 62.816 | -0.171 | 318.7 | 10.39 | 1,322 | 0.889 |

Interpretation。

```text
minimum_holding_days は非常に重要。
5営業日では早売りが多すぎる。
10営業日に伸ばすと改善するが、それでもreplacement_rateは高い。
20営業日はBaseline Aに一致し、今回の軽量validationでは最良。
confirmation_days=3 や rank>50 は多少改善するが、単独では不十分。
replacement_edge_margin 0.00-0.03 の差は小さく、rank decayが強すぎる局面では主制約になっていない。
```

## 7. Transaction Cost Sensitivity

参考比較。

| policy | transaction_cost_bps | cumulative_return | annualized_return | max_drawdown | turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| B_PHASE7A_DEFAULT | 0 | 58.693 | 1.403 | -0.167 | 326.0 |
| COST_DEFAULT_10BPS | 10 | 46.045 | 1.283 | -0.178 | 323.0 |
| COST_DEFAULT_30BPS | 30 | 34.017 | 1.143 | -0.206 | 322.0 |
| E_DAILY_TOP3_SYNC | 0 | 17.346 | 0.866 | -0.055 | 496.4 |
| COST_DAILY_SYNC_10BPS | 10 | 8.463 | 0.619 | -0.085 | 496.4 |
| COST_DAILY_SYNC_30BPS | 30 | 1.527 | 0.220 | -0.185 | 496.4 |

Interpretation。

```text
高回転policyは取引コストにかなり弱い。
Daily Top3 Sync は30bpsで cumulative_return が 17.346 から 1.527 まで低下した。
Phase7-A default もreplacementが多いため、コスト感応度は無視できない。
```

## 8. Yearly Findings

代表policyの年別結果。

| policy | year | annual_return | annual_max_drawdown | annual_trade_count | replacement_count | emergency_exit_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 2021 | 0.305 | 0.000 | 23 | 0 | 0 |
| A_FIXED_20BD | 2022 | 2.014 | -0.083 | 138 | 0 | 0 |
| A_FIXED_20BD | 2023 | 1.553 | -0.024 | 295 | 0 | 0 |
| A_FIXED_20BD | 2024 | 2.900 | -0.000 | 337 | 0 | 0 |
| A_FIXED_20BD | 2025 | 0.661 | -0.074 | 317 | 0 | 0 |
| A_FIXED_20BD | 2026 | 0.389 | -0.006 | 126 | 0 | 0 |
| B_PHASE7A_DEFAULT | 2021 | 0.147 | -0.077 | 67 | 67 | 0 |
| B_PHASE7A_DEFAULT | 2022 | 2.125 | -0.097 | 277 | 264 | 0 |
| B_PHASE7A_DEFAULT | 2023 | 1.417 | -0.036 | 341 | 329 | 0 |
| B_PHASE7A_DEFAULT | 2024 | 2.265 | -0.001 | 358 | 338 | 0 |
| B_PHASE7A_DEFAULT | 2025 | 0.509 | -0.121 | 346 | 320 | 0 |
| B_PHASE7A_DEFAULT | 2026 | 0.379 | -0.016 | 132 | 113 | 0 |
| E_DAILY_TOP3_SYNC | 2021 | 0.150 | -0.016 | 165 | 165 | 0 |
| E_DAILY_TOP3_SYNC | 2022 | 0.813 | -0.032 | 477 | 477 | 0 |
| E_DAILY_TOP3_SYNC | 2023 | 0.885 | -0.032 | 466 | 466 | 0 |
| E_DAILY_TOP3_SYNC | 2024 | 1.794 | -0.005 | 516 | 516 | 0 |
| E_DAILY_TOP3_SYNC | 2025 | 0.471 | -0.055 | 503 | 503 | 0 |
| E_DAILY_TOP3_SYNC | 2026 | 0.117 | -0.021 | 189 | 186 | 0 |

2026 weak-regime。

```text
Baseline A:
annual_return 0.389

Phase7-A default:
annual_return 0.379

Daily Top3 Sync:
annual_return 0.117
```

今回の軽量validationでは、2026でもTop3 fixed holdを崩す明確な利点は確認できなかった。

## 9. Evaluation Against Phase7-B Questions

### Phase7-A conservative replacement は Top3 fixed 20bd hold を壊していないか

壊している。

```text
cumulative_return delta:
58.693 - 90.772 = -32.080
```

### Daily Top3 Sync Replacement は高回転か

高回転である。

```text
average_holding_days:
1.48

replacement_rate:
0.999

turnover:
496.4
```

### minimum_holding_days は必要か

必要。

5営業日は短すぎる。10営業日は改善するが、まだreplacementが多い。20営業日は今回のBaselineと一致し、最も強い。

### confirmation_days は必要か

必要だが、単独では不十分。

confirmation_days=3でもreplacement_rateは0.907で高い。

### replacement_edge_margin はどの程度必要か

今回の範囲 0.00 / 0.01 / 0.02 / 0.03 では大きな差は出なかった。

rank degradationが非常に強いため、edge marginだけでは早売り抑制になりにくい。

### Emergency Exit はDDを下げるか

今回の近似では下げない。

特に -10% / -12% / -15% は利益を大きく壊した。

ただしこれは full daily close path ではないため、Phase7-Cで再検証が必要。

### max_position_weight / cash_buffer の影響

max_position_weightを下げると資金効率が下がり、final_assetsも下がった。

cash_buffer 0% / 5% の差は、今回の軽量validationでは主要因ではなかった。

## 10. Recommended Policy

Phase7-B時点の推奨。

```text
Primary:
Top3 fixed 20bd hold を基準線として維持

Replacement:
Phase7-A default のまま本採用しない

minimum_holding_days:
少なくとも10以上、現時点では20を強く比較候補に残す

Emergency Exit:
Phase7-B結果だけでは本採用しない

Defensive Review:
sell_amount = 0 のreview signalとして継続
```

次に試すべき conservative replacement。

```text
minimum_holding_days >= 10 or 20
confirmation_days >= 3
rank degradation: Candidate Top50外
replacement_edge_marginよりも、sold-then-up / missed-winner抑制を重視
replacement回数の上限またはcooldown導入
```

## 11. Phase7-C Topics

Phase7-Cで検証すべき内容。

```text
full daily close path validation
Emergency Exitの実際の到達日判定
replacement cooldown
monthly / weekly re-evaluation
minimum_holding_days 10 / 15 / 20
Candidate Top50外のみReplacement
replacement edge marginをscore差ではなくrank bucket + forward riskで再設計
transaction cost and slippage sensitivity
2026 weak-regime focused validation
sell-first / buy-after-fill 制約を反映したcash timing simulation
```

## 12. Test Result

実行コマンド。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7b_conservative_replacement_validation.py
```

結果。

```text
2 passed
```

## 13. Execution Commands

Validation実行。

```text
python3 scripts/run_phase7b_conservative_replacement_validation.py
```

テスト。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7b_conservative_replacement_validation.py
```

## 14. Audit

Validation summary。

```text
reports/capital_allocation_ai/phase7b/validation_summary.json
```

Safety flags。

| flag | value |
| --- | --- |
| broker_api_executed | false |
| paper_trading_executed | false |
| order_executed | false |
| live_order_executed | false |
| tachibana_api_called | false |
| replacement_same_time_live_execution_enabled | false |
| replacement_requires_sell_fill_before_buy | true |

Final status。

```text
PHASE7B_CONSERVATIVE_REPLACEMENT_VALIDATION_COMPLETE
```
