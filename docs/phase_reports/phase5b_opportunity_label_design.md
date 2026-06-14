# Phase5-B Opportunity Label Design

作成日: 2026-06-14

## 1. 目的

この資料は、Phase5 Opportunity AI が学習・評価に使う label 設計を定義する。

Phase5 Opportunity AI の責務は、Candidate AI が抽出した Candidate Top50 の中で期待値を比較し、買い候補 Top5 / Top10 / Top20 へ順位付けすることである。地雷除去専用AIではない。`downside_risk_score` と `no_buy_reason` は、`expected_edge_score` を構成するリスク評価・説明要素として扱う。

Phase5-B では label 設計のみを行う。実装、学習、推論、backtest、Paper Trading、Broker API、発注、資金配分、Phase4 成果物の変更、promotion、reader switch は行わない。

## 2. Label 設計の基本方針

Opportunity AI は期待値を学習する。

そのため、単純な `future_return_20d` だけを目的変数にしない。以下を統合して `expected_edge_label_20d` を定義する。

```text
future_return_20d
future_max_return_20d
future_max_drawdown_20d
downside_bad_20d
top_decile_20d
```

設計方針:

```text
20営業日後のリターンを重視する
20営業日以内の上昇余地も評価する
Candidate AI の future_max_return_20d 捕捉力を殺しすぎない
ただし downside risk / drawdown risk が高い候補は減点する
Candidate Top50 内で期待値順位を学べる label にする
future 系データは入力 feature に使わない
future 系データは学習・評価 label としてのみ使う
```

## 3. Label 生成単位

Phase5 label の生成単位:

```text
1 row = target_date + code in Candidate Top50
```

母集団:

```text
Phase4 Candidate AI が feature-only inference で抽出した Candidate Top50
```

重要:

```text
future label を使って Candidate Top50 を作り直さない
Candidate Top50 外の銘柄を Phase5 Opportunity label の母集団に混ぜない
Candidate score を label には使わない
Candidate score は Phase5-C 以降の feature 候補として扱う
```

## 4. Label Horizon

Phase5-B の正式 horizon:

```text
20営業日
```

理由:

```text
system_requirements.md の基本保有期間は 5〜30営業日
Phase4 Candidate AI は 20営業日内の future_max_return 捕捉に強い
Phase5 Opportunity AI は 20営業日内の期待値を比較する初期設計にする
```

将来拡張候補:

```text
5営業日 label
10営業日 label
30営業日 label
```

ただし Phase5-B の正式設計では 20営業日を基準にする。

## 5. Raw Future Label

### 5.1 future_return_20d

定義:

```text
future_return_20d = Close_{t+20} / Close_t - 1
```

用途:

```text
20営業日後の実現リターン
期待値 label の中心要素
selected_mean_future_return の評価
positive / neutral / negative 判定
```

扱い:

```text
expected_edge_label_20d では加点要素
risk_adjusted_future_return_20d のベース
入力 feature には使わない
推論時には参照しない
```

注意:

```text
future_return_20d だけを目的変数にしない
一時的に大きく上昇したが20営業日後に失速した候補は、future_max_return_20d と drawdown も合わせて評価する
```

### 5.2 future_max_return_20d

定義:

```text
future_max_return_20d = max(High_{t+1..t+20}) / Close_t - 1
```

用途:

```text
20営業日以内の最大上昇余地
Candidate AI が得意な「一度大きく吹く銘柄」の捕捉力を評価する
selected_mean_future_max_return の評価
top_decile_20d の候補要素
```

扱い:

```text
expected_edge_label_20d では加点要素
ただし future_return_20d や drawdown と併用する
future_max_return_20d 単独で positive 判定しない
入力 feature には使わない
推論時には参照しない
```

注意:

```text
future_max_return_20d を完全に無視すると Phase4 Candidate AI の強みを殺す
future_max_return_20d だけを重視すると一時的な吹き上げ候補を過大評価する
```

### 5.3 future_max_drawdown_20d

定義:

```text
future_max_drawdown_20d = min(Low_{t+1..t+20} / Close_t - 1)
```

