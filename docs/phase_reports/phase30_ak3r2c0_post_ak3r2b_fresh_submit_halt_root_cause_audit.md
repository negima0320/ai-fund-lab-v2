# Phase30-AK3R2C0 - Post-AK3R2B Fresh Submit HALT Root-Cause Audit

Task ID: `Phase30-AK3R2C0`

Type: `READ_ONLY_RUNTIME_ROOT_CAUSE_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T225719066998Z
```

Boundary:

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK3R2C0
NO_REPLAY_RESUME_FRESH_RUN_BY_CODEX
NO_RUNTIME_MUTATION
```

## Primary Judgment

```text
FIRST_HALT_LAYER = SUBMIT_GUARD_ITEM_CANONICAL_EVIDENCE_REVALIDATION
HALT_DIRECT_REASON = one_lot_authority_quantity_mismatch
POST_AK3R2B_SUBMIT_HALT_CLASSIFICATION = SUBMIT_GUARD_AUTHORITY_GAP
AK3R2B_RUNTIME_ACTION_EFFECTIVE = PARTIAL
```

AK3R2B was action-effective for the reserved-notional cash batch problem. The
fresh runtime materialized `cash_feasible_buy_batch`, pruned `93180`, continued
to later BUY candidates, and produced a 12-item active Pending BUY batch whose
reserved notional fit Current cash.

The HALT is a new downstream Submit guard revalidation gap. Submit aggregate
feasibility passed all 12 active BUY items, but item-level Submit guard blocked
5 AK2 minimum one-lot items with:

```text
one_lot_authority_quantity_mismatch
```

## Required Counts

```text
RUNTIME_BUY_PLAN_COUNT = 13
CASH_FEASIBLE_BATCH_CANDIDATE_COUNT = 13
CASH_FEASIBLE_BATCH_INCLUDED_COUNT = 12
CASH_PRUNED_COUNT = 1
FINAL_RESERVED_NOTIONAL_TOTAL = 970,360
STARTING_CASH = 1,000,000
ACTIVE_PENDING_BUY_COUNT = 12
SUBMIT_PASS_COUNT = 7
SUBMIT_REVIEW_COUNT = 5
SUBMIT_BLOCK_COUNT = 5
HALT_DIRECT_REASON = one_lot_authority_quantity_mismatch
```

## AK3R2B Runtime Conformance

```text
CASH_FEASIBLE_BATCH_RUNTIME_MATERIALIZED = YES
DEFERRED_INSUFFICIENT_RESERVED_CASH_RUNTIME_COUNT = 1
SKIP_AND_CONTINUE_RUNTIME_ACTION_EFFECTIVE = YES
CANONICAL_PRIORITY_RUNTIME_PRESERVED = YES
ACTIVE_BATCH_RESERVED_NOTIONAL_WITHIN_CASH = YES
```

Cash-feasible batch evidence:

| Priority | Symbol | Decision | Reserved Notional | Cash Before | Cash After | Reason |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | 23700 | INCLUDE | 71,400 | 1,000,000 | 928,600 | `planning_submit_feasibility_pass` |
| 2 | 23880 | INCLUDE | 40,800 | 928,600 | 887,800 | `planning_submit_feasibility_pass` |
| 3 | 38410 | INCLUDE | 96,700 | 887,800 | 791,100 | `planning_submit_feasibility_pass` |
| 4 | 39950 | INCLUDE | 61,500 | 791,100 | 729,600 | `planning_submit_feasibility_pass` |
| 5 | 47770 | INCLUDE | 78,000 | 729,600 | 651,600 | `planning_submit_feasibility_pass` |
| 6 | 66590 | INCLUDE | 76,000 | 651,600 | 575,600 | `planning_submit_feasibility_pass` |
| 7 | 76470 | INCLUDE | 78,400 | 575,600 | 497,200 | `planning_submit_feasibility_pass` |
| 8 | 83060 | INCLUDE | 85,920 | 497,200 | 411,280 | `planning_submit_feasibility_pass` |
| 9 | 89180 | INCLUDE | 139,400 | 411,280 | 271,880 | `planning_submit_feasibility_pass` |
| 10 | 93180 | PRUNE | 290,500 | 271,880 | 271,880 | `DEFERRED_INSUFFICIENT_RESERVED_CASH` |
| 11 | 94320 | INCLUDE | 39,760 | 271,880 | 232,120 | `planning_submit_feasibility_pass` |
| 12 | 94340 | INCLUDE | 40,100 | 232,120 | 192,020 | `planning_submit_feasibility_pass` |
| 13 | 99840 | INCLUDE | 162,380 | 192,020 | 29,640 | `planning_submit_feasibility_pass` |

Runtime selected active Pending BUY symbols:

```text
23700, 23880, 38410, 39950, 47770, 66590, 76470, 83060, 89180, 94320, 94340, 99840
```

`93180` was not in the active Pending BUY batch.

## Submit Feasibility

Aggregate Submit feasibility:

```text
status = PASS
item_count = 12
blocked_item_count = 0
cash = 1,000,000
ending_reserved_cash = 29,640
ending_reserved_buying_power = 29,640
ending_reserved_exposure = 970,360
```

Each aggregate feasibility item passed. The previous cash trigger:

```text
reserved notional exceeds Current cash
```

did not recur.

```text
RESERVED_CASH_REVIEW_RECURRENCE = NO
```

## Submit Guard HALT

Submit manifest:

```text
exit_code = 20
final_state = REVIEW_REQUIRED
reason = submit completed with rejected/unknown/blocked items
pending_item_count = 12
pending_slot_status = APPROVED
submitted_count = 7
blocked_count = 5
halt_required = False
review_required = True
```

Blocked items:

| Symbol | Quantity | Estimated Amount | Reserved Notional | Submit Status | Direct Reason |
| --- | ---: | ---: | ---: | --- | --- |
| 38410 | 100 | 80,800 | 96,700 | `REVIEW_REQUIRED` | `one_lot_authority_quantity_mismatch` |
| 39950 | 100 | 52,800 | 61,500 | `REVIEW_REQUIRED` | `one_lot_authority_quantity_mismatch` |
| 47770 | 100 | 68,400 | 78,000 | `REVIEW_REQUIRED` | `one_lot_authority_quantity_mismatch` |
| 83060 | 100 | 71,350 | 85,920 | `REVIEW_REQUIRED` | `one_lot_authority_quantity_mismatch` |
| 99840 | 100 | 132,880 | 162,380 | `REVIEW_REQUIRED` | `one_lot_authority_quantity_mismatch` |

All five are AK2 minimum executable one-lot items with
`one_lot_authority_consumed = true` in `position_sizing_authority`.

## Root Cause

Submit guard revalidates BUY item feasibility through
`submit.pipeline._buy_guard_evidence()` using a synthetic
`SubmitGuardItem`. That synthetic item passes:

```text
pending_item_id
symbol
estimated_amount
quantity_contract
```

but does not provide the top-level `quantity` field expected by
`planning_submit_feasibility._one_lot_submit_authority()`.

`_one_lot_submit_authority()` reads:

```text
quantity = getattr(item, "quantity", 0.0)
authorized_quantity = position_sizing_authority.discrete_authorized_quantity
```

For the blocked one-lot items, the authority says `authorized_quantity = 100`,
but the synthetic SubmitGuardItem exposes no `quantity`, so the revalidation
path sees `quantity = 0` and returns:

```text
one_lot_authority_quantity_mismatch
```

This is a Submit guard authority handoff gap. Planning/Pending aggregate
feasibility and AK3R2B cash-pruning behavior were clean.

## Required Final Judgments

```text
FIRST_HALT_LAYER = SUBMIT_GUARD_ITEM_CANONICAL_EVIDENCE_REVALIDATION
HALT_DIRECT_REASON = one_lot_authority_quantity_mismatch
CASH_FEASIBLE_BATCH_RUNTIME_MATERIALIZED = YES
DEFERRED_INSUFFICIENT_RESERVED_CASH_RUNTIME_COUNT = 1
SKIP_AND_CONTINUE_RUNTIME_ACTION_EFFECTIVE = YES
ACTIVE_BATCH_RESERVED_NOTIONAL_WITHIN_CASH = YES
RESERVED_CASH_REVIEW_RECURRENCE = NO
POST_AK3R2B_SUBMIT_HALT_CLASSIFICATION = SUBMIT_GUARD_AUTHORITY_GAP
AK3R2B_RUNTIME_ACTION_EFFECTIVE = PARTIAL
KNOWN_RUNTIME_DEFECT = YES
KNOWN_AUTHORITY_DEFECT = YES
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK3R2C0
```

## Recommended Next Task

```text
Phase30-AK3R2C1 - Submit Guard One-Lot Quantity Handoff Focused Repair
```
