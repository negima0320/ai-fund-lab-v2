# Phase28-D38: Dynamic Gross Exposure Existing-Baseline Transition Contract Design

## Primary Judgment

```text
PHASE28_D38_PASSIVE_CONVERGENCE_TRANSITION_CONTRACT_DESIGN_COMPLETE_D39_READY
```

Supporting judgments:

```text
PHASE28_D38_EXISTING_BASELINE_OVER_TARGET_DIRECTIONALITY_DESIGN_COMPLETE
PHASE28_D38_ACTIVE_POLICY_DERISK_DEFERRED
```

Implementation Entry Decision:

```text
READY
```

## Scope

This phase is design-only and read-only.

No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## Accepted D37 Inputs

D37 established:

```text
target_gross_exposure = portfolio-level target/cap for target allocation and incremental deployment
target_gross_exposure != direct sell authority
```

Authority boundaries:

```text
Portfolio Policy may set target gross exposure.
Portfolio Policy may not choose sell symbols or directly sell.
Position Management owns HOLD / ADD / REDUCE / EXIT.
Portfolio Construction may consume PM intent and determine target_weight.
Portfolio Construction may not override HOLD / ADD into REDUCE / EXIT.
Position Sizing sizes target to quantity delta.
Runtime Planning materializes executable intent.
```

D37 failing example:

```text
business_date = 2023-06-01
target_gross_exposure = 0.54
current existing exposure before PM = 0.693506
baseline_existing_required_weight after PM REDUCE = 0.677443
gap after PM REDUCE = 0.137443
```

## Selected Transition Mode

```text
PASSIVE_CONVERGENCE
```

Formal intent:

```text
When dynamic target_gross_exposure falls below PM-authorized retained existing baseline,
do not sell positions without PM sell authority,
do not increase risk further,
and allow PM REDUCE / EXIT to move exposure toward target.
```

## Formal Over-Target State

D38 defines:

```text
OVER_TARGET_EXISTING_BASELINE
```

Condition:

```text
baseline_existing_required_weight > target_gross_exposure
```

and baseline is composed only from:

```text
PM HOLD retained baseline
PM ADD retained baseline
PM REDUCE resolved remaining target
PM EXIT resolved zero target
```

This state must not automatically mean Portfolio Construction `BLOCK`.

## Directionality Contract

Aggregate exposure states:

```text
UNDER_TARGET
AT_TARGET
OVER_TARGET_EXISTING_BASELINE
OVER_TARGET_DUE_TO_INVALID_INCREMENT
```

Valid over-target sources:

```text
market movement
dynamic policy target reduction
valid PM lifecycle actions
retained existing baseline
```

Invalid over-target sources:

```text
new BUY allocation
positive BUY_ADD increment
other positive allocation accepted while over target
```

Core invariant:

```text
If aggregate retained exposure > target_gross_exposure:
positive incremental gross exposure = 0
```

## Incremental Budget

D28 formula is preserved:

```text
available_incremental_budget =
max(target_gross_exposure - baseline_existing_required_weight, 0)
```

When baseline is above target:

```text
available_incremental_budget = 0
```

The meaning is:

```text
zero capacity
not negative
not global BLOCK
```

Normal under-target behavior remains unchanged:

```text
baseline = 0.40
target = 0.72
available_incremental_budget = 0.32
ADD / BUY_NEW may compete for allocation
```

At target:

```text
baseline = target
available_incremental_budget = 0
PASS
```

## BUY_NEW

When:

```text
baseline_existing_required_weight > target_gross_exposure
```

then:

```text
BUY_NEW accepted allocation = 0
```

Semantic reason:

```text
NO_NEW_EXPOSURE_WHILE_OVER_TARGET
```

Do not block the whole Portfolio Construction artifact solely because BUY_NEW cannot be allocated.

## ADD

For existing PM `ADD` while over target:

```text
PM ADD remains semantically valid.
existing baseline is preserved.
accepted_incremental_weight = 0.
```

Expected downstream:

```text
Position Sizing:
current quantity retained
quantity_delta_candidate = 0

Runtime Planning:
NO_ACTION
```

This does not mutate PM ADD into HOLD. It only sets portfolio-level incremental capital eligibility to zero.

## HOLD

For PM `HOLD` while over target:

```text
current baseline retained
no synthetic REDUCE
no synthetic SELL
no global BLOCK
```

## REDUCE

For PM `REDUCE` while over target:

```text
execute canonical D34 partial reduction
```

Accepted D34 ratios remain:

```text
LIGHT  = 0.25
MEDIUM = 0.33
STRONG = 0.50
```

The result may still be over target:

```text
current = 0.70
target = 0.54
REDUCE result = 0.65
expected = PASS
```

Reason:

```text
risk-reducing valid PM action
```

No REDUCE intensity maps to full liquidation.

## EXIT

For PM `EXIT` while over target:

```text
target_weight = 0
SELL_EXIT remains allowed downstream when executable
```

D25 full-liquidation authority remains required:

```text
FULL_LIQUIDATION_ALLOWED =
PM_EXIT
OR explicit higher-priority liquidation authority
```

Forbidden:

```text
HOLD -> SELL_EXIT
ADD -> SELL_EXIT
REDUCE -> SELL_EXIT
```

## Invalid Positive Increment

If positive incremental exposure appears while over target:

