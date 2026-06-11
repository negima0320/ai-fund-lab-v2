# AI Fund Lab vNext Capital Allocation Engine 設計書

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
Capital Allocation Engine
```

の役割、責務、入力、出力、成功条件を定義する。

---

# 2. Capital Allocation Engine の役割

## 一言で言うと

```text
いくら買うかを決める
```

---

Candidate AI は

```text
何を見るか
```

を決める。

---

Opportunity AI は

```text
何を買うか
```

を決める。

---

Capital Allocation Engine は

```text
いくら買うか
```

を決める。

---

# 3. Capital Allocation Engine が解く問題

問いは以下。

```text
どの銘柄に

どれだけ資金を配分するか？
```

---

重要。

Capital Allocation Engine は、

```text
銘柄選定
```

をしない。

---

また、

```text
保有判断
```

もしない。

---

# 4. 設計思想

## 現時点の結論

AI化しない。

---

理由。

Phase13-Rの結果では、

```text
primary bottleneck:
candidate_quality

secondary bottleneck:
hold_exit_quality
```

だった。

資金効率は主犯ではなかった。

---

したがって、

vNext初期版では

```text
Capital Allocation AI
```

を作らない。

---

代わりに、

```text
ルールベース
```

で実装する。

---

# 5. システム内の位置付け

```text
Candidate AI

↓

Opportunity AI

↓

Capital Allocation Engine

↓

Order Manager
```

---

# 6. Input

Opportunity AI出力

```text
buy_rank

expected_edge_score

downside_risk_score
```

---

Portfolio情報

```text
cash_available

current_positions

current_assets
```

---

運用設定

```text
max_positions

max_position_size

minimum_order_size
```

---

# 7. Output

```text
order_plan

buy_amount

share_quantity

position_size

allocation_reason

skip_reason
```

---

例

```text
A銘柄
20万円

B銘柄
20万円

C銘柄
20万円

D銘柄
20万円

E銘柄
20万円
```

---

# 8. 初期ルール

vNext初期版

---

## 最大保有数

```text
5銘柄
```

---

## 均等配分

```text
保有枠数で均等割り
```

例

```text
資産100万円

最大保有5

↓

1銘柄20万円
```

---

## 新規購入

新規ポジション数

```text
max_positions
-
current_positions
```

以内。

---

## 追加購入

Position Management AI の

```text
ADD
```

は、無条件の買い増しではない。

初期版では、

```text
target_position_size
-
current_position_size
```

が正の範囲だけ購入候補にする。

以下は禁止。

```text
目標配分を超える買い増し

含み損ポジションへのナンピン

最大保有数や集中上限を超える買い増し
```

条件を満たさない場合は、

```text
skip_reason
```

を記録する。

---

## 現金不足

購入不能時

```text
skip_reason
```

を記録する。

---

# 9. やらないこと

以下は行わない。

---

## AI配分

例

```text
期待値90

↓

50%
```

のような配分。

---

## ケリー基準

---

## レバレッジ

---

## 信用取引

---

## ナンピン

---

## マーチンゲール

---

# 10. 将来の拡張候補

将来検討。

---

## Risk Adjusted Allocation

```text
期待値

ボラティリティ

リスク
```

を考慮。

---

## Kelly系

---

## Dynamic Position Sizing

---

ただし、

以下が成立してから。

```text
Candidate AI

Opportunity AI

Position Management AI
```

が安定稼働。

---

# 11. 成功条件

Capital Allocation Engine の成功条件。

---

## 必須

```text
資金不足にならない

過剰集中しない

常に購入可能
```

---

## 補助

```text
Capital Utilization
```

向上。

---

# 12. 失敗条件

---

## 1銘柄集中

例

```text
100万円

↓

1銘柄
```

---

## ナンピン前提

---

## レバレッジ依存

---

## Candidate AIの代わりになる

資金配分で

```text
銘柄選定
```

を始めたら失敗。

---

# 13. 将来AI化する条件

以下が成立した場合のみ検討。

```text
Candidate Quality改善

Opportunity精度改善

Position Management安定
```

---

その上で、

```text
資金配分が
ボトルネック
```

と確認できた場合。

---

# 14. 最終原則

Capital Allocation Engine は、

```text
利益を作る
```

ものではない。

---

利益は、

```text
Candidate AI

Opportunity AI

Position Management AI
```

が作る。

---

Capital Allocation Engine は、

```text
利益を壊さない
```

ことを目的とする。

---

vNext初期版では、

```text
シンプル

説明可能

均等配分
```

を採用する。
