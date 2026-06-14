# Phase7-E Strict Long-Term Backtest / Exact Accounting

## 1. Summary

Phase7-Eでは、Phase7-Dで残っていた会計近似を減らし、100株単位・cash / unsettled cash・T+2 settlement・取引コスト / slippage・売買ledgerを明示した長期validationを実施した。

判定。

```text
PHASE7E_STRICT_LONG_TERM_BACKTEST_COMPLETE
```

今回のvalidationはローカルartifactのみを使用した。以下は行っていない。

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
固定利確の本採用
単純なTop3脱落Replacementの本採用
REPLACE_SELL / REPLACE_BUY の同時live実行
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

| item | value |
| --- | ---: |
| ranked_start_date | 2021-09-08 |
| ranked_end_date | 2026-05-15 |
| ranked_row_count | 56,995 |
| price_start_date | 2021-09-08 |
| price_end_date | 2026-06-12 |
| price_row_count | 2,416,234 |

## 3. Exact Accounting Scope

Phase7-Eで明示した会計項目。

```text
share_count
avg_entry_price
entry_date
cost_basis
realized_pnl
unrealized_pnl
cash
available_cash
unsettled_cash
invested_value
total_assets_net
transaction_cost_paid
slippage_cost_paid
gross_return_before_cost
net_return_after_cost
```

100株単位で買付数量を丸め、売却数量は保有株数を上限にした。売却代金はT+2でunsettled cashに入り、`conservative_T2_cash_unavailable`では受渡前の買付に使わない。

比較用に `same_settlement_buying_power_allowed` も出力した。ただし実運用では、Phase7-Dまでの制約通り `SELL_FIRST_BUY_AFTER_FILL` を前提にし、売却約定後にbuying powerを再取得して買付を再評価する。

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

Audit artifact。

```text
reports/capital_allocation_ai/phase7e/leakage_audit.json
```

## 5. Implemented Artifacts

作成した実装。

```text
src/ai_fund_lab_v2/capital_allocation_ai/phase7e_strict_backtest.py
scripts/run_phase7e_strict_backtest.py
tests/capital_allocation_ai/test_phase7e_strict_backtest.py
```

出力。

```text
reports/capital_allocation_ai/phase7e/validation_summary.json
reports/capital_allocation_ai/phase7e/policy_comparison.csv
reports/capital_allocation_ai/phase7e/settlement_mode_comparison.csv
reports/capital_allocation_ai/phase7e/transaction_cost_comparison.csv
reports/capital_allocation_ai/phase7e/skip_reason_summary.csv
reports/capital_allocation_ai/phase7e/annual_summary.csv
reports/capital_allocation_ai/phase7e/trade_ledger.csv
reports/capital_allocation_ai/phase7e/daily_portfolio_ledger.csv
reports/capital_allocation_ai/phase7e/holdings_ledger.csv
reports/capital_allocation_ai/phase7e/equity_curve.csv
reports/capital_allocation_ai/phase7e/leakage_audit.json
```

## 6. Main Policy Comparison

Net result。

