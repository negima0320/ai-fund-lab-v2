# Phase5-A Opportunity AI Design Document

作成日: 2026-06-14

## 1. 目的

この資料は、Phase5 Opportunity AI vNext の実装前設計を定義する。

Phase4 Candidate AI は、全銘柄からモメンタム候補 Top50 を抽出する候補抽出器として成立した。一方で、Candidate score は買い順位としては不十分であり、Top50 には大きく上昇する候補と大きく下落する候補が混在する。

Phase5-A の目的は、実装・学習・推論に進む前に、Opportunity AI の責務、入力、出力、label、feature、評価指標、leakage guardrail を固定することである。

## 2. Phase5 の責務

Opportunity AI がやること:

```text
Candidate Top50 から Opportunity TopN を選ぶ
downside / drawdown risk が高い候補を落とす
一時的な吹き上げ候補と持続上昇候補を分ける
candidate_score を上流 prior として扱う
market regime に応じて絞り込み強度を変える
買い検討に進める候補の順位と理由を出す
```

Opportunity AI がやらないこと:

```text
全銘柄から候補を探す
購入株数を決める
購入金額を決める
保有継続を判断する
売却を判断する
発注する
Broker API を呼ぶ
Portfolio を更新する
Paper Trading を行う
Annual Return を評価する
```

責務境界:

```text
Candidate AI:
  全銘柄 -> Top50
  上昇候補を広く拾う

Opportunity AI:
  Top50 -> Top5 / Top10 / Top20
  買い検討に進める候補を選別する

Position Management AI:
  購入後の HOLD / EXIT / ADD / REDUCE

Capital Allocation Engine:
  購入金額と株数を決める

Order Manager:
  注文を実行・管理する
```

## 3. Phase4 からの前提

Phase4 最終判定:

```text
Phase4 final status: SUCCESS
readiness_status: PHASE4_COMPLETE_WITH_IMPROVEMENT_OPPORTUNITIES
Candidate AI role: candidate extraction only
```

Phase4 の強み:

```text
CandidateTop50 は FutureReturnTop50 を random より約 4.9 倍捕捉した
CandidateTop50 は FutureMaxTop50 を random より 7.5 倍捕捉した
FutureMaxTop10 / FutureReturnTop10 捕捉でも random を上回った
latest target_date 2026-06-12 で 4,164 eligible 銘柄から Top50 を生成できた
```

Phase4 の弱み:

```text
Candidate score 単体では Best / Worst を分離できない
score と future_return_20d の相関は弱い、または逆方向
score と downside_bad の相関が正
Top50 には高 drawdown 候補が混ざる
down regime では win rate / return / downside_bad_rate が悪化する
短期 volume surge は Winner より Worst 側で高い傾向がある
```

Phase5 の基本方針:

```text
Candidate AI の「吹く銘柄を拾う力」は残す
買い順位は Candidate score から直接作らない
downside / drawdown / 持続性 / entry confirmation を重視する
短期出来高急増を単純加点しない
down regime では候補数と閾値を厳しくする
```

## 4. Input

### 4.1 Candidate AI output

必須入力:

```text
target_date
code
candidate_rank
candidate_score
candidate_reason
excluded_reason
feature_version
model_version
inference_run_id
```

Candidate score の扱い:

```text
candidate_score は upstream prior として使う
candidate_score を buy_rank に直結しない
candidate_rank だけで Opportunity TopN を決めない
score が高いほど安全とは仮定しない
```

### 4.2 Phase4 feature

Phase4 feature table から再利用する候補:

```text
price_momentum_return_5d
price_momentum_return_20d
price_momentum_return_60d
trend_close_over_ma_20d
trend_ma_5_20_ratio
trend_ma_20_60_ratio
volume_momentum_ratio_5d
volume_momentum_ratio_1d_20d
liquidity_avg_volume_20d
volatility_return_std_20d
universe_eligible
```

Phase5 では、これらをそのまま買い材料として扱わず、以下の観点で再解釈する。

```text
momentum:
  持続上昇の確認

trend:
  上昇基調の確認

liquidity:
  実運用可能性と大幅下落耐性の補助

volume surge:
  関心増加ではなく過熱・材料一巡リスクとしても見る

volatility:
  upside 機会と drawdown risk の両面を見る
```

### 4.3 Opportunity feature

Phase5-C 以降で追加検討する feature:

```text
momentum_consistency_score
  5d / 20d / 60d momentum の方向と過熱度

trend_confirmation_score
  close over MA, MA ratio, high proximity の統合

liquidity_stability_score
  avg volume / turnover と欠損・急減の確認

volume_surge_risk_score
  1d / 5d volume ratio が極端に高い候補のリスク

drawdown_proxy_score
  過去20d/60d volatility、急落回数、下ヒゲ的変動の proxy

entry_overheat_score
  短期 return が中期 trend に対して過剰な候補のリスク

regime_observable_feature
  target_date 時点で観測可能な TOPIX / market trend feature
```

