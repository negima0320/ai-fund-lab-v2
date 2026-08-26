# Phase31-B3 — Marginal Capital Priority Contract Validation Design

## PRIMARY_JUDGMENT

`VALIDATE_ALTERNATIVE_C_AS_MECHANISM_NOT_RETURN_OPTIMIZATION_BEFORE_IMPLEMENTATION`

Alternative C must be validated as an authority/order-preservation mechanism before implementation is authorized. The validation target is not final Historical return and not a 94320-optimized rule. The target is whether a Portfolio Construction-owned PIT marginal-capital order can prevent accidental processing-order starvation while preserving strong BUY_NEW opportunities, legitimate weak-ADD rejection, canonical quantity lineage, Safety hard cap, BUY/SELL independence, cash validity, and lot/discrete correctness.

B0/B1/B2 evidence is design/development evidence. The current run and known 94320 cases may be reused for architecture reproduction, contract regression cases, and descriptive characterization, but not as untouched holdout and not for parameter selection.

Performance implementation remains unauthorized.

## Scope

| Field | Value |
| --- | --- |
| `TASK_TYPE` | `DESIGN_ONLY_READ_ONLY` |
| `TARGET_RUN_CONTEXT` | `runtime-test-historical-extended-smoke-20260818T015851711672Z` |
| `VALIDATION_TARGET` | Alternative C only: canonical marginal-capital ordering between already-eligible BUY_NEW and BUY_ADD opportunities. |
| `OUT_OF_SCOPE_FOR_B3` | Strategy implementation, parameter tuning, cap changes, winner headroom, Alternative E implementation, Expected Edge threshold changes, ADD eligibility changes, exposure targets, position-count targets, fresh/long Historical execution by Codex. |
| `PRIMARY_SUCCESS_CONCEPT` | Explicit PIT marginal order reaches Runtime reserved-notional pruning; no accidental investment priority from iteration order. |
| `PERFORMANCE_IMPLEMENTATION_AUTHORIZED` | `NO` |

## Validation Layers

### Layer 1 — Contract / Architecture Validation

Responsibility: prove authority ownership and lineage remain conformant.

Required checks:

- PC owns `MARGINAL_CAPITAL_VALUE_AUTHORITY`.
- PS consumes PC target/discrete quantity and does not invent priority.
- Runtime Planning consumes canonical Strategy order and does not rank BUY_NEW/BUY_ADD itself.
- Submit validates quantity/cash/safety; it does not resize or re-decide Strategy allocation.
- Safety hard cap remains Safety.
- BUY/SELL independence remains intact.
- No future/outcome fields appear in order evidence.

### Layer 2 — Decision / Ordering Validation

Responsibility: prove the canonical order behaves as designed on PIT evidence.

Required checks:

- BUY_ADD label alone never raises priority.
- BUY_NEW label alone never raises priority.
- Strong NEW can outrank weak ADD.
- Strong ADD can outrank merely comparable NEW when lifecycle evidence supports higher marginal value.
- Expected Edge `WEAKENING` ADD remains non-prioritized under existing semantics.
- Near-comparable cases have deterministic, auditable tie handling.

### Layer 3 — Capital Allocation / Funnel Validation

Responsibility: prove capital follows the canonical order through lot/cash mechanics.

Required checks:

- PC marginal order survives lot-aware final reallocation or records explicit lot-skip reasons.
- Runtime reserved-notional pruning follows canonical order.
- Processing-order starvation due only to incidental iteration order becomes zero.
- ADD funnel is reported separately: Alternative C should affect positive-increment/executable ADD to Pending/Fill, not the upstream PM ADD -> PC positive increment narrowing.
- BUY_NEW funnel remains healthy and high-quality NEW is not starved by weaker ADD.

### Layer 4 — Performance / Risk Validation

Responsibility: evaluate downstream portfolio quality only after structural mechanism passes.

Required checks:

- Return, PnL, MDD, drawdown duration, daily PnL distribution, downside tail, winner/loser contribution, turnover, concentration, and exposure are evaluation labels only.
- No ordering rule or threshold is selected because it improves Historical return.
- Winner damage and NEW opportunity damage are mandatory review sections.