| policy | settlement | final_assets_net | cumulative_return_net | annualized_return_net | max_drawdown_net | profit_factor_net | trade_count | replacement_rate | emergency_exit_count | capital_utilization |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | T+2 cash unavailable | 199,474,980 | 198.475 | 2.051 | -0.354 | 1.822 | 639 | 0.000 | 0 | 0.847 |
| A_FIXED_EMERGENCY10 | T+2 cash unavailable | 246,007,920 | 245.008 | 2.189 | -0.345 | 2.084 | 676 | 0.000 | 234 | 0.833 |
| C3_MIN15_T2 | T+2 cash unavailable | 873,471,440 | 872.471 | 3.165 | -0.362 | 2.938 | 532 | 0.814 | 0 | 0.815 |
| C3_MIN15_BP_ALLOWED | same settlement buying power | 1,442,597,850 | 1441.598 | 3.629 | -0.401 | 2.497 | 563 | 0.798 | 0 | 0.865 |
| C3_MIN15_WEIGHT15 | T+2 cash unavailable | 270,924,160 | 269.924 | 2.255 | -0.338 | 3.209 | 601 | 0.825 | 0 | 0.794 |
| C3_MIN15_EMERGENCY10 | T+2 cash unavailable | 214,237,810 | 213.238 | 2.098 | -0.328 | 1.740 | 632 | 0.620 | 175 | 0.799 |
| C3_MIN15_CAP3 | T+2 cash unavailable | 257,223,190 | 256.223 | 2.219 | -0.267 | 2.102 | 599 | 0.280 | 0 | 0.838 |
| C3_MIN15_CAP4 | T+2 cash unavailable | 442,305,560 | 441.306 | 2.609 | -0.282 | 1.999 | 556 | 0.399 | 0 | 0.831 |
| C3_MIN15_CAP5 | T+2 cash unavailable | 614,731,820 | 613.732 | 2.868 | -0.336 | 2.075 | 570 | 0.484 | 0 | 0.821 |
| C3_MIN15_WEEKLY | T+2 cash unavailable | 199,474,980 | 198.475 | 2.051 | -0.354 | 1.822 | 639 | 0.000 | 0 | 0.847 |

Findings。

```text
C3_MIN15_T2 は厳密T+2会計でも A_FIXED_20BD を大きく上回った。
ただし replacement_rate は 0.814 と高く、Phase7実運用候補としては回転抑制がまだ必要。
same settlement buying power allowed は参考値として最も高いが、実運用では売却約定後の再評価が必須。
max_position_weight 15% はDDをやや抑えるが、リターンを大きく削った。
monthly capは回転を抑えるほどDDも改善しやすいが、今回の設定ではリターン低下が大きい。
weekly reevaluationは今回の実装条件ではReplacementが発生せず、Baseline相当になった。
```

## 7. Emergency Exit

Emergency -10%。

| policy | cumulative_return_net | annualized_return_net | max_drawdown_net | emergency_exit_count | worst_trade_net |
| --- | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 198.475 | 2.051 | -0.354 | 0 | -0.786 |
| A_FIXED_EMERGENCY10 | 245.008 | 2.189 | -0.345 | 234 | -0.643 |
| C3_MIN15_T2 | 872.471 | 3.165 | -0.362 | 0 | -0.607 |
| C3_MIN15_EMERGENCY10 | 213.238 | 2.098 | -0.328 | 175 | -0.607 |

Interpretation。

```text
Baseline Aでは Emergency -10% がリターンとDDを少し改善した。
C3_MIN15では Emergency -10% がDDを抑えた一方、累積リターンを大きく削った。
Phase7-Fでは Emergency を一律ではなく、rank劣化・保有日数・市場環境と組み合わせて検証する必要がある。
```

## 8. Transaction Cost / Slippage

C3_MIN15_T2 cost sensitivity。

| policy | transaction_cost_bps | slippage_bps | final_assets_net | cumulative_return_net | annualized_return_net | max_drawdown_net | transaction_cost_paid | slippage_cost_paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| COST_C3_MIN15_0BPS | 0 | 0 | 873,471,440 | 872.471 | 3.165 | -0.362 | 0 | 0 |
| COST_C3_MIN15_10BPS | 10 | 10 | 360,343,905 | 359.344 | 2.456 | -0.338 | 6,066,952 | 6,067,323 |
| COST_C3_MIN15_30BPS | 30 | 30 | 282,913,143 | 281.913 | 2.285 | -0.360 | 17,800,856 | 17,803,717 |

Interpretation。

```text
Phase7-Dで見られた「costありの方が良い」経路依存の歪みは、Phase7-Eの厳密cash消費後には解消した。
10bps/10bpsでもC3_MIN15_T2はBaseline Aを上回るが、利益は大きく削られる。
高replacement率のままではcost/slippage耐性がPhase7の主要リスクになる。
```

## 9. Skip Summary

主要skip理由。

