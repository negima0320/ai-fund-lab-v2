# Phase5-A Opportunity AI Design Document

作成日: 2026-06-14

## 1. 目的

この資料は、AI Fund Lab vNext Phase5 Opportunity AI の実装前設計を定義する。

Phase4 Candidate AI は、全銘柄から上昇候補 Top50 を抽出する目的を達成した。Phase5 では、その Candidate Top50 を入力として、候補銘柄の期待値を判定し、期待値が高い買い候補を 5 銘柄程度へ順位付けする。

Opportunity AI は「地雷除去専用AI」ではない。主責務は、Candidate 群の中から最も期待値が高い銘柄を選ぶことである。downside risk、drawdown、no_buy_reason は、期待値評価を構成するリスク評価要素として扱う。

Phase5-A では設計のみを行う。実装、学習、推論、backtest、Paper Trading、Broker API、発注、資金配分、promotion、reader switch は行わない。

## 2. Opportunity AI の責務

Opportunity AI がやること:

```text
Candidate AI が抽出した候補50銘柄を順位付けする
Candidate 群の中で期待値を比較する
期待値が高い買い候補5銘柄程度へ絞る
expected_edge_score を出す
buy_rank を出す
expected_return_horizon を出す
downside_risk_score を出す
buy_reason / no_buy_reason を出す
```

Opportunity AI がやらないこと:

```text
全銘柄から候補を抽出しない
保有継続を判断しない
売却を判断しない
購入株数を決めない
購入金額を決めない
資金配分をしない
発注しない
Broker API を呼ばない
Paper Trading を行わない
Portfolio を更新しない
Annual Return / final_assets を評価しない
```

Opportunity AI の問い:

```text
Candidate AI が抽出した候補の中で、
どの銘柄が最も期待値が高いか？
```

## 3. Candidate AI との境界

Candidate AI:

```text
全銘柄から上昇候補を抽出する
4000銘柄程度 -> Top50
candidate_list を出す
candidate_score を出す
candidate_reason を出す
```

Opportunity AI:

```text
Candidate Top50 の中で期待値を比較する
Top50 -> Top5 / Top10 / Top20
expected_edge_score を出す
buy_rank を出す
downside_risk_score を出す
buy_reason / no_buy_reason を出す
```

重要:

```text
Candidate score は買い順位ではない
Opportunity AI は candidate_score を参考情報として使える
ただし buy_rank は expected_edge_score に基づいて決める
Phase5 で Phase4 Candidate AI 自体を修正しない
```

## 4. 後続 Phase との境界

Position Management AI:

```text
購入後の保有継続を判断する
売却を判断する
ADD / REDUCE を判断する
```

Capital Allocation Engine:

```text
購入金額を決める
購入株数を決める
資金配分を決める
```

Broker / Order / Paper Trading:

```text
Broker API 接続は Phase5 対象外
Paper Trading は Phase5 対象外
実発注は Phase5 対象外
Order Manager は Phase5 対象外
```

Opportunity AI の出力は、後続 Phase が使う買い候補順位である。実際に買う金額、買う株数、保有後の売却判断は Phase5 の責務ではない。

## 5. 入力データ

### 5.1 Candidate AI 出力

```text
candidate_list
candidate_score
candidate_reason
candidate_rank
target_date
code
feature_version
model_version
inference_run_id
```

`candidate_score` の扱い:

```text
上流の候補抽出スコアとして扱う
期待値の prior としては使える
buy_rank に直結しない
score が高いほど安全とは仮定しない
```

### 5.2 市場データ

```text
価格
出来高
高値
安値
```

### 5.3 テクニカル

```text
価格モメンタム
出来高モメンタム
トレンド強度
ボラティリティ
```

Phase4 feature からの再利用候補:

```text
price_momentum_return_5d
price_momentum_return_20d
price_momentum_return_60d
volume_momentum_ratio_5d
volume_momentum_ratio_1d_20d
trend_close_over_ma_20d
trend_ma_5_20_ratio
trend_ma_20_60_ratio
volatility_return_std_20d
liquidity_avg_volume_20d
```

