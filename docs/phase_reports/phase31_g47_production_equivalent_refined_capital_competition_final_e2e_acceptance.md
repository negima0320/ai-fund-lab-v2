# Phase31-G47 — Production-Equivalent Refined Capital Competition Final E2E Acceptance

Task type: READ-ONLY / TEST-ONLY FINAL PRODUCTION-EQUIVALENT ACCEPTANCE.

Implementation, Strategy, Market Context, Risk Pacing, Opportunity Quality, Cash competition, ADD / Re-entry / lot, Runtime lineage, Position Sizing, PM, SELL, Safety, config, thresholds, parameters, and fixtures were not changed. No fresh-run, resume, replay, Historical rerun, or long Historical was executed.

## Judgment

`PRIMARY_JUDGMENT = PHASE31_G47_PRODUCTION_EQUIVALENT_REFINED_CAPITAL_COMPETITION_FINAL_E2E_PASS`

The refined capital competition path is connected to the actual Runtime v2 daily entry path used by historical, demo, and production modes. The implementation evidence shows a single common decision contract: mode-specific runtime environments provide evidence and side-effect capability boundaries, while Strategy/Portfolio Construction owns the business decision chain and Runtime consumers persist the resulting authority lineage without recomputing or reclassifying the capital winner.

## Evidence Inspected

- Current architecture SoT: `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- Runtime architecture SoT: `docs/02_architecture/runtime_architecture_v2.md`
- Required reports G38-G46.
- Actual runtime entry: `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- Capital competition and binding interaction: `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- Runtime planning lineage: `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- Runtime planning consumer: `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- Pending persistence/reload: `src/ai_fund_lab_v2/runtime_v2/pending/models.py`, `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- Submit command and ledger persistence: `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`, `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- Execution/ledger projection: `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py`
- Focused integrated regression: 426 tests passed.

## Entry-Point Inventory

The actual common daily entry point is `run_daily_operation.py`. It accepts `--mode demo`, `--mode historical`, and `--mode production`, rejects `simulation` as a formal Runtime environment, and applies mode-specific operational guards. The same active Runtime sequence reaches:

- Strategy Planning Authority via `activate_strategy_planning_authority(...)`
- Submit via `run_submit_pipeline(...)`
- Execution via `run_execution_readonly_pipeline(...)`

Architecture SoT states that historical, demo, and production differ by Current / Ledger / Safety / broker evidence boundaries, not by a separate historical-only policy branch.

## Connectivity Findings

Portfolio Construction creates the canonical `capital_competition` evidence, including the canonical Cash competitor, `market_candidate_cash_interaction.v1`, and final capital winner fields. The interaction evidence records canonical Opportunity Quality, authoritative Risk Pacing, Cash evidence consumption, zero legacy late Risk Pacing authority, zero Cash override, zero outcome-derived rules, and no future / paper ledger / audit-result / MFE-MAE inputs.

Runtime Planning embeds `refined_capital_decision_lineage.v1` in `strategy_authority_lineage`, marks Strategy / Portfolio Construction as the single business decision owner, and sets all downstream recomputation and reclassification counters to zero. Planning Authority copies item lineage into Pending items and order-plan lineage without recomputing the winner. Submit commands copy Pending item lineage. Submit ledger records and broker-readonly execution projection preserve the same lineage and hash.

## Legacy / Fallback Classification

Remaining legacy strings such as `ELIGIBLE_STRONG`, `ELIGIBLE_COMPARABLE`, and `ELIGIBLE_WEAK` are classified as compatibility evidence, aliases, tests, or historical phase remnants. The active G42-G46 binding path records `legacy_marginal_class_used_as_interaction_authority = False`, `legacy_late_risk_pacing_decision_authority_count = 0`, and `legacy_cash_winner_override_count = 0`.

Runtime fallback fields that remain are guard/audit evidence or fail-closed validation flags. No refined capital path fallback was found that allows missing Market Quality, Opportunity Quality, Cash evidence, Risk Pacing, or Runtime lineage to silently reconstruct an authoritative winner from latest state or old capital semantics.

## Real-Artifact Fixture Dependency Audit

The G47 mandatory acceptance suite is synthetic / unit / integration focused and does not require existing long-run artifacts. Repo search found older phase tests that reference fixed runtime-test paths, including C0D/F1D/B6/B8 style historical artifact audits; these are classified as `OPTIONAL_REAL_RUN_FIXTURE` for G47 because this task forbids fresh/resume/replay/Historical rerun and requires production-equivalent connectivity, not real-run performance characterization. No `REQUIRED_FOR_G47` test was excluded because of missing artifacts.

## Focused Regression

Command executed:

```bash
python3 -m pytest tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase13_p_pending_reader_writer.py tests/runtime_v2/test_phase13_q_ledger_projection.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py
```

Result: `426 passed in 6.47s`.

Py compile command executed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_g47 python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/strategy/runtime_planning.py src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py src/ai_fund_lab_v2/runtime_v2/submit/guards.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py
```

