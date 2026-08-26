# Phase31-B9 — Final Marginal Capital Shadow Structural Revalidation

## PRIMARY_JUDGMENT

`PHASE31_B9_ALTERNATIVE_C_STRUCTURAL_GATE_PASS_READY_FOR_MUTATION_AUTHORIZATION_REVIEW`

B9 revalidated the B4-B8 non-mutating shadow evidence using existing diagnostic shadow artifacts for the target run. The structural gate passes: Alternative C is mature enough for a separate mutation-authorization review. This does not authorize mutation, does not prove profitability, and does not use Historical return/PnL.

## TARGET_RUN

`runtime-test-historical-extended-smoke-20260818T015851711672Z`

Artifact scope:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/<DATE>/diagnostic_shadow/marginal_capital_value_shadow.json`

Evaluated mixed BUY_NEW/BUY_ADD dates:

- `2022-08-19`
- `2022-08-22`
- `2022-08-23`
- `2022-08-24`
- `2022-08-30`
- `2022-09-01`
- `2022-09-15`
- `2022-09-16`
- `2022-09-20`

## Revalidated Metrics

`SHADOW_EVALUATED_DAY_COUNT = 9`

`MIXED_NEW_ADD_DAY_COUNT = 9`

`SHADOW_EVALUATED_ITEM_COUNT = 84`

`COMPARISON_INSUFFICIENT_COUNT = 0`

Class distribution:

| Class | Count |
| --- | ---: |
| `ELIGIBLE_STRONG` | 18 |
| `ELIGIBLE_COMPARABLE` | 66 |
| `COMPARISON_INSUFFICIENT` | 0 |

Intent/class distribution:

| Intent | Class | Count |
| --- | --- | ---: |
| `BUY_ADD` | `ELIGIBLE_STRONG` | 9 |
| `BUY_NEW` | `ELIGIBLE_STRONG` | 9 |
| `BUY_NEW` | `ELIGIBLE_COMPARABLE` | 66 |

## Candidate Comparison Gate

`BUY_ADD_LABEL_PRIORITY_VIOLATION_COUNT = 0`

`BUY_NEW_LABEL_PRIORITY_VIOLATION_COUNT = 0`

`WEAK_ADD_PROMOTED_COUNT = 0`

`STRONG_NEW_PROTECTION = PASS`

`STRONG_ADD_COMPARABLE = PASS`

`HIDDEN_ADD_FIRST = NO`

`HIDDEN_NEW_FIRST_IN_SHADOW = NO`

Real mixed-day evidence contains no weak ADD rows after the B6 PIT bridge, so weak ADD / strong NEW protection is additionally covered by focused B4/B6 regression tests. Focused tests confirm strong NEW can outrank weak ADD and weak ADD is not rescued by label.

## Strong ADD Evidence

`STRONG_ADD_CANDIDATE_COUNT = 9`

`STRONG_ADD_AHEAD_OF_COMPARABLE_NEW_COUNT = 66`

`STRONG_ADD_AHEAD_OF_NEW_PAIR_COUNT = 75`

`STRONG_ADD_ACTUALLY_STARVED_COUNT = 2`

`STRONG_ADD_ACTUALLY_STARVED_NOTIONAL = 120,360`

The two strict strong ADD cash-starvation cases are the B0 controls:

- `2022-08-19 / 94320`: `59,850`
- `2022-08-24 / 94320`: `60,510`

## Hidden NEW-First Check

`HIDDEN_NEW_FIRST_IN_SHADOW = NO`

`CURRENT_RUNTIME_NEW_BEFORE_STRONG_ADD_CASES = 29`

The 29 current Runtime cases are existing behavior: BUY_NEW items appear before strong ADD in actual Runtime/Pending order. They are the reason Alternative C exists. They are not shadow semantics and are not treated as a hidden NEW-first policy in Alternative C.

## Cash Causality Gate

`FULL_CASH_CAUSALITY_RECONSTRUCTED_COUNT = 42`

`FULL_CASH_CAUSALITY_UNRESOLVED_COUNT = 0`

`ACTUAL_STARVATION_COUNT = 14`

`ACTUAL_STARVATION_NOTIONAL = 2,606,860`

`ACTUAL_STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT = 2`

`ACTUAL_STRONG_ADD_STARVED_BY_WEAKER_NEW_NOTIONAL = 120,360`

`ACTUAL_STRONG_NEW_STARVED_BY_WEAKER_ADD_COUNT = 0`

`ACTUAL_STRONG_NEW_STARVED_BY_WEAKER_ADD_NOTIONAL = 0`

`CASH_PRUNE_WITH_LOWER_CANONICAL_RANK_INCLUDED_COUNT = 21`

`UNEXPLAINED_CASH_PRUNE_COUNT = 0`

`ORDER_INVERSION_WITHOUT_CASH_EFFECT_COUNT = 42`

Cash causality classifications:

| Classification | Count |
| --- | ---: |
| `NO_ACTUAL_STARVATION` | 42 |
| `CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM` | 14 |
| `LOT_CONSTRAINT` | 14 |
| `LEGITIMATE_FEASIBILITY_PRUNE` | 7 |
| `LEGITIMATE_REVIEW_OR_SAFETY` | 6 |
| `LEGITIMATE_CANONICAL_LOWER_PRIORITY` | 1 |
| `UNRESOLVED` | 0 |

## B0 Control Case Re-Derivation

### 2022-08-19 / 94320

Re-derived from diagnostic shadow bridged to `strategy_planning_authority_evidence.json#lineage.cash_feasible_buy_batch`:

