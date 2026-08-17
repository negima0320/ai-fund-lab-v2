# Phase30-AJ3A - Fresh 3BD Candidate Top50 / Production Action Effect Audit

Task ID: `Phase30-AJ3A`

Boundary:

```text
READ_ONLY
NO_IMPLEMENTATION
NO_TARGET_RUN_MUTATION
NO_RUN_STOP
NO_RESUME_OR_REPLAY
NO_THRESHOLD_TUNING
NO_CANDIDATE_COUNT_CHANGE
NO_MODEL_RETRAINING
NO_ORDERING_CHANGE
NO_HISTORICAL_PNL_PARAMETER_SELECTION
NO_FUTURE_DATE_DATA_USE
```

Compared runs:

```text
BEFORE = runtime-test-historical-extended-smoke-20260816T061732506648Z
AFTER  = runtime-test-historical-extended-smoke-20260816T114233352959Z
WINDOW = 2022-08-10, 2022-08-12, 2022-08-15
```

Generated evidence:

```text
reports/phase_reports/phase30_aj3a_fresh_3bd_candidate_top50_production_action_effect_audit.json
reports/phase_reports/phase30_aj3a/daily_candidate_diff.json
reports/phase_reports/phase30_aj3a/added_removed_symbol_lineage.json
reports/phase_reports/phase30_aj3a/downstream_propagation.json
reports/phase_reports/phase30_aj3a/cut_line_observation.json
```

## Primary Judgment

```text
AJ2R3_RUNTIME_MATERIALIZATION = PASS
HYBRID_ORDERING_ACTION_EFFECTIVE = NO
HYBRID_TOP50_MEMBERSHIP_CHANGED_DAYS = 0 / 3
BEFORE_AFTER_CANDIDATE_TOP50_CHANGED = NO
TOP50_CHANGE_EXPLAINABLE_BY_PIT_EVIDENCE = YES
CANDIDATE_PIT_QUALITY_DIRECTION = UNCHANGED
PORTFOLIO_EQUALITY_ROOT_CAUSE = NO_CANDIDATE_MEMBERSHIP_CHANGE
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
DEFECT_CLASSIFICATION = CANDIDATE_PIT_SURFACE_LIQUIDITY_EVIDENCE_PROPAGATION_GAP
```

Phase30-AJ2R3 semantic hybrid fields are present at runtime, but the ordering
was not action-effective in the first 3BD. The direct reason is that every
Candidate PIT surface row in the audited window is
`INSUFFICIENT_SURFACE_EVIDENCE` because `liquidity_avg_volume_20d` is missing.

This means the implementation contract is materialized, but the data surface
cannot yet exert the intended hybrid ordering effect.

## AJ2R3 Runtime Materialization

AFTER Candidate artifacts exist for all audited days in:

```text
.runtime/runtime_state/buy_ai/<date>/candidate_decisions.json
```

Their sha256 hashes match the AFTER run source manifests:

| Date | AFTER Candidate hash match | Rows | Required AJ2R3 fields |
|---|---:|---:|---|
| 2022-08-10 | YES | 50 | PRESENT |
| 2022-08-12 | YES | 50 | PRESENT |
| 2022-08-15 | YES | 50 | PRESENT |

Materialized per row:

```text
score_evidence_class
candidate_pit_surface_state
semantic_hybrid_class
quality_aware_candidate_rank
```

Materialized run-level evidence:

```text
final_top50_symbol_order
score_only_top50_symbol_order
quality_aware_added_symbols
quality_aware_removed_symbols
semantic_hybrid_class_distribution
score_evidence_class_distribution
```

## Score-Only vs Hybrid Top50

AFTER run:

| Date | Overlap | Ordering diff | Added | Removed | Membership changed |
|---|---:|---:|---:|---:|---|
| 2022-08-10 | 50 | 0 | 0 | 0 | NO |
| 2022-08-12 | 50 | 0 | 0 | 0 | NO |
| 2022-08-15 | 50 | 0 | 0 | 0 | NO |

```text
HYBRID_TOP50_MEMBERSHIP_CHANGED_DAYS = 0 / 3
HYBRID_ORDERING_ACTION_EFFECTIVE = NO
```

## Before vs After Top50

The BEFORE Candidate payload body is not present in the run snapshot; the
BEFORE Candidate sha256 is preserved in source manifests. The downstream
consumed Top50 set/order is preserved in `buy_quality_decisions.json`.

Using the consumed Top50 as the available run-internal comparison:

| Date | BEFORE vs AFTER consumed Top50 overlap | Ordering diff | Added | Removed |
|---|---:|---:|---:|---:|
| 2022-08-10 | 50 | 0 | 0 | 0 |
| 2022-08-12 | 50 | 0 | 0 | 0 |
| 2022-08-15 | 50 | 0 | 0 | 0 |

```text
BEFORE_AFTER_CANDIDATE_TOP50_CHANGED = NO
```

Candidate artifact hashes changed, but the action-consumed Top50 did not. The
hash change is consistent with AJ2R3 schema/materialization changes.

