# Phase29-L7 SELL Quantity-Contract Materialization Repair

## Status

COMPLETE

NARROW PRODUCTION-COMMON REPAIR COMPLETE

SHORT REGRESSION PASS

NO CONFIG CHANGE

NO SCHEMA CHANGE

NO RUNTIME / PENDING / LEDGER MUTATION

NO HISTORICAL EXECUTION

## Primary Judgment

PHASE29_L7_SELL_QUANTITY_CONTRACT_MATERIALIZATION_REPAIRED_SHORT_REGRESSION_PASS_FRESH_977BD_RETRY_READY

## Root Cause Reproduced

L6 root cause was reproduced as a common planner quantity materialization
defect:

```text
symbol = 76920
existing pending SELL quantity = 1000
quantity_contract.final_sell_quantity = 1000
old OrderPlanItem.quantity = 900
cause = notional / price recomputation in common build_order_plan
```

D3 reconciliation was not the defect. It correctly compared pending SELL item
quantity to new SELL item quantity and failed closed on 1000 versus 900.

## Implementation

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/planning/planner.py
tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py
```

For SELL items whose resolved quantity contract has source decision `REDUCE` or
`EXIT`, `OrderPlanItem.quantity` now consumes:

```text
quantity_contract.final_sell_quantity
```

It no longer recalculates that resolved SELL quantity from
`allocated_amount / estimated_price`.

BUY remains on the existing lot-rounding path. ADD, Strategy, PM, Position
Sizing, Safety, Pending composition, Submit, and Execution semantics were not
changed.

## Fail-Closed Guard

The planner now fail-closes contract-required SELL items when:

```text
SELL_ITEM_QUANTITY_CONTRACT_MISSING
SELL_ITEM_QUANTITY_CONTRACT_MISMATCH
```

The existing sell-more-than-owned protection is also preserved.

## 76920 Result

```text
old item quantity = 900
authoritative final_sell_quantity = 1000
new item quantity after repair = 1000
```

If the old halted run's existing pending 1000-share SELL is compared with the
new post-repair SELL item, D3 sees same economic quantity and can preserve the
existing pending item. Genuine different-quantity SELL conflicts still remain
`REVIEW_REQUIRED`.

## Regression

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py
```

```text
10 passed in 0.20s
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py
```

```text
10 passed in 0.89s
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase13_s_order_plan_builder.py tests/runtime_v2/test_phase13_s_planning_to_pending_integration.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
```

```text
25 passed in 0.57s
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase29_l5_raw_ohlcv_materialization.py tests/runtime_v2/test_phase29_l4_b_authority_materialization.py tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py
```

```text
21 passed in 25.93s
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/strategy/test_phase22_i_dynamic_cash_exposure.py tests/strategy/test_phase22_j_position_sizing.py
```

```text
97 passed in 2.83s
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
```

```text
85 passed in 1.22s
```

Compile passed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/planner.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/pending/composition.py
```

## Resume / Fresh Decision

The halted long-horizon run completed 39 business days before this production
source repair. Resume is therefore not allowed.

```text
Resume Allowed = NO
Fresh-run Required = YES
```

Exact abandon command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py abandon --profile historical-smoke --run-id runtime-test-historical-smoke-20260810T154347268066Z --reason phase29_l7_source_changed_fresh_run_required --confirm --yes-i-understand-this-mutates-trading-state
```

Exact fresh 977BD command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --date-from 2022-08-10 --date-to 2026-08-09 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

## Evidence

```text
reports/phase29_l7_sell_quantity_contract_materialization_repair/
```