- lifecycle intent: `BUY_ADD`
- marginal value class: `ELIGIBLE_STRONG`
- shadow priority: `1`
- actual Runtime order: `30`
- actual Pending order: `6`
- pre-batch cash: `187,950`
- required ADD reserved notional: `59,850`
- cumulative prior reserved notional: `163,000`
- remaining cash before ADD: `24,950`
- final state: `PRUNE`
- reason: `DEFERRED_INSUFFICIENT_RESERVED_CASH`
- causality: `CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM`

Lower canonical-priority prior included BUY_NEW items:

- `27780`: shadow priority `10`, pending order `1`, reserved `33,100`
- `60540`: shadow priority `4`, pending order `3`, reserved `44,200`
- `70140`: shadow priority `2`, pending order `4`, reserved `85,700`

### 2022-08-24 / 94320

Re-derived from diagnostic shadow bridged to `strategy_planning_authority_evidence.json#lineage.cash_feasible_buy_batch`:

- lifecycle intent: `BUY_ADD`
- marginal value class: `ELIGIBLE_STRONG`
- shadow priority: `1`
- actual Runtime order: `29`
- actual Pending order: `3`
- pre-batch cash: `68,900`
- required ADD reserved notional: `60,510`
- cumulative prior reserved notional: `55,700`
- remaining cash before ADD: `13,200`
- final state: `PRUNE`
- reason: `DEFERRED_INSUFFICIENT_RESERVED_CASH`
- causality: `CANONICAL_HIGHER_VALUE_ITEM_STARVED_BY_LOWER_VALUE_PRIOR_ITEM`

Lower canonical-priority prior included BUY_NEW item:

- `43760`: shadow priority `6`, pending order `1`, reserved `55,700`

## Lot / Discrete Quantity Gate

`LOT_ORDER_STATUS = YES`

`LOT_MATERIALIZATION_UNRESOLVED_COUNT = 0`

`MARGINAL_ORDER_SURVIVES_LOT_MATERIALIZATION_OR_TYPED_SKIP = YES`

Lot/materialization reason distribution:

| Reason | Count |
| --- | ---: |
| `EXECUTABLE_LOT` | 41 |
| `NOT_IN_RUNTIME_PLAN` | 42 |
| `CONCENTRATION_BOUND` | 1 |

No silent quantity disappearance was found. Non-materialized candidates carry typed reasons.

## Explainability Gate

`CANONICAL_ORDER_EXPLAINABILITY_RATE = 100%`

