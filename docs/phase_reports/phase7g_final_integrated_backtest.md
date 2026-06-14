# Phase7-G Final Integrated Backtest

## 1. Summary

Phase7-Gでは、Phase7-Fで選定した最終候補を、Phase7-E/Fと同等の厳密会計で統合比較した。

判定。

```text
PHASE7G_FINAL_INTEGRATED_BACKTEST_COMPLETE
```

初期資金。

```text
initial_capital = 1,000,000 JPY
```

以下は行っていない。

```text
Broker API接続
Paper Trading
実発注
live order
立花証券API呼び出し
新規J-Quants API取得
future data の decision 利用
backtest outcome の decision 利用
Kelly基準
レバレッジ
信用取引
ナンピン
```

## 2. Source Data

| item | value |
| --- | ---: |
| ranked_daily | reports/phase7_prestudy/opportunity_ranked_daily.parquet |
| daily_close_path | .runtime/data/raw/jquants/equities_bars_daily/responses/ |
| ranked_start_date | 2021-09-08 |
| ranked_end_date | 2026-05-15 |
| ranked_row_count | 56,995 |
| price_start_date | 2021-09-08 |
| price_end_date | 2026-06-12 |
| price_row_count | 2,416,234 |

## 3. Execution Constraints

Phase7-Gで反映した制約。

```text
exact share accounting
exact cash accounting
T+2 settlement
SELL_FIRST_BUY_AFTER_FILL
100株単位
cash buffer 5%
max_position_weight 20%
transaction cost
slippage
```

比較したcost/slippage。

```text
0bps / 0bps
10bps / 10bps
30bps / 30bps
```

## 4. Leakage Guard

Leakage audit。

| flag | value |
| --- | --- |
| status | PASS |
| no_future_data_in_decision | true |
| backtest_outcome_used_in_decision | false |
| future_price_used_in_decision | false |
| future_rank_used_in_decision | false |
| decision_evaluation_separated | true |

Artifact。

```text
reports/capital_allocation_ai/phase7g/leakage_audit.json
```

## 5. Artifacts

実装。

```text
src/ai_fund_lab_v2/capital_allocation_ai/phase7g_final_integrated_backtest.py
scripts/run_phase7g_final_integrated_backtest.py
tests/capital_allocation_ai/test_phase7g_final_integrated_backtest.py
```

出力。

```text
reports/capital_allocation_ai/phase7g/validation_summary.json
reports/capital_allocation_ai/phase7g/final_policy_comparison.csv
reports/capital_allocation_ai/phase7g/annual_summary.csv
reports/capital_allocation_ai/phase7g/monthly_summary.csv
reports/capital_allocation_ai/phase7g/compounding_summary.csv
reports/capital_allocation_ai/phase7g/policy_ranking.csv
reports/capital_allocation_ai/phase7g/leakage_audit.json
reports/capital_allocation_ai/phase7g/equity_curve.csv
reports/capital_allocation_ai/phase7g/trade_ledger.csv
reports/capital_allocation_ai/phase7g/daily_portfolio_ledger.csv
```

## 6. Final Policy Comparison

0bps baseline comparison。

| policy | role | final_assets_net | cumulative_return_net | annualized_return_net | max_drawdown_net | win_rate | avg_holding_days | trade_count | replacement_rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CAP5_0BPS | Primary | 614,731,820 | 613.732 | 2.868 | -0.336 | 0.607 | 18.54 | 570 | 0.484 |
| CAP4_0BPS | Conservative | 442,305,560 | 441.306 | 2.609 | -0.282 | 0.633 | 18.86 | 556 | 0.399 |
| POLICY_Y_CAP4_EDGE08_CONF5_0BPS | Weak Regime | 177,642,720 | 176.643 | 1.978 | -0.336 | 0.591 | 19.64 | 565 | 0.356 |
| A_FIXED_20BD_0BPS | Reference | 199,474,980 | 198.475 | 2.051 | -0.354 | 0.598 | 20.00 | 639 | 0.000 |
| C3_MIN15_T2_0BPS | Reference High Turnover | 873,471,440 | 872.471 | 3.165 | -0.362 | 0.613 | 16.96 | 532 | 0.814 |

Interpretation。

