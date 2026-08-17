# Phase30-AJ2R2 - Candidate Surface / Score Hybrid Ordering Contract Design

Task ID: `Phase30-AJ2R2`

Boundary:

```text
DESIGN_ONLY
NO_IMPLEMENTATION
NO_PERFORMANCE_COMPARISON_SELECTION
NO_HISTORICAL_PNL_USE
NO_FUTURE_RETURN_USE
NO_WEIGHTED_SCORE_FITTING
NO_THRESHOLD_OPTIMIZATION
NO_MODEL_RETRAINING
NO_LABEL_CHANGE
NO_TOP50_COUNT_CHANGE
NO_NEW_AI
NO_PARALLEL_CANDIDATE_PATH
NO_RUNTIME_AUTHORITY_CHANGE
```

Evidence:

```text
docs/phase_reports/phase30_aj2r_candidate_surface_priority_candidate_score_authority_conformance_audit.md
docs/phase_reports/phase30_aj2_candidate_top50_pit_quality_surface_repair_implementation_and_legacy_retirement.md
docs/phase_reports/phase30_aj1_candidate_ai_top50_market_pit_quality_surface_design_audit.md
docs/03_ai_design/candidate_ai_design.md
docs/03_ai_design/candidate_training_data_design.md
docs/03_ai_design/candidate_feature_catalog.md
docs/02_architecture/strategy_intelligence_architecture_v1.md
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

Generated evidence:

```text
reports/phase_reports/phase30_aj2r2_candidate_surface_score_hybrid_ordering_contract_design.json
reports/phase_reports/phase30_aj2r2/ordering_contract_cases.json
```

## Primary Judgment

```text
PHASE30_AJ2R2_HYBRID_ORDERING_CONTRACT = COMPLETE
CANDIDATE_SURFACE_ROLE = SEMANTIC_HYBRID_AUTHORITY
CANDIDATE_SCORE_ROLE = CO_EQUAL_HYBRID_EVIDENCE
RECOMMENDED_ORDERING_CONTRACT =
SEMANTIC_HYBRID_ELIGIBILITY_BANDS_WITH_CANDIDATE_SCORE_WITHIN_CLASS_AUTHORITY
HARD_LEXICOGRAPHIC_SURFACE_FIRST_JUSTIFIED = NO
OPAQUE_WEIGHTED_SCORE_REQUIRED = NO
MODEL_RETRAINING_REQUIRED = NO
TOP50_COUNT_CHANGE_REQUIRED = NO
AJ2_IMPLEMENTATION_CHANGE_REQUIRED = YES
AJ3_VALIDATION_READY = NO
```

AJ2R2 resolves the AJ2R ambiguity by selecting a semantic hybrid contract.
Candidate PIT surface must be action-effective, but not a hard tier that
unconditionally dominates any Candidate score gap.

## Authority Contracts

### Candidate AI

```text
Candidate AI = broad-market upward-momentum discovery authority
candidate_score = momentum_candidate_label model score
```

Candidate score is not:

- BUY probability;
- expected return;
- continuation quality;
- allocation authority.

It is still formal accepted-model momentum discovery evidence. Therefore it
must not be reduced to a meaningless tie-breaker.

### Candidate PIT Surface

Candidate PIT Surface expresses:

```text
current momentum candidate surfacing quality
```

It is based on decision-time evidence such as:

- current trend structure;
- acceleration / deceleration;
- participation;
- volatility;
- liquidity.

It is not BUY authority and not the downstream Strategy Intelligence
comparator.

### Downstream

Preserved:

```text
Phase30-AI / SI = CQ, RS, Downside Risk, Entry Admission, richer continuation interpretation
PC = allocation authority
PS = quantity authority
Runtime = pure mapper
```

## Core Design Answer

When Candidate score and Candidate PIT surface conflict, neither side should
unconditionally dominate across all cases.

Rejected:

```text
surface always beats any score gap
candidate_score always beats any surface gap
opaque weighted hybrid_score
```

Selected:

```text
semantic hybrid eligibility bands
```

The contract combines Candidate score evidence class with PIT surface state.
Within a semantic class, `candidate_score desc` remains the primary ordering
evidence.

## Ordering Contract Families

| Option | Judgment | Reason |
|---|---|---|
| Hard lexicographic surface first | Rejected | Makes surface a hard ordering tier and can underweight Candidate AI authority. |
| Score first with surface adjustment | Rejected | Risks score-only dominance recurrence and weakens AJ1 repair goal. |
| Semantic hybrid eligibility bands | Selected | Preserves both Candidate AI score and PIT surface without opaque weights. |
| Cross-tier bounded override | Incorporated | Surface may override only through semantic classes, not unlimited hard tiering. |

## Candidate Surface Role

```text
CANDIDATE_SURFACE_ROLE = SEMANTIC_HYBRID_AUTHORITY
```

Why:

- More than supporting metadata: it must influence Top50 membership.
- More than veto: `CAUTION_MOMENTUM_SURFACE` is not reject.
- Less than hard ordering tier: surface state alone must not defeat any
  Candidate score gap.
- Not BUY authority: downstream SI / PC / PS responsibilities remain intact.

## Candidate Score Role

```text
CANDIDATE_SCORE_ROLE = CO_EQUAL_HYBRID_EVIDENCE
```

Candidate score remains the accepted model's momentum discovery evidence. It
should determine ordering within semantic classes and help resolve conflict
classes. It is not reduced to within-surface tie-break only.

## Semantic Hybrid Contract

Score evidence classes:

| Class | Meaning |
|---|---|
| `STRONG_DISCOVERY_SCORE` | Existing high Candidate model evidence, such as `high_candidate_score` / accepted-generation equivalent. |
| `MODERATE_DISCOVERY_SCORE` | Finite Candidate model momentum evidence below strong, still usable as discovery evidence. |
| `WEAK_DISCOVERY_SCORE` | Weak, missing, non-finite, or otherwise insufficient Candidate model discovery evidence. |

Surface states:

| State | Guarantees | Does Not Guarantee |
|---|---|---|
| `STRONG_CONTINUATION_SURFACE` | Current PIT structure is strongly suitable for downstream evaluation. | BUY-worthy, expected edge, PC allocation. |
| `VALID_MOMENTUM_SURFACE` | Current PIT structure is acceptable for downstream evaluation. | BUY-worthy, low downside, final continuation quality. |
| `CAUTION_MOMENTUM_SURFACE` | Momentum candidate remains reviewable but has current caution. | Reject, sell, Safety block. |
| `INSUFFICIENT_SURFACE_EVIDENCE` | Surface evidence is incomplete. | Safety, high quality, score-only automatic approval. |

Recommended semantic class order:

| Order | Class | Members |
|---:|---|---|
| 1 | `CONFIRMED_DISCOVERY_AND_SURFACE` | strong score + strong/valid surface |
| 2 | `CONFLICT_RESOLUTION_HIGH_DISCOVERY_OR_STRONG_SURFACE` | strong score + caution surface; moderate score + strong surface |
| 3 | `VALID_BUT_INCOMPLETE_CONFIRMATION` | moderate score + valid surface; strong score + insufficient surface |
| 4 | `LOW_CONVICTION_OR_SURFACE_ONLY_CHALLENGER` | moderate score + caution surface; weak score + strong/valid surface |
| 5 | `INSUFFICIENT_OR_WEAK` | moderate score + insufficient surface; weak score + caution/insufficient surface |

Within each class:

```text
candidate_score descending
then surface-state preference
then code ascending
```

This avoids both failure modes:

- weak Candidate discovery cannot become high-priority solely because surface
  looks strong;
- high Candidate score with caution cannot permanently suppress all healthier
  current PIT structures.

## Case Judgments

| Case | Contract Judgment |
|---|---|
| very high score + CAUTION vs moderate score + STRONG | Hybrid required; neither unconditional score nor surface victory. |
| extremely high score + CAUTION vs low score + VALID | Candidate score must retain cross-surface authority; low score cannot win by surface alone. |
| high score + STRONG | Highest priority class; still not BUY authority. |
| low score + STRONG | Surface-only challenger; do not promote by surface alone. |

## No Opaque Weighted Score

```text
OPAQUE_WEIGHTED_SCORE_REQUIRED = NO
```

Do not implement:

```text
hybrid_score = a * candidate_score + b * acceleration + c * volume ...
```

No coefficient may be selected from Historical return, 100BD result, 200BD
result, later winners/losers, campaign outcome, or Paper Ledger evidence.

## Insufficient Evidence

`INSUFFICIENT_SURFACE_EVIDENCE` means:

- missing evidence is not safety;
- missing evidence is not high quality;
- missing evidence is not a hard reject by itself;
- score-only fallback must not be unconditionally restored;
- strong Candidate score with insufficient surface remains a valid but
  incomplete confirmation class, not a top confirmed class.

## Philosophy Conformance

The selected contract matches the current Strategy philosophy:

```text
Find momentum candidates,
then preferentially surface names whose current PIT structure still supports
sustainable continuation for downstream evaluation.
```

Candidate stage still does not decide BUY, allocation, quantity, or Safety.

## Preservation Requirements

```text
CANDIDATE_MODEL_PRESERVED = YES
CANDIDATE_ACCEPTED_GENERATION_PRESERVED = YES
CANDIDATE_TRAINING_TARGET_CHANGED = NO
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
ONE_PRODUCTION_CANDIDATE_PATH = YES
TOP50_COUNT = 50
```

## Leakage / Evidence Integrity

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
100BD_RESULT_USED_FOR_ORDERING_DESIGN = FALSE
200BD_RESULT_USED_FOR_ORDERING_DESIGN = FALSE
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AJ2R2
```

## Recommended Next Task

```text
Phase30-AJ2R3 - Candidate Hybrid Ordering Contract Implementation Repair
```
