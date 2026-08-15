# Phase29-L21T-AV — Multi-Horizon Momentum Trajectory Semantics Implementation

## Task ID

Phase29-L21T-AV

## Primary Judgment

PHASE29_L21T_AV_MULTI_HORIZON_MOMENTUM_TRAJECTORY_SEMANTICS_IMPLEMENTED_FOCUSED_REGRESSION_PASS

Phase29 remains active. Phase30 was not entered.

## Scope

Implemented the AU/AU2 Production-common Momentum Trajectory design as an
Adaptive BUY Quality extension for BUY_NEW.

No fresh-run, resume, replay, recovery, long Historical run, or target runtime
mutation was performed.

## Changed Files

- `src/ai_fund_lab_v2/strategy/input_materialization.py`
- `src/ai_fund_lab_v2/candidate_ai/feature_builder.py`
- `src/ai_fund_lab_v2/candidate_ai/schemas.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py`
- `src/ai_fund_lab_v2/strategy/buy_quality.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `scripts/build_phase4ak_real_runtime_features.py`
- `scripts/build_phase4bc_long_history_features.py`
- `tests/strategy/test_phase22_qe_input_materialization.py`
- `tests/strategy/test_phase26_h_adaptive_buy_quality.py`
- `tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py`
- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/02_architecture/position_management_feature_input_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`

## Technical Feature Implementation

New Production-common feature facts:

- `price_momentum_return_1d`
- `price_momentum_return_3d`
- `price_momentum_return_10d`
- `recent_move_volatility_z_1d`
- `recent_move_volatility_z_3d`
- `momentum_5d_vs_20d_delta`
- `momentum_1d_vs_5d_delta`

Existing `price_momentum_return_5d` and `price_momentum_return_20d` calculations
were preserved.

## Authority Before / After

Before:

- Adaptive BUY Quality did not distinguish recent fading / overheat trajectory.
- PC / PS could only consume generic BUY Quality fields.
- 53800 / 78780 style cases could remain BUY_NEW-eligible despite broken recent
  trajectory.

After:

- Technical Features own raw multi-horizon PIT facts.
- Adaptive BUY Quality owns `momentum_trajectory_quality` classification.
- PC / PS consume/copy BUY Quality trajectory fields and do not recompute.
- `FADING_PRIOR_WINNER` and `RECENT_ACCELERATION_OVERHEAT` map to `BUY_WAIT`.
- `BUY_WAIT` is temporary BUY_NEW ineligibility, not Human Review.

## BUY_WAIT Semantics

`BUY_WAIT`:

- blocks BUY_NEW quantity for the current day
- creates no BUY Pending
- creates no Human Review Pending
- does not halt Runtime
- does not block SELL Planning
- is reevaluated on the next business day from PIT features
- does not apply to BUY_ADD, REENTRY, HOLD, REDUCE, or EXIT

## Focused Fixture Results

53800-type fading fixture:

- Classification: `FADING_PRIOR_WINNER`
- Action: `BUY_WAIT`
- PC result: zero allocation / excluded from BUY_NEW
- Review pending: not created

78780-type fading fixture:

- Classification: `FADING_PRIOR_WINNER`
- Action: `BUY_WAIT`
- PC result: zero allocation / excluded from BUY_NEW
- Review pending: not created

Healthy continuation fixture:

- Classification: `HEALTHY_CONTINUATION`
- Action: `BUY_ELIGIBLE`
- Existing BUY Quality / PC / Safety chain remains active

Overheat fixture:

- Classification: `RECENT_ACCELERATION_OVERHEAT`
- Action: `BUY_WAIT`
- PC result: zero allocation / excluded from BUY_NEW

## Regression Results

Executed focused regression:

- `tests/strategy/test_phase26_h_adaptive_buy_quality.py`
- `tests/strategy/test_phase22_qe_input_materialization.py`
- `tests/runtime_v2/test_phase15an_feature_consumer_readiness.py`
- Result: 40 passed

Executed PC / PS / Runtime Planning / Pending focused regression:

- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
- `tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`
- Result: 278 passed

Executed Submit / Execution / SELL / REDUCE / REENTRY focused regression:

- `tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py`
- `tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py`
- `tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py`
- `tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`
- `tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- Result: 77 passed

Executed feature generation / readiness regression:

- `tests/test_phase4ak_real_runtime_feature_generation.py`
- `tests/test_phase4bc_long_history_feature_regeneration.py`
- `tests/test_phase4e_candidate_feature_builder_mock.py`
- `tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py`
- Result: 26 passed

## Preserved Constraints

- Historical-only logic: not introduced
- Future data: not used
- Threshold tuned from AT sample: not introduced
- Model retraining: not performed
- Score `<= 0` absolute gate: not restored
- SELL authority: unchanged
- Re-entry guard: not weakened
- Existing holdings SELL behavior: unchanged
- BUY_ADD / REENTRY: not affected by `BUY_WAIT`

## Final Validation

- `py_compile`: PASS
- `summary.json` parse: PASS
- `git diff --check`: PASS

## RESUME_SAFE_NOW

NO. This task did not validate or authorize any target Historical run resume.

## Recommended Next Step

Run the final validation block, then operator-owned short fresh validation can
be considered in a separate task. Codex must not run long Historical validation
for this task.
