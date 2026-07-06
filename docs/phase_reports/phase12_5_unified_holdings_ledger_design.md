# Phase12.5 Unified Holdings Ledger / Demo Ledger Deprecation Design

作成日: 2026-07-04

## 目的

現状は注文履歴を保持できている一方、約定後の確定状態である「現在保有」を永続的に保持できていない。

特に2026-07-03は、Broker Orders上では5件すべて `全部約定` だったが、`broker_executions=0`、`broker_positions=0`、`ledger.positions_count=0`、`demo_ledger.position_history_count=0` となり、翌日PlanやSELL候補生成で保有0扱いになるリスクが残った。

このため、Demoだけ `demo_ledger/`、Productionは別、という保持領域の分け方をやめ、Demo / Production共通の **Unified Ledger** に統一する。

## 現状問題

1. `demo_ledger/` はDemo専用であり、Production Equivalent Runtimeの本線SoTとして扱いにくい。
2. `ledger/YYYY-MM-DD/` はBroker read-onlyからの派生日次集計であり、永続状態ではない。
3. `broker_positions/YYYY-MM-DD` は日次snapshotで、Demo日次リセットやAPI parse不整合で0件になり得る。
4. Broker Orders fallbackで「約定らしい」ことは分かるが、現在保有へ永続反映されていない。
5. Approval exposureは `demo_ledger` / `submitted_orders` fallbackで一部補完するが、SELL候補・Report・position guardの正規SoTにはなっていない。
6. Reportではsynthetic position表示があり得るが、それは派生表示でありSoTではない。

## SoT定義

### 注文

注文はリクエストおよびBroker受付状態の履歴として扱う。

| 種別 | SoT |
|---|---|
| Submit試行履歴 | `submitted_orders/YYYY-MM-DD/submitted_orders.json` |
| Broker受付・注文状態 | `broker_orders/YYYY-MM-DD/orders.json` |
| 永続注文履歴 | `persistent_ledger/orders.jsonl` |

### 約定

約定はBroker Executions APIを最優先SoTにする。

| 環境 | 優先順位 |
|---|---|
| Production | 1. `broker_executions` 2. Unified Ledger executions 3. 不明なら `REVIEW_REQUIRED` |
| Demo | 1. `broker_executions` 2. Broker Orders fallback projection 3. Unified Ledger executions |

Demoのfallback projectionは常に以下を持つ。

```json
{
  "source": "broker_orders_fallback",
  "review_required": true,
  "production_equivalent": false
}
```

### 現在保有

現在保有は「翌日Plan / SELL候補 / Approval exposure / Report」が参照する最重要SoT。

Production優先順位:

1. `broker_positions/YYYY-MM-DD/positions.json`
2. `broker_executions/YYYY-MM-DD/executions.json` から当日分を反映
3. `persistent_ledger/positions.jsonl`
4. それでも無ければ `REVIEW_REQUIRED`

Demo優先順位:

1. `broker_positions/YYYY-MM-DD/positions.json`
2. `broker_executions/YYYY-MM-DD/executions.json`
3. `broker_orders` fallback projection
4. `persistent_ledger/positions.jsonl`

Demoでもfallback由来は必ず `review_required=true` を残す。

### 現金 / 買付余力

Production:

1. `broker_buying_power/YYYY-MM-DD/buying_power.json`
2. `broker_account_summary/YYYY-MM-DD/account_summary.json`
3. `persistent_ledger/cash_history.jsonl`
4. 不明なら `REVIEW_REQUIRED`

Demo:

1. Broker buying power / account summary
2. 100万円評価資金基準のDemo runtime policy
3. Unified Ledger cash history

Broker実口座2,000万円と評価資金100万円は混ぜず、metadataで用途を分ける。

### lifecycle

Runtime lifecycleは `fill_events/YYYY-MM-DD/fill_events.json` と Unified Ledger `events.jsonl` に保持する。

ただし lifecycle はBroker SoTを上書きしない。Broker Executions / Positionsが無い場合は、`REVIEW_REQUIRED` を維持する。

## demo_ledger廃止方針

`.runtime/operations/demo_ledger/` は今後SoTとして使わない。

