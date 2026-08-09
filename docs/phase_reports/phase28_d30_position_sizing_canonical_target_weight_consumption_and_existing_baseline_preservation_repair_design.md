# Phase28-D30: Position Sizing Canonical Target-Weight Consumption and Existing Baseline Preservation Repair Design

## Status

```text
COMPLETE
```

## Primary Judgment

```text
PHASE28_D30_EXISTING_POSITION_BASELINE_TRANSACTION_DELTA_REPAIR_DESIGN_COMPLETE_D31_READY
```

Implementation Entry Decision:

```text
APPROVED
```

## Core Architecture Answer

After Portfolio Construction emits canonical `target_weight`, Position Sizing does not have authority to modify that canonical target weight based on BUY Quality for existing HOLD / ADD baseline rows.

Evidence:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
Portfolio Construction -> target membership / target_weight
Position Sizing -> target_notional / target_quantity_candidate / quantity_delta_candidate

docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
Quality adjustment must not be applied twice across Portfolio Construction and Position Sizing.

docs/02_architecture/strategy_architecture_v1.md
Position Sizing must not reinterpret Opportunity score, rank, or candidate score
to decide investment target or relative weight.
```

The older Adaptive BUY Quality text allows Position Sizing to consume quality adjustment after Portfolio Construction acceptance, but D29 proved this is unsafe for existing-position baseline rows. D30 narrows that behavior:

```text
BUY Quality may remain valid for BUY_NEW and for explicitly accepted incremental ADD transaction sizing.
BUY Quality must not erase or reduce existing HOLD / ADD baseline quantity after Portfolio Construction has retained the position.
```

## BUY Quality Responsibility

| Case | BUY Quality role |
|---|---|
| BUY_NEW | May remain a new-buy eligibility/allocation input, unchanged by D31 unless a focused regression proves otherwise |
| Existing ADD incremental allocation | May size only the accepted incremental transaction, after PC has accepted incremental weight |
| Existing HOLD baseline | Must not modify canonical baseline target or quantity |
| Existing REDUCE | Must not create REDUCE; PM/PC explicit lower target is required |
| Existing EXIT | Must not weaken EXIT; PM EXIT + PC target zero remains full liquidation authority |

Classification:

```text
Position Sizing quality multiplier scope = VALID_FOR_BUY_NEW_AND_ACCEPTED_INCREMENTAL_ADD_ONLY
Current existing baseline application = LEGACY_REDUNDANT_AFTER_PC
```

## Existing Baseline Authority

For current positions, baseline quantity is authority-bearing runtime state:

```text
baseline_quantity = current_quantity
baseline_weight = current_weight or PC baseline_existing_weight
```

Portfolio Construction decides whether the baseline remains in target portfolio. Position Sizing must not independently decide an existing position no longer deserves to exist because quality is weak.

## Designed D31 Algorithm

Primary recommendation:

```text
Option D - Combined minimum repair
```

Implement in D31 as:

```text
remove duplicate quality modification for existing baseline
preserve existing baseline quantity for HOLD / ADD zero-increment
apply minimum meaningful notional and lot rules only to transaction delta
```

### HOLD

Condition:

```text
current_quantity > 0
pm_action = HOLD
membership_intent = RETAIN
weight_intent = MAINTAIN
no explicit REDUCE / EXIT authority
```

Contract:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
target_notional = current_notional or canonical retained baseline notional
Runtime Planning = NO_ACTION
```

BUY Quality `REJECT` or weak quality must not create a SELL.

### ADD With Zero Accepted Increment

Condition:

```text
current_quantity > 0
pm_action = ADD
membership_intent = RETAIN
accepted_incremental_weight = 0
```

Contract:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
Runtime Planning = NO_ACTION / retain
```

This preserves the fact that PM ADD was directional intent, but Portfolio Construction did not accept an executable increment.

### ADD With Positive Accepted Increment

Condition:

```text
current_quantity > 0
pm_action = ADD
accepted_incremental_weight > 0
```

Contract:

```text
baseline_quantity = current_quantity
incremental_target_notional =
  accepted_incremental_weight * canonical_capital_base
incremental_quantity =
  lot_round(incremental_target_notional / PIT reference_price)
target_quantity_candidate =
  current_quantity + incremental_quantity
quantity_delta_candidate =
  incremental_quantity
