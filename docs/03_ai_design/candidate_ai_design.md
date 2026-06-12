# AI Fund Lab vNext Candidate AI 設計書

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
Candidate AI
```

の役割、責務、入力、出力、成功条件を定義する。

---

# 2. Candidate AIの役割

## 一言で言うと

```text
上昇候補を発見するAI
```

---

Candidate AIは、

```text
何を買うか
```

を決定しない。

---

Candidate AIは、

```text
見る価値がある銘柄を探す
```

ことだけを担当する。

---

# 3. Candidate AIが解く問題

Candidate AIの問いは以下。

```text
どの銘柄に
上昇モメンタムが発生しているか？
```

---

重要:

```text
どの銘柄が最も儲かるか？
```

は解かない。

---

それは

```text
Opportunity AI
```

の責務とする。

---

# 4. Candidate AIの位置付け

```text
全銘柄

↓

Candidate AI

↓

候補銘柄

↓

Opportunity AI

↓

購入候補

↓

Capital Allocation Engine
```

---

Candidate AIは

```text
4000銘柄
↓
50銘柄
```

程度まで絞ることを目的とする。

---

# 5. Candidate AIの思想

投資哲学:

```text
良い企業

かつ

市場が評価し始めた
```

銘柄を発見する。

---

Candidate AIは

```text
上昇開始の検知
```

を目的とする。

---

期待値判定は行わない。

---

# 6. 入力

## 市場データ

```text
株価

高値

安値

終値

出来高
```

---

## テクニカル

```text
移動平均

高値更新

ボラティリティ

価格モメンタム

出来高モメンタム
```

---

## ファンダメンタル

```text
売上

利益

成長率

ROE

財務健全性
```

---

## 市場環境

```text
TOPIX

業種指数

市場トレンド
```

---

# 7. 利用禁止データ

以下は禁止。

```text
future_return_*

future_max_return_*

future_max_drawdown_*

top_decile_*

downside_bad_*
```

---

また以下も禁止。

```text
backtest result

trade result

selected

bought

sold

cash

portfolio

annual_return

final_assets
```

ここでの禁止は、

```text
入力featureとして使うこと

推論時に参照すること
```

を指す。

学習・評価ラベルとしての利用は、

```text
system_requirements.md の学習データ要件
```

に従う。

---

# 8. 出力

Candidate AIは以下を出力する。

---

## candidate_score

```text
上昇候補度
```

---

## candidate_rank

```text
候補順位
```

---

## candidate_reason

例:

```text
出来高急増

20日高値更新

移動平均上抜け

業績改善
```

---

## excluded_reason

候補外理由。

例:

```text
流動性不足

下落トレンド

出来高不足
```

---

# 9. Candidate AIが判断しないこと

以下は判断しない。

---

## 買うかどうか

担当:

```text
Opportunity AI
```

---

## 保有するかどうか

担当:

```text
Position Management AI
```

---

## 売るかどうか

担当:

```text
Position Management AI
```

---

## 何株買うか

担当:

```text
Capital Allocation Engine
```

---

# 10. 成功条件

Candidate AIの成功条件は、

```text
候補品質
```

である。

---

## 目標

全銘柄より高い期待値を持つ候補群を作る。

---

理想

```text
4000銘柄

↓

50銘柄

↓

平均期待値向上
```

---

## 評価指標

```text
candidate_mean_future_return

candidate_mean_future_max_return

candidate_downside_bad_rate

candidate_top_decile_rate
```

---

注意:

```text
Annual Return
```

では評価しない。

---

Candidate AI単体では、

```text
候補品質
```

のみ評価する。

---

# 11. 失敗条件

以下は失敗。

---

## 候補品質が市場平均と変わらない

```text
candidate_mean_future_return
≈ market_mean_future_return
```

---

## 候補数が多すぎる

例:

```text
4000銘柄

↓

3000銘柄
```

---

## 候補数が少なすぎる

例:

```text
4000銘柄

↓

1銘柄
```

---

## Opportunity AIと責務が重複する

Candidate AIが、

```text
期待値

買い順位

利益予測
```

を始めたら失敗。

---

# 12. Candidate AI vNext仮説

現時点の仮説。

---

Candidate AIは、

```text
企業品質

+

価格モメンタム

+

出来高モメンタム
```

を組み合わせる。

---

Candidate AIは、

```text
上昇が始まりそうな銘柄
```

を見つける。

---

Opportunity AIが、

```text
その中で
本当に買うべき銘柄
```

を決定する。

---

# 13. 将来の拡張

候補:

```text
業種モメンタム

市場レジーム

決算モメンタム

ニュースモメンタム
```

---

ただし、

```text
Candidate AIの責務
=
候補抽出
```

は変更しない。

---

# 14. 最終原則

Candidate AIは、

```text
上がる株を予言するAI
```

ではない。

---

Candidate AIは、

```text
市場が評価し始めた銘柄を発見するAI
```

である。

---

# 15. Phase4-A Candidate AI Design

## 15.1 Phase4-Aの目的

Phase4-Aは、正式ロードマップ上の `Phase4 Candidate AI vNext` の開始点である。

今回の目的は、Candidate AIを実装する前に、責務、入力、出力、成功条件、失敗条件、学習データ、推論フロー、監査方針、利用可能特徴量、利用禁止データを固定することである。

Phase4-Aでは設計のみを行う。

Phase4-Aでやらないこと:

```text
Candidate AI本体
feature builder本体
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

## 15.2 責務境界

Candidate AIの責務は以下だけである。

```text
全銘柄から「見る価値がある上昇候補」を抽出する
```

