# Phase12.5 Report / Notification Submit vs Plan SoT Fix

作成日: 2026-07-04

## 目的

2026-07-03のReport / Notificationで、「本日Submit結果」として7/3夜に作られた次回用Order Plan 2件を表示していた。

本来の7/3朝Submit実績は `submitted_orders/2026-07-03/submitted_orders.json` の5件であるため、Report / NotificationのSource of Truthを分離した。

## 修正内容

### 本日Submit結果

本日Submit結果は `submitted_orders/YYYY-MM-DD/submitted_orders.json` をSoTにした。

- `STALE_IGNORED` でも `submitted_orders` が存在する場合は本日実績として表示する
- `order_plan` を本日Submit結果として表示しない
- submitted rowが表示に必要なcode/quantity等を持たない場合のみ、同じ `item_id` のorder_plan itemで表示補完する
- SoT自体はsubmitted_ordersのまま維持する

### 本日約定 / 注文確認

本日約定・注文確認は既存どおり以下をSoTにする。

- `broker_orders/YYYY-MM-DD/orders.json`
- `fill_events/YYYY-MM-DD/fill_events.json`
- `reconciliation_result/YYYY-MM-DD/reconciliation_result.json`

Broker Orders fallbackやBroker Executions未確認の場合は、Report Guard側の `REVIEW_REQUIRED` を維持する。

### 次回注文候補

次回注文候補は `order_plan/YYYY-MM-DD/order_plan.json` として別セクションに分離した。

非通常運用Reportでは以下のように明示する。

```text
次回用Order Planの候補はN件です。これは本日Submit結果ではありません。
```

### Notification

Discord / LINE payloadにも同じSoTを追加した。

- `submitted_orders`
- `submitted_order_count`
- `submitted_orders_source`
- `next_order_candidates`
- `next_order_plan_count`
- `next_order_plan_source`

非通常運用Notification summaryにも、submitted_orders基準の本日Submit件数とorder_plan基準の次回候補件数を分けて表示する。

### daily_report_refs

`daily_report_refs.json` にSoT policyを明示した。

```json
{
  "submitted_orders_source_of_truth": "submitted_orders",
  "next_order_plan_source_of_truth": "order_plan",
  "report_sot_policy": {
    "today_submit_result": "submitted_orders/YYYY-MM-DD/submitted_orders.json",
    "today_order_confirmation": "broker_orders / fill_events / reconciliation_result",
    "next_order_candidates": "order_plan/YYYY-MM-DD/order_plan.json",
    "order_plan_used_as_today_submit_result": false,
    "stale_ignored_submit_with_artifact_is_displayed_as_today_result": true
  }
}
```

## 変更ファイル

- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/phase12/test_daily_report_prerequisite_guard.py`
- `docs/phase_reports/phase12_5_report_submit_plan_sot_fix.md`
- `reports/phase_reports/phase12_5_report_submit_plan_sot_fix.json`

## テスト

```text
python3 -m pytest tests/phase12/test_daily_report_prerequisite_guard.py tests/phase12/test_daily_report_writer_quality.py tests/phase12/test_operations_phase12l_report_and_candidate_audit.py tests/phase12/test_operations_notifications.py
```

結果: 10 passed

追加テストでは、以下を確認した。

- submitted_orders 5件とorder_plan 2件が同じ日付に存在しても、本日Submit結果は5件表示になる
- 次回Order Plan候補2件は別セクションになる
- LINE / Discord payloadも submitted_order_count=5 / next_order_plan_count=2 を分離して持つ
- `daily_report_refs.json` にSoT policyが出る

## 禁止事項の遵守

今回は以下を実施していない。

- Submit実行なし
- Broker注文なし
- Production接続なし
- artifact削除なし
- notification送信なし

## 残課題

- 既存の2026-07-03 runtime report artifactは今回の実装中には再生成していない。必要な場合は通知送信なしでReport系artifactのみ再生成する。
- Broker Executions API未確認 / Broker Orders fallback reviewの表示文言は、次回Report実体確認で必要なら追加調整する。
