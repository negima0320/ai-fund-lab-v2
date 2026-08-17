# Phase30-AJ2 - Candidate Top50 PIT Quality Surface Repair Implementation and Legacy Retirement

Task ID: `Phase30-AJ2`

## Primary Judgment

```text
PHASE30_AJ2_CANDIDATE_TOP50_PIT_QUALITY_SURFACE_REPAIR = IMPLEMENTED
CANDIDATE_MODEL_PRESERVED = YES
CANDIDATE_ACCEPTED_GENERATION_PRESERVED = YES
CANDIDATE_STAGE_PIT_QUALITY_SURFACE = IMPLEMENTED
QUALITY_AWARE_TOP50 = IMPLEMENTED
TOP50_COUNT = 50
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
CANDIDATE_TRAINING_TARGET_CHANGED = NO
PARALLEL_CANDIDATE_PATH_CREATED = NO
ONE_PRODUCTION_CANDIDATE_PATH = YES
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
```

Phase30-AJ2 implements the Phase30-AJ1 Option C design in the existing
Production-common Candidate AI path.

The repaired path is:

```text
all eligible stocks
-> accepted Candidate model
-> candidate_score / candidate_rank
-> Candidate-stage PIT Quality Surface
-> quality-aware Top50
-> Opportunity AI
-> Strategy Intelligence / Phase30-AI Selection Quality Comparator
-> PC
-> PS
-> Runtime
```

No Candidate model, label, accepted generation, Top50 count, Runtime authority,
BUY authority, Safety authority, threshold, or training target was changed.

## Candidate Model Preservation

Preserved:

```text
candidate_score = momentum_candidate_label model score
candidate_rank = score-only Candidate model rank
Candidate AI = broad-market upward-momentum discovery authority
```

`candidate_score` was not redefined as BUY probability, expected return,
expected edge, continuation quality, Entry Admission, or allocation authority.

`candidate_rank` remains the model score rank. The new final ordering is
materialized separately as:

```text
quality_aware_candidate_rank
```

## Candidate PIT Quality Surface

Implemented in:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

Schema:

```text
candidate_pit_quality_surface.v1
```

Canonical states:

```text
STRONG_CONTINUATION_SURFACE
VALID_MOMENTUM_SURFACE
CAUTION_MOMENTUM_SURFACE
INSUFFICIENT_SURFACE_EVIDENCE
```

Per-symbol materialization:

- `candidate_score`
- `candidate_rank`
- `score_only_candidate_rank`
- `quality_aware_candidate_rank`
- `candidate_pit_surface_state`
- `candidate_pit_quality_surface`
- raw PIT evidence
- reason codes
- evidence sufficiency
- PIT / leakage metadata
- not-BUY-authority metadata

Allowed evidence is limited to decision-time Candidate-stage PIT features:

- 5D / 20D / 60D return
- close / MA20
- MA5 / MA20
- MA20 / MA60
- acceleration / deceleration
- volume momentum
- volatility
- liquidity

No future returns, campaign outcomes, portfolio PnL, selected/bought outcome,
Paper Ledger result, or downstream full CQ / Risk / Entry comparator copy is
used.

## Quality-Aware Top50

Old action-effective behavior:

```text
candidate_score descending -> Top50
```

New behavior:

```text
Candidate model score/rank
+ Candidate-stage PIT Quality Surface
-> quality-aware Top50
```

Ordering:

```text
surface priority
then candidate_score descending
then code ascending
```

This means:

- strong current continuation surface can compete above high-score but
  currently degrading momentum;
- candidate score remains the tie-breaker and momentum-discovery evidence;
- insufficient evidence does not promote a symbol by quality surface alone;
- Top50 count stays fixed at 50.

## Candidate Score / Rank Role

Phase30-AJ1 migration inventory implemented:

| Logic | Status |
|---|---|
| candidate score dominance | `MODIFY` |
| candidate rank dominance | `MODIFY` |
| high candidate score reason | `KEEP` |
| volume momentum reason | `KEEP` |
| score-only ranking fallback | `DEPRECATE_DURING_MIGRATION` |
| duplicated quality prefilter | `REMOVE_AFTER_MIGRATION` |