値の符号:

```text
0 以下の値を想定する
-0.10 は 20営業日内に -10% まで下落したことを表す
```

用途:

```text
最大下落リスク
expected_edge_label_20d の減点要素
risk_adjusted_future_return_20d の penalty
downside_bad_20d 判定の材料
```

扱い:

```text
drawdown が大きいほど expected_edge_label_20d を減点する
一定閾値を超える drawdown は negative 判定の強い根拠にする
入力 feature には使わない
推論時には参照しない
```

### 5.4 downside_bad_20d

定義案:

```text
downside_bad_20d = true if:
  future_max_drawdown_20d <= -0.10
  or future_return_20d <= -0.05
```

初期閾値案:

```text
max_drawdown threshold: -10%
terminal_return threshold: -5%
```

用途:

```text
明確な downside risk の binary label
expected_edge_label_20d の減点要素
selected_downside_bad_rate の評価
downside_risk_score 学習の補助 label
```

扱い:

```text
downside_bad_20d == true の候補は expected_edge_label_20d で強く減点する
ただし future_max_return_20d が高い候補を一律除外するための label にはしない
期待値評価の risk component として使う
入力 feature には使わない
推論時には参照しない
```

### 5.5 top_decile_20d

定義案:

```text
top_decile_20d = true if:
  target_date の Candidate Top50 内で
  risk_adjusted_future_return_20d が上位10%以内
```

代替定義候補:

```text
target_date の Candidate Top50 内で future_return_20d が上位10%以内
target_date の Candidate Top50 内で future_max_return_20d が上位10%以内
全 eligible universe 内で risk_adjusted_future_return_20d が上位10%以内
```

Phase5-B の推奨:

```text
Candidate Top50 内の risk_adjusted_future_return_20d 上位10%を正式候補にする
```

理由:

```text
Opportunity AI は Candidate Top50 内で順位付けするAIである
future_return だけでなく downside / drawdown を含む期待値順位にしたい
```

用途:

```text
classification label
precision@5 / precision@10 / precision@20
selected_top_decile_rate
CandidateTop50 -> OpportunityTopN の lift 評価
```

## 6. risk_adjusted_future_return_20d

正式定義案:

```text
risk_adjusted_future_return_20d =
  0.60 * clipped_future_return_20d
  + 0.30 * clipped_future_max_return_20d
  - 0.30 * drawdown_penalty_20d
  - 0.20 * downside_bad_penalty_20d
```

各要素:

```text
clipped_future_return_20d:
  clip(future_return_20d, -0.30, 0.50)

clipped_future_max_return_20d:
  clip(future_max_return_20d, 0.00, 0.80)

drawdown_penalty_20d:
  min(abs(future_max_drawdown_20d), 0.30)

downside_bad_penalty_20d:
  1.0 if downside_bad_20d == true else 0.0
```

設計意図:

```text
future_return_20d を中心に置く
future_max_return_20d も残し、Phase4 Candidate AI の強みを維持する
future_max_drawdown_20d と downside_bad_20d でリスク調整する
極端値は clip して label を過度に支配させない
```

注意:

```text
この定義は Phase5-B の初期正式案であり、Phase5-E の学習前監査で分布を確認する
閾値や重みは label audit 結果で改訂候補にできる
ただし改訂する場合も、feature への future 混入は禁止する
```

## 7. expected_edge_label_20d

正式定義:

```text
expected_edge_label_20d = risk_adjusted_future_return_20d
```

目的:

```text
Opportunity AI が学習する期待値 label
expected_edge_score の教師信号
Candidate Top50 内の buy_rank 学習の基礎
```

意味:

```text
高い:
  20営業日後リターン、20営業日内上昇余地、drawdown risk のバランスが良い

低い:
  リターンが低い、上昇余地が乏しい、または downside / drawdown が重い
```

重要:

```text
expected_edge_label_20d は future data 由来なので入力 feature ではない
学習・評価 label としてのみ保存する
推論時には存在しない
```

## 8. Classification Label 候補

### 8.1 opportunity_positive_20d

