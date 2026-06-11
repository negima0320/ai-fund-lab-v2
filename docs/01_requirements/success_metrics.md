# AI Fund Lab vNext 成功指標定義

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
AI Fund Lab vNext
```

における成功指標を定義する。

---

目的は、

```text
何を改善するべきか

何を成功とするのか

何を失敗とするのか
```

を明確にすることである。

---

# 2. 最重要指標

## Primary Metric

最重要指標

```text
Annual Return
```

---

目標

```text
年率50%以上
```

---

AI Fund Labの最終目標は、

```text
Annual Return
```

である。

---

# 3. Secondary Metrics

以下は診断指標。

---

```text
Profit Factor

Drawdown

Win Rate

Capital Utilization

Trade Count

Holding Period
```

---

重要。

これらは

```text
目的
```

ではない。

---

役割は、

```text
なぜAnnual Returnが伸びないのか
```

を調査することである。

---

# 4. 成功指標の階層

成功指標は階層構造を持つ。

---

## Level 1

システム全体

```text
Annual Return
```

---

## Level 2

投資戦略

```text
Average Trade Return

Profit Retention

Opportunity Capture
```

---

## Level 3

各AI

```text
Candidate Quality

Opportunity Ranking

Position Management
```

---

# 5. システム全体の成功条件

## Success

```text
Annual Return >= 50%
```

---

## Warning

```text
Annual Return > 0

だが

50%未達
```

---

## Failure

```text
Annual Return <= 0
```

---

# 6. Candidate AI 成功条件

Candidate AIの責務

```text
上昇候補抽出
```

---

## 成功

```text
候補群の平均期待値が市場平均を上回る
```

---

評価例

```text
candidate_mean_future_return

candidate_mean_future_max_return

candidate_top_decile_rate

candidate_downside_bad_rate
```

---

## 失敗

```text
市場平均と差がない

候補数が多すぎる

候補数が少なすぎる
```

---

# 7. Opportunity AI 成功条件

Opportunity AIの責務

```text
候補順位付け
```

---

## 成功

```text
Opportunity上位候補の期待値が

Candidate平均を上回る
```

---

評価例

```text
selected_mean_future_return

selected_mean_future_max_return

lift

precision
```

---

## 失敗

```text
Candidate AIと差がない
```

---

# 8. Position Management AI 成功条件

責務

```text
利益保持

損失抑制
```

---

## 成功

```text
profit_retention_rate向上

winner_to_loser_rate低下

profit_decay削減
```

---

## 評価例

```text
profit_retention_rate

winner_to_loser_rate

avg_profit_decay_before_exit
```

---

## 失敗

```text
利益を保持できない

損失拡大
```

---

# 9. Capital Allocation Engine 成功条件

責務

```text
利益を壊さない
```

---

## 成功

```text
資金不足なし

過剰集中なし

安定運用
```

---

## 評価例

```text
capital_utilization

position_concentration
```

---

## 注意

Capital Allocation Engineは

```text
利益を作る
```

担当ではない。

---

# 10. Broker Integration 成功条件

## 成功

```text
口座状態一致

約定一致

注文整合性維持
```

---

## 失敗

```text
不整合

二重注文

同期失敗
```

---

# 11. Safety Guard 成功条件

## 成功

```text
異常時停止

異常検知
```

---

## 失敗

```text
異常を見逃す

停止できない
```

---

# 12. AI追加成功条件

新AI追加前に確認。

---

必須

```text
役割

入力

出力

成功条件

失敗条件
```

---

追加後

```text
Annual Return改善に
どう繋がるか
```

説明できること。

---

# 13. やってはいけない評価

禁止。

---

```text
PF改善

↓

成功
```

---

```text
DD改善

↓

成功
```

---

```text
AUC改善

↓

成功
```

---

```text
Top Decile改善

↓

成功
```

---

単体では成功ではない。

---

# 14. 正しい評価順序

常に以下。

---

```text
Annual Return
```

確認。

---

次に

```text
なぜそうなったか
```

を確認。

---

そのために

```text
PF

DD

Win Rate

Capital Utilization

Trade Count
```

を見る。

---

# 15. 実験成功条件

新しい実験を行う場合。

---

必須

```text
この実験は

Annual Return改善に

どう繋がるのか？
```

説明する。

---

説明できない場合、

実施しない。

---

# 16. 最終原則

AI Fund Labは、

```text
AIの精度向上
```

を目的としない。

---

目的は、

```text
Annual Return向上
```

である。

---

すべての改善は、

```text
年率50%達成に
どう繋がるか
```

を説明できなければならない。
