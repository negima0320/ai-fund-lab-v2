# Phase12.5 Persistent Ledger Reader Layer

作成日: 2026-07-04

## Summary

Persistent Ledger Phase A の schema / writer / state集約に続き、Runtime本線へ接続する前段として Reader Layer を実装した。

今回は読み取りインターフェースのみ。Daily Plan / Approval / Report / Notification の参照先切替、Broker Orders fallback projection、Unified Ledger Phase B は実装していない。

## 実装内容

対象:

```text
src/ai_fund_lab_v2/operations/persistent_ledger.py
```

追加したReader関数:

- `read_persistent_ledger_state(root)`
- `get_current_positions(root)`
- `get_current_cash(root)`
- `get_position_by_code(root, code)`
- `get_execution_history(root, code=None, date_from=None, date_to=None)`
- `get_order_history(root, code=None, date_from=None, date_to=None)`
- `get_positions_source_summary(root)`
- `get_review_required_positions(root)`

## state.json優先

Readerは基本的に `.runtime/operations/persistent_ledger/state.json` を読む。

`state.json` が無い場合は空状態を返すが、以下を必ず含める。

```json
{
  "state_missing": true,
  "current_state_confirmed_empty": false
}
```

これにより、将来Runtime本線が誤って「保有0確定」と扱わないようにする。

## current_positions

`get_current_positions()` は以下を返す。

- `current_positions`
- `current_position_count`
- `current_market_value`
- `current_positions_source`
- `current_positions_review_required`
- `review_required_position_count`
- `state_missing`

`source=broker_orders_fallback` のpositionは、Reader側でも必ず `review_required=true` として返す。

## cash

`get_current_cash()` は以下を返す。

- `cash_available`
- `buying_power`
- `evaluation_equity_basis`
- `currency`
- `cash_source`
- `cash_review_required`
- `state_missing`

`evaluation_equity_basis` は `buying_power` 優先、なければ `cash_available`、それもなければ `0`。

## code normalize

`get_position_by_code()` / history filter は4桁broker issue codeと5桁internal codeの両方で検索できる。

例:

```text
6522
65220
```

どちらでも同じpositionを取得できる。

## History filter

`get_execution_history()` / `get_order_history()` は以下でfilterできる。

- `code`
- `date_from`
- `date_to`

code filterも4桁/5桁を吸収する。

## Redaction

Reader返却時にも禁止keyを落とす。

返さないもの:

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

安全フラグは返す。

```json
{
  "raw_request_saved": false,
  "raw_response_saved": false,
  "secret_saved": false,
  "plain_broker_ids_saved": false
}
```

## Runtime本線に接続していないこと

以下は行っていない。

- Daily Plan参照先切替
- Approval参照先切替
- Report参照先切替
- Notification参照先切替
- Broker Orders fallback projection
- demo_ledger削除
- Unified Ledger Phase B実装

確認:

```text
rg persistent_ledger src/ai_fund_lab_v2/operations --glob '!persistent_ledger.py'
```

該当なし。

## テスト

追加:

```text
tests/phase12/test_persistent_ledger_reader_layer.py
```

実行:

```text
PYTHONPATH=src python3 -m pytest tests/phase12/test_persistent_ledger_reader_layer.py tests/phase12/test_persistent_ledger_phase_a.py -q
PYTHONPYCACHEPREFIX=/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/persistent_ledger.py
```

結果:

```text
14 passed
py_compile PASS
```

## 残課題

- Positions Safe Diagnosisの次回実行結果を確認する。
- Broker Positions API / normalizer / writer filter の原因分類が済むまで、Broker Orders fallback projectionは実装しない。
- Runtime本線参照先切替は、Persistent LedgerのSoT方針が確定してから行う。
