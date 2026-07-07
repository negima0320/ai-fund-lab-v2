# Phase13-O Persistent Ledger / Asset Runtime Skeleton

## Status

IMPLEMENTED_SKELETON

## Scope

Phase13-O implements the minimal Persistent Ledger / Asset Runtime skeleton.

Implemented:

- Ledger record dataclasses
- append-only record helper
- dedup helper
- Current Asset State model
- Asset State builder
- explicit-path `persistent_ledger/state.json` writer skeleton
- Asset Runtime single writer structure for Current Asset State
- Current State Reader compatibility test for generated `state.json`
- no side effect guard tests

Not implemented:

- Broker connection
- Broker order submission
- Broker execution ingestion
- Production ledger migration
- Existing artifact reads
- Existing persistent ledger mutation
- Existing demo ledger reads
- Submit
- Notification send
- launchd / plist operation
- Backtest / Simulation execution

## Responsibility Boundary

Ledger Runtime:

- owns append-only ledger record models
- owns dedup helper behavior
- does not write `persistent_ledger/state.json`

Asset Runtime:

- builds `CurrentAssetState` from position and cash ledger records
- is the skeleton single writer for `persistent_ledger/state.json`
- does not build asset state from orders only

## Asset State Rules

Current Asset State is built from position and cash state, not from orders.

Rules implemented:

- `positions + cash` can build confirmed asset state
- `positions=[] + cash` can build explicit confirmed empty candidate
- `positions=None` means positions unknown, not empty
- missing cash means cash and buying power unknown
- cash absence prevents confirmed `total_equity`
- `source=broker_orders_fallback` sets `review_required=true` and `production_equivalent=false`
- order-only construction raises an error

## Writer Skeleton

`write_current_asset_state(path, state)` requires an explicit path.

The writer:

- does not resolve latest artifacts
- does not read existing artifacts
- does not read `demo_ledger`
- does not write Production runtime paths in Phase13-O
- writes only the path passed by the caller

## Guardrail Confirmation

Phase13-O did not perform:

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

