# AI Fund Lab vNext システムアーキテクチャ設計

---

# 1. このドキュメントの目的

このドキュメントは、AI Fund Lab vNext の全体構成を定義する。

目的は以下である。

```text
各コンポーネントの責務を明確にする

AIと非AIの役割を分離する

データの流れを明確にする

売買判断と運用管理を混同しない

実装時に要件が狂わないようにする
```

---

# 2. 全体思想

AI Fund Lab vNext は、

```text
投資判断システム

+

自動売買運用システム
```

で構成する。

投資判断システムは、

```text
何を買うか

いつ売るか

どれだけ買うか
```

を決める。

自動売買運用システムは、

```text
注文する

約定確認する

証券口座と同期する

異常時に止める

記録する
```

を担当する。

---

# 3. 全体フロー

```text
J-Quants API
    ↓
Market Data Store
    ↓
Feature Builder
    ↓
Candidate AI
    ↓
Opportunity AI
    ↓
Broker Sync Manager
    ↓
Portfolio State Manager
    ↓
Position Management AI
    ↓
Capital Allocation Engine
    ↓
Safety Guard
    ↓
Order Manager
    ↓
立花証券 API
    ↓
Broker Sync Manager
    ↓
Portfolio State Manager
```

監視・監査系として以下が常時動作する。

```text
Safety Guard

Reporting System
```

---

# 4. コンポーネント一覧

## 4.1 J-Quants API

役割:

```text
市場データ取得
```

取得対象:

```text
株価

出来高

財務情報

業績情報

上場銘柄情報

市場指標
```

J-Quants API は投資判断の元データを提供する。

---

## 4.2 Market Data Store

役割:

```text
取得した市場データを保存する
```

責務:

```text
日足データ保存

財務データ保存

業績データ保存

銘柄マスタ保存

取得履歴管理
```

注意:

```text
市場データと売買結果を混ぜない
```

---

## 4.3 Feature Builder

役割:

```text
AIやルールが利用する特徴量を作る
```

作成する特徴量例:

```text
価格モメンタム

出来高モメンタム

移動平均

高値更新

ボラティリティ

企業品質

市場環境

セクター相対強度
```

禁止:

```text
backtest result を特徴量にする

trade result を特徴量にする

selected / bought / sold を特徴量にする

future系を特徴量にする
```

---

# 5. 投資判断レイヤー

## 5.1 Candidate AI

目的:

```text
上昇候補を発見する
```

問い:

```text
どの銘柄にモメンタムが発生しているか？
```

Input:

```text
全銘柄リスト

価格特徴量

出来高特徴量

企業品質特徴量

市場環境特徴量
```

Output:

```text
candidate_list

candidate_score

candidate_reason

excluded_reason
```

責務:

```text
全銘柄から候補を絞る

低流動性や明らかに対象外の銘柄を除外する

上昇開始候補を抽出する
```

成功条件:

```text
候補群の平均期待値が市場平均より高い

候補数が運用可能な範囲に収まる

説明可能な候補理由がある
```

---

## 5.2 Opportunity AI

目的:

```text
候補銘柄の期待値を判定し、買い順位を決める
```

問い:

```text
どの銘柄が最も大きな利益機会を持つか？
```

Input:

```text
candidate_list

candidate_score

価格モメンタム

出来高モメンタム

企業品質

市場環境

リスク特徴量
```

Output:

```text
buy_rank

expected_edge_score

expected_return_horizon

upside_score

downside_risk_score

buy_reason

no_buy_reason
```

責務:

```text
候補銘柄を順位付けする

期待値が低い銘柄を除外する

買う理由を説明する
```

成功条件:

```text
上位候補の平均trade returnが改善する

要求平均trade returnに近づく

downsideが過剰に悪化しない
```

---

## 5.3 Capital Allocation Engine

目的:

```text
いくら買うかを決める
```

Input:

```text
buy_rank

expected_edge_score

downside_risk_score

現金残高

現在ポジション

最大保有数

リスク上限
```

Output:

```text
order_plan

buy_amount

share_quantity

position_size

allocation_reason

skip_reason
```

責務:

```text
購入金額を決める

購入株数を決める

過剰集中を防ぐ

買付余力不足を判定する
```

注意:

```text
Capital Allocation Engine は銘柄選定をしない

期待値を作らない

あくまで資金配分を担当する
```

---

## 5.4 Position Management AI

目的:

```text
保有ポジションをどう扱うか判断する
```

問い:

```text
上昇トレンドは継続しているか？

売るべきか？

保有すべきか？

追加すべきか？

減らすべきか？
```

Input:

```text
position_list

entry_price

current_price

holding_days

unrealized_return

peak_return

momentum_status

downside_risk

market_environment
```

Output:

```text
position_action

HOLD

EXIT

REDUCE

ADD

action_reason

exit_reason

stop_loss_flag

profit_take_flag

trend_break_flag
```

責務:

```text
利益を伸ばす

損失を抑える

トレンド失速を検知する

売却理由を説明する
```

注意:

```text
Hold AI と Exit AI は分離しない

Position Management AI に統合する
```

---

# 6. 自動売買運用レイヤー

## 6.1 Order Manager

目的:

```text
注文を安全に作成・管理する
```

Input:

```text
order_plan

broker_account_state

market_price

trading_calendar

risk_check_result
```

Output:

```text
order_request

order_id

order_status

filled_quantity

average_fill_price

cancel_result

order_error
```