## Semantic Hybrid Distribution

AFTER Top50:

| Date | CONFIRMED | CONFLICT | VALID / INCOMPLETE | LOW CONVICTION | INSUFFICIENT / WEAK |
|---|---:|---:|---:|---:|---:|
| 2022-08-10 | 0 | 0 | 40 | 0 | 10 |
| 2022-08-12 | 0 | 0 | 41 | 0 | 9 |
| 2022-08-15 | 0 | 0 | 43 | 0 | 7 |

Score evidence class distribution:

| Date | STRONG_DISCOVERY_SCORE | MODERATE_DISCOVERY_SCORE | WEAK_DISCOVERY_SCORE |
|---|---:|---:|---:|
| 2022-08-10 | 40 | 10 | 0 |
| 2022-08-12 | 41 | 9 | 0 |
| 2022-08-15 | 43 | 7 | 0 |

Surface distribution:

| Date | INSUFFICIENT_SURFACE_EVIDENCE |
|---|---:|
| 2022-08-10 | 50 |
| 2022-08-12 | 50 |
| 2022-08-15 | 50 |

Market-wide Candidate surface distribution was also entirely insufficient:

| Date | Market population insufficient count |
|---|---:|
| 2022-08-10 | 3260 |
| 2022-08-12 | 3367 |
| 2022-08-15 | 3424 |

Observed missing input:

```text
liquidity_avg_volume_20d
```

## Added / Removed Symbol Evidence

There were no symbols added to or removed from Top50 by hybrid ordering:

```text
quality_aware_added_symbols = []
quality_aware_removed_symbols = []
```

Therefore:

```text
TOP50_CHANGE_EXPLAINABLE_BY_PIT_EVIDENCE = YES
```

The lack of change is explained by decision-time evidence: all rows have
insufficient Candidate PIT surface because required liquidity evidence is
missing. No future return, PnL, or later winner/loser result was used.

## Downstream Propagation

Since there were no hybrid-added symbols, no symbol-specific propagation chain
exists.

AFTER daily downstream row counts:

| Date | Opportunity | SI / Buy Quality | PC | PS | Runtime plans | Fills |
|---|---:|---:|---:|---:|---:|---:|
| 2022-08-10 | 50 | 50 | 50 | 50 | 21 | 9 |
| 2022-08-12 | 50 | 50 | 50 | 50 | 30 | 7 |
| 2022-08-15 | 50 | 50 | 50 | 50 | 21 | 6 |

All consumed Top50 memberships matched BEFORE, so the downstream stack
reconverged immediately at Candidate membership.

## Portfolio Equality Root Cause

```text
PORTFOLIO_EQUALITY_ROOT_CAUSE = NO_CANDIDATE_MEMBERSHIP_CHANGE
```

Runtime plan symbol sets and execution fill symbol sets matched between BEFORE
and AFTER for all audited days. Fill ordering differed in artifact order only,
not in economic symbol / side / quantity content.

## Candidate PIT Quality Direction

```text
CANDIDATE_PIT_QUALITY_DIRECTION = UNCHANGED
```

Reason:

- Candidate membership did not change.
- Hybrid ordering did not alter rank or membership.
- Healthy proxy capture did not improve.
- All Top50 rows were `INSUFFICIENT_SURFACE_EVIDENCE`.

This is not a performance judgment. Equity, PnL, future prices, later campaign
outcomes, and 200BD intermediate performance were not used.

## Optional Cut-Line Observation

Available:

```text
final Top50 rank 41-50
```

Unavailable in current Candidate artifact:

```text
rank 51-60
rank 61-75
full pre-cut row evidence
```

Reason: Candidate artifact retains final Top50 rows plus score-only/final order
evidence, but not the full pre-cut population rows.

## Production Integrity

```text
CANDIDATE_MODEL_PRESERVED = YES
CANDIDATE_ACCEPTED_GENERATION_PRESERVED = YES
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
ONE_PRODUCTION_CANDIDATE_PATH = YES
```

No Candidate model retraining, label change, accepted-generation change,
Top50 count change, weighted hybrid score, parallel Candidate path, or Runtime
authority change was observed or performed.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
200BD_INTERMEDIATE_PERFORMANCE_USED_FOR_PARAMETER_SELECTION = FALSE
```

## 200BD Run Decision

```text
200BD_RUN_REVIEW_REQUIRED
```

This is not a contamination quarantine. It is a validation-quality review:
AJ2R3 cannot be judged action-effective while the Candidate PIT surface is
globally insufficient due to missing liquidity evidence.

## Recommended Next Task

```text
Phase30-AJ3B - Candidate PIT Surface Liquidity Evidence Propagation Repair
```

Scope should be read/repair focused on why `liquidity_avg_volume_20d` is absent
from Candidate surface evidence despite Candidate liquidity features existing
in the durable Candidate AI feature contract. It must not tune thresholds,
change Top50 count, retrain the Candidate model, use 200BD performance, or
alter Strategy authority.

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AJ3A
```
