# Phase30-AJ3C - Fresh 5BD Candidate Surface / Top50 / Production Action Conformance Validation

Task ID: `Phase30-AJ3C`

Boundary:

```text
READ_ONLY_VALIDATION
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AJ3C
NO_TARGET_RUN_MUTATION
NO_REPLAY_OR_RESUME
NO_FRESH_RUN_EXECUTED_BY_CODEX
NO_THRESHOLD_TUNING
NO_MODEL_OR_ACCEPTED_GENERATION_CHANGE
NO_HISTORICAL_PNL_PARAMETER_SELECTION
```

Compared runs:

```text
BEFORE = runtime-test-historical-extended-smoke-20260816T061732506648Z
AFTER  = runtime-test-historical-extended-smoke-20260816T120536241332Z
WINDOW = 2022-08-10, 2022-08-12, 2022-08-15, 2022-08-16, 2022-08-17
```

The AFTER window is taken from `run_state.json.completed_business_days`.

## Primary Judgment

```text
AJ3B_LIQUIDITY_PROPAGATION_REAL_RUN = PASS
ALL_MARKET_SURFACE_INSUFFICIENT_RECURRENCE = NO
SEMANTIC_HYBRID_ACTION_EFFECTIVE = YES
HYBRID_TOP50_MEMBERSHIP_CHANGED_DAYS = 5 / 5
BEFORE_AFTER_TOP50_CHANGED = YES
TOP50_CHANGE_EXPLAINABLE_BY_DECISION_TIME_PIT = YES
PORTFOLIO_ACTION_CHANGE_EXPLAINABLE = YES
CANDIDATE_PIT_QUALITY_DIRECTION = IMPROVED
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
LONG_HORIZON_VALIDATION_READY = YES
```

Phase30-AJ3B restored real-run liquidity evidence propagation. Phase30-AJ2R3
semantic hybrid ordering became action-effective in every audited business day.
The Top50 changes are explained by decision-time PIT surface and semantic hybrid
evidence, not by future return or performance tuning.

## AJ3B Liquidity Real-Run Validation

AFTER real run:

| Date | Market rows | Liquidity present | Liquidity missing | Non-insufficient market rows | Top50 non-insufficient |
|---|---:|---:|---:|---:|---:|
| 2022-08-10 | 3260 | 3260 | 0 | 3260 | 50 |
| 2022-08-12 | 3367 | 3367 | 0 | 3367 | 50 |
| 2022-08-15 | 3424 | 3424 | 0 | 3424 | 50 |
| 2022-08-16 | 3454 | 3454 | 0 | 3454 | 50 |
| 2022-08-17 | 3482 | 3482 | 0 | 3482 | 50 |

Runtime lineage confirms:

```text
source_field = liquidity_avg_volume_20d
source_artifact = .runtime/operations/feature_artifacts/<date>/candidate_features.parquet
canonical_liquidity_authority_reused = true
duplicate_liquidity_authority_created = false
fallback_liquidity_heuristic_used = false
future_row_used = false
```

Top50 row value and `candidate_pit_quality_surface.raw_pit_evidence` matched
for all audited Top50 rows.

## Candidate Surface Distribution

Market-wide `INSUFFICIENT_SURFACE_EVIDENCE` recurrence did not occur.

Top50 surface distribution:

| Date | Strong | Valid | Caution | Insufficient |
|---|---:|---:|---:|---:|
| 2022-08-10 | 10 | 0 | 40 | 0 |
| 2022-08-12 | 9 | 1 | 40 | 0 |
| 2022-08-15 | 7 | 1 | 42 | 0 |
| 2022-08-16 | 8 | 1 | 41 | 0 |
| 2022-08-17 | 6 | 1 | 43 | 0 |

Top50 semantic hybrid distribution was dominated by
`CONFLICT_RESOLUTION_HIGH_DISCOVERY_OR_STRONG_SURFACE`, with
`CONFIRMED_DISCOVERY_AND_SURFACE` present on 2022-08-12 through 2022-08-17.

## Score-Only vs Hybrid Top50

| Date | Overlap | Added | Removed | Membership changed |
|---|---:|---:|---:|---|
| 2022-08-10 | 40 | 10 | 10 | YES |
| 2022-08-12 | 41 | 9 | 9 | YES |
| 2022-08-15 | 43 | 7 | 7 | YES |
| 2022-08-16 | 42 | 8 | 8 | YES |
| 2022-08-17 | 45 | 5 | 5 | YES |

```text
SEMANTIC_HYBRID_ACTION_EFFECTIVE = YES
HYBRID_TOP50_MEMBERSHIP_CHANGED_DAYS = 5 / 5
```

## Before vs After Top50

The BEFORE run does not retain copied `candidate_decisions.json` bodies in the
run snapshot. As in AJ3A, BEFORE comparison therefore uses the downstream
consumed `buy_quality_decisions.json` order.

