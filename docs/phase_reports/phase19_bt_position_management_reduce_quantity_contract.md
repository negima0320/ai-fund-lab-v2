# Phase19-BT Position Management REDUCE Quantity Contract

- Phase: `Phase19-BT`
- Judgment: `PHASE19_BT_POSITION_MANAGEMENT_REDUCE_QUANTITY_CONTRACT_COMPLETE`
- 20BD Historical Smoke: `PHASE19_BT_20BD_HISTORICAL_SMOKE_PASS`
- Primary run: `runtime-test-historical-smoke-20260721T120911954822Z`
- JSON evidence: `reports/phase_reports/phase19_bt_position_management_reduce_quantity_contract.json`

## Executive Summary

Phase19-BT implemented the missing Production-common contract that converts Position Management `REDUCE` decisions into partial SELL orders.

Position Management now emits `REDUCE` intent plus `reduce_intensity`; it does not select broker-final quantity. Sell Planning computes the partial SELL quantity from Current, sellable-quantity evidence, tradable unit, and fail-closed constraints, then carries `quantity_contract` evidence through Order Plan and Pending Order Plan. Submit Guard still independently validates sell quantity before broker submit.

No PM thresholds, EXIT thresholds, Opportunity score scaling, BUY ranking, or BUY policy were changed.

## Root Cause

Phase19-BS found 4 `REDUCE` decisions, but all stopped at:

```text
REVIEW_REQUIRED_REDUCE_QUANTITY_CONTRACT_MISSING
```

The root cause was a Contract gap: Runtime had PM `REDUCE` intent but no accepted quantity contract for converting that intent into a partial SELL order.

During BT validation, a secondary Runtime defect was exposed in Historical simulated broker availability: filled execution-equivalent order records in `persistent_ledger/orders.jsonl` were counted as open SELL orders, causing restricted quantity to be overstated after SELL execution. This could produce false `REVIEW_REQUIRED_EXIT_SELLABLE_QUANTITY_ZERO` or Submit Guard available-quantity failures. The fix was to count only unresolved submitted SELL orders and exclude filled execution-equivalent order records. The same open-order interpretation is now applied in Sell Planning and Submit Guard.

## Classification

| Area | Judgment | Evidence |
|---|---|---|
| Original BS REDUCE stop | `Contract mismatch / missing contract` | PM emitted REDUCE but Runtime had no quantity contract. |
| PM score policy | `No defect` | No threshold or scoring change was required. |
| BUY / Opportunity policy | `No defect` | No Opportunity score, ranking, or BUY policy change was made. |
| Historical broker availability duplicate count | `Runtime defect fixed` | Filled execution-equivalent order records are no longer treated as open SELL orders. |
| Production commonness | `PASS` | Shared PM, Sell Planning, Pending, Submit, Execution, Ledger, and Current paths are used across modes. |

## Implemented Contract

New architecture contract:

```text
docs/02_architecture/position_management_reduce_quantity_contract.md
```

Runtime contract version:

```text
runtime_v2_pm_reduce_quantity_v1
```

Intensity mapping:

| Intensity | Ratio |
|---|---:|
| `LIGHT` | 0.25 |
| `MEDIUM` | 0.33 |
| `STRONG` | 0.50 |

Sell Planning formula:

```text
effective_sellable_quantity = min(position_quantity_before, sellable_quantity)
raw_reduce_quantity = effective_sellable_quantity * target_reduce_ratio
rounded_reduce_quantity = floor(raw_reduce_quantity / tradable_unit) * tradable_unit
final_sell_quantity = rounded_reduce_quantity
expected_remaining_quantity = position_quantity_before - final_sell_quantity
```

Default tradable unit is `100` shares. `REDUCE` must remain partial and must not silently become `EXIT`.

## Runtime Data Flow

```text
PM Decision Artifact
-> load_sell_exit_decisions_from_pm_artifact()
-> Sell Planning REDUCE quantity contract
-> Order Plan quantity_contract
-> Pending Order Plan quantity_contract
-> Submit Guard quantity preflight
-> Execution read-only
-> Persistent Ledger
-> Current refresh
```

Key implementation points:

