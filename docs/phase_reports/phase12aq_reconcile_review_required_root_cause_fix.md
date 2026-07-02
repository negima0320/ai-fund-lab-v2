# Phase12-AQ Reconcile REVIEW_REQUIRED Root Cause Fix

## 目的

Phase12-AP後に残った `Reconcile=REVIEW_REQUIRED` の原因を調査し、2026-07-02のDemo Submit結果をDemo仕様として説明可能な正常系へ整理した。

追加Demo注文、Production注文、LINE/Discord実送信、AI再学習、Backtestは実施していない。

## REVIEW_REQUIRED の原因

原因は2つあった。

1. Reconcileが朝Submit日のSource of Truthを誤って見ていた。

2026-07-02朝のSubmitは、仕様通り `submit_run_date=2026-07-02` で、前営業日の `order_plan_source_date=2026-07-01` / `approval_source_date=2026-07-01` を参照していた。

しかしReconcileは、2026-07-02当日の `daily_plan/order_plan/approval` を必須artifactとして見ていたため、`daily_plan`, `order_plan`, `approval`, `daily_report` をmissing扱いにして `REVIEW_REQUIRED` へ落としていた。

2. Daily Manifest / Report Guardが想定内のDemo差分をBLOCK扱いしていた。

`demo_special_fill_simulation_status=BLOCK` は、対象9256の待機注文がないことによるSimulation対象外だった。これは今回の4件Broker accepted + 1件item blockのReconcileを止める理由ではない。

## 修正内容

### Reconcile source date解決

`run_reconcile` が `submitted_orders` の以下を読むようにした。

- `submit_run_date`
- `order_plan_source_date`
- `approval_source_date`

朝Submit日は、当日ではなくsource date側の `daily_plan/order_plan/approval` を照合する。

### Submit reconciliation summary追加

Reconcile artifactに `submit_reconciliation` を追加した。

記録内容:

- submitted_order_count
- accepted_order_count
- blocked_item_count
- explained_blocked_item_count
- broker_order_count
- broker_executions_count
- broker_positions_count
- broker_orders_cover_accepted
- broker_orders_used_as_execution_fallback
- demo_empty_executions_positions_explained
- partial_submit_with_explained_blocked_items

### PASS_WITH_BLOCKED_ITEMS

以下を満たす場合は `REVIEW_REQUIRED` ではなく `PASS_WITH_BLOCKED_ITEMS` とする。

- Broker acceptedがBroker Ordersで確認できる
- item blockがすべて理由付きで説明済み
- Broker executionsが空でもbroker_ordersの `executed_quantity/status` で補完可能
- Demo仕様としてBroker positionsが0でも説明可能
- missing required artifactがない
- SafetyがSYSTEM_EMERGENCY_STOPではない

### Daily Report / Manifest

Daily Report writer / Manifestもsource-awareにし、2026-07-02を正常運用日として扱えるようにした。

また、Demo Special Fill Simulationが対象外でBLOCKになっていても、Daily Manifest全体をBLOCKにしないようにした。

## 2026-07-02 再評価結果

Reconcile:

- status: `PASS_WITH_BLOCKED_ITEMS`
- classification: `PASS_WITH_BLOCKED_ITEMS`
- missing: `[]`
- accepted_order_count: 4
- blocked_item_count: 1
- broker_order_count: 4
- broker_executions_count: 0
- broker_positions_count: 0
- broker_orders_used_as_execution_fallback: true
- demo_empty_executions_positions_explained: true

Audit:

- status: `PASS`

Daily Report:

- status: `PASS`
- operation_day_type: `NORMAL_OPERATION_DAY`
- report_mode: `NORMAL_BLOG`

Daily Manifest:

- status: `PASS`
- reconciliation_status: `PASS_WITH_BLOCKED_ITEMS`
- submit_status: `PARTIAL_PASS_WITH_ITEM_BLOCKS`

## テスト

実施:

- `python3 -m pytest tests/phase12 -q`: PASS（91 passed）
- `python3 -m pytest tests/phase12/test_operations_fill_monitor_states.py tests/phase12/test_operations_reconcile_extended.py tests/phase12/test_phase12_reconcile.py -q`: PASS
- `python3 -m py_compile` 対象Operations / CLI: PASS

追加確認:

- 前営業日Order Planを使う朝Submitで、accepted + explained blocked itemなら `PASS_WITH_BLOCKED_ITEMS` になる。
- Broker executions / positionsが空でも、Demo仕様として説明可能なら `SYSTEM_EMERGENCY_STOP` にしない。
- Daily ManifestでDemo Special Fill対象外を全体BLOCKにしない。

## 禁止事項確認

- Demo追加注文: 未実施
- Production注文: 未実施
- LINE/Discord実送信: 未実施
- AI再学習: 未実施
- Backtest: 未実施
- raw request / raw response保存: 未実施
- secret保存: 未実施