問い:

```text
どの銘柄にモメンタムが発生しているか？
```

Candidate AIがしないこと:

```text
買うかどうかを決める
期待値順位を決める
購入金額を決める
保有判断をする
売却判断をする
Capital Allocationをする
Paper Tradingする
発注する
```

後続Phaseとの境界:

```text
Phase5 Opportunity AI:
  候補の中から期待値を評価し、買うべきかを判断する

Phase6 Position Management AI:
  保有継続、売却、追加、縮小を判断する

Phase7 Capital Allocation:
  購入金額や株数を決める

Phase8 Order Manager:
  発注、訂正、取消、約定確認を扱う

Phase9 Paper Trading:
  仮想運用として各コンポーネントを統合する
```

## 15.3 入力

Phase4-Aでは、Phase1で作成したData Foundationを前提にする。

主要入力:

```text
daily_quotes_normalized
listed issue master
trading calendar
fins summary
market index data
sector aggregation data
```

`daily_quotes_normalized` は日足OHLCVの正規化済み入力として利用する前提である。raw v1は原本証跡であり、Candidate AIの通常feature入力はnormalized dataを使う。

入力featureカテゴリ:

```text
Quality
Price Momentum
Volume Momentum
Liquidity / Tradability
Market Environment
Sector Relative Strength
Exclusion / Risk Filter
```

## 15.4 出力

Candidate AIの出力は候補抽出のための中間成果物に限定する。

出力:

```text
target_date
candidate_list
candidate_score
candidate_reason
excluded_reason
feature_snapshot_id
model_version
audit_flags
```

`candidate_score` は上昇候補度であり、期待利益、買い順位、購入判断ではない。

`candidate_reason` は、候補になった理由を説明するために使う。

例:

```text
20日高値更新
出来高急増
短期/中期移動平均上向き
セクター内相対強度
最低流動性条件を満たす
```

`excluded_reason` は、候補外にした理由を説明するために使う。

例:

```text
低流動性
履歴不足
監理・整理リスク
異常値
daily_quotes_normalized欠損
```

## 15.5 成功条件

システム全体の最重要目標は以下である。

```text
Annual Return >= 50%
```

ただし、Candidate AI単体はAnnual Returnで直接評価しない。

Candidate AI単体の成功条件:

```text
候補品質向上
```

目安:

```text
4000銘柄
↓
50銘柄程度
```

評価観点:

```text
candidate_mean_future_return
candidate_mean_future_max_return
candidate_downside_bad_rate
candidate_top_decile_rate
candidate_count
excluded_count
reason_coverage
```

future系指標は評価ラベルとしてのみ扱う。推論featureには使わない。

## 15.6 失敗条件

Candidate AIの失敗条件:

```text
候補群の品質が市場平均と変わらない
候補数が多すぎる
候補数が少なすぎる
candidate_reason が説明できない
excluded_reason が説明できない
future系ラベルがfeatureへ混入する
backtest/trade/portfolio由来データがfeatureへ混入する
Opportunity AIの期待値ランキング責務を侵食する
Capital AllocationやOrder Managerの責務を侵食する
```

## 15.7 学習データ設計方針

Phase4-Aでは学習データを生成しない。

Phase4-B以降で学習データを設計する場合は、以下を分離する。

```text
feature table:
  target_date時点で利用可能な入力featureだけを持つ

label table:
  future_return_* など将来結果に基づく評価ラベルを持つ

audit table:
  feature生成時刻、入力snapshot、除外理由、leakage check結果を持つ
```

学習データの必須キー:

```text
target_date
code
as_of_date
feature_version
source_snapshot_id
```

`as_of_date` は、target_date時点で利用可能だった情報だけを使ったことを確認するために必須とする。

## 15.8 推論フロー設計

Phase4-Aでは推論処理を実装しない。

Phase4-B以降の推論フロー案:

```text
1. target_dateを決める
2. daily_quotes_normalized と必要なmaster/calendar/finsを読む
3. target_date時点で利用可能なfeatureだけを組み立てる
4. Exclusion / Risk Filterで明確な対象外を除外する
5. Candidate AIがcandidate_scoreとcandidate_reasonを付与する
6. 候補数が多すぎる場合はCandidate内の候補抽出基準で50銘柄程度に抑える
7. candidate_listをOpportunity AIへ渡す
```

この流れでは、買うかどうか、期待値順位、購入金額、発注は決めない。

## 15.9 監査方針

Phase4-A以降のCandidate AI監査では以下を確認する。

```text
daily_quotes_normalized を入力前提としている
target_dateより未来の情報をfeatureに使っていない
future_return_* をfeatureに使っていない
backtest/trade/portfolio/order由来データをfeatureに使っていない
candidate_score が利益予測や買い順位として扱われていない
candidate_reason / excluded_reason が出力される
候補数が監査できる
除外理由のcoverageが監査できる
学習・推論・backtest・paper trading・発注がPhase4-Aでは実装されていない
```

## 15.10 利用禁止データ

以下はCandidate AIの入力feature、推論参照、候補抽出ロジックに使わない。

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
```

future系は学習・評価ラベルとしてのみ扱い、feature tableとは物理的・論理的に分離する。

## 15.11 Phase4-Bへの引き継ぎ

Phase4-Bで決めること:

```text
Candidate Training Data Design
feature table schema
label table schema
as_of_date / target_date の厳密な扱い
daily_quotes_normalized からのfeature生成仕様
candidate_count制御方法
candidate_reason / excluded_reason のenum
leakage auditの機械チェック
学習前のデータ品質チェック
```
