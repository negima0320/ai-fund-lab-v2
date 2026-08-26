# Phase31-G32 - Production-Equivalent Integrated Final Acceptance / Historical Entry Gate

Task type: FINAL INTEGRATED ACCEPTANCE

Implementation changes: NO
Strategy / Runtime / schema / configuration / threshold / fixture changes: NO
Fresh run / resume / replay / Historical rerun / long Historical: NO

## Primary Judgment

PRIMARY_JUDGMENT =
PHASE31_G32_ACCOUNTING_OR_BASIS_PERSISTENCE_GAP_FOUND

G32 is not accepted. The focused integrated regression suite exposed a
mandatory basis/accounting regression in an accepted cost-basis authority test.
Per the G32 instruction, no repair was attempted inside this task.

Failed boundary:

```text
Execution fill sequence
-> runtime-owned current projection
-> open position cost_basis / average_price persistence
-> realized + unrealized PnL reconciliation
```

Failing test:

```text
tests/runtime_v2/test_phase24_h_cost_basis_authority.py::test_phase24_h_phase24g_generalized_sequence_reconciles_execution_basis_pnl
```

Observed failure:

```text
expected open cost_basis sum = 659,070
actual open cost_basis sum   = 711,030
delta                        = +51,960
```

The failed test covers a multi-symbol, multi-cycle BUY / ADD-like buy /
partial/full SELL / re-entry-style sequence and is directly relevant to:

- `BASIS_METADATA_LIFECYCLE`
- `BASIS_MISMATCH_COUNT`
- `INTEGRATED_ACCOUNTING_RECONCILIATION`
- Historical readiness entry safety

## SoT Read

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g28_risk_pacing_authoritative_activation_shadow_cutover.md`
- `docs/phase_reports/phase31_g29_production_end_to_end_implementation_connectivity_audit.md`
- `docs/phase_reports/phase31_g30_runtime_authority_lineage_persistence_connectivity_repair.md`
- `docs/phase_reports/phase31_g31_production_end_to_end_implementation_connectivity_reacceptance.md`

## Focused Integrated Regression

Command run:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_g30_authority_lineage.py tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py
```

Result:

```text
551 passed
1 failed
```

Failing test was re-run alone and reproduced:

```bash
python3 -m pytest tests/runtime_v2/test_phase24_h_cost_basis_authority.py::test_phase24_h_phase24g_generalized_sequence_reconciles_execution_basis_pnl -q
```

Result:

```text
1 failed
```

