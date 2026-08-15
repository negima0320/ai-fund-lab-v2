# Phase29-L21T-X Historical Execution Reconciliation Authority Root-Cause & Repair

## Scope

IMPLEMENTATION + FOCUSED REGRESSION.

Codex did not run fresh-run, resume-run, scoped recovery, replay, long Historical
validation, manual Pending approval, or target runtime mutation.

Target run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Target day:

```text
2023-06-23
```

## Primary Judgment

`PHASE29_L21T_X_HISTORICAL_EXECUTION_RECONCILIATION_AUTHORITY_REPAIRED_FOCUSED_REGRESSION_PASS`

Required judgments:

```text
ROOT_CAUSE_CONFIRMED = YES
EXECUTION_COMMIT_VALID = YES
CURRENT_APPLY_VALID = YES
PENDING_CONSUMED_VALID = YES
RECONCILIATION_AUTHORITY_DEFECT_CONFIRMED = YES
CASH_AVAILABLE_NORMALIZATION_REPAIRED = YES
MICRO_FLOAT_MONEY_TOLERANCE_ADDED = YES
REAL_CASH_MISMATCH_FAIL_CLOSED_PRESERVED = YES
ORDER_EXECUTION_POSITION_QUANTITY_PROTECTION_PRESERVED = YES
Q2_TRANSACTIONALITY_PRESERVED = YES
HISTORICAL_SPECIFIC_WORKAROUND_ADDED = NO
TARGET_RUNTIME_MUTATED_BY_CODEX = NO
DIRECT_RESUME_SAFE = YES_AFTER_L21T_X_PATCH_DRY_RUN_FIRST
RECOVERY_REQUIRED = NO
```

## Read-Only Evidence

Run state:

```text
status = HALT
next_job = 2023-06-23:execution
halted_at.job = execution
halted_at.exit_code = 20
reason = reconciliation findings=2
```

Execution stage:

```text
orders_count = 3
executions_count = 3
fill_count = 3
ledger_orders_appended = 3
ledger_executions_appended = 3
ledger_positions_appended = 8
ledger_cash_appended = 1
persistent_commit_completed = true
current_apply_status = APPLIED
current_apply_reason = current projection applied to runtime state
pre_commit_cash_feasibility_status = PASS
execution_acceptance_status = PASS
reconcile_status = REVIEW_REQUIRED
reconcile_findings = 2
```

Current asset state after execution:

```text
cash = 129889.99999999999
buying_power = 129889.99999999999
market_value = 947170.0
total_equity = 1077060.0
position_count = 8
```

Historical broker snapshot cash payload:

```json
{
  "cash_ref": "historical-cash-2023-06-23",
  "cash_available": "129890.0",
  "buying_power": "129890.0",
  "currency": "JPY"
}
```

## Root Cause

The Reconciliation findings were not caused by Submit, Execution acceptance,
Pending consumption, Current projection, or transaction commit.

The defect was in Broker ReadOnly cash normalization:

```text
Broker payload field present: cash_available = 129890.0
Normalizer field consumed: cash
Normalized broker cash before repair = 0.0
```

That invalid `broker_cash.cash = 0.0` produced:

```text
CASH_MISMATCH
TOTAL_EQUITY_MISMATCH
```

There was also a harmless floating-point representation difference after
runtime-owned projection:

```text
Current cash = 129889.99999999999
Broker cash_available = 129890.0
difference = -1.4551915228366852e-11
```

This is below any meaningful JPY amount and should not be a reconciliation
finding.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/normalizer.py`
- `src/ai_fund_lab_v2/runtime_v2/reconcile/checks.py`
- `tests/runtime_v2/test_phase13_q_broker_readonly_normalizer.py`
- `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
- `docs/phase_reports/phase29_l21t_x_historical_execution_reconciliation_authority_root_cause_and_repair.md`

## Authority Before / After

Before:

```text
Broker cash normalization:
  cash = payload.cash or 0
  buying_power = payload.buying_power or 0

Reconciliation money comparison:
  exact float equality
```

After:

