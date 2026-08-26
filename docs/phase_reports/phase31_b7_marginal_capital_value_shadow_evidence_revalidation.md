# Phase31-B7 — Marginal Capital Value Shadow Evidence Revalidation

## PRIMARY_JUDGMENT

PHASE31_B7_MARGINAL_CAPITAL_SHADOW_GAPS_REMAIN

B6 repaired the key comparison-evidence gap: BUY_NEW and BUY_ADD are now comparable from PIT Strategy evidence, and B0's 94320 ADD cases are no longer `COMPARISON_INSUFFICIENT`.

However, B7 does not pass the full structural gate because the repaired diagnostic shadow still bridges only `runtime_planning.json#plans` for actual Runtime order. It does not carry the downstream reserved-cash / Pending cash-feasibility decision state needed to reconstruct every B3/B7 starvation case as:

```text
pre-batch cash -> prior included reserved notional -> remaining cash -> candidate required notional -> INCLUDE / PRUNE / REVIEW
```

The shadow is ready for a narrower runtime/pending cash bridge refinement, not yet for mutating Alternative C authorization review.

## TARGET_RUN

runtime-test-historical-extended-smoke-20260818T015851711672Z

## Evidence Scope

B7 read the B6 diagnostic artifacts:

```text
daily/<DATE>/diagnostic_shadow/marginal_capital_value_shadow.json
```

Evaluated mixed NEW/ADD days:

- `2022-08-19`
- `2022-08-22`
- `2022-08-23`
- `2022-08-24`
- `2022-08-30`
- `2022-09-01`
- `2022-09-15`
- `2022-09-16`
- `2022-09-20`

No Strategy decisions were regenerated. No fresh-run, resume, replay, or long Historical was executed.

## Q1 — Candidate Comparability

SHADOW_EVALUATED_DAY_COUNT = 9

SHADOW_EVALUATED_ITEM_COUNT = 84

COMPARISON_INSUFFICIENT_COUNT = 0

COMPARISON_INSUFFICIENT_RATE = 0.0%

Class distribution:

| Class | Count |
| --- | ---: |
| `ELIGIBLE_STRONG` | 18 |
| `ELIGIBLE_COMPARABLE` | 66 |

Intent/class distribution:

| Intent | Class | Count |
| --- | --- | ---: |
| `BUY_ADD` | `ELIGIBLE_STRONG` | 9 |
| `BUY_NEW` | `ELIGIBLE_STRONG` | 9 |
| `BUY_NEW` | `ELIGIBLE_COMPARABLE` | 66 |

## Q2 — B0 94320 Development Cases

B0_94320_MECHANISM_REPRODUCED = YES for PIT marginal-value mismatch; PARTIAL for reserved-cash causality reconstruction.

The repaired shadow identifies 94320 as strong ADD and first in canonical shadow order on both B0 dates. This reproduces the B0 strong-ADD / later Runtime-order mismatch using PIT Strategy evidence.

### 2022-08-19 / 94320

| Field | Value |
| --- | --- |
| lifecycle intent | `BUY_ADD` |
| marginal value class | `ELIGIBLE_STRONG` |
| Expected Edge state | `IMPROVING` |
| Incremental Investment Value | `POSITIVE` |
| Opportunity Cost | `PASS` |
| ADD-worthiness | `ADD_REDUCED_ONLY` |
| opportunity rank | `1` |
| campaign provenance | `same_campaign_identity_match`; campaign `pc-e3de6a6771d56574-94320-0001`; evidence date `2022-08-19`; baseline date `2022-08-18`; PIT `PASS` |
| source paths | `.runtime/runtime_state/buy_ai/2022-08-19/opportunity_rankings.json`; `daily/2022-08-19/strategy/buy_quality_decisions.json` |
| current weight | `0.043469` |
| target weight | `0.087200` |
| accepted incremental weight | `0.043731` |
| lot quantity | PS transaction/delta `300` |
| lot/materialization reason | `EXECUTABLE_LOT` |
| shadow priority | `1` |
| actual PC order | `15` |
| actual Runtime order | `30` |
| Runtime inclusion/prune result in B6 bridge | `INCLUDED` from `runtime_planning.plans` |
| prior BUY_NEW reserved notional | `163,000` from B0 pending cash audit |
| ADD reserved notional | `59,850` from B0 pending cash audit |

