# Phase14-D Demo BUY Single-Order Guarded Test

## Status

```text
PHASE14D_REVIEW_REQUIRED
```

## Summary

- environment: `demo`
- base_url_is_demo: `True`
- base_url_is_production: `False`
- BUY order: `9432 / 100 shares / MARKET / 1 order only`
- demo_submit_executed: `True`
- demo_order_accepted: `True`
- submit_status: `ACCEPTED`
- submit_classification: `ACCEPTED`
- post_send_unknown: `False`
- readonly_before_status: `PASS_WITH_WARNINGS`
- readonly_after_status: `FAILED_BROKER_READONLY_FETCH`
- broker_readonly_order_status_confirmed: `True`
- final handling: `accepted demo submit, then REVIEW_REQUIRED because after-submit execution detail fetch failed`

## Runtime v2 Evidence

- pending_plan_path: `.runtime/phase14d/pending_order_plan/pending_order_plan.json`
- approval_artifact_path: `.runtime/phase14d/approval_artifact/approval_phase14d_demo_buy.json`
- ledger_order_count: `1`
- ledger_execution_count: `0`
- ledger_position_count: `7`
- ledger_cash_count: `1`
- asset_state_created: `True`
- reconciliation_findings: `0`
- report_sections: `10`
- notification_payload_created: `True`
- audit_findings: `0`

## Prohibited Actions

- production_order_executed: `False`
- production_broker_api_write_executed: `False`
- real_money_operation_executed: `False`
- sell_order_executed: `False`
- multiple_orders_executed: `False`
- notification_send_executed: `False`
- launchd_or_plist_modified: `False`

## Blocked Reasons

```text
none
```

## Review Reasons

```text
readonly sync after submit status=FAILED_BROKER_READONLY_FETCH
execution detail fetch failed; order list confirmed but execution reflection remains pending
```