### 4.4 Market regime input

Phase4-BM の regime proxy は評価用であり、そのまま推論 feature にしない。

Phase5 で推論に使う場合は、以下を守る。

```text
target_date 時点で観測可能な market index data だけで作る
future_return や post-selection return を使わない
up / flat / down の定義を固定する
regime_unknown を許容する
regime は売買停止ではなく絞り込み強度の調整に使う
```

## 5. Output

Opportunity AI は candidate ごとに以下を出力する。

```text
target_date
code
candidate_rank
candidate_score
opportunity_score
opportunity_rank
opportunity_bucket
downside_risk_score
confirmation_score
regime_adjustment
reject_reason
opportunity_reason
model_version
feature_version
inference_run_id
created_at
```

`opportunity_bucket` の候補:

```text
TOP5
TOP10
TOP20
REJECT_RISK
REJECT_NO_CONFIRMATION
REJECT_REGIME
REJECT_DATA_QUALITY
```

`reject_reason` の候補:

```text
high_drawdown_risk
weak_trend_confirmation
excessive_short_volume_surge
overheated_short_term_move
low_liquidity
down_regime_threshold_not_met
insufficient_feature_history
data_quality_issue
```

## 6. Label Design

Phase5 label は Candidate Top50 内の選別品質を学ぶために使う。推論時 feature には使わない。

### 6.1 Primary label

Primary label 候補:

```text
opportunity_label_20d
```

初期定義案:

```text
positive if:
  future_return_20d > 0
  and future_max_return_20d is above candidate-top50 threshold
  and future_max_drawdown_20d is not worse than downside threshold

negative if:
  downside_bad_20d == true
  or future_max_drawdown_20d <= drawdown threshold
  or future_return_20d <= loss threshold
```

この label は、単なる future_max_return 上位ではなく、20営業日後リターンと途中 drawdown を同時に見る。

### 6.2 Auxiliary labels

補助 label:

```text
sustained_upside_20d
  一時的な高値ではなく、20d return も positive な候補

downside_bad_20d
  一定以上の下落・drawdown を起こした候補

future_max_drawdown_20d
  20営業日内の最大下落幅

future_return_20d_positive
  20営業日後がプラスか

future_max_return_20d_high
  20営業日内に十分な上昇余地があったか

whipsaw_after_spike_20d
  一度吹いた後に失速・大幅下落した候補

failed_breakout_20d
  entry 時点の強さが持続しなかった候補
```

### 6.3 Label guardrail

```text
future_return_*
future_max_return_*
future_max_drawdown_*
downside_bad_*
top_decile_*
label_*
```

これらは label table または evaluation table にのみ保存する。Feature table、inference input、selection logic へ混入させない。

## 7. Dataset Design

Phase5-D で作る dataset の単位:

```text
1 row = target_date + code in Candidate Top50
```

母集団:

```text
Phase4 Candidate AI が feature-only inference で選んだ Top50
```

禁止:

```text
future label を使って Candidate Top50 を作り直す
Candidate Top50 外の銘柄を Opportunity training row に混ぜる
推論時に label table を読む
mock path を formal path に上書きする
Phase4 artifact を破壊する
```

必須メタデータ:

```text
target_date
as_of_date
code
candidate_inference_run_id
candidate_model_version
candidate_feature_version
opportunity_feature_version
label_version
dataset_version
split_name
created_at
```

Train / validation / test split:

```text
time-based split を維持する
Candidate AI と同じ期間境界を初期候補にする
random split は使わない
same target_date の row を複数 split に分けない
```

## 8. Evaluation Metrics

Opportunity AI 単体の成功条件:

```text
Opportunity 上位候補の期待値が Candidate Top50 平均を上回る
downside_bad_rate が Candidate Top50 より下がる
drawdown risk が Candidate Top50 より下がる
future_max_return 捕捉力を大きく毀損しない
```

主要評価:

```text
top5_avg_return_20d
top10_avg_return_20d
top20_avg_return_20d
top5_win_rate_20d
top10_win_rate_20d
top20_win_rate_20d
top5_future_max_return_20d
top10_future_max_return_20d
top20_future_max_return_20d
top5_downside_bad_rate_20d
top10_downside_bad_rate_20d
top20_downside_bad_rate_20d
top5_max_drawdown_20d
top10_max_drawdown_20d
top20_max_drawdown_20d
```

Lift 評価:

```text
topN_return_lift_vs_candidate_top50
topN_win_rate_lift_vs_candidate_top50
topN_downside_bad_reduction_vs_candidate_top50
topN_drawdown_reduction_vs_candidate_top50
topN_future_max_capture_retention
```