### 5.4 ファンダメンタル

```text
売上成長
利益成長
ROE
財務健全性
```

候補 feature:

```text
sales_growth_rate
operating_profit_growth_rate
ordinary_profit_growth_rate
net_income_growth_rate
roe
equity_ratio
operating_margin
earnings_revision_signal
```

財務情報は、`as_of_date` 時点で公表済みのものだけを使う。

### 5.5 市場環境

```text
TOPIX
市場トレンド
セクター強弱
```

候補 feature:

```text
topix_return_5d
topix_return_20d
topix_ma_5_20_ratio
market_regime
market_risk_flag
sector_return_20d
sector_rank_20d
stock_vs_sector_return_20d
sector_momentum_flag
```

TOPIX、市場トレンド、セクター強弱は、`as_of_date` 時点で観測可能な feature として設計する。評価後にしか分からない regime label や future 情報を推論 feature に混入させない。

## 6. 利用禁止データ

以下は入力 feature として使うこと、推論時に参照することを禁止する。

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
```

また以下も禁止する。

```text
trade_result
trade_profit
selected
bought
sold
cash
portfolio
annual_return
final_assets
```

禁止対象:

```text
feature table
training dataset の feature columns
inference input
selection logic
buy_rank 生成ロジック
```

例外:

```text
future_return_* などの future 系データは、
system_requirements.md の学習データ要件に従い、
学習・評価ラベルとしてのみ利用可能。
```

## 7. 出力

Opportunity AI は以下を出力する。

```text
target_date
code
expected_edge_score
buy_rank
expected_return_horizon
downside_risk_score
buy_reason
no_buy_reason
candidate_score
candidate_rank
model_version
feature_version
inference_run_id
created_at
```

### 7.1 expected_edge_score

期待値スコア。

```text
上昇余地
勝率
下落リスク
ドローダウン
トレンド継続性
市場環境
流動性
```

を統合したスコアとする。

### 7.2 buy_rank

購入候補順位。

```text
expected_edge_score が高い順に付与する
Top5 を主な買い候補とする
Top10 / Top20 は監査・比較用にも出す
```

### 7.3 expected_return_horizon

期待値評価の対象期間。

初期案:

```text
20営業日
```

システム要件の保有期間 5〜30 営業日に合わせ、Phase5 初期は 20 営業日を中心に設計する。

### 7.4 downside_risk_score

期待値を減点するリスクスコア。

```text
下落リスク
最大ドローダウンリスク
過熱リスク
短期 volume surge リスク
市場悪化リスク
低流動性リスク
```

を表現する。

これは Opportunity AI の主目的ではなく、expected_edge_score の構成要素である。

### 7.5 buy_reason

例:

```text
企業品質良好
価格モメンタム強い
トレンド継続性が高い
流動性が十分
市場環境良好
セクター強弱が追い風
上昇余地に対してリスクが許容範囲
```

### 7.6 no_buy_reason

例:

```text
期待値不足
リスク過大
市場環境悪化
トレンド確認不足
短期出来高急増が過熱寄り
ドローダウンリスクが高い
流動性不足
```

`no_buy_reason` は「地雷除去」を主目的にするためではなく、期待値が低い理由を説明可能にするために出す。

## 8. Label 設計方針

Opportunity AI は期待値を学習する。

入力 feature ではなく、学習・評価ラベル候補として扱うもの:

```text
future_return_20d
future_max_return_20d
future_max_drawdown_20d
downside_bad_20d
top_decile_20d
```

expected_edge_score の label は、単純な future_return だけでなく、以下を統合して設計する。

```text
将来リターン
上昇余地
勝率
下落リスク
最大ドローダウン
top decile 捕捉
```

初期 label 案:

```text
expected_edge_label_20d
  future_return_20d
  + future_max_return_20d
  - drawdown_penalty(future_max_drawdown_20d)
  - downside_penalty(downside_bad_20d)
  + top_decile_bonus(top_decile_20d)
