# Phase14-E37 Runtime v2 Demo Operation Rehearsal Plan

## Summary

Phase14-E37 defines the Level 3 Runtime v2 Demo Operation Rehearsal plan.

This is not an AI performance evaluation and not a component test. The purpose is to run the existing Runtime v2 operational flow in Demo mode and verify that operation data moves end-to-end through:

`Market Refresh -> Morning -> Pending -> Approval -> Submit -> Broker -> Execution -> Current -> Report -> Blog/Public Report -> Notification -> SELL -> Execution -> Current -> Report -> Blog/Public Report -> Notification`

No Runtime core changes are part of this phase. No test-only Runtime path, test-only Submit, test-only SELL, or fake adapter is allowed.

Final judgment: `PHASE14E37_DEMO_OPERATION_REHEARSAL_READY`

## Review Level

This rehearsal is a **Level 3 Full Runtime Review** as defined in Phase14-E33.

Level 3 boundary:

- Existing Runtime v2 CLI only.
- Demo Broker only.
- Fake adapter forbidden.
- Test-only paths forbidden.
- Runtime bypass forbidden.
- Production endpoint and Production order forbidden.
- Notification actual send only if explicitly enabled by a separate approval gate.

## Rehearsal Objective

The rehearsal verifies operational continuity, not profit quality:

- Market data and feature input are available or explicitly carried over.
- Morning Planning creates valid Pending, or blocks with a valid operational reason.
- Demo Submit uses the normal Runtime v2 submit pipeline.
- Broker OrderList / Position / Cash evidence is read by Runtime v2.
- Execution-equivalent records are generated.
- Current SoT is updated only by Runtime v2 writers.
- Report and Public/Blog artifacts reflect Current, Today, Run, Ledger History, Pending, Warnings, and Notification scope correctly.
- Notification payload / queue / delivery result are generated according to configured mode.
- SELL flow uses Current Position as the only SELL source.
- SELL execution updates position, cash, ledger, current, report, and notification artifacts.

## Hard Prohibitions

- Production order.
- Production Broker API Write.
- Runtime core modification during rehearsal.
- Rehearsal-only module.
- Rehearsal-only CLI.
- Rehearsal-only Runtime path.
- Rehearsal-specific operational directory such as `reports/runtime_v2/rehearsals/`.
- Test-only Runtime entry.
- Test-only Submit.
- Test-only SELL.
- Submit bypass.
- Fake adapter in the main flow.
- Runtime mainline branch for rehearsal success.
- Direct state modification to make the rehearsal pass.
- Current direct manual edit.
- `.runtime/demo/...` Current path revival.
- Phase9 Runtime.
- Phase9 writer as Runtime v2 path.
- Raw request / raw response / secret persistence.
- launchd/plist change during the rehearsal unless separately approved.

## Pre-Rehearsal Backup Plan

Backup must be completed before any rehearsal execution.

Backup source targets:

- `.runtime/`
- `reports/runtime_v2/`
- `reports/public/runtime_v2/`

Backup destination contract:

- Do not create a rehearsal-only Runtime path.
- Do not create `.runtime/backups/phase14e37/...`.
- Do not create `reports/runtime_v2/rehearsals/...`.
- Use an operator-managed external archive location outside the Runtime v2 operational tree, such as `/private/tmp/phase14e37_backup_{timestamp}/`, or an existing backup mechanism.
- The only repository record for the rehearsal plan/result is under `docs/phase_reports/` and `reports/phase_reports/`.

Backup contents:

- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/executions.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/cash.jsonl`
- `.runtime/persistent_ledger/events.jsonl`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/current_state.json`
- `.runtime/runtime_state/run_manifest/`
- `.runtime/operations/`
- `reports/runtime_v2/`
- `reports/public/runtime_v2/`

Broker state should also be recorded before rehearsal using Broker ReadOnly only:

- cash
- buying power
- positions
- orders
- executions/order status

Backup acceptance:

- backup manifest exists
- source paths listed
- destination paths listed
- checksums or file counts recorded
- restore command recorded
- no new Runtime operational path created
- no new rehearsal operational report path created
- no Broker Write
- no Submit

## Restore Plan

Restore is allowed only after explicit operator decision.

Restore source:

- operator-managed external archive location outside the Runtime v2 operational tree

Restore targets:

- `.runtime/`
- `reports/runtime_v2/`
- `reports/public/runtime_v2/`

Restore rules:

- Restore must not infer Current from report/blog/audit artifacts.
- Restore must not mix backup Current with post-rehearsal Ledger records.
- Restore must not touch Broker state.
- Restore must not create a rehearsal-only Runtime path.
- Restore must not introduce a rehearsal-only CLI/module.
- Broker state must be reconciled after restore with Broker ReadOnly.
- If Broker state changed during rehearsal, restored Current may require REVIEW_REQUIRED until Broker ReadOnly/Reconcile confirms consistency.

Restore confirmation:

- Current SoT readable.
- Pending state safe.
- Runtime state not HALT unless expected.
- Reconcile status known.
- Public report regenerated or marked stale.

## Initial State Contract

Required initial Runtime state:

