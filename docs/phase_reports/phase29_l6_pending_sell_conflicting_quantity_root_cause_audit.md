# Phase29-L6 Pending SELL Conflicting Quantity Root Cause Audit

## Status

COMPLETE

READ_ONLY ROOT CAUSE AUDIT / REPAIR DESIGN

NO PRODUCTION CODE CHANGE

NO CONFIG CHANGE

NO SCHEMA CHANGE

NO RUNTIME / PENDING / LEDGER MUTATION

NO HISTORICAL RESUME OR FRESH RUN

## Primary Judgment

PHASE29_L6_PENDING_SELL_FALSE_QUANTITY_CONFLICT_PRODUCTION_DEFECT_CONFIRMED

## Direct HALT

Long-horizon Historical run:

```text
run_id = runtime-test-historical-smoke-20260810T154347268066Z
completed_business_days = 39
halt = 2022-10-07:sell_planning
reason = PENDING_SELL_CONFLICTING_QUANTITY_REVIEW;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED
```

Non-causal authorities were PASS/READY: PM input, PM temporal validation,
Listed PIT, Accepted Generation binding, Safety, Current position, Current
valuation, Calendar, Market, Position Sizing quantity contract, and Planning
submit feasibility.

## Quantity Trace

| Field | Value |
|---|---:|
| symbol | 76920 |
| current owned quantity | 2000 |
| existing pending side | SELL |
| existing pending quantity | 1000 |
| existing pending requested quantity | -1000 |
| existing pending quantity delta | -1000 |
| existing pending decision | SELL_REDUCE |
| new PM action | REDUCE |
| new target weight | 0.124713 |
| new target notional | 137800.38 |
| new target quantity | 1000 |
| new quantity delta | -1000 |
| new SELL item quantity | 900 |
| new quantity contract final sell quantity | 1000 |
| comparison left | `existing_item.quantity = 1000` |
| comparison right | `new_item.quantity = 900` |
| conflict result | REVIEW_REQUIRED |

This is not a sign-normalization defect. The reconciliation code compared two
positive SELL item quantities.

This is not target-remaining quantity confused with sell quantity. The new
target remaining quantity is 1000 and the authoritative sell delta is also
1000 shares.

## Comparison Code

The exact branch is:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py
_classify_sell_pair lines 454-461
_equivalent_quantity lines 884-885
```

Expression:

```python
abs(float(left or 0.0) - float(right or 0.0)) < 1e-9
```

The branch compares:

```text
existing_item.quantity
new_item.quantity
```

There is no sign conversion, no target-vs-sell semantic conversion, and no lot
tolerance beyond exact float equality.

For the actual evidence:

```text
existing_item.quantity = 1000
new_item.quantity = 900
equivalent_quantity = false
classification = SAME_SYMBOL_CONFLICTING_QUANTITY
```

D3 reconciliation therefore failed closed and preserved the original approved
pending plan. That behavior was safe.

## Root Cause

The actual Production defect is upstream of D3 reconciliation:

```text
Sell Planning quantity_contract.final_sell_quantity = 1000
Strategy / Runtime Planning planned_quantity = 1000
Position Sizing quantity_delta_candidate = -1000
OrderPlanItem / Pending item quantity = 900
```

Sell Planning first calculates the PM REDUCE contract correctly:

```text
position_quantity_before = 2000
target_reduce_ratio = 0.5
raw_reduce_quantity = 1000
rounded_reduce_quantity = 1000
final_sell_quantity = 1000
expected_remaining_quantity = 1000
```

Then common `build_order_plan()` materializes item quantity by recomputing from
notional and price:

```text
quantity = _round_lot_quantity(estimated_amount, estimated_price)
estimated_amount = 137800.0
estimated_price = 137.8
```

Because the common planner ignores `quantity_contract.final_sell_quantity`, the
new SELL item becomes 900 even though its own contract says 1000. This is an
internal quantity-authority mismatch.

Classification:

```text
L6-C SAME_INTENT_DIFFERENT_QUANTITY_CALCULATION_DEFECT
```

Production defect:

```text
YES
```

## Pending Reservation

The existing approved 1000-share SELL was not incorporated as a reserved
quantity in the new Sell Planning reduce contract:

```text
owned quantity used = 2000
sellable quantity = 2000
restricted quantity = 0
```

However, pending-reservation double count is not the direct cause of this HALT.
The new authoritative contract still requested 1000 shares, equal to the
existing pending. If item materialization had preserved the contract quantity,
D3 would have treated this as same-symbol compatible / duplicate quantity and
preserved the existing pending item.

```text
Pending reservation double-count = NO as direct cause
Same-day duplicate planning involved = YES
Same-day duplicate planning expected = YES
```

## Phase28-D3 Contract Review

D3 intended and implemented:

| Case | Implemented behavior |
|---|---|
| exact same SELL plan | preserve existing |
| same symbol same quantity | preserve/merge compatible |
| REDUCE -> REDUCE changed quantity | REVIEW_REQUIRED |
| REDUCE -> EXIT | replace with EXIT if safe |
| EXIT -> REDUCE | preserve existing EXIT |
| duplicate retry | preserve existing |
| stale pending | REVIEW_REQUIRED |
| same-session recomputation | supported when quantity is equivalent |

For this case, D3 covered the intended scenario if the new item quantity had
remained 1000. The actual materialized 900 caused the designed fail-closed
quantity-conflict path.

## Repair Design

Design only; not implemented in L6.

Recommended repair:

```text
For SELL allocations carrying quantity_contract.final_sell_quantity,
OrderPlanItem.quantity must consume that authoritative sell quantity instead
of recomputing from allocated_amount / estimated_price.
```

Add fail-closed validation before Pending promotion:

```text
SELL item.quantity == quantity_contract.final_sell_quantity
```

when `quantity_contract.source_decision` is `REDUCE` or `EXIT`.

Keep D3 reconciliation semantics:

| Scenario | Design |
|---|---|
| Exact equivalent | Preserve existing pending, PASS |
| Same intent / same economic target | Preserve existing pending, PASS |
| Stronger sell, REDUCE -> EXIT | Replace/supersede only with evidence and only if not submitted |
| Weaker sell | Review unless a cancel/reduce pending policy exists |
| Genuine ambiguity | REVIEW_REQUIRED |

Do not suppress `PENDING_SELL_CONFLICTING_QUANTITY_REVIEW`. The right repair is
to keep item quantity semantically bound to authoritative SELL quantity, then
let D3 distinguish equivalent from genuinely changed orders.

BUY/SELL independence is preserved by this design.

Strategy change required:

```text
NO
```

## Resume / Fresh Decision

If the repair is implemented, it requires a Production code change after 39
completed business days in this run.

```text
Resume after repair allowed = NO
Fresh-run after repair required = YES
```

Use a fresh run for a clean source/code baseline after implementation.

## Evidence

Evidence root:

```text
reports/phase29_l6_pending_sell_conflicting_quantity_root_cause_audit/
```

Files:

```text
existing_pending_authority.json
new_sell_candidate_authority.json
quantity_comparison_trace.json
pm_target_reconstruction.json
pending_reservation_audit.json
phase28_d3_contract_comparison.json
root_cause.json
production_defect_decision.json
repair_design.json
resume_fresh_decision.json
```
