# Phase12.5 Pending Plan Full Manual Runtime Rehearsal

## Summary

判定: REVIEW_REQUIRED

Phase A/B/Cで実装した `pending_order_plan` runtime flowを、手動で最後まで進めるリハーサルとして実行した。

結果:

- Broker ReadOnly: `FAILED_LOGIN_SESSION`
- Market Refresh: `BLOCK`
- Feature Refresh: `BLOCK`
- Daily Plan: `BLOCK`
- pending_order_plan: 未生成
- Approval: 日付別artifactは `APPROVED` だが `approved_item_ids=0`
- Submit: pending条件未充足のため未実行
- Fill Monitor: `PASS / SKIPPED_NO_ORDERS`
- Safety Monitor: `PASS`
- Reconcile: `REVIEW_REQUIRED`

Phase Cの重要要件である「pendingが無い場合に日付別Plan/ApprovalへfallbackしてSubmitしない」ことは今回も確認できた。一方、pending生成からDemo Submitまでのfull flowは、Market/FeatureとBroker ReadOnly前提が満たせず未完了。

## Commands Executed

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_preflight.py --root .runtime/operations --refresh-broker-readonly
TACHIBANA_API_ENV=demo python3 scripts/run_preflight.py --root .runtime/operations --refresh-broker-readonly
TACHIBANA_API_ENV=demo python3 scripts/run_market_refresh.py --root .runtime/operations --allow-api-fetch
TACHIBANA_API_ENV=demo python3 scripts/run_daily_plan.py --root .runtime/operations
TACHIBANA_API_ENV=demo python3 scripts/run_approval_prepare.py --root .runtime/operations --auto-demo-approval --approver-label manual_pending_full_rehearsal
TACHIBANA_API_ENV=demo python3 scripts/run_fill_monitor.py --root .runtime/operations
TACHIBANA_API_ENV=demo python3 scripts/run_safety_monitor.py --root .runtime/operations
TACHIBANA_API_ENV=demo python3 scripts/run_reconcile.py --root .runtime/operations
```

Submit command was not executed:

```bash
TACHIBANA_API_ENV=demo python3 scripts/run_submit_operation.py --root .runtime/operations --execute-demo-order --second-password-present
```

Reason: `pending_order_plan/pending_order_plan.json` was missing, so Phase C Submit guard was not satisfied.

## Step Results

### 1. Broker ReadOnly / Preflight

Result:

- preflight: `REVIEW_REQUIRED`
- broker readonly report: `.runtime/operations/broker_readonly_reports/2026-07-06/broker_readonly_snapshot_report.json`
- broker readonly status: `FAILED_LOGIN_SESSION`
- failure_classification: `login_session_error`
- final_failure_classification: `FAILED_LOGIN_SESSION`
- retry_attempts: `3`
- failure_stage: `login_session`
- safe_error_class: `BrokerTransportError`
- raw_response_saved: `false`
- secret_saved: `false`

Safe diagnosis:

- attempts: 3
- retryable attempts: first 2 attempts retryable, final attempt not retryable
- decrypt_attempted: `false`
- decrypt_success: `false`
- login_result_code_present: `false`

Generated:

- `.runtime/operations/preflight/2026-07-06/preflight_result.json`
- `.runtime/operations/broker_readonly_reports/2026-07-06/broker_readonly_snapshot_report.json`

Not generated:

- `.runtime/operations/broker_snapshot/2026-07-06/broker_snapshot.json`
- `.runtime/operations/broker_orders/2026-07-06/orders.json`
- `.runtime/operations/broker_executions/2026-07-06/executions.json`
- `.runtime/operations/broker_positions/2026-07-06/positions.json`
- `.runtime/operations/broker_readonly_reports/2026-07-06/positions_safe_diagnosis.json`

Classification:

This is not classified as missing configuration in the current artifact. It is a login/session failure surfaced as `FAILED_LOGIN_SESSION` with `BrokerTransportError`.

### 2. Market Refresh

Command completed after a long run and returned `BLOCK`.

Artifacts:

- `.runtime/operations/market_refresh/2026-07-06/market_refresh_manifest.json`
- `.runtime/operations/feature_refresh/2026-07-06/feature_refresh_manifest.json`

Result:

- market_refresh status: `BLOCK`
- feature_refresh status: `BLOCK`
- feature_freshness_status: `MARKET_DATA_NOT_YET_AVAILABLE`
- data_until: `2026-07-06`
- latest_available_market_date: `2026-07-06`
- AI feature contamination audit: `PASS`
- raw_response_saved: `false`
- secret_saved: `false`

Not generated:

- `.runtime/operations/feature_artifacts/2026-07-06/candidate_features.parquet`

Conclusion:

Market/Feature prerequisites did not reach PASS. The blocker is market data freshness/availability, not AI contamination.

### 3. Daily Plan

Result:

- status: `BLOCK`
- artifact: `.runtime/operations/order_plan/2026-07-06/order_plan.json`
- daily result: `.runtime/operations/daily_plan/2026-07-06/daily_plan_result.json`
- buy_item_count: `0`
- sell_item_count: `0`
- order_plan_generation_executed: `false`

Market refresh gate:

- status: `BLOCK`
- reasons:
  - `market_refresh_not_pass`
  - `feature_refresh_not_pass`

Feature adapter:

- status: `NO_FEATURE_ARTIFACT`
- reason: `candidate_feature_path_missing`
- candidate_count: `0`

Pending promotion:

```text
status=SKIPPED
promoted=false
blocked_reason=order_plan_status_block
intended_submit_date=2026-07-07
target_session_date=2026-07-07
```

Pending artifact:

- `.runtime/operations/pending_order_plan/pending_order_plan.json`: not generated

Conclusion:

Daily Plan failed safely and did not promote a BLOCK plan into pending.

### 4. Approval

Result:

- command status: `PASS`
- artifact: `.runtime/operations/approval_artifact/2026-07-06/approval_artifact.json`
- approval status: `APPROVED`
- approved_item_ids: `0`
- approval_max_notional: `850000`
- approval_max_notional_source: `dynamic_max_exposure`
- demo_order_allowed: `true`
- production_order_allowed: `false`

Pending linkage:

- pending artifact was missing
- pending.state did not become `APPROVED`

Conclusion:

日付別approvalは履歴として生成されたが、pending SoT候補は成立していない。

### 5. Submit Precheck

Checked:

- `.runtime/operations/pending_order_plan/pending_order_plan.json`

Result:

- pending artifact exists: `false`
- state=APPROVED: not satisfied
- intended_submit_date / target_session_date: not checkable
- allow_dated_order_plan_fallback=false: not checkable
- approval hash / order_plan hash: not checkable

Decision:

Demo Submit was not executed.

Reason:

Phase C requires pending-only Submit source. Dated `order_plan/2026-07-06` and `approval_artifact/2026-07-06` must not be used as fallback.

### 6. Demo Submit

Not executed.

Expected if run:

- Submit guard would block with `pending_order_plan_missing`
- `dated_order_plan_fallback_used=false`
- Broker order API would not be called

Actual:

- `.runtime/operations/submitted_orders/2026-07-06/submitted_orders.json`: not generated
- demo order API: not executed
- broker_order_api_called: `false`
- production_order_submitted: `false`

### 7. Fill Monitor

Result:

- artifact: `.runtime/operations/fill_events/2026-07-06/fill_events.json`
- status: `PASS`
- classification: `SKIPPED_NO_ORDERS`
- fill_events: `0`
- broker_orders_count: `0`
- broker_executions_count: `0`
- production_order_submitted: `false`

### 8. Safety Monitor

Result:

- artifact: `.runtime/operations/safety_monitor/2026-07-06/safety_monitor_result.json`
- status: `PASS`
- production_order_submitted: `false`

### 9. Reconcile

Result:

- artifact: `.runtime/operations/reconciliation_result/2026-07-06/reconciliation_result.json`
- status: `REVIEW_REQUIRED`
- classification: `REVIEW_REQUIRED`
- production_order_submitted: `false`

Missing:

- `submitted_orders`
- `broker_snapshot`
- `broker_orders`
- `executions`
- `positions`
- `buying_power`
- `ledger`
- `ledger_state`

## Pending Flow Result

The pending flow did not reach submit-ready state.

Reason chain:

```text
Broker ReadOnly: FAILED_LOGIN_SESSION
Market Refresh: BLOCK / MARKET_DATA_NOT_YET_AVAILABLE
Feature Refresh: BLOCK / MARKET_DATA_NOT_YET_AVAILABLE
Daily Plan: BLOCK / candidate_feature_path_missing
Pending promotion: SKIPPED / order_plan_status_block
Approval: dated approval only, approved_item_ids=0
Submit precheck: pending missing
Demo Submit: not executed
```

## Broker Orders / Executions / Positions

Not generated in this rehearsal:

- broker_orders: missing
- broker_executions: missing
- broker_positions: missing

Reason:

Broker ReadOnly failed at login/session stage, and Demo Submit was not executed.

## positions_safe_diagnosis

Not generated:

- `.runtime/operations/broker_readonly_reports/2026-07-06/positions_safe_diagnosis.json`

Reason:

Broker ReadOnly did not reach positions API response handling.

## Production Disabled Confirmation

Confirmed:

- All executed commands used `TACHIBANA_API_ENV=demo`
- No Production connection was executed
- No Production order was submitted
- `production_order_submitted=false` appears in generated runtime artifacts that include it
- notification was not sent
- artifacts were not deleted

## Remaining Issues

1. Broker ReadOnly `FAILED_LOGIN_SESSION`
   - Needs separate diagnosis before full runtime acceptance.
   - Current artifact suggests login/session transport failure, not raw secret/config leakage.

2. Market/Feature Refresh `MARKET_DATA_NOT_YET_AVAILABLE`
   - Full pending rehearsal requires feature artifacts.
   - Current run could not generate candidate features for `2026-07-06`.

3. Pending not generated
   - Correct behavior because Daily Plan was `BLOCK`.
   - Full rehearsal requires Daily Plan `PASS`.

4. Approval with zero approved items
   - Date-based approval artifact can be `APPROVED` with no items when Plan is BLOCK/empty.
   - Since pending is missing, Submit remains blocked.

5. Full Demo Submit path remains unverified in real runtime
   - Unit tests cover Phase C guard and pending read switch.
   - Manual runtime requires successful pending generation and approval linkage.

## Minimum Next Action

Do not weaken pending guards.

Minimum path to complete full rehearsal:

1. Resolve or wait out Broker ReadOnly login/session failure.
2. Run Market Refresh after market data is available, or identify the expected availability timing.
3. Confirm `feature_artifacts/YYYY-MM-DD/candidate_features.parquet` generation.
4. Re-run Daily Plan and verify `status=PASS`.
5. Verify pending promotion and Approval linkage.
6. Only then run Demo Submit.

## Conclusion

判定: REVIEW_REQUIRED

The rehearsal progressed as far as the runtime guards safely allowed. Phase C fail-closed behavior is confirmed again: no pending means no dated-artifact fallback and no Demo Submit. The full pending-to-Demo-Submit path remains blocked by Broker ReadOnly login/session failure and Market/Feature freshness availability.