方針:

- 新規書き込みを止める。
- 参照箇所をUnified Ledgerへ移す。
- 既存 `demo_ledger/` は `legacy_demo_ledger` としてmigration/fallback扱いにする。
- 移行完了後は削除可能なartifactにする。
- Demo固有補正は保存先を分けず、Unified Ledger内のmetadataで区別する。

metadata例:

```json
{
  "environment": "demo",
  "source": "broker_orders_fallback",
  "review_required": true,
  "production_equivalent": false,
  "demo_constraint": "broker_orders_filled_but_executions_or_positions_missing"
}
```

## Unified Ledger schema

推奨ディレクトリ:

```text
.runtime/operations/persistent_ledger/
```

理由:

- Demo / Production共通名
- `ledger/YYYY-MM-DD` との混同を避ける
- 日次派生集計ではなく、永続状態であることが名前から分かる

### ファイル構成

```text
.runtime/operations/persistent_ledger/
  orders.jsonl
  executions.jsonl
  positions.jsonl
  cash_history.jsonl
  events.jsonl
  state.json
  migrations.jsonl
```

### orders.jsonl

```json
{
  "record_type": "order",
  "recorded_at": "2026-07-03T08:50:00+09:00",
  "business_date": "2026-07-03",
  "environment": "demo",
  "source": "submitted_orders",
  "item_id": "buy_2026-07-02_65220_001",
  "side": "BUY",
  "internal_code": "65220",
  "broker_issue_code": "6522",
  "quantity": "100",
  "limit_price": "1960",
  "expected_notional": "196000",
  "status": "ORDER_ACCEPTED",
  "broker_order_id_hash": "sha256:...",
  "review_required": false,
  "production_equivalent": true,
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false
}
```

### executions.jsonl

```json
{
  "record_type": "execution",
  "recorded_at": "2026-07-03T15:45:00+09:00",
  "business_date": "2026-07-03",
  "environment": "demo",
  "source": "broker_orders_fallback",
  "side": "BUY",
  "internal_code": "65220",
  "broker_issue_code": "6522",
  "quantity": "100",
  "price": "1960",
  "notional": "196000",
  "broker_executions_api_confirmed": false,
  "broker_positions_api_confirmed": false,
  "review_required": true,
  "production_equivalent": false,
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false
}
```

### positions.jsonl

`positions.jsonl` はsnapshotではなく、position state eventをappendする。`state.json` が最新状態を集約する。

```json
{
  "record_type": "position_state",
  "recorded_at": "2026-07-03T15:45:00+09:00",
  "business_date": "2026-07-03",
  "environment": "demo",
  "source": "broker_orders_fallback",
  "position_state": "OPEN",
  "internal_code": "65220",
  "broker_issue_code": "6522",
  "quantity": "100",
  "average_price": "1960",
  "market_value": "196000",
  "review_required": true,
  "production_equivalent": false,
  "supersedes_previous_state": true,
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false
}
```

### cash_history.jsonl

```json
{
  "record_type": "cash_state",
  "recorded_at": "2026-07-03T15:45:00+09:00",
  "business_date": "2026-07-03",
  "environment": "demo",
  "source": "broker_buying_power",
  "cash_available": "19439420",
  "buying_power": "19439420",
  "evaluation_equity_basis": "1000000",
  "evaluation_basis_source": "demo_policy",
  "review_required": false,
  "production_equivalent": true
}
```

### events.jsonl

```json
{
  "record_type": "lifecycle_event",
  "recorded_at": "2026-07-03T15:45:00+09:00",
  "business_date": "2026-07-03",
  "environment": "demo",
  "event": "broker_orders_fallback_position_projection",
  "source": "broker_orders_fallback",
  "review_required": true,
  "production_equivalent": false
}
```

### state.json

`state.json` は最新の集約状態。Plan / Approval / Reportは原則ここを読む。

