# Phase31-B6 — Marginal Capital Shadow Evidence Bridge / Real-Run Materialization Repair

## PRIMARY_JUDGMENT

PHASE31_B6_MARGINAL_CAPITAL_SHADOW_REAL_EVIDENCE_BRIDGE_REPAIRED

## Summary

B6 repaired the B5 shadow validation gaps without connecting Alternative C to the actual trading path.

Implemented:

- Real-run diagnostic materialization path.
- Runtime `plans` order bridge into `actual_runtime_cash_batch_order`.
- PIT ADD campaign evidence bridge from existing Portfolio Construction `add_investment_evidence`.
- Typed lot/materialization reason bridge.

No PM, PC target decision, PS quantity, Runtime Planning order, Pending, reserved cash, Submit, Execution, fill, Strategy cap, or Safety hard cap behavior was changed.

## REAL_RUN_SHADOW_MATERIALIZATION

YES

Diagnostic command used:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.strategy.marginal_capital_value_shadow --run-root reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z --all-completed-days
```

Output namespace:

```text
daily/<business_date>/diagnostic_shadow/marginal_capital_value_shadow.json
```

Materialized mixed NEW/ADD days:

- `2022-08-19`
- `2022-08-22`
- `2022-08-23`
- `2022-08-24`
- `2022-08-30`
- `2022-09-01`
- `2022-09-15`
- `2022-09-16`
- `2022-09-20`

Materialized day count = 9

Materialized item count = 84

## RUNTIME_PLANS_ORDER_BRIDGED

YES

The shadow now reads actual Runtime Planning artifact shape:

```text
daily/<DATE>/strategy/runtime_planning.json#plans
```

It preserves artifact list order semantics and materializes:

- `symbol`
- `side`
- `item_id`
- `planning_intent`
- `quantity`
- `planned_notional`
- `actual_runtime_order`
- `inclusion_state`
- `reason`

All 9 materialized mixed days have populated `actual_runtime_cash_batch_order`.

## ADD_CAMPAIGN_PIT_EVIDENCE_BRIDGED

YES

Canonical PIT source consumed:

```text
Portfolio Construction member.add_investment_evidence
```

Fallback source where needed:

```text
Portfolio Construction member.target_weight_resolution.add_allocation_bridge.add_investment_evidence
```

The bridge materializes:

- campaign identifier
- campaign state source
- evidence business date
- Expected Edge baseline date
- Expected Edge current state
- Incremental Investment Value state
- Opportunity Cost state
- ADD-worthiness state
- source artifact paths/hashes
- PIT validation status

If PIT provenance cannot be proven, the candidate remains `COMPARISON_INSUFFICIENT`.

## B0_94320_COMPARISON_INSUFFICIENT_AFTER_REPAIR

0

Post-repair B0 development cases:

| Date | Symbol | Class | Shadow Order | Runtime Order | Lot/Materialization |
| --- | --- | --- | ---: | ---: | --- |
| `2022-08-19` | `94320` | `ELIGIBLE_STRONG` | 1 | 30 | `EXECUTABLE_LOT` |
| `2022-08-24` | `94320` | `ELIGIBLE_STRONG` | 1 | 29 | `EXECUTABLE_LOT` |

The result does not assert that 94320 must always win. It confirms that the prior B5 insufficiency was an evidence-transport gap, not a legitimate absence of PIT ADD evidence.

## LOT_MATERIALIZATION_TYPED

YES

Candidate units now include `lot_materialization_reason`.

Supported categories:

- `EXECUTABLE_LOT`
- `ZERO_QUANTITY_DELTA`
- `LOT_NOT_FEASIBLE`
- `CONCENTRATION_BOUND`
- `BUDGET_BOUND`
- `NOT_IN_RUNTIME_PLAN`

Runtime order rows also expose `inclusion_state`, including `RESERVED_CASH_PRUNE` and `REVIEW_REQUIRED` where existing Runtime reason evidence supports it.

Post-repair materialized count:

- Typed candidate units = 84 / 84

## FUTURE_INFORMATION_USED

NO

The bridge consumes existing PIT Strategy/PC evidence only. It does not use future price, future/forward return, future PnL, later campaign outcome, MFE/MAE outcome labels, selected/bought outcome, fill outcome, future-known regime, or Historical performance labels.

## ACTUAL_TRADING_PATH_MUTATED

NO

Mandatory non-mutation fields are materialized as false:

- `actual_pc_decision_mutated = false`
- `actual_ps_quantity_mutated = false`
- `actual_runtime_order_mutated = false`
- `actual_pending_mutated = false`
- `actual_submit_mutated = false`
- `actual_execution_mutated = false`
- `actual_fill_mutated = false`
- `actual_run_state_mutated = false`
- `actual_trading_path_mutated = false`

The diagnostic materializer writes only `diagnostic_shadow/marginal_capital_value_shadow.json` files.

## STRONG_NEW_PROTECTION

PASS

Focused tests confirm strong NEW may still outrank weak ADD. B6 did not add a numeric lifecycle premium, ADD bonus, NEW penalty, threshold tuning, or symbol-specific rule.

## WEAK_ADD_PROTECTION

PASS

Expected Edge `WEAKENING` remains non-promoted and emits `expected_edge_weakening_not_rescued`.

## BUY_ADD_LABEL_PRIORITY_VIOLATION_COUNT

0

## BUY_NEW_LABEL_PRIORITY_VIOLATION_COUNT

0

## Post-Repair Real-Run Class Distribution

| Class | Count |
| --- | ---: |
| `ELIGIBLE_STRONG` | 18 |
| `ELIGIBLE_COMPARABLE` | 66 |
| `COMPARISON_INSUFFICIENT` | 0 |

## TEST_RESULTS

Focused tests:

```bash
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py
```

Result:

```text
15 passed in 0.22s
```

Compile check:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_value_shadow.py
```

Result: PASS

## LONG_HISTORICAL_EXECUTED

NO

No fresh-run, resume, replay, 25BD, 100BD, 500BD, or long Historical run was executed.

## SHADOW_REVALIDATION_READY

YES

B6 repairs the B5 structural gaps enough to run B7 shadow evidence revalidation using the repaired bridge.

## MUTATING_ALTERNATIVE_C_AUTHORIZED

NO

B6 does not authorize mutating Alternative C.

## Next Recommendation

Run B7 shadow evidence revalidation using the repaired bridge.
