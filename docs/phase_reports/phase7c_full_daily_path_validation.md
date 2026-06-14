# Phase7-C Full Daily Path Validation

## 1. Summary

Phase7-Cでは、Phase7-Bのforward label近似を、既存のJ-Quants由来 daily close path で再検証した。

判定。

```text
PHASE7C_FULL_DAILY_PATH_VALIDATION_COMPLETE
```

今回の主目的。

```text
Emergency Exitを日次終値到達ベースで検証する
Replacement途中売却returnを日次終値で計算する
same-day replacement と SELL_FIRST_BUY_AFTER_FILL の差を見る
decision と evaluation をコード上で分離する
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

daily close は、既存のJ-Quants raw response JSONから `AdjC` を優先し、欠損時のみ `C` を使用した。

新規API取得は行っていない。

| item | value |
| --- | ---: |
| ranked_start_date | 2021-09-08 |
| ranked_end_date | 2026-05-15 |
| ranked_row_count | 56,995 |
| price_start_date | 2021-09-08 |
| price_end_date | 2026-06-12 |
| price_date_count | 1,163 |
| price_row_count | 2,416,234 |

## 3. Leakage Guard

Decision生成に使用したもの。

```text
target_date時点のOpportunity rank / expected_edge_score
target_date時点のclose
entry price
holding_days
current unrealized_return
target_date以前のconfirmation state
```

Decision生成に使用していないもの。

```text
future_return
future_close
future_high
future_low
future_max_return
future_max_drawdown
realized_pnl
backtest outcome
将来日のOpportunity rank
将来日のscore
```

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
reports/capital_allocation_ai/phase7c/leakage_audit.json
```

## 4. Implemented Artifacts

作成した実装。

```text
src/ai_fund_lab_v2/capital_allocation_ai/phase7c_daily_path_validation.py
scripts/run_phase7c_daily_path_validation.py
tests/capital_allocation_ai/test_phase7c_daily_path_validation.py
```

出力。

```text
reports/capital_allocation_ai/phase7c/validation_summary.json
reports/capital_allocation_ai/phase7c/policy_comparison.csv
reports/capital_allocation_ai/phase7c/emergency_exit_comparison.csv
reports/capital_allocation_ai/phase7c/replacement_timing_comparison.csv
reports/capital_allocation_ai/phase7c/annual_summary.csv
reports/capital_allocation_ai/phase7c/trade_level_decisions.csv
reports/capital_allocation_ai/phase7c/equity_curve.csv
reports/capital_allocation_ai/phase7c/leakage_audit.json
```

## 5. Policy Comparison

主要policy結果。

| policy | timing | cumulative_return | annualized_return | max_drawdown | trade_count | avg_hold | turnover | replacement_count | emergency_exit_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | NONE | 488.078 | 2.686 | -0.394 | 485 | 20.00 | 102.2 | 0 | 0 |
| C1_EMERGENCY_10 | NONE | 354.355 | 2.446 | -0.265 | 527 | 16.23 | 111.0 | 0 | 163 |
| C1_EMERGENCY_12 | NONE | 396.368 | 2.528 | -0.324 | 541 | 16.72 | 114.0 | 0 | 155 |
| C1_EMERGENCY_15 | NONE | 120.066 | 1.747 | -0.288 | 559 | 17.78 | 117.8 | 0 | 115 |
| C1_EMERGENCY_20 | NONE | 110.560 | 1.700 | -0.417 | 529 | 18.64 | 111.4 | 0 | 70 |
| C1_EMERGENCY_25 | NONE | 146.091 | 1.862 | -0.255 | 480 | 19.34 | 101.1 | 0 | 43 |
| C2_WEEKLY_MIN10_SAME_DAY | SAME_DAY | 179.837 | 1.989 | -0.357 | 591 | 16.53 | 124.5 | 410 | 0 |
| C2_WEEKLY_MIN10_SELL_FIRST_BUY_AFTER_FILL | SELL_FIRST_BUY_AFTER_FILL | 1099.690 | 3.373 | -0.436 | 482 | 16.58 | 101.5 | 330 | 0 |
| C3_TOP50OUT_MIN10_SAME_DAY | SAME_DAY | 1287.036 | 3.520 | -0.383 | 730 | 12.93 | 153.8 | 635 | 0 |
| C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL | SELL_FIRST_BUY_AFTER_FILL | 3040.561 | 4.417 | -0.266 | 551 | 12.87 | 116.1 | 477 | 0 |
| E_DAILY_TOP3_SYNC_SAME_DAY | SAME_DAY | 9613547.340 | 28.582 | -0.189 | 2,316 | 1.51 | 487.9 | 2,313 | 0 |
| E_DAILY_TOP3_SYNC_SELL_FIRST_BUY_AFTER_FILL | SELL_FIRST_BUY_AFTER_FILL | 2453.588 | 4.178 | -0.148 | 1,183 | 1.64 | 249.2 | 1,180 | 0 |

Interpretation。

