# Phase31-B8 — Pending Reserved-Cash Causality Bridge / Shadow Structural Closure

## PRIMARY_JUDGMENT

`PHASE31_B8_PENDING_RESERVED_CASH_CAUSALITY_BRIDGE_REPAIRED`

The non-mutating `MARGINAL_CAPITAL_VALUE_AUTHORITY` shadow now bridges the canonical Pending reserved-cash feasibility chain used by Runtime Planning. The bridge reconstructs, per BUY candidate where canonical evidence exists, the actual Pending order, pre-batch cash, required reserved notional, cumulative prior reserved notional, remaining cash before/after the item, final Pending state/scope, typed cash feasibility result, and reason code.

No Strategy, Runtime Planning decision, Pending membership behavior, Submit, Execution, fills, Strategy cap, or Safety hard cap behavior was changed.

## Canonical Authority

`PENDING_CASH_AUTHORITY_PRODUCER = runtime_v2.planning.strategy_authority._cash_feasible_buy_batch`

`PENDING_CASH_AUTHORITY_ARTIFACT = daily/<BUSINESS_DATE>/morning/strategy_planning_authority_evidence.json#lineage.cash_feasible_buy_batch`

`PENDING_CASH_AUTHORITY_FIELD = lineage.cash_feasible_buy_batch`

`PENDING_REVIEW_SCOPE_ARTIFACT = daily/<BUSINESS_DATE>/morning/pending_generation_evidence.json + pending_order_plan referenced by strategy_planning_authority_evidence.pending_path`

`RESERVED_NOTIONAL_SOURCE = runtime_v2.order_reservation.resolve_order_cash_reservation`

`ITEM_PROCESSING_ORDER_SOURCE = cash_feasible_buy_batch.items[].canonical_priority_index`

`TEMPORAL_BINDING = business_date morning planning decision-time authority evidence`

The bridge consumes only same-business-date Runtime authority evidence. It does not use future returns, later classifications, fills, or Historical outcome labels.

## Implementation

Updated:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value_shadow.py`
- `tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py`

The shadow now adds:

- `pending_cash_authority`
- `actual_pending_cash_batch_order`
- per-candidate `actual_pending_order`
- per-candidate `pending_cash_causality`
- pending cash metrics

Per-candidate bridged fields include:

- `shadow_priority`
- `actual_runtime_order`
- `actual_pending_order`
- `pre_batch_cash`
- `required_reserved_notional`
- `cumulative_reserved_before_item`
- `remaining_cash_before_item`
- `included_reserved_notional`
- `remaining_cash_after_item`
- `final_pending_state`
- `final_pending_scope`
- `final_cash_feasibility_result`
- `final_cash_reason_code`
- `typed_guard_class`
- `typed_guard_code`

Classification values implemented:

- `CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM`
- `LEGITIMATE_CANONICAL_LOWER_PRIORITY`
- `LEGITIMATE_FEASIBILITY_PRUNE`
- `LEGITIMATE_REVIEW_OR_SAFETY`
- `LOT_CONSTRAINT`
- `CONCENTRATION_CONSTRAINT`
- `NOT_REACHED_DUE_TO_UPSTREAM_ZERO_QUANTITY`
- `NO_ACTUAL_STARVATION`
- `UNRESOLVED`

## B0 Control Cases

### B0_2022_08_19_94320_FULL_CAUSALITY

`94320` is `BUY_ADD`, `ELIGIBLE_STRONG`.

- `shadow_priority = 1`
- `actual_runtime_order = 30`
- `actual_pending_order = 6`
- `pre_batch_cash = 187,950`
- `required_reserved_notional = 59,850`
- `cumulative_reserved_before_item = 163,000`
- `remaining_cash_before_item = 24,950`
- `remaining_cash_after_item = 24,950`
- `final_pending_state = PRUNE`
- `final_cash_reason_code = DEFERRED_INSUFFICIENT_RESERVED_CASH`
- `cash_causality_classification = CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM`

Lower-value prior included BUY_NEW items consuming cash before `94320`:

- `27780`: actual pending order 1, shadow priority 10, included reserved notional 33,100
- `60540`: actual pending order 3, shadow priority 4, included reserved notional 44,200
- `70140`: actual pending order 4, shadow priority 2, included reserved notional 85,700

### B0_2022_08_24_94320_FULL_CAUSALITY

`94320` is `BUY_ADD`, `ELIGIBLE_STRONG`.

- `shadow_priority = 1`
- `actual_runtime_order = 29`
- `actual_pending_order = 3`
- `pre_batch_cash = 68,900`
- `required_reserved_notional = 60,510`
- `cumulative_reserved_before_item = 55,700`
- `remaining_cash_before_item = 13,200`
- `remaining_cash_after_item = 13,200`
- `final_pending_state = PRUNE`
- `final_cash_reason_code = DEFERRED_INSUFFICIENT_RESERVED_CASH`
- `cash_causality_classification = CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM`

Lower-value prior included BUY_NEW item consuming cash before `94320`:

- `43760`: actual pending order 1, shadow priority 6, included reserved notional 55,700

## 9-Day Structural Metrics

Target run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z`

