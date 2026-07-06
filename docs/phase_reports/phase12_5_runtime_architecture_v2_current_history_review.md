# Phase12.5 Runtime Architecture v2 / Current-History Separation Review

作成日: 2026-07-06

## Summary

判定: **REVIEW_REQUIRED**

Submit本線は Phase C により `pending_order_plan/pending_order_plan.json` 固定参照へ切り替わっている。一方で、Daily Plan / Approval / Reconcile / Report / Audit はまだ日付別artifactをCurrent Stateとして読んでいる箇所が多い。

現状は「Current State」「History」「Derived Report」の分類が途中段階で、次の混線リスクが残る。

- `order_plan/YYYY-MM-DD` は履歴になりつつあるが、Approval / Report / Auditでは本線入力として残っている。
- `approval_artifact/YYYY-MM-DD` は履歴だが、Approval linkage後も Report / Audit / ReconcileではCurrent判定に使われる。
- 現在保有・現金の固定Current Stateが未整備で、Daily Plan / Approval は `broker_positions/YYYY-MM-DD`、`broker_snapshot_summary/YYYY-MM-DD`、`demo_ledger/`、`submitted_orders/YYYY-MM-DD` fallbackを読む。
- `persistent_ledger/` はwriter/reader layerまで存在するが、Runtime本線は未接続。
- `demo_ledger/` がまだSubmit / Fill Monitor / Reconcile / Reportで「Persistent Demo Ledger」として現役で、v2の共通Persistent Ledgerへ移行できていない。

## Read Code / Artifact Areas

