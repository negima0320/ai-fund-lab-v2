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
