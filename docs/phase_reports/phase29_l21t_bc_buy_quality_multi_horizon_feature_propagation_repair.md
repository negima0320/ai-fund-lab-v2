# Phase29-L21T-BC BUY Quality Multi-Horizon Feature Propagation Repair

## Task

Phase29-L21T-BC

Mode: IMPLEMENTATION REPAIR.

Phase30 was not entered. Codex did not run fresh-run, resume, replay, recovery, or long Historical. The target run was not mutated.

## Primary Judgment

`PHASE29_L21T_BC_BUY_QUALITY_MULTI_HORIZON_FEATURE_PROPAGATION_REPAIRED_REGRESSION_PASS`

## Root Cause

Phase29-L21T-BB confirmed that actual runtime market refresh generated the AV multi-horizon feature columns, but the BUY Quality consumer rows did not receive them:

```text
feature artifact
-> Candidate artifact rows: raw trajectory fields dropped
-> Opportunity artifact rows: raw trajectory fields dropped
-> BUY Quality: required feature missing
-> MIXED_OR_UNRESOLVED / BUY_WAIT
```

On `2022-08-10`, all 50 BUY Quality decisions were `MIXED_OR_UNRESOLVED`; 41 became BUY_WAIT, while non-momentum BUY Quality components were PASS.

## Repair

Updated `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` so the production-common BUY AI producer preserves a whitelisted PIT feature subset from canonical feature artifacts into decision artifacts:

```text
candidate_features.parquet
-> candidate_decisions.json rows

opportunity_feature_input.parquet
-> opportunity_rankings.json rankings
```

The repair propagates existing values only. It does not recompute, infer, zero-fill, relax consumer requirements, or alter BUY Quality logic.

## Propagated Fields

The BUY Quality passthrough subset is:

- `price_momentum_return_1d`
- `price_momentum_return_3d`
- `price_momentum_return_5d`
- `price_momentum_return_10d`
- `price_momentum_return_20d`
- `price_momentum_return_60d`
- `volatility_return_std_20d`
- `recent_move_volatility_z_1d`
- `recent_move_volatility_z_3d`
- `momentum_5d_vs_20d_delta`
- `momentum_1d_vs_5d_delta`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `trend_ma_20_60_ratio`
- `volume_momentum_ratio_5d`
- `volume_momentum_ratio_1d_20d`

If a field is truly missing or NaN in the source feature artifact, the producer does not synthesize a value. BUY Quality therefore retains the existing fail-closed MIXED/WAIT behavior for true missing evidence.

## Contract Update

Updated `docs/02_architecture/ai_input_output_and_artifact_contract.md` to state that Candidate and Opportunity decision artifacts must preserve the PIT multi-horizon feature subset needed by downstream Adaptive BUY Quality when those fields are present in their canonical feature artifacts.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`

## Regression Coverage

Focused propagation regression:

```text
python3 -m pytest tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py
8 passed
```

This verifies:

- Candidate row has required propagated feature fields.
- Opportunity row has required propagated feature fields.
- Candidate and Opportunity values match the source feature artifact.
- Existing planning signal loading remains unchanged.

BUY Quality classification regression:

```text
python3 -m pytest tests/strategy/test_phase26_h_adaptive_buy_quality.py
24 passed
```

This verifies:

- `HEALTHY_CONTINUATION` remains BUY eligible.
- `FADING_PRIOR_WINNER` becomes BUY_WAIT.
- `RECENT_ACCELERATION_OVERHEAT` becomes BUY_WAIT.
- true required feature missing remains MIXED / BUY_WAIT fail-closed.
- BUY_WAIT does not become Human Review.

Market refresh / readiness / producer integration:

```text
python3 -m pytest tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py
21 passed
```

PC / PS / Runtime Planning:

```text
python3 -m pytest tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py
263 passed
```

BA no-order / normal execution / submit:

```text
python3 -m pytest tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py
43 passed
```

SELL / REDUCE / BUY_ADD / REENTRY:

```text
python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21r3_reentry_capacity_authority_resolves_normal_excessive_and_missing_cases tests/strategy/test_phase22_j_position_sizing.py::test_phase29_l21t_c_ps_preserves_reentry_semantics_for_one_lot_quantity_authority
54 passed
```

Validation:

```text
PYTHONPYCACHEPREFIX=/tmp/ai_fund_lab_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py
PASS

git diff --check -- src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py docs/02_architecture/ai_input_output_and_artifact_contract.md
PASS
```

## Preservation

- Feature artifact source: `candidate_features.parquet` and `opportunity_feature_input.parquet`
- Candidate propagation: repaired
- Opportunity propagation: repaired
- BUY Quality propagation: repaired through existing source-summary row consumption
- Feature values preserved: YES
- PIT preserved: YES
- Zero-fill introduced: NO
- Consumer requirement relaxed: NO
- BUY_WAIT semantics changed: NO
- SELL affected: NO
- BUY_ADD affected: NO
- REENTRY affected: NO
- BA authorized no-order contract preserved: YES
- Runtime mutated by Codex: NO
- Fresh-run executed by Codex: NO
- Phase30 entered: NO

## Residual Risk

No focused regression failures remain. The halted target run was not resumed, and no new 20BD fresh validation was run by Codex. Operator validation is still required to observe the repaired feature propagation in an actual fresh runtime run.

## Next Step

Recommended next action:

`Phase29-L21T-BD - Post-BC Short Fresh Validation Readiness / Operator Command Prep`

Prepare user-run short fresh validation for the Post-AV/Post-AY/Post-BA/Post-BC path, with checks for Candidate/Opportunity/BQ feature propagation, HEALTHY/FADING/OVERHEAT distribution, BUY_WAIT no-Pending semantics, BA no-order continuity, and SELL independence.