責務:

```text
新規注文

売却注文

注文取消

注文状態管理

約定確認

二重注文防止
```

注意:

```text
Order Manager は投資判断をしない

AI判断を受け取って注文処理だけを行う
```

---

## 6.2 立花証券 API

役割:

```text
実際の注文・照会を行う外部API
```

利用用途:

```text
買い注文

売り注文

注文照会

残高照会

保有株照会

約定照会
```

注意:

```text
証券会社APIの状態を正とする

システム内部状態と差異があれば同期・停止する
```

---

## 6.3 Broker Sync Manager

目的:

```text
証券口座とシステム状態を同期する
```

Input:

```text
立花証券APIの残高

保有株

注文一覧

約定履歴

system_portfolio_state
```

Output:

```text
synced_cash

synced_positions

synced_orders

reconciliation_result

discrepancy_report

sync_error
```

責務:

```text
実口座状態を取得する

システム状態と照合する

不一致を検出する

約定結果をPortfolio State Managerへ反映する
```

---

## 6.4 Portfolio State Manager

目的:

```text
保有資産の状態を管理する
```

Input:

```text
synced_cash

synced_positions

filled_orders

market_price

AI判断履歴
```

Output:

```text
current_assets

unrealized_profit_loss

realized_profit_loss

position_list

holding_days

entry_price

current_return

portfolio_snapshot
```

責務:

```text
現在資産を管理する

保有銘柄を管理する

損益を管理する

保有日数を管理する

Position Management AIへ状態を渡す
```

注意:

```text
Portfolio State Manager は投資判断をしない

状態管理のみを担当する
```

---

# 7. 監視・安全・監査レイヤー

## 7.1 Safety Guard

目的:

```text
異常を検知し、自動売買を停止する
```

Input:

```text
broker_sync_result

order_status

portfolio_snapshot

daily_loss

drawdown

API error logs

discrepancy_report
```

Output:

```text
safety_status

OK

WARNING

HALT

halt_reason

alert_message

allowed_to_trade
```

停止条件例:

```text
API異常

口座不整合

想定外ポジション

二重注文疑い

異常損失

日次損失上限超過

システム内部状態と証券口座状態の不一致
```

原則:

```text
異常時は売買を継続しない

原因不明のまま自動売買しない
```

---

## 7.2 Reporting System

目的:

```text
判断と結果を監査可能にする
```

Input:

```text
AI判断履歴

order history

trade history

portfolio snapshots

performance metrics

safety events
```

Output:

```text
daily_report

trade_report

performance_report

AI decision audit

backtest_report

live_operation_report
```

責務:

```text
売買理由を記録する

AI判断を記録する

成績を記録する

失敗理由を分析できるようにする

ブログなどで共有可能な情報を整理する
```

---

# 8. データの分類

## 8.1 Market Data

```text
株価

出来高

財務

業績

市場指標
```

用途:

```text
feature作成

AI学習

AI推論
```

---

## 8.2 Future Label Data

```text
future_return_*

future_max_return_*

future_max_drawdown_*
```

用途:

```text
学習ラベル

評価ラベル
```

禁止:

```text
featureとして使用しない

entry判断に使用しない

exit判断に使用しない
```

---

## 8.3 Trading Data

```text
注文

約定

売買損益

保有銘柄

現金残高

portfolio
```

用途:

```text
運用管理

監査

レポート
```

禁止:

```text
AI学習featureに使用しない

AI targetに使用しない
```

---

# 9. AIと非AIの境界

## AIが担当すること

```text
候補発見

期待値判定

ポジション判断
```

---

## ルール・エンジンが担当すること

```text
資金配分

注文管理

口座同期

状態管理

異常検知
```

---

## 外部APIが担当すること

```text
J-Quants API:
市場データ取得

立花証券 API:
注文・約定・残高・保有株照会
```

---

# 10. 実行サイクル

## 日次サイクル

```text
1. J-Quants APIから市場データ取得

2. Feature Builderで特徴量作成

3. Candidate AIで候補抽出

4. Opportunity AIで買い順位決定

5. Broker Sync Managerで口座状態確認

6. Portfolio State Managerで現在状態更新

7. Position Management AIで保有銘柄判断

8. Capital Allocation Engineで購入金額決定

9. Safety Guardで売買可否判定

10. Order Managerで注文実行

11. Broker Sync Managerで約定確認

12. Reporting Systemで記録・レポート作成
```

---

# 11. 設計上の禁止事項

以下は禁止する。

```text
AIを増やすためにAIを作る

既存AIと役割が重複するAIを追加する

backtest結果を学習featureに使う

trade結果を学習featureに使う

証券口座状態をAI学習featureに使う

Safety Guardを通さず注文する

Broker Syncなしにportfolioを更新する

理由を記録せず売買する
```

---

# 12. このアーキテクチャの狙い

本アーキテクチャは、

```text
投資判断

資金管理

注文実行

口座同期

安全停止

監査
```

を明確に分離する。

これにより、

```text
なぜ買ったのか

なぜ売ったのか

本当に注文されたのか

実際の口座状態と一致しているのか

異常時に止まれるのか
```

を説明できる状態にする。

---

# 13. 最終原則

AI Fund Lab vNext は、

```text
AIが勝手に売買するブラックボックス
```

ではない。

```text
投資哲学に基づき、

各判断を説明でき、

口座状態を正しく管理し、

異常時に停止できる

信頼可能な自動売買システム
```

である。
