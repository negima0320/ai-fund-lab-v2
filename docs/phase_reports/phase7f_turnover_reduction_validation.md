# Phase7-F Turnover Reduction & Robustness Validation

## 1. Summary

Phase7-Fでは、Phase7-Eの有力候補 `C3_MIN15_T2` をベースに、利益をなるべく維持したまま `replacement_rate` を 0.2-0.5 程度まで下げられるかを検証した。

判定。

```text
PHASE7F_TURNOVER_REDUCTION_VALIDATION_COMPLETE
```

今回もローカルartifactのみを使用した。以下は行っていない。

```text
Broker API接続
Paper Trading
実発注
live order
立花証券API呼び出し
新規J-Quants API取得
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
reports/capital_allocation_ai/phase7f/leakage_audit.json
```

## 4. Implemented Artifacts

作成した実装。

```text
src/ai_fund_lab_v2/capital_allocation_ai/phase7f_turnover_reduction_validation.py
scripts/run_phase7f_turnover_reduction_validation.py
tests/capital_allocation_ai/test_phase7f_turnover_reduction_validation.py
```

Phase7-Eの厳密会計engineに以下を追加パラメータ化した。

```text
replacement_rank_threshold
replacement_edge_margin
confirmation_days
reentry_cooldown_days
replacement_cap_per_month
```

出力。

```text
reports/capital_allocation_ai/phase7f/validation_summary.json
reports/capital_allocation_ai/phase7f/policy_comparison.csv
reports/capital_allocation_ai/phase7f/turnover_comparison.csv
reports/capital_allocation_ai/phase7f/robustness_comparison.csv
reports/capital_allocation_ai/phase7f/annual_summary.csv
reports/capital_allocation_ai/phase7f/leakage_audit.json
```

## 5. Baseline

Phase7-Eとの比較基準。

| policy | cumulative_return_net | annualized_return_net | max_drawdown_net | trade_count | replacement_count | replacement_rate | annual_return_2026 | annual_dd_2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | 198.475 | 2.051 | -0.354 | 639 | 0 | 0.000 | -0.001 | -0.278 |
| C3_MIN15_T2 | 872.471 | 3.165 | -0.362 | 532 | 433 | 0.814 | 0.604 | -0.135 |

Interpretation。

```text
C3_MIN15_T2は引き続き非常に強い。
ただし replacement_rate 0.814 はPhase8 Broker Test / Paper Trading候補としては高すぎる。
```

## 6. Turnover Reduction Results

Target band。

```text
replacement_rate 0.2-0.5
```

この範囲で最も強かった候補。

| policy | cumulative_return_net | annualized_return_net | max_drawdown_net | replacement_count | replacement_rate | average_holding_days | annual_return_2026 | annual_dd_2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CAP5 | 613.732 | 2.868 | -0.336 | 276 | 0.484 | 18.54 | -0.055 | -0.257 |
| CAP4 | 441.306 | 2.609 | -0.282 | 222 | 0.399 | 18.86 | -0.096 | -0.262 |
| CAP3 | 256.223 | 2.219 | -0.267 | 168 | 0.280 | 19.30 | -0.124 | -0.267 |
| POLICY_Y_CAP4_EDGE08_CONF5 | 176.643 | 1.978 | -0.336 | 201 | 0.356 | 19.64 | 0.522 | -0.138 |

Findings。

```text
CAP5はreplacement_rateを0.814から0.484まで下げつつ、累積return 613.732を維持した。
CAP4はさらに回転を落とし、DDも-0.282まで改善したが、利益はCAP5より落ちた。
CAP3はDDが最も小さいが、利益低下が大きい。
Policy Yは2026が強いが、全期間ではA_FIXED_20BDをやや下回った。
```

## 7. Parameter Findings

### Replacement Cap

| policy | cumulative_return_net | max_drawdown_net | replacement_rate | annual_return_2026 |
| --- | ---: | ---: | ---: | ---: |
| CAP3 | 256.223 | -0.267 | 0.280 | -0.124 |
| CAP4 | 441.306 | -0.282 | 0.399 | -0.096 |
| CAP5 | 613.732 | -0.336 | 0.484 | -0.055 |
| CAP6 | 246.949 | -0.383 | 0.676 | 0.185 |
| CAP8 | 284.126 | -0.366 | 0.757 | 0.053 |

