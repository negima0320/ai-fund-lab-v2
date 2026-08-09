# Phase28-D32: Portfolio Construction REDUCE Partial-Target Semantics Root Cause

## Primary Judgment

```text
PHASE28_D32_PC_REDUCE_PARTIAL_TARGET_AUTHORITY_GAP_CONFIRMED
```

Supporting Judgments:

```text
PHASE28_D32_REDUCE_DESIGN_GAP_REQUIRES_D33_DESIGN
PHASE28_D32_EXISTING_REDUCE_SCALE_AUTHORITY_FOUND
PHASE28_D32_D28_REDUCE_BASELINE_ZERO_PROPAGATION_CONFIRMED
```

No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

## 77760 End-to-End Trace

| Stage | Evidence |
| --- | --- |
| PM action | `REDUCE` |
| PM decision id | `pm-2023-04-11-77760-reduce` |
| PM reason | `risk_increased_but_trend_not_broken` |
| PM canonical reason | `expected_edge_weakening_risk_increased` |
| PM dominant cause | `REDUCE_BY_WEAK_HOLD_SCORE` |
| PM intensity | `LIGHT` |
| current_weight | `0.053147` |
| current_quantity | `100` |
| PC membership_intent | `REDUCE_CANDIDATE` |
| PC weight_intent | `DECREASE` |
| PC target_weight | `0.0` |
| PC baseline_existing_weight | `0.0` |
| PS target_quantity_candidate | `0` |
| PS quantity_delta_candidate | `-100` |
| Runtime Planning intent | `UNRESOLVED` |
| Runtime reason | `planning_conflict_review:full_liquidation_authority_missing:77760` |

PM remains source-grounded as `REDUCE`, not `EXIT`. Runtime Planning correctly refuses to turn the full negative quantity into `SELL_EXIT` because `full_liquidation_authority_present=false`.

## First Divergence

Last semantically correct stage:

```text
Strategy Position Management
symbol=77760
action=REDUCE
intensity=LIGHT
reason=risk_increased_but_trend_not_broken
```

First zero producer:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py:925-927
```

The branch:

```text
membership_intent in {"REDUCE_CANDIDATE", "REMOVE_CANDIDATE"}
```

sets:

```text
zero_weight_reason = existing_position_reduce_or_exit
reason = existing_position_reduce_or_exit
```

Because the initial row was not a selected target member, `weight` remains `0.0`. This branch collapses `REDUCE_CANDIDATE` and `REMOVE_CANDIDATE` into the same zero-target semantics.

D28 then propagates the already-zero target:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py:1093-1096
baseline = original_target
released_reduce += current_weight - baseline
```

For 77760:

```text
original_target = 0.0
baseline_existing_weight = 0.0
released_reduce_capacity = 0.053147
```

D28 is not the first zero producer, but it records the zero as the REDUCE baseline.

## REDUCE Semantics

Architecture confirms:

```text
REDUCE = reduce exposure while preserving optionality
EXIT = full close intent
```

Evidence:

- `docs/02_architecture/strategy_architecture_v1.md`: REDUCE is independent and exists before full EXIT is justified.
- `docs/phase_reports/phase28_d24_pm_intent_preserving_sell_authority_repair_design.md`: PM REDUCE should map to partial remaining quantity or review/no-order, not silent EXIT.
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`: Portfolio Construction owns target membership and target_weight; Position Sizing owns notional/quantity conversion.

Therefore, for executable REDUCE:

```text
0 < target_quantity_candidate < current_quantity
```

or if constraints prevent execution:

```text
NO_ORDER / REVIEW_REQUIRED
```

not a silent full liquidation.

## Existing REDUCE Scale Authority

Existing REDUCE scale/fraction authority exists, but not in the active Strategy PC target-weight path.

PM source evidence for 77760 contains:

```text
reduce_intensity = LIGHT
runtime_quantity_authority = SELL_PLANNING_REDUCE_QUANTITY_CONTRACT
```

Legacy/runtime Sell Planning contains:

```text
REDUCE_INTENSITY_RATIOS:
LIGHT = 0.25
MEDIUM = 0.33
STRONG = 0.50
```

Code:

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:66-70
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1309-1391
```

However, `src/ai_fund_lab_v2/strategy/portfolio_construction.py` does not consume `reduce_intensity`, `target_reduce_ratio`, or Sell Planning's quantity contract. D32 therefore must not declare a new PC rule such as `REDUCE = 25%` without D33 design.

## Other REDUCE Cases

