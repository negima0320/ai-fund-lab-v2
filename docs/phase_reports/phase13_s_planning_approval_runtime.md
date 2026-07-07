# Phase13-S Planning / Approval Runtime v2 Skeleton

## Status

IMPLEMENTED_SKELETON

## Scope

Phase13-S implements Planning / Approval Runtime skeletons.

Implemented:

- AI output placeholder models
- Capital Allocation and Safety placeholder models
- `PlanningInput` / `PlanningResult`
- `DailyPlan` / `OrderPlan` / `OrderPlanItem`
- Current State guard in planning
- OrderPlan to Pending promotion integration
- `ApprovalRequest`
- `ApprovalArtifact`
- `ApprovalDecision`
- Approval policy skeleton
- Approval to Pending linkage helper
- no side effect tests

Not implemented:

- AI inference
- AI scoring or ranking logic
- fixed symbol count limit
- Submit
- Broker connection
- Broker order submission
- Notification send
- launchd / plist operation
- Backtest / Simulation execution

## Runtime Principles

Planning accepts AI output as payload. Runtime v2 does not reimplement AI judgment logic and does not recalculate AI rank or score.

Runtime v2 does not impose a fixed symbol count limit. It processes the provided AI signals and applies Current State, Safety, and Capital Allocation constraints.

Current State guard behavior:

- missing asset state blocks planning
- cash unknown blocks BUY items
- buying power unknown blocks BUY items
- current positions unknown makes items review required
- Safety blocked items are blocked
- Safety review required items require review
- cash required above buying power blocks the item

## Approval Boundary

`OrderPlan` is History / Evidence and is not a Submit source.

`ApprovalArtifact` is History / Evidence and is not a Submit source.

Only an explicitly promoted and approval-linked `PendingOrderPlan` can become the future Submit target.

## Guardrail Confirmation

Phase13-S did not perform:

- Submit
- Broker order
- Broker API call
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

