# Phase13-I Simulation / Backtest Compatibility Design

作成日: 2026-07-07

判定: DESIGN_ONLY

## 1. 目的

Runtime v2 は将来的に、Production / Demo とは別に Simulation / Backtest mode を持てる設計にする。

ただし、Backtest 都合のロジックを Production Runtime へ混ぜない。

目的:

- Runtime v2 と同じ Data Model を使って Simulation / Backtest できるようにする。
- Runtime v2 と同じ State Machine / Transaction / Report / Audit を使えるようにする。
- Broker、Clock、Fill だけを Simulation 用に差し替えられるようにする。
- Backtest artifact を Production Current State へ混入させない。
- Backtest 結果や損益を AI 学習データへ混入させない。

Phase13-I は Simulation / Backtest Compatibility Design のみである。実装変更、Submit、Broker 注文、Demo / Production 注文、通知送信、`launchd` 再開、既存 plist 削除、新規 plist 作成、Backtest 実行、Simulation 実行は行わない。

## 2. 基本方針

- Simulation / Backtest は Production Runtime の一部ではない。
- Simulation / Backtest は Runtime v2 と互換の別 mode として扱う。
- Production Runtime に Backtest 専用ロジックを混ぜない。
- Backtest は実 Broker Submit を行わない。
- Backtest は Simulation Broker を使う。
- Backtest は Simulation Clock を使う。
- Backtest は Simulation Fill Model を使う。
- Backtest 結果は Production Current State に使わない。
- Backtest 損益・約定シミュレーション結果を AI 学習データに混ぜない。

## 3. Runtime Mode 分類

| mode | 説明 | Broker | Clock | Current State | 注文 |
| --- | --- | --- | --- | --- | --- |
| `production` | 実 Broker ReadOnly / Submit を使う本番運用 | real broker | real business day | production current | 厳格に制御。Phase13-Iでは禁止 |
| `demo` | Broker Demo 環境または Production 相当の手動リハーサル環境 | demo broker | real business day | demo current | Production 注文は禁止 |
| `simulation` | 現在または近い将来のデータを使い、Broker を Simulation Adapter に差し替える検証 mode | simulated broker | simulation or real-like clock | simulation current | 実 Broker Submit なし |
| `backtest` | 過去期間を対象に Clock、Market Data、Broker、Execution を Simulation Adapter に差し替えて検証する mode | simulated broker | simulation clock | backtest current | 実 Broker Submit なし |

## 4. 共通化するもの

Simulation / Backtest でも Runtime v2 本線と共通化してよいもの:

- Runtime Data Model
- Runtime State Machine
- Runtime Transaction Design
- Current State Contract の概念
- Pending Order Plan lifecycle
- Order / Execution / Position / Asset separation
- Report Runtime
- Audit Runtime
- Reconcile Runtime の考え方
- Notification payload generation

注意:

- Current State Contract は共通概念として使うが、保存先は environment / mode で分離する。
- Report は共通形式で生成してよいが、Production Report と混同しない。
- Audit は共通観点で実行してよいが、Production Audit と混同しない。

## 5. Adapter で差し替えるもの

Simulation / Backtest では以下を Adapter で差し替える。

- Broker Runtime
- Execution / Fill Runtime
- Market Data Runtime
- Clock / Calendar
- Cash / Buying Power source
- Order acceptance model
- Price source
- Slippage / fee / tax model
- Corporate action handling

| Runtime area | Production / Demo | Simulation / Backtest |
| --- | --- | --- |
| Broker Runtime | real broker / demo broker | Simulated Broker Adapter |
| Clock | real business day | Simulation Clock |
| Market Data | actual market data source | Historical Market Data Adapter |
| Execution | broker executions / positions | Simulated Fill Model |
| Cash / Buying Power | broker account / demo account | Simulated Cash Ledger |
| Order acceptance | broker response | simulated order acceptance model |
| Price source | live / official market data | historical or scenario price source |

## 6. Simulation Broker Adapter

役割:

- Broker Submit を実 Broker へ送らず、注文受付を Simulation 上で模擬する。
- Broker Orders 相当の結果を生成する。
- Broker Executions 相当の約定結果を生成する。
- Broker Positions 相当の保有状態を生成する。
- Broker Cash / Buying Power 相当の資金状態を生成する。

生成する evidence:

- Simulated BrokerOrder
- Simulated BrokerExecution
- Simulated BrokerPosition
- Simulated BrokerCashSnapshot

禁止:

- 実 Broker へ接続しない。
- 実 Broker Submit しない。
- Production Current State へ書かない。
- Simulation 結果を Production Broker 状態として扱わない。

## 7. Simulated Fill Model

将来対応候補:

- `next_open_fill`
- `same_close_fill`
- `limit_price_fill`
- `volume_constrained_fill`
- `partial_fill`
- `no_fill`
- `slippage_model`
- `fee_model`
- `tax_model`

注意:

- Phase13-I では実装しない。
- モデル詳細や損益評価は後続フェーズで定義する。
- Simulated Fill は BrokerExecution 相当の External Simulation Evidence として扱い、Production BrokerExecution とは分離する。
- Simulated Fill は AI 学習用の教師ラベルや実データ評価に混ぜない。

## 8. Simulation Clock / Calendar

Backtest では実時間ではなく Simulation Clock を使う。

定義するもの:

- `simulation_start_date`
- `simulation_end_date`
- `current_simulation_date`
- `target_session_date`
- `business_day_calendar`
- `market_open` / `market_close` simulation
- step unit

step unit 候補:

- `daily`
- `intraday`
- `event-driven`

Phase13-I では `daily` 前提でよい。Intraday / event-driven は後続フェーズで詳細化する。

## 9. Storage 分離

Simulation / Backtest artifact は Production Current と完全分離する。

### Option A: mode root 分離

```text
.runtime/production/
.runtime/demo/
.runtime/simulation/
.runtime/backtest/
```

利点:

- Production と Backtest の物理分離が明確。
- 誤読防止がしやすい。
- mode ごとに Current fixed path を同じ相対構造で保てる。

注意:

- 共通 reader は mode root を必ず明示する必要がある。

### Option B: object root + environment 分離

```text
runtime_state/{environment}/
pending_order_plan/{environment}/
persistent_ledger/{environment}/
reports/{environment}/
```

利点:

- object 種別ごとの比較がしやすい。

注意:

- path resolver が複雑になり、Production / Backtest 混入リスクが上がる。

### Phase13-I 方針案

Phase13-I では Option A を優先案とする。

```text
.runtime/{mode}/runtime_state/current_state.json
.runtime/{mode}/pending_order_plan/pending_order_plan.json
.runtime/{mode}/persistent_ledger/state.json
.runtime/{mode}/persistent_ledger/orders.jsonl
.runtime/{mode}/persistent_ledger/executions.jsonl
.runtime/{mode}/persistent_ledger/positions.jsonl
.runtime/{mode}/persistent_ledger/cash_history.jsonl
.runtime/{mode}/persistent_ledger/events.jsonl
.runtime/{mode}/notification_delivery/delivery_ledger.jsonl
.runtime/{mode}/reports/YYYY-MM-DD/
```

必須原則:

- Backtest Current を Production Current として読まない。
- Production Current を Backtest で上書きしない。
- Simulation / Backtest Report を Production Report として扱わない。
- environment / mode metadata を必ず持つ。
- `mode=backtest` の artifact は Production Submit 対象にならない。

## 10. AI 学習データ混入禁止

Backtest 結果を AI 学習データへ混ぜない。

混入禁止:

- Backtest 結果
- Backtest 損益
- Simulated fill
- Simulated position
- Simulated cash
- Simulated report
- Backtest selected / bought / sold
- Backtest ledger
- Backtest performance

これらは AI 学習用特徴量、教師ラベル、評価対象の実データとして使わない。

許可される使い方:

- Runtime 動作検証
- Transaction 検証
- Report 検証
- Safety 検証
- Ledger 整合性検証
- 運用テスト
- シナリオテスト

## 11. Backtest で検証したいこと

