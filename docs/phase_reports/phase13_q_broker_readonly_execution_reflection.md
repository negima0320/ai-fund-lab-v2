# Phase13-Q Broker ReadOnly Ingestion / Execution Reflection Skeleton

## Status

IMPLEMENTED_SKELETON

## Scope

Phase13-Q implements read-only Broker snapshot normalization and execution reflection skeletons.

Implemented:

- Broker ReadOnly snapshot models
- Broker ReadOnly normalizer skeleton
- Fill classification model
- Fill classifier skeleton
- Ledger projection skeleton
- Demo broker orders fallback policy
- Production broker orders fallback prohibition
- no side effect tests

Not implemented:

- Broker API connection
- Broker order submission
- Submit
- Ledger append transaction
- Asset state update transaction
- Notification send
- launchd / plist operation
- Backtest / Simulation execution

## Runtime Principles

Broker order snapshots are order state, not asset state.

Execution / position / cash grounding:

```text
BrokerExecutionSnapshot -> LedgerExecutionRecord
BrokerPositionSnapshot -> LedgerPositionRecord
BrokerCashSnapshot -> LedgerCashRecord
```

BrokerOrderSnapshot can project only to `LedgerOrderRecord`. It is not used to create `LedgerPositionRecord` or `CurrentAssetState`.

## Raw Broker Data

Snapshot models store hashed references only:

- `order_ref_hash`
- `execution_ref_hash`
- `position_ref_hash`
- `cash_ref_hash`
- `broker_ref_hash`

They do not store raw request, raw response, session, URL, account id, account number, or unhashed broker ids.

## Demo Fallback Policy

Broker orders fallback is allowed only when:

- mode is `demo`
- environment is `demo`
- fallback is explicitly requested

Fallback metadata is always:

```text
source=broker_orders_fallback
review_required=true
production_equivalent=false
```

Production broker orders fallback is not allowed.

## Guardrail Confirmation

Phase13-Q did not perform:

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
- Current Asset State update

