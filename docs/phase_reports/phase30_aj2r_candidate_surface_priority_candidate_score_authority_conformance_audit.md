# Phase30-AJ2R - Candidate Surface Priority / Candidate Score Authority Conformance Audit

Task ID: `Phase30-AJ2R`

Boundary:

```text
READ_ONLY
NO_IMPLEMENTATION
NO_CANDIDATE_ORDERING_CHANGE
NO_THRESHOLD_CHANGE
NO_WEIGHTED_SCORE
NO_MODEL_RETRAINING
NO_LABEL_CHANGE
NO_CANDIDATE_TOP50_COUNT_CHANGE
NO_HISTORICAL_OUTCOME_FIT
NO_TARGET_RUN_MUTATION
```

Evidence:

```text
docs/phase_reports/phase30_aj2_candidate_top50_pit_quality_surface_repair_implementation_and_legacy_retirement.md
docs/phase_reports/phase30_aj1_candidate_ai_top50_market_pit_quality_surface_design_audit.md
docs/03_ai_design/candidate_ai_design.md
docs/03_ai_design/candidate_training_data_design.md
docs/03_ai_design/candidate_feature_catalog.md
docs/phase_reports/phase30_ai_selection_quality_opportunity_capture_repair_implementation_and_legacy_retirement.md
docs/02_architecture/strategy_intelligence_architecture_v1.md
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

Generated evidence:

```text
reports/phase_reports/phase30_aj2r_candidate_surface_priority_candidate_score_authority_conformance_audit.json
reports/phase_reports/phase30_aj2r/ordering_case_analysis.json
```

## Primary Judgment

```text
AJ1_EXPLICITLY_AUTHORIZES_LEXICOGRAPHIC_SURFACE_FIRST = NO
CANDIDATE_SURFACE_ROLE = HARD_ORDERING_TIER
CANDIDATE_SCORE_AUTHORITY_PRESERVED = PARTIAL
CANDIDATE_STAGE_OVERREACH = NO
AJ2_ORDERING_CONFORMS_TO_DESIGN = PARTIAL
AJ2_ORDERING_REPAIR_REQUIRED = NO
```

AJ2 correctly preserved Candidate model score semantics, did not retrain the
model, did not change labels, did not change Top50 count, and did not copy the
full downstream Phase30-AI comparator into Candidate selection.

However, the specific ordering:

```text
surface priority -> candidate_score descending -> code ascending
```

turns `candidate_pit_surface_state` into a hard lexicographic ordering tier.
AJ1 authorized a hybrid surface and weakening score-only dominance, but it did
not explicitly authorize that one surface-state step should dominate any size
of Candidate score difference.

Therefore the conformance result is `PARTIAL`, not clean `YES`.

## Candidate AI Authority Contract

Durable Candidate AI authority:

```text
Candidate AI = broad-market upward-momentum discovery authority
candidate_score = momentum_candidate_label model score
candidate_score != BUY probability
candidate_score != expected return
candidate_score != continuation quality
candidate_score != allocation authority
```

Candidate score should remain meaningful in the final Candidate surface because
it is the accepted model's momentum-discovery evidence. It should not be the
sole Top50 authority, but the design does not say it should become merely a
within-tier tie-breaker.

## AJ1 Option C Interpretation

AJ1 Option C explicitly requires:

- keep Candidate AI authority;
- preserve candidate score/rank;
- add Candidate-stage PIT quality surface;
- weaken score-only dominance;
- keep Top50 count fixed;
- do not create new AI;
- do not create a parallel Candidate path;
- do not copy the full downstream comparator into Candidate selection.

AJ1 does not explicitly state:

```text
Any STRONG beats any VALID regardless of candidate_score.
Any VALID beats any CAUTION regardless of candidate_score.
Surface tier is a hard ordering tier.
```

Thus:

```text
AJ1_EXPLICITLY_AUTHORIZES_LEXICOGRAPHIC_SURFACE_FIRST = NO
```

## AJ2 Current Ordering

Code inspection confirms:

```text
sort key =
(
  candidate_pit_surface_priority,
  -candidate_score,
  code
)
```

Surface priority:

| State | Priority |
|---|---:|
| `STRONG_CONTINUATION_SURFACE` | 0 |
| `VALID_MOMENTUM_SURFACE` | 1 |
| `CAUTION_MOMENTUM_SURFACE` | 2 |
| `INSUFFICIENT_SURFACE_EVIDENCE` | 3 |

Preserved:

- `candidate_rank` remains score-only rank;
- `score_only_candidate_rank` is materialized;
- `quality_aware_candidate_rank` is generated separately;
- `code` is final tie-breaker;
- insufficient evidence ranks last.

## Surface vs Score Authority Balance

Case analysis:

| Case | Current AJ2 Result | Judgment |
|---|---|---|
| `STRONG` + very low score vs `VALID` + very high score | `STRONG` always wins | `AMBIGUOUS` |
| `VALID` + low score vs `CAUTION` + extremely high score | `VALID` always wins | `AMBIGUOUS` |
| same surface state, different candidate score | higher score wins | `EXPECTED_BY_DESIGN` |

The issue is not that surface evidence is invalid. The issue is that AJ2 makes
surface tier absolutely dominant across tiers, while AJ1 only clearly
authorizes a hybrid quality-aware Top50 and modification of score dominance.

## Candidate Surface Role

Current implementation role:

```text
CANDIDATE_SURFACE_ROLE = HARD_ORDERING_TIER
```

Most conservative reading of AJ1:

```text
Candidate PIT surface should be more than SUPPORTING_METADATA,
but AJ1 does not prove it must be a HARD_ORDERING_TIER.
```

A clearer contract is needed to decide whether Candidate surface should remain
hard lexicographic or become a semantic hybrid where Candidate score and
surface evidence both retain cross-tier authority.

## Downstream Responsibility Boundary

```text
CANDIDATE_STAGE_OVERREACH = NO
```

AJ2 does not copy the full Strategy Intelligence / Phase30-AI comparator.
Candidate surface uses Candidate-stage PIT evidence only, and downstream
responsibilities remain intact:

- CQ remains downstream Strategy Intelligence evidence;
- Relative Strength remains downstream / partial upstream only where safe;
- Downside Risk remains downstream rollup;
- Entry Admission remains downstream;
- Phase30-AI comparator remains Top50-internal downstream quality comparison;
- PC remains allocation authority;
- PS remains quantity authority;
- Runtime remains pure mapper.

## Semantic Ordering vs Weighted Ordering

Lexicographic:

- simple and explainable;
- PIT-safe;
- avoids opaque Historical-fit weights;
- but can underweight Candidate AI score across surface tiers.

Monotonic hybrid:

- may better preserve both Candidate score and surface evidence;
- requires explicit design contract;
- should avoid opaque numeric fitting.

Weighted score:

- not recommended in AJ2R;
- risks opaque semantics and Historical outcome fitting.

## Design Conformance

```text
AJ2_ORDERING_CONFORMS_TO_DESIGN = PARTIAL
AJ2_ORDERING_REPAIR_REQUIRED = NO
```

No implementation repair is authorized by AJ2R. The right next step is to
clarify the ordering contract before changing code.

## Production Integrity

```text
CANDIDATE_MODEL_PRESERVED = YES
CANDIDATE_ACCEPTED_GENERATION_PRESERVED = YES
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
ONE_PRODUCTION_CANDIDATE_PATH = YES
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED_BY_PHASE30_AJ2R
```

## Recommended Next Task

```text
Phase30-AJ2R2 - Candidate Surface / Score Hybrid Ordering Contract Design
```
