# Phase17-BV10 Historical SELL Execution Projection and Reconciliation Fix

## Executive Summary

Phase17-BV10 fixed the Historical SELL execution path exposed by:

- run_id: `runtime-test-historical-extended-smoke-20260716T085259299113Z`
- halt point: `2026-07-01:execution`
- exit code: `20`
- final state: `REVIEW_REQUIRED`
- reason: `reconciliation findings=7`

BV9 Submit quantity authority was functioning correctly. The remaining defect was in Execution normalization, ledger projection, Runtime-owned Current projection, and reconciliation.

Final judgment:

`PHASE17_BV10_HISTORICAL_SELL_EXECUTION_PROJECTION_RECONCILIATION_ACCEPTED`

Rerun status:

`FRESH_RERUN_SAFE`

The halted run is already partially mutated and remains:

`RESUME_UNSAFE`

## Root Cause

The target run had one accepted Historical SELL order for `70630` quantity `2500`, and Historical execution acceptance succeeded. However, the execution path still treated Historical synthetic execution evidence like a live broker ReadOnly bundle.

Exact defects:

1. `HistoricalExecutionSnapshotProvider` emitted positions only for BUY fills.
   - Full SELL produced `positions=[]`.
   - No position transition record was appended.
   - The sold position remained in Persistent Ledger state.

2. `readonly_pipeline` appended both:
   - broker detail execution projected from the Historical synthetic execution, and
   - execution-equivalent record.
   This produced `fill_count=2` and `ledger_executions_appended=2` for one logical Historical fill.

3. The execution-equivalent SELL record used missing position evidence as its price source.
   - For full liquidation, the post-SELL position is absent.
   - The equivalent record got `price=0` and `cash_effect=0`.
   - Runtime-owned cash projection could not increase cash by SELL proceeds.

4. `runtime_owned_fill_projection` projected active positions from latest position ledger snapshots only.
   - It did not apply canonical SELL fills to reduce or remove Runtime-owned positions in Historical mode.

5. Reconciliation required raw broker execution ledger evidence even when a canonical execution-equivalent record already represented the Historical simulated fill.

## Affected Call Graph

1. Historical Submit accepted order
2. `HistoricalExecutionSnapshotProvider`
3. `normalize_broker_readonly_payload`
4. `project_order_to_ledger_record`
5. `project_execution_to_ledger_record`
6. `_execution_equivalent_records`
7. `_historical_position_transition_records`
8. `_append_ledger_records`
9. `project_runtime_owned_fills_to_current`
10. `apply_current_projection_to_runtime_state`
11. `run_reconciliation`

## Fix

Changed files:

- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/reconcile/checks.py`
- `tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py`

Key behavior after fix:

- Historical snapshot provider projects post-fill active positions:
  - BUY creates/updates active position.
  - partial SELL leaves remaining active quantity.
  - full SELL removes active position.
- Historical execution ledger appends one canonical execution-equivalent logical fill.
- Historical raw synthetic broker execution remains reconciliation authority but is not duplicated into the ledger as a second logical fill.
- Historical SELL position transition records are appended when needed, including quantity `0` for full liquidation.
- Runtime-owned projection applies canonical Historical BUY/SELL fills to compute active quantity.
- Demo/Production projection behavior remains broker-position snapshot based.
- Duplicate Historical execution invocation is idempotent.
- Reconciliation accepts canonical execution-equivalent as the ledger representation of a Historical broker execution authority.

## Before / After

Before:

- `fill_count=2`
- `ledger_executions_appended=2`
- `ledger_positions_appended=0`
- `ledger_cash_appended=0` for the target execution day
- `70630` remained active with quantity `2500`
- `reconcile_status=REVIEW_REQUIRED`

After:

- one logical Historical fill
- full SELL removes active position
- partial SELL leaves remaining quantity
- cash increases exactly once
- duplicate execution appends no duplicate order/execution/position/cash records
- reconciliation passes only when ledger and Current projection agree

## Historical Scope

Historical-specific behavior is explicitly scoped to:

- `mode == "historical"`
- `HistoricalExecutionSnapshotProvider`
- `broker_environment == "historical_simulated"`
- `production_equivalent=false`
- `broker_write=false`

Demo and Production continue to use their existing broker execution and position evidence contracts.

## Verification

Targeted BV10:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py
4 passed
```

Related regression:

```text
PYTHONPATH=src python3 -m pytest -q ...execution/submit/projection/reconciliation related set
38 passed
```

Static checks:

```text
py_compile PASS
git diff --check PASS
```

Full runtime_v2:

```text
922 passed, 5 failed
```

The five remaining failures are the known non-BV10 Sell Planning PM fixture residuals already present before this phase. The BV10-introduced `phase15bx` idempotency regression was fixed and now passes.

## Prohibited Operations Confirmation

Not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run edit
- `.runtime` manual edit
- Persistent Ledger manual edit
- Pending manual edit
- broker write
- J-Quants API fetch
- external notification

## Rerun Guidance

The target halted run is partially mutated and must not be used as acceptance evidence via resume.

Use a fresh operator-controlled lifecycle:

1. close halted run
2. reset clean baseline
3. create fresh plan
4. start fresh run

`FRESH_RERUN_SAFE`
