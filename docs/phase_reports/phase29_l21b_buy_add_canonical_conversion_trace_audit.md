# Phase29-L21B - BUY_ADD Canonical Conversion Trace Audit

Task ID: `Phase29-L21B`

Mode:

```text
READ-ONLY ROOT CAUSE / CONVERSION TRACE AUDIT
NO IMPLEMENTATION
NO CURRENT RUN MUTATION
NO RESUME / FRESH-RUN / RUN / PENDING_LIFECYCLE / REPAIR
NO LONG HISTORICAL EXECUTION
```

## Primary Judgment

```text
PHASE29_L21B_BUY_ADD_SUPPLY_COLLAPSES_BEFORE_RUNTIME_PLANNING_NO_MAPPING_DEFECT_CONFIRMED
```

The observed `Runtime BUY_ADD = 0` is not caused by a Runtime Planning mapping defect in the materialized evidence. The canonical mapper still maps positive quantity delta on an existing current position to `BUY_ADD`.

The apparent L21A tension came from mixing two different concepts:

```text
membership_intent = ADD_CANDIDATE
```

is often a new BUY candidate row, not necessarily an existing-position ADD. When restricted to true existing-position PM `ADD`, every row had `quantity_delta_candidate = 0`, so Runtime Planning correctly emitted `NO_ACTION`.

Root chain:

```text
PM ADD rows = 50
PC pre-lot ADD target/increment triggered = 23
PC final target increased after L19 = 0
PS positive delta for PM ADD = 0
Runtime BUY_ADD = 0
```

Primary root classification:

```text
PRIMARY:
PC_INCREMENTAL_INVESTMENT_NOT_TRIGGERED

SECONDARY:
LOT_CONCENTRATION_BLOCK_DOMINANT

NOT CONFIRMED:
RUNTIME_PLANNING_BUY_ADD_MAPPING_GAP
EXISTING_POSITION_MEMBERSHIP_GAP
PENDING_CONFLICT_SUPPRESSION
```

## Target Run

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T113809030985Z
```

Run state at read time:

```text
status = HALT
next_job = 2022-10-25:submit
completed_business_days = 50
first_completed_day = 2022-08-10
last_completed_day = 2022-10-24
```

The run advanced after L21A. This audit used only materialized completed days and did not mutate the run.

## Evidence Window

Inspected all completed days under:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T113809030985Z/daily/
```

Primary artifacts:

```text
strategy/position_management.json
strategy/portfolio_construction.json
strategy/position_sizing.json
strategy/runtime_planning.json
morning/pending_generation_evidence.json
submit/runtime_manifest.json
execution/fills.json
```

Read-only source contract references:

```text
src/ai_fund_lab_v2/strategy/runtime_planning.py
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
```

## Required Funnel Table

| Stage | Count | Drop from prior | Drop rate | Dominant drop reason |
|---|---:|---:|---:|---|
| PM ADD | 50 | - | - | Existing-position PM intent observed |
| PC pre-lot target/increment increased | 23 | 27 | 54.0% | Expected edge / incremental value fail-closed |
| PC final target increased after L19 | 0 | 23 | 100.0% | `minimum_lot_exceeds_concentration_cap` |
| PS positive delta | 0 | 0 | n/a | No final target increase reached PS |
| Lot executable | 0 | 0 | n/a | All PM ADD preflights were concentration-blocked |
| Runtime BUY_ADD | 0 | 0 | n/a | Correct `NO_ACTION` from zero delta |
| Pending BUY_ADD | 0 | 0 | n/a | No Runtime BUY_ADD candidate |
| Submitted BUY_ADD | 0 | 0 | n/a | No Pending BUY_ADD |
| Filled BUY_ADD | 0 | 0 | n/a | No Submitted BUY_ADD |

## PM ADD Count

Existing-position PM action distribution:

| PM action | Count |
|---|---:|
| ADD | 50 |
| HOLD | 64 |
| REDUCE | 10 |
| EXIT | 8 |
| NO_ACTION | 0 |

