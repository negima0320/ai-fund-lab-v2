# Phase31-G50 - Final Capital Winner to Position Sizing to Runtime Planning Connectivity Repair

Task type: IMPLEMENTATION / AUTHORITATIVE CONNECTIVITY REPAIR.

No Market Quality, Risk Pacing, Opportunity Quality, Cash competitor, G43
binding matrix, ADD / re-entry / lot semantics, Candidate eligibility, PM SELL,
Safety, threshold, parameter, config, or fixture semantics were changed. No
fresh-run, resume, replay, Historical rerun, or long Historical was executed.

## Judgment

`PRIMARY_JUDGMENT = PHASE31_G50_FINAL_CAPITAL_WINNER_RUNTIME_BINDING_CONNECTIVITY_REPAIRED_ACCEPTED`

G49's defect is repaired at the authority boundary. Portfolio Construction now
materializes a canonical `portfolio_construction.canonical_deployment_set.v1`
owned by Portfolio Construction. Position Sizing consumes that set before
discrete sizing. Runtime Planning consumes the already-bound Position Sizing
output and preserves the deployment-set lineage without recomputing Cash
preference or capital competition.

## Root Cause

`G50_ROOT_CAUSE = SIZING_USES_PRE_INTERACTION_PORTFOLIO_MEMBERS + PC_WINNER_EVIDENCE_ONLY_NOT_DECISION_INPUT`

Pre-G50, Portfolio Construction produced correct `capital_competition` evidence,
including final winner and defeated competitor lineage, but Position Sizing read
the full `portfolio_members` row set as sizing input. Pre-binding target weights
therefore still created positive NEW_BUY / ADD quantity candidates even when
the canonical PC winner was Cash. Runtime Planning then mapped those Position
Sizing quantities into BUY plans. The final winner lineage was preserved, but
lineage persistence was not executable decision binding.

## Implementation Summary

- Added `canonical_deployment_set` to Portfolio Construction capital
  competition output.
- Declared winner cardinality as `SINGLE`, matching the existing G43/G48
  interaction winner implementation.
- Added Position Sizing input filtering from the canonical deployment set.
- Cash winner now leaves the incremental deployment security set empty.
- Security winner now admits only the selected deployment security to positive
  incremental sizing.
- Defeated NEW_BUY / ADD / re-entry rows are retained for evidence but their
  positive incremental target, notional, and quantity are zeroed before sizing.
- Existing HOLD baselines and PM-owned SELL / REDUCE / EXIT remain independent.
- Runtime Planning lineage now records the canonical deployment set and Position
  Sizing consumption status, without downstream redecision.
- Permanent SoT now states that final capital winner binding must occur before
  discrete sizing and that lineage persistence is not decision binding.

## Acceptance Evidence

G50 focused regression:

```bash
python3 -m pytest tests/strategy/test_phase31_g50_final_capital_winner_binding.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g46_refined_capital_competition_integrated_acceptance.py tests/runtime_v2/test_phase31_g45_refined_capital_lineage.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase13_p_pending_reader_writer.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase13_q_ledger_projection.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py -q
```

Result: `363 passed in 5.52s`.

Py compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_g50 python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/runtime_planning.py tests/strategy/test_phase31_g50_final_capital_winner_binding.py
```

Result: `PASS`.

Diff check:

```bash
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/runtime_planning.py docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md docs/02_architecture/portfolio_construction_and_position_sizing_contract.md tests/strategy/test_phase31_g50_final_capital_winner_binding.py
```

Result: `PASS`.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G50_FINAL_CAPITAL_WINNER_RUNTIME_BINDING_CONNECTIVITY_REPAIRED_ACCEPTED`

`G50_ROOT_CAUSE = SIZING_USES_PRE_INTERACTION_PORTFOLIO_MEMBERS + PC_WINNER_EVIDENCE_ONLY_NOT_DECISION_INPUT`

`PRE_G50_PC_TO_SIZING_CONNECTIVITY_TRACE_COMPLETE = YES`

`CANONICAL_DEPLOYMENT_SET_IMPLEMENTED = YES`

`CANONICAL_DEPLOYMENT_SET_OWNER = PORTFOLIO_CONSTRUCTION`

`CASH_WINNER_SECURITY_SIZING_INPUT_COUNT = 0`

`DEFEATED_SECURITY_SIZING_INPUT_COUNT = 0`

`POSITION_SIZING_REMAINS_DISCRETE_QUANTITY_OWNER = YES`

`POSITION_SIZING_CAPITAL_WINNER_AUTHORITY = NO`

`PRE_BINDING_TARGET_CAN_CREATE_INCREMENTAL_QUANTITY = NO`

`EXISTING_HOLDINGS_PRESERVED_WHEN_CASH_WINS = YES`

`CASH_WINNER_FORCES_EXISTING_EXIT = NO`

`BUY_CASH_WINNER_BLOCKS_SELL = NO`

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

`ADD_LOST_TO_CASH_SIZING_QUANTITY = 0`

`ADD_WINNER_SIZING_PATH = PASS`

`NEW_BUY_LOST_TO_CASH_SIZING_QUANTITY = 0`

`NEW_BUY_WINNER_SIZING_PATH = PASS`

`REENTRY_LOST_TO_CASH_SIZING_QUANTITY = 0`

`LOT_RECONSIDERATION_AUTHORITY_PRESERVED = YES`

`LOT_RECONSIDERATION_CASH_WINNER_SECURITY_ORDER_COUNT = 0`

`LOT_RECONSIDERATION_TERMINATION_CONTRACT = PASS`

`RUNTIME_PLANNING_USES_CANONICAL_SIZED_DEPLOYMENT_SET = YES`

`RUNTIME_REINTRODUCES_DEFEATED_SECURITY_COUNT = 0`

`PENDING_REINTRODUCES_DEFEATED_SECURITY_COUNT = 0`

`SUBMIT_REINTRODUCES_DEFEATED_SECURITY_COUNT = 0`

`EXECUTION_CAN_FILL_DEFEATED_SECURITY_COUNT = 0`

`G49_2022_10_03_DEFECT_REPRODUCTION_REPAIRED = PASS`

`G49_2022_10_20_STRONG_EXCEPTION_PATH = PASS`

`G49_2022_10_25_REDEPLOYMENT_PATH = PASS`

`G49_2022_10_27_REBRAKE_PATH = PASS`

`CAPITAL_WINNER_CARDINALITY_CONTRACT = SINGLE`

`UNSELECTED_SECURITY_ORDER_COUNT = 0`

`SECOND_CAPITAL_COMPETITION_AUTHORITY_COUNT = 0`

`DOWNSTREAM_CASH_REDECISION_COUNT = 0`

`DEPLOYMENT_SET_LINEAGE_COMPLETE = YES`

`PERMANENT_SOT_PC_TO_SIZING_BINDING_EXPLICIT = YES`

`LINEAGE_DECISION_BINDING_DISTINCTION_DOCUMENTED = YES`

`ACCOUNTING_BASIS_REGRESSION = PASS`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_DECISION_INPUT_COUNT = 0`

`PAPER_LEDGER_DECISION_INPUT_COUNT = 0`

`AUDIT_RESULT_DECISION_INPUT_COUNT = 0`

`EVIDENCE_ARTIFACT_AS_STRATEGY_DATA_SOURCE_COUNT = 0`

`G50_FOCUSED_REGRESSION = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`PARAMETER_TUNING_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`NEXT_TASK_RECOMMENDATION = PHASE31_G51_FINAL_CAPITAL_WINNER_BINDING_PRODUCTION_E2E_REACCEPTANCE`