- Runtime State Machine が長期間壊れないか。
- Pending lifecycle が正しく進むか。
- Submit 重複が発生しないか。
- Order / Execution / Position / Asset が分離されているか。
- Ledger 二重反映が起きないか。
- Report が Current State から生成されるか。
- Current State 欠損時に BUY / Approval / Submit が止まるか。
- Recovery が機能するか。
- Notification delivery dedup が効くか。
- Safety 停止が効くか。
- Capital Allocation 結果が資金制約内に収まるか。
- 銘柄数固定上限を Runtime が持っていないか。

## 12. Backtest で検証しないこと

Phase13-I で明記する非対象:

- AI の将来収益保証
- Production 発注可否
- 実 Broker の約定保証
- 実運用での利益保証
- AI 再学習
- フルバックテスト実行

Phase13-I では Backtest を実行しない。設計のみである。

## 13. Simulation / Backtest Transaction

Runtime Transaction Design との対応:

Production:

```text
Submit Transaction
↓
Broker Submit
```

Backtest:

```text
Submit Transaction
↓
Simulated Broker Submit
↓
Simulated BrokerOrder
```

Production:

```text
Execution Reflection
↓
Broker Execution / Broker Position
```

Backtest:

```text
Execution Reflection
↓
Simulated Fill
↓
Simulated Position
```

重要:

- Transaction Boundary は同じ考え方を使う。
- 副作用先だけを差し替える。
- Production Broker Submit は絶対に呼ばない。
- Simulated Broker Submit は実 Broker 接続を持たない。
- Delivery Ledger の考え方は共通化できるが、Backtest notification は原則 send せず payload generation までに留める。

## 14. Report / Audit in Backtest

Backtest でも Report / Audit を生成してよい。

ただし:

- Backtest Report は Derived。
- Production Report とは分離。
- Backtest Audit は Runtime 検証用。
- Production Audit とは分離。

Report には必ず以下を表示する。

```text
mode=backtest
simulation_period
simulation_date
simulated=true
production_equivalent=false
not_for_trading=true
```

Backtest Report は Runtime Current 入力にしない。Backtest Report を Production Report として扱わない。

## 15. Safety

Backtest でも Safety を通す。

ただし:

- Safety ロジックを Runtime へ再実装しない。
- Safety 結果を Runtime 制御に接続するだけ。
- Backtest Safety 結果を Production Safety 状態に反映しない。
- Backtest Safety result は mode metadata と `production_equivalent=false` を持つ。

## 16. Acceptance Criteria

- Simulation / Backtest が Production Runtime と分離されている。
- Production Runtime に Backtest 専用ロジックを混ぜない。
- Broker Runtime / Clock / Market Data / Fill Model を Adapter 差し替え対象として定義している。
- Backtest artifact が Production Current に混入しない。
- Backtest 結果を AI 学習データに混ぜない。
- Backtest では実 Broker Submit を呼ばない。
- Backtest Report は Production Report と分離される。
- Transaction Boundary は共通概念として使える。
- Backtest で検証できる対象・できない対象が明確である。

## 17. 禁止事項

Phase13-I では以下を禁止する。

- 実装変更
- Submit
- Broker 注文
- Demo 注文
- Production 注文
- 通知送信
- `launchd` 再開
- 既存 plist 削除
- 新規 plist 作成
- artifact 削除
- AI 再学習
- フルバックテスト実行
- Backtest 実行
- Simulation 実行

## 18. 完了条件

- Simulation / Backtest Compatibility Design が作成されている。
- Production / Demo / Simulation / Backtest mode が整理されている。
- 共通化するものと差し替えるものが整理されている。
- Simulation Broker Adapter が定義されている。
- Simulated Fill Model 方針が定義されている。
- Simulation Clock / Calendar 方針が定義されている。
- Storage 分離方針が定義されている。
- Backtest 結果の AI 学習データ混入禁止が明記されている。
- Backtest で検証できること・できないことが整理されている。
- Transaction Design との対応が整理されている。
- JSON レポートが作成され、妥当性確認されている。
- 実装変更は一切行われていない。

