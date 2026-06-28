# Phase11-G Safety Integration Dry Run

- status: PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE
- business_date: 2026-06-29
- generated_at: 2026-06-28T03:30:35.361160+00:00
- broker_api_connected: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- auto_sell_executed: false
- auto_recovery_executed: false
- runtime_behavior_changed: false

## Summary

Phase11-B〜Fで作成した Safety Runtime / Hourly Monitor / Report / Emergency Stop / Recovery / Manual Unlock を、mockデータだけで統合dry-runした。

このdry-runは実運用接続ではなく、Safety subsystemの連携監査成果物である。Broker Snapshot、Safety result、Audit result、Order / Execution result はAI学習に使用しない。

## Scenarios

### normal

- overall_decision: ALLOW
- next_state: NORMAL
- emergency_required: false
- recovery_candidate: false
- review_item_count: 0
- report: reports/safety/phase11/integration_dry_run/2026-06-29_normal.json

### individual_warning

- overall_decision: REVIEW_REQUIRED
- next_state: WARNING
- emergency_required: false
- recovery_candidate: false
- review_item_count: 1
- report: reports/safety/phase11/integration_dry_run/2026-06-29_individual_warning.json

### stop_loss_candidate

- overall_decision: REVIEW_REQUIRED
- next_state: BUY_STOP
- emergency_required: false
- recovery_candidate: false
- review_item_count: 1
- report: reports/safety/phase11/integration_dry_run/2026-06-29_stop_loss_candidate.json

### emergency_candidate

- overall_decision: EMERGENCY_STOP
- next_state: EMERGENCY_STOP
- emergency_required: true
- recovery_candidate: false
- review_item_count: 1
- report: reports/safety/phase11/integration_dry_run/2026-06-29_emergency_candidate.json

### market_crash

- overall_decision: BLOCK
- next_state: BUY_STOP
- emergency_required: false
- recovery_candidate: false
- review_item_count: 1
- report: reports/safety/phase11/integration_dry_run/2026-06-29_market_crash.json

### duplicate_active_order

- overall_decision: EMERGENCY_STOP
- next_state: EMERGENCY_STOP
- emergency_required: true
- recovery_candidate: false
- review_item_count: 2
- report: reports/safety/phase11/integration_dry_run/2026-06-29_duplicate_active_order.json

### stale_quote_snapshot

- overall_decision: BLOCK
- next_state: EMERGENCY_STOP
- emergency_required: true
- recovery_candidate: false
- review_item_count: 2
- report: reports/safety/phase11/integration_dry_run/2026-06-29_stale_quote_snapshot.json

### manual_emergency

- overall_decision: EMERGENCY_STOP
- next_state: EMERGENCY_STOP
- emergency_required: true
- recovery_candidate: false
- review_item_count: 1
- report: reports/safety/phase11/integration_dry_run/2026-06-29_manual_emergency.json

### recovery_candidate

- overall_decision: REVIEW_REQUIRED
- next_state: RECOVERY_CANDIDATE
- emergency_required: false
- recovery_candidate: true
- review_item_count: 1
- report: reports/safety/phase11/integration_dry_run/2026-06-29_recovery_candidate.json

### manual_unlock

- overall_decision: REVIEW_REQUIRED
- next_state: MANUAL_APPROVED
- emergency_required: false
- recovery_candidate: true
- review_item_count: 2
- report: reports/safety/phase11/integration_dry_run/2026-06-29_manual_unlock.json

## Output

- integration_summary: reports/safety/phase11/integration_dry_run/2026-06-29_phase11g_integration_dry_run_summary.json
- phase_json: reports/phase_reports/phase11g_safety_integration_dry_run.json

## Result

```text
PHASE11G_SAFETY_INTEGRATION_DRY_RUN_COMPLETE
PHASE11Z_READY_TO_START
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
