# Phase28-D33: Portfolio Construction REDUCE Partial-Target Repair Design

## Primary Judgment

```text
PHASE28_D33_CANONICAL_REDUCE_PARTIAL_TARGET_DESIGN_COMPLETE_D34_READY
```

Supporting Judgments:

```text
PHASE28_D33_EXISTING_REDUCE_INTENSITY_AUTHORITY_REUSE_APPROVED
PHASE28_D33_SHARED_REDUCE_AUTHORITY_REFACTOR_REQUIRED
```

Implementation Entry Decision:

```text
APPROVED_FOR_D34_DESIGN_CONTRACT_IMPLEMENTATION
```

No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## Authority Answer

| Layer | Ownership |
| --- | --- |
| PM | `REDUCE` intent and `reduce_intensity` evidence |
| Portfolio Construction | canonical remaining target membership / `target_weight` |
| Position Sizing | target-weight-to-quantity and transaction-delta feasibility |
| Sell Planning | execution order construction / compatible legacy quantity contract |

This matches the Strategy and PC/PS boundary contracts: PM owns existing-position directional intent, PC owns target portfolio and target weight, PS owns target notional/quantity conversion, and Runtime Planning only maps executable intent.

## Existing REDUCE Intensity Authority

PM `reduce_intensity` is formal decision evidence in the Runtime PM handoff. For 77760:

```text
decision = REDUCE
reduce_intensity = LIGHT
runtime_quantity_authority = SELL_PLANNING_REDUCE_QUANTITY_CONTRACT
```

The active Sell Planning quantity contract defines:

```text
LIGHT  = 0.25
MEDIUM = 0.33
STRONG = 0.50
```

These ratios are reusable only if D34 avoids blind duplication. The selected design is to promote the existing constants into a shared canonical REDUCE intensity authority used by both Strategy PC/PS and compatible Sell Planning.

## Selected Option

Primary Recommendation:

```text
Option B — Shared canonical REDUCE quantity / intensity contract
```

Why:

- uses existing PM/Sell Planning authority instead of inventing ratios
- avoids duplicating REDUCE strategy logic in Portfolio Construction
- preserves PC target-weight ownership
- preserves PS quantity conversion ownership
- keeps Production/Demo/Historical common runtime semantics aligned

Rejected as primary:

- Option A: acceptable behaviorally, but risks copying Sell Planning constants into PC.
- Option C: makes PS decide strategic target reduction, conflicting with PC target-weight ownership.
- Option D: safe but leaves REDUCE non-functional.

## Canonical REDUCE Contract

For a current position with PM `REDUCE`:

```text
reduce_fraction = canonical_reduce_fraction(reduce_intensity)
remaining_target_weight = current_weight * (1 - reduce_fraction)
released_reduce_capacity = current_weight - remaining_target_weight
```

Required guard:

```text
0 < remaining_target_weight < current_weight
```

If intensity is missing or unknown:

```text
Portfolio Construction REVIEW_REQUIRED
```

If PM action is `EXIT`:

```text
target_weight = 0
```

`STRONG` remains REDUCE, not EXIT:

```text
STRONG = 0.50
remaining_target_weight = 50% of current_weight
```

No REDUCE intensity maps to full liquidation.

## Downstream Quantity Contract

D33 separates:

```text
strategic REDUCE target
```

from:

```text
executable sell quantity
```

For multi-lot positions, PS should produce a negative partial quantity delta when the lot-rounded transaction is executable.

