# Phase30-AK3R2B0 - Reserved-Notional Cash-Feasible BUY Batch Authority Design Audit

Task ID: `Phase30-AK3R2B0`

Type: `READ_ONLY_DESIGN_AUDIT`

Implementation boundary:

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK3R2B0
```

## Primary Judgment

```text
RESERVED_NOTIONAL_CASH_FEASIBLE_BATCH_AUTHORITY_DESIGN_APPROVED
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
```

Phase30-AK3R2A proved that AK3R1 was action-effective, but the fresh
2022-08-10 BUY path still produced zero submitted orders because a 13-item BUY
batch reached Pending with one cash-infeasible item:

```text
symbol = 93180
estimated_amount = 49,800
reserved_notional = 290,500
cash_at_check = 271,880
reason = reserved notional exceeds Current cash
```

Twelve BUY items passed item-level Submit feasibility, but Pending atomic BUY
batch protection blocked submission of the full batch. This is not a Submit
defect. Submit correctly failed closed. The missing authority is earlier:
Planning/Pending must construct a cash-feasible BUY batch using canonical
reserved notional before the batch is finalized for approval/submission.

## Authority Boundary

```text
CASH_FEASIBLE_BATCH_CONSTRUCTION_AUTHORITY =
  PLANNING_PENDING_BUY_BATCH_CONSTRUCTION_USING_CANONICAL_RESERVED_NOTIONAL_AND_CANONICAL_STRATEGY_PRIORITY
```

Responsibility split:

| Layer | Responsibility | Must Not Do |
| --- | --- | --- |
| Portfolio Construction | Decide investment membership, target change, and construction priority | Recompute broker cash reservation |
| Position Sizing | Convert approved target changes into executable quantity / lot semantics | Override reserved-cash feasibility |
| Planning/Pending batch construction | Convert PC/PS BUY candidates into a cash-feasible Pending BUY set using canonical reserved notional and canonical priority | Invent a new investment score or weaken Submit |
| Submit | Final authority verifier and fail-closed guard | Prune and submit a mutated batch silently at final send time |

Therefore the repair surface should be Production-common Planning/Pending batch
construction, not PC scoring, PS quantity authority, Submit final guard, or
Strategy thresholds.

## Reserved Notional Authority

```text
RESERVED_NOTIONAL_CANONICAL_PRODUCER =
  runtime_v2.order_reservation.resolve_order_cash_reservation
```

The canonical reservation producer is already present:

```text
authority_type = ORDER_CONDITION_DERIVED_RESERVATION_PRICE_AUTHORITY
production_broker_cash_semantics = MARKET_BUY_USES_STOP_HIGH_PRICE_LIMIT_FOR_BUYING_POWER
```

`PendingOrderItem` already carries:

```text
reservation_price
reservation_price_type
reservation_price_authority
reservation_reason
reserved_notional
```

and `planning_submit_feasibility` already consumes those fields. This means the
repair must reuse the same producer and evidence shape. It must not create a
second cash buffer, percentage haircut, or broker-feasibility heuristic.

```text
RESERVED_NOTIONAL_AVAILABLE_BEFORE_PENDING_FINALIZATION = YES
```

The caveat is scope: it is available at Pending item materialization and
approval-link feasibility. The missing step is to use the same reservation
authority to choose the committed BUY batch before a review-scoped Pending plan
becomes the active atomic batch.

## Canonical BUY Priority

```text
CANONICAL_BUY_PRIORITY_AUTHORITY =
  STRATEGY_RUNTIME_PLANNING_ORDER_DERIVED_FROM_PORTFOLIO_CONSTRUCTION_AND_POSITION_SIZING

CANONICAL_BUY_PRIORITY_AVAILABLE_TO_BATCH_CONSTRUCTION = YES
NEW_INVESTMENT_PRIORITY_IN_PLANNING_REQUIRED = NO
```

Runtime planning already preserves the production strategy order consumed by
Planning/Pending. The fresh 2022-08-10 selected BUY order was:

```text
23700, 23880, 38410, 39950, 47770, 66590, 76470, 83060, 89180, 93180, 94320, 94340, 99840
```

Planning/Pending may use that order as a deterministic batch-construction
priority. It must not sort by cash size, price, ticker, model score, historical
outcome, or a newly invented planning-layer priority.

## Cash-Feasible Batch Selection Semantic

```text
CASH_FEASIBLE_BATCH_SELECTION_SEMANTIC =
  PRIORITY_ORDERED_RESERVED_NOTIONAL_SKIP_AND_CONTINUE_PRUNING

