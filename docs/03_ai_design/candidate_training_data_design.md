# AI Fund Lab vNext Candidate Training Data Design

---

# 1. このドキュメントの目的

本ドキュメントは、Phase4-B Candidate Training Data Design として、Candidate AI の学習データ設計を定義する。

Phase4-Bの目的は、Candidate AIを学習させる前に以下を固定することである。

```text
feature table schema
label table schema
training dataset schema
audit table schema
as_of_date rule
target_date rule
lookback window rule
future label isolation
train/validation/test split rule
leakage audit rule
candidate selection evaluation rule
```

Phase4-Bでは設計のみを行う。

Phase4-Bで実装しないこと:

```text
feature builder本体
dataset builder本体
label生成本体
Candidate AI本体
学習処理
推論処理
バックテスト
Historical Evaluation
Opportunity AI
Position Management AI
Capital Allocation
Paper Trading
Order Manager
Broker実API接続
発注
売買
Portfolio自動更新
```

---

# 2. Candidate AIの責務境界

Candidate AIがやること:

```text
全銘柄から見る価値がある上昇候補を抽出する
candidate_scoreを出す
candidate_reasonを出す
excluded_reasonを出す
```

Candidate AIがやらないこと:

```text
買い判断
期待値判断
購入金額判断
保有判断
売却判断
資金配分
Paper Trading
発注
売買
Portfolio更新
```

Candidate AIの学習データは、候補抽出の品質を上げるためだけに使う。買うべきか、どれだけ買うか、保有するか、売るかは後続Phaseの責務である。

---

# 3. 利用可能データ

Phase4-Bで利用可能とする市場データ:

```text
2021-06以降の実市場データ
daily_quotes_normalized
listed issue master
trading calendar
fins summary
market index data
sector aggregation data
```

`daily_quotes_normalized` は価格・出来高featureの正規入力である。raw v1は原本証跡であり、Candidate training featureには原則として直接使わない。

---

# 4. 禁止feature

以下はfeatureとして利用禁止である。

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
backtest result
trade result
selected
bought
sold
cash
portfolio
annual_return
final_assets
paper_trade
position
allocation
order
execution
profit
loss
pnl
```

禁止対象は、feature table、training dataset の feature列、推論時参照、candidate selection logic への混入である。

future系は label table と evaluation table には持ってよい。ただし feature table とは物理的・論理的に分離する。

---

# 5. 日付ルール

## 5.1 target_date rule

`target_date` は、Candidate AIが候補を抽出する対象営業日である。

ルール:

```text
target_date は trading calendar 上の営業日を原則とする
target_date の日次確定後に候補生成する前提とする
target_date の当日OHLCVを使う場合は、日次確定後データのみを使う
target_date より後の価格、出来高、財務、売買、評価結果はfeatureに使わない
```

## 5.2 as_of_date rule

`as_of_date` は、feature作成時点で観測可能な情報の上限日である。

最重要ルール:

```text
featureは as_of_date 時点で観測可能な情報のみで作る
```

原則:

```text
as_of_date <= target_date
日次確定後に作るfeatureでは as_of_date = target_date を許可する
財務情報は公表日 <= as_of_date のものだけ利用する
listed issue master は as_of_date 時点で有効な情報だけ利用する
market index / sector aggregation は as_of_date 以前の情報だけ利用する
```

## 5.3 future label isolation

ラベルは `target_date` 以降のfuture情報から作る。

ルール:

```text
future情報は label table にのみ保存する
future情報を feature table に保存しない
feature table と label table は別schema・別保存先にする
training dataset を作る時は feature columns と label columns を明示的に分離する
推論時には label table を読まない
```

---

# 6. lookback window rule

lookback window は、feature計算に使う過去営業日の範囲である。

基本window:

```text
5営業日
10営業日
20営業日
60営業日
```

ルール:

```text
lookback window は target_date 以前の営業日だけを含む
価格・出来高featureは daily_quotes_normalized の target_date 以前だけを使う
window日数に満たない銘柄は insufficient_history_flag を立てる
履歴不足の銘柄を無理に未来データで補完しない
非営業日はwindowに数えない
```

---

# 7. feature table schema

feature table は、Candidate AIが観測可能な説明変数だけを保持する。

主キー:

```text
target_date
code
feature_version
```

必須メタ列:

```text
target_date
as_of_date
code
feature_version
source_snapshot_id
data_start_date
data_end_date
created_at
feature_set_name
```

featureカテゴリ列:

```text
quality_features
price_momentum_features
volume_momentum_features
liquidity_tradability_features
market_environment_features
sector_relative_strength_features
exclusion_risk_filter_features
```

代表feature列:

```text
sales_growth_rate
operating_profit_growth_rate
ordinary_profit_growth_rate
net_income_growth_rate
roe
equity_ratio
operating_margin
earnings_revision_signal
return_5d
return_20d
return_60d
ma_5_20_ratio
ma_20_60_ratio
close_to_20d_high
close_to_60d_high
new_20d_high_flag
new_60d_high_flag
breakout_strength
volatility_20d
volume_ratio_5d_20d
volume_ratio_1d_20d
volume_surge_flag
volume_trend_20d
avg_volume_20d
avg_turnover_20d
low_liquidity_flag
tradable_flag
topix_return_5d
topix_return_20d
topix_ma_5_20_ratio
market_regime
market_risk_flag
sector_return_20d
sector_rank_20d
stock_vs_sector_return_20d
sector_momentum_flag
supervision_flag
delisting_risk_flag
extreme_low_price_flag
abnormal_price_move_flag
insufficient_history_flag
```

feature table に入れない列:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
candidate_label
backtest result
trade result
portfolio
order
profit
loss
pnl
```

