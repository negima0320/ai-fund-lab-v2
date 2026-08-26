# Phase31-B5 — Marginal Capital Value Shadow Evidence Validation

## PRIMARY_JUDGMENT

PHASE31_B5_MARGINAL_CAPITAL_SHADOW_NOT_READY_FOR_MUTATION

The B4 shadow mechanism can be evaluated against completed-day Strategy artifacts and it remains non-mutating, PIT-only, and explicit about insufficient comparison evidence. However, the real-evidence validation found two structural gaps that block mutation authorization:

1. B4 is not wired to a real-evidence non-mutating invocation path.
2. The B4 producer does not yet consume the target run's actual Runtime Planning `plans` structure as `actual_runtime_cash_batch_order`; the field remains empty on real artifacts unless a diagnostic evaluator derives the Runtime order separately.

The shadow therefore validates important guardrails, but not the full B3 order-preservation mechanism.

## TARGET_RUN

runtime-test-historical-extended-smoke-20260818T015851711672Z

## Scope

Only completed business days from `run_state.json` were evaluated.

No fresh-run, resume, replay, 25BD, 100BD, 500BD, long Historical execution, Strategy decision regeneration, Submit, Execution, fill, ledger, or valuation outcome analysis was performed.

The run later HALTed at `2022-12-16:current_valuation_refresh`; this B5 report does not attribute that HALT to Alternative C and does not use PnL/valuation outcome labels.

## Q1 — Shadow Production Path

SHADOW_INVOCATION_PATH = not wired to production or run materialization; B5 used an in-memory diagnostic invocation of `build_marginal_capital_value_shadow_payload`.

SHADOW_INPUT_ARTIFACTS:

- `daily/<business_date>/strategy/portfolio_construction.json`
- `daily/<business_date>/strategy/position_sizing.json`
- `daily/<business_date>/strategy/runtime_planning.json`
- `daily/<business_date>/morning/pending_generation_evidence.json`

SHADOW_OUTPUT_ARTIFACT = B4 canonical default would be `strategy_artifacts/marginal_capital_value_shadow/<business_date>/marginal_capital_value_shadow.json`; B5 did not write per-day shadow artifacts into the target run to avoid mutating run evidence.

Runtime authority consumption = NO

Trading-state mutation = NO

Actual order mutation = NO

## Q2 — Evaluated Evidence

SHADOW_EVALUATED_DAY_COUNT = 9

SHADOW_EVALUATED_ITEM_COUNT = 84

DAYS_WITH_BOTH_NEW_AND_ADD:

- `2022-08-19`
- `2022-08-22`
- `2022-08-23`
- `2022-08-24`
- `2022-08-30`
- `2022-09-01`
- `2022-09-15`
- `2022-09-16`
- `2022-09-20`

Class distribution:

| Class | Count |
| --- | ---: |
| `ELIGIBLE_STRONG` | 9 |
| `ELIGIBLE_COMPARABLE` | 66 |
| `COMPARISON_INSUFFICIENT` | 9 |

Intent/class distribution:

| Intent | Class | Count |
| --- | --- | ---: |
| `BUY_NEW` | `ELIGIBLE_STRONG` | 9 |
| `BUY_NEW` | `ELIGIBLE_COMPARABLE` | 66 |
| `BUY_ADD` | `COMPARISON_INSUFFICIENT` | 9 |

## Q3 — B0 Development Reproduction

B0_94320_CASES_EXPLAINABLE = YES, with a blocking caveat: B4 does not prove 94320 should win. It places 94320 behind NEW because the B4 source extraction lacks explicit campaign-continuation evidence and emits `COMPARISON_INSUFFICIENT`.

### 2022-08-19 / 94320

BUY_ADD 94320 shadow class = `COMPARISON_INSUFFICIENT`

94320 reason = `missing_or_non_pass_add_evidence:campaign`

Competing BUY_NEW classes:

- `70140`: `ELIGIBLE_STRONG`
- `93180`, `60540`, `52120`, `67310`, `79010`, `88910`, `95010`, `27780`: `ELIGIBLE_COMPARABLE`