The ADD supply is concentrated in true existing positions. The dominant ADD symbol is the continuing existing campaign, especially `94320`, with later rows also reflecting changing held names after fills/exits.

## PC Target Increase Count

For the 50 PM ADD rows:

| PC condition | Count |
|---|---:|
| `add_allocation_eligibility_status = PASS` | 23 |
| `add_allocation_eligibility_status = FAIL_CLOSED` | 27 |
| `incremental_investment_value_state = POSITIVE` | 24 |
| `opportunity_cost_status = PASS` | 50 |
| pre-lot target/increment increased | 23 |
| final target increased after L19 | 0 |

Fail-closed drivers:

| Driver | Count |
|---|---:|
| `expected_edge = FAIL_CLOSED` | 26 |
| `incremental_value = FAIL_CLOSED` | 26 |
| `ADD_INCREMENTAL_VALUE_UNKNOWN` | 26 |
| `ADD_EXPECTED_EDGE_WEAKENING` | 23 |
| `ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED` | 3 |

Interpretation:

```text
Phase28-C bridge is present.
It passes on 23 rows before lot-aware final reallocation.
It fail-closes on 27 rows before target increase.
```

## PS Positive Delta Count

For true PM ADD rows:

| Position Sizing condition | Count |
|---|---:|
| PM ADD rows with `quantity_delta_candidate > 0` | 0 |
| PM ADD rows with `quantity_delta_candidate = 0` | 50 |
| PM ADD rows missing quantity delta | 0 |

Representative PS reasons:

```text
ADD_TARGET_WEIGHT_UNCHANGED
ADD_INCREMENT_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT
ADD_TARGET_NOTIONAL_DELTA_ZERO
```

This means there is no observed case where Runtime Planning received a true existing-position positive ADD delta and failed to map it to `BUY_ADD`.

## Lot Executable Count

For PM ADD:

| L19 / lot condition | Count |
|---|---:|
| BUY_ADD lot preflight rows | 23 |
| `EXECUTABLE_NOW` | 0 |
| `CONCENTRATION_BLOCKED` | 23 |
| `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX` | 23 |
| `MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX` | 0 |
| L19 executable quantity delta | 0 |

L19 causality:

```text
L19 did not erase executable BUY_ADD evidence.
It explicitly classified all pre-lot PM ADD increments as Strategy-cap concentration blocked while still within Safety hard max.
```

## Runtime Planning Count

Runtime Planning aggregate across completed days:

| Planning intent | Count |
|---|---:|
| BUY_NEW | 21 |
| BUY_ADD | 0 |
| SELL_REDUCE | 0 |
| SELL_EXIT | 8 |
| NO_ACTION | 124 |
| NO_ORDER | 22 |

Runtime Planning contract check:

```text
quantity_delta_candidate > 0 and code in current_codes -> BUY_ADD
quantity_delta_candidate > 0 and code not in current_codes -> BUY_NEW
quantity_delta_candidate = 0 and current membership resolved -> NO_ACTION
```

Observed PM ADD rows landed in:

```text
planning_intent = NO_ACTION
planning_reason =
current_position_membership_resolved:current_portfolio_member;
current_position_zero_delta_maps_to_no_action
```

This is consistent with the current implementation and Phase28 contract.

## Pending / Submit / Execution

Pending generation:

| Pending intent | Count |
|---|---:|
| BUY_NEW | 21 |
| SELL_EXIT | 8 |
| BUY_ADD | 0 |

Execution fills:

| Fill source / side | Count |
|---|---:|
| BUY | 11 |
| EXIT | 8 |
| REDUCE | 9 |
| BUY_ADD | 0 |

No BUY_ADD reached Pending, Submit, or Execution.

## Critical Trace Set

### Case A - PM ADD -> PC increased -> PS positive -> Runtime BUY_ADD missing

```text
NOT OBSERVED
```

No true PM ADD row had `quantity_delta_candidate > 0`. Therefore no Runtime Planning mapping defect is proven.

### Case B - PM ADD -> PC target unchanged

Representative:

