# Phase28-D54: BUY_ADD Evidence Availability and Lot-Aware Capital Conversion Design

## Primary Judgment

```text
PHASE28_D54_BUY_ADD_EVIDENCE_AND_LOT_AWARE_CONVERSION_DESIGN_COMPLETE
```

D54 is design-only. No implementation, config, schema, threshold, production strategy logic, PM logic, Portfolio Construction logic, Position Sizing logic, Runtime Planning, Submit Guard, Broker logic, fresh run, resume, long historical run, or runtime mutation was executed.

## D53 Findings Accepted

```text
D53 findings accepted = YES
Run = runtime-test-historical-smoke-20260808T015847315534Z
100BD Runtime = PASS
Compounding = FULL_COMPOUNDING_CONFIRMED
Active fixed 1,000,000 authority = NO
```

D54 does not redesign compounding or exposure targets.

## BUY_ADD Root Cause

```text
PM ADD = 191
PC positive ADD increment = 0
Runtime BUY_ADD = 0
```

Root cause classification:

```text
REQUIRED_PC_ADD_AUTHORITY_MISSING_OR_INCOMPATIBLE
```

PM ADD is an intent, not executable authorization. In the accepted run it means a current holding has PM evidence such as:

```text
strong_trend_continuation
opportunity_rank_still_high
no_loss_averaging
```

Those are useful inputs, but they are not equivalent to PC's required ADD authorization fields:

```text
campaign_continuation_status
expected_edge_improvement_state or baseline score comparison
incremental_investment_value_state
opportunity_cost_status
broker / concentration / capital / execution feasibility
```

The failures are partly cascading. `expected_edge` is missing because no same-campaign baseline is available to PC; `incremental_value` becomes UNKNOWN when expected edge is not PASS. `campaign_continuation` is independently missing as an explicit PC authority. Opportunity cost is separately evaluated and failed 15 times.

## Preferred BUY_ADD Design

```text
Unified ADD Investment Evidence Resolver / artifact consumed by Portfolio Construction
```

The resolver is production-common and fail-closed. It emits explicit evidence for:

```text
campaign_continuation_status
expected_edge_baseline_score
expected_edge_improvement_state
incremental_investment_value_state
opportunity_cost_status
no_loss_averaging_status
source lineage and business-date authority
```

PC remains the target-weight authority. PM ADD remains intent only. Missing, stale, incompatible, future-dated, or semantically invalid evidence remains fail-closed.

Design impact:

```text
production code change = YES
schema change = LIKELY_NEW_OR_ADDITIVE_EVIDENCE_CONTRACT
config change = NO
threshold change = NO
new producer = YES
```

## BUY_NEW Lot / Min-Notional Root Cause

D53 accepted funnel:

```text
PC positive BUY_NEW weights = 132
PS positive BUY_NEW quantities = 22
lot/min-notional blocks = 110
```

Current order of operations is:

```text
PC computes continuous target_weight
↓
PS computes target_notional
↓
PS computes minimum executable notional / tradable lot
↓
PS floors quantity to lot
↓
Runtime Planning emits BUY only when quantity_delta_candidate > 0
```

PC does not currently know reference price, trading unit, or minimum executable notional before allocating target weight. Therefore positive economic weights can become zero executable quantity.

## Preferred Lot-Aware Design

```text
Two-pass PC economic draft -> PS lot feasibility preflight -> PC final reallocation -> PS final sizing
```

Ownership remains clean:

```text
PC owns economic desirability, target weights, opportunity cost, and reallocation.
PS owns price/trading-unit/minimum-notional feasibility and final quantity.
```

This must not mean "target_weight > 0 always buys one lot." One lot is allowed only if PC explicitly authorizes it within value, cash, exposure, concentration, broker eligibility, passive convergence, and opportunity-cost constraints.

## Reallocation Semantics

Unused budget from broker-unsupported, ADD-ineligible, or lot-infeasible items may flow to:

```text
next eligible BUY_NEW
eligible ADD
stronger existing target
cash
```

Cash remains a valid endpoint. No fixed purchase count and no forced cash utilization may be introduced.

## Compatibility

```text
Passive convergence compatibility = PASS
Broker eligibility compatibility = PASS
SELL independence compatibility = PASS
Historical/Production common path = YES
Training leakage risk = NONE
```

Passive convergence remains authoritative: if existing baseline is over target, positive increments stay disabled.

## D55 Boundary

Recommended implementation split:

```text
D55-A: BUY_ADD evidence availability repair
D55-B: Lot-aware capital conversion repair
```

Recommended first implementation:

```text
D55-A
```

Reason: BUY_ADD is entirely blocked before Position Sizing across 191/191 ADD rows. Lot-aware conversion is a distinct PC/PS feedback contract and should not be bundled into the ADD evidence repair.

Fresh 100BD after implementation:

```text
YES
```

## Deliverables

```text
docs/phase_reports/phase28_d54_buy_add_evidence_and_lot_aware_capital_conversion_design.md
reports/phase_reports/phase28_d54_buy_add_evidence_and_lot_aware_capital_conversion_design.json
reports/phase28_d54_buy_add_evidence_and_lot_aware_capital_conversion_design/
```
