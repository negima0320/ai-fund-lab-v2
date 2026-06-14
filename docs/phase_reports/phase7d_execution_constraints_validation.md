# Phase7-D Realistic Execution Constraint Validation

## 1. Summary

Phase7-Dでは、Phase7-Cで強く見えた Candidate Top50外 only Replacement を、より現実的な売買制約で再検証した。

判定。

```text
PHASE7D_EXECUTION_CONSTRAINT_VALIDATION_COMPLETE
```

今回反映した制約。

```text
SELL_FIRST_BUY_AFTER_FILL
100株単位
min_position_value
cash_buffer
max_position_weight
transaction cost
slippage
replacement cooldown
replacement cap per month
weekly / monthly reevaluation
```

以下は行っていない。

```text
Broker API接続
Paper Trading
実発注
live order
立花証券API呼び出し
新規J-Quants API取得
AIによる資金配分
Kelly基準
レバレッジ
信用取引
ナンピン
Phase6 EXIT単発での自動売却
固定利確
単純なTop3脱落Replacementの本採用
REPLACE_SELL / REPLACE_BUY の同時live実行
future data の decision 利用
backtest outcome の decision 利用
```

## 2. Source Data

Opportunity rank。

```text
reports/phase7_prestudy/opportunity_ranked_daily.parquet
```

Daily close path。

```text
.runtime/data/raw/jquants/equities_bars_daily/responses/
```

新規J-Quants API取得は行っていない。

| item | value |
| --- | ---: |
| ranked_start_date | 2021-09-08 |
| ranked_end_date | 2026-05-15 |
| ranked_row_count | 56,995 |
| price_start_date | 2021-09-08 |
| price_end_date | 2026-06-12 |
| price_row_count | 2,416,234 |

## 3. Leakage Guard

Leakage audit。

| flag | value |
| --- | --- |
| status | PASS |
| no_future_data_in_decision | true |
| backtest_outcome_used_in_decision | false |
| future_price_used_in_decision | false |
| future_rank_used_in_decision | false |
| decision_evaluation_separated | true |

Audit artifact。

```text
reports/capital_allocation_ai/phase7d/leakage_audit.json
```

## 4. Implemented Artifacts

作成した実装。

```text
src/ai_fund_lab_v2/capital_allocation_ai/phase7d_execution_constraints_validation.py
scripts/run_phase7d_execution_constraints_validation.py
tests/capital_allocation_ai/test_phase7d_execution_constraints_validation.py
```

出力。

```text
reports/capital_allocation_ai/phase7d/validation_summary.json
reports/capital_allocation_ai/phase7d/policy_comparison.csv
reports/capital_allocation_ai/phase7d/execution_constraint_comparison.csv
reports/capital_allocation_ai/phase7d/transaction_cost_comparison.csv
reports/capital_allocation_ai/phase7d/lot_size_summary.csv
reports/capital_allocation_ai/phase7d/annual_summary.csv
reports/capital_allocation_ai/phase7d/trade_level_decisions.csv
reports/capital_allocation_ai/phase7d/equity_curve.csv
reports/capital_allocation_ai/phase7d/leakage_audit.json
```

## 5. Execution Constraint Comparison

主要結果。

| policy | cumulative_return | annualized_return | max_drawdown | trade_count | avg_hold | replacement_count | replacement_rate | lot_skip | min_value_skip | cash_drag |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 216.474 | 2.107 | -0.343 | 662 | 20.00 | 0 | 0.000 | 278 | 1,418 | 0.072 |
| C3_BASE_MIN10 | 1173.981 | 3.433 | -0.403 | 614 | 12.90 | 537 | 0.875 | 160 | 766 | 0.172 |
| C3_MIN15 | 1441.598 | 3.629 | -0.401 | 563 | 17.06 | 449 | 0.798 | 169 | 948 | 0.135 |
| C3_MIN20 | 216.474 | 2.107 | -0.343 | 662 | 20.00 | 0 | 0.000 | 278 | 1,418 | 0.072 |
| C3_MIN10_COOLDOWN5 | 412.276 | 2.557 | -0.446 | 654 | 19.14 | 203 | 0.310 | 270 | 1,024 | 0.093 |
| C3_MIN10_COOLDOWN10 | 154.089 | 1.894 | -0.425 | 677 | 19.55 | 102 | 0.151 | 305 | 1,158 | 0.079 |
| C3_WEEKLY_REEVAL | 343.901 | 2.424 | -0.440 | 564 | 17.02 | 336 | 0.596 | 251 | 990 | 0.124 |
| C3_MONTHLY_REEVAL | 103.446 | 1.663 | -0.467 | 479 | 18.79 | 157 | 0.328 | 172 | 1,796 | 0.101 |
| C3_CAP_MONTH_1 | 63.981 | 1.409 | -0.353 | 649 | 19.81 | 57 | 0.088 | 305 | 1,217 | 0.086 |
| C3_CAP_MONTH_2 | 85.436 | 1.559 | -0.440 | 532 | 19.39 | 114 | 0.214 | 205 | 1,642 | 0.093 |
| C3_MIN10_SAME_DAY_REFERENCE | 936.192 | 3.227 | -0.308 | 875 | 12.87 | 760 | 0.869 | 280 | 1,041 | 0.070 |

