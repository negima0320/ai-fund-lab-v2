# Phase12.5 Report / Notification Submit SoT Fix

## Summary

2026-07-03 の Report / Notification payload で、「本日Submit結果」と「次回注文候補」を明確に分離した。

- 本日Submit結果の Source of Truth: `submitted_orders/YYYY-MM-DD/submitted_orders.json`
- 次回注文候補の Source of Truth: `order_plan/YYYY-MM-DD/order_plan.json`
- `order_plan` を本日Submit結果として扱わない
- `REVIEW_REQUIRED_REPORT` でも `submitted_orders` が存在する場合は本日Submit実績を表示する
- Broker Executions / Positions が未確定であることを Report 上に明示する

## Fixed Behavior

2026-07-03 の再生成後 artifact では以下を確認した。

### 本日Submit結果

SoT: `.runtime/operations/submitted_orders/2026-07-03/submitted_orders.json`

表示件数: 5件

- `6522`
- `7878`
- `6166`
- `4265`
- `6897`

### 次回注文候補

SoT: `.runtime/operations/order_plan/2026-07-03/order_plan.json`

表示件数: 2件

- `6522`
- `6166`

### Broker確認

Report本文に以下を明示するようにした。

- Broker Orders件数
- Broker Executions件数
- Broker Positions件数
- Broker Orders上は注文確認があるが、Broker Executions API由来の確定約定は未確認であること
- Broker Positionsが0件または未反映の場合、現在保有を確定扱いにしないこと

## Changed Files

- `src/ai_fund_lab_v2/operations/operations.py`
  - `REVIEW_REQUIRED_REPORT` の非通常運用レポートに `## Broker確認` セクションを追加
- `tests/phase12/test_daily_report_prerequisite_guard.py`
  - `submitted_orders` 5件と `order_plan` 2件の分離
  - Broker Executions / Positions 未確定表示
  - LINE / Discord payload の件数整合

## Regenerated Artifacts

通知送信なしで `run_daily_report(..., send_notifications=False)` を実行し、2026-07-03 のReport系artifactのみ再生成した。

- `.runtime/operations/reports/2026-07-03/public_report.md`
- `.runtime/operations/reports/2026-07-03/blog_draft.md`
- `.runtime/operations/reports/2026-07-03/safety_report.md`
- `.runtime/operations/reports/2026-07-03/line_payload.json`
- `.runtime/operations/reports/2026-07-03/discord_payload.json`
- `.runtime/operations/daily_report_refs/2026-07-03/daily_report_refs.json`

## Verification

実施テスト:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/phase12/test_daily_report_prerequisite_guard.py::test_review_report_separates_today_submitted_orders_from_next_order_plan \
  tests/phase12/test_daily_report_writer_quality.py \
  -q
```

結果:

```text
4 passed
```

追加確認:

- `daily_report_refs.submitted_order_count = 5`
- `daily_report_refs.next_order_plan_count = 2`
- `daily_report_refs.report_sot_policy.order_plan_used_as_today_submit_result = false`
- `line_payload.json.submitted_order_count = 5`
- `line_payload.json.next_order_plan_count = 2`
- `discord_payload.json.submitted_order_count = 5`
- `discord_payload.json.next_order_plan_count = 2`
- LINE / Discord payload の `submitted_orders` は `6522, 7878, 6166, 4265, 6897`
- LINE / Discord payload の `next_order_candidates` は `6522, 6166`
- `notification_status = NOT_REQUESTED`
- `send_executed = false`

## Prohibited Actions

今回は以下を実施していない。

- Submit実行なし
- Broker注文なし
- Production接続なし
- notification送信なし
- artifact削除なし
- secret / raw request / raw response 保存なし

## Result

判定: PASS

7/3 Report / Notification payload は、本日Submit実績と次回Order Plan候補を混同しない状態になった。
