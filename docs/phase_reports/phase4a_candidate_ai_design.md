# AI Fund Lab vNext Phase4-A Candidate AI Design Report

---

# 1. このレポートの目的

本レポートは、正式ロードマップ上の `Phase4 Candidate AI vNext` の開始タスクとして、`Phase4-A Candidate AI Design` の完了条件を確認する。

Phase4-Aの目的は、Candidate AIを実装する前に以下を固定することである。

```text
入力
出力
成功条件
失敗条件
学習データ
推論フロー
監査方針
利用可能特徴量
利用禁止データ
責務境界
```

Phase4-Aでは設計のみを行う。

---

# 2. 読んだ資料

```text
docs/00_vision/investment_philosophy.md
docs/01_requirements/system_requirements.md
docs/01_requirements/success_metrics.md
docs/01_requirements/phase_roadmap.md
docs/02_architecture/system_architecture.md
docs/03_ai_design/candidate_ai_design.md
docs/03_ai_design/candidate_feature_catalog.md
```

`docs/03_ai_design/candidate_feature_catalog.md` は存在する。

---

# 3. Phase4の位置付け

現在地:

```text
Phase4 Candidate AI vNext
```

目的:

```text
上昇候補抽出
```

Candidate AIが答える問い:

```text
どの銘柄にモメンタムが発生しているか？
```

---

# 4. Candidate AIの責務境界

Candidate AIの責務は以下だけである。

```text
全銘柄から「見る価値がある上昇候補」を抽出する
```

目安:

```text
4000銘柄
↓
50銘柄程度
```

Candidate AIは以下をしない。

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

後続Phaseの責務:

```text
Phase5 Opportunity AI:
  期待値評価、買うべきかの判断

Phase6 Position Management AI:
  保有、売却、追加、縮小判断

Phase7 Capital Allocation:
  資金配分、購入金額、株数

Phase8 Order Manager:
  発注、訂正、取消、約定確認

Phase9 Paper Trading:
  仮想運用統合
```

---

# 5. 入力

Phase4-Aでは、Phase1 Data Foundationを前提にする。

利用可能データ:

```text
daily_quotes_normalized
listed issue master
trading calendar
fins summary
market index data
sector aggregation data
```

重要:

```text
daily_quotes_normalized
```

をCandidate AIの価格・出来高feature入力の前提にする。

raw v1は原本証跡であり、通常のCandidate feature入力にはnormalized dataを使う。

---

# 6. 利用可能特徴量カテゴリ

`candidate_feature_catalog.md` の以下カテゴリをPhase4-Aの設計入力とする。

```text
Quality
Price Momentum
Volume Momentum
Liquidity / Tradability
Market Environment
Sector Relative Strength
Exclusion / Risk Filter
```

Phase4-Aではfeature計算実装を行わない。

---

# 7. 出力

Candidate AIの出力は候補抽出結果に限定する。

出力案:

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

`candidate_score` は上昇候補度であり、利益予測、期待値順位、買い判断ではない。

---

# 8. 成功条件

システム全体の最重要目標:

```text
Annual Return >= 50%
```

ただし、Candidate AI単体はAnnual Returnで直接評価しない。

Candidate AI単体の成功条件:

```text
候補品質向上
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

future系指標は評価ラベルとしてのみ使い、推論featureには使わない。

---

# 9. 失敗条件

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

---

# 10. 学習データ方針

Phase4-Aでは学習データを生成しない。

Phase4-B以降で設計する学習データは以下を分離する。

```text
feature table:
  target_date時点で利用可能なfeatureのみ

label table:
  future_return_* など将来結果に基づく評価ラベル

audit table:
  入力snapshot、feature生成時刻、leakage check結果、除外理由
```

必須キー案:

```text
target_date
code
as_of_date
feature_version
source_snapshot_id
```

---

# 11. 推論フロー方針

Phase4-Aでは推論処理を実装しない。

Phase4-B以降の推論フロー案:

```text
1. target_dateを決める
2. daily_quotes_normalized と必要なmaster/calendar/finsを読む
3. target_date時点で利用可能なfeatureだけを組み立てる
4. Exclusion / Risk Filterで明確な対象外を除外する
5. Candidate AIがcandidate_scoreとcandidate_reasonを付与する
6. 候補数を50銘柄程度に制御する
7. candidate_listをOpportunity AIへ渡す
```

Candidate AIは、買うかどうか、期待値順位、購入金額、発注を決めない。

---

# 12. 監査方針

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
Phase4-Aでは学習・推論・backtest・paper trading・発注が実装されていない
```

---

# 13. 利用禁止データ

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

Future系は学習・評価ラベルとしてのみ扱い、feature tableとは物理的・論理的に分離する。

---

# 14. Phase4-Aで実装しないこと

Phase4-Aでは以下を実装しない。

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

---

# 15. Phase4-A完了判定

Phase4-Aは完了可能である。

理由:

```text
Candidate AIの責務が候補抽出に限定されている
入力、出力、成功条件、失敗条件が明記されている
daily_quotes_normalized 利用前提が明記されている
利用可能featureカテゴリが整理されている
利用禁止データが明記されている
学習・推論・backtest・paper trading・発注を実装していない
Phase4-BでTraining Data Designに進める
```

---

# 16. Phase4-B案

次に進むべきPhase4-B:

```text
Candidate Training Data Design
```

Phase4-Bで決めること:

```text
feature table schema
label table schema
audit table schema
as_of_date / target_date の厳密ルール
daily_quotes_normalized からのfeature生成仕様
candidate_reason / excluded_reason enum
leakage auditの機械チェック
候補数50銘柄程度への制御方法
学習前データ品質チェック
```
