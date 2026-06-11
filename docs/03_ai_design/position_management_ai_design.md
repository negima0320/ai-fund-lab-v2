# AI Fund Lab vNext Position Management AI 設計書

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
Position Management AI
```

の役割、責務、入力、出力、成功条件を定義する。

---

# 2. Position Management AI の役割

## 一言で言うと

```text
保有ポジションを管理するAI
```

---

Candidate AIは、

```text
候補発見
```

---

Opportunity AIは、

```text
購入判断
```

---

Position Management AIは、

```text
購入後
```

を担当する。

---

# 3. Position Management AI が解く問題

問いは以下。

```text
この銘柄を

保有し続けるべきか？

売却するべきか？

買い増しするべきか？

減らすべきか？
```

---

重要。

Position Management AIは、

```text
何を買うか
```

を決めない。

---

Position Management AIは、

```text
持っている銘柄をどう扱うか
```

だけを判断する。

---

# 4. Position Management AI の位置付け

```text
Candidate AI

↓

Opportunity AI

↓

Capital Allocation Engine

↓

購入

↓

Position Management AI

↓

HOLD
EXIT
ADD
REDUCE
```

---

# 5. 投資哲学との関係

AI Fund Lab の投資哲学は、

```text
良い企業

+

上昇開始

+

上昇継続
```

を取ること。

---

したがって、

Position Management AIの目的は、

```text
利益を最大化すること
```

ではない。

---

目的は、

```text
上昇トレンドが続く限り持つ
```

こと。

---

# 6. Position Management AI の思想

## やらないこと

```text
天井を当てる

底を当てる

最高値で売る
```

---

これは不可能。

---

## やること

```text
上昇継続中なら持つ

失速したら売る

シナリオ崩壊なら損切りする
```

---

# 7. Input

## Portfolio情報

```text
entry_price

holding_days

position_size

current_return

peak_return
```

---

## 市場データ

```text
現在価格

高値

安値

終値

出来高
```

---

## テクニカル

```text
価格モメンタム

出来高モメンタム

移動平均

トレンド強度

ボラティリティ
```

---

## Opportunity情報

```text
expected_edge_score

downside_risk_score
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

future_profit

future_sell_price

future_best_price
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

Position Management AI は未来を見ない。

---

# 9. Output

---

## HOLD

意味

```text
上昇継続中
```

---

## EXIT

意味

```text
上昇終了

シナリオ崩壊
```

---

## ADD

意味

```text
強い上昇継続

追加購入候補
```

注意:

```text
ADD は買い増し命令ではない。

ADD は買い増し候補シグナルである。

最終的な購入可否、購入金額、保有上限判定は Capital Allocation Engine が行う。

含み損ポジションへのナンピン目的ADDは禁止。
```

---

## REDUCE

意味

```text
上昇継続だが

リスク増大
```

---

## action_reason

例

```text
トレンド継続

出来高維持

失速検知

ストップ条件発動
```

---

# 10. Position Management AI が判断しないこと

---

## 候補抽出

担当

```text
Candidate AI
```

---

## 購入順位

担当

```text
Opportunity AI
```

---

## 購入金額

担当

```text
Capital Allocation Engine
```

---

## 注文実行

担当

```text
Order Manager
```

---

# 11. Position Management AI が見るもの

重要。

Position Management AIは、

```text
利益
```

ではなく、

```text
トレンド
```

を見る。

---

例

悪い考え方

```text
+5%

だから売る
```

---

良い考え方

```text
+5%

でも上昇継続

↓

保有
```

---

例

```text
+2%

失速

↓

売却
```

---

# 12. 成功条件

成功条件は、

```text
利益保持率向上
```

である。

---

評価例

```text
profit_retention_rate

winner_to_loser_rate

profit_decay_before_exit
```

---

目標

```text
上昇トレンドを取り切る

不要な損失を防ぐ
```

---

# 13. 失敗条件

---

## 利益確定AIになる

例

```text
+5%で売る

+10%で売る
```

だけ。

---

これは失敗。

---

## 損切りAIになる

例

```text
損切りしかしない
```

---

これも失敗。

---

## Opportunity AIと重複

Position Management AIが、

```text
どの銘柄を買うか
```

を判断したら失敗。

---

# 14. Position Management AI vNext 仮説

現時点の仮説。

---

保有継続条件

```text
価格モメンタム継続

出来高維持

市場環境良好
```

---

売却条件

```text
モメンタム失速

トレンド崩壊

市場環境悪化

ストップ条件発動
```

---

# 15. 将来の拡張

候補。

```text
モメンタム失速AI

利益保持AI

トレンド寿命推定

市場レジーム判定
```

---

ただし、

```text
Position Management AI

=
保有ポジション管理
```

という責務は変えない。

---

# 16. 最終原則

Position Management AIは、

```text
最高値で売るAI
```

ではない。

---

Position Management AIは、

```text
上昇トレンドが続く限り保有し、

上昇トレンドが終わったら売却するAI
```

である。

---

利益を最大化するのではなく、

トレンドを最大限活用することを目的とする。
