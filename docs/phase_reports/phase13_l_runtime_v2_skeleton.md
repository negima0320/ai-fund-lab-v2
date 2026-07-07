# Phase13-L Runtime v2 Skeleton / Path Resolver / Schema Validator

## Status

IMPLEMENTED_SKELETON

## Scope

Phase13-L starts the minimal Runtime v2 implementation foundation only.

Implemented:

- `src/ai_fund_lab_v2/runtime_v2/` package skeleton
- mode / environment required path resolver
- Current State Contract metadata for the 9 Runtime v2 Current Objects
- pure validator skeleton for JSON object and JSONL record payloads
- architecture tests for path resolution, contract metadata, and legacy workflow import guard

Not implemented:

- Runtime execution workflow
- Submit Runtime
- Broker connection
- Broker order submission
- Notification send
- launchd / plist operation
- Backtest / Simulation execution

## Files Added

Implementation:

- `src/ai_fund_lab_v2/runtime_v2/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/storage/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/contracts/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/contracts/current_state_contracts.py`
- `src/ai_fund_lab_v2/runtime_v2/contracts/validation.py`

Tests:

- `tests/runtime_v2/test_phase13_l_path_resolver.py`
- `tests/runtime_v2/test_phase13_l_current_state_contracts.py`
- `tests/runtime_v2/test_phase13_l_no_legacy_runtime_import.py`

Report:

- `reports/phase_reports/phase13_l_runtime_v2_skeleton.json`

## Path Resolver

The resolver requires all of:

- `mode`
- `environment`
- `object_type`

Supported `mode` values:

- `production`
- `demo`
- `simulation`
- `backtest`

Supported `environment` values:

- `production`
- `demo`
- `simulation`
- `backtest`

There is no default production fallback. Current paths resolve under:

```text
.runtime/{mode}/
```

Current object mappings:

```text
runtime_state -> runtime_state/current_state.json
pending_order_plan -> pending_order_plan/pending_order_plan.json
persistent_ledger_state -> persistent_ledger/state.json
persistent_ledger_orders -> persistent_ledger/orders.jsonl
persistent_ledger_executions -> persistent_ledger/executions.jsonl
persistent_ledger_positions -> persistent_ledger/positions.jsonl
persistent_ledger_cash_history -> persistent_ledger/cash_history.jsonl
persistent_ledger_events -> persistent_ledger/events.jsonl
notification_delivery_ledger -> notification_delivery/delivery_ledger.jsonl
```

Current path resolution does not search date directories, phase directories, or latest artifacts.

## Current State Contracts

The following 9 Current Object contracts are defined:

- `runtime_state`
- `pending_order_plan`
- `persistent_ledger_state`
- `persistent_ledger_orders`
- `persistent_ledger_executions`
- `persistent_ledger_positions`
- `persistent_ledger_cash_history`
- `persistent_ledger_events`
- `notification_delivery_ledger`

Each contract defines:

- contract name
- path object type
- file kind: `json` or `jsonl`
- required top-level field candidates
- `append_only`
- `snapshot`
- owner component
- writer components
- reader components

## Validator Skeleton

The validator is intentionally pure and payload-based.

Implemented functions:

- `validate_required_fields(payload, required_fields)`
- `validate_json_object(payload, object_type)`
- `validate_jsonl_record(payload, object_type)`

The validator does not:

- read existing artifacts
- connect to Broker
- submit orders
- send notifications
- handle raw request / raw response / secrets
- inherit existing Runtime validators

## Guardrail Confirmation

Phase13-L did not perform:

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

