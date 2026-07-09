# Phase14-D8 Pure Runtime v2 Demo BUY Single-Order Re-test After External Cancel Sync

作成日: 2026-07-07

## Status

```text
PHASE14D8_REVIEW_REQUIRED
```

## Summary

- d7_sync_pass: `True`
- existing_9432_cancelled: `True`
- runtime_v2_pure_submit_path: `True`
- legacy_order_command_submit_authority_used: `False`
- legacy_runtime_mode_submit_authority_used: `False`
- environment: `demo`
- base_url_is_demo: `True`
- base_url_is_production: `False`
- symbol: `7203`
- side: `BUY`
- quantity: `100.0`
- demo_submit_executed: `True`
- demo_order_accepted: `True`
- broker_api_called: `True`
- post_send_unknown: `False`
- submit_status: `ACCEPTED`
- execution_state_classification: `FILLED_BY_ORDER_STATUS_EXECUTION_DETAIL_REVIEW`
- fill_classifications: `REVIEW_REQUIRED, ORDER_CANCELLED`

## Broker ReadOnly Diagnosis

- order list: `PASS`
- 7203 order status: `全部約定`
- 7203 executed_quantity: `100`
- 7203 remaining_quantity: `0`
- executions detail: `FAIL / FAILED_BROKER_READONLY_FETCH`
- decision: Demo Submit and order status sync succeeded, but execution detail evidence is unavailable, so integrated reflection is `REVIEW_REQUIRED`.

## Evidence

- pending_plan_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d8/pending_order_plan/pending_order_plan.json`
- approval_artifact_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d8/approval_artifact/approval_phase14d8_demo_buy.json`
- broker_response_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d8/submit_response/runtime_v2_submit_result.json`
- readonly_before_snapshot_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d8/broker_readonly_before/tachibana_demo_snapshot.json`
- readonly_after_snapshot_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d8/broker_readonly_after/tachibana_demo_snapshot.json`
- readonly_before_status: `FAILED_BROKER_READONLY_FETCH`
- readonly_after_status: `FAILED_BROKER_READONLY_FETCH`
- submit_preflight_status: `PASS`
- adapter_preflight_status: `DRY_RUN_READY`
- order_status_readonly_confirmed: `True`

## Runtime v2 Reflection

- ledger_order_count: `2`
- ledger_execution_count: `0`
- ledger_position_count: `8`
- ledger_cash_count: `1`
- asset_state_created: `True`
- reconciliation_findings: `0`
- report_sections: `10`
- notification_payload_created: `True`
- audit_findings: `0`

## Prohibited Actions

- production_order_executed: `False`
- production_broker_api_write_executed: `False`
- sell_submit_executed: `False`
- notification_sent: `False`
- launchd_or_plist_modified: `False`

## Blocked Reasons

```text
none
```

## Review Reasons

```text
order status indicates fill but execution detail evidence is unavailable
fill classification requires review
```