For single-lot or otherwise non-executable partial REDUCE:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
REDUCE_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT
Runtime Planning = NO_ORDER or REVIEW_REQUIRED
```

Forbidden:

```text
target_quantity_candidate = 0
quantity_delta_candidate = -current_quantity
```

unless PM action is `EXIT` or another explicit full-liquidation authority exists.

## Design Replay

### 77760

```text
business_date = 2023-04-11
current_weight = 0.053147
current_quantity = 100
reduce_intensity = LIGHT
reduce_fraction = 0.25
remaining_target_weight = 0.039860
released_weight = 0.013287
raw reduce quantity = 25 shares
tradable_unit = 100
rounded executable sell quantity = 0
```

Expected downstream behavior:

```text
strategic REDUCE retained
no forced EXIT
no SELL_EXIT
NO_ORDER or REVIEW_REQUIRED for non-executable partial REDUCE
```

### 43880

```text
business_date = 2023-04-07
current_weight = 0.127745
current_quantity = 100
reduce_intensity = LIGHT
reduce_fraction = 0.25
remaining_target_weight = 0.095809
released_weight = 0.031936
raw reduce quantity = 25 shares
tradable_unit = 100
rounded executable sell quantity = 0
```

Expected downstream behavior is the same:

```text
strategic REDUCE retained
no forced EXIT
NO_ORDER or REVIEW_REQUIRED due to single-lot partial reduction infeasibility
```

## D28 Interaction

REDUCE should be resolved before incremental budget reconciliation:

```text
resolve existing target changes
↓
calculate released REDUCE capacity
↓
calculate baseline existing requirement
↓
allocate ADD / BUY_NEW incremental budget
```

For REDUCE:

```text
baseline_existing_weight = remaining_target_weight
released_reduce_capacity = current_weight - remaining_target_weight
```

D28 may reuse released capacity for accepted ADD and BUY_NEW. That is intended.

## D31 Compatibility

D31 remains downstream. D34 must give D31 a positive remaining PC target for REDUCE, then D31/PS must preserve non-executable partial REDUCE as no-order/review rather than full negative delta.

The D31 contract remains:

```text
explicit lower PC target -> partial negative delta when executable
non-executable REDUCE -> no forced EXIT
```

## D25 Compatibility

D25 remains unchanged:

```text
PM REDUCE + partial negative delta -> SELL_REDUCE
PM REDUCE + target zero + no full liquidation authority -> UNRESOLVED / REVIEW_REQUIRED
PM EXIT + target zero -> SELL_EXIT
```

D34 must not weaken the full-liquidation guard.

## Config / Schema / Threshold Impact

Preferred D34 impact:

```text
Config change required: NO
Schema change required: NO
Threshold change required: NO
```

D34 may perform a code authority refactor:

```text
move existing REDUCE_INTENSITY_RATIOS into a shared canonical module
```

This is not a threshold change if values are unchanged and existing lineage is preserved.

## Required D34 Fixtures

1. LIGHT REDUCE with multi-lot position -> partial SELL_REDUCE.
2. MEDIUM REDUCE -> partial SELL_REDUCE.
3. STRONG REDUCE -> partial SELL_REDUCE, not EXIT.
4. LIGHT REDUCE on 100-share single-lot position -> no forced EXIT.
5. 77760 reproduction -> no full liquidation.
6. 43880 reproduction -> no full liquidation.
7. EXIT remains full SELL_EXIT.
8. HOLD remains no SELL.
9. ADD remains BUY_ADD-capable.
10. REDUCE released capacity flows into D28 budget.
11. D31 baseline transaction-delta regression.
12. D25 full-liquidation guard regression.

## Next Phase

```text
Phase28-D34: Canonical REDUCE Intensity Authority Integration Implementation
```

Minimal D34 scope:

```text
1. Create / expose shared canonical REDUCE intensity authority with existing ratios unchanged.
2. PC consumes PM reduce_intensity for REDUCE remaining_target_weight.
3. D28 uses REDUCE remaining target as baseline.
4. PS preserves non-executable partial REDUCE without full liquidation.
5. Sell Planning continues to use the same shared authority.
```

## Final Judgment

```text
Primary Judgment: PHASE28_D33_CANONICAL_REDUCE_PARTIAL_TARGET_DESIGN_COMPLETE_D34_READY
Existing reduce_intensity authority: YES
Existing ratios reusable: YES, via shared authority refactor
Selected Option: Option B
REDUCE authority owner: PM intent/intensity + PC remaining target + PS quantity + Sell Planning execution
Config change required: NO
Schema change required: NO
Threshold change required: NO
Implementation changed: false
Resume executed: false
Fresh run executed: false
Long Historical executed: false
Runtime mutated: false
Next Phase: Phase28-D34 Canonical REDUCE Intensity Authority Integration Implementation
```
