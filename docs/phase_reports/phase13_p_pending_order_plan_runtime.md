# Phase13-P Pending Order Plan Runtime

## Status

IMPLEMENTED_PENDING_RUNTIME

## Scope

Phase13-P implements the minimal Pending Order Plan Runtime.

Implemented:

- `PendingOrderPlan` and `PendingOrderItem` models
- Pending lifecycle states and transition validation
- fixed-path pending reader
- explicit-path pending writer
- promotion skeleton from an explicit source order plan reference
- approval link skeleton
- consume skeleton
- re-submit guard
- no fallback and no side effect tests

Not implemented:

- Submit
- Broker connection
- Broker order submission
- Production order submission
- Notification send
- launchd / plist operation
- Backtest / Simulation execution

## Current Artifact Rule

Submit target resolution is limited to:

```text
pending_order_plan/pending_order_plan.json
```

The reader uses Runtime v2 path resolution and reads only:

```text
.runtime/{mode}/pending_order_plan/pending_order_plan.json
```

The reader does not search:

- `order_plan/YYYY-MM-DD`
- `approval_artifact/YYYY-MM-DD`
- latest artifacts
- phase directories
- legacy runtime entrypoints

## Lifecycle

Pending lifecycle states:

- `PENDING_APPROVAL`
- `APPROVED`
- `SUBMITTING`
- `SUBMITTED`
- `CONSUMED`
- `EXPIRED`
- `BLOCKED`
- `REVIEW_REQUIRED`
- `POST_SEND_UNKNOWN`

`CONSUMED` is a Pending lifecycle state, not a Runtime State.

Forbidden transitions include:

- `CONSUMED -> SUBMITTING`
- `CONSUMED -> APPROVED`
- `POST_SEND_UNKNOWN -> SUBMITTING`
- `SUBMITTED -> SUBMITTING`
- `REVIEW_REQUIRED -> APPROVED`
- `EXPIRED -> APPROVED`

## Re-Submit Guard

`can_submit_pending_plan` returns false when:

- state is not `APPROVED`
- the plan is `CONSUMED`
- the plan is `SUBMITTING`
- the plan is `SUBMITTED`
- the plan is `POST_SEND_UNKNOWN`
- the plan is `REVIEW_REQUIRED`
- the plan is `EXPIRED`
- approval is missing
- approved item ids are missing or invalid
- the same `pending_plan_id` exists in order dedup keys

Phase13-P does not submit. It only exposes the guard.

## Evidence Links

Promotion stores source order plan path and hash as evidence. Approval link stores approval path and hash as evidence.

These artifacts are not treated as Current and are not used as fallback submit sources.

## Guardrail Confirmation

Phase13-P did not perform:

- Submit
- Broker order
- Demo order
- Production order
- Notification send
- launchd restart
- existing plist deletion
- new plist creation
- artifact deletion
- AI retraining
- full backtest
- Backtest execution
- Simulation execution
- History fallback
- Derived fallback
- default production fallback
- existing demo ledger read

