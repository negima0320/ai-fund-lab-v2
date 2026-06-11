# AI Fund Lab vNext 開発ロードマップ

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
AI Fund Lab vNext
```

の開発順序を定義する。

---

目的は、

```text
何を作るべきか

今どこにいるのか

次に何を作るべきか
```

を明確にすることである。

---

# 2. 開発方針

vNextでは、

```text
投資哲学

↓

要件定義

↓

システム設計

↓

AI設計

↓

実装

↓

検証

↓

運用
```

の順番を守る。

---

禁止。

```text
とりあえずAI作る
```

---

# 3. 現在地

完了済み。

```text
README

docs/README

00_vision/investment_philosophy

00_vision/v1_to_v2_transition_requirements

01_requirements/system_requirements

01_requirements/success_metrics

01_requirements/phase_roadmap

02_architecture/system_architecture

02_architecture/broker_integration_design

02_architecture/safety_guard_design

03_ai_design/candidate_ai_design

03_ai_design/opportunity_ai_design

03_ai_design/position_management_ai_design

03_ai_design/capital_allocation_design
```

---

現在

```text
設計フェーズ
```

完了。

---

# 4. Phase1

## Data Foundation

目的

```text
市場データ基盤構築
```

---

実装対象

```text
J-Quants接続

Market Data Store

Feature Builder基盤
```

---

完了条件

```text
日次データ取得

保存

再取得

更新
```

可能。

---

# 5. Phase2

## Broker Foundation

目的

```text
証券会社接続
```

---

実装対象

```text
立花証券接続

Broker Sync

Portfolio State
```

---

完了条件

```text
残高取得

保有株取得

注文一覧取得
```

可能。

---

# 6. Phase3

## Safety Foundation

目的

```text
事故防止
```

---

実装対象

```text
Safety Guard

ログ

監査基盤
```

---

完了条件

```text
異常検知

停止
```

可能。

---

# 7. Phase4

## Candidate AI vNext

目的

```text
上昇候補抽出
```

---

問い

```text
どの銘柄にモメンタムが発生しているか？
```

---

成功条件

```text
候補品質向上
```

---

# 8. Phase5

## Opportunity AI vNext

目的

```text
期待値順位付け
```

---

問い

```text
どの銘柄を買うべきか？
```

---

成功条件

```text
平均trade edge向上
```

---

# 9. Phase6

## Position Management AI vNext

目的

```text
保有判断
売却判断
追加判断
縮小判断
```

---

問い

```text
保有継続か？

売却か？

追加か？

縮小か？
```

---

成功条件

```text
profit_retention改善
```

---

# 10. Phase7

## Capital Allocation Engine

目的

```text
資金配分
```

---

実装

```text
均等配分
```

から開始。

---

AI化しない。

---

# 11. Phase8

## Order Manager

目的

```text
発注
```

---

実装

```text
新規注文

売却注文

取消

約定確認
```

---

# 12. Phase9

## Paper Trading

目的

```text
仮想運用
```

---

構成

```text
Candidate

Opportunity

Position

Capital

Safety
```

統合。

---

完了条件

```text
仮想運用可能
```

---

# 13. Phase10

## Historical Evaluation

目的

```text
過去評価
```

---

注意

```text
学習ではない

評価
```

---

確認

```text
Annual Return

PF

DD

Trade Count
```

---

# 14. Phase11

## Small Live Test

目的

```text
少額実運用
```

---

条件

```text
Safety Guard稼働

Broker Sync稼働

監査可能
```

---

# 15. Phase12

## Full Automation

目的

```text
完全自動運用
```

---

条件

```text
少額運用成功

安全性確認
```

---

# 16. フェーズ進行ルール

次へ進める条件。

---

必須

```text
成功条件達成
```

---

禁止

```text
未完成のまま次へ進む
```

---

# 17. AI追加ルール

新AI追加条件。

---

必須

```text
役割

入力

出力

成功条件

失敗条件
```

定義。

---

追加理由

```text
Annual Return改善との関係
```

説明必須。

---

# 18. 凍結ルール

vNext初期版では作らない。

---

```text
Position Management AIとは別の追加PM系AI

Exit AI

Downside AI

複雑なAllocation AI

ニュースAI

SNS分析AI

LLM判断AI

レバレッジ

信用取引
```

---

理由

```text
まずはコア戦略を成立させる
```

---

# 19. 完成条件

vNext完成とは、

```text
AIが動く
```

ことではない。

---

以下を満たすこと。

```text
理由を説明できる

監査できる

停止できる

運用できる

信頼できる
```

---

# 20. 最終原則

迷ったら確認する。

```text
今やろうとしていることは

ロードマップ上で必要か？
```

---

必要でないなら、

実装しない。

---

vNextは、

```text
実装主導
```

ではなく、

```text
設計主導
```

で進める。
