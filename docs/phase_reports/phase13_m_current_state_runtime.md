# Phase13-M Current State Runtime

## Status

IMPLEMENTED_CURRENT_STATE_READER

## Scope

Phase13-M implements Current State read, validation, and classification only.

Implemented:

- `src/ai_fund_lab_v2/runtime_v2/current_state/` package
- `CurrentStateReadResult` model
- fixed-path Current State Reader
- Missing / Stale / Unknown / Confirmed Empty / Invalid / Review Required classification
- Current Contract validation integration
- safety flags for missing / invalid / unknown Current State
- no History / Derived fallback tests

Not implemented:

- Current State write path
- Persistent Ledger update
- Pending promotion
- Approval
- Submit
- Broker connection
- Broker order submission
- Notification send
- launchd / plist operation
- Backtest / Simulation execution

## Current State Reader

The reader API is:

```python
read_current_state(
    *,
    mode: str,
    environment: str,
    object_type: str,
    base_dir: Path | None = None,
) -> CurrentStateReadResult
```

The reader uses `resolve_current_path()` from Phase13-L and reads only:

```text
.runtime/{mode}/...
```

The reader does not search:

- `order_plan/YYYY-MM-DD`
- `approval_artifact/YYYY-MM-DD`
- `reports/YYYY-MM-DD`
- `phase13` directories
- latest artifacts
- legacy runtime resolvers

## Classification

Classification values:

- `VALID`
- `MISSING`
- `STALE`
- `UNKNOWN`
- `CONFIRMED_EMPTY`
- `INVALID`
- `REVIEW_REQUIRED`

Safety behavior:

- missing Current State is not confirmed empty
- unknown Current State is not empty
- missing / invalid / unknown sets `review_required=true`
- missing / invalid / unknown sets positions, cash, and buying power unknown

`CONFIRMED_EMPTY` is allowed only for `persistent_ledger_state` when it is explicit and supported by confirmed cash, confirmed buying power, empty positions, and an allowed source.

## Guardrail Confirmation

Phase13-M did not perform:

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

