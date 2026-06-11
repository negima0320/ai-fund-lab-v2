# AI Fund Lab vNext Opportunity AI 設計書

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
Opportunity AI
```

の役割、責務、入力、出力、成功条件を定義する。

---

# 2. Opportunity AIの役割

## 一言で言うと

```text
候補銘柄の期待値を判定するAI
```

---

Opportunity AIは、

```text
候補の中で

どれを買うべきか
```

を決定する。

---

# 3. Opportunity AIが解く問題

Opportunity AIの問いは以下。

```text
Candidate AIが抽出した候補の中で

どの銘柄が最も期待値が高いか？
```

---

重要:

```text
候補を探す
```

ではない。

---

それは

```text
Candidate AI
```

の責務。

---

Opportunity AIは、

```text
候補を順位付けする
```

ことが仕事。

---

# 4. Opportunity AIの位置付け

```text
全銘柄

↓

Candidate AI

↓

候補50銘柄

↓

Opportunity AI

↓

買い候補5銘柄

↓

Capital Allocation Engine
```

---

Opportunity AIは

```text
50銘柄
↓
5銘柄
```

程度まで絞ることを目的とする。

---

# 5. Opportunity AIの思想

Candidate AIは、

```text
上昇しそう
```

を探す。

---

Opportunity AIは、

```text
その上昇で

十分な利益が取れるか
```

を判定する。

---

投資哲学としては、

```text
良い企業

かつ

上昇が始まり

かつ

まだ上昇余地が残っている
```

銘柄を優先する。

---

# 6. Opportunity AIが予測するもの

重要。

Opportunity AIは、

```text
株価そのもの
```

を予測しない。

---

Opportunity AIが予測したいのは、

```text
期待値
```

である。

---

例

```text
A銘柄

上がる確率
高い

でも
+2%

---

B銘柄

上がる確率
普通

でも
+15%
```

---

Opportunity AIは、

```text
期待値
```

で比較する。

---

# 7. Input

## Candidate AI出力

```text
candidate_list

candidate_score

candidate_reason
```

---

## 市場データ

```text
価格

出来高

高値

安値
```

---

## テクニカル

```text
価格モメンタム

出来高モメンタム

トレンド強度

ボラティリティ
```

---

## ファンダメンタル

```text
売上成長

利益成長

ROE

財務健全性
```

---

## 市場環境

```text
TOPIX

市場トレンド

セクター強弱
```

---

# 8. 利用禁止データ

禁止。

```text
future_return_*

future_max_return_*

future_max_drawdown_*

top_decile_*

downside_bad_*
```

---

また禁止。

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

# 9. Output

Opportunity AIは以下を出力する。

---

## expected_edge_score

```text
期待値スコア
```

---

## buy_rank

```text
購入順位
```

---

## expected_return_horizon

```text
期待上昇余地
```

---

## downside_risk_score

```text
下落リスク
```

---

## buy_reason

例

```text
企業品質良好

価格モメンタム強い

出来高増加

市場環境良好
```

---

## no_buy_reason

例

```text
期待値不足

リスク過大

市場環境悪化
```

---

# 10. Opportunity AIが判断しないこと

以下は判断しない。

---

## 候補抽出

担当

```text
Candidate AI
```

---

## 保有継続

担当

```text
Position Management AI
```

---

## 売却判断

担当

```text
Position Management AI
```

---

## 購入株数

担当

```text
Capital Allocation Engine
```

---

# 11. 成功条件

Opportunity AIの成功条件は、

```text
平均trade edge向上
```

である。

---

目標

```text
Candidate群の中から

最も期待値が高い銘柄を選ぶ
```

---

評価指標

```text
selected_mean_future_return

selected_mean_future_max_return

selected_top_decile_rate

selected_downside_bad_rate
```

---

重要:

```text
Opportunity AI単体では

Annual Returnを評価しない
```

---

Annual Returnは

```text
システム全体
```

の責務。

---

# 12. 失敗条件

以下は失敗。

---

## Candidate AIと責務が重複

Opportunity AIが、

```text
候補抽出
```

を始めたら失敗。

---

## Position Management AIと重複

Opportunity AIが、

```text
売却判断
```

を始めたら失敗。

---

## Capital Allocation Engineと重複

Opportunity AIが、

```text
購入金額
```

を決め始めたら失敗。

---

# 13. Opportunity AI vNext仮説

現時点の仮説。

---

Opportunity AIは、

```text
企業品質

+

価格モメンタム

+

出来高モメンタム

+

市場環境

+

リスク
```

を統合して評価する。

---

目的は、

```text
上がる銘柄
```

を探すことではない。

---

目的は、

```text
期待値が高い銘柄
```

を順位付けすること。

---

# 14. 将来の拡張

候補。

```text
決算モメンタム

業種モメンタム

市場レジーム

ニュース評価
```

---

ただし、

```text
Opportunity AIの責務

=
期待値判定
```

は変更しない。

---

# 15. 最終原則

Opportunity AIは、

```text
未来を予言するAI
```

ではない。

---

Opportunity AIは、

```text
Candidate群の中から

最も期待値が高い銘柄を選ぶAI
```

である。

---

Candidate AI

↓

Opportunity AI

↓

Capital Allocation Engine

という責務分離を絶対に維持する。
