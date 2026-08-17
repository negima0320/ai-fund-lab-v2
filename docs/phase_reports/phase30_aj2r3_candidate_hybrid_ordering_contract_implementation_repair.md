# Phase30-AJ2R3 - Candidate Hybrid Ordering Contract Implementation Repair

Task ID: `Phase30-AJ2R3`

## Primary Judgment

```text
SEMANTIC_HYBRID_ORDERING_IMPLEMENTED = YES
CANDIDATE_SCORE_ROLE = CO_EQUAL_HYBRID_EVIDENCE
CANDIDATE_SURFACE_ROLE = SEMANTIC_HYBRID_AUTHORITY
HARD_LEXICOGRAPHIC_SURFACE_FIRST_RETIRED = YES
SCORE_ONLY_DOMINANCE_RETIRED = YES
CANDIDATE_MODEL_PRESERVED = YES
CANDIDATE_ACCEPTED_GENERATION_PRESERVED = YES
TOP50_COUNT = 50
ONE_PRODUCTION_CANDIDATE_PATH = YES
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
```

Phase30-AJ2R3 implements the Phase30-AJ2R2 ordering contract in the existing
Production-common Candidate producer. The repair replaces AJ2's hard
surface-first final ordering with semantic hybrid eligibility bands while
preserving Candidate model score/rank as formal momentum discovery evidence.

No Candidate model, label, accepted generation, Top50 count, Runtime authority,
threshold, minimum exposure, forced investment, or downstream authority was
changed.

## Semantic Hybrid Ordering

Implemented contract:

```text
SEMANTIC_HYBRID_ELIGIBILITY_BANDS_WITH_CANDIDATE_SCORE_WITHIN_CLASS_AUTHORITY
```

Production ordering is now:

```text
semantic_hybrid_class priority
then candidate_score descending
then surface-state preference
then code ascending
```

This retires both failure modes:

- `STRONG_CONTINUATION_SURFACE` alone no longer makes a weak score outrank all
  higher discovery evidence.
- `candidate_score` alone no longer restores score-only Top50 dominance,
  because the semantic hybrid class is the first ordering authority.

## Candidate Score Authority

Preserved:

```text
Candidate AI = broad-market upward-momentum discovery authority
candidate_score = momentum_candidate_label accepted model score
candidate_rank = score-only model rank
```

Materialized:

```text
score_evidence_class =
  STRONG_DISCOVERY_SCORE
  MODERATE_DISCOVERY_SCORE
  WEAK_DISCOVERY_SCORE
```

`STRONG_DISCOVERY_SCORE` reuses existing Candidate semantics:
`high_candidate_score` / accepted-generation equivalent. The implementation
does not fit or optimize a new Historical-return threshold.

## Candidate Surface Authority

Preserved AJ2 surface states:

```text
STRONG_CONTINUATION_SURFACE
VALID_MOMENTUM_SURFACE
CAUTION_MOMENTUM_SURFACE
INSUFFICIENT_SURFACE_EVIDENCE
```

Candidate PIT surface remains current momentum surfacing quality. It is not BUY
authority, allocation authority, Safety authority, or Expected Edge authority.

## Eligibility Bands

Implemented semantic classes:

```text
1. CONFIRMED_DISCOVERY_AND_SURFACE
   strong score + strong/valid surface

2. CONFLICT_RESOLUTION_HIGH_DISCOVERY_OR_STRONG_SURFACE
   strong score + caution surface
   moderate score + strong surface

3. VALID_BUT_INCOMPLETE_CONFIRMATION
   moderate score + valid surface
   strong score + insufficient surface

4. LOW_CONVICTION_OR_SURFACE_ONLY_CHALLENGER
   moderate score + caution surface
   weak score + strong/valid surface

5. INSUFFICIENT_OR_WEAK
   moderate score + insufficient surface
   weak score + caution/insufficient surface
```

Per-symbol evidence now includes:

```text
score_only_candidate_rank
score_evidence_class
candidate_pit_surface_state
semantic_hybrid_class
semantic_hybrid_class_reason
quality_aware_candidate_rank
PIT / leakage metadata
```

Run-level evidence now includes:

```text
score_evidence_class_distribution
semantic_hybrid_class_distribution
top50_score_evidence_class_distribution
top50_semantic_hybrid_class_distribution
candidate_pit_surface_distribution
top50_surface_distribution
final_top50_symbol_order
score_only_top50_symbol_order
quality_aware_added_symbols
quality_aware_removed_symbols
healthy_proxy_capture_ratio
```

## Legacy Retirement

```text
HARD_LEXICOGRAPHIC_SURFACE_FIRST_REFERENCE_COUNT = 0
OBSOLETE_SCORE_ONLY_TOP50_PATH_REFERENCE_COUNT = 0
PARALLEL_CANDIDATE_PATH_REFERENCE_COUNT = 0
DUPLICATE_HYBRID_ORDERING_REFERENCE_COUNT = 0
ONE_PRODUCTION_CANDIDATE_PATH = YES
```

The remaining `score_only_top50_symbol_order` evidence is audit-only
before/after coverage evidence. It is not the final production authority.

The remaining `candidate_pit_surface_priority` metadata is used only as the
surface-state preference after semantic class and candidate score within class.
It is not a surface-first final ordering path.

## Candidate Model Preservation

```text
CANDIDATE_MODEL_RETRAINED = NO
CANDIDATE_TRAINING_TARGET_CHANGED = NO
CANDIDATE_ACCEPTED_GENERATION_CHANGED = NO
WEIGHTED_HYBRID_SCORE_CREATED = NO
TOP50_COUNT_CHANGED = NO
```

## Downstream Preservation

```text
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_W_ONE_LOT_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
PHASE30_AC_CAMPAIGN_LIFECYCLE_PRESERVED = YES
PHASE30_AD1_BOOTSTRAP_PRESERVED = YES
SELL_REDUCE_EXIT_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
SAFETY_HARD_GUARDRAILS_PRESERVED = YES
```

## Leakage / Evidence Integrity

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
100BD_RESULT_USED_FOR_ORDERING_IMPLEMENTATION = FALSE
200BD_RESULT_USED_FOR_ORDERING_IMPLEMENTATION = FALSE
CANDIDATE_MODEL_RETRAINED = NO
CANDIDATE_TRAINING_TARGET_CHANGED = NO
CANDIDATE_ACCEPTED_GENERATION_CHANGED = NO
```

## Tests

Executed by Codex:

```text
python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py
python3 -m pytest tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py -q
python3 -m pytest tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py::test_phase15ag_candidate_and_opportunity_artifacts_feed_morning -q
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ai_high_quality_lower_rank_candidate_reaches_pc_competition -q
python3 -m pytest tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_ae1_pm_pc_ps_runtime_canonical_campaign_buy_add_e2e -q
python3 -m pytest tests/strategy/test_phase30_w_entry_one_lot_repair.py -q
python3 -m pytest tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q
python3 -m pytest tests/strategy/test_phase30_j_strategy_intelligence.py::test_phase30_j_strategy_intelligence_shadow_artifact_contract -q
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -q
python3 -m pytest tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py -q
python3 -m pytest tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py -q
```

Initial `python` / `pytest` command names were unavailable in this environment,
so verification used `python3` and `python3 -m pytest`.

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
FRESH_20BD_EXECUTED_BY_CODEX = NO
FRESH_100BD_EXECUTED_BY_CODEX = NO
FRESH_200BD_EXECUTED_BY_CODEX = NO
```

## Fresh Validation Gate

```text
USER_OPERATED_FRESH_VALIDATION_READY
```

Recommended next task:

```text
Phase30-AJ3 - Fresh Candidate Top50 / Production Action Effect Validation
```