```text
date = 2022-08-12
symbol = 94320
PM action = ADD
PC current_weight = 0.134747
PC post_add_target_weight = 0.134747
PC target_weight = 0.134747
add_allocation_eligibility_status = FAIL_CLOSED
incremental_investment_value_state = UNKNOWN
PS current_quantity = 900
PS target_quantity_candidate = 900
PS quantity_delta_candidate = 0
Runtime Planning = NO_ACTION
```

Reason:

```text
ADD_EXPECTED_EDGE_UNKNOWN_FAIL_CLOSED
ADD_INCREMENTAL_VALUE_UNKNOWN
```

Other fail-closed rows mostly show:

```text
ADD_EXPECTED_EDGE_WEAKENING
ADD_INCREMENTAL_VALUE_UNKNOWN
```

### Case C - PC pre-lot target increased -> L19 concentration block -> PS zero

Representative:

```text
date = 2022-09-26
symbol = 94320
PM action = ADD
PC current_weight = 0.141294
PC post_add_target_weight = 0.180000
PC requested_incremental_weight = 0.038706
PC accepted_incremental_weight = 0.038706
PC final target_weight after L19 = 0.141294
lot_aware_accepted_incremental_weight = 0.000000
add_allocation_eligibility_status = PASS
incremental_investment_value_state = POSITIVE
opportunity_cost_status = PASS
lot_first_rebatch_skip_reason = minimum_lot_exceeds_concentration_cap
L19 boundary = DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX
PS current_quantity = 900
PS target_quantity_candidate = 900
PS quantity_delta_candidate = 0
Runtime Planning = NO_ACTION
```

This is the important L21B correction: the bridge can increase pre-lot intent, but L19 final reallocation returns the target to baseline because the minimum executable ADD lot exceeds remaining Strategy cap headroom.

## Existing Position Membership Audit

No existing-position membership propagation gap was found.

Observed Runtime Planning reason on PM ADD rows:

```text
current_position_membership_resolved:current_portfolio_member
current_position_zero_delta_maps_to_no_action
```

Count:

```text
existing-position membership gap = 0
existing PM ADD misclassified as BUY_NEW = 0
```

The `BUY_NEW` rows are new candidates with `membership_intent = ADD_CANDIDATE`, not existing-position PM ADD rows.

## Pending Conflict Interaction

No PM ADD row showed `existing_pending_conflict` as the suppressing cause.

Count:

```text
PM ADD pending conflict suppressions = 0
```

The lack of BUY_ADD occurs before Pending because no PM ADD row became quantity-positive.

## Phase28-C Status

```text
PARTIALLY_ACTIVE
```

Rationale:

```text
ACTIVE:
PM ADD evidence and add investment evidence are present.
Expected edge / incremental value / opportunity cost checks are materialized.
23 rows pass ADD eligibility before lot-aware final reallocation.

NOT FULLY CONVERTING:
0 rows survive to final PC target increase, PS positive delta, or Runtime BUY_ADD.

NO REGRESSION CONFIRMED:
No prior evidence in this audit proves this exact run/contract previously produced executable BUY_ADD and later lost it.
```

## L19 Causality

```text
L19_CAUSAL_AS_SECONDARY_EXECUTION_BOUNDARY
```

L19 is not a mapping bug. It is the explicit boundary that prevents the 23 pre-lot ADD increments from becoming final executable ADDs:

```text
minimum lot > remaining Strategy cap headroom
within Safety hard max
=> DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX
=> final ADD increment = 0
```

This preserves the Phase29-L19 safety contract.

## Runtime Planning Mapping Audit

Intended contract:

```text
existing position + positive quantity_delta_candidate -> BUY_ADD
existing position + zero quantity_delta_candidate -> NO_ACTION
```

Current implementation:

```text
_resolve_intent() maps positive quantity_delta to BUY_ADD when code is in current_codes.
_resolve_quantity_status() then materializes executable quantity only when sizing is nonzero.
```

Observed evidence:

```text
No PM ADD row had positive quantity_delta_candidate.
All PM ADD rows mapped to NO_ACTION with resolved current-position membership.
```

