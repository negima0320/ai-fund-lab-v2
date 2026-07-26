# Phase20-P: Summarize REDUCE Lifecycle Consistency Contract Correction

## 1. Executive Summary

Phase20-P corrected `summarize` Lifecycle Consistency semantics for PM `REDUCE`.

The previous check required:

```text
pm_reduce_count == reduce_sell_plan_count
```

That contradicted the Phase20-M REDUCE Execution Feasibility Contract, where a valid REDUCE may terminate as an approved non-executable no-order outcome below the minimum tradable quantity.

Final judgment:

```text
PHASE20_P_SUMMARIZE_ACCEPTANCE_PASS
```

## 2. Scope and Non-goals

Scope was limited to Runtime Test `summarize` classification, Lifecycle Consistency output, operator documentation, and targeted regression tests.

No Runtime execution logic, PM logic, Sell Planning logic, REDUCE ratio, minimum tradable quantity, Broker behavior, AI behavior, Opportunity behavior, Risk behavior, Capital Allocation behavior, Accepted Generation, Training, Calibration, Validation, long Historical run, or target run evidence was changed.

## 3. Target Run

```text
run_id = runtime-test-historical-extended-smoke-20260722T082906704807Z
status = COMPLETED
final_judgment = PASS
business_days = 20
completed range = 2026-06-15 to 2026-07-10
```

Before correction:

```text
summarize --scope full exit_code = 10
runtime_judgment = REVIEW_REQUIRED
finding = LIFECYCLE_CONSISTENCY_REVIEW_REQUIRED
PM_REDUCE_TO_PARTIAL_SELL_PLAN = false
```

## 4. Evidence Confirmation

PM REDUCE decisions:

```text
pm_reduce_count = 10
```

Executable REDUCE SELL Plans:

```text
2026-06-16 66590 quantity=700
2026-06-17 50310 quantity=100
2026-06-17 66590 quantity=500
2026-06-19 66590 quantity=400
2026-07-03 67400 quantity=1000
2026-07-09 67400 quantity=600
```

Approved non-executable terminal REDUCE evidence:

```text
2026-06-18 50310
2026-07-02 43780
2026-07-03 43780
2026-07-06 43780
```

Each non-executable terminal item was confirmed in `.runtime/runtime_state/sell_pipeline/<DATE>/order_plan.json` under `non_executable_sell_decisions` with:

```text
execution_feasibility_status = NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY
reason = REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY
status = NOT_EXECUTABLE
effective_action = NO_SELL_ORDER
pending_order_generated = false
runtime_continuation_status = PASS
position_lifecycle_event = REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY
final_sell_quantity = 0
rounded_executable_quantity = 0
position_quantity_after = position_quantity_before
```

## 5. Corrected Lifecycle Contract

Formal REDUCE consistency:

```text
pm_reduce_count
=
executable_reduce_sell_plan_count
+
non_executable_reduce_terminal_count
```

Decision-level classifications:

```text
EXECUTABLE_WITH_SELL_PLAN
NON_EXECUTABLE_TERMINAL
UNRESOLVED
CONFLICTING
```

The check now passes only when each PM REDUCE resolves to exactly one executable SELL Plan or exactly one approved non-executable terminal outcome.

## 6. Review-required Cases

The corrected implementation keeps `REVIEW_REQUIRED` for:

```text
REDUCE with no SELL Plan and no terminal evidence
REDUCE with both SELL Plan and terminal evidence
multiple compatible SELL Plans
multiple compatible terminal outcomes
invalid terminal reason
invalid execution feasibility status
pending order generated for non-executable REDUCE
non-executable REDUCE with position quantity mutation
non-zero final sell quantity
non-zero rounded executable quantity
missing Current / Ledger / Pending consistency checks
existing EXIT / Submit / Execution consistency failures
```

## 7. Implementation Changes

Updated `scripts/runtime_test.py`:

- Normalizes PM decision records across legacy Runtime-root fields and Phase20-J run-scoped observability fields.
- Reads `non_executable_sell_decisions` from sell pipeline order plans.
- Adds non-executable REDUCE terminal summary fields.
- Classifies each PM REDUCE decision into a formal lifecycle outcome.
- Updates `PM_REDUCE_TO_PARTIAL_SELL_PLAN` semantics.
- Adds REDUCE lifecycle counts to human output.

Added / updated tests in `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`.

Updated `docs/03_operations/runtime_test_command_guide.md`.

## 8. Added Summary Fields

Lifecycle Consistency now includes:

```text
pm_reduce_count
executable_reduce_sell_plan_count
non_executable_reduce_terminal_count
unresolved_reduce_count
conflicting_reduce_count
non_executable_reduce_reason_distribution
reduce_lifecycle_outcome_distribution
reduce_lifecycle_items
non_executable_reduce_items
unresolved_reduce_items
conflicting_reduce_items
```

Existing top-level fields remain additive-compatible.

## 9. Target Run Acceptance

Command:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_p_pycache python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-extended-smoke-20260722T082906704807Z --scope full --json
```

Result:

```text
process_returncode = 0
status = PASS
runtime_judgment = PASS
final_judgment = PASS
exit_code = 0
Lifecycle Consistency = PASS
pm_reduce_count = 10
executable_reduce_sell_plan_count = 6
non_executable_reduce_terminal_count = 4
unresolved_reduce_count = 0
conflicting_reduce_count = 0
non_executable_reduce_reason_distribution = {"REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY": 4}
reduce_lifecycle_outcome_distribution = {"EXECUTABLE_WITH_SELL_PLAN": 6, "NON_EXECUTABLE_TERMINAL": 4}
findings = []
```

Performance remains an observation, not a Runtime lifecycle failure:

```text
final_equity = 913300.0
total_return_amount = -86700.0
total_return_percent = -8.67
performance_judgment = NEGATIVE_RETURN_OBSERVED
```

## 10. Validation

Short validation executed:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_p_pycache python3 -m pytest -q tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_p_pycache python3 -m pytest -q tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_p_pycache python3 -m pytest -q tests/runtime_v2/test_phase20_j_performance_observability.py tests/runtime_v2/test_phase20_k_performance_observability_consumer.py tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_p_pycache python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-extended-smoke-20260722T082906704807Z --scope full --json
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_p_pycache python3 scripts/runtime_test.py summarize --run-id runtime-test-historical-extended-smoke-20260722T082906704807Z --scope full
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_p_pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
python3 -m json.tool reports/phase_reports/phase20_p_summarize_reduce_lifecycle_consistency_contract_correction.json >/dev/null
git diff --check
```

Result:

```text
18 passed
29 passed
8 passed
target summarize acceptance PASS
target summarize human PASS
py_compile PASS
json validation PASS
git diff --check PASS
```

Long Historical, Broker, Training, Calibration, Validation, and Full Backtest were not executed.

## 11. Final Judgment

```text
PHASE20_P_SUMMARIZE_ACCEPTANCE_PASS
```