Ranking 評価:

```text
opportunity_score_future_return_correlation
opportunity_score_future_max_return_correlation
opportunity_score_downside_bad_correlation
precision_at_5
precision_at_10
precision_at_20
```

失敗条件:

```text
TopN が Candidate Top50 平均と差がない
TopN downside_bad_rate が Candidate Top50 と同等または悪化
future_max_return 捕捉をほぼ失う
down regime で候補品質が制御不能
candidate_score の並べ替えだけになっている
```

## 9. Regime Policy

初期方針:

```text
up regime:
  Top20 まで広めに残す
  momentum / trend confirmation を重視

flat regime:
  Top10 を標準候補にする
  downside risk と confirmation のバランスを見る

down regime:
  Top5 程度まで強く絞る
  drawdown filter と liquidity filter を強める
  weak confirmation は reject する

unknown regime:
  flat regime より保守的に扱う
```

Regime は最終売買停止判断ではない。Phase5 では Opportunity ranking の閾値調整に限定する。

## 10. Model Design

Phase5-E の初期候補:

```text
baseline rule scorer
  downside / confirmation / candidate prior を明示式で統合

LightGBM ranker or classifier
  Candidate Top50 内の opportunity_label_20d を学習

two-stage model
  1. downside risk model
  2. confirmation / opportunity ranking model
```

推奨初手:

```text
Phase5-B/C/D で label と feature を固める
Phase5-E では rule baseline と LightGBM classifier を比較する
downside_risk_score と confirmation_score は別々に監査可能にする
```

Candidate score の統合:

```text
candidate_prior_score = clipped / normalized candidate_score
opportunity_score = f(candidate_prior_score, confirmation_score, downside_risk_score, regime_adjustment)
```

ただし `candidate_prior_score` が `opportunity_score` を支配しないよう、feature importance と ablation で確認する。

## 11. Leakage Audit

Phase5 で必須の監査:

```text
feature column に future_* / label_* / downside_bad_* がない
inference path が label table を読まない
Candidate Top50 は feature-only inference artifact から読む
regime feature は target_date 時点で観測可能な market data だけで作る
as_of_date <= target_date を満たす
財務・銘柄マスタは公表日または有効日 <= as_of_date のみ使う
target_date より後の価格・出来高を feature に使わない
train / validation / test が時系列分離されている
same target_date が複数 split に混ざらない
```

監査出力:

```text
leakage_audit_status
forbidden_feature_columns
label_feature_overlap_count
future_column_in_feature_count
split_leakage_status
as_of_date_violation_count
regime_observability_status
```

## 12. Artifact Policy

Phase5 は Phase4 artifact を破壊しない。

読み取り候補:

```text
reports/candidate_ai/full_range/
reports/candidate_ai/final_check/
formal Candidate inference output
formal Candidate feature table
formal Candidate label table
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
mock path overwrite
reader switch
promotion
live path update
Broker path update
Portfolio path update
```

## 13. Phase5 Roadmap

Phase5 の推奨順序:

```text
Phase5-A: Opportunity AI Design Document
Phase5-B: Downside / Drawdown Label Design
Phase5-C: Opportunity Feature Design / Expansion
Phase5-D: Candidate Top50 -> Opportunity Dataset Builder
Phase5-E: Opportunity Model Training
Phase5-F: Opportunity Inference
Phase5-G: Opportunity Quality Audit
Phase5-H: Candidate + Opportunity Combined Validation
```

各 subphase の完了条件:

```text
Phase5-B:
  label schema / thresholds / label audit を固定

Phase5-C:
  feature schema / forbidden columns / as_of_date rule を固定

Phase5-D:
  Candidate Top50 only dataset を再現可能に生成

Phase5-E:
  baseline と model training を比較し、downside reduction を確認

Phase5-F:
  latest target_date で Opportunity TopN を生成

Phase5-G:
  Top5 / Top10 / Top20 の quality audit を実施

Phase5-H:
  Candidate + Opportunity の combined lift と risk reduction を確認
```

## 14. Phase5-A Conclusion

Phase5 Opportunity AI は、Candidate AI の後段に置く「地雷除去 + 本命候補選別AI」として設計する。

Phase4 の Candidate AI は、20営業日以内に一度大きく吹く銘柄を random より高く捕捉できた。ただし、その候補には高 drawdown / downside_bad 候補も混在する。Phase5 では、Candidate score を買い順位として使わず、momentum consistency、trend confirmation、liquidity、volume surge risk、drawdown proxy、market regime を使って Candidate Top50 を Top5 / Top10 / Top20 に絞る。

Phase5-A では設計のみを行った。実装、学習、推論、backtest、Paper Trading、Broker API、発注、promotion、reader switch は行っていない。
