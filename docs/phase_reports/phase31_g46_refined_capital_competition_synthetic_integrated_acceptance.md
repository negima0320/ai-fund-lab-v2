# Phase31-G46 - Refined Capital Competition Synthetic Integrated Acceptance

Task type: READ-ONLY / TEST-ONLY INTEGRATED ACCEPTANCE

Production implementation change: NO

Fresh run / resume / replay / Historical rerun / long Historical: NO

## Primary Judgment

PRIMARY_JUDGMENT =
PHASE31_G46_REFINED_CAPITAL_COMPETITION_SYNTHETIC_INTEGRATED_ACCEPTANCE_PASS

G46 accepts the G40-G45 refined capital competition architecture as a coherent
synthetic integrated system. The test-only acceptance harness verifies that
Market Quality evidence, Risk Pacing, Opportunity Quality, Cash optionality,
pre-final Market x Candidate x Cash interaction, ADD / re-entry, lot
reconsideration, Runtime lineage persistence, Pending reload, and
Execution/ledger projection remain connected without downstream capital
redecision.

No Strategy rule, Market Quality, Risk Pacing, Opportunity Quality, Cash,
ADD/re-entry/lot, Runtime lineage, Position Sizing, PM, SELL, Safety, config,
threshold, or parameter behavior was changed.

## Evidence Read

Read / inspected:

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g38_economically_binding_risk_pacing_market_candidate_cash_interaction_architecture_refinement.md`
- `docs/phase_reports/phase31_g39_opportunity_quality_true_cash_competition_implementation_planning.md`
- `docs/phase_reports/phase31_g40_opportunity_quality_producer_reachable_continuum_implementation.md`
- `docs/phase_reports/phase31_g41_true_cash_competitor_evidence_framework_implementation.md`
- `docs/phase_reports/phase31_g42_pre_final_market_candidate_cash_interaction_implementation.md`
- `docs/phase_reports/phase31_g43_risk_pacing_economic_binding_activation.md`
- `docs/phase_reports/phase31_g44_add_reentry_lot_reconsideration_binding_integration.md`
- `docs/phase_reports/phase31_g45_refined_capital_decision_lineage_runtime_persistence_integration.md`
- G40-G45 focused tests

## Test-Only Addition

Added:

- `tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py`

Coverage added:

- authority uniqueness and legacy non-binding checks
- full refined Opportunity Quality reachability
- same-candidate market sensitivity
- same-market candidate sensitivity
- Cash as true competitor
- brake -> redeployment -> rebrake reversibility
- CAUTIOUS strong exception
- ADD competition
- re-entry competition
- lot reconsideration to security or Cash
- no forced deployment after lot/cap failure
- Runtime/Pending/Execution ledger refined lineage roundtrip
- missing evidence fail-closed and forbidden input preservation

## Verification

G46 integrated acceptance tests:

```bash
python3 -m pytest tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py
```

Result:

```text
6 passed
```

Focused G30/G40-G46 + Strategy/Runtime/Pending/Submit/Execution/basis
regression:

```bash
python3 -m pytest tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py tests/runtime_v2/test_phase31_g30_authority_lineage.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/runtime_v2/test_phase13_p_pending_reader_writer.py tests/runtime_v2/test_phase13_q_ledger_projection.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py
```

Result:

```text
373 passed
```

PY_COMPILE = PASS

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_g46 python3 -m py_compile tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py
```

GIT_DIFF_CHECK = PASS

```bash
git diff --check -- tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py
```

## Required Summary Output

PRIMARY_JUDGMENT =
PHASE31_G46_REFINED_CAPITAL_COMPETITION_SYNTHETIC_INTEGRATED_ACCEPTANCE_PASS

G38_ARCHITECTURE_CONFORMANCE =
PASS

MARKET_QUALITY_OWNER_COUNT =
1

RISK_PACING_OWNER_COUNT =
1

OPPORTUNITY_QUALITY_OWNER_COUNT =
1

CASH_COMPETITOR_OWNER_COUNT =
1

FINAL_CAPITAL_WINNER_OWNER_COUNT =
1

DISCRETE_QUANTITY_OWNER_COUNT =
1

DOWNSTREAM_CAPITAL_REDECISION_OWNER_COUNT =
0

CANONICAL_REFINED_CAPITAL_PATH_COUNT =
1

PERMANENT_LEGACY_FALLBACK_COUNT =
0

LEGACY_NON_BINDING_DECISION_AUTHORITY_COUNT =
0

STRONG_REACHABLE =
YES

COMPARABLE_HIGH_REACHABLE =
YES

COMPARABLE_MARGINAL_REACHABLE =
YES

WEAK_VALID_REACHABLE =
YES

INSUFFICIENT_REACHABLE =
YES

BLOCKED_REACHABLE =
YES

SAME_CANDIDATE_MARKET_SENSITIVITY =
PASS