NEW_BATCH_OPTIMIZATION_REQUIRED = NO
```

Required semantic:

1. Iterate BUY candidates in canonical Runtime Planning order.
2. Resolve canonical `reserved_notional` for each candidate.
3. If the item passes all non-cash authority checks and fits remaining cash /
   buying power / exposure / position count, include it in the Pending BUY
   batch and reserve its notional.
4. If it fails solely because it cannot fit remaining reserved cash, do not
   include it in the active Pending BUY batch; mark it as cash-pruned evidence.
5. Continue to later candidates in the same canonical order.
6. Submit receives only the cash-feasible Pending BUY batch and still performs
   final fail-closed verification.

This is not a knapsack optimizer. It does not reorder, backtrack, or maximize
notional. The later-candidate continuation is acceptable because the planning
layer is not changing investment preference; it is admitting the highest
priority feasible subset under broker cash-reservation semantics.

## Atomic Batch Interpretation

```text
ATOMIC_BATCH_REQUIRES_ALL_ORIGINAL_BUY_CANDIDATES = NO
CASH_PRUNED_VALID_BATCH_CAN_SUBMIT = YES
```

Atomic BUY protection should apply to the finalized cash-feasible Pending BUY
batch, not to every original PC/PS-positive candidate. A candidate that cannot
fit reserved cash is not a submitted-batch member. It is a deferred planning
outcome with evidence.

```text
CASH_PRUNED_ITEM_SEMANTIC = DEFERRED_INSUFFICIENT_RESERVED_CASH
```

Cash-pruned items must be explicit in evidence, but they should not create an
item-scoped review that blocks unrelated feasible BUYs. If a pruned item fails
for a non-cash authority reason, that remains review/halt semantics according
to the existing authority.

## AK2 One-Lot Interaction

```text
AK2_ONE_LOT_CASH_PRIORITY_SPECIAL_CASE_REQUIRED = NO
```

AK2 one-lot admission authorizes minimum executable quantity when the strategy
intends the BUY and the one-lot notional is above the selected position amount.
It does not grant reserved-cash priority over other canonical BUY candidates.
One-lot items participate in the same priority-ordered reserved-notional
feasibility pass.

## Preservation Requirements

```text
SUBMIT_FINAL_CASH_FAIL_CLOSED_PRESERVED = YES
ATOMIC_BATCH_PROTECTION_PRESERVED = YES
PC_INVESTMENT_PRIORITY_PRESERVED = YES
PS_QUANTITY_AUTHORITY_PRESERVED = YES
AK2_ONE_LOT_AUTHORITY_PRESERVED = YES
STRATEGY_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
```

The approved design preserves the final Submit guard. It only prevents a known
cash-infeasible candidate from becoming a member of the atomic submitted BUY
batch when enough evidence exists to defer it during Planning/Pending
construction.

## Required Final Judgments

```text
CASH_FEASIBLE_BATCH_CONSTRUCTION_AUTHORITY =
  PLANNING_PENDING_BUY_BATCH_CONSTRUCTION_USING_CANONICAL_RESERVED_NOTIONAL_AND_CANONICAL_STRATEGY_PRIORITY

RESERVED_NOTIONAL_CANONICAL_PRODUCER =
  runtime_v2.order_reservation.resolve_order_cash_reservation

RESERVED_NOTIONAL_AVAILABLE_BEFORE_PENDING_FINALIZATION = YES

CANONICAL_BUY_PRIORITY_AUTHORITY =
  STRATEGY_RUNTIME_PLANNING_ORDER_DERIVED_FROM_PORTFOLIO_CONSTRUCTION_AND_POSITION_SIZING

CANONICAL_BUY_PRIORITY_AVAILABLE_TO_BATCH_CONSTRUCTION = YES
NEW_INVESTMENT_PRIORITY_IN_PLANNING_REQUIRED = NO

CASH_FEASIBLE_BATCH_SELECTION_SEMANTIC =
  PRIORITY_ORDERED_RESERVED_NOTIONAL_SKIP_AND_CONTINUE_PRUNING

NEW_BATCH_OPTIMIZATION_REQUIRED = NO

ATOMIC_BATCH_REQUIRES_ALL_ORIGINAL_BUY_CANDIDATES = NO
CASH_PRUNED_VALID_BATCH_CAN_SUBMIT = YES
CASH_PRUNED_ITEM_SEMANTIC = DEFERRED_INSUFFICIENT_RESERVED_CASH

AK2_ONE_LOT_CASH_PRIORITY_SPECIAL_CASE_REQUIRED = NO
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
```

## Recommended Next Task

```text
Phase30-AK3R2B - Reserved-Notional-Aware Cash-Feasible BUY Batch Construction Repair
```

Repair should be limited to Production-common Planning/Pending BUY batch
construction and its regression evidence. Fresh 20BD/100BD/long Historical
validation should remain user-operated after the focused repair.