Code:

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/broker_readonly.py`
- `src/ai_fund_lab_v2/operations/demo_ledger.py`
- `src/ai_fund_lab_v2/operations/exit_adapter.py`
- `src/ai_fund_lab_v2/operations/ledger.py`
- `src/ai_fund_lab_v2/operations/notifications.py`
- `src/ai_fund_lab_v2/operations/pending_order_plan.py`
- `src/ai_fund_lab_v2/operations/persistent_ledger.py`
- `scripts/run_daily_plan.py`
- `scripts/run_approval_prepare.py`
- `scripts/run_submit_operation.py`
- `scripts/run_fill_monitor.py`
- `scripts/run_reconcile.py`

Runtime directories sampled:

- `.runtime/operations/order_plan/`
- `.runtime/operations/approval_artifact/`
- `.runtime/operations/pending_order_plan/`
- `.runtime/operations/submitted_orders/`
- `.runtime/operations/broker_*`
- `.runtime/operations/fill_events/`
- `.runtime/operations/reconciliation_result/`
- `.runtime/operations/reports/`
- `.runtime/operations/daily_report_refs/`
- `.runtime/operations/demo_ledger/`
- `.runtime/operations/persistent_ledger/`
- `.runtime/operations/ledger/`

## Current Read Paths By Runtime Module

| Module | Current reads | History writes / outputs | Notes |
| --- | --- | --- | --- |
| `run_daily_plan` | `market_refresh/YYYY-MM-DD/market_refresh_manifest.json`, `feature_refresh/YYYY-MM-DD/latest_features.json`, `feature_artifacts/YYYY-MM-DD/candidate_features.parquet`, `broker_snapshot_summary/YYYY-MM-DD/broker_snapshot_summary.json`, broker bundle, `broker_positions/YYYY-MM-DD/positions.json` via exit generation/budget | `daily_plan/YYYY-MM-DD/daily_plan_result.json`, `order_plan/YYYY-MM-DD/order_plan.json`, `feature_candidate_audit/YYYY-MM-DD/feature_candidate_audit.json`, conditional `pending_order_plan/pending_order_plan.json` | Still uses dated broker and feature artifacts as Current for plan generation. |
| `run_approval_prepare` | `order_plan/YYYY-MM-DD/order_plan.json`, `safety_result/YYYY-MM-DD/safety_result.json`, `broker_snapshot_summary/YYYY-MM-DD/broker_snapshot_summary.json`, broker bundle, `demo_ledger/`, `submitted_orders/YYYY-MM-DD/submitted_orders.json` exposure fallback | `approval_request/YYYY-MM-DD/approval_request.json`, `approval_artifact/YYYY-MM-DD/approval_artifact.json`, pending approval linkage update | Approval still reads dated order_plan directly. Pending linkage is secondary write-back. |
| `run_submit_operation` | `pending_order_plan/pending_order_plan.json`, pending source `order_plan` path/hash, pending approval path/hash, `safety_result/YYYY-MM-DD`, `broker_snapshot_summary/YYYY-MM-DD`, broker bundle, `positions/YYYY-MM-DD/positions.json`, previous `submitted_orders/YYYY-MM-DD` retry parent, `demo_ledger/` summary | `submitted_orders/YYYY-MM-DD/submitted_orders.json`, `daily_manifest/YYYY-MM-DD`, `demo_ledger/` update in demo | Submit selection is pending fixed path. Dated order_plan/approval are only hash-validated source artifacts from pending metadata. |
| `run_fill_monitor` | `submitted_orders/YYYY-MM-DD/submitted_orders.json`, broker bundle; if live submitted orders and broker bundle incomplete, refreshes Demo read-only | `fill_events/YYYY-MM-DD/fill_events.json`, `demo_ledger/` monitoring update | Uses dated submitted_orders and dated broker bundle as Current for same-day lifecycle. |
| `run_safety_monitor` | `broker_snapshot_summary/YYYY-MM-DD`, `submitted_orders/YYYY-MM-DD`, `fill_events/YYYY-MM-DD`, broker bundle | `safety_monitor/YYYY-MM-DD/safety_monitor_result.json`, `safety_events/YYYY-MM-DD`, `human_review/YYYY-MM-DD`, report line payload placeholder | Dated broker state is Current. |
| `run_reconcile` | `submitted_orders/YYYY-MM-DD`, source dates from submitted metadata, source `order_plan/<source_date>`, source `approval_artifact/<source_date>`, broker bundle, `fill_events/YYYY-MM-DD`, `safety_monitor/YYYY-MM-DD`, `ledger/YYYY-MM-DD`, `demo_ledger/` reset detection | `reconciliation_result/YYYY-MM-DD/reconciliation_result.json` | Source-date aware, but still treats dated artifacts as reconciliation truth. |
| `run_daily_report` | current operation statuses from dated artifacts, `market_refresh/YYYY-MM-DD`, `order_plan/YYYY-MM-DD`, `feature_candidate_audit/YYYY-MM-DD`, broker bundle, `ledger/YYYY-MM-DD`, `approval_artifact/YYYY-MM-DD`, `submitted_orders/YYYY-MM-DD`, `fill_events/YYYY-MM-DD`, `safety_monitor/YYYY-MM-DD`, `reconciliation_result/YYYY-MM-DD`, `audit_result/audit_result.json` | `reports/YYYY-MM-DD/*`, `daily_report_refs/YYYY-MM-DD/daily_report_refs.json`, optional `notifications/YYYY-MM-DD/notification_result.json` | Report separates submitted_orders as today Submit SoT and order_plan as next candidates, but still loads dated order_plan for next section and dated approval for checks. |
| `run_audit` | all `.runtime/operations/**/*.json`, latest `daily_manifest`, latest dated `order_plan`, market, ledger, broker bundle, report/reconcile/safety | `audit_result/audit_result.json` | Broad scan is useful for audit but can amplify History/Current ambiguity unless latest/current semantics are explicit. |
| notifications | `report_refs` from `run_daily_report`, env/dotenv config | `notifications/YYYY-MM-DD/notification_result.json` | Notification is derived from daily_report_refs/report model, not direct order_plan SoT. |

## `order_plan/YYYY-MM-DD` Still On Mainline

`order_plan/YYYY-MM-DD/order_plan.json` is still used in these places:

- `run_daily_plan`: writes dated order_plan history and uses it as pending promotion source.
- `run_approval_prepare`: reads the dated order_plan for approval generation.
- `link_approval_to_pending_order_plan`: validates pending source against dated order_plan hash.
- `run_reconcile`: validates source order_plan existence using submitted source date.
- `run_daily_report`: reads dated order_plan for next order candidate display and flow guard.
- `_build_daily_report_model`: uses the order_plan passed from `run_daily_report` to build next BUY/SELL rows and display fallback for submitted rows.
- `_collect_operation_statuses` / `_current_operation_statuses` / `_operation_flow_integrity_guard`: use dated order_plan to classify operation day and stale submit.
- `run_audit`: loads latest dated order_plan from latest manifest.
- `_collect_sell_report_summary`: reads dated order_plan and dated approval.
- `_resolve_submit_order_plan_date`: legacy function still exists but is not used by `run_submit_operation`.

Current interpretation:

- For Submit target selection: **not mainline**.
- For Approval target selection, Report next-candidate display, flow guard and audit: **still mainline**.

## `approval_artifact/YYYY-MM-DD` Still On Mainline

`approval_artifact/YYYY-MM-DD/approval_artifact.json` is still used in these places:

- `run_approval_prepare`: writes dated approval history.
- `link_approval_to_pending_order_plan`: links approval into pending.
- `load_pending_order_plan_for_submit`: reads approval path from pending metadata and validates hash/status.
- `run_reconcile`: validates source approval existence using submitted source date.
- `run_daily_report` / `_build_daily_report_model`: reads dated approval for report model and checklist.
- `_operation_flow_integrity_guard` / `_source_of_truth_consistency_guard`: checks approval status and manual override.
- `_demo_production_parity_audit`, `_production_equivalence_checklist`, `_collect_sell_report_summary`.
- `_resolve_submit_order_plan_date`: legacy function still exists but is not used by Submit mainline.

Current interpretation:

- For Submit target selection: approval is reached through pending metadata and hash guard.
- For Approval generation, Report/Audit/Reconcile: dated approval remains mainline history/current hybrid.

## Pending Order Plan Status

`pending_order_plan/pending_order_plan.json` is now the Submit SoT.

Evidence:

- `run_submit_operation()` calls `load_pending_order_plan_for_submit(root=paths.root, submit_run_date=trade_date)`.
- Submit no longer calls `_resolve_submit_order_plan_date()`.
- Pending guard blocks missing, non-APPROVED, date mismatch, target session mismatch, source order_plan hash mismatch, approval hash mismatch, approval item mismatch, expiry, terminal states, and stale `SUBMITTING`.
- Submitted artifact writes `uses_pending_order_plan=true`, `submit_source=pending_order_plan`, `dated_order_plan_fallback_used=false`, pending path/id/source metadata.

Remaining gaps:

- Phase D consume is not connected. Submit can mark/consume only minimally; terminal state lifecycle is not complete.
- Approval linkage is connected, but Approval itself still starts from dated order_plan rather than pending.
- Daily Plan promotion is time-guarded and can skip pending; natural operation still needs strict schedule discipline.

## Persistent Ledger Status

`persistent_ledger/` exists as a common Demo/Production writer/reader layer:

- `orders.jsonl`
- `executions.jsonl`
- `positions.jsonl`
- `cash_history.jsonl`
- `events.jsonl`
- `migrations.jsonl`
- `state.json`

Implemented functions include:

- `append_order`
- `append_execution`
- `append_position_state`
- `append_cash_state`
- `append_event`
- `summarize_persistent_ledger`
- `read_persistent_ledger_state`
- `get_current_positions`
- `get_current_cash`
- `get_position_by_code`
- `get_execution_history`
- `get_order_history`
- `get_positions_source_summary`
- `get_review_required_positions`

But `rg` shows the runtime mainline does not call these functions outside `persistent_ledger.py` and tests. Current runtime still uses:

- `demo_ledger/` for Demo persistence.
- dated `broker_positions/YYYY-MM-DD`.
- dated `broker_buying_power/YYYY-MM-DD`.
- dated `ledger/YYYY-MM-DD`.

Therefore persistent_ledger is **not yet Current State SoT**.

## Current State Needed Fixed Paths

Recommended v2 Current State fixed paths:

| Current State | Proposed fixed path | Current status |
| --- | --- | --- |
| Submit target | `.runtime/operations/pending_order_plan/pending_order_plan.json` | Implemented for Submit. |
| Pending history | `.runtime/operations/pending_order_plan/history/YYYY-MM-DD/<plan_id>.json` | Implemented. |
| Pending consumed/archive | `.runtime/operations/pending_order_plan/consumed/YYYY-MM-DD/<plan_id>.json` | Path exists in design, consume not connected. |
| Current holdings | `.runtime/operations/persistent_ledger/state.json` | Implemented but not connected. |
| Current cash/buying power | `.runtime/operations/persistent_ledger/state.json` | Implemented but not connected. |
| Order history | `.runtime/operations/persistent_ledger/orders.jsonl` | Implemented but not connected. |
| Execution history | `.runtime/operations/persistent_ledger/executions.jsonl` | Implemented but not connected. |
| Lifecycle/event history | `.runtime/operations/persistent_ledger/events.jsonl` | Implemented but not connected. |
| Latest broker read-only snapshot | Suggested: `.runtime/operations/current_broker_state/broker_snapshot.json` or generated from dated broker artifacts into persistent ledger | Not implemented. |
| Current runtime day status | Suggested: `.runtime/operations/current_runtime_state/state.json` or daily_manifest latest pointer | Not implemented. |
| Latest report refs for notification | Derived from `daily_report_refs/YYYY-MM-DD`; fixed latest pointer optional | Not implemented. |

## History Artifacts To Keep

These should remain immutable or append-only History / Evidence:

- `market_refresh/YYYY-MM-DD/market_refresh_manifest.json`
- `feature_refresh/YYYY-MM-DD/*`
- `feature_artifacts/YYYY-MM-DD/candidate_features.parquet`
- `daily_plan/YYYY-MM-DD/daily_plan_result.json`
- `order_plan/YYYY-MM-DD/order_plan.json`
- `approval_request/YYYY-MM-DD/approval_request.json`
- `approval_artifact/YYYY-MM-DD/approval_artifact.json`
- `submitted_orders/YYYY-MM-DD/submitted_orders.json`
- `broker_readonly_source/YYYY-MM-DD/tachibana_demo_snapshot.json`
- `broker_readonly_reports/YYYY-MM-DD/broker_readonly_snapshot_report.json`
- `broker_snapshot/YYYY-MM-DD/broker_snapshot.json`
- `broker_orders/YYYY-MM-DD/orders.json`
- `broker_executions/YYYY-MM-DD/executions.json`
- `broker_positions/YYYY-MM-DD/positions.json`
- `broker_buying_power/YYYY-MM-DD/buying_power.json`
- `broker_account_summary/YYYY-MM-DD/account_summary.json`
- `fill_events/YYYY-MM-DD/fill_events.json`
- `safety_monitor/YYYY-MM-DD/safety_monitor_result.json`
- `safety_events/YYYY-MM-DD/safety_events.json`
- `ledger/YYYY-MM-DD/ledger_state.json`
- `ledger/YYYY-MM-DD/ledger_summary.json`
- `reconciliation_result/YYYY-MM-DD/reconciliation_result.json`
- `daily_manifest/YYYY-MM-DD/daily_manifest.json`

## Derived Reports

Derived outputs:

- `reports/YYYY-MM-DD/public_report.md`
- `reports/YYYY-MM-DD/blog_draft.md`
- `reports/YYYY-MM-DD/safety_report.md`
- `reports/YYYY-MM-DD/line_payload.json`
- `reports/YYYY-MM-DD/discord_payload.json`
- `daily_report_refs/YYYY-MM-DD/daily_report_refs.json`
- `notifications/YYYY-MM-DD/notification_result.json`
- `audit_result/audit_result.json`

These should not become operational Current State inputs except for notification reading the report model/refs.

## Current-History Mixed Risks

High risks:

- Daily Plan can still treat dated `broker_positions/YYYY-MM-DD` absence as no positions, so holdings can disappear across days until persistent ledger is connected.
- Approval current exposure still falls back from dated broker positions to `demo_ledger/` to `submitted_orders/YYYY-MM-DD`, which can carry stale same-day exposure semantics.
- Report creates synthetic demo positions from filled submitted rows when broker positions are empty. This is useful for display but not a true Current State SoT.
- `demo_ledger/` remains Demo-specific persistent state despite the target architecture moving to common `persistent_ledger/`.

Medium risks:

- Report and Audit still classify operation health using dated order_plan/approval status even after Submit source moved to pending.
- `_current_operation_statuses()` treats submitted_orders older than same-day order_plan as `STALE_IGNORED`; this helps report correctness but is still a dated artifact heuristic.
- `_resolve_submit_order_plan_date()` remains in code. It is not used by Submit mainline, but its presence is a maintenance hazard.
- `ledger/YYYY-MM-DD` is derived from dated broker read-only, not persistent ledger, so it is History/Derived but named like current ledger.

Low risks:

- Notifications are report-derived and do not directly use order_plan as Submit SoT.
- Reconcile is source-date aware when submitted_orders contains `order_plan_source_date` / `approval_source_date`.

## Target v2 Classification

Current State:

- `pending_order_plan/pending_order_plan.json`
- `persistent_ledger/state.json`
- `persistent_ledger/*.jsonl`
- future fixed broker/current status pointer, if needed

History / Evidence:

- all `*/YYYY-MM-DD/*` runtime artifacts
- pending history/consumed records

Derived:

- reports
- daily_report_refs
- notifications
- audit_result

## Proposed Migration Order

1. **Freeze terminology**: update internal docs/constants so `order_plan/YYYY-MM-DD` and `approval_artifact/YYYY-MM-DD` are explicitly History/Evidence except where pending validates them by hash.
2. **Complete Pending Phase D**: Submit should transition pending to `SUBMITTED` / `CONSUMED` atomically enough to prevent reuse.
3. **Connect Persistent Ledger writer**: after Submit / broker read-only / fill / reconcile, append order/execution/position/cash/event to common `persistent_ledger`.
4. **Connect Daily Plan read path**: SELL generation and max_positions should read current holdings from `persistent_ledger/state.json`, with broker_positions as refresh source, not the only source.
5. **Connect Approval read path**: current exposure and available cash should read fixed Current State first; dated submitted_orders fallback should be removed or limited to same-run review.
6. **Connect Report read path**: current holdings/cash should come from persistent ledger; order_plan remains next-candidate section only; synthetic demo positions should be review-labeled display fallback only.
7. **Legacy demo_ledger deprecation**: stop new writes to `demo_ledger/`, migrate if needed, then keep read-only legacy fallback for a bounded period.
8. **Remove legacy Submit resolver**: delete or quarantine `_resolve_submit_order_plan_date()` after tests confirm no caller.
9. **Add Current/History architecture tests**: assert Submit only uses pending; Daily Plan/Approval/Report do not use dated order_plan/approval as Current State.

## Final Judgment

`REVIEW_REQUIRED`

Reason:

- Submit SoT is now pending, but Current State for holdings/cash/exposure is not yet unified.
- History artifacts are still used as live/current inputs in several modules.
- `persistent_ledger` is present but not connected.
- `demo_ledger` remains active and overlaps with the intended common ledger responsibility.

## Prohibited Actions Confirmation

This review did not:

- change implementation
- run Submit
- place Broker orders
- delete artifacts
- send notifications
- connect to Production

