# Phase29-L21T-AY — Runtime Market Refresh Multi-Horizon Feature Producer Integration Repair

## Task ID

Phase29-L21T-AY

## Primary Judgment

PHASE29_L21T_AY_RUNTIME_MARKET_REFRESH_MULTI_HORIZON_FEATURE_PRODUCER_INTEGRATION_REPAIRED_FOCUSED_REGRESSION_PASS

Phase29 remains active. Phase30 was not entered.

## Scope

IMPLEMENTATION REPAIR only. Codex did not execute fresh-run, resume, replay,
recovery, or long Historical validation, and did not mutate the AX target run.

## Root Cause

AX confirmed that the actual Production-common market_refresh feature producer:

```text
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
```

did not materialize the Phase29-L21T-AV multi-horizon feature columns. Consumer
readiness required those columns and correctly halted with:

```text
consumer_schema_review_required:candidate,opportunity
```

## Changed Files

- `src/ai_fund_lab_v2/paper_trading/feature_refresh.py`
- `tests/paper_trading/test_phase9j_feature_refresh.py`
- `tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`

## Repair

Updated the actual runtime market_refresh producer contract so candidate and
opportunity feature artifacts materialize:

```text
price_momentum_return_1d
price_momentum_return_3d
price_momentum_return_10d
recent_move_volatility_z_1d
recent_move_volatility_z_3d
momentum_5d_vs_20d_delta
momentum_1d_vs_5d_delta
```

The opportunity artifact receives the same raw technical facts through the
existing candidate-to-opportunity feature input copy path.

## Preserved Semantics

- Existing 5BD / 20BD / 60BD calculations: unchanged
- PIT-only cutoff: preserved
- Future data: not used
- Zero-fill for missing / insufficient history: not introduced
- True insufficient history: remains fail-closed through existing
  `candidate_no_universe_eligible_rows` behavior
- Consumer readiness: not relaxed
- Model retraining: not performed
- Threshold policy: unchanged
- BUY_WAIT semantics: unchanged
- SELL / BUY_ADD / REENTRY authority: unchanged
- Historical-only branch: not introduced

## Focused Producer Results

Focused regression proves:

- actual `run_feature_refresh()` emits all 7 AV columns in
  `candidate_features.parquet`
- actual `run_feature_refresh()` emits all 7 AV columns in
  `opportunity_feature_input.parquet`
- 1BD / 3BD / 10BD formulas match source PIT quotes
- volatility z and momentum delta formulas match source PIT quotes
- 5BD / 20BD formulas remain unchanged
- insufficient history leaves AV columns null rather than zero-filled
- consumer readiness returns `READY`

Focused test result:

```text
tests/paper_trading/test_phase9j_feature_refresh.py
tests/runtime_v2/test_phase15an_feature_consumer_readiness.py
tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py
18 passed
```

## Broader Regression Results

Strategy / Planning / SELL / REENTRY focused:

```text
tests/strategy/test_phase26_h_adaptive_buy_quality.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
tests/strategy/test_phase22_g_runtime_planning.py
tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py
tests/strategy/test_phase29_l21k_prior_exit_materialization.py
310 passed
```

Feature generation / data readiness / Submit / Execution focused:

```text
tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
tests/test_phase4ak_real_runtime_feature_generation.py
tests/test_phase4bc_long_history_feature_regeneration.py
tests/test_phase4e_candidate_feature_builder_mock.py
tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py
56 passed
```

## Final Validation

- `py_compile`: PASS
- summary JSON parse: PASS
- `git diff --check`: PASS

## Runtime Mutation Statement

Runtime mutated by Codex: NO.

AX target run mutated by Codex: NO.

Fresh-run / resume / replay / recovery executed by Codex: NO.

## Recommended Next Action

Run a new operator-owned Phase29-L21T-AW short fresh validation. The previous AX
halted run should not be resumed for this validation.
