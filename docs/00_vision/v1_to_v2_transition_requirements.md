# AI Fund Lab v1 → vNext 移行方針

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
AI Fund Lab v1
```

で得られた知見を整理し、

```text
AI Fund Lab vNext
```

をゼロベースで再設計するための方針を定義する。

---

# 2. 基本方針

## v1のコードは引き継がない

vNextは、

```text
v1の改善版
```

ではない。

---

vNextは、

```text
新規設計

新規実装

新規アーキテクチャ
```

として構築する。

---

# 3. 引き継ぐもの

引き継ぐのは、

```text
知見
```

のみ。

---

## 引き継ぐ

### 投資哲学の重要性

v1では、

```text
AIを先に作った
```

ため迷走した。

---

vNextでは、

```text
投資哲学

↓

戦略

↓

システム設計

↓

AI設計

↓

実装
```

の順番を守る。

---

### Strict OOS

引き継ぐ。

```text
Train

Validation

Test
```

分離。

---

### 学習禁止ルール

引き継ぐ。

禁止。

```text
backtest result

trade result

profit

selected

bought

sold

cash

portfolio

annual_return

final_assets
```

---

### 市場結果のみ学習

許可。

```text
future_return_*

future_max_return_*

future_max_drawdown_*
```

ラベルのみ。

---

### Broker Sync思想

引き継ぐ。

```text
証券会社状態を正とする
```

---

### Safety Guard思想

引き継ぐ。

```text
分からない時は止まる
```

---

# 4. 引き継がないもの

## すべてのAIモデル

引き継がない。

---

例

```text
Candidate AI

Stock Selection

Valuation

PM AI

Exit AI

Downside AI
```

すべて再設計。

---

## すべての学習済モデル

引き継がない。

---

## すべてのcurrent profile

引き継がない。

---

## すべての売買ルール

引き継がない。

---

## バックテスト成績

引き継がない。

---

理由

```text
前提条件が異なる

設計思想が異なる

投資哲学が異なる
```

---

# 5. v1で分かったこと

## Candidate Quality が重要

最重要。

---

利益の源泉は、

```text
何を買うか
```

である。

---

## Hold / Exit は重要

ただし主犯ではない。

---

## Capital Allocation は主犯ではない

初期版はルールベースでよい。

---

## AI乱立は失敗

役割が曖昧になる。

---

## 責務分離が必要

```text
Candidate

Opportunity

Position
```

は分離する。

---

# 6. vNextで守ること

## AIを増やさない

追加条件。

```text
役割

入力

出力

成功条件

失敗条件
```

定義必須。

---

## AIは未来を予言しない

AIは、

```text
期待値順位付け
```

を行う。

---

## 説明できないAIは禁止

以下は禁止。

```text
なぜ買うか説明できない

なぜ売るか説明できない

なぜ保有するか説明できない
```

---

# 7. vNextの再出発条件

実装開始条件。

---

以下が揃うこと。

```text
README

要件定義

システム構成

Candidate AI設計

Opportunity AI設計

Position Management AI設計

Capital Allocation Engine設計

Broker Integration設計

Safety Guard設計
```

---

揃うまでは実装しない。

---

# 8. vNextの目的

vNextは、

```text
v1を修正する
```

ためのプロジェクトではない。

---

目的は、

```text
信頼できる投資システムを作ること
```

である。

---

# 9. 最終原則

迷ったら確認する。

```text
この機能は

投資哲学に必要か？

既存コンポーネントで代替できないか？

説明できるか？

年率50%へ近づくか？
```

答えられない場合、

実装しない。
