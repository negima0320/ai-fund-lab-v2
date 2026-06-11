# AI Fund Lab vNext

## Documents

- [要件定義・設計ドキュメント](docs/README.md)
- [システム構成の全体像](docs/ai-found-lab.png)

## プロジェクトの目的

AI Fund Lab の目的は、AIを活用した株式売買システムを構築し、

```text
なるべく年率50%以上の利益を出すこと
```

を目指すことである。

ただし、

```text
年率50%を達成すること
```

だけが目的ではない。

以下も同時に満たすことを目標とする。

```text
なぜ買うのか説明できる

なぜ保有するのか説明できる

なぜ売るのか説明できる

システムを信頼して感情に流されず運用できる
```

また、売買状況をブログなどで情報共有する。

---

# 最重要原則

## AIは未来を予言しない

AI Fund Lab は、

```text
未来を当てる
```

システムではない。

AIは、

```text
候補の中から

期待値が高い銘柄を順位付けし、

期待値が上がりきった所で売却（利確）

または、過剰に下がったところで売却（損切り）

の判断を行う。
```

ために利用する。

---

# 投資哲学

## 投資スタイル

```text
スイングモメンタム
```

---

## 基本思想

市場は短期的には非効率であり、

良い企業が市場に評価され始めると、

その上昇トレンドは一定期間継続する傾向がある。

AI Fund Lab は、

```text
良い企業

かつ

上昇が始まり

かつ

まだ上昇余地がある
```

銘柄を発見し、

その上昇トレンドから利益を得ることを目的とする。

---

## 狙う期間

基本保有期間

```text
5〜30営業日
```

中心。

デイトレードは行わない。

長期投資も主目的としない。

---

## 買わない銘柄

以下は原則として避ける。

```text
単に安いだけの銘柄

下落中の銘柄

出来高が少ない銘柄

市場から評価されていない銘柄
```

---

## 買う銘柄

以下を満たす銘柄を狙う。

```text
企業品質が良い

市場が評価し始めている

価格モメンタムが発生している

出来高モメンタムが発生している

上昇余地が残っている
```

---

# システムの役割

AI Fund Lab は以下の判断を行う。

---

## Candidate AI

役割

```text
上昇候補発見

概要
全銘柄候補から、上昇候補を発見する
```

問い

```text
どの銘柄にモメンタムが発生しているか？
```

Input:

- 全銘柄リスト

- 株価OHLCV

- 出来高

- 移動平均

- 高値更新

- 出来高急増

- 市場/セクター情報

- 財務・業績情報

Output:

- candidate_list

- momentum_score

- quality_score

- candidate_reason

- excluded_reason

---

## Opportunity AI

役割

```text
期待値判定

概要
Candidate AIで抽出した銘柄の期待値を判定する
```

問い

```text
どの銘柄が最も大きな利益機会を持つか？
```

Input:

- candidate_list

- momentum_score

- quality_score

- opportunity features

- downside features

- 市場環境

Output:

- buy_rank

- expected_edge_score

- expected_return_horizon

- upside_score

- downside_risk_score

- buy_reason

- no_buy_reason

---

## Position Management AI

役割

```text
保有継続判定

概要
今持っているポジションをどう扱うか？を継続して判断する。
保有する、売却するの判断を行う
```

問い

```text
上昇トレンドは継続しているか？（保有）
上昇トレンドは終了したか？（利確）
急激な下げトレンドか？（損切）
```



Input:

- position_list

- entry_price

- current_price

- holding_days

- unrealized_return

- peak_return

- momentum_status

- downside_risk

- market_environment

Output:

- position_action

  - HOLD

  - EXIT

  - REDUCE

  - ADD

- action_reason

- exit_reason

- stop_loss_flag

- profit_take_flag

- trend_break_flag

---

## Capital Allocation Engine

役割

```text
資金管理
```

問い

```text
Candidate AI、Opportunity AIの結果から
どれだけ買うべきか？いくら買うべきか？を判断する
```

Input:

- buy_rank

- expected_edge_score

- downside_risk_score

- cash_available

- current_positions

- max_positions

- risk_limits

Output:

- order_plan

- buy_amount

- share_quantity

- position_size

- allocation_reason

- skip_reason

---

## Order Manager

役割

