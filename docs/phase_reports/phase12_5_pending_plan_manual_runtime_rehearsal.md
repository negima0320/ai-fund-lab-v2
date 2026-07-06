# Phase12.5 Pending Plan Manual Runtime Rehearsal

## Summary

判定: REVIEW_REQUIRED

Phase A/B/Cで実装した `pending_order_plan` runtime flowを手動リハーサルした。

結果として、Demo Broker ReadOnlyは `FAILED_LOGIN_SESSION`、Daily PlanはMarket/Feature manifest不足により `BLOCK` となり、`pending_order_plan` は生成されなかった。したがってSubmit前条件を満たさず、Demo Submitは実行していない。

## Commands Executed

実行したコマンド:

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_preflight.py --root .runtime/operations --refresh-broker-readonly
TACHIBANA_API_ENV=demo python3 scripts/run_daily_plan.py --root .runtime/operations
TACHIBANA_API_ENV=demo python3 scripts/run_approval_prepare.py --root .runtime/operations --auto-demo-approval --approver-label manual_pending_rehearsal
TACHIBANA_API_ENV=demo python3 scripts/run_fill_monitor.py --root .runtime/operations
TACHIBANA_API_ENV=demo python3 scripts/run_reconcile.py --root .runtime/operations
TACHIBANA_API_ENV=demo python3 scripts/run_reconcile.py --root .runtime/operations
```

補足:

- Fill / Reconcileを最初に並列確認したため、Reconcileが先に走り `fill_events` をmissing扱いした可能性があった。
- そのためFill生成後にReconcileだけ再実行した。

実行しなかったコマンド:

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_submit_operation.py --root .runtime/operations --execute-demo-order --second-password-present
```

理由: pendingが存在せず、Submit前条件を満たさなかったため。

## Step 1. Broker ReadOnly / Preflight

Command:

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_preflight.py --root .runtime/operations --refresh-broker-readonly
```

Result:

- preflight: `REVIEW_REQUIRED`
- artifact: `.runtime/operations/preflight/2026-07-06/preflight_result.json`
- broker readonly report: `.runtime/operations/broker_readonly_reports/2026-07-06/broker_readonly_snapshot_report.json`
- broker readonly status: `FAILED_LOGIN_SESSION`
- retry attempts: `3`
- `raw_response_saved=false`
- `secret_saved=false`

Not generated:

- `.runtime/operations/broker_snapshot/2026-07-06/broker_snapshot.json`
- `.runtime/operations/broker_orders/2026-07-06/orders.json`
- `.runtime/operations/broker_executions/2026-07-06/executions.json`
- `.runtime/operations/broker_positions/2026-07-06/positions.json`
- `.runtime/operations/broker_readonly_reports/2026-07-06/positions_safe_diagnosis.json`

Conclusion:

Demo read-only API did not complete due login/session failure. Safe diagnosis for positions was not generated because snapshot fetch did not reach positions response handling.

## Step 2. Daily Plan

Command:

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_daily_plan.py --root .runtime/operations
```

Result:

- status: `BLOCK`
- order_plan: `.runtime/operations/order_plan/2026-07-06/order_plan.json`
- daily_plan_result: `.runtime/operations/daily_plan/2026-07-06/daily_plan_result.json`
- buy_item_count: `0`
- sell_item_count: `0`
- order_plan_generation_executed: `false`

Block reasons:

- `market_refresh_manifest_missing`
- `feature_refresh_manifest_missing`
- `ai_feature_contamination_audit_block`
- feature buy adapter: `NO_FEATURE_MARKER`

Pending promotion:

```text
promoted=false
status=SKIPPED
blocked_reason=order_plan_status_block
intended_submit_date=2026-07-07
target_session_date=2026-07-07
```

Pending artifact:

- `.runtime/operations/pending_order_plan/pending_order_plan.json`: not generated

Conclusion:

Daily Planは日付別履歴を生成したが、status `BLOCK` のためpendingへ昇格しなかった。これはPhase A/Cのguard仕様どおり。

## Step 3. Approval

Command:

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_approval_prepare.py --root .runtime/operations --auto-demo-approval --approver-label manual_pending_rehearsal
```

Result:

- command status: `PASS`
- approval artifact: `.runtime/operations/approval_artifact/2026-07-06/approval_artifact.json`
- approval status: `APPROVED`
- approved_item_ids: `0`
- approval_max_notional: `850000`
- approval_max_notional_source: `dynamic_max_exposure`
- demo_order_allowed: `true`
- production_order_allowed: `false`

Pending linkage:

- pending artifact was missing
- no pending state update occurred
- pending did not become `APPROVED`

Conclusion:

日付別approvalは履歴として生成されたが、pendingが存在しないためSubmit SoT候補にはならなかった。

## Step 4. Submit Precheck

Checked:

- `.runtime/operations/pending_order_plan/pending_order_plan.json`

Result:

- pending artifact: missing
- `state=APPROVED`: not satisfied
- `intended_submit_date == submit_run_date`: not checkable
- `target_session_date == submit_run_date`: not checkable
- `allow_dated_order_plan_fallback=false`: not checkable

Decision:

Demo Submit was skipped.

Reason:

Phase C requires Submit source to be `pending_order_plan` only. Dated `order_plan/2026-07-06` and `approval_artifact/2026-07-06` must not be used as fallback.

## Step 5. Demo Submit

Submit command was not executed.

Expected guard if run:

- `pending_order_plan_missing`
- `dated_order_plan_fallback_used=false`
- Broker order API must not be called

Actual:

- No submitted_orders artifact was generated for `2026-07-06`
- `.runtime/operations/submitted_orders/2026-07-06/submitted_orders.json`: missing
- demo order API: not executed
- production order: not executed

## Step 6. Fill / Reconcile

Commands:

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_fill_monitor.py --root .runtime/operations
TACHIBANA_API_ENV=demo python3 scripts/run_reconcile.py --root .runtime/operations
```

