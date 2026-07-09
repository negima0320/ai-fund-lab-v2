# Phase14-D5 Pure Runtime v2 Demo BUY Single-Order Re-test

作成日: 2026-07-07

## Status

```text
PHASE14D5_REVIEW_REQUIRED
```

## Summary

- runtime_v2_pure_submit_path: `True`
- legacy_order_command_submit_authority_used: `False`
- legacy_runtime_mode_submit_authority_used: `False`
- environment: `demo`
- base_url_is_demo: `True`
- base_url_is_production: `False`
- symbol: `7203`
- side: `BUY`
- quantity: `100.0`
- demo_submit_executed: `False`
- demo_order_accepted: `False`
- broker_api_called: `False`
- post_send_unknown: `False`
- submit_status: `NOT_EXECUTED`
- execution_state_classification: `UNFILLED_OR_NOT_CONFIRMED`

## Evidence

- pending_plan_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d5/pending_order_plan/pending_order_plan.json`
- approval_artifact_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d5/approval_artifact/approval_phase14d5_demo_buy.json`
- broker_response_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d5/submit_response/runtime_v2_submit_result.json`
- readonly_before_snapshot_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d5/broker_readonly_before/tachibana_demo_snapshot.json`
- readonly_after_snapshot_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d5/broker_readonly_after/tachibana_demo_snapshot.json`
- readonly_before_status: `FAILED_BROKER_READONLY_FETCH`
- readonly_after_status: `NOT_EXECUTED`
- submit_preflight_status: `PASS`
- adapter_preflight_status: `NOT_EXECUTED`
- order_status_readonly_confirmed: `True`

## Runtime v2 Reflection

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
- sell_submit_executed: `False`
- notification_sent: `False`
- launchd_or_plist_modified: `False`

## Blocked Reasons

```text
readonly before status=FAILED_BROKER_READONLY_FETCH
```

## ReadOnly Before Diagnosis

- account: `PASS`
- orders: `PASS`
- positions: `PASS`
- quotes: `PASS_WITH_EMPTY_RESULT`
- executions: `FAIL`
- execution_detail_failure_stage: `order_detail_response`
- execution_detail_failure_classification: `FAILED_BROKER_READONLY_FETCH`
- existing_order_detected: `9432 BUY 100 remaining_quantity=100 status=未約定`
- D5 submit decision: `blocked before submit`

## Review Reasons

```text
none
```