Canonical shadow order:

`70140 -> 93180 -> 60540 -> 52120 -> 67310 -> 79010 -> 88910 -> 95010 -> 27780 -> 94320`

Actual PC order among evaluated candidates:

`94320 -> 93180 -> 60540 -> 52120 -> 67310 -> 79010 -> 70140 -> 88910 -> 95010 -> 27780`

Actual Runtime buy order derived from `runtime_planning.plans`:

`27780 -> 52120 -> 60540 -> 70140 -> 93180 -> 94320 -> 95010`

Prior BUY_NEW reserved notional = `163,000` from B0 PIT audit.

94320 reserved notional = `59,850` from B0 PIT audit.

Shadow-vs-actual difference classification = `COMPARISON_INSUFFICIENT` for 94320; `LEGITIMATE_FEASIBILITY_DIFFERENCE` for B4 item-level NEW differences.

Interpretation: no accidental ADD-first rule appears in the shadow. The shadow also fails to validate strong ADD priority because ADD campaign evidence is not sufficiently materialized into B4's comparison inputs.

### 2022-08-24 / 94320

BUY_ADD 94320 shadow class = `COMPARISON_INSUFFICIENT`

94320 reason = `missing_or_non_pass_add_evidence:campaign`

Competing BUY_NEW classes:

- `93180`: `ELIGIBLE_STRONG`
- `99840`, `52120`, `66190`, `43760`: `ELIGIBLE_COMPARABLE`

Canonical shadow order:

`93180 -> 99840 -> 52120 -> 66190 -> 43760 -> 94320`

Actual PC order among evaluated candidates:

`94320 -> 93180 -> 99840 -> 52120 -> 66190 -> 43760`

Actual Runtime buy order derived from `runtime_planning.plans`:

`43760 -> 93180 -> 94320`

Prior BUY_NEW reserved notional = `55,700` from B0 PIT audit.

94320 reserved notional = `60,510` from B0 PIT audit.

Shadow-vs-actual difference classification = `COMPARISON_INSUFFICIENT` for 94320; `LEGITIMATE_FEASIBILITY_DIFFERENCE` for B4 item-level NEW differences.

Interpretation: 94320 is explainably behind NEW in the current shadow due comparison insufficiency, not because the shadow learned a hidden NEW-first or ADD-first policy.

## Q4 — Strong NEW Protection

STRONG_NEW_PROTECTION = PASS

STRONG_NEW_AHEAD_OF_ADD_CASE_COUNT = 7

Real completed-day evidence contains cases where strong/comparable BUY_NEW ranks ahead of BUY_ADD. This is not a performance claim; it only confirms the shadow does not become hidden ADD_FIRST.

## Q5 — Weak ADD Protection

BUY_ADD_LABEL_PRIORITY_VIOLATION_COUNT = 0

BUY_NEW_LABEL_PRIORITY_VIOLATION_COUNT = 0

WEAK_ADD_PROMOTED_BY_LABEL_COUNT = 0

Expected Edge weakening, non-positive/unknown incremental value, opportunity-cost failure, or missing ADD lifecycle evidence did not gain priority from the ADD label. All 9 real BUY_ADD units were `COMPARISON_INSUFFICIENT`, not promoted.

## Q6 — Comparison Insufficient

COMPARISON_INSUFFICIENT_COUNT = 9

COMPARISON_INSUFFICIENT_RATE = 10.7% (`9 / 84`)

Blocking dimension:

| Reason | Count |
| --- | ---: |
| `missing_or_non_pass_add_evidence:campaign` | 9 |

This is the central B5 maturity gap. B0/B1 showed 94320 had PIT ADD evidence in surrounding Strategy artifacts, but B4's candidate extraction does not yet carry enough explicit same-campaign/campaign-continuation evidence into the shadow comparison. B5 must not repair that by inventing numeric weights or carrying labels forward.

## Q7 — Shadow vs Actual Order

SHADOW_VS_PC_ORDER_DELTA_COUNT = 84 item-level differences across 9 mixed days.