```json
{
  "artifact_type": "persistent_ledger_state",
  "generated_at": "2026-07-03T15:45:00+09:00",
  "environment": "demo",
  "current_positions": [
    {
      "internal_code": "65220",
      "broker_issue_code": "6522",
      "quantity": "100",
      "average_price": "1960",
      "market_value": "196000",
      "source": "broker_orders_fallback",
      "review_required": true,
      "production_equivalent": false
    }
  ],
  "cash": {
    "cash_available": "19439420",
    "buying_power": "19439420",
    "evaluation_equity_basis": "1000000"
  },
  "counts": {
    "orders": 5,
    "executions": 5,
    "positions": 5,
    "review_required_positions": 5
  },
  "current_positions_source": "broker_orders_fallback",
  "current_positions_review_required": true,
  "legacy_demo_ledger_used": false,
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false
}
```

## Demo / Production分岐

分岐は保存先ではなくmetadataとpolicyで行う。

| 観点 | Demo | Production |
|---|---|---|
| 保存先 | `persistent_ledger/` | `persistent_ledger/` |
| 現在保有優先 | broker_positions -> broker_executions -> broker_orders fallback -> persistent_ledger | broker_positions -> broker_executions -> persistent_ledger -> REVIEW_REQUIRED |
| Orders fallback | projection可。ただしreview_required必須 | 自動position projection禁止。REVIEW_REQUIRED |
| 100万円評価資金 | `evaluation_equity_basis` metadata | 使用しない |
| 2,000万円Demo口座 | broker cashとして保持するが評価資金とは分離 | 該当なし |
| 9000番台非約定 | Unified Ledgerにdemo constraint metadata付きで記録 | 該当なし |

## broker_orders fallback projection方針

Broker Ordersで以下が揃う場合:

```text
status=全部約定
executed_quantity > 0
remaining_quantity = 0
```

Demoでは以下を生成する。

- `executions.jsonl` に `source=broker_orders_fallback`
- `positions.jsonl` に `source=broker_orders_fallback`
- `state.json.current_positions` に反映
- `review_required=true`
- `production_equivalent=false`
- `broker_executions_api_confirmed=false`
- `broker_positions_api_confirmed=false`

Productionでは:

- `events.jsonl` に `POST_BROKER_ORDER_FILLED_STATUS_WITHOUT_EXECUTION_POSITION` を記録
- `state.json.current_positions` には反映しない
- `REVIEW_REQUIRED` とする
- 人間確認またはBroker Executions / Positions復旧を待つ

## Daily Planへの影響

Daily Planは現在保有を以下から取得する。

1. `persistent_ledger/state.json.current_positions`
2. `broker_positions/YYYY-MM-DD/positions.json` が新鮮であれば同期してstate更新
3. Demoのみ、Broker Orders fallback projectionがある場合はreview付きcurrent_positionsとして扱う

ルール:

- 現在保有が不明なら、保有0とみなしてBUY候補を出さない。
- `current_positions_unknown=true` の場合、Daily Planは `REVIEW_REQUIRED` または `BLOCK`。
- `broker_orders_fallback` 由来のpositionがある場合、BUY再選定は可能だがReport/Approvalにreview flagを残す。
- SELL候補生成は `persistent_ledger/state.json.current_positions` を基準にする。

7/3のような状態では、次回Planで保有0扱いではなく以下になるべき。

```json
{
  "current_positions_source": "broker_orders_fallback",
  "current_positions_review_required": true,
  "current_positions_count": 5
}
```

## Approvalへの影響

Approval exposureは以下を使う。

1. `persistent_ledger/state.json.current_positions.market_value`
2. Broker positions market value
3. Demo broker_orders fallback projection market value
4. 不明なら `REVIEW_REQUIRED`

`submitted_orders` の単純累積は最終fallbackに落とし、通常経路から外す。

理由:

- 注文はリクエストであり、約定・保有の確定SoTではない。
- 二重計上やキャンセル/失効反映漏れが起きる。

## Report / Notificationへの影響

Reportでは以下を分けて表示する。

1. 本日Submit実績
   - SoT: `submitted_orders/YYYY-MM-DD`
2. 約定確認
   - SoT: `broker_executions`
   - Demo fallback: `broker_orders_fallback`
3. 現在保有
   - SoT: `persistent_ledger/state.json.current_positions`