- cash: `1,000,000`
- buying_power: `1,000,000`
- market_value: `0`
- total_equity: `1,000,000`
- positions: `[]`
- Pending: no stale submit-capable Pending
- Runtime State: not `REVIEW_REQUIRED`, not `BLOCKED`, not `HALT`
- Demo Capability: enabled
- 9000-series Demo guard: enabled

Current must not be manually edited. If initialization is required, use an existing Runtime v2-approved initializer or restore a known clean Runtime snapshot, then read back fixed Current paths.

Canonical Current paths:

- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/executions.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/cash.jsonl`
- `.runtime/persistent_ledger/events.jsonl`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/current_state.json`

## Go / No-Go Gates

### Gate 0: Environment

PASS requires:

- `--mode demo`
- `TACHIBANA_API_ENV=demo`
- Production endpoint blocked
- Production credential not used
- Runtime v2 CLI only
- Phase9 not called

### Gate 1: Backup

PASS requires:

- backup manifest written
- restore procedure recorded
- Broker ReadOnly before snapshot recorded

### Gate 2: Current

PASS requires:

- 100万円 / 保有0
- no stale Pending
- no `POST_SEND_UNKNOWN`
- no `SUBMITTED` / `MONITORING_FILL` carryover unless deliberately part of the rehearsal

### Gate 3: Market Data

PASS requires:

- feature-date contract exists
- selected feature artifacts exist
- carryover metadata explicit when used
- stale carryover not allowed
- E28 price source contract satisfied

### Gate 4: Submit Enable

PASS requires:

- Submit enabled only for the Submit job
- Pending state `APPROVED`
- approval hash and pending source hash consistent
- duplicate submit guard PASS
- Demo capability guard PASS
- 9000-series candidate excluded in Demo

### Gate 5: Notification

Default:

- `notification-mode=payload-only`

Actual send requires separate explicit approval:

- LINE/Discord secrets verified without exposing values
- Delivery queue ready
- dry-run/payload inspection PASS
- operator approves send-enabled mode

## Runtime Operation Sequence

All steps must use existing Runtime v2 CLI and existing Runtime paths only.

Forbidden during repetition:

- creating a rehearsal-specific module;
- creating a rehearsal-specific CLI;
- creating a rehearsal-specific Runtime path;
- adding Runtime mainline branches for the rehearsal;
- creating a test-only Submit/SELL path;
- using a fake adapter;
- changing Current directly to make the next run pass.

Repeat procedure:

1. Back up existing `.runtime/`, `reports/runtime_v2/`, and `reports/public/runtime_v2/` to the approved external/archive backup location.
2. Reset existing `.runtime/` and reports to the approved initial state through an existing Runtime v2-approved initializer or known clean snapshot restore.
3. Execute only the existing Runtime v2 CLI.
4. On failure, preserve existing logs, manifests, ledger, reports, and phase report result.
5. Next rehearsal attempt starts from the same backup/reset/restore procedure, not from a new rehearsal Runtime path.

### Step 1: Market Refresh

Purpose:

- update market data and canonical artifacts
- generate or select feature artifacts
- write feature-date contract

Command shape:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job market_refresh \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked \
  --market-refresh-allow-api-fetch true
```

Acceptance:

- manifest exit code is success or explicit REVIEW/BLOCK with reason
- no checkpoint-only PASS
- generated artifacts or carryover contract recorded
- no Submit
- no Notification actual send

### Step 2: Morning

Purpose:

- read Current SoT
- read feature-date contract
- perform AI inference / Planning
- apply Demo capability filter
- generate OrderPlan
- generate Approval artifact
- write Pending Current

Command shape:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Acceptance:

- feature input missing is not silent NO_SIGNAL
- selected feature date and price source aligned
- Pending is either `APPROVED` with items, or REVIEW/BLOCK with explicit reason
- no Submit

### Step 3: Submit

Purpose:

- submit approved Pending through normal Runtime v2 submit pipeline
- Demo Broker only

Command shape:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job submit \
  --submit-enabled true \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Acceptance:

- Submit source is only `.runtime/pending_order_plan/pending_order_plan.json`
- Pending state is `APPROVED`
- approval required and linked
- duplicate guard PASS
- Demo 9000-series guard PASS
- broker request uses normalized broker issue code
- manifest records submitted / accepted / rejected / unknown / blocked counts
- raw request/response/secrets are not saved
- Pending consume state updated
- Ledger orders written

### Step 4: BUY Execution

Purpose:

- read Broker OrderList / Position / Cash
- classify fills
- write execution-equivalent records
- update Ledger and Current SoT
- generate Report / Public Blog / Notification payload / Audit

Command shape:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job execution \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Acceptance:

- OrderList status read
- Position evidence read
- Cash / buying power evidence read
- OrderListDetail optional policy respected
- `executions.jsonl` receives execution-equivalent records
- Current positions/cash/equity updated by Runtime v2 writer only
- Reconcile PASS or explicit REVIEW/BLOCK
- Runtime/Public report generated
- Notification payload generated
- Blog/Public artifact generated

### Step 5: Blog/Public Report Check

Purpose:

- verify human-readable operation output

Artifacts:

- `reports/runtime_v2/{business_date}/runtime_report.md`
- `reports/runtime_v2/{business_date}/runtime_report.json`
- `reports/public/runtime_v2/{business_date}/public_report.md`
- `reports/public/runtime_v2/{business_date}/public_report.json`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`

