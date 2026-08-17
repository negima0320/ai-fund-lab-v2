# Phase30-AJ3B - Candidate PIT Surface Liquidity Evidence Propagation Repair

Task ID: `Phase30-AJ3B`

## Primary Judgment

```text
LIQUIDITY_PROPAGATION_ROOT_CAUSE = BUY_QUALITY_PROPAGATED_FEATURE_COLUMNS omitted liquidity_avg_volume_20d before candidate_pit_quality_surface.v1
LIQUIDITY_PROPAGATION_DROP_LAYER = src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py::_buy_quality_feature_metadata projection
LIQUIDITY_PROPAGATION_REPAIRED = YES
CANONICAL_LIQUIDITY_AUTHORITY_REUSED = YES
DUPLICATE_LIQUIDITY_AUTHORITY_CREATED = NO
CANDIDATE_SURFACE_SUFFICIENCY_RESTORED = YES
SEMANTIC_HYBRID_ORDERING_PRESERVED = YES
CANDIDATE_MODEL_PRESERVED = YES
TOP50_COUNT = 50
```

The repair is limited to Candidate PIT surface liquidity evidence propagation.
No Candidate model, label, accepted generation, candidate score, semantic
hybrid ordering, surface semantics, threshold, Top50 count, Runtime authority,
BUY authority, PC authority, or PS authority was changed.

## Root Cause

The canonical Candidate feature builder already produced
`liquidity_avg_volume_20d`, and Candidate inference already recognized the same
field for `liquidity_available` evidence.

The Candidate PIT surface also required `liquidity_avg_volume_20d`, but Runtime
BUY quality metadata omitted the field from
`BUY_QUALITY_PROPAGATED_FEATURE_COLUMNS`. Therefore the field existed upstream
in the feature artifact but was absent when `candidate_pit_quality_surface.v1`
evaluated the row.

Observed READ-ONLY source artifact check:

```text
.runtime/operations/feature_artifacts/2022-08-10/candidate_features.parquet rows=4165 liquidity_present=3533 liquidity_positive=3533
.runtime/operations/feature_artifacts/2022-08-12/candidate_features.parquet rows=4165 liquidity_present=3655 liquidity_positive=3655
.runtime/operations/feature_artifacts/2022-08-15/candidate_features.parquet rows=4165 liquidity_present=3722 liquidity_positive=3722
```

This confirms the drop layer was not Candidate feature generation.

## Liquidity Authority

Canonical authority reused:

```text
source_artifact = Candidate feature artifact
source_field = liquidity_avg_volume_20d
consumer = Runtime Candidate PIT surface
```

No new rolling average, fallback heuristic, surface-only liquidity producer, or
Historical-specific liquidity calculation was added.

## Propagation Repair

Implemented path:

```text
Candidate feature artifact liquidity_avg_volume_20d
-> _buy_quality_feature_metadata
-> Candidate artifact row
-> candidate_pit_quality_surface.raw_pit_evidence
-> candidate_coverage_evidence.liquidity_evidence_lineage
```

The same BUY quality metadata projection also keeps Opportunity ranking rows
aligned with the Candidate feature artifact value.

## PIT / Temporal Integrity

Runtime evidence now materializes:

```text
source_artifact
source_field
source_date
as_of_date
business_date
pit_safety.feature_date_lte_business_date
present_row_count
missing_row_count
duplicate_liquidity_authority_created = false
fallback_liquidity_heuristic_used = false
```

Leakage status:

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
200BD_INTERMEDIATE_PERFORMANCE_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Candidate Surface Sufficiency

Focused sentinels verify:

```text
Liquidity available + complete surface evidence -> STRONG_CONTINUATION_SURFACE
Liquidity missing -> INSUFFICIENT_SURFACE_EVIDENCE
Real Runtime fixture lineage -> candidate raw_pit_evidence liquidity equals feature artifact value
```

The missing case remains fail-safe. Missing liquidity is not filled with zero,
market average, or any substitute value.

## Semantic Hybrid Preservation

Preserved ordering:

```text
semantic_hybrid_class priority
then candidate_score descending
then surface-state preference
then code ascending
```

Preserved:

```text
CANDIDATE_SCORE_ROLE = CO_EQUAL_HYBRID_EVIDENCE
CANDIDATE_SURFACE_ROLE = SEMANTIC_HYBRID_AUTHORITY
HARD_LEXICOGRAPHIC_SURFACE_FIRST_RETIRED = YES
SCORE_ONLY_DOMINANCE_RETIRED = YES
TOP50_COUNT = 50
```

## Candidate Model Preservation

```text
CANDIDATE_MODEL_PRESERVED = YES
CANDIDATE_MODEL_RETRAINED = NO
CANDIDATE_TRAINING_TARGET_CHANGED = NO
CANDIDATE_ACCEPTED_GENERATION_PRESERVED = YES
CANDIDATE_ACCEPTED_GENERATION_CHANGED = NO
CANDIDATE_SCORE_CHANGED = NO
EXPECTED_EDGE_STATUS = UNCALIBRATED
```

## Downstream Preservation

Focused regressions passed for Candidate runtime connection, accepted generation,
Phase30-AI comparator, Phase30-AE1 ADD conversion, Phase30-W entry admission,
Phase30-Z reentry, and Position Sizing.

```text
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
SAFETY_HARD_GUARDRAILS_PRESERVED = YES
```

## Legacy / Duplicate Review

```text
DUPLICATE_LIQUIDITY_AUTHORITY_CREATED = NO
DUPLICATE_LIQUIDITY_AUTHORITY_REFERENCE_COUNT = 0
LEGACY_LIQUIDITY_FALLBACK_REFERENCE_COUNT = 0
NEW_AI_CREATED = NO
PARALLEL_CANDIDATE_PATH_CREATED = NO
```

The only new liquidity reference in Runtime is propagation and lineage
materialization of the existing canonical field.

## Tests

Executed by Codex:

```text
env PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py
python3 -m pytest tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py -q
python3 -m pytest tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py::test_phase15ag_candidate_and_opportunity_artifacts_feed_morning -q
python3 -m pytest tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py -q
python3 -m pytest tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py -q
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ai_high_quality_lower_rank_candidate_reaches_pc_competition -q
python3 -m pytest tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_ae1_pm_pc_ps_runtime_canonical_campaign_buy_add_e2e -q
python3 -m pytest tests/strategy/test_phase30_w_entry_one_lot_repair.py -q
python3 -m pytest tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q
python3 -m pytest tests/strategy/test_phase30_j_strategy_intelligence.py::test_phase30_j_strategy_intelligence_shadow_artifact_contract -q
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q
```

The first plain `python3 -m py_compile` attempt failed because macOS attempted
to write pycache under `/Users/negishi/Library/Caches/com.apple.python`, which
is outside the sandbox. Re-running with `PYTHONPYCACHEPREFIX=/private/tmp/...`
passed.

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
Phase30-AJ3C - Fresh Candidate Surface / Top50 Action Effect Validation
```