4. 現在保有source
   - `broker_positions`
   - `broker_executions`
   - `broker_orders_fallback`
   - `persistent_ledger`
5. Review表示
   - fallback projectionを使っている場合は必ず明示

通知payloadにも以下を追加する。

```json
{
  "current_positions_count": 5,
  "current_positions_source": "broker_orders_fallback",
  "current_positions_review_required": true,
  "execution_source": "broker_orders_fallback",
  "review_required_reasons": [
    "broker_orders_filled_but_broker_executions_missing",
    "broker_orders_filled_but_broker_positions_missing"
  ]
}
```

## 実装段階

### Phase A: Unified Ledger schema設計

目的:

- `persistent_ledger/` schemaを追加
- writer / reader / state aggregatorを作る
- まだ既存runtime参照先は変えない

作業:

- `src/ai_fund_lab_v2/operations/persistent_ledger.py` 追加
- `PersistentLedgerWriter`
- `PersistentLedgerState`
- `append_order`
- `append_execution`
- `append_position_state`
- `append_cash_state`
- `append_event`
- `summarize_persistent_ledger`
- tests追加

完了条件:

- orders/executions/positions/cash/events/stateをDemo/Production共通metadataで書ける
- raw request/response/secret/plain broker idを保存しない

### Phase B: Demo broker_orders fallback projection生成

目的:

- Broker Orders上の全部約定をDemoではreview付きprojectionとして永続化

作業:

- `write_broker_readonly_artifacts_from_snapshot()` またはFill Monitor後にprojection生成
- Demoのみ `executions.jsonl` / `positions.jsonl` / `state.json` へ反映
- Productionではprojection反映せずevent + REVIEW_REQUIRED

完了条件:

- 7/3相当のBroker Orders 5件全部約定 / executions 0 / positions 0で、persistent ledger current_positions=5、review_required=true
- Productionではcurrent_positionsに反映されない

### Phase C: Daily Plan / Approval / Report参照先統一

目的:

- 現在保有参照先をUnified Ledgerへ寄せる

作業:

- Daily Plan SELL候補生成のposition sourceを `persistent_ledger/state.json` にする
- Approval exposureを `persistent_ledger/state.json` 優先にする
- Report holdingsを `persistent_ledger/state.json` から表示する
- Notification payloadへpositions source/review flagを追加
- current_positions不明ならDaily Planを `REVIEW_REQUIRED` / `BLOCK`

完了条件:

- broker_positions emptyでもDemo fallback projectionがあれば保有0扱いにならない
- position sourceがReport/Auditに出る
- ProductionではBroker SoTが無い時に安易なfallbackをしない

### Phase D: demo_ledger legacy化

目的:

- `demo_ledger/` を本線SoTから外す

作業:

- `record_demo_*` 系の新規書き込みを停止またはpersistent ledger writerへ移譲
- 既存demo_ledger readerをmigration/fallbackに限定
- `legacy_demo_ledger_used` metadataを残す
- runbook / docs更新

完了条件:

- 新規runtimeで `demo_ledger/` に書かない
- `persistent_ledger/` が唯一の永続保持領域
- 既存demo_ledgerは削除可能

## リスク

1. Broker Orders fallbackをposition projectionへ使うと、実約定未確認の状態を強く見せるリスクがある。
   - 対策: Demo限定、`review_required=true`、`production_equivalent=false` を必須。
2. ProductionでOrders fallbackを使うと二重発注・誤保有の危険がある。
   - 対策: Productionではposition反映禁止。
3. `persistent_ledger` と日次 `ledger/YYYY-MM-DD` が混同される。
   - 対策: 日次ledgerは派生集計、persistent ledgerは永続SoTとschemaに明記。
4. 既存demo_ledger移行で二重計上が起きる。
   - 対策: migration recordとsource hashを持ち、同一item_id/order hashをdedup。
5. Reportがfallback projectionを通常保有のように見せる。
   - 対策: source/review flagを必ず表示。

## 今回実装していないこと

今回は設計と実装計画のみ。

- 実装変更なし
- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- notification送信なし
- secret/raw request/raw response保存なし
- AI再学習なし
- フルバックテストなし
- artifact削除なし
- artifact再生成なし
