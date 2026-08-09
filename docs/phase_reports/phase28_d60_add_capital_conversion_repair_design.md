# Phase28-D60 Production-Common ADD Capital Conversion Repair Design

## Primary Judgment

```text
PHASE28_D60_ADD_CAPITAL_CONVERSION_REPAIR_DESIGN_COMPLETE_D61_READY
```

D60 is design-only. No implementation, config, schema, threshold, runtime artifact, fresh run, resume, or long historical execution was performed.

Target run:

```text
runtime-test-historical-smoke-20260809T010010445473Z
```

## D59 Evidence Basis

| Funnel Stage | Count |
| --- | ---: |
| PM ADD rows in active PC | 142 |
| D55-A final PASS | 69 |
| requested_incremental_weight > 0 | 23 |
| budget accepted > 0 | 23 |
| lot-aware accepted > 0 | 11 |
| PC positive existing-position ADD | 11 |
| PS positive BUY_ADD delta | 4 |
| Runtime BUY_ADD | 4 |
| Runtime BUY_ADD Fill | 3 |

D55-A PASS classification:

| Class | Count |
| --- | ---: |
| A target/current collision request 0 | 46 |
| B lot-aware zero | 12 |
| C PC positive -> PS zero | 7 |
| D PS positive -> Runtime missing | 0 |
| E Runtime BUY_ADD -> no fill | 1 |
| F Runtime BUY_ADD -> fill | 3 |

## Current Contract Findings

Portfolio Construction currently computes an ordinary base target before ADD bridge:

```text
base_weight = target_gross_exposure / effective_count, capped by single-name cap
```

Code evidence:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1032-1043`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1192-1200`

The ADD bridge then receives that ordinary base target as `candidate_target_weight` and computes:

```text
desired_increment = max(candidate_target_weight - current_weight, 0)
eligible requires desired_increment > 0
```

Code evidence:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1817`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1893-1914`

Therefore, `PM ADD + D55-A PASS` is zeroed whenever the current position already meets or exceeds the ordinary base target. That is an architecture gap, not the intended ADD contract, because D55-A PASS means incremental investment value was approved for the existing campaign, not merely that the position should be restored to the ordinary base target.

Position Sizing also has a post-PC mismatch:

```text
ADD transaction_delta_weight uses accepted_incremental_weight first.
It does not first consume lot_aware_accepted_incremental_weight or
target_weight_resolution.lot_aware_final_reallocation.accepted_lot_increment_weight.
```

Code evidence:

- `src/ai_fund_lab_v2/strategy/position_sizing.py:730-848`

This explains the 21340-style case where PC final target is lot-aware positive, but PS reuses the pre-lot accepted increment and rounds to zero.

## D60-A Target / Current Collision Design

### Options Compared

Option A:

```text
target = current_weight + approved_incremental_weight
```

This is semantically close, but unsafe if the approved increment is not allocated through existing PC opportunity competition and budget reconciliation.

Option B:

```text
target = max(current_weight, base_target) + approved_incremental_weight
```

This avoids some current/base collisions, but still mixes ordinary base target authority with ADD incremental authority.

Option C:

```text
existing-position baseline
+
independent ADD incremental allocation authority
```

Selected.

Option C best fits the architecture because it separates two meanings:

- ordinary base target: portfolio membership / base allocation authority
- ADD increment: D55-A-approved incremental investment authority competing for remaining capital

The ADD increment must still pass through:

- portfolio opportunity competition
- target gross exposure
- deployable capital
- single-name concentration
- broker eligibility
- lot/minimum executable feasibility
- no-loss and campaign continuation controls

## D60-B Incremental Allocation Amount Semantics

The approved incremental amount must not be fixed, such as "ADD means add 5%".

D61 should compute the ADD incremental request inside Portfolio Construction using existing allocator inputs:

- D55-A PASS evidence
- expected-edge improvement and current opportunity score as ranking / competition evidence
- construction priority and BUY_NEW competition
- available incremental budget
- target gross exposure
- single-name remaining capacity
- current position weight
- campaign continuation and no-loss evidence
- Buy Quality allocation evidence as attribution, not as an unconditional zeroing gate for D55-A-approved ADD

The request must be an allocation candidate, not an order instruction. It becomes executable only after incremental budget reconciliation, lot-aware final reallocation, PS final sizing, Runtime Planning, Pending, Approval, Submit, and Fill.

## D60-C Adaptive Buy Quality Interaction

D59 did not confirm Adaptive Buy Quality as the primary root cause.

Selected quality ordering:

```text
Quality adjustment applies to ordinary base allocation.
D55-A-approved ADD increment is evaluated as its own PC incremental allocation.
```