### 2022-08-24 / 94320

| Field | Value |
| --- | --- |
| lifecycle intent | `BUY_ADD` |
| marginal value class | `ELIGIBLE_STRONG` |
| Expected Edge state | `IMPROVING` |
| Incremental Investment Value | `POSITIVE` |
| Opportunity Cost | `PASS` |
| ADD-worthiness | `ADD_REDUCED_ONLY` |
| opportunity rank | `1` |
| campaign provenance | `same_campaign_identity_match`; campaign `pc-e3de6a6771d56574-94320-0001`; evidence date `2022-08-24`; baseline date `2022-08-23`; PIT `PASS` |
| source paths | `.runtime/runtime_state/buy_ai/2022-08-24/opportunity_rankings.json`; `daily/2022-08-24/strategy/buy_quality_decisions.json` |
| current weight | `0.114841` |
| target weight | `0.157792` |
| accepted incremental weight | `0.042951` |
| lot quantity | PS transaction/delta `300` |
| lot/materialization reason | `EXECUTABLE_LOT` |
| shadow priority | `1` |
| actual PC order | `14` |
| actual Runtime order | `29` |
| Runtime inclusion/prune result in B6 bridge | `REVIEW_REQUIRED` from `runtime_planning.plans` reason `existing_pending_conflict` |
| prior BUY_NEW reserved notional | `55,700` from B0 pending cash audit |
| ADD reserved notional | `60,510` from B0 pending cash audit |

Important discrepancy: B0's reserved-cash audit found 94320 pending cash-pruned on these dates; B6/B7 shadow artifacts only bridge `runtime_planning.plans`, which is not sufficient to expose the final pending reserved-cash prune decision. This is the remaining bridge gap.

## Q3 — Strong ADD vs Weaker/Comparable NEW

STRONG_ADD_CANDIDATE_COUNT = 9

STRONG_ADD_AHEAD_OF_NEW_PAIR_COUNT = 75

STRONG_ADD_BEHIND_WEAKER_NEW_ACTUAL_RUNTIME_COUNT = 29 pairwise Runtime-order inversions

STRONG_ADD_RUNTIME_CASH_PRUNED_COUNT = 2 confirmed B0 pending-cash audit cases (`2022-08-19`, `2022-08-24`); not fully materialized in B6 diagnostic shadow artifacts

STRONG_ADD_RUNTIME_CASH_PRUNED_NOTIONAL = `120,360` from B0 pending-cash audit (`59,850 + 60,510`)

STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT = 29 pairwise Runtime-order inversions

STRONG_ADD_STARVED_BY_WEAKER_NEW_NOTIONAL = `2,034,560` on prior lower-canonical NEW planned-notional basis from B6 runtime plans

These are structural order inversions, not profitability claims.

## Q4 — Strong NEW Protection

STRONG_NEW_PROTECTION = PASS

STRONG_NEW_CANDIDATE_COUNT = 9

STRONG_NEW_AHEAD_OF_ADD_PAIR_COUNT = 0 in the repaired real mixed-day shadow, because each mixed day includes a PIT-strong 94320 ADD ranked first.

STRONG_NEW_BEHIND_WEAKER_ADD_SHADOW_COUNT = 0

No hidden ADD_FIRST is inferred from this: focused B4/B6 tests still prove strong NEW can outrank weak ADD, and real evidence contains no weak ADD candidates in the materialized mixed-day set after B6.

## Q5 — Label Priority Violations

BUY_ADD_LABEL_PRIORITY_VIOLATION_COUNT = 0

BUY_NEW_LABEL_PRIORITY_VIOLATION_COUNT = 0

No candidate received priority solely from `BUY_ADD` or `BUY_NEW`.

## Q6 — Weak ADD Protection

WEAK_ADD_CANDIDATE_COUNT = 0 in B6 materialized mixed-day shadow artifacts.

