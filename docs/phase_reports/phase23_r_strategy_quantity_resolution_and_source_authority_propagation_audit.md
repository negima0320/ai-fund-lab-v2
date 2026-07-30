# Phase23-R: Strategy Quantity Resolution and Source Authority Propagation Audit

## Primary Judgment

`PHASE23_R_CORPORATE_EVENT_SOURCE_CONNECTION_GAP_CONFIRMED`

## Secondary Judgment

- `PHASE23_R_STRATEGY_REVIEW_PROPAGATION_CONTRACT_GAP_CONFIRMED`
- `PHASE23_R_PARTIAL_REPAIR_QUANTITY_RESOLUTION_BLOCKER_REMAINS`
- `PHASE23_R_CONSUMER_OBSERVABILITY_REPAIRED_SHORT_VALIDATION_PASS`
- `NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

## Target Run

`runtime-test-historical-smoke-20260729T003614334924Z` stopped on `2026-07-06:morning` with `exit_code=20`, `final_state=REVIEW_REQUIRED`, reason `morning pipeline review required: strategy_planning_authority_unresolved`.

Confirmed normal path reached Market Refresh, Historical PIT input, Historical Evaluation Authority, fixed Accepted Generation, Candidate AI, Opportunity AI, Market Context, Historical Safety Authority, Strategy artifact generation, and Strategy Planning Authority activation.

## Q1. Corporate Event Authority Contract

Corporate Event Authority is a Production-common PIT fact authority. It provides event facts and coverage evidence only; it must not make BUY/SELL or quantity decisions. The PASS condition requires valid source authority and available source coverage. Missing optional event-source datasets are not equivalent to no events.

Observed `2026-07-06`:

- `producer_result_status = REVIEW_REQUIRED`
- `coverage_status = PARTIAL`
- `source_authority_status = VALID`
- reason codes: `corporate_event_source_coverage_incomplete, jquants_corporate_actions_not_implemented_or_missing, jquants_earnings_schedule_not_implemented_or_missing, jquants_financial_statements_not_implemented_or_missing`

## Q2. J-Quants Input Reality

`.runtime/operations/jquants/raw/jquants` contains `equities_bars_daily`, `listed_issues`, and `trading_calendar`. It does not contain `corporate_actions`, `earnings_calendar`, or `statements` data required by the Corporate Event full-coverage contract.

This is a source connection/materialization gap. It was not converted to PASS.

## Q3. REVIEW Propagation Contract

The current chain is:

`corporate_event REVIEW_REQUIRED -> SOURCE_REVIEW_REQUIRED -> portfolio_policy / portfolio_construction / position_management / capital_deployment -> dynamic_position_count / dynamic_cash_exposure -> position_sizing -> runtime_planning consumer`.

This propagation is fail-closed. The open design risk is that Corporate Event PARTIAL coverage currently reviews the whole chain rather than symbol-scoped eligibility. That requires a separate source/eligibility contract repair, not a fixed fallback.

## Q4. Quantity Resolution Direct Condition

Phase23-I consumer resolves quantity only when a Strategy plan has:

- BUY/SELL intent requiring quantity
- PIT price greater than zero
- matching Position Sizing row
- `target_notional`, `incremental_buy_notional`, or sell notional large enough to round to a 100-share lot

Observed:

- Runtime plans: `50`
- quantity required: `50`
- quantity unresolved: `50`
- Position Sizing rows: `0`
- pending items generated: `0`

Direct blocker: Position Sizing produced no rows because upstream count/exposure/policy remain review-required.

## Q5. Phase21 Dynamic Policy Regression Audit

No fixed Strategy fallback to 5 positions or 850,000 JPY was introduced. Dynamic Position Count and Dynamic Cash/Exposure remain unresolved/null under upstream review. The legacy runtime policy values are only historical inventory/context and were not used to force Strategy quantities.

## Q6. AI Lifecycle Review Impact

AI Lifecycle is not the direct quantity blocker in this run:

- `buy_ai_status = PASS`
- `ai_lifecycle_gate_decision = REVIEW_REQUIRED`
- `ai_lifecycle_gate_trading_permission_effect = NONE`
- `ai_lifecycle_gate_block_buy = False`

The direct stop is `strategy_planning_authority_unresolved` caused by unresolved quantities.

## Q7. Consumer Observability

Confirmed ambiguity: `strategy_shadow_summary.json` said `strategy_planning_authority_consumer_called=false`, while Morning manifest showed `strategy_planning_authority_active=true` and the Phase23-I stage evidence existed.

Repair applied for future runs: after `activate_strategy_planning_authority`, daily Strategy summary is annotated with the StrategyPlanningAuthorityResult, and run-level shadow indexes aggregate `strategy_planning_authority_consumer_called` / `active_runtime_consumer_eligibility` from daily summaries.

This is observability-only. It does not alter quantities, status semantics, exit codes, Runtime Switch, or Broker Write.

## Production Commonality

Production, Demo, and Historical continue to use the same Strategy Planning Authority consumer. No historical-only ignore, fixed quantity, latest fallback, Runtime Switch, or Broker Write was introduced.

## Evidence

Evidence directory: `reports/phase23_r_strategy_quantity_resolution_and_source_authority_propagation_audit/`

Required evidence files were generated:

- `corporate_event_authority_contract_audit.json`
- `historical_corporate_event_source_inventory.json`
- `corporate_event_consumer_resolution_audit.json`
- `strategy_review_propagation_graph.json`
- `quantity_resolution_input_audit.json`
- `quantity_resolution_direct_condition.json`
- `phase21_dynamic_policy_regression_audit.json`
- `ai_lifecycle_review_effect_audit.json`
- `strategy_consumer_observability_audit.json`
- `short_validation_results.json`
- `modified_files.json`

## 10BD Gate

`NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

Reason: Corporate Event source connection/materialization gap remains, and quantity authority inputs remain unresolved. 10BD was not run.

## Short Validation

- compile: PASS
- targeted regression: `42 passed in 2.82s`
- JSON validation: PASS
- long runtime / 10BD: not run