```text
Top3 fixed 20bd hold は、日次終値パスでも強い。
Emergency ExitはDDを下げるケースがあるが、利益を削る。
Daily Top3 Syncは異常に高いリターンも出たが、replacement_rateがほぼ100%で本命ではない。
SELL_FIRST_BUY_AFTER_FILL はsame-dayと大きく異なるため、Phase7-Dではcash timingを必ず入れる必要がある。
```

## 6. Emergency Exit

Emergency Exitは、entry_priceから日次closeが閾値に到達した最初の日にexitした。

| policy | cumulative_return | annualized_return | max_drawdown | emergency_exit_count | emergency_exit_rate | worst_trade |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C1_EMERGENCY_10 | 354.355 | 2.446 | -0.265 | 163 | 0.309 | -0.279 |
| C1_EMERGENCY_12 | 396.368 | 2.528 | -0.324 | 155 | 0.287 | -0.500 |
| C1_EMERGENCY_15 | 120.066 | 1.747 | -0.288 | 115 | 0.206 | -0.643 |
| C1_EMERGENCY_20 | 110.560 | 1.700 | -0.417 | 70 | 0.132 | -0.500 |
| C1_EMERGENCY_25 | 146.091 | 1.862 | -0.255 | 43 | 0.090 | -0.643 |

Findings。

```text
-10% / -12% はBaselineよりDDを抑えたが、累積リターンは低下。
-15%以降も利益低下が大きく、単純Emergency Exitの本採用はまだ危険。
Emergency ExitはDD抑制目的の候補として残すが、利益毀損とのトレードオフが強い。
```

## 7. Replacement Timing

Validationでは以下を比較した。

```text
Same-day logical replacement
SELL_FIRST_BUY_AFTER_FILL
```

実運用では、必ず `SELL_FIRST_BUY_AFTER_FILL` とする。

代表比較。

| policy | timing | cumulative_return | max_drawdown | trade_count | avg_hold | turnover | replacement_count | replacement_rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C2_WEEKLY_MIN10 | SAME_DAY | 179.837 | -0.357 | 591 | 16.53 | 124.5 | 410 | 0.694 |
| C2_WEEKLY_MIN10 | SELL_FIRST_BUY_AFTER_FILL | 1099.690 | -0.436 | 482 | 16.58 | 101.5 | 330 | 0.685 |
| C3_TOP50OUT_MIN10 | SAME_DAY | 1287.036 | -0.383 | 730 | 12.93 | 153.8 | 635 | 0.870 |
| C3_TOP50OUT_MIN10 | SELL_FIRST_BUY_AFTER_FILL | 3040.561 | -0.266 | 551 | 12.87 | 116.1 | 477 | 0.866 |
| E_DAILY_TOP3_SYNC | SAME_DAY | 9613547.340 | -0.189 | 2,316 | 1.51 | 487.9 | 2,313 | 0.999 |
| E_DAILY_TOP3_SYNC | SELL_FIRST_BUY_AFTER_FILL | 2453.588 | -0.148 | 1,183 | 1.64 | 249.2 | 1,180 | 0.997 |

Findings。

```text
cash timingの影響は非常に大きい。
Daily Syncではsame-dayとsell-firstで結果が桁違いに変わった。
Phase7-D以降ではsame-day結果を参考値にとどめ、sell-firstを標準評価にするべき。
```

## 8. Transaction Cost Sensitivity

参考比較。

| policy | transaction_cost_bps | cumulative_return | annualized_return | max_drawdown | turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 0 | 488.078 | 2.686 | -0.394 | 102.2 |
| COST_FIXED_10BPS | 10 | 437.334 | 2.602 | -0.396 | 102.2 |
| COST_FIXED_30BPS | 30 | 351.236 | 2.440 | -0.398 | 102.2 |
| E_DAILY_TOP3_SYNC_SAME_DAY | 0 | 9613547.340 | 28.582 | -0.189 | 487.9 |
| COST_DAILY_SYNC_10BPS | 10 | 3762993.000 | 23.278 | -0.199 | 487.9 |
| COST_DAILY_SYNC_30BPS | 30 | 576631.200 | 15.353 | -0.232 | 487.9 |

Findings。

```text
高回転policyはコスト感応度が極端に大きい。
Daily Syncの見かけの高リターンは、手数料・スリッページ・約定制約を入れるほど信頼度が落ちる。
```

## 9. Yearly View

代表policyの年別結果。

