# Phase13-N Runtime State Machine / Orchestrator Skeleton

## Status

IMPLEMENTED_SKELETON

## Scope

Phase13-N implements the Runtime v2 State Machine and Orchestrator skeleton only.

Implemented:

- `RuntimeState` enum
- `RuntimeTransition` model
- allowed transition table
- transition validation
- invalid transition detection
- `RuntimeRunRequest`
- `RuntimeRunResult`
- side-effect-free `RuntimeOrchestrator.run_preflight`
- Current State Runtime connection for preflight
- no side effect architecture tests

Not implemented:

- Market Refresh execution
- Feature Refresh execution
- AI inference execution
- Daily Plan creation
- Pending promotion
- Approval workflow
- Submit
- Broker connection
- Broker order submission
- Ledger update
- Report generation
- Notification send
- launchd / plist operation
- Backtest / Simulation execution

## Runtime State Machine

Runtime states:

- `IDLE`
- `MARKET_DATA_READY`
- `FEATURE_READY`
- `CURRENT_STATE_LOADED`
- `AI_INFERENCE_DONE`
- `DAILY_PLAN_CREATED`
- `PENDING_PROMOTED`
- `APPROVAL_PENDING`
- `APPROVED`
- `SUBMITTING`
- `SUBMITTED`
- `POST_SEND_UNKNOWN`
- `MONITORING_FILL`
- `LEDGER_UPDATED`
- `RECONCILED`
- `REPORT_READY`
- `REVIEW_REQUIRED`
- `BLOCKED`
- `HALT`

`CONSUMED` is intentionally not a `RuntimeState`. It remains a Pending Order Plan lifecycle state.

Forbidden transitions include:

- `POST_SEND_UNKNOWN -> SUBMITTING`
- `SUBMITTED -> SUBMITTING`
- `IDLE -> SUBMITTING`
- `CURRENT_STATE_LOADED -> SUBMITTING`
- `REPORT_READY -> SUBMITTING`

Transitions involving `SUBMITTING`, `SUBMITTED`, or `POST_SEND_UNKNOWN` are marked as side-effect boundaries.

## Orchestrator Skeleton

`run_preflight` performs only:

- request validation
- fixed-path Current State reads
- persistent ledger state classification
- safe transition selection

`run_preflight` returns `side_effect_executed=false` in all cases.

Missing / invalid / unknown `persistent_ledger_state` causes `REVIEW_REQUIRED`.

Valid minimal `persistent_ledger_state` reaches `CURRENT_STATE_LOADED` through preflight marker transitions:

```text
IDLE -> MARKET_DATA_READY -> FEATURE_READY -> CURRENT_STATE_LOADED
```

These are markers only. Market refresh and feature refresh are not executed in Phase13-N.

## Guardrail Confirmation

Phase13-N did not perform:

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

