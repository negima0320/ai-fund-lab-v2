# Position Management REDUCE Quantity Contract

Status: Phase19-BT accepted runtime contract

This contract applies to Historical, Demo, and Production Runtime v2. It defines how a Position Management `REDUCE` decision becomes a partial SELL order without changing Position Management score thresholds, Opportunity score scale, BUY policy, or EXIT policy.

## Authority Boundary

Position Management owns the investment decision:

```text
HOLD / ADD / REDUCE / EXIT
```

For `REDUCE`, Position Management may emit only a reduce intent and reduce intensity. It must not decide the broker-final sell quantity.

Sell Planning owns the deterministic quantity contract. It consumes Current, PM decision evidence, broker available quantity evidence where available, trading unit policy, and pending-order conflict state, then produces an Order Plan and Pending Order Plan.

Submit Guard remains final preflight authority. It independently validates Current-owned quantity and broker available quantity before any broker write. Sell Planning may cap by sellable quantity, but Submit Guard is still the final safety check.

## REDUCE Decision Output

The PM decision artifact may emit:

- `decision = REDUCE`
- `runtime_action = SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING`
- `runtime_sell_quantity = 0`
- `runtime_quantity_authority = SELL_PLANNING_REDUCE_QUANTITY_CONTRACT`
- `reduce_intensity`
- `reduce_intensity_evidence`

Allowed `reduce_intensity` values:

| Intensity | Target reduce ratio |
|---|---:|
| `LIGHT` | 0.25 |
| `MEDIUM` | 0.33 |
| `STRONG` | 0.50 |

## Sell Planning Quantity Contract

Sell Planning writes the quantity contract into both `OrderPlanItem.quantity_contract` and `PendingOrderItem.quantity_contract`.

Contract version:

```text
runtime_v2_pm_reduce_quantity_v1
```

Required fields:

- `quantity_contract_version`
- `source_decision`
- `reduce_intensity`
- `target_reduce_ratio`
- `position_quantity_before`
- `sellable_quantity`
- `sellable_quantity_source`
- `restricted_quantity`
- `tradable_unit`
- `minimum_order_quantity`
- `minimum_remaining_quantity`
- `rounding_policy`
- `raw_reduce_quantity`
- `rounded_reduce_quantity`
- `final_sell_quantity`
- `expected_remaining_quantity`
- `execution_feasibility_status`
- `effective_action`
- `pending_order_generated`
- `runtime_continuation_status`
- `status`
- `reason`

Formula:

```text
effective_sellable_quantity = min(position_quantity_before, sellable_quantity)
raw_reduce_quantity = effective_sellable_quantity * target_reduce_ratio
rounded_reduce_quantity = floor(raw_reduce_quantity / tradable_unit) * tradable_unit
final_sell_quantity = rounded_reduce_quantity
expected_remaining_quantity = position_quantity_before - final_sell_quantity
```

Default tradable unit is `100` shares. The rounding policy is floor-to-tradable-unit. `REDUCE` must leave a remaining position; it must not implicitly escalate into `EXIT`.

## Non-executable Minimum Tradable Quantity

When a valid `REDUCE` decision has known Current quantity, known tradable unit, known reduce intensity, and deterministic rounding produces zero executable quantity, Sell Planning must preserve the original PM `REDUCE` decision but generate no SELL order.

This is not a silent `HOLD`, not an implicit `EXIT`, and not a 0-share order. It is an execution-feasibility result:

```text
status = NOT_EXECUTABLE
reason = REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY
execution_feasibility_status = NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY
final_sell_quantity = 0
rounded_executable_quantity = 0
effective_action = NO_SELL_ORDER
pending_order_generated = false
position_quantity_after = position_quantity_before
runtime_continuation_status = PASS
position_lifecycle_event = REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY
```

Sell Planning writes this evidence to the no-action Order Plan and Pending Plan under `non_executable_sell_decisions`. The Pending Plan remains empty and inactive. Position Campaign remains open and no realized slice or execution event is created.

## Fail-Closed Conditions

Sell Planning must stop with `REVIEW_REQUIRED` instead of silently changing PM intent when quantity authority or calculation safety is uncertain:

- Current position is missing or zero.
- Trading unit is unknown or invalid.
- Reduce intensity is unknown.
- Sellable quantity is negative or authority is ambiguous.
- Final sell quantity is greater than or equal to the current position quantity.
- Minimum remaining quantity would be violated.
- A same-symbol active pending SELL conflict exists.

Representative reasons:

- `REVIEW_REQUIRED_REDUCE_CURRENT_POSITION_MISSING`
- `REVIEW_REQUIRED_REDUCE_TRADABLE_UNIT_UNKNOWN`
- `REVIEW_REQUIRED_REDUCE_INTENSITY_UNKNOWN`
- `REVIEW_REQUIRED_REDUCE_SELLABLE_QUANTITY_NEGATIVE`
- `REVIEW_REQUIRED_REDUCE_QUANTITY_EXCEEDS_OR_EQUALS_POSITION`
- `REVIEW_REQUIRED_REDUCE_MINIMUM_REMAINING_QUANTITY_VIOLATION`
- `REVIEW_REQUIRED_REDUCE_PENDING_SELL_CONFLICT:<symbols>`

## EXIT Interaction

If `EXIT` and `REDUCE` exist for the same symbol in the same PM artifact, Sell Planning gives `EXIT` priority and drops the lower-priority `REDUCE` for that symbol.

`EXIT` intent remains full-position liquidation. Sell Planning may cap the planned sell quantity to the currently sellable quantity evidenced by broker/historical authority, and records:

```text
quantity_contract_version = runtime_v2_pm_exit_full_quantity_v1
source_decision = EXIT
requested_sell_quantity
sellable_quantity
restricted_quantity
final_sell_quantity
expected_remaining_quantity
```

This cap prevents a known broker-available preflight failure while preserving Submit Guard as final authority.

## Production Commonness

The same Position Management producer, Sell Planning pipeline, Order Plan model, Pending model, Pending reader, Submit Guard, Execution read-only pipeline, Ledger projection, and Current refresh path are used by Historical, Demo, and Production. Historical uses `historical_simulated_broker_authority` to emulate broker available quantity from Runtime-owned Current and open SELL order ledger. Demo and Production use broker read-only available quantity snapshots when available, falling back to Current with Submit Guard as final authority when no snapshot exists.

Historical open SELL order evidence counts only unresolved submitted SELL orders. It excludes rejected/cancelled orders and execution-equivalent filled order records so that filled orders are not counted again as restricted quantity.