Result: `PASS`.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G47_PRODUCTION_EQUIVALENT_REFINED_CAPITAL_COMPETITION_FINAL_E2E_PASS`

`ACTUAL_RUNTIME_ENTRY_POINT_INVENTORY_COMPLETE = YES`

`PRODUCTION_EQUIVALENT_REFINED_PATH_CONNECTED = YES`

`HISTORICAL_REFINED_PATH_CONNECTED = YES`

`DEMO_REFINED_PATH_CONNECTED = YES`

`PRODUCTION_REFINED_PATH_CONNECTED = YES`

`PRODUCTION_DEMO_HISTORICAL_COMMON_DECISION_CONTRACT = PASS`

`MARKET_QUALITY_OWNER_COUNT = 1`

`RISK_PACING_OWNER_COUNT = 1`

`OPPORTUNITY_QUALITY_OWNER_COUNT = 1`

`CASH_COMPETITOR_OWNER_COUNT = 1`

`FINAL_CAPITAL_WINNER_OWNER_COUNT = 1`

`DISCRETE_QUANTITY_OWNER_COUNT = 1`

`LOT_RECONSIDERATION_OWNER_COUNT = 1`

`DOWNSTREAM_CAPITAL_REDECISION_OWNER_COUNT = 0`

`LEGACY_ACTIVE_DECISION_CONSUMER_COUNT = 0`

`IMPLICIT_REFINED_PATH_FALLBACK_COUNT = 0`

`PRODUCTION_EQUIVALENT_MISSING_EVIDENCE_FAIL_CLOSED = PASS`

`MARKET_QUALITY_REAL_PRODUCTION_CONSUMER_CONNECTED = YES`

`RISK_PACING_REAL_PRODUCTION_CONSUMER_CONNECTED = YES`

`OPPORTUNITY_QUALITY_REAL_PRODUCTION_CONSUMER_CONNECTED = YES`

`CASH_COMPETITOR_REAL_PRODUCTION_CONSUMER_CONNECTED = YES`

`BINDING_INTERACTION_REAL_PRODUCTION_CONSUMER_CONNECTED = YES`

`CANONICAL_WINNER_TO_POSITION_SIZING_CONNECTED = YES`

`SIZING_EVIDENCE_TO_PC_RECONSIDERATION_CONNECTED = YES`

`RECONSIDERATION_TO_CANONICAL_FINAL_WINNER_CONNECTED = YES`

`FINAL_WINNER_TO_RUNTIME_PLANNING_CONNECTED = YES`

`REFINED_LINEAGE_RUNTIME_PLANNING_CONNECTED = YES`

`REFINED_LINEAGE_PENDING_CONNECTED = YES`

`REFINED_LINEAGE_SUBMIT_CONNECTED = YES`

`REFINED_LINEAGE_EXECUTION_LEDGER_CONNECTED = YES`

`PRODUCTION_EQUIVALENT_CASH_WINNER_PATH = PASS`

`PRODUCTION_EQUIVALENT_SECURITY_WINNER_PATH = PASS`

`PRODUCTION_EQUIVALENT_ADD_PATH = PASS`

`PRODUCTION_EQUIVALENT_REENTRY_PATH = PASS`

`PRODUCTION_EQUIVALENT_LOT_RECONSIDERATION_PATH = PASS`

`PRODUCTION_EQUIVALENT_BUY_SELL_INDEPENDENCE = PASS`

`RISK_PACING_FORCED_EXISTING_POSITION_EXIT_COUNT = 0`

`PRODUCTION_EQUIVALENT_SAFETY_BOUNDARY = PASS`

`SUBMIT_CASH_VALIDATION_PRESERVED = YES`

`SUBMIT_CASH_VALIDATION_REDECIDES_STRATEGY_WINNER = NO`

`PRODUCTION_EQUIVALENT_ACCOUNTING_BASIS = PASS`

`PRODUCTION_EQUIVALENT_TEMPORAL_CONTRACT = PASS`

`FUTURE_PRICE_DECISION_INPUT_COUNT = 0`

`FUTURE_RETURN_DECISION_INPUT_COUNT = 0`

`FUTURE_FEATURE_DECISION_INPUT_COUNT = 0`

`LATER_REGIME_DECISION_INPUT_COUNT = 0`

`MFE_MAE_DECISION_INPUT_COUNT = 0`

`HISTORICAL_PERFORMANCE_DECISION_INPUT_COUNT = 0`

`PAPER_LEDGER_DECISION_INPUT_COUNT = 0`

`AUDIT_RESULT_DECISION_INPUT_COUNT = 0`

`TEST_RESULT_DECISION_INPUT_COUNT = 0`

`EVIDENCE_ARTIFACT_AS_STRATEGY_DATA_SOURCE_COUNT = 0`

`G46_BRAKE_CAPABILITY_REGRESSION = NO`

`G46_REDEPLOYMENT_CAPABILITY_REGRESSION = NO`

`G46_REBRAKE_CAPABILITY_REGRESSION = NO`

`G46_STRONG_EXCEPTION_REGRESSION = NO`

`G43_BINDING_MATRIX_BYPASS_COUNT = 0`

`RESIDUAL_CAPITAL_BINDING_BYPASS_COUNT = 0`

`DOWNSTREAM_RISK_PACING_RECOMPUTATION_COUNT = 0`

`DOWNSTREAM_OPPORTUNITY_QUALITY_RECOMPUTATION_COUNT = 0`

`DOWNSTREAM_CASH_COMPETITION_RECOMPUTATION_COUNT = 0`

`DOWNSTREAM_CAPITAL_WINNER_RECOMPUTATION_COUNT = 0`

`DOWNSTREAM_CAPITAL_RECLASSIFICATION_COUNT = 0`

`PRODUCTION_EQUIVALENT_LINEAGE_ROUNDTRIP = PASS`

`RESTART_RELOAD_REFINED_DECISION_EQUIVALENCE = PASS`

`REFINED_DECISION_PERSISTENCE_IDEMPOTENCY = PASS`

`G47_PRODUCTION_EQUIVALENT_REGRESSION = PASS`

`REAL_ARTIFACT_FIXTURE_DEPENDENCY_AUDIT = COMPLETE`

`HISTORICAL_PROFITABILITY_USED_AS_G47_GATE = NO`

`EXISTING_PIT_ACTIVATION_AUDIT_READY = YES`

`FRESH_HISTORICAL_BEFORE_EXISTING_PIT_ACTIVATION_AUDIT_ALLOWED = NO`

`IMPLEMENTATION_CHANGE_EXECUTED = NO`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`PARAMETER_TUNING_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = PHASE31_G48_EXISTING_PIT_REFINED_CAPITAL_ACTIVATION_REVERSIBILITY_AUDIT`