`MATERIALIZATION_EXPLAINABILITY_RATE = 100%`

`CASH_CAUSALITY_EXPLAINABILITY_RATE = 100%`

`UNEXPLAINED_ORDER_COUNT = 0`

`UNEXPLAINED_MATERIALIZATION_COUNT = 0`

`UNEXPLAINED_CASH_CAUSALITY_COUNT = 0`

## PIT / Future Leakage Gate

`FUTURE_INFORMATION_USED = NO`

`FUTURE_OUTCOME_FIELD_COUNT = 0`

`POST_DECISION_FIELD_COUNT = 0`

`UNKNOWN_TEMPORAL_BINDING_FIELD_COUNT = 0`

The shadow comparison consumes existing PIT Strategy/Portfolio Construction evidence and same-date Runtime/Pending cash authority evidence. It does not consume future price, future return, later PnL, fills, Historical outcomes, later market movement, or post-hoc labels.

If Phase31-A6 later finds retroactive contamination in any Strategy PIT evidence used here, affected B9 evidence must be revalidated. B9 does not use the later `2022-12-16:current_valuation_refresh` HALT or any valuation/PnL outcome.

## Architecture Ownership Gate

`ARCHITECTURE_OWNERSHIP_VIOLATION = NO`

Confirmed boundaries:

| Component | B9 Judgment |
| --- | --- |
| PM | PASS: owns ADD intent / eligibility evidence; does not own final capital order. |
| Portfolio Construction | PASS: owns marginal capital priority, allocation, and canonical Strategy order. |
| Position Sizing | PASS: consumes PC target/discrete authority; does not invent priority. |
| Runtime Planning | PASS: consumes canonical Strategy order for reserved-cash ordering; does not decide NEW vs ADD preference. |
| Pending | PASS: consumes Runtime Planning result and review scope; does not re-rank Strategy opportunities. |
| Submit | PASS: validates feasibility; does not resize or re-prioritize Strategy. |
| Safety | PASS: owns hard safety boundary; does not own marginal investment priority. |

## Quantity / Cash Contracts

`CANONICAL_QUANTITY_CHAIN_PRESERVED = YES`

Quantity lineage remains:

`PC discrete quantity -> PS -> Runtime Planning -> Pending -> Submit -> Fill`

Distinct cash semantics remain separate:

- Strategy deployable budget
- PC incremental budget
- Current cash
- Pending reserved cash
- Submit aggregate cash
- broker buying power
- post-fill cash

Alternative C must not create a generic merged cash authority.

## BUY / SELL Independence

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

Reviewed or pruned BUY evidence does not block valid SELL evidence. Alternative C, if later authorized, must only affect BUY marginal capital ordering.

## Cap Isolation

`NORMAL_STRATEGY_CAP_CHANGED = NO`

`SAFETY_HARD_CAP_CHANGED = NO`

`WINNER_HEADROOM_ADDED = NO`

Alternative E remains a separate future gate.

## Current Trading Path Non-Mutation

`ACTUAL_PC_DECISION_MUTATED = NO`

`ACTUAL_PS_QUANTITY_MUTATED = NO`

`ACTUAL_RUNTIME_ORDER_MUTATED = NO`

`ACTUAL_PENDING_MUTATED = NO`

`ACTUAL_SUBMIT_MUTATED = NO`

`ACTUAL_EXECUTION_MUTATED = NO`

`ACTUAL_FILL_MUTATED = NO`

`ACTUAL_RUN_STATE_MUTATED = NO`

`ACTUAL_TRADING_PATH_MUTATED = NO`

## B3_INVARIANT_RESULTS