Conclusion:

```text
RUNTIME_PLANNING_BUY_ADD_MAPPING_GAP = NOT_CONFIRMED
```

## Root Cause Classification

| Classification | Judgment | Evidence |
|---|---|---|
| PM_ADD_SUPPLY_TOO_THIN | NO | PM ADD rows exist: 50 |
| PC_INCREMENTAL_INVESTMENT_NOT_TRIGGERED | PRIMARY | 27 / 50 fail closed before pre-lot increase |
| PC_TARGET_WEIGHT_BRIDGE_GAP | NO | Bridge passes on 23 rows before L19 |
| PS_POSITIVE_DELTA_LOST | NO | PS never receives final target increase for PM ADD |
| LOT_CONCENTRATION_BLOCK_DOMINANT | SECONDARY | 23 / 23 ADD lot preflights concentration-blocked |
| RUNTIME_PLANNING_BUY_ADD_MAPPING_GAP | NO | Case A absent |
| EXISTING_POSITION_MEMBERSHIP_GAP | NO | membership resolved in Runtime Planning |
| PENDING_CONFLICT_SUPPRESSION | NO | no ADD suppression by pending conflict |
| EXPECTED_BY_CURRENT_STRATEGY | YES | fail-closed ADD + Strategy cap lot boundary |

## Architecture Check

If a future repair is desired, it should not be a BUY_ADD-only Runtime Planning special case. The current general contract is already shaped correctly:

```text
position delta sign
+ current position membership
+ canonical action taxonomy
```

The unresolved performance question is upstream of Runtime Planning:

```text
Should Strategy allow any discrete-lot ADD when current_weight is below Strategy cap
but the minimum executable lot would cross the Strategy cap while remaining within Safety hard max?
```

That is a Strategy/Portfolio Construction policy design question, not a Runtime mapper patch.

## Required Final Fields

```text
Primary Judgment:
PHASE29_L21B_BUY_ADD_SUPPLY_COLLAPSES_BEFORE_RUNTIME_PLANNING_NO_MAPPING_DEFECT_CONFIRMED

Target Run:
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T113809030985Z

Evidence Window:
2022-08-10 through 2022-10-24, 50 completed business days

PM ADD Count:
50

PC Target Increase Count:
pre-lot = 23
final after L19 = 0

PS Positive Delta Count:
0

Lot Executable Count:
0

Runtime BUY_ADD Count:
0

Pending BUY_ADD Count:
0

Submitted BUY_ADD Count:
0

Filled BUY_ADD Count:
0

Primary Drop Boundary:
PM ADD -> PC incremental investment eligibility / pre-lot target increase

Primary Drop Reason:
Expected edge weakening or unknown; incremental investment value unknown

Secondary Drop Boundary:
PC pre-lot ADD increase -> L19 lot-aware final reallocation

Secondary Drop Reason:
minimum_lot_exceeds_concentration_cap / DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX

Phase28-C Status:
PARTIALLY_ACTIVE

L19 Causality:
SECONDARY_CAUSAL_BOUNDARY_NOT_MAPPING_BUG

Pending Conflict Causality:
NO

Regression Confirmed:
NO

Architecture Gap:
NO_RUNTIME_PLANNING_GAP; STRATEGY_POLICY_DESIGN_QUESTION_EXISTS

Repair Required:
NO_RUNTIME_MAPPING_REPAIR

Recommended Next Task:
Phase29-L21C - ADD Strategy Cap Boundary Policy Design Audit

Current Run Mutation:
NO

Long Historical Executed:
NO
```

## Recommended Next Task

```text
Phase29-L21C - ADD Strategy Cap Boundary Policy Design Audit
```

Recommended scope:

```text
READ-ONLY / DESIGN-FIRST.
Evaluate whether ADD should remain strictly blocked when the minimum executable lot
would cross the Strategy cap but remain inside the Safety hard max, or whether a
separate capped-lot ADD policy should be designed.
```

No Runtime Planning repair is recommended from L21B evidence.
