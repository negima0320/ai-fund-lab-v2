# Phase12.5 Final Issue Summary and Phase13 Handoff

Date: 2026-07-06

Final judgement: **REVIEW_REQUIRED / CLOSED_FOR_REDESIGN**

## Summary

Phase12.5 was started as a Production Equivalent Runtime Acceptance Test on the Tachibana Demo environment. During the work, several individual gaps were fixed, including retry diagnosis, report Source of Truth separation, and the first stages of `pending_order_plan` and `persistent_ledger`.

However, the main finding is more fundamental: the Runtime still mixes **Current State**, **History / Evidence**, and **Derived Report** artifacts. This is not primarily an AI stock-selection issue. It is a Runtime state-management issue.

Because current holdings, cash, execution history, and pending submit state are not yet cleanly represented as fixed Current State, Phase12.5 cannot honestly be closed as Production Equivalent. It is closed as `REVIEW_REQUIRED / CLOSED_FOR_REDESIGN`, and Phase13 must become **Runtime Architecture v2 Rebuild**.

## Documents Read

- `docs/phase_reports/phase12_5_runtime_architecture_v2_current_history_review.md`
- `docs/phase_reports/phase12_5_pending_order_plan_sot_design.md`
- `docs/phase_reports/phase12_5_pending_order_plan_phase_a.md`
- `docs/phase_reports/phase12_5_pending_order_plan_phase_b_approval_linkage.md`
- `docs/phase_reports/phase12_5_pending_order_plan_phase_c_submit_read_switch.md`
- `docs/phase_reports/phase12_5_storage_sot_classification_audit.md`
- `docs/phase_reports/phase12_5_unified_holdings_ledger_design.md`
- `docs/phase_reports/phase12_5_persistent_ledger_phase_a.md`
- `docs/phase_reports/phase12_5_persistent_ledger_reader_layer.md`
- `docs/phase_reports/phase12_5_report_notification_submit_sot_fix.md`
- `docs/phase_reports/phase12_5_positions_api_root_cause_audit.md`
- `docs/phase_reports/phase12_5_positions_safe_diagnosis.md`
- `docs/phase_reports/phase12_5_pending_plan_full_manual_runtime_rehearsal.md`
- `docs/01_requirements/phase_roadmap.md`

## What Phase12.5 Implemented

- Tachibana API retry and safe diagnosis improvements.
- Read-only failure classification separation, including `FAILED_LOGIN_SESSION`.
- Positions API safe diagnosis that records key names and match rates without raw values.
- Report / Notification separation of today's Submit result and next order candidates.
- `pending_order_plan` Phase A schema, writer, reader, hash, and promotion guard.
- `pending_order_plan` Phase B approval linkage.
- `pending_order_plan` Phase C Submit read switch.
- Submit now reads `pending_order_plan/pending_order_plan.json` as the Submit source and does not use dated order-plan fallback.
- `persistent_ledger` Phase A schema, writer, dedup, JSONL files, and `state.json` summarization.
- `persistent_ledger` Reader Layer for future Daily Plan / Approval / Report / Notification integration.

## What Phase12.5 Fixed

- The old Submit path that could select `order_plan/YYYY-MM-DD` directly was replaced by a pending-only Submit guard.
- `order_plan` is no longer allowed to be silently used as today's Submit result in reports.
- `submitted_orders/YYYY-MM-DD` is the Source of Truth for today's Submit result.
- `order_plan/YYYY-MM-DD` is treated as the next order candidate source in Report / Notification.
- `REVIEW_REQUIRED_REPORT` can still display real submitted orders when `submitted_orders` exists.
- Broker ReadOnly failures now preserve safer classifications and do not masquerade as a clean pass.
- Report text now exposes that Broker Orders may show filled status while Broker Executions / Positions remain unconfirmed.

## What Remains Unresolved

- Current holdings are not yet a single fixed Current State.
- Current cash and buying power are not yet a single fixed Current State.
- `persistent_ledger/state.json` exists but is not connected to Daily Plan, Approval, Report, Notification, Reconcile, or Audit as the main Current State.
- `demo_ledger/` still overlaps with the new persistent ledger concept and must be legacy-only.
- Broker Orders can show `全部約定`, but Broker Executions / Positions may still be zero or unavailable.
- Positions API root cause is not fully closed until safe diagnosis from a successful Broker ReadOnly run is reviewed.
- Pending Plan lacks Phase D consume lifecycle: `SUBMITTED`, `CONSUMED`, `EXPIRED`, stale `SUBMITTING`, archive, and idempotent re-run handling.
- Approval generation still begins from dated `order_plan/YYYY-MM-DD`.
- Daily Plan and Approval still have dated/current hybrid reads for holdings, exposure, and cash.
- Reconcile / Audit / Report still read several dated artifacts as current health indicators.
- Launchd through-operation should not resume until Architecture v2 Acceptance Test is redesigned and passed.

## Why This Is Not an AI Layer Problem

The observed failures did not come from Candidate AI choosing the wrong names or Safety AI producing a wrong investment judgement. The failures came from Runtime state ambiguity:

- A plan date was used as both an evidence date and an execution target date.
- A dated approval artifact was used as both proof and operational state.
- Submitted orders were sometimes confused with planned orders.
- Filled broker orders did not reliably flow into current holdings.
- Current holdings could disappear the next day because the Runtime did not have a single persistent Current State.
- Reports could look coherent while the underlying SoT was mixed.

Therefore Phase13 must not start by changing AI selection models. It must first rebuild Runtime state management.

## Current / History / Derived Mixing

### Current State That Must Be Fixed Path

- Submit target: `pending_order_plan/pending_order_plan.json`
- Current holdings: `persistent_ledger/state.json`
- Current cash / buying power: `persistent_ledger/state.json`
- Order history: `persistent_ledger/orders.jsonl`
- Execution history: `persistent_ledger/executions.jsonl`
- Position state history: `persistent_ledger/positions.jsonl`
- Cash history: `persistent_ledger/cash_history.jsonl`
- Lifecycle / runtime events: `persistent_ledger/events.jsonl`

### History / Evidence

- `order_plan/YYYY-MM-DD/order_plan.json`
- `approval_request/YYYY-MM-DD/approval_request.json`
- `approval_artifact/YYYY-MM-DD/approval_artifact.json`
- `submitted_orders/YYYY-MM-DD/submitted_orders.json`
- `broker_orders/YYYY-MM-DD/orders.json`
- `broker_executions/YYYY-MM-DD/executions.json`
- `broker_positions/YYYY-MM-DD/positions.json`
- `fill_events/YYYY-MM-DD/fill_events.json`
- `reconciliation_result/YYYY-MM-DD/reconciliation_result.json`
- `broker_readonly_reports/YYYY-MM-DD/*.json`

### Derived

- `reports/YYYY-MM-DD/*`
- `daily_report_refs/YYYY-MM-DD/daily_report_refs.json`
- `notifications/YYYY-MM-DD/notification_result.json`
- Blog, LINE, Discord payloads.

Derived artifacts must never become operational Source of Truth.

## Why Dated `order_plan` and `approval_artifact` Were Dangerous

`order_plan/YYYY-MM-DD` previously meant too many things:

- Plan creation day.
- Candidate evidence day.
- Report day.
- Possible Submit target day.
- Sometimes next session intent.

This created weekend and morning mixing risk. A manually generated current-day plan could be selected ahead of the intended previous-session plan.

`approval_artifact/YYYY-MM-DD` had a similar problem. It is valid as evidence of approval, but if it is also used as current executable state without a pending lifecycle, the Runtime cannot tell whether it is approved, submitted, consumed, expired, or stale.

The prevention is explicit:

- Dated order plans and approvals are History / Evidence.
- Submit target is only `pending_order_plan`.
- Approval is linked by path and hash into pending.
- Submit consumes pending and never falls back to dated artifacts.

## Pending Order Plan Status

Implemented:

- Fixed path `pending_order_plan/pending_order_plan.json`.
- History path `pending_order_plan/history/YYYY-MM-DD/<plan_id>.json`.
- Schema with `plan_created_date`, `intended_submit_date`, and `target_session_date`.
- Promotion guard for market-close plan creation.
- Approval linkage with path/hash/item validation.
- Submit read switch to pending-only.
- Submit metadata records `submit_source=pending_order_plan` and `dated_order_plan_fallback_used=false`.
- Missing or invalid pending blocks Submit rather than falling back.

Still incomplete:

- Phase D consume lifecycle.
- `SUBMITTED` / `CONSUMED` / `EXPIRED` transitions.
- stale `SUBMITTING` recovery policy.
- consumed archive wiring.
- Report / Audit display of consumed pending state.
- Full manual and launchd acceptance after market data and Broker ReadOnly prerequisites pass.

## Persistent Ledger Status

Implemented:

- Common Demo / Production path: `.runtime/operations/persistent_ledger/`
- `orders.jsonl`
- `executions.jsonl`
- `positions.jsonl`
- `cash_history.jsonl`
- `events.jsonl`
- `migrations.jsonl`
- `state.json`
- writer functions and dedup logic.
- reader functions for current positions, cash, order history, execution history, and review-required positions.
- redaction guard for raw request, raw response, secrets, and plain broker IDs.

Still not connected:

- Daily Plan holdings and SELL candidate source.
- Daily Plan max_positions calculation.
- Approval current exposure, cash, and buying power.
- Report / Notification current holdings and cash.
- Reconcile / Audit current-state checks.
- Broker Positions / Executions ingestion into persistent ledger.
- Demo-only Broker Orders fallback projection.

## Why `demo_ledger` Must Become Legacy

`demo_ledger/` was useful to absorb Demo-specific daily reset constraints, but it is named and structured as Demo-only state. Phase13 needs Demo and Production to share the same Runtime shape.

The target is not separate Demo and Production ledgers. The target is a common `persistent_ledger/` with metadata:

- `environment=demo` or `environment=production`
- `source`
- `review_required`
- `production_equivalent`

`demo_ledger/` should become legacy evidence or migration fallback only. It must not remain the main SoT for holdings, executions, or cash.

## Why Execution / Holdings / Cash SoT Is Still Incomplete