## Pre-Registered Success Criteria

Structural success criteria:

- `PROCESSING_ORDER_STARVATION_COUNT` attributable only to arbitrary BUY_NEW/BUY_ADD iteration order is zero.
- `CANONICAL_ORDER_PRESERVATION_RATE` is 100% except where explicit later-stage Safety, broker, cash, review, or lot authority blocks an item with typed evidence.
- Runtime Planning evidence carries and preserves PC canonical priority.
- Weak ADD is not rescued by label alone.
- Strong NEW remains capable of outranking weak ADD.
- Canonical quantity lineage remains unchanged: PC discrete quantity -> PS -> Runtime Planning -> Pending -> Submit -> Fill.
- Safety hard cap remains unchanged.
- Normal Strategy cap remains unchanged for Alternative C.
- Valid SELL remains independent from BUY marginal competition.
- Cash remains a valid residual result.
- No future leakage or Historical outcome fields participate in ordering.

Performance/risk success criteria:

- Numeric gates must be chosen before implementation from risk policy, existing non-B3 architecture gates, or pre-registered operator policy, not from the target run's outcome.
- Directional evaluation is allowed: no unexplained worsening in concentration instability, no systematic high-quality NEW starvation, no unexplained cash starvation migration from ADD to NEW, and no winner robustness damage hidden by higher total return.

## Evidence Separation

| Evidence class | Use |
| --- | --- |
| `DESIGN_DEVELOPMENT_EVIDENCE` | B0/B1/B2, current inspected 94320 cases, completed-day funnel counts, known B0 starvation dates. Used for design rationale and regression cases only. |
| `VALIDATION_EVIDENCE` | Later user-operated runs or pre-declared chronological segments/symbol sets not used to shape the rule. Used to evaluate Alternative C mechanics after implementation/shadowing. |
| `HOLDOUT_EVIDENCE` | Untouched chronological period(s) or separate long-run evidence reserved for final confirmation where feasible. Must not include B0/B1/B2-inspected 94320 cases as untouched holdout. |

Selection principles:

- Split chronologically or by pre-declared run boundary, never by favorable returns.
- Preserve multiple Market Context states where available.
- Avoid symbol-specific splits that isolate only 94320.
- Do not execute splits in B3; define them before future validation runs.

## Current Run Reuse Rule

The current run may be used for:

- architecture reproduction;
- B0/B1/B2 regression examples;
- shadow artifact schema design;
- descriptive characterization;
- contract test case construction.

The current run must not be used for:

- parameter selection;
- threshold tuning;
- final validation claims;
- untouched holdout;
- selecting a rule because 94320 or final return improves.

Known B0 cases `2022-08-19 94320` and `2022-08-24 94320` are development regression cases. Required result is not that 94320 must win; required result is that any win/loss is explained by canonical marginal value or explicit feasibility/Safety evidence, not accidental iteration order.

## Alternative C Isolation

Alternative C validation must not change:

- normal Strategy cap;
- Safety hard cap;
- winner headroom;
- Expected Edge, Incremental Investment Value, Opportunity Cost, Market Context thresholds;
- ADD eligibility;
- PM semantics;
- position count targets;
- exposure targets.

Only the effect of explicit canonical marginal-capital ordering among already-eligible BUY_NEW and BUY_ADD opportunities is validated.

## Mandatory Invariants

1. BUY_ADD label alone cannot increase priority.
2. BUY_NEW label alone cannot increase priority.
3. Expected Edge `WEAKENING` ADD remains non-incremental / non-prioritized under existing semantics.
4. Canonical PC marginal order reaches Runtime Planning unchanged except where explicit later-stage authority blocks an item.
5. Reserved-notional pruning follows canonical Strategy order, not incidental iteration order.
6. Valid SELL remains independent from BUY marginal competition.
7. Safety hard cap remains unchanged.
8. Normal Strategy cap remains unchanged in Alternative C.
9. No Historical outcome labels participate in ordering.
10. Cash remains valid when no qualifying marginal opportunity exists.
11. PC remains target/allocation/order authority; PS and Runtime do not duplicate it.
12. Lot/discrete quantity authority remains canonical and auditable.
13. Reviewed BUY does not block valid SELL.
14. No 94320-specific rule, symbol-specific exception, or current-run outcome proxy.

