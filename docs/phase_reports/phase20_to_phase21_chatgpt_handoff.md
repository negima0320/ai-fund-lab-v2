# Phase20 to Phase21 ChatGPT Handoff

## Handoff Status

`PHASE20_CLOSURE_COMPLETE_WITH_PERFORMANCE_IMPROVEMENT_REQUIRED`

Phase21 can start without waiting for the active 245BD run to finish. The 245BD final result must still be captured in Phase21-A.

The 245BD Historical Run is the primary diagnostic evidence source for Phase21, but it is not the sole acceptance period and must not be used in a way that introduces future leakage, performance-result imitation, or single-period overfitting.

## Core Interpretation

Phase20 should not be interpreted as a failed performance-improvement phase.

Phase20 established the boundary between:

- invalid performance caused by Historical Runtime authority defects
- valid Runtime replay with weak strategy performance

After BT / BU / BV / BW, corrected Bull and Range 20BD runs both passed Runtime and Lifecycle checks, yet both produced negative returns. This means Phase21 should focus on strategy and performance improvement while preserving Runtime, Safety, and PIT contracts.

## Formal Post-fix Evidence

### 5BD Runtime Revalidation

- run_id: `runtime-test-historical-extended-smoke-20260726T023256813084Z`
- period: `2022-09-01` to `2022-09-07`
- status: `PASS`
- return_rate: `-1.758%`
- BUY execution: `4`
- SELL execution: `2`
- PM: `ADD 3`, `EXIT 1`, `HOLD 11`, `REDUCE 1`
- review/block findings: `0`

### Bull 20BD

- run_id: `runtime-test-historical-extended-smoke-20260726T024433336288Z`
- period: `2026-03-24` to `2026-04-20`
- status: `PASS`
- final_equity: `973,280`
- return: `-26,720`
- return_rate: `-2.672%`
- BUY execution: `5`
- SELL execution: `9`
- PM: `ADD 7`, `EXIT 3`, `HOLD 25`, `REDUCE 6`
- review/block findings: `0`

### Range 20BD

- run_id: `runtime-test-historical-extended-smoke-20260726T043951394342Z`
- period: `2022-08-01` to `2022-08-29`
- status: `PASS`
- final_equity: `989,310`
- return: `-10,690`
- return_rate: `-1.069%`
- BUY execution: `3`
- SELL execution: `2`
- PM: `ADD 2`, `EXIT 2`, `HOLD 24`, `REDUCE 0`
- review/block findings: `0`

### Active 245BD

- run_id: `runtime-test-historical-extended-smoke-20260726T053732539035Z`
- requested period: `2022-09-01` to `2023-08-30`
- requested_business_days: `245`
- status: `RUNNING`
- completed_business_days: `188`
- latest_completed_business_date: `2023-06-08`
- next_job: `2023-06-09:market_refresh`

No final 245BD performance summary exists at handoff. Do not treat partial evidence as final performance.

When completed, this run should be certified as the primary Phase21 diagnostic dataset for:

- one-year profit structure
- PM decision contribution
- holding periods
- profit retention and profit disappearance
- loss expansion
- ADD / REDUCE / EXIT effect
- capital deployment and reinvestment
- cash and invested ratio
- position count and slot utilization
- BUY funnel drop-off
- symbol and sector concentration
- regime and benchmark comparison

## Closed Runtime Defects

- BT: Historical Morning Planning now uses run-scoped logical normalized OHLCV.
- BU: Historical Submit Corporate Action Guard now uses run-scoped logical raw OHLCV; BUY evidence no longer carries SELL-only broker available quantity review.
- BV: End-to-end Historical authority wiring reviewed; critical/unfixed high findings closed; Current Valuation now uses run-scoped logical normalized OHLCV.
- BW: Historical Data Readiness previous trading date now uses run-scoped trading calendar authority. `2022-08-12` previous trading date resolves to `2022-08-10`.

## Current Strategy Judgment

The current strategy is insufficient versus the annual `+50%` target.

Evidence:

- Bull 20BD return: `-2.672%`
- Range 20BD return: `-1.069%`
- Runtime/Lifecycle: PASS for both
- Review/block findings: `0`

This is a strategy-performance problem, not a confirmed Runtime failure.

## Phase21 Objective

Phase21 should improve the Japanese equities AI operation toward annual `+50%` while preserving:

- Runtime Contract
- Safety Contract
- PIT Authority
- No Future Leakage
- Fail-closed behavior
- Accepted Generation Authority

## Phase21 Starting Workstreams

1. 245BD Long-run Finalization and Diagnostic Dataset Certification: capture the active 245BD final result and certify the run-scoped evidence as Phase21 diagnostic data.
2. Performance Metric Completion: daily equity, drawdown, cash utilization, exposure, turnover, concentration, benchmark, sector, trade quality.
3. PM Attribution: HOLD / ADD / REDUCE / EXIT outcome quality.
4. Position Holding Attribution: campaign-level entry, peak, drawdown, exit, post-exit.
5. Capital Deployment Audit: actual invested ratio, cash ratio, max_positions constraint, reinvestment, slot reuse.
6. Candidate / Opportunity Ranking Quality: score vs forward return, executed vs non-executed eligible opportunities.
7. Improvement Experiment Contract: one changed variable per experiment, control/treatment, acceptance/rollback criteria.

## Guardrails

Do not:

- use future returns as decision-time evidence
- put PnL directly into model input
- tune only to Bull/Range outcomes
- discard unfavorable runs
- change multiple variables in one experiment
- add symbol-specific or date-specific exceptions
- weaken Broker Safety or Runtime fail-closed behavior

## First Phase21 Recommendation

Start with Phase21-A and Phase21-B:

1. Wait for the user to complete the 245BD run.
2. Record the final 245BD performance formally.
3. Certify the 245BD run-scoped diagnostic dataset.
4. Complete the missing metric authority map before changing PM, Candidate, Opportunity, or Capital logic.

Phase21-A deliverables should include:

- `docs/phase_reports/phase21_a_245bd_long_run_diagnostic_dataset_certification.md`
- `reports/phase_reports/phase21_a_245bd_long_run_diagnostic_dataset_certification.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/dataset_inventory.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/daily_portfolio_state.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/position_campaign_attribution.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/pm_decision_attribution.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/capital_deployment_timeline.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/execution_and_realized_slice_attribution.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/missing_metric_inventory.json`
- `reports/phase21_a_245bd_long_run_diagnostic_dataset_certification/diagnostic_dataset_certification.json`

The 245BD data may drive diagnosis, counterfactual analysis, attribution, hypothesis generation, experiment design, and holdout planning. It must not become Runtime input, training leakage, direct threshold imitation, or the only acceptance period.

## Required Reading

- `docs/phase_reports/phase20_final_summary_and_phase21_handoff.md`
- `docs/phase_reports/phase20_bv_historical_runtime_end_to_end_authority_wiring_review.md`
- `docs/phase_reports/phase20_bw_historical_data_readiness_previous_trading_date_authority_fix.md`
- `docs/phase_reports/phase20_bu_historical_submit_corporate_action_preflight_regression.md`
- `docs/phase_reports/phase20_bt_5bd_post_fix_zero_trade_regression.md`
- `docs/phase_reports/phase20_bn_three_regime_trading_attribution_audit.md`
- `docs/phase_reports/phase20_bo_final_independent_architecture_objective_regression_review.md`
- `docs/phase_reports/phase20_bm_run_scoped_final_performance_authority.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`