The Day1 runtime showed a critical pattern:

- Submit accepted orders.
- Broker Orders could show filled status.
- Broker Executions could be zero.
- Broker Positions could be zero.
- Runtime current holdings were not updated reliably.

Until Broker Positions / Executions are confirmed and connected to persistent ledger, holdings cannot be treated as settled Current State. Demo-only fallback from Broker Orders may be necessary, but it must be review-required and forbidden as a Production position-confirmation mechanism.

Cash and buying power have the same issue. They must come from broker state or persistent current state, not from dated plans or optimistic sell proceeds.

## Report / Notification Mixing and Fix State

The 2026-07-03 report initially mixed:

- Today's Submit result from `submitted_orders/2026-07-03`.
- Next order candidates from `order_plan/2026-07-03`.

This was fixed so that:

- Today's Submit result uses `submitted_orders/YYYY-MM-DD`.
- Today's order/fill confirmation uses Broker Orders, Broker Executions, Fill Events, and Reconcile.
- Next order candidates use `order_plan/YYYY-MM-DD` in a separate section.
- Discord and LINE payloads follow the same policy.
- REVIEW_REQUIRED reasons remain visible.

Remaining Phase13 work:

- Current holdings, cash, and asset display should come from `persistent_ledger/state.json`.
- Report must show source and review flags for fallback positions.
- Notification must not imply terminal device delivery from HTTP success alone.

## Broker ReadOnly / J-Quants Auxiliary Issues

Broker ReadOnly:

- `FAILED_LOGIN_SESSION` can still block read-only state capture.
- Safe retry and diagnosis exist, but a successful run is needed to inspect `positions_safe_diagnosis.json`.
- Positions API root cause remains unresolved until key-only diagnosis confirms API empty vs normalizer mismatch vs writer filter.

J-Quants / Market data:

- Full manual rehearsal hit `MARKET_DATA_NOT_YET_AVAILABLE`.
- Feature artifacts were not generated, Daily Plan blocked, and pending was not promoted.
- This confirms fail-closed behavior, but not full runtime acceptance.

These are auxiliary blockers. They do not change the main conclusion: Runtime Current State architecture must be rebuilt.

## Why Launchd Was Stopped / Not Restarted

Launchd through-operation should not run while Runtime state is still mixed.

Reasons:

- A scheduled plan could create dated history that looks executable.
- Current holdings may be stale, missing, or Demo-only.
- Report / Audit could pass derived checks while Current State remains incomplete.
- Broker ReadOnly or market-data blockers can produce partial daily artifacts.
- Pending consume lifecycle is not finished.

Phase13 must require a launchd Acceptance Test before automatic operation is restarted.

## Phase13 Carryover Tasks

Critical:

- Freeze Current State / History / Derived definitions.
- Complete Pending Plan Phase D consume lifecycle.
- Connect Persistent Ledger to Runtime mainline.
- Make `persistent_ledger/state.json` the current holdings and cash source.
- Remove `demo_ledger/` from main SoT usage.
- Define and test Broker Positions / Executions ingestion.
- Keep Broker Orders fallback Demo-only and review-required.
- Prohibit Broker Orders fallback as Production current holdings.

High:

- Move Daily Plan holdings / SELL / max_positions decisions to persistent ledger current state.
- Move Approval current exposure / cash / buying power to persistent ledger current state.
- Move Report / Notification current holdings and cash display to persistent ledger current state.
- Make Reconcile / Audit current-state references explicit.
- Add architecture tests to prevent dated artifact fallback.

Medium:

- Report pending consume state.
- Add current runtime-state latest pointers if needed.
- Re-run full manual rehearsal only after Broker ReadOnly and Market/Feature prerequisites pass.
- Rebuild launchd Acceptance Gate after Phase13 implementation.

Deferred:

- Replacement Policy / Portfolio Rotation AI.
- Candidate AI redesign.
- Opportunity AI redesign.
- Safety investment judgement changes.
- Full backtest.

## Phase13 Principles

- Runtime SoT before AI changes.
- Current State must be fixed-path and explicit.
- Dated artifacts are History / Evidence unless explicitly promoted.
- Derived reports are never SoT.
- Submit must read only pending.
- No silent fallback from pending to dated order_plan.
- No current holdings = no optimistic BUY planning.
- Demo-specific fallback must be marked `review_required=true`.
- Production must use Broker Positions / Executions as the official confirmation source.
- Production orders remain prohibited.
- Launchd stays stopped until Acceptance Test passes.

## Phase13 Start Conditions

- `docs/01_requirements/phase_roadmap.md` updated with Phase13 Runtime Architecture v2 Rebuild.
- Phase12.5 issue list documented in this handoff.
- launchd automatic operation remains stopped / not restarted.
- Phase13 begins with Architecture / SoT / Acceptance Test fixed before more runtime automation.

## Prohibited Actions Confirmation

This handoff performed documentation and roadmap updates only.

- No implementation change.
- No Submit execution.
- No Broker order.
- No Production connection.
- No Production order.
- No artifact deletion.
- No notification send.
- No AI retraining.
- No full backtest.
- No raw request / raw response / secret material was added.