```

分類 label 候補:

```text
opportunity_positive_20d
high_expected_edge_20d
top_decile_20d
downside_bad_20d
```

回帰 label 候補:

```text
risk_adjusted_future_return_20d
future_return_20d
future_max_return_20d
future_max_drawdown_20d
```

Phase5-B で、閾値、重み、positive / negative 定義、neutral 扱いを固定する。

## 9. 評価指標

Opportunity AI 単体の評価指標:

```text
selected_mean_future_return
selected_mean_future_max_return
selected_top_decile_rate
selected_downside_bad_rate
```

CandidateTop50 との比較:

```text
CandidateTop50 平均 vs OpportunityTop5
CandidateTop50 平均 vs OpportunityTop10
CandidateTop50 平均 vs OpportunityTop20
```

比較観点:

```text
mean_future_return_20d
mean_future_max_return_20d
top_decile_rate_20d
downside_bad_rate_20d
future_max_drawdown_20d
win_rate_20d
```

成功条件:

```text
OpportunityTop5 / Top10 / Top20 の期待値が CandidateTop50 平均を上回る
selected_mean_future_return が改善する
selected_mean_future_max_return が改善または十分維持される
selected_top_decile_rate が改善する
selected_downside_bad_rate が悪化しない、可能なら低下する
```

失敗条件:

```text
CandidateTop50 と差がない
candidate_score の並べ替えだけになっている
selected_downside_bad_rate が大きく悪化する
future_max_return_20d 型の上昇候補捕捉を大きく失う
down regime で品質劣化を制御できない
```

Opportunity AI 単体では以下を評価しない。

```text
annual_return
final_assets
portfolio drawdown
profit factor
actual trade result
```

これらは後続の統合評価、Paper Trading、Historical Evaluation の責務である。

## 10. Phase4 結果の反映

Phase4 で分かったこと:

```text
Candidate AI は future_max_return_20d 型の上昇候補捕捉に強い
Candidate score 単体では Best / Worst を分離しきれない
高 score 候補にも downside risk が混ざる
down regime では候補品質が悪化する
volume surge は Winner より Worst 側でも高く、単純加点に向かない
```

Opportunity Score への反映:

```text
candidate_score は prior として扱い、buy_rank に直結しない
future_max_return 型の捕捉力を維持する評価指標を置く
future_return_20d と drawdown を合わせて期待値を評価する
downside_risk_score を expected_edge_score の減点要素にする
volume surge は単純加点ではなく、持続性・過熱度とセットで評価する
market regime / TOPIX / セクター強弱を観測可能 feature として設計する
```

Phase5 でやらないこと:

```text
Phase4 Candidate AI を修正しない
Candidate Top50 の作成条件を future label で変えない
Candidate score を買い順位として扱わない
```

## 11. Regime / 市場環境の扱い

Opportunity AI は、市場環境を期待値評価の一部として扱う。

利用候補:

```text
TOPIX return
TOPIX moving average ratio
TOPIX volatility
market trend
sector relative strength
sector rank
stock vs sector return
```

Regime 設計方針:

```text
up regime:
  上昇余地と trend continuation を素直に評価しやすい

flat regime:
  expected edge と downside risk のバランスを重視する

down regime:
  expected_edge_score の閾値を厳しくする
  downside_risk_score の重みを上げる
  Top5 への絞り込みを強める

unknown regime:
  保守的に扱う
```

禁止:

```text
future 情報を使った regime label を推論 feature に使わない
評価後にしか分からない up / flat / down 判定を feature にしない
post-selection return を regime 判定に使わない
```

Regime feature は、必ず `as_of_date` 時点で観測可能な market data だけで作る。

## 12. Leakage Audit 方針

Phase5 では、入力 feature と label / evaluation data を明確に分離する。

入力 feature 一覧:

```text
candidate_score
candidate_rank
candidate_reason encoded features
price
volume
high
low
price_momentum_features
volume_momentum_features
trend_features
volatility_features
quality_features
liquidity_features
TOPIX_features
market_trend_features
sector_strength_features
```

禁止列一覧:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
trade_result
trade_profit
selected
bought
sold
cash
portfolio
annual_return
final_assets
```