This avoids the current failure mode where `post_quality_target_weight < current_weight` indirectly suppresses an independently approved ADD increment. D61 must not change quality thresholds or model behavior.

Separate ADD-specific quality authority is not D61 scope.

## D60-D Lot-Aware Increment Conversion Design

D59 confirmed 12 rows with:

```text
requested_incremental_weight > 0
accepted_incremental_weight > 0
lot_aware_accepted_incremental_weight = 0
```

Required cases include:

- `30410 / 2023-05-24`
- `30410 / 2023-05-25`
- `30410 / 2023-05-29`
- `30410 / 2023-05-30`
- `76470 / 2023-05-08`
- `76470 / 2023-07-12`

Current D55-B primitive already implements the right production-common shape:

```text
PC draft
-> PS lot feasibility preflight
-> PC final lot-aware reallocation
-> PS final sizing
```

Code evidence:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1494-1665`
- `src/ai_fund_lab_v2/strategy/position_sizing.py:197-207`
- `src/ai_fund_lab_v2/strategy/position_sizing.py:970-1045`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1246-1277`

Selected repair:

```text
Reuse the D55-B primitive.
Repair ADD increment basis and final lineage consumption.
Do not create a parallel ADD-only lot allocator.
```

Production semantics:

```text
approved ADD incremental notional
-> executable round-lot quantity evidence from PS preflight
-> PC accepts the maximum safe positive lot only inside budget/cap/exposure rules
-> PS final consumes the same accepted lot increment lineage
```

If minimum 1 lot cannot be bought within budget, cap, cash, broker eligibility, and exposure limits, zero is correct.

## D60-E PC Positive -> PS Zero Design

D59 representative:

```text
21340 / 2023-06-08
PC current_weight = 0.065571
PC target_weight = 0.112141
PC lot_aware_accepted_incremental_weight = 0.046570
PS accepted_incremental_weight = 0.028179
PS transaction_quantity_candidate = 0
PS quantity_delta_candidate = 0
```

The conflict is that PC final lot-aware authority accepted a larger executable ADD increment, but PS final sizing recalculated from `accepted_incremental_weight` instead of the final lot-aware accepted increment.

Options:

Option A, PC weight only and PS sole lot authority:

Rejected for D61. It would undo D55-B's two-pass final reallocation.

Option B, PC lot-aware maintained and PS respects resolved quantity/notional lineage:

Selected as the minimal implementation contract.

Option C, shared lot-resolution primitive:

Selected as direction. If it can be extracted without schema/config change, D61 should use shared code for the ADD transaction basis to prevent double rounding. If extraction is too broad, D61 should still consume existing PC lot-aware lineage in PS.

## Authority Ownership

| Authority | Owner |
| --- | --- |
| PM ADD intent | Position Management; intent only |
| D55-A ADD eligibility | ADD Investment Evidence Resolver |
| Incremental investment value | D55-A resolver |
| Portfolio opportunity competition | Portfolio Construction |
| Incremental capital budget | Portfolio Construction |
| Target weight | Portfolio Construction |
| Concentration / gross exposure | Portfolio Construction, with PS hard revalidation only |
| Lot-aware execution feasibility | Position Sizing preflight |
| Quantity sizing | Position Sizing final |
| Runtime BUY_ADD mapping | Runtime Planning mapper |

Runtime Planning remains innocent: D59 showed `D = 0`, so a positive PS ADD delta is already mapped to Runtime BUY_ADD.

## BUY_NEW Compatibility

BUY_NEW must not change in D61.

D59 BUY_NEW evidence:

```text
BUY_NEW requested > 0 = 115
lot-aware accepted > 0 = 28
Runtime BUY_NEW = 23
fill = 19
```

D61 should preserve existing BUY_NEW semantics and share only common capital-conversion primitives. The difference between BUY_NEW and BUY_ADD should remain:

- BUY_NEW baseline is zero / new slot target
- BUY_ADD baseline is current existing position
- both compete through PC budget and lot-aware feasibility

## Safety Analysis

D61 must preserve these guards:

- no fixed ADD percentage
- no forced BUY_ADD
- no forced use of leftover cash
- no cash or gross exposure overshoot
- no single-name cap violation
- no symbol-only fallback
- no future evidence
- no missing evidence fail-open
- no Submit Guard or SELL behavior change

Repeated daily ADD is controlled by daily D55-A re-evaluation:

- campaign continuation
- expected-edge improvement
- opportunity cost
- no-loss averaging
- incremental value
- PC budget and cap competition

D61 must not implement unconditional `current_weight + fixed_increment`.

## Required Final Design

### 1. Target / Current Collision Repair

Selected:

