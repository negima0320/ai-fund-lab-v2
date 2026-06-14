# Phase7 Completion Audit And Phase8 Handoff

## 1. Completion Status

Phase7は、Capital Allocation Engine の設計、実装、検証、厳密会計、回転率抑制、最終統合バックテストまで完了した。

判定。

```text
PHASE7_COMPLETED_WITH_VALIDATED_CAPITAL_ALLOCATION_POLICY
```

初期資金。

```text
initial_capital = 1,000,000 JPY
```

## 2. Safety Audit

Phase7全体で以下は行っていない。

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

Phase7-G leakage audit。

| flag | value |
| --- | --- |
| status | PASS |
| no_future_data_in_decision | true |
| backtest_outcome_used_in_decision | false |
| future_price_used_in_decision | false |
| future_rank_used_in_decision | false |
| decision_evaluation_separated | true |

## 3. Phase7-A To F Summary

### Phase7-A

Capital Allocation Engine の最小実装。

```text
BUY
HOLD
REPLACE_SELL
REPLACE_BUY
EMERGENCY_EXIT
DEFENSIVE_REVIEW
NO_ACTION
```

をdecision recordとして出力できるようにした。

### Phase7-B

軽量validation。

結果。

```text
Phase7-A default は Top3 fixed hold を壊す
原因は高replacement_rate
```

### Phase7-C

full daily close path validation。

結果。

```text
Daily Top3 Sync は高回転すぎる
SELL_FIRST_BUY_AFTER_FILL と same-day は結果が大きく違う
```

### Phase7-D

実運用制約validation。

反映。

```text
100株単位
cash buffer
max_position_weight
transaction cost
slippage
replacement cap
cooldown
weekly/monthly reevaluation
```

### Phase7-E

Strict Long-Term Backtest / Exact Accounting。

結果。

```text
C3_MIN15_T2 は非常に強い
ただし replacement_rate 0.814 で高すぎる
```

### Phase7-F

Turnover Reduction & Robustness Validation。

結果。

```text
CAP5 が最良バランス
CAP4 が保守候補
POLICY_Y が2026 weak-regime比較候補
```

### Phase7-G

Final Integrated Backtest。

結果。

```text
CAP5をPrimary候補として確定
CAP4をConservative候補として確定
POLICY_YをWeak-regime comparisonとして確定
```

## 4. Final Adopted Candidates

### Primary: CAP5

```text
minimum_holding_days = 15
replacement_rank_threshold = Candidate Top50外
confirmation_days = 2
replacement_edge_margin = 0.02
replacement_cap_per_month = 5
settlement = conservative_T2_cash_unavailable
lot_size = 100
cash_buffer_ratio = 5%
max_position_weight = 20%
```

Phase7-G 0bps result。

| metric | value |
| --- | ---: |
| final_assets_net | 614,731,820 |
| cumulative_return_net | 613.732 |
| annualized_return_net | 2.868 |
| max_drawdown_net | -0.336 |
| win_rate | 0.607 |
| replacement_rate | 0.484 |

### Conservative: CAP4

```text
replacement_cap_per_month = 4
その他はCAP5と同じ
```

Phase7-G 0bps result。

| metric | value |
| --- | ---: |
| final_assets_net | 442,305,560 |
| cumulative_return_net | 441.306 |
| annualized_return_net | 2.609 |
| max_drawdown_net | -0.282 |
| win_rate | 0.633 |
| replacement_rate | 0.399 |

### Weak Regime: POLICY_Y_CAP4_EDGE08_CONF5

```text
replacement_cap_per_month = 4
replacement_edge_margin = 0.08
confirmation_days = 5
```

用途。

```text
2026 weak-regimeの比較監視用
全期間のPrimaryではない
```

## 5. Unresolved Risks

未解決リスク。

```text
税コスト未反映
部分約定未反映
値幅制限未反映
売買停止未反映
実スプレッド未反映
寄成 / 引成 / 指値など注文タイプ未確定
約定失敗時の状態遷移未実装
Broker buying powerとT+2 cashの実仕様差分未確認
2026 weak-regimeでCAP5が弱い
銘柄名・上場廃止・分割等の運用データ監査は未完了
```

## 6. Phase8 Handoff

Phase8の目的。

```text
Broker Test / Paper Trading
```

ただしPhase8開始時も、最初は実発注しない。

Phase8でやること。

```text
1. Broker snapshot取得のdry-run設計
2. holdings / cash / buying power / unsettled cash のmapping確認
3. CAP5 decisionをpaper ledgerに流す
4. SELL_FIRST_BUY_AFTER_FILL の状態遷移を実装
5. REPLACE_SELL約定後にREPLACE_BUYを再評価
6. lot / price / cash / orderable quantity のbroker仕様確認
7. order生成はdry-runから開始
8. Tachibana APIの実呼び出し前にmock / fixtureで監査
```

Phase8へ引き継ぐPrimary policy。

```text
CAP5
```

Phase8へ引き継ぐ比較policy。

```text
CAP4
POLICY_Y_CAP4_EDGE08_CONF5
A_FIXED_20BD
C3_MIN15_T2 reference only
```

## 7. Phase8 Gate Conditions

Phase8でlive orderへ進む前の必須条件。

```text
Paper Tradingで30営業日以上のdecision ledgerが安定
cash / holdings / buying powerの差分が説明可能
REPLACE_SELLとREPLACE_BUYが同時実行されていない
orderable quantityが100株単位で正しい
skip理由が全て記録されている
API failure時に注文しない
duplicate orderが発生しない
ユーザー承認なしにlive orderへ進まない
```