Interpretation。

```text
cap5が最も良いバランス。
cap6 / cap8は回転が再び高くなり、利益もCAP5より落ちた。
```

### Confirmation

| policy | cumulative_return_net | max_drawdown_net | replacement_rate | annual_return_2026 |
| --- | ---: | ---: | ---: | ---: |
| CONFIRM2 | 872.471 | -0.362 | 0.814 | 0.604 |
| CONFIRM3 | 215.013 | -0.331 | 0.728 | 0.471 |
| CONFIRM5 | 454.548 | -0.350 | 0.588 | 0.352 |

Interpretation。

```text
confirmationだけではtarget bandまで落ちない。
confirm5は利益を残すが、replacement_rateはまだ0.588と高め。
```

### Edge Margin

| policy | cumulative_return_net | replacement_rate |
| --- | ---: | ---: |
| EDGE02 | 872.471 | 0.814 |
| EDGE03 | 872.471 | 0.814 |
| EDGE05 | 872.471 | 0.814 |
| EDGE08 | 872.471 | 0.814 |
| EDGE10 | 872.471 | 0.814 |

Interpretation。

```text
今回のscore分布ではedge margin単独は効かなかった。
Replacement発生時の新規Top3候補scoreが、保有銘柄scoreを十分上回っていた可能性が高い。
```

### Rank Degradation

| policy | cumulative_return_net | max_drawdown_net | replacement_rate | annual_return_2026 |
| --- | ---: | ---: | ---: | ---: |
| RANK_OUT50 | 872.471 | -0.362 | 0.814 | 0.604 |
| RANK_OUT30 | 279.651 | -0.382 | 0.869 | 0.376 |
| RANK_OUT20 | 572.002 | -0.361 | 0.858 | 0.108 |
| RANK_OUT10 | 716.819 | -0.362 | 0.884 | 0.507 |

Interpretation。

```text
rank thresholdを厳しくしても回転は下がらなかった。
Top10/20/30外はむしろreplacement候補が増えるため、回転抑制目的には不向き。
```

### Re-entry Cooldown

| policy | cumulative_return_net | max_drawdown_net | replacement_rate | annual_return_2026 |
| --- | ---: | ---: | ---: | ---: |
| COOLDOWN5 | 253.398 | -0.322 | 0.833 | 0.035 |
| COOLDOWN10 | 428.106 | -0.301 | 0.842 | 0.287 |
| COOLDOWN15 | 516.547 | -0.305 | 0.843 | 0.959 |

Interpretation。

```text
同一銘柄re-entry cooldownは2026改善に効いたが、replacement_rate低下には効かなかった。
高回転の主因は同一銘柄への再入替ではなく、別銘柄へのReplacementである。
```

## 8. Cost Robustness

0bps / 10bps / 30bps 比較。

| policy | cost/slippage | cumulative_return_net | annualized_return_net | max_drawdown_net | replacement_rate | annual_return_2026 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ROBUST_C3_MIN15 | 0/0 | 872.471 | 3.165 | -0.362 | 0.814 | 0.604 |
| ROBUST_C3_MIN15 | 10/10 | 359.344 | 2.456 | -0.338 | 0.843 | 0.631 |
| ROBUST_C3_MIN15 | 30/30 | 281.913 | 2.285 | -0.360 | 0.838 | 0.927 |
| ROBUST_CAP5 | 0/0 | 613.732 | 2.868 | -0.336 | 0.484 | -0.055 |
| ROBUST_CAP5 | 10/10 | 288.950 | 2.302 | -0.322 | 0.547 | 0.066 |
| ROBUST_CAP5 | 30/30 | 225.982 | 2.136 | -0.344 | 0.560 | 0.036 |
| ROBUST_POLICY_Y | 0/0 | 176.643 | 1.978 | -0.336 | 0.356 | 0.522 |
| ROBUST_POLICY_Y | 10/10 | 270.369 | 2.256 | -0.358 | 0.357 | 0.462 |
| ROBUST_POLICY_Y | 30/30 | 63.208 | 1.403 | -0.337 | 0.381 | 0.233 |

注意。

```text
一部policyではcost/slippageありの方が0bpsより良い。
これは100株単位の丸めとcash timingの経路依存で、コストが良いという意味ではない。
Primary比較は0bps、Robustness比較は30bpsでもBaseline Aを超えるかを重視する。
```