```text
注文管理
```

問い

```text
どの注文を発行するか？
```

責務
```text
新規注文

売却注文

注文状態管理

約定確認

取消処理

二重注文防止
```

Input:

- order_plan

- broker_account_state

- market_price

- trading_calendar

- risk_check_result

Output:

- order_request

- order_id

- order_status

- filled_quantity

- average_fill_price

- cancel_result

- order_error

---

## Broker Sync Manager

役割

```text
証券口座同期
```

問い

```text
実際の口座状態はどうなっているか？
```

責務
```text
現金残高取得

保有銘柄取得

注文一覧取得

約定履歴取得

システム状態との照合
```

Input:

- 立花証券APIの残高

- 保有株

- 注文一覧

- 約定履歴

- system_portfolio_state

Output:

- synced_cash

- synced_positions

- synced_orders

- reconciliation_result

- discrepancy_report

- sync_error

---

## Portfolio State Manager

役割

```text
保有資産管理
```

責務
```text
現在資産

評価損益

ポジション一覧

購入単価

保有日数

期待リターン管理
```

Input:

- synced_cash

- synced_positions

- filled_orders

- market_price

- AI判断履歴

Output:

- current_assets

- unrealized_profit_loss

- realized_profit_loss

- position_list

- holding_days

- entry_price

- current_return

- portfolio_snapshot

---

## Safety Guard

役割

```text
異常検知
```

責務
```text
APIエラー検知

口座不整合検知

想定外ポジション検知

異常損失検知

自動売買停止
```

Input:

- broker_sync_result

- order_status

- portfolio_snapshot

- daily_loss

- drawdown

- API error logs

- discrepancy_report

Output:

- safety_status

  - OK

  - WARNING

  - HALT

- halt_reason

- alert_message

- allowed_to_trade

---

## Reporting System

役割

```text
監査・分析
```

責務
```text
売買履歴

AI判断履歴

パフォーマンス分析

バックテスト結果

運用レポート
```

Input:

- AI判断履歴

- order history

- trade history

- portfolio snapshots

- performance metrics

- safety events

Output:

- daily_report

- trade_report

- performance_report

- AI decision audit

- backtest_report

- live_operation_report

---

## システムの判断フロー

```text
Candidate AI
↓
Opportunity AI
↓
Capital Allocation Engine
↓
Order Manager
↓
Broker Sync Manager
↓
Portfolio State Manager
↓
Position Management AI
↓
Safety Guard
```

---

# このプロジェクトで作らないもの

```text
- デイトレードAI

- 長期バリュー投資AI

- バックテスト結果を学習するAI

- AIを増やすためのAI

- 理由を説明できない売買ロジック

- current modelをいきなり上書きする実験
```

---

# AI開発の原則

## 市場を学習する

AIは、

```text
市場結果
```

を学習する。

---

## システム結果を学習しない

以下は学習禁止。

```text
backtest result

trade result

trade profit

selected

bought

sold

cash

portfolio

annual_return

final_assets

allocation result

pm result
```

---

## 学習に利用可能

以下は利用可能。

```text
主にJ-Quants APIから情報を取得する 

価格

出来高

財務情報

業績情報

テクニカル指標

市場指標

future_return_*

future_max_return_*

future_max_drawdown_*
```

ただし、

```text
future系はラベルのみ
```

であり、

featureとして利用してはならない。

---

# 評価指標

## Primary Metric

最重要指標

```text
Annual Return
```

---

## Secondary Metrics

以下は診断用。

```text
Profit Factor

Drawdown

Win Rate

Capital Utilization

Trade Count

Holding Period
```

これらは目的ではない。

---

# Reality Audit原則

新しいAIを作る前に必ず確認する。

```text
本当に必要か？

既存AIで代替できないか？

投資哲学と整合しているか？
```

---

# Strict OOS原則

Train / Validation / Test を厳格に分離する。

基本構成

```text
Train:
2023

Validation:
2024

Test:
2025
```

未来情報の混入は禁止。

---

# 最後に

AI Fund Lab の目的は、

```text
AIを作ること
```

ではない。

```text
信頼できる投資システムを作ること
```

である。

すべての実装は、

```text
この変更は

年率50%達成にどう繋がるのか？
```

を説明できなければならない。