```text
Broker cash normalization:
  cash = payload.cash if present else payload.cash_available if present else 0
  buying_power = payload.buying_power or 0

Reconciliation money comparison:
  cash / buying_power / market_value / total_equity use micro-yen tolerance
  tolerance = 0.000001
```

Quantity, order status, execution identity, execution price, missing broker
evidence, missing ledger evidence, and structural fail-closed checks remain
unchanged.

## 2023-06-23 Recalculation

Codex ran a read-only recalculation using the existing target snapshot and
Current state after the patch.  It did not invoke the execution pipeline and did
not write to the target runtime.

Result:

```json
{
  "broker_cash": 129890.0,
  "broker_buying_power": 129890.0,
  "asset_cash": 129889.99999999999,
  "asset_buying_power": 129889.99999999999,
  "finding_count": 0,
  "findings": []
}
```

Expected execution result after user-run resume:

```text
reconcile_status = PASS
reconcile_findings = 0
execution final_state = COMPLETED/PASS path
```

## Regression Results

Focused L21T-X / reconciliation:

```bash
python3 -m pytest \
  tests/runtime_v2/test_phase13_q_broker_readonly_normalizer.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  -k 'l21t_x or normalizer or reconciliation'
```

Result:

```text
8 passed
```

Reconciliation / normalizer focused suite:

```bash
python3 -m pytest \
  tests/runtime_v2/test_phase13_q_broker_readonly_normalizer.py \
  tests/runtime_v2/test_phase13_q_broker_readonly_models.py \
  tests/runtime_v2/test_phase13_r_reconcile_positions_vs_asset.py \
  tests/runtime_v2/test_phase13_r_reconcile_orders_vs_executions.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py
```

Result:

```text
38 passed
```

Broad focused Runtime suite:

```bash
python3 -m pytest \
  tests/runtime_v2/test_phase13_q_broker_readonly_normalizer.py \
  tests/runtime_v2/test_phase13_r_reconcile_positions_vs_asset.py \
  tests/runtime_v2/test_phase13_r_reconcile_orders_vs_executions.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
```

Result:

```text
165 passed
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-l21t-x-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/broker_readonly/normalizer.py \
  src/ai_fund_lab_v2/runtime_v2/reconcile/checks.py \
  tests/runtime_v2/test_phase13_q_broker_readonly_normalizer.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py
```

Result:

```text
PASS
```

Whitespace:

```bash
git diff --check
```

Result:

```text
PASS
```

## Safety Preservation

Q2 transactionality:

```text
PRESERVED
```

No execution transaction commit logic was relaxed.  The repair happens only in
read-only broker cash normalization and post-commit reconciliation comparison.

Negative cash protection:

```text
PRESERVED
```

Pre-commit cash feasibility is unchanged.

Real reconciliation mismatch protection:

```text
PRESERVED
```

The negative fixture with a 0.01 JPY mismatch still produces:

```text
CASH_MISMATCH
BUYING_POWER_MISMATCH
TOTAL_EQUITY_MISMATCH
```

Order/execution/position authority:

```text
PRESERVED
```

The repair does not change order, execution, quantity, price, missing evidence,
or pending-vs-ledger checks.

## Resume / Recovery

```text
RECOVERY_REQUIRED = NO
DIRECT_RESUME_SAFE = YES_AFTER_L21T_X_PATCH_DRY_RUN_FIRST
```

The target day already committed Ledger and applied Current.  The execution
pipeline has dedup protection for ledger appends and Current apply can return
`NOOP_ALREADY_APPLIED` when the same current hash and execution references are
already active.  However, operator should still start with dry-run.

Recommended operator command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T212155604711Z \
  --dry-run \
  --json
```

If dry-run is acceptable, run the same command with:

```text
--confirm --yes-i-understand-this-mutates-trading-state --json
```

## Next Step

After user-run resume, inspect:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T212155604711Z/daily/2023-06-23/execution/runtime_manifest.json
```

Expected:

```text
reconcile_status = PASS
reconcile_findings = 0
final_state no longer REVIEW_REQUIRED from reconciliation findings
```
