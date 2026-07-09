# Phase14-E49 Runtime v2 Demo Operation Rehearsal SELL Cleanup Cycle

## Summary

- phase: Phase14-E49
- objective: Sell Runtime-owned Demo positions through the regular Runtime v2 path and verify Broker -> Execution -> Current -> Report -> Notification.
- execution_status: NOT_EXECUTED
- reason: regular Runtime v2 CLI has no SELL planning job.
- runtime_changed: false
- new_runtime_module: false
- new_cli: false
- new_runtime_path: false
- fake_adapter: false
- sell_bypass: false
- current_direct_edit: false
- buy_executed: false
- sell_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- final_judgment: `LEVEL3_DEMO_OPERATION_SELL_REVIEW_REQUIRED`

## Decision

E49 was stopped before SELL planning or Broker write.

The user request requires:

- existing Runtime CLI only
- no new CLI
- no Runtime bypass
- no fake adapter
- no Current direct edit
- no test-only SELL path

Current Runtime v2 has a SELL planning component, but that component is not connected to the regular CLI operation entry.

Therefore, executing SELL by directly calling `run_sell_planning_pending_pipeline(...)` from an ad hoc Python command would bypass the required Runtime CLI entry contract. It would prove the component, not the Level3 regular operation path.

## Current State Before E49

Current SoT:

- path: `.runtime/persistent_ledger/state.json`
- source: `runtime_v2_runtime_owned_fill_projection`
- cash: `140500.0`
- buying_power: `140500.0`
- market_value: `2047500.0`
- total_equity: `2188000.0`
- positions_count: `5`

Current positions:

| Symbol | Quantity | Average Price | Market Value | Source |
| --- | ---: | ---: | ---: | --- |
| `6897` | 500 | 102 | 338000 | runtime_v2_runtime_owned_fill_projection |
| `4591` | 5000 | 101 | 410000 | runtime_v2_runtime_owned_fill_projection |
| `3926` | 1000 | 101 | 351000 | runtime_v2_runtime_owned_fill_projection |
| `4446` | 500 | 102 | 435500 | runtime_v2_runtime_owned_fill_projection |
| `4935` | 1500 | 101 | 513000 | runtime_v2_runtime_owned_fill_projection |

Pending before E49:

- state: `CONSUMED`
- pending_plan_id: `pending-order-plan-faa37c48f1867a67`
- target_session_date: `2026-07-09`
- items: 5 BUY items from E48

Runtime Report and Notification payload both show the same 5 Current positions.

## CLI Capability Audit

`src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` defines:

```python
ALLOWED_JOBS = ("daily_rehearsal", "morning", "submit", "execution", "market_refresh")
```

There is no supported CLI job for:

- `sell`
- `sell_planning`
- `sell_cleanup`
- `exit`
- `rebalance`

Existing CLI jobs:

| Job | Can produce SELL Pending? | Notes |
| --- | --- | --- |
| `market_refresh` | No | Market/feature refresh only. |
| `morning` | No | Calls BUY-oriented `run_morning_ai_planning_pending_pipeline`. |
| `submit` | Only submits existing Pending | Cannot generate SELL Pending. |
| `execution` | No | Broker ReadOnly / execution reflection only. |
| `daily_rehearsal` | No | Checkpoint/preflight path, not SELL planning. |

## SELL Component Audit

SELL component exists:

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- function: `run_sell_planning_pending_pipeline(...)`
- test coverage:
  - `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`

Component behavior:

- Current Position is the only SELL source.
- BUY candidates are not accepted as SELL source.
- SELL quantity above Current position is blocked.
- It can build SELL OrderPlan / Approval / Pending.

But it is not wired to:

- `run_daily_operation.py`
- launchd job design
- regular CLI operation entry

## Why E49 Cannot Proceed Safely

To execute the requested SELL cleanup, Runtime must first create SELL Pending. With the current CLI, there are only two possible approaches:

1. Directly call `run_sell_planning_pending_pipeline(...)` from an ad hoc script.
2. Add a new CLI job or connect SELL planning to an existing CLI job.

Both are disallowed in E49:

- Direct call would be Runtime bypass / not existing CLI only.
- Adding CLI job would be Runtime change / new operation entry.

Therefore no SELL Submit was executed.

## Flow Matrix

| Flow | Status | Reason |
| --- | --- | --- |
| Current SoT -> SELL Planning | NOT_CONNECTED | SELL component exists but no regular CLI job invokes it. |
| SELL Planning -> Pending | NOT_EXECUTED | Stopped before bypassing CLI. |
| Pending -> Approval | NOT_EXECUTED | No SELL Pending generated. |
| Approval -> Submit | NOT_EXECUTED | No SELL Pending available. |
| Submit -> Broker Accepted | NOT_EXECUTED | No Broker write performed. |
| Broker -> Execution | NOT_EXECUTED | No new SELL order. |
| Execution -> Current | NOT_EXECUTED | No SELL execution evidence. |
| Current -> Report | CURRENT_EXISTING_ONLY | Existing E48 Current remains visible. |
| Current -> Notification | CURRENT_EXISTING_ONLY | Existing E48 Current remains visible. |

## Required Fix Before SELL Level3

Next phase should connect SELL planning to the regular Runtime v2 operation entry.

Minimum design:

- Add or define a regular CLI job such as `--job sell_planning` or a defined sell cleanup operation.
- The job must call `run_sell_planning_pending_pipeline(...)` without bypass.
- It must use Current SoT as the only SELL source.
- It must write fixed Pending Current:
  - `.runtime/pending_order_plan/pending_order_plan.json`
- Submit job must then submit that Pending through the existing submit pipeline.
- Execution job must reflect fills and project Current through E47 path.

Important:

- This should not be Phase14-only.
- This should not be Demo-only.
- It should be part of the Runtime v2 operation entry contract.

## Prohibited Actions Check

- runtime_changed: false
- new_runtime_module: false
- new_cli: false
- new_runtime_path: false
- fake_adapter: false
- sell_bypass: false
- current_direct_edit: false
- buy_executed: false
- sell_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- raw_request_saved: false
- raw_response_saved: false
- secret_saved: false
- Phase9 runtime used: false
- Phase9 writer used: false

## Acceptance Matrix

| Acceptance | Result | Notes |
| --- | --- | --- |
| SELL Planning PASS | REVIEW_REQUIRED | No regular CLI job exists. |
| SELL Submit PASS | NOT_EXECUTED | Stopped before bypass. |
| Broker Accepted PASS | NOT_EXECUTED | No SELL Submit. |
| Execution PASS | NOT_EXECUTED | No SELL order. |
| Current update PASS | NOT_EXECUTED | No SELL execution. |
| Report PASS | CURRENT_EXISTING_ONLY | Existing E48 Current remains. |
| Notification Payload PASS | CURRENT_EXISTING_ONLY | Existing E48 payload remains. |
| Runtime-owned holdings=0 | NOT_ACHIEVED | SELL cleanup not executed. |
| Broker ReadOnly consistency | NOT_EXECUTED | No new SELL cleanup. |
| Prohibited actions | PASS | No forbidden action performed. |

## Final Judgment

`LEVEL3_DEMO_OPERATION_SELL_REVIEW_REQUIRED`

Root cause:

`SELL planning is implemented as a component but not connected to the regular Runtime v2 CLI operation entry.`