Acceptance:

- Current Portfolio section correct
- Today's Operation Summary correct
- Ledger History Summary separated from Today
- Market data freshness visible
- execution-equivalent count visible
- redaction scan PASS
- no raw broker IDs/secrets/raw response

### Step 6: Notification Check

Default mode:

- payload-only

Artifacts:

- `reports/runtime_v2/{business_date}/notification_payload.json`
- delivery queue / delivery result artifacts if configured by Runtime v2 path
- audit result

Acceptance:

- payload generated
- queue entry generated if enabled
- LINE/Discord sender status reflects configured mode
- actual send is false unless separately approved
- Audit records no unexpected send

### Step 7: SELL Planning

Purpose:

- create SELL decision from Runtime Current Position only

Allowed SELL source:

- Current SoT positions only

Acceptance:

- no Current position means SELL cannot be planned
- SELL quantity <= Current quantity
- SELL quantity <= available quantity when Broker evidence is available
- BUY candidates are not mixed into SELL
- OrderPlan/Pending/Approval identify side=SELL
- no test-only SELL path

### Step 8: SELL Submit

Purpose:

- submit SELL Pending through normal Runtime v2 submit pipeline

Acceptance:

- Submit source is Pending Current only
- Approval required
- duplicate guard PASS
- quantity guard PASS
- Broker request side=SELL
- Demo Broker only
- Ledger orders written
- Pending consumed or REVIEW/BLOCK with reason

### Step 9: SELL Execution

Purpose:

- verify sell fill and reflect it into Runtime Current

Acceptance:

- OrderList read
- Position decreased or removed
- Cash / buying power increased or updated
- execution-equivalent SELL record written
- Ledger updated
- Current SoT updated
- Reconcile PASS or explicit REVIEW/BLOCK
- Runtime/Public report updated
- Notification payload updated
- Blog/Public report updated

## Verification Matrix

| Area | Evidence | PASS Condition |
| --- | --- | --- |
| BUY | Pending / Broker response / OrderList / executions.jsonl | accepted and filled or explicit REVIEW/BLOCK |
| SELL | Current Position / Pending / Broker response / OrderList / executions.jsonl | quantity guard and fill reflection PASS |
| Current | state.json | cash, buying_power, positions, market_value, total_equity consistent |
| Ledger | orders/executions/positions/cash/events jsonl | records written by Runtime v2 only |
| Execution | execution-equivalent records | BUY/SELL records present when filled |
| Report | runtime_report/public_report/latest | Current/Today/History scopes separated |
| Blog/Public | public_report/latest | readable, redacted, current |
| Notification | payload/queue/result/audit | payload-only unless send approved |
| Broker一致 | Broker ReadOnly | Broker evidence reconciles with Runtime state |
| Pending | pending_order_plan.json | no stale submit-capable Pending after completion |
| Carryover | feature_date_contract | requested/selected/latest/carryover/lag recorded |
| Feature Date | manifest + pending metadata | selected feature date used by Morning |

## Failure Policy

If any stage fails:

- stop at `REVIEW_REQUIRED`, `BLOCKED`, or `HALT`
- do not continue to next write stage
- do not retry Submit automatically
- do not reuse consumed Pending
- do not manually edit Current
- record manifest, report, and audit
- decide whether restore is required

Special handling:

- `POST_SEND_UNKNOWN`: no automatic resend
- Broker mismatch: Broker ReadOnly first, then Review
- Position drift: Review Event and Reconcile
- Notification send failure: no trading rollback

## Completion Criteria

The rehearsal is complete when the following are available:

- backup manifest
- restore procedure
- Broker ReadOnly before/after snapshots
- Market Refresh manifest
- Morning manifest
- Submit manifest
- BUY Execution manifest
- SELL Planning/Submit/Execution manifests
- Current SoT before/after summaries
- Ledger summaries
- Runtime Report
- Public/Blog Report
- Notification Payload / Queue / Delivery Result
- Audit result
- final operator summary

Records are written only to:

- `docs/phase_reports/`
- `reports/phase_reports/`

Runtime operation artifacts continue to use existing Runtime paths only:

- `.runtime/`
- `reports/runtime_v2/`
- `reports/public/runtime_v2/`

No `rehearsals/` Runtime path is introduced.

## Rehearsal Result Classification

Possible final classifications:

- `LEVEL3_DEMO_OPERATION_REHEARSAL_PASS`
- `LEVEL3_DEMO_OPERATION_REHEARSAL_PASS_WITH_NOTIFICATION_PAYLOAD_ONLY`
- `LEVEL3_DEMO_OPERATION_REHEARSAL_REVIEW_REQUIRED`
- `LEVEL3_DEMO_OPERATION_REHEARSAL_BLOCKED`

E37 creates the plan only. It does not execute the rehearsal.

## Final Judgment

`PHASE14E37_DEMO_OPERATION_REHEARSAL_READY`