```text
OPTION_C_ADD_INCREMENT_AUTHORITY_ON_TOP_OF_CURRENT_BASELINE_WITH_PORTFOLIO_COMPETITION
```

Current defect:

```text
ADD increment is derived from ordinary base target minus current weight.
```

Owning authority:

```text
Portfolio Construction
```

Exact behavior change:

```text
PM ADD + D55-A PASS creates an ADD incremental request even when current_weight >= ordinary base target,
but only if PC budget/cap/competition can accept it.
```

Production-common implementation point:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
```

### 2. Lot-Aware Increment Conversion Repair

Selected:

```text
REUSE_D55B_TWO_PASS_LOT_AWARE_PRIMITIVE_WITH_ADD_INCREMENT_BASIS_AND_SAFE_MINIMUM_LOT_PROMOTION
```

Current defect:

```text
ADD request can be positive but final lot-aware accepted increment becomes zero,
partly because the ADD basis remains tied to draft target-current rather than a durable ADD increment request.
```

Owning authorities:

```text
PS preflight owns lot feasibility.
PC final owns reallocation and target weight.
```

Exact behavior change:

```text
Use ADD incremental request as the lot-aware transaction basis.
Authorize minimum safe positive lot only inside cap/budget/exposure/broker constraints.
```

Production-common implementation point:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
```

### 3. PC Positive -> PS Zero Repair

Selected:

```text
SHARED_LOT_RESOLUTION_LINEAGE_CONSUMPTION_BY_PS_FOR_ADD_TRANSACTION_DELTA
```

Current defect:

```text
PS final uses accepted_incremental_weight before lot_aware_accepted_incremental_weight,
so PC's final lot-aware accepted ADD increment can be ignored.
```

Owning authority:

```text
Position Sizing final quantity authority, consuming PC final lot-aware target lineage.
```

Exact behavior change:

```text
For ADD, PS final transaction_delta_weight should prefer
lot_aware_accepted_incremental_weight or
target_weight_resolution.lot_aware_final_reallocation.accepted_lot_increment_weight
when present and positive.
```

Production-common implementation point:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
```

## D61 Minimal Scope

Affected files:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`

Do not touch:

- D55-A resolver semantics
- `shadow_runtime.py` orchestration
- Runtime Planning mapping
- Submit Guard
- SELL path
- Broker eligibility semantics
- config
- schemas
- thresholds

## Regression Plan

Required focused tests:

- 94320-like target/current collision creates positive ADD request when D55-A PASS and capacity exists
- same case remains zero when no available budget/cap/cash exists
- 30410-like minimum lot too expensive remains zero with explicit reason
- 76470-like minimum safe ADD lot can be accepted
- 21340-like PC positive lot-aware ADD produces positive PS quantity
- BUY_NEW D55-B behavior unchanged
- Runtime Planning maps only positive PS delta to BUY_ADD
- SELL / REDUCE / EXIT unchanged

Fresh 100BD is required after D61 implementation and short validation pass.

## Secondary Judgments

```text
target/current collision repair design = OPTION_C_ADD_INCREMENT_AUTHORITY_ON_TOP_OF_CURRENT_BASELINE_WITH_PORTFOLIO_COMPETITION
lot-aware repair design = REUSE_D55B_TWO_PASS_LOT_AWARE_PRIMITIVE_WITH_ADD_INCREMENT_BASIS_AND_SAFE_MINIMUM_LOT_PROMOTION
PC->PS repair design = SHARED_LOT_RESOLUTION_LINEAGE_CONSUMPTION_BY_PS_FOR_ADD_TRANSACTION_DELTA
D55-A change required = NO
Runtime Planning change required = NO
Submit change required = NO
BUY_NEW behavior change required = NO
schema change required = NO
threshold change required = NO
fresh 100BD required after implementation = YES
```

## Deliverables

- `reports/phase28_d60_add_capital_conversion_repair_design/code_contract_audit.json`
- `reports/phase28_d60_add_capital_conversion_repair_design/option_comparison.json`
- `reports/phase28_d60_add_capital_conversion_repair_design/authority_ownership.json`
- `reports/phase28_d60_add_capital_conversion_repair_design/d61_minimal_scope.json`
- `reports/phase28_d60_add_capital_conversion_repair_design/regression_plan.json`
- `reports/phase28_d60_add_capital_conversion_repair_design/safety_regression_analysis.json`
- `reports/phase28_d60_add_capital_conversion_repair_design/next_phase_contract.json`
- `reports/phase_reports/phase28_d60_add_capital_conversion_repair_design.json`

## Execution Flags

```text
Implementation changed = NO
Config changed = NO
Schema changed = NO
Threshold changed = NO
Runtime mutated = NO
Resume executed = NO
Fresh run executed = NO
Long Historical executed = NO
```
