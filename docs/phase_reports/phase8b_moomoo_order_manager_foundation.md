# Phase8-B moomoo Order Manager Foundation

## 1. 目的

Phase8-Bでは、Phase8-A設計に基づき、以下のmock-only foundationを実装した。

```text
OrderPlan / OrderPlanItem schema
moomoo read-only Broker snapshot schema
moomoo mock response fixture
mock response normalizer
.runtime/broker/ snapshot writer
禁止API不在audit
pytest
```

実API接続、OpenD接続、moomoo SDK接続、実発注は未実施である。

## 2. 実装範囲

追加・更新対象:

```text
src/ai_fund_lab_v2/order_manager/
src/ai_fund_lab_v2/broker/moomoo/
src/ai_fund_lab_v2/broker/models.py
src/ai_fund_lab_v2/broker/runtime_paths.py
src/ai_fund_lab_v2/broker/snapshot_writer.py
src/ai_fund_lab_v2/broker/sync_result.py
scripts/audit_phase8b_moomoo_order_manager_foundation.py
tests/order_manager/
tests/broker/
```

## 3. Safety境界

OrderPlanは必ず以下を満たす。

```text
executable = false
live_order_allowed = false
requires_human_review = true
```

moomoo mock normalizerは、以下のread-only method名だけを受け付ける。

```text
get_acc_list
accinfo_query
position_list_query
order_list_query
history_order_list_query
```

## 4. 保存先

mock-only snapshotは以下へ保存される。

```text
.runtime/broker/snapshots/accounts/
.runtime/broker/snapshots/balance/
.runtime/broker/snapshots/positions/
.runtime/broker/snapshots/orders/
.runtime/broker/snapshots/executions/
.runtime/broker/sync_results/
```

## 5. 監査

audit script:

```text
scripts/audit_phase8b_moomoo_order_manager_foundation.py
```

確認内容:

```text
Phase8対象sourceが存在する
moomoo read-only method setが設計通り
Phase8対象sourceにwrite系API tokenがない
Phase8対象sourceにTachibana / CLMID tokenがない
OrderPlanが非実行でhuman review必須
OrderPlanItemが非実行
```

実行結果:

```text
python3 scripts/audit_phase8b_moomoo_order_manager_foundation.py
status = PASS
```

## 6. テスト結果

実行したテスト:

```text
python3 -m pytest tests/broker/test_moomoo_normalizer.py tests/broker/test_moomoo_snapshot_writer.py tests/order_manager/test_order_plan_schema.py tests/broker/test_phase8b_moomoo_audit.py
8 passed

python3 -m pytest tests/broker
50 passed

python3 -m pytest
799 passed, 22 warnings
```

## 7. Phase8-Cへの引き継ぎ

Phase8-Cでは、実API接続なしのまま以下へ進む。

```text
Capital Allocation decision loader
Broker snapshot loader
Paper ledger schema
Broker snapshotとpaper ledgerの分離突合
Order Plan Generator
Human Review report writer
locked時のreview-only診断出力
```

Phase8-Cでも、live order、auto order、OpenD接続、moomoo SDK接続、発注系API実装は禁止する。