```

If incremental quantity is positive, Runtime Planning maps to BUY_ADD.

### Tiny ADD

Condition:

```text
accepted_incremental_weight > 0
but incremental transaction notional < minimum meaningful notional
or incremental lot quantity = 0
```

Contract:

```text
target_quantity_candidate = current_quantity
quantity_delta_candidate = 0
reason = ADD_INCREMENT_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT
Runtime Planning = NO_ACTION
```

No SELL is generated.

### REDUCE

Condition:

```text
current_quantity > 0
pm_action = REDUCE
PC target_weight < current_weight or membership_intent = REDUCE_CANDIDATE
```

Contract:

```text
derive explicit reduction quantity from PC lower target
0 < target_quantity_candidate < current_quantity when executable
quantity_delta_candidate < 0
Runtime Planning = SELL_REDUCE
```

If reduction is below lot/minimum transaction constraints, D31 should emit a non-executable REDUCE result with lineage, not silently convert to HOLD and not escalate to EXIT.

### EXIT

Condition:

```text
pm_action = EXIT
PC target_weight = 0
membership_intent in REMOVE_CANDIDATE / EXCLUDE
```

Contract:

```text
target_quantity_candidate = 0
quantity_delta_candidate = -current_quantity
Runtime Planning = SELL_EXIT
D25 full liquidation authority guard remains satisfied by PM EXIT
```

### UNRESOLVED

Condition:

```text
current_quantity > 0
PM / PC state unresolved
```

Contract:

```text
no implicit target zero
no SELL_EXIT
REVIEW_REQUIRED or preserve according to D25 / existing unresolved contract
```

## Minimum Meaningful Notional Contract

D31 must distinguish:

```text
total position notional
```

from:

```text
incremental transaction notional
```

For existing HOLD / ADD retention:

```text
minimum_meaningful_notional applies to new incremental order notional,
not to the existing baseline holding.
```

Therefore:

```text
incremental transaction below minimum
→ no executable incremental order
→ baseline retained
```

## Weight Drift Decision

D29 showed 94320:

```text
PC target_weight = 0.047587
current_quantity = 300
mechanical lot conversion from weight/equity/price = 200 shares
```

Cause class:

```text
valuation timing / equity and price authority / weight precision / lot rounding drift
```

D30 design decision:

```text
For existing HOLD and ADD zero-increment rows, current_quantity has baseline
precedence over mechanical target-weight-to-lot conversion.
```

This is not a Portfolio Construction override. It is a Position Sizing rule that recognizes PC target is expressing baseline retention, while current_quantity is the authoritative existing baseline quantity.

## Design Replays

### 83060

```text
PM = HOLD
current_quantity = 100
PC target_weight = 0.085181
quality_action = REJECT

Expected D31:
target_quantity_candidate = 100
quantity_delta_candidate = 0
runtime intent = NO_ACTION / HOLD
```

### 94320

```text
PM = ADD
current_quantity = 300
PC baseline target_weight = 0.047587
accepted_incremental_weight = 0

Expected D31:
target_quantity_candidate = 300
quantity_delta_candidate = 0
runtime intent = NO_ACTION / retain
```

### Positive ADD

```text
PM = ADD
current_quantity = 300
accepted_incremental_weight > 0
incremental notional >= minimum meaningful notional
incremental lot >= 1

Expected D31:
target_quantity_candidate > 300
quantity_delta_candidate > 0
runtime intent = BUY_ADD
```

### Tiny ADD

```text
PM = ADD
current_quantity = 300
accepted_incremental_weight > 0
increment below minimum or lot

Expected D31:
target_quantity_candidate = 300
quantity_delta_candidate = 0
runtime intent = NO_ACTION
```

### REDUCE

```text
PM = REDUCE
current_quantity = 300
PC explicit lower target

Expected D31:
0 < target_quantity_candidate < 300
quantity_delta_candidate < 0
runtime intent = SELL_REDUCE
```

### EXIT

```text
PM = EXIT
current_quantity = 300
PC target = 0

Expected D31:
target_quantity_candidate = 0
quantity_delta_candidate = -300
runtime intent = SELL_EXIT
D25 guard remains active and satisfied
```

## Repair Option Comparison

| Option | Judgment |
|---|---|
| A - Remove PS quality multiplier for existing positions | Necessary but incomplete. Does not solve 94320 baseline quantity drift/minimum-notional erasure alone. |
| B - Existing-position baseline quantity preservation layer | Necessary. Protects HOLD and zero-increment ADD from accidental SELL. |
| C - Split Position Sizing into baseline + transaction delta | Strong conceptual model; best long-term framing. |
| D - Combined minimum repair | Selected. Minimal enough for D31 while fixing both D29 defects. |

## D31 Scope

Primary file:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
```

Do not require changes to:

```text
Portfolio Construction
Runtime Planning
D19 PM wiring
D25 Full Liquidation Authority guard
D28 incremental budget reconciliation
BUY Quality model or thresholds
Config
Schema
```

## Required D31 Fixtures

```text
1. HOLD + BUY Quality REJECT -> baseline retained
2. ADD + zero accepted increment -> baseline retained
3. ADD + positive executable increment -> BUY_ADD
4. ADD + tiny increment -> baseline retained / no order
5. REDUCE -> partial SELL
6. EXIT -> full SELL
7. UNRESOLVED -> no SELL_EXIT
8. BUY_NEW quality behavior unchanged
9. 83060 reproduction
10. 94320 reproduction
11. D19 regression
12. D25 regression
13. D28 regression
14. Phase28-C regression
```

## Mutation Flags

```text
implementation_changed = false
config_changed = false
schema_changed = false
threshold_changed = false
resume_executed = false
fresh_run_executed = false
long_historical_executed = false
runtime_mutated = false
```

## Next Phase

```text
Phase28-D31 Position Sizing Existing-Position Baseline and Transaction-Delta Repair Implementation
```