## Candidate Comparison Evidence

Permitted existing Production-visible evidence:

- Expected Edge and same-campaign Expected Edge trajectory;
- Incremental Investment Value;
- Opportunity Cost;
- opportunity rank / relative score under the uncalibrated score contract;
- Entry Quality / ADD-worthiness;
- momentum, trend, acceleration, decay;
- Market Context;
- current campaign state;
- current position state;
- current/target weight and concentration headroom;
- lot feasibility, broker feasibility, Safety hard-cap preservation.

B3 does not choose numeric weights. The validation may define semantic order classes such as:

```text
BLOCKED_OR_NOT_ELIGIBLE
ELIGIBLE_WEAK
ELIGIBLE_COMPARABLE
ELIGIBLE_STRONG
REVIEW_REQUIRED
```

These classes must be auditable normalization of existing evidence, not a new alpha predictor. If NEW and ADD evidence cannot be compared without hidden weighting, the design must mark the case as `COMPARISON_INSUFFICIENT` and defer to deterministic non-investment tie handling rather than tuning.

## No New Predictor Rule

`marginal_capital_value_class` is an ordering contract, not a trained feature.

Controls:

- It must be derived only from existing PIT fields already available to Production Strategy.
- It must disclose source fields and authority status.
- It must not consume final PnL, future return, future MFE/MAE, campaign outcome, fill outcome, or later regime labels.
- It must not be trained against Historical return.
- It must have reason codes explaining class/order.
- Any missing or incomparable evidence must be explicit and fail closed or deterministic.

## Development Regression Cases

### B0 Reproduction Cases

| Case | Expected test question |
| --- | --- |
| `2022-08-19 94320` | Where does 94320 rank against competing BUY_NEW units using only PIT evidence, and does Runtime preserve that order? |
| `2022-08-24 94320` | If 94320 still loses capital, is the cause canonical marginal order or legitimate feasibility/Safety/cash evidence? |

Expected result:

```text
NO_ACCIDENTAL_PROCESSING_ORDER_DECISION
```

not:

```text
94320_MUST_WIN
```

### Strong NEW Protection Cases

Select cases before outcome review where:

- BUY_NEW has stronger PIT marginal evidence than available ADD;
- capital is limited;
- NEW has clean eligibility and lot/Safety feasibility.

Expected: BUY_NEW may rank ahead. This prevents hidden `ADD_FIRST`.

### Weak ADD Protection Cases

Include PM ADD rows with:

- Expected Edge `WEAKENING`;
- Incremental Value not `POSITIVE`;
- Opportunity Cost fail;
- Market Context deterioration;
- concentration/headroom failure.

Expected: Alternative C must not rescue ADD merely because it is ADD.

### Equal / Near-Comparable Cases

If NEW and ADD have near-comparable PIT evidence, lifecycle-aware continuation may be a documented tie component only when the evidence is explicit and comparable. No numeric tie threshold may be selected from B0/B1. If insufficient, deterministic fallback should be:

```text
preserve existing PC stable order with COMPARISON_INSUFFICIENT evidence
```

or defer tie design.

## Lot-Aware Validation

Validate at executable lot granularity:

- one NEW lot vs one ADD lot;
- multiple ADD lots from same symbol;
- multiple NEW candidates;
- residual capital after first allocation;
- next candidate skipped because the next lot does not fit;
- reallocation after lot skip;
- Strategy concentration cap boundary;
- Safety hard-cap boundary;
- low-price/high-share-count cases.

Required property:

```text
MARGINAL_ORDER_SURVIVES_LOT_MATERIALIZATION_OR_TYPED_SKIP
```

The order must rank executable lot units or explicitly mark fractional units as non-executable.

## Metrics

### Cash-Starvation Metrics

