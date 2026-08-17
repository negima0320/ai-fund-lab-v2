# Phase30-AI - Selection Quality / Opportunity Capture Repair Implementation and Legacy Retirement

Task ID: `Phase30-AI`

## Primary Judgment

```text
PHASE30_AI_SELECTION_QUALITY_OPPORTUNITY_CAPTURE_REPAIR = IMPLEMENTED
REGRESSION_REPAIR_STATUS = REPAIRED
ONE_PRODUCTION_SELECTION_PATH = YES
PARALLEL_SELECTION_PATH_CREATED = NO
USER_OPERATED_FRESH_100BD_READY
```

Phase30-AI implements the Phase30-AH design in the existing Production-common
Strategy Intelligence -> Portfolio Construction -> Position Sizing path. It
does not add a parallel selector, force investment, tune thresholds from
Historical outcomes, retrain a model, or change Runtime authority.

## Implementation Status

Implemented:

- `strategy_intelligence.py` now emits `selection_quality_comparator.v1` per
  symbol and `selection_quality_comparator_summary.v1` at payload level.
- `portfolio_construction.py` consumes the comparator fields and uses quality
  tier as allocation evidence inside existing target-member competition.
- `position_sizing.py` materializes `pc_ps_zero_delta_taxonomy.v1` for
  resolved zero-delta outcomes.
- Regression sentinels were added for high-quality lower-rank candidate
  competition and PC-positive / PS-zero taxonomy.

No fresh 20BD, 100BD, or long Historical run was executed by Codex.

## Selection Quality Comparator

Canonical tiers:

```text
HIGH_QUALITY_CONTINUATION
VALID_CONTINUATION
CAUTION_CONTINUATION
INSUFFICIENT_QUALITY
REJECT
```

The comparator uses existing PIT evidence only:

- 5D / 20D return structure;
- MA5 / MA20 structure;
- acceleration / deceleration;
- Continuation Quality;
- Relative Strength;
- Downside Risk;
- volatility and participation;
- regime compatibility;
- Entry Admission;
- BUY Quality;
- opportunity rank / score as supporting metadata.

The comparator is evidence, not action authority:

```text
selection_quality_not_action_authority = TRUE
future_information_used = FALSE
```

## Rank / Score Migration

`runtime_opportunity_score` and Expected Edge remain uncalibrated:

```text
EXPECTED_EDGE_STATUS = UNCALIBRATED
EXPECTED_EDGE_ROLE = UNCALIBRATED_SUPPORTING
OPPORTUNITY_RANK_ROLE = SUPPORTING_NOT_HARD_REJECTION_AUTHORITY
```

`below_opportunity_top20` and `non_positive_expected_edge_score` are preserved
as observable soft relative metadata under uncalibrated semantics. They are not
standalone hard BUY_NEW rejection authority for high-quality PIT candidates.

Economic hard rejection remains preserved only when calibrated economic units
are explicitly available.

## Candidate Coverage

Strategy Intelligence now materializes:

- candidate quality-tier distribution;
- candidate rows with comparator;
- candidate healthy proxy count;
- market healthy proxy count from `technical_feature_summary.rows`;
- rank / score supporting role metadata.

## PC Integration

Portfolio Construction consumes SI comparator fields:

- `selection_quality_comparator`;
- `selection_quality_tier`;
- `selection_quality_reason_codes`;
- `selection_quality_evidence_sufficiency`;
- `selection_quality_rank_score_role`;
- `selection_quality_expected_edge_role`;
- `selection_quality_score_only_hard_rejection_retired`.

When any selection tier is present, PC target-member ordering uses tier priority
before construction priority. This restores high-quality candidate competition
without bypassing hard blockers or downstream feasibility.

## Market Caution / Individual Quality

Market caution remains evidence and does not automatically erase individual
quality. A strong individual setup can remain PC-competitive when CQ, RS, Risk,
Entry Admission, BUY Quality, and eligibility support it. Hard risk blockers
still win.

## Capital Utilization