Mixed BUY_NEW/BUY_ADD days materialized: 9

Candidate units: 84

`FULL_CASH_CAUSALITY_RECONSTRUCTED_COUNT = 42`

`FULL_CASH_CAUSALITY_UNRESOLVED_COUNT = 0`

`ACTUAL_STARVATION_COUNT = 14`

`ACTUAL_STARVATION_NOTIONAL = 2,606,860`

`STRONG_ADD_NEW_STARVED_COUNT = 5`

`STRONG_ADD_NEW_STARVED_NOTIONAL = 696,360`

`CASH_PRUNE_LOWER_CANONICAL_INCLUDED_COUNT = 21`

`UNEXPLAINED_CASH_PRUNE_COUNT = 0`

`ORDER_INVERSION_WITHOUT_CASH_EFFECT_COUNT = 42`

Per-day reconstructed/unresolved counts:

| Date | Candidates | Reconstructed | Unresolved | Starved | Strong Starved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-08-19 | 10 | 7 | 0 | 4 | 1 |
| 2022-08-22 | 10 | 5 | 0 | 3 | 1 |
| 2022-08-23 | 13 | 6 | 0 | 2 | 1 |
| 2022-08-24 | 6 | 3 | 0 | 2 | 2 |
| 2022-08-30 | 7 | 3 | 0 | 0 | 0 |
| 2022-09-01 | 11 | 6 | 0 | 0 | 0 |
| 2022-09-15 | 11 | 5 | 0 | 2 | 0 |
| 2022-09-16 | 6 | 2 | 0 | 0 | 0 |
| 2022-09-20 | 10 | 5 | 0 | 1 | 0 |

## Guardrails

`PRE_BATCH_CASH_BRIDGED = YES`

`PER_ITEM_RESERVED_NOTIONAL_BRIDGED = YES`

`REMAINING_CASH_CHAIN_BRIDGED = YES`

`FINAL_PENDING_STATE_BRIDGED = YES`

`ACTUAL_TRADING_PATH_MUTATED = NO`

`FUTURE_INFORMATION_USED = NO`

`SHADOW_COMPARISON_SEMANTICS_CHANGED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`MUTATING_ALTERNATIVE_C_AUTHORIZED = NO`

`STRUCTURAL_REVALIDATION_READY = YES`

## Validation

Focused tests:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_b8_pycache python3 -m pytest -q tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py
```

Result:

`19 passed in 0.27s`

Diagnostic shadow materialization only:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_b8_pycache python3 -m ai_fund_lab_v2.strategy.marginal_capital_value_shadow --run-root reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z --all-completed-days
```

Result:

`materialized_day_count = 9`

`materialized_item_count = 84`

`actual_trading_path_mutated = false`

## Next Recommendation

Proceed to Phase31-B9 final shadow structural revalidation. B8 closes the B7 structural blocker by bridging Pending reserved-cash causality from canonical Runtime decision-time evidence without mutating the actual trading path.