SAME_MARKET_CANDIDATE_SENSITIVITY =
PASS

CASH_EXISTS_WITH_VALID_SECURITY =
YES

CASH_CAN_BEAT_VALID_SECURITY =
YES

SECURITY_CAN_BEAT_CASH =
YES

CASH_IS_NOT_RESIDUAL_ONLY =
YES

INTEGRATED_BRAKE_SCENARIO =
PASS

INTEGRATED_STRONG_EXCEPTION_SCENARIO =
PASS

INTEGRATED_BRAKE_TO_RECOVERY_REDEPLOYMENT =
PASS

INTEGRATED_REBRAKING_AFTER_RECOVERY =
PASS

CASH_WIN_DOES_NOT_CREATE_PERMANENT_DEPLOYMENT_BAN =
YES

SECURITY_WIN_DOES_NOT_BYPASS_LATER_CAUTION =
YES

INTEGRATED_ADD_COMPETITION =
PASS

INTEGRATED_REENTRY_COMPETITION =
PASS

INTEGRATED_LOT_RECONSIDERATION =
PASS

LOT_OR_CAP_FAILURE_DOES_NOT_FORCE_NEXT_SECURITY =
YES

FINAL_NO_DEPLOYABLE_ONLY_AFTER_CANONICAL_COMPETITION_AND_RECONSIDERATION =
YES

POSITION_SIZING_REMAINS_ONLY_DISCRETE_QUANTITY_OWNER =
YES

PC_QUANTITY_RECOMPUTATION_COUNT =
0

RUNTIME_REFINED_CAPITAL_REDECISION_COUNT =
0

PENDING_REFINED_LINEAGE_ROUNDTRIP =
PASS

SECURITY_WINNER_SUBMIT_PATH =
PASS

CASH_WINNER_NO_SECURITY_SUBMIT =
PASS

REFINED_LINEAGE_EXECUTION_LEDGER_PERSISTENCE =
PASS

ACCOUNTING_BASIS_INTEGRATED_REGRESSION =
PASS

BUY_SELL_INDEPENDENCE_INTEGRATED =
PASS

RISK_PACING_EXISTING_HOLDING_FORCED_EXIT_COUNT =
0

SAFETY_AUTHORITY_INTEGRATED_REGRESSION =
PASS

FUTURE_PRICE_INPUT_COUNT =
0

FUTURE_RETURN_INPUT_COUNT =
0

FUTURE_FEATURE_INPUT_COUNT =
0

LATER_REGIME_INPUT_COUNT =
0

HISTORICAL_OUTCOME_DECISION_INPUT_COUNT =
0

PAPER_LEDGER_DECISION_INPUT_COUNT =
0

AUDIT_RESULT_DECISION_INPUT_COUNT =
0

INTEGRATED_AS_OF_CONTRACT =
PASS

INTEGRATED_MISSING_EVIDENCE_FAIL_CLOSED =
PASS

PRODUCTION_DEMO_HISTORICAL_REFINED_DECISION_CONTRACT_ALIGNED =
YES

ELIGIBLE_WEAK_UNREACHABLE_DEFECT =
CLOSED

COMPARABLE_AUTOMATIC_BYPASS_DEFECT =
CLOSED

CASH_RESIDUAL_ONLY_DEFECT =
CLOSED

RISK_PACING_AFTER_SELECTION_TOO_LATE_DEFECT =
CLOSED

CAUTIOUS_GRADUAL_NO_ECONOMIC_DIFFERENCE_DEFECT =
CLOSED

RISK_PACING_EFFECTIVELY_NON_BINDING_DEFECT =
CLOSED

REFINED_CAPITAL_ECONOMIC_SENSITIVITY =
PASS

BRAKE_CAPABILITY =
PASS

REDEPLOYMENT_CAPABILITY =
PASS

REBRAKE_CAPABILITY =
PASS

STRONG_EXCEPTION_CAPABILITY =
PASS

OUTCOME_DERIVED_THRESHOLD_COUNT =
0

OUTCOME_DERIVED_WEIGHT_COUNT =
0

OUTCOME_DERIVED_CLASS_BOUNDARY_COUNT =
0

G46_INTEGRATED_ACCEPTANCE_TESTS =
PASS

G46_FOCUSED_REGRESSION =
PASS

PY_COMPILE =
PASS

GIT_DIFF_CHECK =
PASS

IMPLEMENTATION_CHANGE_EXECUTED =
NO

CONFIG_CHANGE_EXECUTED =
NO

THRESHOLD_CHANGE_EXECUTED =
NO

PARAMETER_TUNING_EXECUTED =
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

NEXT_TASK_RECOMMENDATION =
PHASE31_G47_PRODUCTION_EQUIVALENT_REFINED_CAPITAL_COMPETITION_FINAL_E2E_ACCEPTANCE