- `position_management/producer.py` emits `reduce_intensity` and quantity authority evidence.
- `planning/sell_pipeline.py` computes REDUCE quantities, handles EXIT priority, checks pending SELL conflicts, and caps planned sell quantity by sellable quantity evidence.
- `planning/models.py`, `planning/planner.py`, `pending/models.py`, and `pending/reader.py` carry `quantity_contract`.
- `submit/pipeline.py` uses the same open SELL order interpretation for Historical simulated broker availability.

## Fail-Closed Behavior

Sell Planning returns `REVIEW_REQUIRED` when quantity cannot be safely derived. Covered conditions include unknown intensity, missing Current position, invalid trading unit, sellable quantity below tradable unit, rounded quantity zero, REDUCE consuming the entire position, minimum remaining violation, and active same-symbol pending SELL conflict.

This is intentional. Runtime must not invent a quantity, force a SELL, or adjust thresholds to improve SELL count.

## 20BD Runtime Evidence

Historical Smoke:

```text
run_id: runtime-test-historical-smoke-20260721T120911954822Z
profile: historical-smoke
date_from: 2026-06-17
date_to: 2026-07-14
business_days: 20
initial_cash: 1000000
status: PASS
final_judgment: PASS
accepted_artifact_unchanged: true
registry_unchanged: true
broker_write_performed: false
external_delivery_performed: false
```

PM distribution:

| Decision | Count |
|---|---:|
| HOLD | 29 |
| ADD | 11 |
| REDUCE | 4 |
| EXIT | 3 |

SELL order plans by PM source decision:

| Source decision | Count |
|---|---:|
| REDUCE | 4 |
| EXIT | 3 |

REDUCE contracts generated:

| Date | Symbol | Intensity | Quantity | Sellable | Restricted | Expected remaining |
|---|---:|---|---:|---:|---:|---:|
| 2026-06-18 | 81050 | MEDIUM | 200 | 800 | 0 | 600 |
| 2026-06-19 | 66590 | LIGHT | 700 | 2900 | 0 | 2200 |
| 2026-06-22 | 66590 | MEDIUM | 700 | 2200 | 0 | 1500 |
| 2026-06-30 | 89180 | MEDIUM | 5000 | 15400 | 0 | 10400 |

EXIT contracts generated:

| Date | Symbol | Quantity | Sellable | Restricted | Expected remaining |
|---|---:|---:|---:|---:|---:|
| 2026-06-19 | 81050 | 600 | 600 | 0 | 0 |
| 2026-06-22 | 43780 | 200 | 200 | 0 | 0 |
| 2026-06-23 | 66590 | 1500 | 1500 | 0 | 0 |

The prior 06/22 false halt was removed after the open-order calculation fix.

## Regression

Required Phase19-BT tests:

```text
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
tests/runtime_v2/test_phase15af_position_management_runtime_connection.py
tests/runtime_v2/test_phase15ap_position_management_input_contract.py
tests/runtime_v2/test_phase19_bn_pm_opportunity_model_authority.py
tests/runtime_v2/test_phase19_br_accepted_generation_bound_runtime_inference.py
```

Result:

```text
35 passed
```

Related Runtime tests:

```text
Sell Planning, Sell IO, Historical Sell Authority, Order Plan models/builders,
Pending models/reader/writer/promotion, Submit pending promotion,
broker available quantity evidence, Submit pipeline, Execution read-only,
Execution acceptance, execution normalization/current apply, Ledger models,
Ledger append/dedup, Ledger projection, Historical sell execution projection
```

Result:

```text
89 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase19_bt_pycache python3 -m py_compile ...
PASS
```

Staged Historical Smoke:

| Scope | Run ID | Result |
|---|---|---|
| 1BD | `runtime-test-historical-smoke-20260721T120529636082Z` | PASS |
| 5BD | `runtime-test-historical-smoke-20260721T120618045233Z` | PASS |
| 20BD | `runtime-test-historical-smoke-20260721T120911954822Z` | PASS |

## Fix Necessity

Required and completed.

Without this contract, Production Runtime could identify a valid `REDUCE` decision but had no accepted way to size the partial SELL. With this contract, REDUCE is sell-capable, deterministic, auditable, and still fail-closed.

## Historical Smoke Re-Run Need

Completed. The final 20BD Historical Smoke passed after the contract implementation and open-order evidence fix.

## Final Judgment

```text
PHASE19_BT_POSITION_MANAGEMENT_REDUCE_QUANTITY_CONTRACT_COMPLETE
PHASE19_BT_20BD_HISTORICAL_SMOKE_PASS
```