```text
baseline = 0.50
target = 0.54
positive increment = 0.08
final = 0.58
```

Expected:

```text
BLOCK / fail-closed
```

State:

```text
OVER_TARGET_DUE_TO_INVALID_INCREMENT
```

This preserves aggregate exposure validation for newly-created over-allocation.

## BUY / SELL Independence

Passive Convergence must preserve:

```text
BUY_NEW blocked by zero allocation
BUY_ADD blocked by zero increment
SELL_REDUCE allowed by PM REDUCE
SELL_EXIT allowed by PM EXIT
```

Do not globally block safe no-action or valid sell-side de-risking merely because retained baseline remains over target.

## 2023-06-01 Design Replay

Input:

```text
target_gross_exposure = 0.54
current existing exposure before PM = 0.693506
baseline_existing_required_weight after PM REDUCE = 0.677443
gap = 0.137443
```

Expected per-symbol behavior:

```text
21340 ADD    -> baseline retain, increment 0
30410 ADD    -> baseline retain, increment 0
59550 ADD    -> baseline retain, increment 0
76470 HOLD   -> baseline retain
93990 REDUCE -> LIGHT partial reduction executes; target 0.048188
94320 ADD    -> baseline retain, increment 0
BUY_NEW      -> allocation 0
```

Expected aggregate:

```text
total_target_weight = 0.677443
state = OVER_TARGET_EXISTING_BASELINE
Portfolio Construction != BLOCK solely because total_target_weight > 0.54
```

This is a PASS in design.

## Cash Reserve Semantics

If:

```text
cash_reserve = 0.46
```

but actual cash is below that because retained positions exceed the dynamic target, Portfolio Construction must not synthesize cash by unauthorized sales.

Passive Convergence expresses the regime shift immediately as:

```text
incremental budget = 0
BUY_NEW blocked
BUY_ADD blocked
PM REDUCE / EXIT permitted
```

## Active De-Risk Boundary

Explicitly deferred:

```text
Policy target decrease
-> aggregate de-risk request
-> PM consumes request
-> PM chooses REDUCE / EXIT by existing evidence
-> PC executes resulting PM intents
```

This is not required for D39. It is a separate authority layer and must not be smuggled into Portfolio Construction as forced sell-symbol selection.

## Compatibility

D25:

```text
HOLD / ADD cannot become SELL_EXIT
REDUCE cannot become SELL_EXIT
EXIT remains SELL_EXIT
```

D28:

```text
baseline calculation unchanged
available_incremental_budget formula unchanged
ADD / BUY_NEW competition unchanged when baseline <= target
only baseline > target global BLOCK boundary changes
```

D31:

```text
ADD zero increment retains existing quantity
quantity_delta_candidate = 0
```

D34:

```text
canonical REDUCE intensity preserved
LIGHT / MEDIUM / STRONG partial reduction preserved
```

D36:

```text
existing single-name baseline above cap may be retained with zero positive delta
aggregate retained baseline above lowered target may be retained with zero positive aggregate delta
```

## D39 Implementation Scope

Next phase:

```text
Phase28-D39 Portfolio Construction Existing-Baseline Over-Target Passive Convergence Implementation
```

Preferred minimal files:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
tests/strategy/test_phase22_e_portfolio_construction.py
```

Actual test location confirmed:

```text
tests/strategy/test_phase22_e_portfolio_construction.py
```

Avoid changes to:

```text
Portfolio Policy
Position Management
Position Sizing
Runtime Planning
Sell Planning
Config
Schema
Thresholds
Pending
Approval
Submit
Broker
```

## D39 Test Matrix

Minimum tests:

```text
1. baseline < target -> existing behavior unchanged
2. baseline == target -> zero incremental budget, PASS
3. retained baseline > target -> PASS passive convergence
4. BUY_NEW while over target -> zero allocation
5. ADD while over target -> baseline preserved, increment zero
6. HOLD while over target -> baseline preserved
7. REDUCE while over target -> partial reduction allowed
8. EXIT while over target -> exit allowed
9. REDUCE remains above target after reduction -> PASS
10. positive increment causing over-target -> BLOCK
11. 2023-06-01 exact replay
12. D28 regression
13. D31 regression
14. D34 regression
15. D36 regression
16. D25 regression
17. BUY/SELL independence regression
```

## Evidence

```text
reports/phase28_d38_dynamic_gross_exposure_existing_baseline_transition_contract_design/
reports/phase_reports/phase28_d38_dynamic_gross_exposure_existing_baseline_transition_contract_design.json
```

Required evidence files produced:

```text
passive_convergence_contract.json
aggregate_exposure_directionality_contract.json
incremental_budget_over_target_contract.json
buy_new_over_target_contract.json
add_over_target_contract.json
hold_over_target_contract.json
reduce_over_target_contract.json
exit_over_target_contract.json
20230601_design_replay.json
invalid_positive_increment_contract.json
buy_sell_independence_contract.json
active_derisk_future_boundary.json
d25_compatibility.json
d28_compatibility.json
d31_compatibility.json
d34_compatibility.json
d36_compatibility.json
d39_test_matrix.json
implementation_scope.json
open_gap_inventory.json
next_phase_contract.json
```

## Final Status

```text
Config change required = false
Schema change required = false
Threshold change required = false
Implementation changed = false
Resume executed = false
Fresh run executed = false
Long Historical executed = false
Runtime mutated = false
```
