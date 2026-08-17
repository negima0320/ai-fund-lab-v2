# Phase30-AK3R2B - Reserved-Notional-Aware Cash-Feasible BUY Batch Construction Repair

Task ID: `Phase30-AK3R2B`

Type: `FOCUSED_IMPLEMENTATION_REPAIR`

## Primary Judgment

```text
RESERVED_NOTIONAL_AWARE_BUY_BATCH_REPAIR_IMPLEMENTED = YES
CASH_FEASIBLE_BATCH_CONSTRUCTION_ACTION_EFFECTIVE = YES
```

Phase30-AK3R2B implemented the Phase30-AK3R2B0 approved contract in the
Production-common Strategy Runtime Planning consumer:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
```

The repair constructs the active Pending BUY batch using canonical Runtime
Planning order and canonical `reserved_notional` before approval and final
Submit verification. A BUY candidate that fails only because it cannot fit
remaining Current cash / buying_power is now deferred as:

```text
DEFERRED_INSUFFICIENT_RESERVED_CASH
```

and is not a member of the active atomic BUY batch. Later candidates continue
to be considered in the original canonical order.

## Implemented Contract

```text
CASH_FEASIBLE_BATCH_CONSTRUCTION_AUTHORITY =
  PLANNING_PENDING_BUY_BATCH_CONSTRUCTION_USING_CANONICAL_RESERVED_NOTIONAL_AND_CANONICAL_STRATEGY_PRIORITY

RESERVED_NOTIONAL_CANONICAL_PRODUCER =
  runtime_v2.order_reservation.resolve_order_cash_reservation

CANONICAL_BUY_PRIORITY_AUTHORITY =
  STRATEGY_RUNTIME_PLANNING_ORDER_DERIVED_FROM_PORTFOLIO_CONSTRUCTION_AND_POSITION_SIZING

CASH_FEASIBLE_BATCH_SELECTION_SEMANTIC =
  PRIORITY_ORDERED_RESERVED_NOTIONAL_SKIP_AND_CONTINUE_PRUNING
```

No new investment ranking, candidate score, cheap-lot ordering, knapsack,
backtracking, or notional maximization was introduced.

## Evidence Materialized

`order_plan.json` and result lineage now include:

```text
cash_feasible_buy_batch
```

Run-level evidence includes:

```text
starting_cash
starting_buying_power
candidate_buy_count
included_buy_count
cash_pruned_count
final_reserved_notional_total
remaining_reserved_cash
priority_order_preservation
```

Item-level evidence includes:

```text
symbol
pending_item_id
canonical_priority_index
executable_quantity
reservation_price
reserved_notional
cash_before_item
reserved_cash_before_item
remaining_cash_before_item
decision
reason
reserved_cash_after_item
source_submit_feasibility_status
source_violated_policy
```

## Sentinel Coverage

Implemented:

```text
tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py
```

Sentinels covered:

| Case | Result |
| --- | --- |
| All fit | PASS |
| One item does not fit | PASS |
| Later cheaper item fits after prune | PASS |
| Exact cash boundary | PASS |
| Non-cash authority failure | PASS, fail-closed preserved |
| AK2 one-lot fits | PASS |
| AK2 one-lot cash shortfall | PASS, no special priority |
| Submit final verification after pruned batch | PASS |

## Preservation

```text
SUBMIT_FINAL_CASH_FAIL_CLOSED_PRESERVED = YES
ATOMIC_BATCH_PROTECTION_PRESERVED = YES
PC_INVESTMENT_PRIORITY_PRESERVED = YES
PS_QUANTITY_AUTHORITY_PRESERVED = YES
AK2_ONE_LOT_AUTHORITY_PRESERVED = YES
AK3R1_SUBMIT_HANDOFF_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
BUY_ADD_BEHAVIOR_UNCHANGED = YES
```

Submit remains the final verifier. Non-cash authority failures remain in the
active batch and retain existing review / fail-closed behavior.

## Required Final Judgments

```text
RESERVED_NOTIONAL_AWARE_BUY_BATCH_REPAIR_IMPLEMENTED = YES
CASH_FEASIBLE_BATCH_CONSTRUCTION_ACTION_EFFECTIVE = YES
CANONICAL_BUY_PRIORITY_PRESERVED = YES
CASH_PRUNED_ITEM_SEMANTIC_IMPLEMENTED = YES
SKIP_AND_CONTINUE_ACTION_EFFECTIVE = YES
NEW_INVESTMENT_PRIORITY_CREATED = NO
NEW_BATCH_OPTIMIZATION_CREATED = NO
SUBMIT_FINAL_CASH_FAIL_CLOSED_PRESERVED = YES
ATOMIC_BATCH_PROTECTION_PRESERVED = YES
AK2_ONE_LOT_AUTHORITY_PRESERVED = YES
AK3R1_SUBMIT_HANDOFF_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
BUY_ADD_BEHAVIOR_UNCHANGED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r2b_pycache python3 -m pytest \
  tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py -q
7 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r2b_pycache python3 -m pytest \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
39 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r2b_pycache python3 -m pytest \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase26_step6_submit_guard_authority.py -q
31 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r2b_pycache python3 -m pytest \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/strategy/test_phase22_j_position_sizing.py -q
117 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r2b_pycache python3 -m pytest \
  tests/strategy/test_phase22_g_runtime_planning.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q
65 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_ak3r2b_pycache python3 -m compileall \
  src/ai_fund_lab_v2/runtime_v2 src/ai_fund_lab_v2/strategy
PASS
```

## Historical Runs

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Deliverables

```text
docs/phase_reports/phase30_ak3r2b_reserved_notional_aware_cash_feasible_buy_batch_construction_repair.md
reports/phase_reports/phase30_ak3r2b_reserved_notional_aware_cash_feasible_buy_batch_construction_repair.json
```

## Recommended Next Task

```text
Phase30-AK3R2C - User-Operated Fresh 5BD End-to-End BUY Batch / One-Lot Validation
```