- `PROCESSING_ORDER_STARVATION_COUNT`
- `PROCESSING_ORDER_STARVATION_NOTIONAL`
- `STRONG_ADD_STARVED_BY_WEAKER_NEW_COUNT`
- `STRONG_NEW_STARVED_BY_WEAKER_ADD_COUNT`
- `CANONICAL_ORDER_PRESERVATION_RATE`
- `RESERVED_CASH_PRUNE_BY_CANONICAL_RANK`
- `UNEXPLAINED_CASH_PRUNE_COUNT`
- `CASH_PRUNE_WITH_LOWER_RANK_INCLUDED_COUNT`

Strong/weak must be PIT-class based, never future-outcome based.

### ADD Funnel Metrics

Track:

```text
PM ADD
-> PC positive increment
-> PS BUY_ADD
-> Runtime Planning
-> Pending
-> Submit
-> Fill
```

Alternative C should be credited only for the positive-increment/executable opportunity -> capital-ordering/Pending/Fill segment. It must not be credited for solving B1's upstream `63 -> 9` materialization gap.

### BUY_NEW Preservation Metrics

- `BUY_NEW_ELIGIBLE_COUNT`
- `BUY_NEW_POSITIVE_ALLOCATION_COUNT`
- `BUY_NEW_FILLED_COUNT`
- `BUY_NEW_FILLED_NOTIONAL`
- `HIGH_PIT_NEW_DISPLACED_BY_ADD_COUNT`
- `NEW_LOST_TO_LOWER_VALUE_ADD_COUNT`
- `BUY_NEW_OPPORTUNITY_RANK_DISTRIBUTION`
- `BUY_NEW_SHORT_HOLD_EARLY_FAILURE` as outcome label only

### Capital / Portfolio Metrics

- average cash;
- final cash;
- average exposure;
- final exposure;
- deployable capital;
- deployed capital;
- stranded capital;
- turnover;
- turnover / equity;
- position count distribution;
- concentration distribution.

High exposure is not a success target. Capital should follow opportunity.

### Performance / Risk Metrics

After structural validation:

- total return;
- realized PnL;
- unrealized PnL;
- MDD;
- drawdown duration;
- recovery duration;
- daily PnL distribution;
- downside tail;
- profit concentration;
- winner contribution;
- loser contribution.

Do not optimize the ordering rule to these outcomes.

## Damage Analysis

### WINNER_DAMAGE_ANALYSIS

Track:

- top contribution campaigns;
- long HOLD campaigns;
- successful ADD campaigns;
- high-MFE campaigns where clean PIT/outcome separation exists;
- campaigns receiving less capital because NEW outranked ADD;
- campaigns receiving more capital because ADD outranked NEW.

Higher total return is not acceptable if caused by unstable concentration that damages winner robustness elsewhere.

### NEW_OPPORTUNITY_DAMAGE_ANALYSIS

Track whether lifecycle-aware ADD suppresses high-quality NEW:

- high-PIT NEW displaced by ADD;
- NEW rank/quality distribution before and after;
- missed diversification opportunities;
- NEW short-hold / early failure only as post-decision labels.

Alternative C must not improve ADD by starving diversification.

## Regime Attribution

Split validation by canonical PIT Market Context where sample permits:

- `BULL`
- `RANGE`
- `BEAR`
- `RECOVERY`
- `CORRECTION`
- any other canonical state materialized by the current Market Context authority.

Track by regime:

- capital ordering;
- ADD/NEW displacement;
- exposure;
- PnL;
- MDD;
- winner damage;
- NEW damage.

Do not create regime-specific priority rules in Alternative C. This is attribution only.

## Counterfactual Rules

Allowed:

- replay same-day ordering among opportunities actually available at that date;
- apply same-day cash, lot, cap, and Safety constraints;
- determine which candidate receives the next lot under the pre-defined order;
- freeze the counterfactual decision before applying outcomes.

Forbidden:

- substituting later-known winners;
- using future price/return/MFE/MAE;
- using final campaign outcome;
- using later-known regime;
- selecting thresholds from counterfactual PnL.

## Shadow Validation Design

Before mutating Strategy, Alternative C should run as non-mutating shadow.

Required shadow artifact:

```text
strategy/marginal_capital_value_shadow.json
```