`score_only_top50_symbol_order` remains only as before/after coverage evidence.
It is not the final Top50 authority.

## Phase30-AI Interaction

Preserved:

```text
PHASE30_AI_SELECTION_COMPARATOR_PRESERVED = YES
```

Role split remains:

```text
Candidate PIT Quality Surface = broad market Top50 surface
Phase30-AI Comparator = richer downstream quality comparison inside Top50
PC = target allocation authority
PS = quantity authority
Runtime = pure mapper
```

The Candidate surface does not copy the full Phase30-AI comparator.

## Candidate Coverage Evidence

Candidate artifact now materializes:

- `market_eligible_count`
- `candidate_pre_cut_count`
- `candidate_score_distribution`
- `candidate_rank_distribution`
- `candidate_pit_surface_distribution`
- `top50_surface_distribution`
- `market_healthy_proxy_count`
- `candidate_healthy_proxy_count`
- `healthy_proxy_capture_ratio`
- `final_top50_symbol_order`
- `score_only_top50_symbol_order`
- `score_only_ordering_changed`
- `quality_aware_added_symbols`
- `quality_aware_removed_symbols`

This makes the Phase30-AJ3 fresh validation question directly auditable:

```text
Did Candidate Top50 actually change?
Which symbols were added / removed by quality-aware ordering?
Did HIGH / VALID surface counts improve downstream comparator quality?
```

## Ordering Sentinels

Added:

```text
tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py
```

Sentinels cover:

- high candidate score + strong historical momentum + current degradation is
  materialized as `CAUTION_MOMENTUM_SURFACE`;
- moderate candidate score + healthy current continuation can outrank the
  degrading high-score case;
- strong score + healthy continuation remains high priority;
- insufficient evidence does not override Candidate model evidence;
- Top50 count remains fixed;
- model score rank is preserved separately from quality-aware rank.

## Legacy Retirement

```text
OBSOLETE_SCORE_ONLY_TOP50_PATH_REFERENCE_COUNT = 0
DUPLICATE_CANDIDATE_QUALITY_SURFACE_REFERENCE_COUNT = 0
PARALLEL_CANDIDATE_PATH_REFERENCE_COUNT = 0
ONE_PRODUCTION_CANDIDATE_PATH = YES
```

Evidence:

```text
reports/phase_reports/phase30_aj2_candidate_legacy_retirement_evidence.json
```

The remaining `score_only_top50_symbol_order` and `score_only_top = rows[:top_n]`
references are before/after evidence only, not production Top50 authority.

## Production Integrity

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

## Leakage / Training Integrity

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
CANDIDATE_TRAINING_TARGET_CHANGED = NO
CANDIDATE_MODEL_RETRAINED = NO
CANDIDATE_ACCEPTED_GENERATION_CHANGED = NO
```

## Tests

Passed:

```text
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py

PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m pytest tests/runtime_v2/test_phase30_aj2_candidate_pit_quality_surface.py

PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m pytest tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py::test_phase15ag_candidate_and_opportunity_artifacts_feed_morning tests/runtime_v2/test_phase19_br_accepted_generation_bound_runtime_inference.py::test_phase19_br_runtime_producer_uses_generation_bound_scaler_without_legacy_fallback

PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m pytest tests/strategy/test_phase30_j_strategy_intelligence.py::test_phase30_j_strategy_intelligence_shadow_artifact_contract tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ai_high_quality_lower_rank_candidate_reaches_pc_competition tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_ae1_pm_pc_ps_runtime_canonical_campaign_buy_add_e2e tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py
```

One Accepted Generation runtime producer test skipped when the local real
accepted-generation pointer/artifacts were not available in that isolated test
context.

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
FRESH_20BD_EXECUTED_BY_CODEX = NO
FRESH_100BD_EXECUTED_BY_CODEX = NO
```

## Fresh Validation Gate

```text
USER_OPERATED_FRESH_VALIDATION_READY
```

## Recommended Next Task

```text
Phase30-AJ3 - Fresh Candidate Top50 / Production Action Effect Validation
```