| policy | LOT_SIZE | MIN_POSITION_VALUE |
| --- | ---: | ---: |
| A_FIXED_20BD | 223 | 1,549 |
| A_FIXED_EMERGENCY10 | 264 | 1,542 |
| C3_MIN15_T2 | 158 | 1,051 |
| C3_MIN15_BP_ALLOWED | 169 | 948 |
| C3_MIN15_WEIGHT15 | 222 | 835 |
| C3_MIN15_EMERGENCY10 | 208 | 1,040 |
| C3_MIN15_CAP3 | 320 | 1,304 |

Interpretation。

```text
100株単位とmin_position_valueによる買付見送りは引き続き多い。
初期100万円ではlot制約が資金効率と保有銘柄数に強く影響する。
Phase7-Fでは min_position_value / max_position_weight / cash_buffer の組み合わせを、より小さなgridで再確認する。
```

## 10. Annual Results

主要policyの年別net return。

| policy | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 0.192 | 2.310 | 1.838 | 7.769 | 0.781 | -0.001 |
| A_FIXED_EMERGENCY10 | 0.281 | 2.632 | 1.794 | 8.888 | 0.018 | 0.687 |
| C3_MIN15_T2 | 0.124 | 3.548 | 2.163 | 8.968 | 1.996 | 0.604 |
| C3_MIN15_EMERGENCY10 | 0.151 | 1.715 | 3.540 | 8.947 | 0.513 | -0.043 |
| C3_MIN15_CAP3 | 0.176 | 2.406 | 1.785 | 6.134 | 2.588 | -0.124 |

Interpretation。

```text
C3_MIN15_T2は2022-2026でBaseline Aを概ね上回った。
2021はBaseline Aの方が良い。
2026 weak-regimeではC3_MIN15_T2がプラスを維持したが、これはreplacementの有効性と高回転リスクの両方を含む結果である。
```

## 11. Phase7-E Conclusion

分かったこと。

```text
1. 厳密T+2会計でも C3_MIN15_T2 は A_FIXED_20BD を壊していない。
2. ただし C3_MIN15_T2 の replacement_rate は 0.814 で、実運用には高すぎる。
3. cost/slippageを10bpsずつ入れると累積リターンは 872.471 から 359.344 まで低下する。
4. それでも10bps/10bps条件ではBaseline Aを上回った。
5. Emergency -10%はBaseline Aでは有効候補だが、C3_MIN15では利益を大きく削る。
6. monthly capは回転抑制に有効だが、単純capではリターン低下が大きい。
7. max_position_weight 15%はDD改善候補だが、資金効率低下が大きい。
8. 100株単位・min_position_value skipは無視できず、初期100万円運用の重要制約である。
9. same settlement buying power allowedは参考値として高いが、liveではsell-fill後の再評価が必須。
10. Phase7-Fでは「高回転を抑えつつC3_MIN15の優位を残す」ことが主課題。
```

## 12. Recommended Policy For Phase7-F

Primary candidate。

```text
C3_MIN15_T2
minimum_holding_days = 15
replacement_rank_degradation_threshold = Candidate Top50外
confirmation_days = 2
replacement_edge_margin = 0.02
settlement = conservative_T2_cash_unavailable
lot_size = 100
cash_buffer_ratio = 5%
max_position_weight = 20%
```

ただし、このまま本採用しない。理由はreplacement_rateが高く、cost/slippage・税・約定遅延・注文失敗に弱い可能性があるため。

Defensive candidate。

```text
A_FIXED_20BD + Emergency -10%
```

Baseline Aを守りながらDDと2026の弱さを少し改善したため、低回転な防御比較対象として残す。

## 13. Phase7-F Open Questions

Phase7-Fで検証すべき内容。

```text
replacement_rate を 0.2-0.5 程度に抑える条件
monthly cap 3-5 と edge margin / rank degradation の同時最適化
Emergency Exit を一律ではなく rank degradation と組み合わせる条件
10bps/10bps, 30bps/30bps のcost/slippage耐性
min_position_value と max_position_weight の再grid
2021の弱さと2026 weak-regimeの要因
税・部分約定・売買停止・値幅制限を含むさらに現実的なExecution validation
SELL_FIRST_BUY_AFTER_FILLの実運用状態遷移設計
```

