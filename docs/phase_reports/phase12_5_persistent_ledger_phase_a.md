# Phase12.5 Persistent Ledger Phase A

作成日: 2026-07-04

## Summary

Demo / Production 共通の永続保持領域として `.runtime/operations/persistent_ledger/` の Phase A を実装した。

今回は schema / writer / reader / state集約のみ。Runtime本線の参照先切替、Broker Orders fallback projection、Daily Plan / Approval / Report の参照先切替、demo_ledger削除は行っていない。

## 追加モジュール

```text
src/ai_fund_lab_v2/operations/persistent_ledger.py
```

## Ledger保存領域

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

## 実装機能

- `append_order()`
- `append_execution()`
- `append_position_state()`
- `append_cash_state()`
- `append_event()`
- `summarize_persistent_ledger()`

## State集約

`state.json` には以下を集約する。

- `orders_count`
- `executions_count`
- `position_history_count`
- `cash_history_count`
- `event_count`
- `migration_count`
- `current_positions`
- `current_position_count`
- `current_market_value`
- `current_cash`
- `environments`
- `sources`
- `demo_production_common_storage=true`
- `runtime_reference_switched=false`
- `demo_ledger_legacy_deleted=false`

`current_positions` は `positions.jsonl` の最新position stateから、`issue_code / account_type / side / environment` 相当のposition keyで集約する。数量が0以下のposition stateはクローズ扱いでcurrentから外す。

## Dedup

JSONL append時に `dedup_key` を付与し、既存行に同じkeyがある場合は追記しない。

優先key:

- orders: `item_id`, `order_hash`, `broker_order_id_hash`
- executions: `execution_key`, `execution_hash`, `execution_id_hash`
- positions: `item_id`, `position_hash`, `position_key`
- cash: `cash_state_key`, `item_id`, `cash_hash`
- events: `event_id`, `event_hash`, `item_id`

優先keyがなければ、`recorded_at` を除くsanitized payloadのstable hashを使う。

## Redaction / 保存禁止

以下は保存しない。

- raw request
- raw response
- secret
- token
- session
- URL
- auth id
- account/customer id
- plain broker order id
- plain order id
- plain execution id

各record / state / append result に以下を明示する。

```json
{
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false,
  "plain_broker_ids_saved": false
}
```

## Demo / Production共通metadata

各recordは `environment` と `source` を保持する。`persistent_ledger/` はDemo専用名ではなく、Demo / Production共通の保存領域として使えるschemaにした。

なお、`source=broker_orders_fallback` かつ `environment=demo` の場合は `production_equivalent=false` になる設計を入れているが、今回はfallback projection自体は未実装。

## Runtime本線への影響

`operations.__init__` には接続していない。既存のDaily Plan / Approval / Report / demo_ledger参照先は切り替えていない。

## テスト

追加:

```text
tests/phase12/test_persistent_ledger_phase_a.py
```

実行:

```text
PYTHONPATH=src python3 -m pytest tests/phase12/test_persistent_ledger_phase_a.py tests/phase12/test_persistent_demo_ledger.py -q
PYTHONPYCACHEPREFIX=/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/persistent_ledger.py
```

結果:

```text
8 passed
py_compile PASS
```

補足: 最初の `py_compile` はmacOSのデフォルトpycache書き込み先権限で失敗したため、`PYTHONPYCACHEPREFIX=/tmp/aifundlab_pycache` を指定して構文確認した。

## 今回やっていないこと

- Broker Orders fallback projection
- Daily Plan参照先切替
- Approval参照先切替
- Report参照先切替
- demo_ledger削除
- Submit実行
- Broker注文
- Production接続
- Production注文
- artifact削除
- notification送信

## 残課題

Phase B以降で、Broker Positions / Broker Executions / Broker Orders fallback のどの確定情報を persistent_ledger に流すかを、Positions API safe diagnosisの結果を待って決める。