---

# 8. label table schema

label table は、学習・評価用の将来結果だけを保持する。

主キー:

```text
target_date
code
label_version
```

必須メタ列:

```text
target_date
code
label_version
label_horizon
future_start_date
future_end_date
created_at
source_snapshot_id
```

ラベル候補:

```text
future_return_5d
future_return_10d
future_return_20d
future_max_return_20d
future_max_drawdown_20d
top_decile_20d
downside_bad_20d
momentum_candidate_label
```

`momentum_candidate_label` の初期案:

```text
top_decile_20d == true
かつ
downside_bad_20d == false
```

ただし、閾値はPhase4-C以降で実データ分布を見て確定する。

label table の注意:

```text
label table は推論時に読まない
label table はfeature生成前にjoinしない
label table は評価・学習時のみfeature tableとtarget_date/codeでjoinする
```

---

# 9. training dataset schema

training dataset は、feature table と label table を学習用に結合した論理datasetである。

主キー:

```text
target_date
code
dataset_version
```

必須メタ列:

```text
target_date
as_of_date
code
dataset_version
feature_version
label_version
split
created_at
```

feature columns:

```text
feature table のfeature列のみ
```

label columns:

```text
future_return_5d
future_return_10d
future_return_20d
future_max_return_20d
future_max_drawdown_20d
top_decile_20d
downside_bad_20d
momentum_candidate_label
```

重要:

```text
training dataset では feature columns と label columns を列名prefixまたはschemaで明示的に分離する
推論用datasetには label columns を含めない
```

---

# 10. audit table schema

audit table は、学習データ生成とleakage確認の証跡を保持する。

主キー:

```text
audit_id
target_date
code
```

必須列:

```text
audit_id
target_date
as_of_date
code
feature_version
label_version
dataset_version
source_snapshot_id
feature_generated_at
label_generated_at
dataset_generated_at
leakage_check_status
leakage_check_messages
forbidden_feature_detected
future_label_isolated
split
excluded_reason
candidate_reason_coverage_ready
created_at
```

audit status:

```text
OK
WARNING
ERROR
```

ERROR条件:

```text
feature table にfuture系列が存在する
feature table にbacktest/trade/portfolio/order由来列が存在する
as_of_date > target_date
財務情報の公表日 > as_of_date
ランダム分割が使われている
```

---

# 11. train/validation/test split rule

分割は必ず時系列順に行う。

ランダム分割は禁止である。

推奨分割:

```text
Train:      2021-06 ～ 2024-12
Validation: 2025-01 ～ 2025-12
Test:       2026-01 ～
```

実データ範囲に応じて調整してよいが、以下を必須とする。

```text
Train終了日 < Validation開始日
Validation終了日 < Test開始日
未来期間を過去期間の学習に混ぜない
同一target_dateが複数splitにまたがらない
銘柄単位のランダム分割を行わない
```

初期split列:

```text
train
validation
test
```

---

# 12. leakage audit rule

leakage audit は、training dataset 作成前後で必ず実施する。

必須チェック:

```text
1. as_of_date <= target_date
2. feature table に future_return_* が存在しない
3. feature table に future_max_return_* が存在しない
4. feature table に future_max_drawdown_* が存在しない
5. feature table に top_decile_* が存在しない
6. feature table に downside_bad_* が存在しない
7. feature table に backtest/trade/selected/bought/sold/cash/portfolio/order/execution/profit/loss/pnl が存在しない
8. 財務featureは公表日 <= as_of_date のデータだけを使う
9. 価格・出来高featureは target_date 以前の daily_quotes_normalized だけを使う
10. split は時系列分割でありランダム分割ではない
11. 推論用datasetに label columns が存在しない
```

leakage audit が ERROR の場合、学習に進まない。

---

# 13. candidate selection evaluation rule

Candidate AI単体はAnnual Returnでは直接評価しない。

評価目的:

```text
候補品質向上
```

評価指標:

```text
candidate_mean_future_return
candidate_mean_future_max_return
candidate_downside_bad_rate
candidate_top_decile_rate
candidate_count
excluded_count
reason_coverage
```

評価ルール:

```text
全銘柄平均と候補群平均を比較する
候補数が50銘柄程度に収まるか確認する
excluded_reason が十分に付与されるか確認する
candidate_reason が十分に付与されるか確認する
Validationで閾値を調整し、Testは最終確認に使う
Test結果を見てからTrain/Validationの設計を作り直さない
```

---

# 14. Phase4-B完了条件

Phase4-Bは以下を満たせば完了とする。

```text
feature table schema が定義されている
label table schema が定義されている
training dataset schema が定義されている
audit table schema が定義されている
as_of_date rule が定義されている
target_date rule が定義されている
lookback window rule が定義されている
future label isolation が定義されている
train/validation/test split rule が時系列分割として定義されている
ランダム分割禁止が明記されている
leakage audit rule が定義されている
candidate selection evaluation rule が定義されている
禁止feature一覧が明記されている
Phase4-Bでは学習・推論・backtest・Paper Trading・発注を実装していない
```

---

# 15. Phase4-Cへの引き継ぎ

Phase4-C案:

```text
Candidate Feature Builder Design
```

Phase4-Cで決めること:

```text
feature builderの入出力設計
daily_quotes_normalized からの価格・出来高feature生成仕様
fins summary の公表日反映仕様
sector aggregation の生成仕様
feature_version管理
runtime保存先
leakage auditの実装計画
mock fixture設計
```

Phase4-Cでも、AI学習、推論、backtest、Paper Trading、発注はまだ実装しない。