Cash remains valid. Phase30-AI does not introduce minimum exposure, minimum BUY
count, cash cap, or forced residual deployment. High cash is acceptable when
quality, opportunity cost, PC, PS, Runtime, or Safety evidence does not support
execution.

## PC -> PS Zero Delta Taxonomy

Position Sizing now emits `pc_ps_zero_delta_taxonomy.v1`:

```text
GENUINE_LOT_INFEASIBILITY
MINIMUM_MEANINGFUL_NOTIONAL
CONCENTRATION_HEADROOM_LIMIT
ZERO_INCREMENTAL_TARGET
RESIDUAL_CAPITAL_TOO_SMALL
QUALITY_DEFERRED_TO_CASH
```

This is observability only. It does not weaken PS lot constraints or force a
Runtime BUY.

## ADD / Winner Preservation

Preserved:

```text
HOLD-worthy != ADD-worthy
BUY_NEW quality tier cannot authorize ADD
PM ADD -> PC campaign continuation -> PS quantity delta -> Runtime BUY_ADD remains required
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
SELL_REDUCE_EXIT_SEMANTICS_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
```

## Legacy Retirement Integrity

Source reference search result:

```text
UNCALIBRATED_SCORE_ONLY_HARD_REJECTION_REFERENCE_COUNT = 0
STANDALONE_BELOW_TOP20_HARD_REJECTION_REFERENCE_COUNT = 0
OBSOLETE_RANKING_FALLBACK_REFERENCE_COUNT = 0
DUPLICATE_SELECTION_QUALITY_ENGINE_REFERENCE_COUNT = 0
```

Remaining `non_positive_expected_edge_score` hard-block references are guarded
by `economic_units_available == true`, preserving calibrated-economic semantics.

## Production Integrity

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
PHASE30_S_HANDOFF_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_W_ONE_LOT_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
ONE_PRODUCTION_SELECTION_PATH = YES
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
EXPECTED_EDGE_STATUS = UNCALIBRATED
```

## Tests

Passed:

```text
python3 -m py_compile src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py

python3 -m pytest tests/strategy/test_phase30_j_strategy_intelligence.py::test_phase30_j_strategy_intelligence_shadow_artifact_contract tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ai_high_quality_lower_rank_candidate_reaches_pc_competition tests/strategy/test_phase22_j_position_sizing.py::test_phase30_ai_pc_ps_zero_delta_taxonomy_materializes_lot_infeasibility

python3 -m pytest tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21t_ak_negative_uncalibrated_full_quality_reaches_target_member_competition tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21t_ak_negative_uncalibrated_reduced_quality_reaches_target_member_competition tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21t_ak_high_downside_hard_block_preserved_with_combined_soft_reasons tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21t_ak_top20_uncalibrated_reason_is_soft_metadata tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21t_ak_buy_quality_reject_remains_zero_allocation tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ae1_canonical_si_campaign_repairs_runtime_current_add_mismatch tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ae1_canonical_campaign_preserves_reversal_risk_no_add tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_ae1_pm_pc_ps_runtime_canonical_campaign_buy_add_e2e

python3 -m pytest tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase22_g_runtime_planning.py::test_phase29_l21f_runtime_planning_consumes_soft_cap_buy_add_positive_quantity tests/strategy/test_phase22_g_runtime_planning.py::test_phase29_l21t_b_runtime_planning_consumes_one_lot_buy_new_soft_cap_quantity

python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py
```

Summary:

```text
ADDED_SENTINELS = 3 passed
PHASE29_SCORE_RANK_SOFT_REGRESSIONS = passed
AE1_ADD_PRESERVATION = passed
W_ENTRY_ONE_LOT_PRESERVATION = passed
Z_REENTRY_PRESERVATION = passed
S_HANDOFF_PRESERVATION = passed
PC_PS_FULL_FILES = 195 passed
```

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Fresh Validation Gate

```text
USER_OPERATED_FRESH_100BD_READY
```

## Recommended Next Task

```text
Phase30-AJ - Fresh 100BD Selection / Winner / Capital Validation
```
