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

Acceptance Criteria

データ管理

```text
取得日を保存する

対象日を保存する

銘柄コードを保存する
```

重複防止

```text
同日再取得で重複しない
```

障害対応

```text
取得失敗をログに残す

欠損をログに残す
```

データ分離

```text
Raw Data

Feature Data

Future Label Data
```

を分離する。

セキュリティ

```text
APIキーをGit管理しない
```

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

## 30営業日Paper Trading / Unified Daily Operation Validation

目的

```text
Daily Paper Trading Validation

修正版ロジックで30営業日の日次AI運用を継続し、
Unified Runner / Ledger / Report / Trackerの安定性を確認する
```

---

構成

```text
Paper Ledger運用

20:00 launchd自動実行

J-Quants market refresh

canonical normalized update

feature refresh

daily inference

pending order作成

virtual fill

ledger valuation

Blog Report v4

30BD tracker

non-business-day skip

pending dedup

trading calendar guard

score saturation fix

phase9 bugfixes
```

統合対象

```text
Candidate

Opportunity

Position

Capital Allocation

Order Manager

Paper Ledger

Human Review / Auto Approval for Paper Trading

Safety status / no-live-order guard
```

統合。

---

完了条件

```text
30営業日Paper Trading完走

Unified Runner安定

Blog Report安定

Ledger/Tracker整合

Broker注文なし

実売買なし

重大バグ解消

Phase10に進むためのreadiness report作成
```

注意

```text
Phase9の30営業日テストは継続する

Phase9の結果はPhase10/Phase11の設計にフィードバックする
```

---

# 13. Phase10

## Tachibana Securities API Connection

目的

```text
立花証券e支店APIと接続し、
実売買前のBroker Integrationを進める
```

---

注意

```text
立花証券口座開設完了後に開始する

初期は必ずread-only / dry-run / sandbox相当から開始する

Phase10中の本番発注は原則禁止

Safety Layerなしでは実売買しない
```

---

想定スコープ

```text
1. 立花証券API認証情報管理

2. secrets管理

3. login/logoutまたはセッション管理

4. read-only疎通確認

5. account snapshot取得

6. positions取得

7. orders/history取得

8. market price / realtime quote取得

9. API response schema保存

10. Broker Snapshot保存

11. Tachibana Broker Adapter実装

12. Paper Ledgerとのreconciliation

13. dry-run order plan → broker order plan変換

14. 実発注禁止ガード

15. no-live-order audit
```

---

許可

```text
read-only API接続

価格取得

口座情報取得

保有銘柄取得

注文履歴取得

dry-run order validation

broker adapterのmock / dry-run

APIレスポンス保存

audit / pytest
```

禁止

```text
実買い注文

実売り注文

信用取引

unlock_trade

発注API実行

自動売買

Safety Layer未実装状態での本番売買

secretsの平文コミット
```

完了条件

```text
Tachibana read-only接続PASS

account/positions/orders/history snapshot取得PASS

realtime quote取得PASS

secrets管理PASS

order APIが明示的に禁止されていること

no-live-order audit PASS

Paper LedgerとBroker Snapshotのreconciliation設計完了

Phase11 Safety Layerに進める状態
```

---

# 14. Phase11

## Safety Layer / Emergency Brake

目的

```text
実運用前に、AI判断とは独立したSafety Layerを追加する

AIがどの銘柄を買いたいと言っても、
Safety Layerが危険と判断したら、
新規買い停止・保有縮小・売却候補化・全停止を行えるようにする
```

---

重要方針

```text
Safety LayerはAI判断とは独立したルールベース安全装置

人間は解除判断に使わず、解除条件もできるだけ自動化する

ただし実売買を伴う解除・売却はPhase12以降で慎重に扱う
```

---

想定スコープ

### 14.1 個別銘柄ブレーキ

```text
購入価格から -7% で警告

購入価格から -10% で売却候補

購入価格から -15% で強制売却候補

立花証券APIのリアルタイム価格で監視する設計

gap down時も検知できるようにする

約定保証はしないが、検知時に最短で売却判断へ回す
```

### 14.2 新規買い停止ブレーキ

発動条件例

```text
portfolio equityがpeak比 -5%

TOPIX / 日経平均が20日線割れ

保有銘柄の過半数が含み損

直近N営業日の損益が連続マイナス

market breadth悪化

data quality異常

stale price

API異常

Ledger/Broker不整合
```

発動時

```text
新規買い停止

pending buy cancel / block

保有銘柄は個別ルールで評価継続
```

### 14.3 緊急停止ブレーキ

発動条件例

```text
portfolio equityがpeak比 -10%

初期資金比 -10%

保有銘柄の半数以上が -7%超

Broker/Ledger不整合

price feed異常

order reconciliation異常

APIレスポンス異常

実売買安全境界違反
```

発動時

```text
新規買い停止

pending order停止

実発注停止

人間通知

必要に応じて売却候補生成

ただし即全売却は慎重に扱う
```

### 14.4 自動解除条件

```text
peak比DD -10%で緊急停止

peak比DD -5%以内まで回復

かつ 5営業日継続

TOPIX/日経平均が20日線上に回復

data quality正常

API正常

Ledger/Broker一致

pending/order不整合なし
```

解除時

```text
新規買い再開

pending order許可

ただし解除直後はposition size縮小から再開してもよい
```

### 14.5 Safety State Machine

状態例

```text
NORMAL

BUY_SUSPENDED

REDUCE_ONLY

EMERGENCY_STOP

RECOVERY_WATCH
```

遷移例

```text
NORMAL → BUY_SUSPENDED

BUY_SUSPENDED → RECOVERY_WATCH

RECOVERY_WATCH → NORMAL

BUY_SUSPENDED → EMERGENCY_STOP

EMERGENCY_STOP → RECOVERY_WATCH
```

### 14.6 Safety Report

毎日以下を出す。

```text
safety_state

triggered_rules

解除条件進捗

individual stop candidates

portfolio drawdown

market regime

data quality

broker reconciliation

allowed actions

blocked actions
```

---

許可

```text
Safety Layer設計

Safety State Machine実装

Paper Trading上でのSafety simulation

read-only broker data利用

realtime quote read-only監視

sell candidate generation

buy suspension

pending order block

audit / pytest
```

禁止

```text
Safety Layer未完成状態での本番自動発注

unlock_trade

無条件の全売却

人間承認なしの実売却

実売買

secrets平文保存
```

完了条件

```text
Safety State Machine PASS

-10% individual stop検知PASS

buy suspension PASS

emergency stop PASS

auto recovery PASS

Safety Report PASS

Paper TradingでSafety動作確認

Broker read-only / realtime quote連携確認

no-live-order audit PASS

Phase12以降の実運用準備に進める状態
```

---

# 15. Phase12

## Live Trading Readiness / Small Live Test

目的

```text
Phase10のBroker接続とPhase11のSafety Layerを前提に、
実売買へ進むための最終準備と少額検証を行う
```

---

条件

```text
Phase9 30営業日Paper Trading結果確認

Phase10 Tachibana read-only接続PASS

Phase11 Safety Layer PASS

no-live-order audit PASS

人間承認フロー確認

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
