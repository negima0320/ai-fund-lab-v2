# AI Fund Lab vNext システム要件定義

---

# 1. 目的

本システムは、

```text
AIを利用した日本株自動売買システム
```

を構築し、

```text
なるべく年率50%以上
```

を目指す。

---

ただし、

```text
利益だけを追求するシステム
```

ではない。

以下も同時に満たす。

```text
説明可能

監査可能

再現可能

感情を排除できる

自動運用可能
```

---

# 2. システム成功条件

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

## Secondary Metrics

以下は診断用とする。

```text
Profit Factor

Drawdown

Win Rate

Capital Utilization

Trade Count

Holding Period
```

---

注意

```text
PF改善

DD改善

Win Rate改善
```

だけでは成功としない。

---

# 3. 投資戦略要件

## 投資スタイル

```text
スイングモメンタム
```

---

## 保有期間

基本

```text
5〜30営業日
```

---

## 対象市場

```text
日本株
```

---

## 投資対象

```text
流動性が十分ある銘柄
```

---

除外候補

```text
極端な低流動性

整理銘柄

監理銘柄
```

---

# 4. Candidate AI要件

## 目的

```text
上昇候補発見
```

---

## 入力

```text
市場データ

企業情報

出来高

価格情報

市場環境
```

---

## 出力

```text
candidate_list

candidate_score
```

---

## 成功条件

```text
候補品質向上

候補抽出精度向上
```

---

## 禁止事項

```text
バックテスト結果利用

売買結果利用

ポートフォリオ状態利用
```

---

# 5. Opportunity AI要件

## 目的

```text
期待値ランキング
```

---

## 入力

```text
candidate_list

企業情報

市場情報

テクニカル情報
```

---

## 出力

```text
buy_rank

expected_edge

risk_score
```

---

## 成功条件

```text
平均trade return向上
```

---

## 禁止事項

```text
trade_result利用

profit利用

selected利用

bought利用
```

---

# 6. Position Management AI要件

## 目的

```text
保有継続判断

売却判断
```

---

## 入力

```text
保有日数

現在価格

購入価格

含み損益

市場環境
```

---

## 出力

```text
HOLD

EXIT

REDUCE

ADD
```

---

## 成功条件

```text
利益保持率向上

不要な損失削減
```

---

# 7. Capital Allocation Engine要件

## 目的

```text
資金配分
```

---

## 入力

```text
buy_rank

risk_score

口座残高

保有状況
```

---

## 出力

```text
購入株数

購入金額
```

---

## 成功条件

```text
資金効率向上
```

---

# 8. Order Manager要件

## 目的

```text
安全な発注
```

---

必須機能

```text
新規注文

売却注文

取消

約定確認

二重注文防止
```

---

# 9. Broker Sync Manager要件

## 目的

```text
証券口座同期
```

---

対象

```text
立花証券API
```

---

必須機能

```text
残高取得

保有銘柄取得

注文取得

約定取得

状態照合
```

---

# 10. Portfolio State Manager要件

## 目的

```text
現在状態管理
```

---

管理対象

```text
現金

保有銘柄

損益

購入価格

保有日数
```

---

# 11. Safety Guard要件

## 目的

```text
異常時停止
```

---

停止条件例

```text
API異常

口座不整合

想定外ポジション

異常損失

注文異常
```

---

## 出力

```text
WARNING

HALT
```

---

# 12. Reporting System要件

## 目的

```text
監査

分析

説明
```

---

保存対象

```text
AI判断

売買履歴

口座履歴

損益履歴

システムイベント
```

---

# 13. 学習データ要件

## 学習可能

```text
価格

出来高

財務

業績

市場データ
```

---

## ラベルとして利用可能

```text
future_return_*

future_max_return_*

future_max_drawdown_*
```

---

## 学習禁止

```text
backtest_result

trade_result

profit

cash

portfolio

selected

bought

sold

annual_return

final_assets

allocation_result

pm_result
```

---

# 14. Strict OOS要件

必須

```text
Train
Validation
Test
```

分離。

標準構成

```text
Train:
2023

Validation:
2024

Test:
2025
```

---

禁止

```text
2025評価

↓

2025学習済モデル
```

---

# 15. AI追加ルール

新しいAIを追加する前に確認する。

```text
既存AIで代替できないか？

本当に必要か？

役割が重複していないか？

投資哲学と整合しているか？
```

---

追加条件

```text
役割

入力

出力

成功条件

失敗条件
```

を定義してから実装する。

---

# 16. 最終原則

AI Fund Lab の目的は、

```text
AIを増やすこと
```

ではない。

---

目的は、

```text
信頼できる投資システムを作ること
```

である。

---

すべての実装は、

```text
この変更は

年率50%達成に

どう繋がるのか？
```

を説明できなければならない。