Fill result:

- artifact: `.runtime/operations/fill_events/2026-07-06/fill_events.json`
- status: `PASS`
- classification: `SKIPPED_NO_ORDERS`
- broker_orders_count: `0`
- broker_executions_count: `0`
- fill_events: `0`
- production_order_submitted: `false`

Reconcile result after rerun:

- artifact: `.runtime/operations/reconciliation_result/2026-07-06/reconciliation_result.json`
- status: `REVIEW_REQUIRED`
- classification: `REVIEW_REQUIRED`
- missing:
  - `market_refresh`
  - `feature_refresh`
  - `submitted_orders`
  - `broker_snapshot`
  - `broker_orders`
  - `executions`
  - `positions`
  - `buying_power`
  - `ledger`
  - `ledger_state`
  - `ledger_update_manifest`
  - `safety_monitor`
- production_order_submitted: `false`

## Generated Artifacts

Generated / updated:

- `.runtime/operations/preflight/2026-07-06/preflight_result.json`
- `.runtime/operations/broker_readonly_reports/2026-07-06/broker_readonly_snapshot_report.json`
- `.runtime/operations/order_plan/2026-07-06/order_plan.json`
- `.runtime/operations/daily_plan/2026-07-06/daily_plan_result.json`
- `.runtime/operations/approval_request/2026-07-06/approval_request.json`
- `.runtime/operations/approval_artifact/2026-07-06/approval_artifact.json`
- `.runtime/operations/fill_events/2026-07-06/fill_events.json`
- `.runtime/operations/reconciliation_result/2026-07-06/reconciliation_result.json`

Not generated:

- `.runtime/operations/pending_order_plan/pending_order_plan.json`
- `.runtime/operations/submitted_orders/2026-07-06/submitted_orders.json`
- `.runtime/operations/broker_snapshot/2026-07-06/broker_snapshot.json`
- `.runtime/operations/broker_orders/2026-07-06/orders.json`
- `.runtime/operations/broker_executions/2026-07-06/executions.json`
- `.runtime/operations/broker_positions/2026-07-06/positions.json`
- `.runtime/operations/broker_readonly_reports/2026-07-06/positions_safe_diagnosis.json`

## Pending Flow Result

Pending flow did not reach approved submit-ready state.

Reason chain:

```text
Broker ReadOnly: FAILED_LOGIN_SESSION
Daily Plan: BLOCK
Pending promotion: SKIPPED / order_plan_status_block
Approval: dated approval generated, approved_item_ids=0
Pending linkage: no pending artifact
Submit precheck: pending missing
Submit: skipped
```

## Demo API Execution Result

- Demo Broker read-only API attempted.
- Result: `FAILED_LOGIN_SESSION` after 3 retry attempts.
- Demo order API not executed because pending Submit conditions were not satisfied.

## Production Disabled Confirmation

Confirmed:

- `TACHIBANA_API_ENV=demo` used for all executed commands
- `production_order_submitted=false` in Fill / Reconcile outputs
- No Production connection command was run
- No Production order was submitted

## Prohibited Actions

今回は以下を実施していない。

- Production接続なし
- Production注文なし
- artifact削除なし
- notification送信なし
- AI再学習なし
- フルバックテストなし
- Demo Submitなし
- Broker注文なし

## Remaining Issues

1. Broker ReadOnly login/session failure must be resolved or retried successfully before full rehearsal.
2. Market Refresh / Feature Refresh for `2026-07-06` were missing, causing Daily Plan `BLOCK`.
3. Pending generation was not exercised in this runtime rehearsal because Daily Plan did not PASS.
4. Approval generated `APPROVED` with `approved_item_ids=0`; this is not submit-ready and should remain non-submittable without pending.
5. A complete Phase C rehearsal requires:
   - Market Refresh PASS
   - Feature Refresh PASS
   - Daily Plan PASS
   - pending promotion
   - Approval linkage to pending `APPROVED`
   - Submit precheck PASS

## Conclusion

判定: REVIEW_REQUIRED

The pending Plan runtime path failed safely. It did not fall back to dated `order_plan` / `approval_artifact`, and Demo Submit was not run because pending was missing. This confirms the fail-closed direction of Phase C, but full submit-ready pending flow remains unverified until Broker ReadOnly and Daily Plan prerequisites pass.