WEAK_ADD_PROMOTED_COUNT = 0

Expected Edge `WEAKENING`, non-positive Incremental Investment Value, Opportunity Cost failure, ADD-worthiness failure, and insufficient campaign evidence remain covered by focused tests. B7 does not credit Alternative C with fixing B1 upstream PM ADD -> positive increment narrowing.

## Q7 — Shadow vs Actual PC Order

SHADOW_VS_PC_ORDER_DELTA_DAY_COUNT = 6

SHADOW_VS_PC_ORDER_DELTA_ITEM_COUNT = 36 / 84

PC_ORDER_MATCH_RATE = 57.1%

Difference classification:

| Class | Count |
| --- | ---: |
| `MARGINAL_VALUE_REORDER` | 18 |
| `LOT_MATERIALIZATION_DIFFERENCE` | 18 |
| `COMPARISON_INSUFFICIENT` | 0 |

## Q8 — Shadow vs Actual Runtime Order

SHADOW_VS_RUNTIME_ORDER_DELTA_DAY_COUNT = 9

SHADOW_VS_RUNTIME_ORDER_DELTA_ITEM_COUNT = 36 / 42 runtime-present candidates

RUNTIME_ORDER_MATCH_RATE = 14.3%

CANONICAL_ORDER_PRESERVATION_RATE_IF_MUTATED_CONCEPTUALLY = PARTIAL

The diagnostic shadow can identify order differences, but B7 cannot prove full conceptual preservation through reserved cash because Pending cash-feasibility state is not bridged into the diagnostic artifact.

## Q9 — Processing-Order Starvation

PROCESSING_ORDER_STARVATION_COUNT = 62 pairwise canonical-vs-runtime inversions

PROCESSING_ORDER_STARVATION_NOTIONAL = `4,112,850` prior lower-canonical planned-notional basis from `runtime_planning.plans`

STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT = 29 pairwise inversions

STRONG_ADD_STARVED_BY_WEAKER_NEW_NOTIONAL = `2,034,560`

STRONG_NEW_STARVED_BY_WEAKER_ADD_COUNT = 0

STRONG_NEW_STARVED_BY_WEAKER_ADD_NOTIONAL = `0`

CASH_PRUNE_WITH_LOWER_CANONICAL_RANK_INCLUDED_COUNT = 2 confirmed B0 pending-cash cases; 29 order inversions are observable but not all cash-prune confirmed in B6 artifacts

UNEXPLAINED_CASH_PRUNE_COUNT = 0 explicit unexplained prunes in B6 artifacts, because cash-prune decisions are not present there. This is a coverage gap, not a clean zero.

## Q10 — Runtime Reserved-Cash Causality

Core causal validation status = PARTIAL

Confirmed B0 causal cases from prior pending-cash audit:

| Date | Classification | Prior lower-canonical BUY_NEW notional | Higher-canonical ADD notional | Result |
| --- | --- | ---: | ---: | --- |
| `2022-08-19` | `CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM` | `163,000` | `59,850` | B0 pending cash prune |
| `2022-08-24` | `CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM` | `55,700` | `60,510` | B0 pending cash prune |

For the remaining pairwise inversions, B7 can reconstruct:

```text
canonical shadow order -> actual Runtime plans order -> prior planned notional -> Runtime plan inclusion/review state
```

But B7 cannot reconstruct:

```text
pre-batch cash -> remaining cash before candidate -> final pending reserved-cash prune
```

from B6 diagnostic artifacts alone.

## Q11 — Lot / Materialization Validation

EXECUTABLE_LOT_COUNT = 41

ZERO_QUANTITY_DELTA_COUNT = 0

LOT_NOT_FEASIBLE_COUNT = 0

CONCENTRATION_BOUND_COUNT = 1

BUDGET_BOUND_COUNT = 0

NOT_IN_RUNTIME_PLAN_COUNT = 42

RESERVED_CASH_PRUNE_COUNT = 0 in B6 diagnostic artifact state; 2 known from B0 pending-cash audit

REVIEW_REQUIRED_COUNT = 2 in actual Runtime plans order

UNRESOLVED_MATERIALIZATION_COUNT = 0

