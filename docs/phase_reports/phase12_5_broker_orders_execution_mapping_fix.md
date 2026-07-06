# Phase12.5 Broker Orders / Executions / Positions Mapping Fix

作成日: 2026-07-03

## 目的

Phase12.5 Day1で、Broker Orders上は5件すべて `全部約定` と確認できた一方、Runtime artifactでは `broker_executions=0` / `broker_positions=0` となり、Reconcileが実態を説明しきれない状態だった。

本修正では、Broker Orders / Executions / Positions のschemaと分類を整理し、Broker Executions APIまたはOrder Detailが不足している場合でも、Broker Orders上の約定シグナルを隠さず `REVIEW_REQUIRED` として扱えるようにした。

## 修正内容

### 1. issue_code / code schema統一

Broker Orders artifactでは `issue_code` を正フィールドとして扱い、下流互換のため `code` aliasも同じ値で出力するようにした。

出力方針:

```json
{
  "issue_code": "6522",
  "code": "6522",
  "broker_issue_code": "6522"
}
```

これにより、表示やReconcile側で `code=null` に見える経路を避ける。

### 2. side mapping修正

立花仕様に合わせ、Broker Orders / Order Detailのside正規化を以下に統一した。

```text
sBaibaiKubun=1 -> SELL
sBaibaiKubun=3 -> BUY
```

既存のmock fixtureで `1` をBUY相当として使っていた箇所も `3` に更新した。

### 3. Order Detail全件取得

`run_tachibana_broker_snapshot()` で、Broker Ordersの先頭1件だけではなく全注文に対して `CLMOrderListDetail` 相当のDetail取得を試みるようにした。

- 各注文ごとにDetail取得を試行
- 1件失敗しても他注文のDetail取得を継続
- raw order idは保存せず、diagnosisにはhashのみ保存
- Detail取得のattempt / failureはsafe diagnosisとして記録

### 4. Orders fallback分類

Broker Executions APIまたはOrder Detail由来のExecutionが得られない場合でも、Broker Ordersに以下が揃っていればfallback executionを生成する。

```text
status = 全部約定
executed_quantity > 0
remaining_quantity = 0
```

ただし、これはBroker Executions API由来ではないため、正常PASSとして隠さない。

分類:

```text
ORDER_STATUS_FILLED_FALLBACK_REVIEW
```

fallback executionには以下を明示する。

```json
{
  "source": "broker_orders_fallback",
  "classification": "ORDER_STATUS_FILLED_FALLBACK_REVIEW",
  "review_required": true,
  "raw_broker_order_id_saved": false
}
```

### 5. Positions API safe key diagnosis

Positions APIが空またはゼロ行になった場合に、raw responseを保存せず、key候補の存在状況だけを保存する診断を追加した。

例:

```json
{
  "positions_source_count": 2,
  "positions_valid_count": 0,
  "candidate_key_presence": {
    "issue_code_keys_present": ["issue_code", "code"],
    "quantity_keys_present": ["quantity"]
  },
  "all_rows_empty_or_zero": true,
  "raw_response_saved": false,
  "secret_saved": false
}
```

### 6. Reconcile / Reportへの影響

Reconcileは、Broker Orders fallbackが使われた場合に `REVIEW_REQUIRED` を維持する。

追加した主なフラグ:

```text
broker_orders_used_as_execution_fallback
order_status_filled_fallback_review
fallback_execution_count
broker_executions_classification
positions_safe_diagnosis
```

Daily Report modelにも同情報を渡すようにし、Report/Auditで以下の状態を区別できるようにした。

- Broker Orders上は全部約定
- Broker Executions API由来の約定は未確認または失敗
- Broker Positionsは未反映または0件
- 判定は `REVIEW_REQUIRED`

## 変更ファイル

- `src/ai_fund_lab_v2/broker/normalizer.py`
- `src/ai_fund_lab_v2/broker/sync.py`
- `src/ai_fund_lab_v2/broker/tachibana_broker_snapshot.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/broker/test_broker_normalizer.py`
- `tests/broker/test_tachibana_phase10c_session_foundation.py`
- `tests/phase12/test_phase12_5_production_equivalent_guards.py`

## 実施テスト

```text
python3 -m pytest tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py::test_order_normalizers_hash_order_number_and_keep_sanitized_fields tests/broker/test_tachibana_phase10c_session_foundation.py::test_tachibana_broker_snapshot_attempts_order_detail_for_all_orders_and_continues_after_failure tests/phase12/test_phase12_5_production_equivalent_guards.py::test_broker_orders_filled_fallback_writes_review_executions_and_safe_positions_diagnosis tests/phase12/test_phase12_5_production_equivalent_guards.py::test_reconcile_keeps_orders_fallback_review_required
```

結果: 12 passed

```text
python3 -m pytest tests/broker/test_retry_policy.py tests/broker/test_tachibana_phase10c_session_foundation.py tests/phase12/test_phase12_5_production_equivalent_guards.py
```

結果: 99 passed

```text
python3 -m pytest tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py tests/broker/test_retry_policy.py tests/phase12/test_phase12_5_production_equivalent_guards.py tests/safety/test_broker_state_adapter.py
```

結果: 109 passed

## 禁止事項の遵守

今回は以下を実施していない。

- Submit実行なし
- Broker注文なし
- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし
- secret出力なし
- raw request / raw response保存なし
- raw broker order id保存なし
- AI再学習なし
- フルバックテストなし

## 残課題

- Broker Positions APIが0件になる根本原因は、次回実Broker ReadOnly取得時のsafe key diagnosisで追加確認が必要。
- Broker Executions APIまたはOrder Detailが安定して取得できるまでは、Broker Orders fallbackは `REVIEW_REQUIRED` のまま扱う。
- Report本文でfallback reviewをどの文言で見せるかは、次回の実artifact確認後に必要なら微調整する。