Cost robustness interpretation。

```text
C3_MIN15は30bps/30bpsでもA_FIXED_20BDを上回るが、replacement_rateは高い。
CAP5は30bps/30bpsでもA_FIXED_20BDを上回り、replacement_rateも大幅に低い。
Policy Yは30bps/30bpsではBaseline Aを下回る。
```

## 9. 2026 Focus

2026単年。

| policy | annual_return_2026 | annual_dd_2026 | annual_trade_count_2026 | annual_replacement_count_2026 |
| --- | ---: | ---: | ---: | ---: |
| A_FIXED_20BD | -0.001 | -0.278 | 70 | 0 |
| C3_MIN15_T2 | 0.604 | -0.135 | 45 | 30 |
| CAP5 | -0.055 | -0.257 | 65 | 20 |
| CAP4 | -0.096 | -0.262 | 58 | 14 |
| CAP3 | -0.124 | -0.267 | 63 | 12 |
| POLICY_Y_CAP4_EDGE08_CONF5 | 0.522 | -0.138 | 55 | 14 |
| COOLDOWN15 | 0.959 | -0.180 | 40 | 30 |

Interpretation。

```text
2026だけを見ると、C3_MIN15_T2 / COOLDOWN15 / Policy Y が強い。
CAP系は全期間では強いが、2026では弱い。
Phase8候補を1本に絞るならCAP5だが、2026耐性を見るならPolicy Yも併走比較する価値がある。
```

## 10. Answers To Phase7-F Questions

### replacement_rate 0.2-0.5で維持可能な最良Policy

```text
CAP5
```

理由。

```text
replacement_rate 0.484
cumulative_return_net 613.732
annualized_return_net 2.868
max_drawdown_net -0.336
30bps/30bpsでもBaseline Aを上回る
```

### cost耐性が最も高いPolicy

```text
C3_MIN15_T2
```

ただし、replacement_rate 0.814 のため実運用候補としては高回転すぎる。回転制約込みでは `CAP5` が最も良い。

### 2026で崩れにくいPolicy

```text
COOLDOWN15
C3_MIN15_T2
POLICY_Y_CAP4_EDGE08_CONF5
```

ただしCOOLDOWN15とC3_MIN15_T2はreplacement_rateが高い。Phase8候補としてはPolicy Yを補助比較に残す。

## 11. Recommended Policy TOP3

### 1. CAP5

```text
minimum_holding_days = 15
replacement_rank_threshold = Top50外
confirmation_days = 2
replacement_edge_margin = 0.02
replacement_cap_per_month = 5
settlement = conservative_T2_cash_unavailable
lot_size = 100
cash_buffer_ratio = 5%
max_position_weight = 20%
```

採用理由。

```text
replacement_rateを0.814から0.484へ低下。
累積return 613.732を維持。
30bps/30bpsでもA_FIXED_20BDを上回る。
Phase8 Broker Test / Paper Tradingの主候補。
```

### 2. CAP4

```text
minimum_holding_days = 15
replacement_cap_per_month = 4
その他はCAP5と同じ
```

採用理由。

```text
replacement_rate 0.399。
max_drawdown -0.282でCAP5より低い。
利益はCAP5より落ちるが、より保守的な比較候補として有効。
```

### 3. POLICY_Y_CAP4_EDGE08_CONF5

```text
minimum_holding_days = 15
replacement_cap_per_month = 4
replacement_edge_margin = 0.08
confirmation_days = 5
```

採用理由。

```text
replacement_rate 0.356。
2026 annual_return 0.522、annual_dd -0.138。
全期間returnはA_FIXED_20BDを下回るが、2026 weak-regimeの補助候補として価値がある。
```

## 12. Phase8 / Next Step

Phase8 Broker Test / Paper Trading候補。

```text
Primary:
CAP5

Conservative:
CAP4

2026 weak-regime guard comparison:
POLICY_Y_CAP4_EDGE08_CONF5

Reference only:
C3_MIN15_T2
```

Phase8前に確認したい論点。

```text
CAP5の2026弱さをEmergency / Defensive Reviewで補えるか
CAP5の30bps/30bps耐性をさらに細かく確認するか
税・部分約定・値幅制限・売買停止をどう近似するか
Paper TradingでREPLACE_SELL後のbuying power再取得をどう状態管理するか
```