定義案:

```text
opportunity_positive_20d = true if:
  expected_edge_label_20d > 0
  and downside_bad_20d == false
```

用途:

```text
binary classifier
precision / recall
OpportunityTopN の positive rate
```

### 8.2 high_expected_edge_20d

定義案:

```text
high_expected_edge_20d = true if:
  target_date の Candidate Top50 内で
  expected_edge_label_20d が上位20%以内
```

用途:

```text
Top10 相当の候補を学習する classification label
Candidate Top50 内順位学習の補助
```

### 8.3 top_decile_20d

定義:

```text
target_date の Candidate Top50 内で
expected_edge_label_20d が上位10%以内
```

用途:

```text
Top5 相当の候補を評価する label
selected_top_decile_rate
precision@5
```

### 8.4 downside_bad_20d

定義:

```text
future_max_drawdown_20d <= -0.10
or future_return_20d <= -0.05
```

用途:

```text
downside_risk_score の補助教師
selected_downside_bad_rate の評価
no_buy_reason の評価材料
```

## 9. Regression Label 候補

主 label:

```text
expected_edge_label_20d
risk_adjusted_future_return_20d
```

補助 regression label:

```text
future_return_20d
future_max_return_20d
future_max_drawdown_20d
```

用途:

```text
expected_edge_score model の主目的変数
multi-task training の補助目的
quality audit の分解評価
```

注意:

```text
補助 regression label を feature として使わない
推論時に補助 regression label を参照しない
```

## 10. Positive / Neutral / Negative 閾値案

Phase5-B 初期閾値案:

```text
positive:
  expected_edge_label_20d >= 0.05
  and downside_bad_20d == false

neutral:
  -0.03 < expected_edge_label_20d < 0.05
  and downside_bad_20d == false

negative:
  expected_edge_label_20d <= -0.03
  or downside_bad_20d == true
```

解釈:

```text
positive:
  買い候補として期待値がある

neutral:
  上昇余地または安全性が不十分で、Top5 には弱い

negative:
  期待値不足または下落リスクが重い
```

閾値の扱い:

```text
Phase5-D dataset 生成後に分布を監査する
positive が極端に少ない、または多すぎる場合は Phase5-B 改訂資料で調整する
調整時も future 系は label 側に閉じ込める
```

## 11. Candidate Top50 内の相対順位 Label

Opportunity AI は Candidate Top50 内の順位付けAIであるため、同一 `target_date` 内の相対順位 label を持つ。

### 11.1 opportunity_rank_label_20d

定義:

```text
target_date ごとに Candidate Top50 を expected_edge_label_20d の降順で並べた順位
1 が最良
```

用途:

```text
ranking model
Top5 / Top10 / Top20 評価
CandidateTop50 内の相対比較
```

### 11.2 opportunity_quantile_label_20d

定義:

```text
target_date の Candidate Top50 内で expected_edge_label_20d を5分位に分ける
```

値:

```text
Q5: 上位20%
Q4
Q3
Q2
Q1: 下位20%
```

用途:

```text
classification / ordinal model
rank monotonicity audit
```

### 11.3 opportunity_top_n_label_20d

定義:

```text
is_top5_expected_edge_20d
is_top10_expected_edge_20d
is_top20_expected_edge_20d
```

用途:

```text
OpportunityTop5 / Top10 / Top20 の再現性評価
precision@N
```

## 12. Label Schema

Phase5-B label table の候補 schema:

```text
target_date
code
label_version
candidate_inference_run_id
future_return_20d
future_max_return_20d
future_max_drawdown_20d
downside_bad_20d
top_decile_20d
risk_adjusted_future_return_20d
expected_edge_label_20d
opportunity_positive_20d
high_expected_edge_20d
opportunity_rank_label_20d
opportunity_quantile_label_20d
is_top5_expected_edge_20d
is_top10_expected_edge_20d
is_top20_expected_edge_20d
label_source_start_date
label_source_end_date
created_at
```

保存方針:

```text
feature table とは別 table / 別 path に保存する
inference path から読ませない
Phase4 label artifact を上書きしない
Phase5 用 label artifact として新規に管理する
```