Findings。

```text
C3_MIN10 / C3_MIN15 の優位は、100株単位・min_position_value・sell-first制約後も残った。
ただし replacement_rate は 0.875 / 0.798 と高い。
C3_MIN15 はC3_MIN10より保有日数が長く、replacement_countが減り、累積リターンも上回った。
C3_MIN20 は実質Baselineと同じ挙動になった。
cooldown / monthly / cap は回転を抑えるが、今回の設定ではリターンも大きく削った。
```

## 6. Lot Size / Min Position Value

100株単位とmin position valueによる制約。

| policy | lot_skip | min_value_skip | uninvested_cash_due_to_lot_size | cash_drag | capital_utilization |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 278 | 1,418 | 104,421,144 | 0.072 | 0.928 |
| C3_BASE_MIN10 | 160 | 766 | 83,109,937 | 0.172 | 0.828 |
| C3_MIN15 | 169 | 948 | 73,826,688 | 0.135 | 0.865 |
| C3_MIN10_COOLDOWN5 | 270 | 1,024 | 96,911,412 | 0.093 | 0.907 |
| C3_CAP_MONTH_1 | 305 | 1,217 | 95,865,123 | 0.086 | 0.914 |
| MAX_WEIGHT_10 | 277 | 206 | 115,864,386 | 0.287 | 0.713 |
| MAX_WEIGHT_15 | 209 | 555 | 100,605,285 | 0.189 | 0.811 |

Interpretation。

```text
100株単位による買い逃しは無視できない。
max_position_weightを下げるとcash_dragが増え、資金効率が落ちた。
ただしmax_position_weight 10%ではDDが抑えられる傾向もある。
```

## 7. Transaction Cost / Slippage

参考比較。

| policy | transaction_cost_bps | slippage_bps | cumulative_return | annualized_return | max_drawdown | transaction_cost_paid | slippage_cost_paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| COST_C3_MIN10_0BPS | 0 | 0 | 1173.981 | 3.433 | -0.403 | 0 | 0 |
| COST_C3_MIN10_10BPS | 10 | 0 | 2329.867 | 4.122 | -0.367 | 66,220,570 | 0 |
| COST_C3_MIN10_30BPS | 30 | 0 | 2131.638 | 4.027 | -0.405 | 180,811,282 | 0 |
| SLIPPAGE_C3_MIN10_0BPS | 0 | 0 | 1173.981 | 3.433 | -0.403 | 0 | 0 |
| SLIPPAGE_C3_MIN10_10BPS | 0 | 10 | 2329.867 | 4.122 | -0.367 | 0 | 66,220,570 |
| SLIPPAGE_C3_MIN10_30BPS | 0 | 30 | 2131.638 | 4.027 | -0.405 | 0 | 180,811,282 |

注意。

```text
一部で cost / slippage ありの方が成績が良くなっている。
これは100株単位の丸めにより、買付株数・現金残・次回買付可否が変わる経路依存の副作用である。
したがって、Phase7-Dのcost sensitivityは「コスト耐性の厳密評価」ではなく、lot rounding込みの粗い比較として扱う。
Phase7-Eでは約定数量とcash timingをさらに厳密化する必要がある。
```

## 8. Cash Buffer / Max Position Weight

| policy | cash_buffer_ratio | max_position_weight | cumulative_return | max_drawdown | capital_utilization | cash_drag | replacement_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CASH_BUFFER_0 | 0.00 | 0.20 | 1580.981 | -0.372 | 0.881 | 0.119 | 531 |
| CASH_BUFFER_5 | 0.05 | 0.20 | 1173.981 | -0.403 | 0.828 | 0.172 | 537 |
| CASH_BUFFER_10 | 0.10 | 0.20 | 458.854 | -0.371 | 0.799 | 0.201 | 528 |
| MAX_WEIGHT_10 | 0.05 | 0.10 | 406.742 | -0.279 | 0.713 | 0.287 | 688 |
| MAX_WEIGHT_15 | 0.05 | 0.15 | 918.598 | -0.343 | 0.811 | 0.189 | 602 |
| MAX_WEIGHT_20 | 0.05 | 0.20 | 1173.981 | -0.403 | 0.828 | 0.172 | 537 |