| # | Invariant | Result |
| ---: | --- | --- |
| 1 | BUY_ADD label alone cannot increase priority. | PASS |
| 2 | BUY_NEW label alone cannot increase priority. | PASS |
| 3 | Weak ADD is not rescued. | PASS |
| 4 | Strong NEW may outrank weak ADD. | PASS |
| 5 | Strong ADD may outrank comparable/weaker NEW if PIT evidence supports it. | PASS |
| 6 | PC owns canonical marginal order. | PASS |
| 7 | Runtime consumes order rather than invents it. | PASS |
| 8 | Pending cash causality is fully explainable. | PASS |
| 9 | Quantity lineage is preserved. | PASS |
| 10 | Cash authority semantics are preserved. | PASS |
| 11 | Normal Strategy cap unchanged. | PASS |
| 12 | Safety hard cap unchanged. | PASS |
| 13 | BUY/SELL independence preserved. | PASS |
| 14 | No future leakage. | PASS |
| 15 | Cash remains valid when no opportunity exists. | PASS |
| 16 | No 94320-specific rule. | PASS |
| 17 | No Historical-return optimized priority. | PASS |
| 18 | Lot/discrete behavior explainable. | PASS |

## Structural Gate Decision

`STRUCTURAL_GATE_PASS = YES`

This means only that Alternative C is structurally mature enough for a separate mutation-authorization review. It does not mean Alternative C is profitable or should be deployed without a separate user-authorized implementation task.

`MUTATING_ALTERNATIVE_C_READINESS = READY_FOR_AUTHORIZATION_REVIEW`

`MUTATING_ALTERNATIVE_C_AUTHORIZED = NO`

## Narrow Mutation Surface If Authorized

If the user separately authorizes mutating Alternative C, the narrow conceptual mutation surface should be:

- Portfolio Construction: materialize canonical marginal priority as real authority for already-eligible BUY_NEW and positive-increment BUY_ADD units.
- Runtime Planning: preserve that canonical priority in BUY reserved-cash feasibility ordering.
- Position Sizing: continue consuming existing PC quantity authority.

Do not change:

- PM ADD semantics
- Expected Edge thresholds
- Incremental Investment Value thresholds
- Opportunity Cost thresholds
- Market Context logic
- normal Strategy cap
- Safety hard cap
- winner headroom
- Submit
- Execution
- SELL

## Pre-Mutation Validation Requirement

Before or with any B10 implementation, require focused tests for:

- authority contract ownership
- exact actual-order preservation where priorities are equal
- strong ADD vs weaker/comparable NEW
- strong NEW vs weak ADD
- cash-limited mixed batch
- lot-bound mixed batch
- BUY/SELL independence
- quantity authority regression
- Pending review scope regression
- Safety hard-cap regression
- no-future-leakage

Do not run long Historical as part of the implementation step.

## Performance Validation Separation

`ACTUAL_STRONG_ADD_STARVATION != PROVEN_RETURN_UPLIFT`

The evidence proves capital-allocation opportunity loss under the canonical PIT marginal-value contract. It does not prove final return improvement.

After any future mutating implementation, validation must proceed separately:

1. focused tests
2. short user-operated targeted validation
3. separate chronological validation evidence
4. winner damage analysis
5. NEW opportunity damage analysis
6. capital deployment analysis
7. MDD/risk analysis
8. longer clean Historical
9. holdout confirmation where feasible

Do not tune Alternative C from the current development run.

## Validation Commands

Focused regression tests were rerun:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_b9_pycache python3 -m pytest -q tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py
```

Result:

`19 passed in 0.31s`

No fresh-run, resume, replay, 25BD, 100BD, 500BD, or long Historical runtime was executed.

## Final Questions

1. Is the BUY_NEW / BUY_ADD processing-order starvation defect now proven with complete PIT and Pending cash causality evidence?

`YES`

2. Does the proposed Alternative C shadow contain hidden ADD_FIRST behavior?

`NO`

3. Does it contain hidden NEW_FIRST behavior?

`NO`

4. Can strong NEW outrank weak ADD?

`YES`

5. Can strong ADD outrank weaker/comparable NEW when PIT evidence supports it?

`YES`

6. Are lot, cash, quantity, Pending, Safety, and BUY/SELL contracts preserved?

`YES`

7. Is Alternative C structurally ready for a separately authorized mutating implementation?

`YES`

## NEXT_RECOMMENDATION

Prepare a separate mutating Alternative C implementation task for user authorization review. Do not execute that task inside B9.