```text
C3_MIN15_T2は最も高い利益だが、replacement_rate 0.814で高回転すぎる。
CAP5はreplacement_rateを0.484まで抑えつつ、Reference A_FIXEDを大きく上回った。
CAP4はCAP5より利益は落ちるが、DDと回転率が低い。
POLICY_Yは2026 weak-regime比較用で、全期間ではReference A_FIXEDを下回った。
```

## 7. Cost / Slippage Robustness

| policy | cost/slippage | final_assets_net | cumulative_return_net | annualized_return_net | max_drawdown_net | replacement_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CAP5 | 0/0 | 614,731,820 | 613.732 | 2.868 | -0.336 | 0.484 |
| CAP5 | 10/10 | 289,949,883 | 288.950 | 2.302 | -0.322 | 0.547 |
| CAP5 | 30/30 | 226,981,639 | 225.982 | 2.136 | -0.344 | 0.560 |
| CAP4 | 0/0 | 442,305,560 | 441.306 | 2.609 | -0.282 | 0.399 |
| CAP4 | 10/10 | 186,691,221 | 185.691 | 2.009 | -0.266 | 0.420 |
| CAP4 | 30/30 | 87,209,830 | 86.210 | 1.563 | -0.318 | 0.400 |
| POLICY_Y | 0/0 | 177,642,720 | 176.643 | 1.978 | -0.336 | 0.356 |
| POLICY_Y | 10/10 | 271,368,700 | 270.369 | 2.256 | -0.358 | 0.357 |
| POLICY_Y | 30/30 | 64,207,520 | 63.208 | 1.403 | -0.337 | 0.381 |
| A_FIXED_20BD | 0/0 | 199,474,980 | 198.475 | 2.051 | -0.354 | 0.000 |
| C3_MIN15_T2 | 0/0 | 873,471,440 | 872.471 | 3.165 | -0.362 | 0.814 |

注意。

```text
一部でcost/slippageありの方が良いケースがある。
これは100株単位の丸めとcash timingによる経路依存であり、コストが成績を改善するという意味ではない。
```

## 8. Annual Summary For Primary CAP5

| year | start_assets | end_assets | annual_profit | annual_return | max_drawdown | trade_count | replacement_count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2021 | 1,000,000 | 1,205,350 | 205,350 | 0.205 | -0.206 | 26 | 19 |
| 2022 | 1,264,150 | 8,030,440 | 6,766,290 | 5.352 | -0.184 | 106 | 60 |
| 2023 | 7,876,980 | 27,199,660 | 19,322,680 | 2.453 | -0.164 | 104 | 60 |
| 2024 | 29,283,260 | 274,484,420 | 245,201,160 | 8.373 | -0.336 | 121 | 57 |
| 2025 | 279,962,770 | 634,303,170 | 354,340,400 | 1.266 | -0.193 | 148 | 60 |
| 2026 | 650,684,020 | 614,731,820 | -35,952,200 | -0.055 | -0.257 | 65 | 20 |

2026はCAP5で弱く、Phase8ではPolicy Yを併走比較する理由になる。

## 9. Monthly Summary For Primary CAP5

| item | value |
| --- | ---: |
| month_count | 58 |
| winning_months | 46 |
| losing_months | 12 |
| best_month | 2022-06 |
| best_month_return | 0.826 |
| worst_month | 2022-01 |
| worst_month_return | -0.149 |

## 10. Phase7-G Conclusion

開発者向け結論。

```text
Primary = CAP5
Conservative = CAP4
Weak-regime comparison = POLICY_Y_CAP4_EDGE08_CONF5
Reference = A_FIXED_20BD
Reference high turnover = C3_MIN15_T2
```

Phase8へ進める候補。

```text
CAP5:
主候補。利益と回転率のバランスが最も良い。

CAP4:
保守候補。DDと回転率をさらに抑える。

POLICY_Y:
2026 weak-regime監視用。全期間主候補ではない。
```

Phase8で必ず維持する制約。

```text
SELL_FIRST_BUY_AFTER_FILL
売却約定確認後にbroker snapshot / buying power / cashを再取得
REPLACE_BUYは再評価後のみ
Paper Tradingでも同時売買しない
```