Findings。

```text
cash_buffer 0% が最も高リターン。
cash_buffer 10% は資金効率を大きく落とした。
max_position_weight 10% はDDを抑えるが、リターンも落ちる。
max_position_weight 15% はバランス候補。
```

## 9. Emergency Hybrid

| policy | cumulative_return | annualized_return | max_drawdown | emergency_exit_count | worst_trade |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 216.474 | 2.107 | -0.343 | 0 | -0.786 |
| A_EMERGENCY_10 | 290.737 | 2.306 | -0.312 | 225 | -0.643 |
| A_EMERGENCY_12 | 159.326 | 1.914 | -0.410 | 192 | -0.500 |
| C3_MIN20_EMERGENCY_10 | 290.737 | 2.306 | -0.312 | 225 | -0.643 |
| C3_MIN20_EMERGENCY_12 | 159.326 | 1.914 | -0.410 | 192 | -0.500 |

Findings。

```text
-10% Emergency はBaselineよりリターンを上げ、DDもやや抑えた。
-12% Emergency は今回の制約下ではBaselineを下回った。
Emergencyは本命ではないが、-10%はPhase7-Eで再検証する価値がある。
```

## 10. Yearly View

代表policyの年別結果。

| policy | year | annual_return | annual_max_drawdown | trade_count | replacement_count | emergency_exit_count | lot_skip |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 2021 | 0.121 | -0.266 | 24 | 0 | 0 | 181 |
| A_FIXED_20BD | 2022 | 1.608 | -0.191 | 101 | 0 | 0 | 442 |
| A_FIXED_20BD | 2023 | 2.381 | -0.188 | 147 | 0 | 0 | 357 |
| A_FIXED_20BD | 2024 | 6.965 | -0.301 | 149 | 0 | 0 | 328 |
| A_FIXED_20BD | 2025 | 1.484 | -0.315 | 167 | 0 | 0 | 293 |
| A_FIXED_20BD | 2026 | 0.011 | -0.248 | 74 | 0 | 0 | 95 |
| C3_BASE_MIN10 | 2021 | 0.460 | -0.288 | 40 | 38 | 0 | 97 |
| C3_BASE_MIN10 | 2022 | 1.619 | -0.242 | 116 | 106 | 0 | 196 |
| C3_BASE_MIN10 | 2023 | 4.523 | -0.176 | 132 | 123 | 0 | 220 |
| C3_BASE_MIN10 | 2024 | 14.346 | -0.317 | 145 | 121 | 0 | 168 |
| C3_BASE_MIN10 | 2025 | 0.777 | -0.282 | 135 | 116 | 0 | 165 |
| C3_BASE_MIN10 | 2026 | 0.767 | -0.117 | 46 | 33 | 0 | 80 |
| C3_MIN15 | 2021 | 0.111 | -0.257 | 24 | 23 | 0 | 144 |
| C3_MIN15 | 2022 | 4.805 | -0.181 | 103 | 85 | 0 | 278 |
| C3_MIN15 | 2023 | 3.971 | -0.271 | 133 | 113 | 0 | 190 |
| C3_MIN15 | 2024 | 9.114 | -0.290 | 123 | 93 | 0 | 239 |
| C3_MIN15 | 2025 | 0.867 | -0.401 | 130 | 102 | 0 | 189 |
| C3_MIN15 | 2026 | 1.025 | -0.130 | 50 | 33 | 0 | 77 |
| A_EMERGENCY_10 | 2021 | 0.397 | -0.195 | 30 | 0 | 7 | 172 |
| A_EMERGENCY_10 | 2022 | 1.828 | -0.225 | 135 | 0 | 44 | 372 |
| A_EMERGENCY_10 | 2023 | 2.946 | -0.214 | 159 | 0 | 44 | 340 |
| A_EMERGENCY_10 | 2024 | 5.953 | -0.209 | 144 | 0 | 35 | 396 |
| A_EMERGENCY_10 | 2025 | 0.408 | -0.277 | 156 | 0 | 65 | 383 |
| A_EMERGENCY_10 | 2026 | 0.581 | -0.172 | 59 | 0 | 30 | 143 |

2026。

```text
A_FIXED_20BD:
annual_return 0.011

C3_BASE_MIN10:
annual_return 0.767

C3_MIN15:
annual_return 1.025

A_EMERGENCY_10:
annual_return 0.581
```