Suggested fields:

```text
schema_version
business_date
producer
authority_type = MARGINAL_CAPITAL_VALUE_AUTHORITY_SHADOW
pit_status
future_information_used = false
candidate_units[]
canonical_shadow_order[]
actual_pc_order[]
actual_runtime_cash_batch_order[]
order_differences[]
expected_decision_impact
blocked_or_reviewed_items
lot_materialization_status
source_artifacts
source_hashes
```

Comparison metrics:

- shadow vs actual order delta;
- cases where shadow would remove accidental starvation;
- cases where shadow would protect NEW over weak ADD;
- order explanations missing/insufficient;
- lot materialization differences.

Acceptance criteria before mutation:

- no future leakage;
- order explainability complete;
- weak ADD not promoted by label;
- strong NEW protection demonstrated;
- B0 development cases reproduce no accidental processing-order authority;
- no SELL coupling in shadow output.

Duration/evidence requirement should be pre-declared by the operator before implementation and should include multiple dates/regimes where available.

## Implementation Validation Sequence

Pre-registered future sequence:

1. Focused contract/unit tests.
2. Non-mutating shadow order validation.
3. Short user-operated targeted Historical validation.
4. Compare ordering/funnel mechanics.
5. Winner damage check.
6. NEW damage check.
7. Capital/deployment check.
8. Risk/MDD check.
9. Longer user-operated clean Historical validation.
10. Untouched holdout confirmation where feasible.

Codex must not execute long runs.

## Stop / Rollback Conditions

Reject or rollback Alternative C if any occur:

- canonical quantity lineage regression;
- Safety hard-cap regression;
- normal Strategy cap changed;
- BUY/SELL independence regression;
- future leakage;
- Runtime invents priority;
- weak ADD receives priority because of label alone;
- high-quality NEW is systematically starved;
- concentration instability without explicit Safety/Strategy evidence;
- large increase in unexplained cash starvation;
- typed evidence insufficient to explain order;
- order cannot survive lot materialization;
- outcome-only improvement with structural failures.

Historical-return-only success must not override these failures.

## Alternative E Gate

Alternative E, controlled winner-amplification headroom above normal Strategy cap, must not proceed merely because:

- ADD count remains low;
- 94320 would have benefited;
- Alternative C improves return.

Required evidence before E design/implementation:

1. Strong PIT ADD opportunities remain systematically blocked by the normal cap after Alternative C.
2. The pattern exists across multiple symbols/periods where possible.
3. Winner continuation evidence is distinguishable from weak/late ADD.
4. Normal-cap blockage has material net opportunity using post-frozen evaluation labels.
5. Concentration/Safety risk can be bounded.
6. No simpler Alternative C-only solution explains the gap.

B3 selects no numeric winner cap.

## Anti-Overfit Rules

Strictly preserve:

- no future information;
- no future return;
- no campaign outcome as Strategy input;
- no MFE/MAE as Strategy input;
- no test PnL as Strategy input;
- no selected/bought outcome as feature;
- no threshold chosen because it maximizes current-run return;
- no 94320-specific rule;
- no regime-specific tuning from current outcomes.

Current outcomes are evaluation labels only.

## Final Answers

1. How can we determine without overfit whether Alternative C is worth implementing?

By validating authority, PIT ordering, order preservation, lot/cash mechanics, weak-ADD rejection, strong-NEW preservation, and damage analysis first, using B0/B1/B2 only as development evidence and pre-declared separate validation/holdout evidence for confirmation.

2. What must pass before implementation authorization?

Layer 1 architecture conformance, Layer 2 PIT ordering behavior, Layer 3 funnel/cash/lot mechanics, no future leakage, no Safety/cap/quantity/SELL regression, and non-mutating shadow evidence that accidental processing-order starvation is removed without hidden ADD_FIRST behavior.

3. Can Alternative C be validated by improved final return alone?

`NO`.

Final return is an evaluation label after the decision contract is frozen. It cannot select the ordering rule and cannot override structural regressions.

4. Is Alternative E part of the first validation candidate?

`NO`.

Alternative E requires a separate gate after Alternative C validation.