MARGINAL_ORDER_SURVIVES_LOT_MATERIALIZATION_OR_TYPED_SKIP = PARTIAL

Every candidate has a typed materialization reason, but candidates missing from Runtime order are often typed only as `NOT_IN_RUNTIME_PLAN`, not as a final cash/lot/safety causality.

## Q12 — Explainability

SHADOW_ORDER_EXPLAINED_COUNT = 84

SHADOW_ORDER_UNEXPLAINED_COUNT = 0

CANONICAL_ORDER_EXPLAINABILITY_RATE = 100%

MATERIALIZATION_EXPLAINED_COUNT = 84

MATERIALIZATION_UNEXPLAINED_COUNT = 0

MATERIALIZATION_EXPLAINABILITY_RATE = 100%

No silent fallback superiority was used.

## Q13 — PIT / Leakage Revalidation

FUTURE_INFORMATION_USED = NO

FUTURE_OUTCOME_FIELD_COUNT = 0

POST_DECISION_FIELD_COUNT = 0

UNKNOWN_TEMPORAL_BINDING_FIELD_COUNT = 0

ADD campaign provenance was present for all 9 BUY_ADD candidates:

- evidence business date present
- Expected Edge baseline date present and not after business date
- source artifact path present
- source hash present
- PIT validation status `PASS`
- `future_information_used = false`

B7 did not use final return, hypothetical return, later 94320 profit, future campaign outcome, later MFE/MAE, or valuation/PnL outcomes.

If Phase31-A6 later finds retroactive contamination affecting these Strategy PIT artifacts, affected B7 evidence must be revalidated.

## Q14 — Non-Mutation Proof

ACTUAL_PC_DECISION_MUTATED = NO

ACTUAL_PS_QUANTITY_MUTATED = NO

ACTUAL_RUNTIME_ORDER_MUTATED = NO

ACTUAL_PENDING_MUTATED = NO

ACTUAL_SUBMIT_MUTATED = NO

ACTUAL_EXECUTION_MUTATED = NO

ACTUAL_FILL_MUTATED = NO

ACTUAL_RUN_STATE_MUTATED = NO

ACTUAL_TRADING_PATH_MUTATED = NO

Diagnostic shadow files are the only materialized outputs used.

## Q15 — Alternative C Structural Gate

STRUCTURAL_GATE_PASS = NO

| Gate | Result |
| --- | --- |
| PIT-only evidence | PASS |
| BUY_ADD label no priority | PASS |
| BUY_NEW label no priority | PASS |
| Weak ADD protection | PASS |
| Strong NEW protection | PASS with focused-test support |
| Strong ADD comparable | PASS |
| B0 development mechanism reproducible | PASS for marginal-order mismatch; PARTIAL for cash causality |
| Runtime actual order bridged | PASS for `runtime_planning.plans` |
| Canonical order explainable | PASS |
| Lot/materialization typed | PASS |
| Processing-order starvation measurable | PASS as order inversion; PARTIAL as cash-prune causality |
| No hidden ADD_FIRST | PASS |
| No hidden NEW_FIRST | PASS for shadow; current Runtime still shows NEW-before-ADD processing |
| Actual trading path unchanged | PASS |
| Strategy cap unchanged | PASS |
| Safety hard cap unchanged | PASS |
| BUY/SELL independence preserved | PASS |
| Reserved-cash causality fully reconstructed | FAIL |

## Q16 — Mutation Readiness

MUTATING_ALTERNATIVE_C_READINESS = NOT_READY_LOT_OR_RUNTIME_BRIDGE

The comparison semantics and PIT provenance are now strong enough for the development evidence. The remaining blocker is the bridge from shadow/Runtime plans order into final Pending reserved-cash feasibility decisions.

## Q17 — Mutation Surface Preview

Not authorized in B7. If the remaining bridge passes later, the narrow conceptual mutation surface would be:

PC:

```text
produce canonical marginal-capital priority
```

PS:

```text
consume PC target/discrete quantity unchanged
```

Runtime Planning:

```text
preserve canonical priority when reserving cash
```

