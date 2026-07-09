# Phase14-E46 Runtime v2 Execution -> Current Projection Audit

## Summary

- phase: Phase14-E46
- objective: Audit why Runtime v2 Execution PASS does not update Current SoT.
- scope: investigation only
- code_changed: false
- current_changed: false
- runtime_changed: false
- submit_executed: false
- sell_executed: false
- notification_sent: false
- launchd_changed: false
- final_judgment: `PHASE14E46_EXECUTION_CURRENT_ROOT_CAUSE_IDENTIFIED`

## Finding

The Execution -> Current data flow stops at:

`Ledger -> runtime_owned_fill_projection`

Execution ReadOnly writes broker evidence and execution-equivalent records to Ledger, but the regular execution job does not call `project_runtime_owned_fills_to_current(...)`. Therefore `persistent_ledger/state.json` remains at the demo initial Current state.

This is not caused by missing execution evidence. It is a projection connection gap.

## Evidence

Latest execution manifest:

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-execution-2026-07-09-20260709T004439.572155+0000.json`
- exit_code: `0`
- stage: `runtime_v2_execution_readonly_pipeline`
- status: `PASS`
- execution_acceptance_status: `PASS`
- execution_equivalent_count: `20`
- ledger_orders_appended: `20`
- ledger_executions_appended: `20`
- ledger_positions_appended: `11`
- ledger_cash_appended: `1`
- ledger_events_appended: `1`
- reconcile_status: `PASS_WITH_WARNINGS`
- asset_policy: `broker_position_cash_evidence_recorded_only`
- asset_current_written: `false`

Latest Current SoT:

- path: `.runtime/persistent_ledger/state.json`
- cash: `1000000.0`
- buying_power: `1000000.0`
- market_value: `0`
- total_equity: `1000000.0`
- positions_count: `0`
- source: `phase14e8_demo_operation_initial_state`

Latest ledger state:

- `.runtime/persistent_ledger/orders.jsonl`: `25` records
- `.runtime/persistent_ledger/executions.jsonl`: `20` records
- `.runtime/persistent_ledger/positions.jsonl`: `11` records
- `.runtime/persistent_ledger/cash.jsonl`: `2` records
- `.runtime/persistent_ledger/events.jsonl`: `2` records

Execution records:

- source: `runtime_v2_execution_readonly`
- record_type: `execution`
- execution_evidence_type: `execution_equivalent`
- sample fields:
  - symbol: `6897`
  - broker_issue_code: `6897`
  - side: `BUY`
  - quantity: `100.0`
  - filled_quantity: `100.0`
  - execution_status: `filled`
  - average_price: `102.0`
  - cash_effect: `10200.0`
  - detail_required: `false`
  - detail_status: `OPTIONAL_FAILED`

## Code Evidence

`src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py` explicitly states that Demo Broker cash/positions are recorded as ledger evidence but do not overwrite Current:

- Demo Broker cash/positions can reset independently.
- Demo mode records broker evidence in Ledger JSONL.
- It does not overwrite `persistent_ledger/state.json` from broker cash or positions.

The same function sets:

- `asset_policy = "broker_position_cash_evidence_recorded_only"`
- `asset_current_written = False`

It then returns `ExecutionReadOnlyPipelineResult(... asset_current_written=asset_current_written, asset_policy=asset_policy ...)`.

There is no call to:

- `project_runtime_owned_fills_to_current(...)`

inside the regular execution pipeline or Runtime v2 CLI execution path.

## E25 / E31 / E44 Consistency

E31:

- Defines `execution_equivalent` as canonical execution evidence when OrderList + Position + Cash are consistent and detail API is optional.
- This is working. `executions.jsonl` is not empty.

E25:

- Adds `runtime_owned_fill_projection`.
- It can project accepted Runtime-owned fills into fixed Current SoT.
- It deliberately excludes unrelated Demo broker positions and does not copy Demo broker 20M cash.

E44:

- Proves the normal Runtime path reaches Demo Submit, Broker ACCEPTED, Execution PASS, and execution-equivalent ledger records.
- It does not prove Current projection, because the normal execution job does not call E25 projection.

Therefore:

- E31 and E44 are consistent: execution evidence exists.
- E25 and E44 are not connected in the regular Runtime path.
- The observed Current SoT remaining at 1,000,000 cash / 0 positions is explained by this missing connection.

## Flow Matrix

| Flow | Status | Evidence | Reason |
| --- | --- | --- | --- |
| Broker OrderList -> Execution Acceptance | PASS | manifest execution_acceptance_status=`PASS` | OrderList + Position + Cash evidence accepted. |
| Execution Acceptance -> Ledger Orders | PASS | ledger_orders_appended=`20` | Execution job appends broker order evidence. |
| Execution Acceptance -> Ledger Executions | PASS | ledger_executions_appended=`20` | Execution-equivalent records are written. |
| Execution Acceptance -> Ledger Positions | PASS | ledger_positions_appended=`11` | Broker position evidence is written. |
| Execution Acceptance -> Ledger Cash | PASS | ledger_cash_appended=`1` | Broker cash/buying-power evidence is written. |
| Ledger -> runtime_owned_fill_projection | FAIL | no call site in execution pipeline / CLI | E25 projection exists but is not connected to regular execution job. |
| runtime_owned_fill_projection -> Current Writer | SKIP | projection not invoked | Current writer is available but not reached. |
| Current Writer -> state.json | SKIP | state source remains `phase14e8_demo_operation_initial_state` | No projection write occurred. |
| state.json -> Runtime/Public Report | PASS | report current_portfolio shows 1,000,000 cash / 0 positions | Report correctly reflects unchanged Current. |

## Root Cause

Root cause:

`runtime_owned_fill_projection` is implemented but not connected to the regular Runtime v2 execution job.

More specifically:

1. Execution ReadOnly pipeline writes order, position, cash, and execution-equivalent evidence to Ledger.
2. It intentionally avoids direct Broker cash/position copying into Current.
3. It sets `asset_current_written=false`.
4. It does not invoke the E25 runtime-owned projection that safely filters Runtime-owned symbols and computes Runtime-owned Current.
5. Report then reads unchanged `persistent_ledger/state.json`, so Current Portfolio stays cash=1,000,000 / positions=0.

This is a connection gap, not missing Broker evidence and not a Current writer failure.

## Policy Interpretation

`broker_position_cash_evidence_recorded_only` means:

- Broker evidence is trusted as evidence and recorded in Ledger.
- Broker Demo account-wide cash and unrelated positions are not copied directly to Current.
- This is correct for Demo capability because Demo broker cash/positions can reset.
- However, it should not prevent Runtime-owned accepted fills from being projected via E25's filtered projection.

Therefore Current update should not be implemented as "copy Broker positions/cash." It should be implemented as:

`accepted Runtime Submit records + execution_equivalent + matching Position evidence -> runtime_owned_fill_projection -> Current`

## Is This Design, Gap, or Regression?

Classification:

- Not a Broker evidence failure.
- Not a Current writer failure.
- Not a direct data corruption.
- Not a regression from E25 implementation itself.
- It is a regular Runtime path connection gap.

E25 proved the projection component. E46 shows it is not called by Execution.

## Acceptance Impact

For Level3 Demo Operation Rehearsal:

- If Level3 only requires Broker Submit / Execution evidence / Ledger / Report / Notification payload, E44 can pass.
- If Level3 means "BUY operation changes Runtime-owned Current Portfolio," Current projection must be required.

Recommended Level3 acceptance update:

- Execution PASS is not sufficient.
- BUY Level3 should require either:
  - Current projection PASS, or
  - explicit policy status explaining why Current projection was intentionally skipped.

Current E44/E45 result should be classified as:

- Broker/Execution evidence path: PASS
- Current projection path: NOT_CONNECTED

## Fix Direction

No code was changed in E46.

Recommended next phase:

1. Connect `project_runtime_owned_fills_to_current(...)` after successful execution acceptance and ledger append.
2. Use fixed Current path only.
3. Only project Runtime-owned accepted symbols.
4. Do not copy Demo broker cash.
5. Do not copy unrelated Demo broker positions.
6. Record projection result in execution manifest:
   - `runtime_owned_projection_status`
   - `runtime_owned_symbols`
   - `excluded_broker_position_symbols`
   - `asset_current_written`
   - `current_sot_before`
   - `current_sot_after` summary
7. If projection cannot run after execution PASS, mark REVIEW_REQUIRED rather than silently leaving Current unchanged.

## Prohibited Actions Check

- code_changed: false
- current_changed: false
- runtime_changed: false
- submit_executed: false
- sell_executed: false
- notification_sent: false
- launchd_changed: false
- current_direct_edit: false
- runtime_bypass: false
- fake_adapter: false
- new_runtime_path: false
- new_cli: false
- new_module: false

## Final Judgment

`PHASE14E46_EXECUTION_CURRENT_ROOT_CAUSE_IDENTIFIED`