Phase7-Dでは、2026 weak-regimeでC3系とEmergency -10%がBaselineを上回った。

## 11. Answers To Phase7-D Questions

### C3_TOP50OUT_MIN10 の強さは実運用制約後も残るか

残った。

```text
C3_BASE_MIN10 cumulative_return:
1173.981

A_FIXED_20BD cumulative_return:
216.474
```

ただしreplacement_rate 0.875は高い。

### minimum_holding_days は 10 / 15 / 20 のどれが自然か

今回の結果では15が最有力。

```text
C3_MIN15:
returnが高く、min10よりreplacement_countが少ない
```

20はBaselineと同等になり、Replacementの効果が消える。

### replacement cooldown は必要か

必要候補ではあるが、今回のcooldown設定はリターンを大きく削った。

cooldownは固定日数ではなく、月次capや再評価間隔と組み合わせるべき。

### monthly / weekly reevaluation は高回転を抑えられるか

抑えられる。

ただしmonthlyはリターンをかなり削った。weeklyは中間候補。

### replacement cap per month は有効か

回転抑制には有効。

ただし cap 1 / 2 は今回かなり保守的すぎた。

### 100株単位・min_position_valueで買えないケースが多いか

多い。

Baselineでもlot skip 278、min value skip 1,418。C3_BASE_MIN10でもlot skip 160、min value skip 766。

### 手数料・スリッページでC3の優位性は消えるか

今回の粗いモデルでは消えなかった。

ただしlot roundingの経路依存でcostありの方が良くなる逆転があり、厳密評価にはPhase7-Eが必要。

## 12. Recommended Policy

Phase7-D時点の推奨。

```text
Primary baseline:
Top3 fixed 20bd hold

Best candidate:
C3_MIN15

Defensive candidate:
A_FIXED_20BD + Emergency -10%

Avoid as primary:
C3_MIN10 without additional turnover control
C3 monthly reevaluation
replacement cap per month 1 / 2
same-day replacement
```

Phase7-Eで優先すべき候補。

```text
C3_MIN15 + SELL_FIRST_BUY_AFTER_FILL
C3_MIN15 + max_position_weight 15%
C3_MIN15 + Emergency -10%
C3_MIN15 + softer replacement cap
A_FIXED_20BD + Emergency -10%
```

## 13. Phase7-E Topics

Phase7-Eで検証すべき内容。

```text
full long-term backtest
strict cash settlement timing
lot size and exact share accounting
fee / slippage model recheck without lot-rounding artifact
replacement cooldown as stateful per-position rule
monthly cap 3 / 4 / 5
weekly reevaluation with min15
C3_MIN15 + Emergency -10%
max_position_weight 15% / 20%
2026 weak-regime focused validation
Phase6 Defensive Review integration without auto-sell
```

## 14. Test Result

実行コマンド。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7d_execution_constraints_validation.py
```

結果。

```text
3 passed
```

関連Phase7テスト。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7a_schema.py tests/capital_allocation_ai/test_phase7a_policy.py tests/capital_allocation_ai/test_phase7a_audit.py tests/capital_allocation_ai/test_phase7b_conservative_replacement_validation.py tests/capital_allocation_ai/test_phase7c_daily_path_validation.py tests/capital_allocation_ai/test_phase7d_execution_constraints_validation.py
```

結果。

```text
19 passed
```

## 15. Execution Commands

Validation実行。

```text
python3 scripts/run_phase7d_execution_constraints_validation.py
```

テスト。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7d_execution_constraints_validation.py
python3 -m pytest tests/capital_allocation_ai/test_phase7a_schema.py tests/capital_allocation_ai/test_phase7a_policy.py tests/capital_allocation_ai/test_phase7a_audit.py tests/capital_allocation_ai/test_phase7b_conservative_replacement_validation.py tests/capital_allocation_ai/test_phase7c_daily_path_validation.py tests/capital_allocation_ai/test_phase7d_execution_constraints_validation.py
```

## 16. Final Audit

Safety flags。

| flag | value |
| --- | --- |
| broker_api_executed | false |
| paper_trading_executed | false |
| order_executed | false |
| live_order_executed | false |
| tachibana_api_called | false |
| jquants_api_called | false |
| no_future_data_in_decision | true |
| backtest_outcome_used_in_decision | false |
| future_price_used_in_decision | false |
| future_rank_used_in_decision | false |
| decision_evaluation_separated | true |

Final status。

```text
PHASE7D_EXECUTION_CONSTRAINT_VALIDATION_COMPLETE
```