SHADOW_VS_RUNTIME_ORDER_DELTA_COUNT = 9 day-level sequence differences when Runtime order is diagnostically derived from `runtime_planning.plans`.

Important producer gap: B4 artifact `actual_runtime_cash_batch_order` is empty on these real artifacts because the producer only looks for cash-batch shaped fields and does not parse the actual `plans` list.

SHADOW_ADD_AHEAD_OF_NEW_COUNT = 0 cross-lifecycle shadow pairs.

SHADOW_NEW_AHEAD_OF_ADD_COUNT = 75 cross-lifecycle shadow pairs.

ACTUAL_ORDER_PROCESSING_ARTIFACT_COUNT = 0 in B4's own item classification.

LOT_MATERIALIZATION_DIFFERENCE_COUNT = 0 as a separate B4 classification.

LEGITIMATE_FEASIBILITY_DIFFERENCE_COUNT = 75 in B4 item classification.

REVIEW_OR_SAFETY_DIFFERENCE_COUNT = 0

The high feasibility-difference count reflects that several shadow candidates have accepted target/increment evidence but Runtime/PS materialization can yield zero executable buy quantity or omit them from the Runtime buy list. This requires a clearer typed lot/materialization bridge before mutation.

## Q8 — Processing-Order Starvation

PROCESSING_ORDER_STARVATION_COUNT = 37 diagnostic Runtime-plan inversions against current shadow order.

PROCESSING_ORDER_STARVATION_NOTIONAL = `2,791,680` diagnostic planned-notional basis.

STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT = 0 under current B4 shadow classes, because all real ADD units are `COMPARISON_INSUFFICIENT`.

STRONG_NEW_STARVED_BY_WEAKER_ADD_COUNT = 37 under the current diagnostic inversion definition.

CASH_PRUNE_WITH_LOWER_RANK_INCLUDED_COUNT = 37 diagnostic inversions.

This does not overturn B0. It means the current B4 shadow is not yet capable of reproducing B0's strong-ADD starvation mechanism because it fails closed on ADD campaign evidence.

## Q9 — Canonical Order Explainability

SHADOW_ORDER_EXPLAINED_COUNT = 84

SHADOW_ORDER_UNEXPLAINED_COUNT = 0

CANONICAL_ORDER_EXPLAINABILITY_RATE = 100%

Every order difference is backed by explicit reason evidence or explicit `COMPARISON_INSUFFICIENT`. No silent fallback superiority was used as an investment explanation.

## Q10 — PIT / Leakage Audit

FUTURE_INFORMATION_USED = NO

FUTURE_OUTCOME_FIELD_COUNT = 0

POST_DECISION_FIELD_COUNT = 0

UNKNOWN_TEMPORAL_BINDING_FIELD_COUNT = 0 at artifact-level validation scope.

The evaluated source artifacts carry `business_date`, `as_of`, `feature_date`, and source hashes. B5 did not inspect or use future price, forward return, later PnL, later campaign outcome, MFE/MAE outcome labels, fill outcome, selected/bought outcome, future-known regime, or Historical performance labels.

If Phase31-A6 later finds retroactive evidence contamination in these dates, affected B5 evidence must be marked invalid and revalidated.

## Q11 — Lot Materialization

LOT_ORDER_STATUS = PARTIAL

MARGINAL_ORDER_SURVIVES_LOT_MATERIALIZATION_OR_TYPED_SKIP = PARTIAL

Evidence:

- Lot-aware quantity requirements are preserved in candidate units.
- B0 cases show 94320 had executable BUY_ADD quantities in RP (`300` shares on both `2022-08-19` and `2022-08-24`).
- Several BUY_NEW candidates in shadow order have zero Runtime quantity and are absent from derived Runtime buy order.
- B4 does not yet produce a sufficiently typed per-candidate lot skip / residual cash / next-canonical-candidate explanation for all real differences.

## Q12 — Runtime Non-Mutation Proof

ACTUAL_PC_DECISION_MUTATED = NO

ACTUAL_PS_QUANTITY_MUTATED = NO