| policy | year | annual_return | annual_max_drawdown | annual_trade_count | replacement_count | emergency_exit_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 2021 | 0.297 | -0.142 | 20 | 0 | 0 |
| A_FIXED_20BD | 2022 | 1.366 | -0.221 | 67 | 0 | 0 |
| A_FIXED_20BD | 2023 | 2.786 | -0.195 | 83 | 0 | 0 |
| A_FIXED_20BD | 2024 | 6.907 | -0.394 | 92 | 0 | 0 |
| A_FIXED_20BD | 2025 | 1.210 | -0.324 | 161 | 0 | 0 |
| A_FIXED_20BD | 2026 | 1.083 | -0.188 | 62 | 0 | 0 |
| C1_EMERGENCY_10 | 2021 | 0.363 | -0.137 | 21 | 0 | 1 |
| C1_EMERGENCY_10 | 2022 | 2.003 | -0.226 | 90 | 0 | 26 |
| C1_EMERGENCY_10 | 2023 | 2.888 | -0.265 | 112 | 0 | 29 |
| C1_EMERGENCY_10 | 2024 | 9.556 | -0.194 | 114 | 0 | 24 |
| C1_EMERGENCY_10 | 2025 | 0.332 | -0.257 | 140 | 0 | 58 |
| C1_EMERGENCY_10 | 2026 | 0.327 | -0.164 | 50 | 0 | 25 |
| C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL | 2021 | 0.726 | -0.074 | 32 | 30 | 0 |
| C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL | 2022 | 1.564 | -0.175 | 102 | 95 | 0 |
| C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL | 2023 | 6.900 | -0.189 | 111 | 100 | 0 |
| C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL | 2024 | 20.981 | -0.163 | 116 | 99 | 0 |
| C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL | 2025 | 2.460 | -0.266 | 140 | 116 | 0 |
| C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL | 2026 | 0.115 | -0.191 | 50 | 37 | 0 |

2026 weak-regime。

```text
A_FIXED_20BD:
annual_return 1.083

C1_EMERGENCY_10:
annual_return 0.327

C3_TOP50OUT_MIN10_SELL_FIRST_BUY_AFTER_FILL:
annual_return 0.115

E_DAILY_TOP3_SYNC_SELL_FIRST_BUY_AFTER_FILL:
annual_return 0.627
```

今回の日次パスでは、2026でもTop3 fixed 20bd holdを明確に上回る保守的policyは確認できなかった。

## 10. Answers To Phase7-C Questions

### Top3 fixed 20bd hold は日次終値パスでも強いか

強い。

```text
cumulative_return:
488.078

annualized_return:
2.686
```

### Emergency Exitは本当にDDを下げるか

一部下げる。

```text
Baseline max_drawdown:
-0.394

-10% Emergency:
-0.265

-12% Emergency:
-0.324

-25% Emergency:
-0.255
```

ただし利益を削る。

### minimum_holding_days 10 / 20 のどちらが自然か

20がより自然。

min10は良い結果もあるが、replacement_countがまだ多い。min20はBaselineと同等で、早売りを抑える。

### Weekly re-evaluation はDaily replacementより優れているか

高回転抑制の観点では優れている。

Daily Syncはリターンだけ見ると極端に強く見えるが、平均保有1.5営業日・replacement_rateほぼ100%で実運用向きではない。

### Candidate Top50外 only Replacement は利益を壊さないか

min10では壊していないように見えるが、replacement_rateが0.866-0.870で高い。

本採用にはcooldown / transaction cost / slippage / sell-first厳密化が必要。

### SELL_FIRST_BUY_AFTER_FILL のcash timing影響は大きいか

大きい。

same-day logical replacementとは別物として扱う必要がある。

## 11. Recommended Policy

Phase7-C時点の推奨。

```text
Primary baseline:
Top3 fixed 20bd hold

Emergency Exit:
候補として残すが、本採用はまだ不可
特に -10% / -12% はDD抑制候補

Replacement:
Daily Top3 Syncは本命にしない
Candidate Top50外 only + minimum_holding_days 10/20 をPhase7-Dで再検証

Execution timing:
SELL_FIRST_BUY_AFTER_FILL を標準評価にする
```

## 12. Phase7-D Topics

Phase7-Dで検証すべき内容。

```text
full backtest with stricter cash / settlement timing
lot size and tradable share quantity
slippage model
transaction cost model by turnover
replacement cooldown
weekly / monthly rebalance only
minimum_holding_days 10 / 15 / 20
Emergency Exit -10% / -12% with re-entry delay
Candidate Top50外 only Replacement with replacement cap
2026 weak-regime focused validation
Phase6 Defensive Review integration without auto-sell
```

## 13. Test Result

実行コマンド。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7c_daily_path_validation.py
```

結果。

```text
3 passed
```

関連Phase7テスト。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7a_schema.py tests/capital_allocation_ai/test_phase7a_policy.py tests/capital_allocation_ai/test_phase7a_audit.py tests/capital_allocation_ai/test_phase7b_conservative_replacement_validation.py tests/capital_allocation_ai/test_phase7c_daily_path_validation.py
```

結果。

```text
16 passed
```

## 14. Execution Commands

Validation実行。

```text
python3 scripts/run_phase7c_daily_path_validation.py
```

テスト。

```text
python3 -m pytest tests/capital_allocation_ai/test_phase7c_daily_path_validation.py
python3 -m pytest tests/capital_allocation_ai/test_phase7a_schema.py tests/capital_allocation_ai/test_phase7a_policy.py tests/capital_allocation_ai/test_phase7a_audit.py tests/capital_allocation_ai/test_phase7b_conservative_replacement_validation.py tests/capital_allocation_ai/test_phase7c_daily_path_validation.py
```

## 15. Final Audit

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
PHASE7C_FULL_DAILY_PATH_VALIDATION_COMPLETE
```