| Date | BEFORE/AFTER consumed overlap | Added | Removed | Changed |
|---|---:|---:|---:|---|
| 2022-08-10 | 40 | 10 | 10 | YES |
| 2022-08-12 | 41 | 9 | 9 | YES |
| 2022-08-15 | 43 | 7 | 7 | YES |
| 2022-08-16 | 42 | 8 | 8 | YES |
| 2022-08-17 | 45 | 5 | 5 | YES |

```text
BEFORE_AFTER_TOP50_CHANGED = YES
```

## Added / Removed Symbol PIT Evidence

All hybrid-added symbols include decision-time PIT evidence in the AFTER
Candidate artifact:

```text
candidate_score
score_only_candidate_rank
score_evidence_class
candidate_pit_surface_state
semantic_hybrid_class
quality_aware_candidate_rank
5D / 20D / 60D return structure
MA structure
acceleration / deceleration
volume momentum
liquidity
volatility
```

No future return was used. Removed symbols are not fully materialized in the
final Top50 body because the artifact stores final Top50 rows only; their
removal is evidenced by `score_only_top50_symbol_order` and
`quality_aware_removed_symbols`.

Detailed per-symbol PIT evidence is in:

```text
reports/phase_reports/phase30_aj3c/added_removed_symbol_pit_evidence.json
```

## Production Action Propagation

Hybrid-added symbols reached:

```text
Candidate -> Opportunity -> Buy Quality / Strategy -> PC competition
```

Distribution for 39 hybrid-added symbol-date rows:

```text
PC_COMPETITION_REACHED = 39
PC_POSITIVE = 0
PS_POSITIVE = 0
RUNTIME_BUY = 0
BUY_FILL = 0
```

This is expected for the observed added set: the semantic hybrid repair changed
Top50 membership, but the added names generally entered at lower opportunity
ranks and were rejected or not allocated by downstream BQ/PC/PS. This is
action-effective at Candidate/Production input level without forcing BUYs.

## Portfolio Difference Attribution

5BD quantity comparison reconstructed from run-scoped fills:

| Symbol | BEFORE qty | AFTER qty | Difference | Attribution |
|---|---:|---:|---:|---|
| 23700 | 600 | 700 | +100 | Same BQ rank/action; day1 PC weight 0.047619 -> 0.052632, PS 600 -> 700 |
| 45710 | 0 | 0 | 0 | Timing changed: BEFORE buy day1/sell day2; AFTER buy day3/sell day4 |
| 89180 | 500 | 500 | 0 | Larger initial buy offset by larger staged sells |
| 93180 | 0 | 0 | 0 | Larger initial buy offset by larger staged sells/exit |

Primary portfolio difference after 5BD is 23700 quantity `600 -> 700`.
This is best classified as downstream recomputation / lot-aware capital
conversion under changed Top50/BQ population context, not as a direct
hybrid-added-symbol BUY fill.

```text
PORTFOLIO_ACTION_CHANGE_EXPLAINABLE = YES
```

## Candidate PIT Quality Direction

```text
CANDIDATE_PIT_QUALITY_DIRECTION = IMPROVED
```

Compared with AJ3A's all-insufficient Candidate PIT surface failure, AJ3C has:

```text
market-wide liquidity present = all audited rows
Top50 insufficient surface = 0 / 250
hybrid membership changed = 5 / 5 days
decision-time surface distributions materialized
```

This is PIT quality conformance, not performance validation.

## Cut-Line Observation

```text
CUT_LINE_51_75_OBSERVABLE = NO
HIGH_QUALITY_CANDIDATES_BELOW_TOP50 = not observed
```

The runtime Candidate artifact materializes final Top50 rows only. Ranks 51-75
are not available in the run artifact, so no Top50 capacity change is proposed.

## Production Integrity

```text
CANDIDATE_MODEL_PRESERVED = YES
CANDIDATE_ACCEPTED_GENERATION_PRESERVED = YES
CANDIDATE_TRAINING_TARGET_CHANGED = NO
SEMANTIC_HYBRID_ORDERING_PRESERVED = YES
TOP50_COUNT = 50
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
ONE_PRODUCTION_CANDIDATE_PATH = YES
```

## Runtime / Authority Defects

```text
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
```

The AFTER final summary has a non-blocking
`strategy_shadow_review_required_non_blocking` acceptance review. It does not
block runtime judgment, accounting state, Candidate propagation, or action
conformance in this validation.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
5BD_RESULT_USED_FOR_PARAMETER_SELECTION = FALSE
100BD_RESULT_USED_FOR_PARAMETER_SELECTION = FALSE
200BD_RESULT_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Performance Record

Recorded only:

```text
AFTER as_of = 2022-08-17
Equity = 994,290
Return = -0.5710%
Cash = 687,020
Market Value = 307,270
Exposure = 30.9035%
```

Performance was not used for parameter selection.

## Long-Horizon Gate

```text
LONG_HORIZON_VALIDATION_READY = YES
```

Recommended next task:

```text
User-operated fresh 200BD validation
```