Do not redesign PM ADD semantics, Expected Edge, Incremental Investment Value, Opportunity Cost, Strategy cap, Safety hard cap, winner headroom, Submit, or Execution. Alternative E remains out of scope.

## Q18 — A6 Valuation HALT Separation

The target run HALTed at:

```text
2022-12-16:current_valuation_refresh
```

B7 does not use valuation/PnL outcomes and does not attribute that HALT to Alternative C.

## Required Output Summary

TARGET_RUN = runtime-test-historical-extended-smoke-20260818T015851711672Z

SHADOW_EVALUATED_DAY_COUNT = 9

SHADOW_EVALUATED_ITEM_COUNT = 84

COMPARISON_INSUFFICIENT_COUNT = 0

B0_94320_MECHANISM_REPRODUCED = YES/PARTIAL

STRONG_ADD_CANDIDATE_COUNT = 9

STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT = 29 pairwise Runtime-order inversions; 2 confirmed B0 pending-cash prune cases

STRONG_ADD_STARVED_BY_WEAKER_NEW_NOTIONAL = `2,034,560` pairwise planned-notional basis; `120,360` confirmed B0 pending-cash prune notional

STRONG_NEW_PROTECTION = PASS

BUY_ADD_LABEL_PRIORITY_VIOLATION_COUNT = 0

BUY_NEW_LABEL_PRIORITY_VIOLATION_COUNT = 0

WEAK_ADD_PROMOTED_COUNT = 0

SHADOW_VS_PC_ORDER_DELTA_COUNT = 36 item-level / 6 day-level

SHADOW_VS_RUNTIME_ORDER_DELTA_COUNT = 36 item-level / 9 day-level

PROCESSING_ORDER_STARVATION_COUNT = 62 pairwise inversions

PROCESSING_ORDER_STARVATION_NOTIONAL = `4,112,850`

CASH_PRUNE_WITH_LOWER_CANONICAL_RANK_INCLUDED_COUNT = 2 confirmed B0 pending-cash cases

LOT_ORDER_STATUS = PARTIAL

CANONICAL_ORDER_EXPLAINABILITY_RATE = 100%

MATERIALIZATION_EXPLAINABILITY_RATE = 100%

FUTURE_INFORMATION_USED = NO

ACTUAL_TRADING_PATH_MUTATED = NO

NORMAL_STRATEGY_CAP_CHANGED = NO

SAFETY_HARD_CAP_CHANGED = NO

BUY_SELL_INDEPENDENCE_PRESERVED = YES

STRUCTURAL_GATE_PASS = NO

MUTATING_ALTERNATIVE_C_READINESS = NOT_READY_LOT_OR_RUNTIME_BRIDGE

MUTATING_ALTERNATIVE_C_AUTHORIZED = NO

## NEXT_RECOMMENDATION

refine lot/runtime bridge

Specifically, add a non-mutating bridge from diagnostic shadow / Runtime plans order to final Pending reserved-cash feasibility evidence so B8 can reconstruct cash causality for every starvation case without relying on B0 report-side values.

## Final Questions

### 1. Does the repaired shadow now reproduce the B0 strong-ADD starvation mechanism using complete PIT evidence?

YES for the PIT marginal-value mismatch and known B0 cash-prune cases; PARTIAL for complete cash-causality reconstruction across all cases.

### 2. Is there any evidence of hidden ADD_FIRST behavior?

NO.

### 3. Is there any evidence of hidden NEW_FIRST behavior inside the shadow itself?

NO. Current Runtime ordering still shows NEW-before-ADD processing in several cases, but that is distinct from shadow logic.

### 4. Can strong NEW still outrank weaker ADD?

YES, proven by focused B4/B6 tests. The repaired real mixed-day set has no weak ADD examples.

### 5. Can strong ADD outrank weaker/comparable NEW when PIT evidence supports it?

YES. The 9 real mixed-day ADD candidates are `ELIGIBLE_STRONG`; 75 ADD-over-NEW canonical pairs were observed.

### 6. Is the structural mechanism ready for a separate mutation-authorization review?

NO. It still needs the final Pending reserved-cash causality bridge.