ACTUAL_RUNTIME_ORDER_MUTATED = NO

ACTUAL_PENDING_MUTATED = NO

ACTUAL_SUBMIT_MUTATED = NO

ACTUAL_FILL_MUTATED = NO

ACTUAL_TRADING_PATH_MUTATED = NO

B5 used existing completed-day artifacts and an in-memory diagnostic evaluator. It did not write into the run's daily artifacts and did not connect the shadow to any Runtime authority consumer.

## Q13 — Structural Gate

STRUCTURAL_GATE_PASS = NO

Gate results:

| Gate | Result |
| --- | --- |
| no future leakage | PASS |
| BUY_ADD label alone gives no priority | PASS |
| BUY_NEW label alone gives no priority | PASS |
| weak ADD protection | PASS |
| strong NEW protection | PASS |
| B0 development cases explainable | PASS with `COMPARISON_INSUFFICIENT` caveat |
| shadow order fully auditable | PASS |
| no accidental processing-order superiority hidden | PASS |
| lot semantics coherent | PARTIAL |
| actual trading path unchanged | PASS |
| actual Runtime order consumed by B4 artifact | FAIL |
| ADD campaign evidence sufficient for marginal comparison | FAIL |

## Q14 — Mutation Authorization

MUTATING_ALTERNATIVE_C_AUTHORIZED = NO

B5 does not authorize mutation by itself, and the current evidence does not support mutation anyway.

## Required Output Summary

TARGET_RUN = runtime-test-historical-extended-smoke-20260818T015851711672Z

SHADOW_EVALUATED_DAY_COUNT = 9

SHADOW_EVALUATED_ITEM_COUNT = 84

DAYS_WITH_BOTH_NEW_AND_ADD = `2022-08-19`, `2022-08-22`, `2022-08-23`, `2022-08-24`, `2022-08-30`, `2022-09-01`, `2022-09-15`, `2022-09-16`, `2022-09-20`

B0_94320_CASES_EXPLAINABLE = YES

BUY_ADD_LABEL_PRIORITY_VIOLATION_COUNT = 0

BUY_NEW_LABEL_PRIORITY_VIOLATION_COUNT = 0

WEAK_ADD_PROMOTED_BY_LABEL_COUNT = 0

STRONG_NEW_PROTECTION = PASS

COMPARISON_INSUFFICIENT_COUNT = 9

COMPARISON_INSUFFICIENT_RATE = 10.7%

SHADOW_VS_PC_ORDER_DELTA_COUNT = 84 item-level / 9 day-level

SHADOW_VS_RUNTIME_ORDER_DELTA_COUNT = 9 day-level, diagnostically derived from `runtime_planning.plans`; B4 artifact field is empty on real RP shape

PROCESSING_ORDER_STARVATION_COUNT = 37 diagnostic inversions

PROCESSING_ORDER_STARVATION_NOTIONAL = `2,791,680`

STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT = 0

STRONG_NEW_STARVED_BY_WEAKER_ADD_COUNT = 37

CANONICAL_ORDER_EXPLAINABILITY_RATE = 100%

LOT_ORDER_STATUS = PARTIAL

FUTURE_INFORMATION_USED = NO

ACTUAL_TRADING_PATH_MUTATED = NO

STRUCTURAL_GATE_PASS = NO

MUTATING_ALTERNATIVE_C_AUTHORIZED = NO

## NEXT_RECOMMENDATION

repair/refine shadow comparison semantics

Specifically:

1. Add a read-only real-evidence materialization/evaluation command or job that writes shadow artifacts only under a diagnostic shadow namespace.
2. Teach the shadow evaluator to consume actual `runtime_planning.plans` order as Runtime cash-batch evidence without mutating Runtime.
3. Carry explicit PIT ADD campaign-continuation evidence into candidate units so strong ADD can be compared rather than fail-closed as `COMPARISON_INSUFFICIENT`.
4. Add typed lot/materialization skip reasons linking shadow order to PS/RP executable quantity outcomes.

Do not implement mutating Alternative C until those gaps are validated in a separate task.