## 13. Future Leakage 防止ルール

禁止:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
downside_bad_*
top_decile_*
expected_edge_label_*
risk_adjusted_future_return_*
opportunity_rank_label_*
```

を入力 feature、推論 input、selection logic に使うこと。

また以下も使わない。

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

label 生成ルール:

```text
label は target_date より後のデータだけで生成する
feature は as_of_date <= target_date のデータだけで生成する
feature table と label table を物理的・論理的に分離する
training dataset 作成時は feature columns と label columns を明示的に分ける
inference 実行時は label table を読まない
Candidate Top50 は Phase4 の feature-only inference artifact から読む
```

欠損時:

```text
t+20 までの future data が不足する target_date は training / evaluation label 対象外にする
future window 内に必要な High / Low / Close が不足する row は label_missing として除外または監査対象にする
未来データを補完して label を作らない
```

## 14. Label Audit 項目

必須 audit:

```text
label_row_count
candidate_top50_row_count
label_coverage_rate
missing_future_return_20d_count
missing_future_max_return_20d_count
missing_future_max_drawdown_20d_count
downside_bad_rate_20d
top_decile_rate_20d
positive_rate_20d
neutral_rate_20d
negative_rate_20d
expected_edge_label_min
expected_edge_label_max
expected_edge_label_mean
expected_edge_label_std
expected_edge_label_quantiles
same_target_date_rank_completeness
duplicate_target_date_code_count
forbidden_feature_column_overlap_count
label_feature_separation_status
leakage_audit_status
```

品質確認:

```text
target_date ごとの Candidate Top50 に rank label が付いている
top_decile_20d が target_date 内でおおむね上位10%になっている
positive / neutral / negative が極端に偏りすぎていない
expected_edge_label_20d が future_return_20d だけに支配されていない
future_max_return_20d の情報が label に残っている
downside_bad_20d が expected_edge_label_20d を減点している
```

監査ステータス:

```text
OK
WARNING_LABEL_DISTRIBUTION_SKEWED
WARNING_LOW_LABEL_COVERAGE
FAIL_LEAKAGE_RISK
FAIL_MISSING_REQUIRED_LABEL
FAIL_DUPLICATE_KEY
```

## 15. Phase5-C Feature Design へ渡す前提

Phase5-C へ渡す前提:

```text
Opportunity AI の主 label は expected_edge_label_20d
expected_edge_label_20d は risk_adjusted_future_return_20d と同義の初期正式定義
future_return_20d は中心加点要素
future_max_return_20d は上昇余地の加点要素
future_max_drawdown_20d は drawdown penalty
downside_bad_20d は downside penalty と補助 classification label
top_decile_20d は Candidate Top50 内の相対上位 label
```

Phase5-C で設計すべき feature は、上記 label を推定するための `as_of_date` 時点で観測可能な情報に限定する。

Phase5-C で feature 候補にしてよいもの:

```text
candidate_score
candidate_rank
candidate_reason
価格
出来高
高値
安値
価格モメンタム
出来高モメンタム
トレンド強度
ボラティリティ
売上成長
利益成長
ROE
財務健全性
TOPIX
市場トレンド
セクター強弱
```

Phase5-C でも feature にしてはいけないもの:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
expected_edge_label_*
risk_adjusted_future_return_*
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

## 16. Phase5-B 結論

Phase5-B では、Opportunity AI が学習する主 label として `expected_edge_label_20d` を定義した。

`expected_edge_label_20d` は `risk_adjusted_future_return_20d` と同義の初期正式定義であり、`future_return_20d` を中心に、`future_max_return_20d` による上昇余地、`future_max_drawdown_20d` と `downside_bad_20d` によるリスク減点、`top_decile_20d` による相対上位判定を統合する。

future 系データは学習・評価 label としてのみ使い、入力 feature や推論時参照には使わない。trade result、portfolio、annual_return、final_assets 由来のデータも使わない。

この資料により、Phase5-C Opportunity Feature Design / Expansion に進める状態になった。