PY_COMPILE =
PASS with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache-g32 python3 -m compileall -q src tests`

GIT_DIFF_CHECK =
PASS

## Non-Failing Evidence

Before the basis failure, the focused suite passed Strategy, Runtime Planning,
Pending, Submit, Execution no-action, Safety, BUY/SELL independence, pending
composition/idempotency, lineage, prior EXIT/Re-entry, lot-aware PC/Sizing, and
most runtime-owned fill projection tests.

This means G32 did not find a new G29/G30/G31 lineage connectivity failure.
The blocker is specifically the accounting/basis persistence contract.

## Required Summary Output

PRIMARY_JUDGMENT =
PHASE31_G32_ACCOUNTING_OR_BASIS_PERSISTENCE_GAP_FOUND

SCENARIO_A_NEW_BUY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_B_ADD =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_C_CASH_OPTIONALITY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_D_REENTRY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_E_REENTRY_SCOPE =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_F_LOT_RECONSIDERATION =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_G_NO_DEPLOYABLE =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_H_BUY_SELL_INDEPENDENCE =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_I_PENDING_SCOPE =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_J_SAFETY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

SCENARIO_K_NO_ACTION =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

RISK_PACING_CROSS_DAY_TRANSITION =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

STALE_RISK_PACING_USE_COUNT =
0

POSITION_LIFECYCLE_CROSS_DAY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

CASH_LIFECYCLE_CROSS_DAY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

CASH_DOUBLE_USE_COUNT =
0

STALE_CASH_USE_COUNT =
0

PRICE_QUANTITY_ADJUSTMENT_BASIS_CONTRACT =
FAIL

BASIS_METADATA_LIFECYCLE =
FAIL

BASIS_MISMATCH_COUNT =
1

LINEAGE_LIFECYCLE_END_TO_END =
PASS

LINEAGE_HASH_MISMATCH_COUNT =
0

AUTHORITATIVE_FIELD_LOSS_ON_RELOAD_COUNT =
0

RUNTIME_STRATEGY_REDECISION_COUNT =
0

PENDING_STRATEGY_REDECISION_COUNT =
0

SUBMIT_STRATEGY_REDECISION_COUNT =
0

EXECUTION_STRATEGY_REDECISION_COUNT =
0

DISCRETE_QUANTITY_OWNER =
POSITION_SIZING

DOWNSTREAM_QUANTITY_REDECISION_COUNT =
0

SECOND_DISCRETE_QUANTITY_AUTHORITY_COUNT =
0

CAPITAL_COMPETITION_OWNER =
PORTFOLIO_CONSTRUCTION

FINAL_NO_DEPLOYABLE_OWNER =
PORTFOLIO_CONSTRUCTION

DOWNSTREAM_CAPITAL_REDECISION_COUNT =
0

RISK_PACING_OWNER =
PORTFOLIO_POLICY

RISK_PACING_AUTHORITATIVE_CONSUMER =
PORTFOLIO_CONSTRUCTION

RISK_PACING_AUTHORITATIVE_CONSUMER_COUNT =
1

REENTRY_ELIGIBILITY_OWNER =
PORTFOLIO_CONSTRUCTION

DUPLICATE_REENTRY_AUTHORITY_COUNT =
0

PM_ADD_INTENT_OWNER =
POSITION_MANAGEMENT

ADD_CAPITAL_COMPETITION_OWNER =
PORTFOLIO_CONSTRUCTION

ADD_DISCRETE_QUANTITY_OWNER =
POSITION_SIZING

DUPLICATE_ADD_AUTHORITY_COUNT =
0

SAFETY_AUTHORITY =
SAFETY

SAFETY_BYPASS_COUNT =
0

G32_END_TO_END_PIT =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

FUTURE_INPUT_COUNT =
0

HISTORICAL_RESULT_INPUT_COUNT =
0

PAPER_LEDGER_STRATEGY_INPUT_COUNT =
0

AUDIT_RESULT_STRATEGY_INPUT_COUNT =
0

PERMANENT_LEGACY_BUSINESS_FALLBACK_COUNT =
0

PERMANENT_SHADOW_BUSINESS_PATH_COUNT =
0

IMPLICIT_BUSINESS_FALLBACK_COUNT =
0

FALSE_RUNTIME_HALT_COUNT =
0

PENDING_STATE_INTEGRITY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

ORPHAN_PENDING_ITEM_COUNT =
0

ORDER_IDEMPOTENCY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

FILL_IDEMPOTENCY =
PASS_FOCUSED_REGRESSION_BEFORE_BASIS_GATE

DUPLICATE_ECONOMIC_EFFECT_COUNT =
0

INTEGRATED_ACCOUNTING_RECONCILIATION =
FAIL

HISTORICAL_CONNECTIVITY_RISK =
HIGH

HISTORICAL_VALIDATION_ENTRY_READY =
NO

G32_INTEGRATED_ACCEPTANCE_TESTS =
FAIL

ALL_G32_REGRESSIONS =
FAIL

IMPLEMENTATION_CHANGE_EXECUTED =
NO

CONFIG_CHANGE_EXECUTED =
NO

PARAMETER_CHANGE_EXECUTED =
NO

FRESH_RUN_EXECUTED =
NO

RESUME_EXECUTED =
NO

REPLAY_EXECUTED =
NO

HISTORICAL_RERUN_EXECUTED =
NO

LONG_HISTORICAL_EXECUTED =
NO

PY_COMPILE =
PASS

GIT_DIFF_CHECK =
PASS

NEXT_TASK_RECOMMENDATION =
PHASE31_G33_RUNTIME_OWNED_FILL_PROJECTION_BASIS_ACCOUNTING_REPAIR

Do not start the user-operated fresh 150BD Historical performance validation
until the basis/accounting regression is repaired and G32 is re-run cleanly.
