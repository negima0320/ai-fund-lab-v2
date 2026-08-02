# Phase24-ID Execution Post-Fill Reconciliation and Aggregate Portfolio Constraint Root Cause Audit

## 1. Primary Judgment

`PHASE24_ID_EXECUTION_RECONCILIATION_REPAIRED_SHORT_VALIDATION_PASS_RUNTIME_RERUN_REQUIRED`

## 2. Executive Summary

Target run `runtime-test-historical-extended-smoke-20260801T195620733988Z` stopped on `2023-02-14` in Execution with `final_state=REVIEW_REQUIRED`, `reason=reconciliation findings=2`, `exit_code=20`.

The exact reconciliation findings are `CASH_MISMATCH` and `BUYING_POWER_MISMATCH`. They are produced by `run_execution_readonly_pipeline -> run_reconciliation -> check_broker_cash_vs_asset_state`. Position count was not one of the two findings.

## 3. Reviewed Evidence

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T195620733988Z/daily/2023-02-14/execution/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T195620733988Z/daily/2023-02-14/execution/fills.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T195620733988Z/daily/2023-02-14/submit/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T195620733988Z/daily/2023-02-14/strategy/runtime_planning.json`
- `.runtime/runtime_state/broker_readonly/2023-02-14/tachibana_snapshot.json`
- `.runtime/persistent_ledger/state.json`
- `configs/runtime_v2/capital_deployment.json`

## 4. Exact Reconciliation Findings

| Finding | Expected | Actual | Severity |
|---|---:|---:|---|
| CASH_MISMATCH | 0.0 | -143650.0 | REVIEW_REQUIRED |
| BUYING_POWER_MISMATCH | 0.0 | -143650.0 | REVIEW_REQUIRED |

Finding objects were not serialized in the execution manifest; only `reconcile_findings=2` and `reconcile_status=REVIEW_REQUIRED` were materialized. This is an observability gap, but the findings are exactly reproducible from producer inputs.

## 5. Cash Authority Audit

| Item | Value |
|---|---:|
| Pre-fill canonical cash | 355010.0 |
| Aggregate BUY notional | 533060.0 |
| Aggregate SELL notional | 34400.0 |
| Net cash effect | -498660.0 |
| Expected post-fill cash | -143650.0 |
| Historical snapshot cash_available | -143650.0 |
| Runtime projected cash | 0.0 |
| Cash difference | -143650.0 |

Negative cash is not a legitimate spot-cash state. The historical snapshot preserved the aggregate over-buy result, while runtime-owned projection clamped the raw negative value to zero and returned PASS before this repair.

## 6. Aggregate Constraint Audit

Pre-fill exposure was `665180.0` and active `max_exposure` is `850000.0`. Post-fill snapshot exposure is `1164240.0`. Pre-fill position count was `4` and post-fill position count is `7`, while active `max_positions` is `5`.

Planning/Submit had item-scoped feasibility, so each BUY could pass individually. The approved batch was not reserved sequentially across cash, buying_power, exposure, and position count before the broker boundary.

## 7. Order Reconstruction

| Symbol | Side | Qty | Fill | Notional | Cash Effect | Planning |
|---|---|---:|---:|---:|---:|---|
| 45860 | BUY | 800 | 223.0 | 178400.0 | -178400.0 | BUY_NEW |
| 54010 | BUY | 300 | 570.2 | 171060.0 | -171060.0 | BUY_NEW |
| 45940 | SELL | 200 | 172.0 | 34400.0 | 34400.0 | NO_ACTION |
| 93180 | BUY | 61200 | 3.0 | 183600.0 | -183600.0 | BUY_NEW |

## 8. Root Cause Matrix

Primary root cause: aggregate/sequential BUY cash/exposure/position reservation was missing before Submit boundary.

Secondary root cause: runtime-owned projection clamped negative cash to zero and marked projection PASS, turning a projection defect into reconciliation REVIEW_REQUIRED.

Not root cause: Corporate Action Guard, Opportunity Ranking, PM, Position Sizing policy, Strategy parameters.

## 9. Repair Summary

Updated Architecture, Strategy boundary, Roadmap, and added the Phase24-ID contract before implementation.

Implementation:

- Planning Submit Feasibility now reserves BUY cash, buying_power, exposure, and new position slots sequentially across the approved batch.
- Submit Guard now runs aggregate batch feasibility before adapter boundary.
- Submit Guard evidence now includes cash/exposure/position reservation values.
- Runtime-owned fill projection now returns REVIEW_REQUIRED on negative projected cash instead of clamping to zero and passing.

## 10. Safety Stage Audit

Execution manifest `SAFETY_MISSING` is not the direct halt reason. Submit used historical neutral safety authority PASS. The execution-stage safety marker is confusing observability and should be reported separately from direct execution reconciliation halt.

## 11. Validation

Short regression: PASS, 29 tests.

Runtime fresh-run/resume: not executed.

## 12. Recommended Next Task

Run operator historical extended smoke rerun for Phase24-ID and confirm the 2023-02-14 invalid aggregate batch is stopped before execution with materialized aggregate feasibility evidence.
