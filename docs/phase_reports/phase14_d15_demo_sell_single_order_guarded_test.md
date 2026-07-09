# Phase14-D15 Demo SELL Single-Order Guarded Test

作成日: 2026-07-07

## Status

```text
PHASE14D15_DEMO_SELL_SINGLE_ORDER_PASS
```

## Summary

- runtime_v2_pure_submit_path: `True`
- legacy_order_command_submit_authority_used: `False`
- legacy_runtime_mode_submit_authority_used: `False`
- environment: `demo`
- base_url_is_demo: `True`
- base_url_is_production: `False`
- symbol: `7203`
- side: `SELL`
- quantity: `100.0`
- account_type: `cash`
- demo_submit_executed: `True`
- sell_submit_executed: `True`
- demo_order_accepted: `True`
- broker_api_called: `True`
- post_send_unknown: `False`
- submit_status: `ACCEPTED`
- sell_fill_classification: `ORDER_LIST_POSITION_CASH_DERIVED_FULL_SELL`

## Guard Evidence

- before_position_quantity: `100.0`
- before_available_quantity: `100.0`
- submit_preflight_status: `PASS`
- adapter_preflight_status: `DRY_RUN_READY`
- readonly_before_status: `FAILED_BROKER_READONLY_FETCH`
- readonly_before_health_ok: `True`
- readonly_after_status: `FAILED_BROKER_READONLY_FETCH`
- readonly_after_health_ok: `True`

## Broker Reflection

- order_status_readonly_confirmed: `True`
- target_order_status: `filled`
- target_order_filled_quantity: `100.0`
- target_order_remaining_quantity: `0.0`
- after_position_quantity: `0.0`
- position_decreased_or_disappeared: `True`
- cash_before: `19989824.0`
- cash_after: `19999648.0`
- buying_power_before: `19989824.0`
- buying_power_after: `19999648.0`
- cash_or_buying_power_updated: `True`
- orderlist_position_cash_evidence_used: `True`
- asset_built_from_broker_order_only: `False`

## Runtime v2 Outputs

- pending_plan_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d15/pending_order_plan/pending_order_plan.json`
- approval_artifact_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d15/approval_artifact/approval_phase14d15_demo_sell.json`
- broker_response_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d15/submit_response/runtime_v2_submit_result.json`
- readonly_before_snapshot_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d15/broker_readonly_before/tachibana_demo_snapshot.json`
- readonly_after_snapshot_path: `/Users/negishi/work/ai-fund-lab-v2/.runtime/phase14d15/broker_readonly_after/tachibana_demo_snapshot.json`
- ledger_order_count: `3`
- ledger_execution_count: `0`
- ledger_event_count: `1`
- ledger_position_count: `7`
- ledger_cash_count: `1`
- asset_state_created: `True`
- reconcile_pass: `True`
- reconciliation_findings: `0`
- report_sections: `10`
- notification_payload_created: `True`
- notification_sent: `False`
- audit_pass: `True`
- audit_findings: `0`

## Prohibited Actions

- buy_submit_executed: `False`
- production_order_executed: `False`
- production_broker_api_write_executed: `False`
- notification_sent: `False`
- launchd_or_plist_modified: `False`

## Blocked Reasons

```text
none
```

## Review Reasons

```text
none
```

## Final Decision

```text
PHASE14D15_DEMO_SELL_SINGLE_ORDER_PASS
```