Target run inventory:

| Date | Symbol | PM intensity | current_weight | PC target_weight | PS delta | Runtime intent |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 2023-04-07 | 43880 | LIGHT | 0.127745 | 0.0 | -100 | UNRESOLVED |
| 2023-04-11 | 77760 | LIGHT | 0.053147 | 0.0 | -100 | UNRESOLVED |

Distribution:

```text
REDUCE -> zero PC target -> full negative PS delta -> Runtime UNRESOLVED: 2
REDUCE -> partial sell: 0
```

This is systematic for observed REDUCE rows in the target run.

## D23 Relation

D23 found three old `PM REDUCE -> SELL_EXIT` cases. D24 records that they passed through Strategy PM `UNRESOLVED -> target zero -> SELL_EXIT`. D32 differs:

```text
77760 PM REDUCE is preserved into Strategy PM and PC.
The new first divergence is Portfolio Construction zero-target semantics.
```

Same high-level family:

```text
REDUCE partial intent became target zero downstream.
```

Different direct root:

```text
D23: PM action loss / Runtime target-zero mapping.
D32: PC REDUCE target generation defaults to zero.
```

## Causality

D28 direct causality:

```text
PARTIAL
```

D28 does not first set 77760 target to zero. It consumes `original_target=0.0` and materializes `baseline_existing_weight=0.0`, contrary to the D27/D28 design phrase `REDUCE remaining target participates as baseline`.

D31 direct causality:

```text
NO
```

D31 only consumes PC target_weight. With PC target zero, PS produces target quantity zero and delta `-100`. That is defensive downstream consumption of an invalid/ambiguous PC target.

D25 direct causality:

```text
NO
```

D25 correctly blocks silent full liquidation:

```text
PM REDUCE + target zero + no PM EXIT authority -> UNRESOLVED / REVIEW_REQUIRED
```

## Root Cause Classification

Primary:

```text
PC_REDUCE_PARTIAL_TARGET_AUTHORITY_MISSING
```

Supporting:

```text
PC_REDUCE_TARGET_DEFAULTS_TO_ZERO
D28_REDUCE_BASELINE_ZERO_PROPAGATION
REDUCE_MEMBERSHIP_TARGET_SEMANTIC_GAP
PM_REDUCE_SCALE_NOT_PROPAGATED_TO_PC
```

Design vs runtime classification:

```text
Implementation defect: yes, REDUCE_CANDIDATE and REMOVE_CANDIDATE share a zero-target branch.
Design gap: yes, PC has no approved partial remaining target algorithm.
Authority propagation gap: yes, PM reduce_intensity / Sell Planning reduce contract is not propagated into PC target_weight.
Legacy behavior: yes, Sell Planning has REDUCE ratios but Strategy PC does not consume them.
```

## Minimal Next Scope

D33 should be design-first:

```text
Phase28-D33: Portfolio Construction REDUCE Partial-Target Repair Design
```

D33 should decide one canonical repair path, likely among:

```text
1. PC consumes PM reduce_intensity and converts it to remaining target_weight.
2. PC preserves REDUCE as REVIEW_REQUIRED until a canonical partial target authority is connected.
3. PC delegates REDUCE quantity to an existing approved Sell Planning contract while preserving Strategy PC lineage.
```

D32 does not choose an arbitrary fraction.

## Final Judgment

```text
Primary Judgment: PHASE28_D32_PC_REDUCE_PARTIAL_TARGET_AUTHORITY_GAP_CONFIRMED
First divergence point: Portfolio Construction target-weight resolution
Existing REDUCE scale/fraction authority: YES, but legacy Sell Planning / PM intensity, not active PC target-weight path
Who owns partial target: Portfolio Construction owns target_weight; PM owns REDUCE intent and intensity evidence; Position Sizing converts target to quantity
Why target_weight became zero: REDUCE_CANDIDATE was grouped with REMOVE_CANDIDATE and left at zero target
D28 direct causality: PARTIAL propagation
D31 direct causality: false
D25 direct causality: false
Other REDUCE cases: 2 observed, both same zero-target pattern
D23 relation: same family, different direct root
Existing evidence sufficient for repair: PARTIAL
Minimal Next Scope: D33 design
Implementation changed: false
Config changed: false
Schema changed: false
Threshold changed: false
Resume executed: false
Fresh run executed: false
Long Historical executed: false
Runtime mutated: false
Next Phase: Phase28-D33 Portfolio Construction REDUCE Partial-Target Repair Design
```
