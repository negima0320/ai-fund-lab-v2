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

## Phase29-L21T-AD Intentional No-Order Semantics

The Production/Demo/Historical common REDUCE contract distinguishes PM intent from executable broker quantity. A valid PM `REDUCE` can intentionally materialize as no order when the partial sell is not expressible under market constraints.

Canonical intentional no-order semantics:

```text
REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL
```

Compatibility fields such as `reason = REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY` remain valid for existing Sell Planning quantity-contract consumers, but AD-era lifecycle classification must use the explicit semantic evidence when present.

Required observability for intentional no-order REDUCE:

- source PM decision and decision id;
- symbol;
- reduce intensity;
- target reduce ratio;
- position quantity before;
- raw reduce quantity;
- tradable unit;
- rounded executable quantity;
- final sell quantity;
- execution semantic;
- intentional no-order reason;
- position effect.

Authority rules:

- `REDUCE` remains partial exposure-reduction intent and must not silently become `EXIT`.
- Runtime must not ceil a sub-lot `REDUCE` to one lot.
- Runtime must not persist reduce debt or force a later catch-up order.
- The position remains unchanged for the day and the next day receives a fresh PM reevaluation.
- Missing semantic or lifecycle evidence is not fail-open; it remains `REVIEW_REQUIRED`.
- Explicit `EXIT` and mandatory executable SELL paths are unchanged.
- BUY and SELL authorities remain independent.
- This is common runtime behavior, not a Historical-only workaround.

## Phase32-BQ Lot-Blocked REDUCE Reconsidered FULL EXIT Authority

The default rule above remains authoritative: an unexecutable `REDUCE` does not silently become `EXIT`. Phase32-BQ adds one explicit Strategy-owned exception for durable-winner profit-protection cases accepted by the BO shadow evidence track.

Canonical authority:

```text
PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT
```

Production promotion is allowed only at the Sell Planning materialization boundary, before ordinary executable SELL planning and before Pending publication, when all of the following are true:

- source PM action is `REDUCE`;
- canonical campaign and current-position authority exist and agree;
- desired partial reduce quantity is positive;
- final executable REDUCE quantity is exactly `0`;
- the no-order semantic is specifically `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`;
- same-business-date PIT Strategy Intelligence and market context evidence are complete and run/profile bound;
- the BO semantic reconsideration result is `SHADOW_FULL_EXIT`;
- no native PM `EXIT`, executable `REDUCE`, stale/cross-run/future evidence, or malformed provenance conflict exists.

When the authority passes, Sell Planning materializes an ordinary downstream `SELL_EXIT` for the current full sellable position quantity. It must preserve the original PM `REDUCE` lineage in the quantity contract:

```text
source_pm_action = REDUCE
source_pm_decision_id = <original PM decision id>
original_source_decision = REDUCE
reconsidered_action = FULL_EXIT
reconsideration_reason = PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT
runtime_invented_exit = false
```

Runtime, Submit, Execution, Ledger, and broker adapters must not invent this promotion. They consume the materialized order as an ordinary `SELL_EXIT`; there is no special broker-side order type.

Explicit exclusions remain unchanged:

- executable `REDUCE` remains partial `REDUCE`;
- minimum-notional no-order remains no-order;
- BO `SHADOW_HOLD` and `SHADOW_INSUFFICIENT_EVIDENCE` do not promote;
- BUY, ADD, HOLD, native EXIT, ranking, threshold, weight, cash, and risk pacing semantics are unchanged;
- stale same-symbol/campaign/date retry must either reuse the existing equivalent SELL Pending or fail closed.

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
