# Phase30-AK9R1A - selected_position_amount Submit Guard Authority Audit

Task ID: `Phase30-AK9R1A`

Type: `READ_ONLY_AUTHORITY_AND_RESPONSIBILITY_AUDIT`

Target evidence:

```text
runtime-test-historical-extended-smoke-20260817T040435873521Z
2022-08-10
```

No implementation, guard deletion, Safety relaxation, Strategy cap change,
PC/PS change, threshold change, fresh Historical, long Historical, replay, or
target-run mutation was performed.

## Primary Judgment

```text
KNOWN_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
```

The `estimated amount exceeds selected_position_amount` review is not a clean
post-AK7R Submit responsibility for the eight AK9R0 BUY items. All eight have
PC `PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY` `PASS`, and
PS materialized the same executable quantity as `final_quantity_delta`.

Submit feasibility then compared the exact executable lot notional against a
lower top-level Position Sizing `selected_position_amount`, re-reviewing the
same investment sizing decision with a weaker continuous-notional artifact.

## Canonical Producer

```text
SELECTED_POSITION_AMOUNT_CANONICAL_PRODUCER =
  runtime_v2.position_sizing_authority from strategy.position_sizing /
  pending policy_context

SELECTED_POSITION_AMOUNT_SEMANTIC =
  continuous/incremental Position Sizing selected notional; not final discrete
  executable quantity authority, not Safety hard cap, not cash authority, and
  not an execution estimate.
```

The resolver derives it as:

```text
target_notional = row.target_notional or row.selected_position_amount
incremental_buy = row.incremental_buy_notional or row.remaining_add_capacity
selected_position_amount = max(incremental_buy, 0)
```

## Canonical Quantity Authority

```text
CANONICAL_EXECUTABLE_QUANTITY_AUTHORITY =
  PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY

PC_AUTHORIZED_QUANTITY_IS_FINAL_STRATEGY_ALLOCATION = YES

PS_ROLE =
  consume and preserve PC-authoritative executable quantity
```

AK7R made PC the capital allocation authority and PS the executable quantity
consumer. For the AK9R0 review population, PS `final_quantity_delta` equals the
PC authorized quantity in all eight rows.

## Submit Responsibility

```text
SUBMIT_SELECTED_POSITION_AMOUNT_CHECK_RESPONSIBILITY = CONDITIONAL
```

Submit should verify cash, buying power, dynamic exposure, Strategy cap,
Safety hard cap, canonical quantity consistency, pending consistency, broker
feasibility, and reservation-price authority.

`selected_position_amount` remains legitimate only as fallback / diagnostic
validation when canonical discrete executable quantity authority is absent,
invalid, stale, malformed, or inconsistent. It should not override an already
PC-authorized and PS-consumed discrete quantity.

## Review Population

```text
REVIEW_ITEM_COUNT = 8
REVIEW_ITEMS_WITH_VALID_PC_DISCRETE_AUTHORITY = 8
```

| Symbol | PC target notional | PC qty auth | PS qty | Est amount | Reserved | selected_position_amount | Strategy cap | Safety | Cash item-local | Review reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| 23880 | 52,632 | 300 PASS | 300 | 45,300 | 61,200 | 39,054 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |
| 47840 | 52,632 | 100 PASS | 100 | 45,000 | 52,800 | 28,776 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |
| 61980 | 52,632 | 100 PASS | 100 | 35,600 | 43,000 | 32,823 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |
| 76470 | 52,632 | 2,000 PASS | 2,000 | 52,000 | 112,000 | 38,679 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |
| 89180 | 50,000 | 5,000 PASS | 5,000 | 50,000 | 205,000 | 34,547 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |
| 94320 | 52,632 | 300 PASS | 300 | 44,940 | 59,640 | 42,661 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |
| 94340 | 52,632 | 300 PASS | 300 | 45,540 | 60,150 | 37,647 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |
| 95010 | 52,632 | 100 PASS | 100 | 50,000 | 56,900 | 33,322 | PASS | PASS | PASS | estimated amount exceeds selected_position_amount |

Evidence sources:

- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `submit/runtime_manifest.json`

## Counterfactual Safety Check

```text
OTHERWISE_FULLY_EXECUTABLE_REVIEW_COUNT = 8
```

All eight reviewed items are otherwise executable at the item-local authority
level when only the `selected_position_amount` comparison is ignored. PC
quantity authority, PS quantity, Strategy cap, Safety hard cap, cash, and
buying power all pass at each item's recorded reserved-current point.

Boundary note: all eight reviewed items plus all existing PASS items would
exceed aggregate cash. That should remain a cash-feasible batch / cash-pruning
responsibility, not a `selected_position_amount` responsibility.

## Double Authority

```text
SIZING_DOUBLE_AUTHORITY_CONFIRMED = YES
```

The conflict shape is:

```text
PC:     canonical discrete executable quantity = X, status PASS
PS:     final_quantity_delta = X
Submit: selected_position_amount says quantity X's executable notional is too large
```

This is the same sizing decision judged twice, with Submit using a weaker
continuous-notional artifact after a stronger discrete authority has passed.

## Historical Lineage

```text
SELECTED_POSITION_AMOUNT_GUARD_ORIGINAL_PURPOSE =
  fail-closed unauthorized notional overshoot guard before complete discrete
  executable authority propagation

GUARD_STILL_REQUIRED_AFTER_AK7R = CONDITIONAL
```

Phase29 L21T-G/H/K and Phase30 AK3R1 showed the same general class: exact lot
notional can exceed continuous selected notional unless the runtime consumer
uses canonical discrete authority. Those repairs kept fail-closed behavior for
missing or inconsistent authority while accepting formally authorized discrete
one-lot cases. AK7R extends that authority boundary to PC-authorized discrete
executable quantity.

## Recommended Boundary

```text
RECOMMENDED_AUTHORITY_BOUNDARY =
  PC/PS own Strategy allocation and executable quantity authority.
  Submit owns execution safety and authority-consistency verification.
```

Submit should consume canonical quantity rather than recompute the desired
investment size from `selected_position_amount`.

## Required Final Judgments

```text
SELECTED_POSITION_AMOUNT_CANONICAL_PRODUCER =
  runtime_v2.position_sizing_authority from strategy.position_sizing / policy_context

SELECTED_POSITION_AMOUNT_SEMANTIC =
  continuous/incremental Position Sizing selected notional; not final discrete executable quantity authority

CANONICAL_EXECUTABLE_QUANTITY_AUTHORITY =
  PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY consumed by PS

PC_AUTHORIZED_QUANTITY_IS_FINAL_STRATEGY_ALLOCATION = YES
SUBMIT_SELECTED_POSITION_AMOUNT_CHECK_RESPONSIBILITY = CONDITIONAL
REVIEW_ITEM_COUNT = 8
REVIEW_ITEMS_WITH_VALID_PC_DISCRETE_AUTHORITY = 8
OTHERWISE_FULLY_EXECUTABLE_REVIEW_COUNT = 8
SIZING_DOUBLE_AUTHORITY_CONFIRMED = YES

SELECTED_POSITION_AMOUNT_GUARD_ORIGINAL_PURPOSE =
  fail-closed unauthorized notional overshoot guard before complete discrete executable authority propagation

GUARD_STILL_REQUIRED_AFTER_AK7R = CONDITIONAL

RECOMMENDED_AUTHORITY_BOUNDARY =
  PC/PS allocation authority; Submit execution safety and authority-consistency verifier

KNOWN_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R1A
```

## Recommended Next Task

```text
Phase30-AK9R1B - Canonical Discrete Quantity selected_position_amount Guard Boundary Repair
```