監査項目:

```text
forbidden_feature_columns が 0 件である
future 系列が feature table に存在しない
trade 結果系列が feature table に存在しない
portfolio 系列が feature table に存在しない
inference path が label table を読まない
as_of_date <= target_date を満たす
財務情報は公表日 <= as_of_date のものだけ使う
TOPIX / sector feature は as_of_date 以前の情報だけで作る
same target_date が train / validation / test にまたがらない
```

監査出力候補:

```text
leakage_audit_status
forbidden_feature_column_count
future_column_in_feature_count
trade_result_column_in_feature_count
portfolio_column_in_feature_count
as_of_date_violation_count
label_feature_overlap_count
regime_observability_status
```

## 13. Artifact Policy

Phase5 は Phase4 成果物を破壊しない。

読み取り候補:

```text
Phase4 formal Candidate inference output
Phase4 feature table
Phase4 label table
reports/candidate_ai/full_range/
reports/candidate_ai/final_check/
```

書き込み候補:

```text
reports/opportunity_ai/phase5a/
reports/opportunity_ai/phase5b/
reports/opportunity_ai/phase5c/
reports/opportunity_ai/phase5d/
models/opportunity_ai/
```

禁止:

```text
Phase4 成果物を破壊しない
mock path を上書きしない
promotion を行わない
reader switch を行わない
Broker path を更新しない
Portfolio path を更新しない
```

## 14. Phase5-B 以降のロードマップ

```text
Phase5-B Opportunity Label Design
Phase5-C Opportunity Feature Design / Expansion
Phase5-D Candidate Top50 to Opportunity Dataset Builder
Phase5-E Opportunity Model Training
Phase5-F Opportunity Inference
Phase5-G Opportunity Quality Audit
Phase5-H Candidate + Opportunity Combined Validation
```

Phase5-B:

```text
expected_edge_label_20d を具体化する
future_return_20d / future_max_return_20d / future_max_drawdown_20d / downside_bad_20d / top_decile_20d の扱いを固定する
label schema と label audit を定義する
```

Phase5-C:

```text
Opportunity feature schema を固定する
Candidate feature 再利用列を固定する
TOPIX / market trend / sector strength feature を as_of_date ルール込みで設計する
```

Phase5-D:

```text
Candidate Top50 だけを母集団にした Opportunity dataset を設計・生成する
feature / label / split / audit の分離を守る
```

Phase5-E:

```text
expected_edge_score を学習する model を作る
rule baseline と model を比較する
```

Phase5-F:

```text
latest target_date の Candidate Top50 から Opportunity TopN を出す
```

Phase5-G:

```text
OpportunityTop5 / Top10 / Top20 の品質を監査する
```

Phase5-H:

```text
Candidate + Opportunity の combined validation を行う
CandidateTop50 から OpportunityTopN へ絞った改善を確認する
```

## 15. Phase5-A 結論

Phase5 Opportunity AI は、Candidate AI が抽出した候補50銘柄の中から、期待値が高い買い候補を順位付けする AI として設計する。

主出力は `expected_edge_score` と `buy_rank` である。`downside_risk_score` と `no_buy_reason` は重要だが、地雷除去を主目的にするためではなく、期待値をリスク調整して説明可能にするための構成要素である。

Phase4 の成果は、Candidate AI が future_max_return_20d 型の上昇候補を捕捉できる一方、Candidate score 単体では期待値の高低や downside risk を分離しきれない、という前提として反映する。Phase5 では Phase4 Candidate AI を修正せず、Candidate Top50 の中で期待値を比較し、Top5 / Top10 / Top20 の quality lift を評価する。

この資料により、Phase5-B Opportunity Label Design に進める状態になった。
