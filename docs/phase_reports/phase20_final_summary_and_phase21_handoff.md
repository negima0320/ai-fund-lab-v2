# Phase20 Final Summary and Phase21 Handoff

## Primary Judgment

`PHASE20_CLOSURE_COMPLETE_WITH_PERFORMANCE_IMPROVEMENT_REQUIRED`

Supporting judgments:

- `PHASE20_RUNTIME_CONTRACT_REVALIDATED`
- `PHASE20_HISTORICAL_REPLAY_20BD_PASS`
- `PHASE20_HISTORICAL_AUTHORITY_WIRING_DEFECTS_CLOSED`
- `PHASE20_STRATEGY_TARGET_NOT_MET`
- `PHASE20_PHASE21_PERFORMANCE_IMPROVEMENT_REQUIRED`

## Phase20 Positioning

Phase20 started as a Performance Improvement preparation phase. During the work, multiple Historical Runtime Authority Wiring and Temporal Contract defects were found before strategy improvement could be judged safely.

The final role of Phase20 was to separate these two explanations:

```text
Runtime is broken, therefore performance evidence is invalid.
```

from:

```text
Runtime is correctly replaying, but current strategy performance is insufficient.
```

After BT / BU / BV / BW, the corrected Bull and Range 20BD runs are Runtime PASS and Lifecycle PASS. Therefore, current underperformance cannot be explained only as a Runtime defect.

## Old Baseline Treatment

The initial 20BD baseline showed:

- initial_equity: `1,000,000`
- final_equity: `955,100`
- return: `-44,900`
- return_rate: `-4.49%`
- max_drawdown: `-86,300 / -8.47%`
- BUY executions: `5`
- SELL executions: `7`

This was produced before the Historical Authority Wiring fixes. It remains reference evidence only and is not a formal post-fix Performance Baseline.

Old Bull / Bear / Range results before BT / BU / BV / BW are also reference evidence only.

## Runtime Defects Closed

### Phase20-BT Morning Planning Price Authority

Historical Morning Planning was using operations canonical normalized OHLCV instead of run-scoped Historical logical normalized OHLCV. The fix wires:

```text
Run-scoped Historical logical_input_manifest.json
→ logical_paths.normalized_ohlcv
→ Morning Planning
```

### Phase20-BU Submit Corporate Action Authority

Historical Submit Preflight Corporate Action Guard was using operations canonical raw OHLCV instead of run-scoped Historical logical raw OHLCV. Correct run-scoped raw OHLCV showed no corporate action event for the investigated symbols.

BUY evidence contamination from SELL-only broker available quantity was also fixed:

```text
broker_available_quantity_source = not_applicable_buy
broker_available_quantity_review_required = false
```

SELL broker available quantity guard remains in force.

### Phase20-BV End-to-End Historical Authority Wiring Review

Reviewed stages: `24`

Authority types: `19`

Result:

- Producer/Consumer mismatch: `3`
- Invalid fallback: `3`
- Temporal defect remaining: `0`
- BUY/SELL branch contamination: `1 fixed`
- Critical remaining: `0`
- Unfixed High: `0`

BV also fixed Current Valuation to prefer the run-scoped logical normalized OHLCV authority.

### Phase20-BW Historical Previous Trading Date Authority

Range 20BD stopped at `2022-08-12` because Data Readiness used fallback calendar and resolved previous trading date as `2022-08-11`.

J-Quants run-scoped calendar evidence shows:

```text
2022-08-11 HolDiv = 0
2022-08-12 previous trading date = 2022-08-10
```

Historical Data Readiness now resolves the calendar in this order:

1. Run-scoped Historical logical input manifest `logical_paths.trading_calendar`
2. Historical as-of view `trading_calendar` authority
3. Explicit Historical contract calendar

Invalid or missing Historical authority fails closed. Production/Demo calendar behavior is unchanged.

## Post-fix Runtime Revalidation

### 5BD Historical

- run_id: `runtime-test-historical-extended-smoke-20260726T023256813084Z`
- period: `2022-09-01` to `2022-09-07`
- business_days: `5`
- status: `PASS`
- final_equity: `982,420`
- return: `-17,580`
- return_rate: `-1.758%`
- realized_pnl: `-7,200`
- unrealized_pnl: `-10,380`
- BUY plan: `8`
- SELL plan: `2` derived from PM REDUCE/EXIT
- BUY execution: `4`
- SELL execution: `2`
- PM: `ADD 3`, `EXIT 1`, `HOLD 11`, `REDUCE 1`
- current_positions: `3`
- review/block findings: `0`

This proves Planning → Submit → Fill → Ledger → Valuation → PM → SELL continuity after BT / BU / BV.

### Bull 20BD

- run_id: `runtime-test-historical-extended-smoke-20260726T024433336288Z`
- period: `2026-03-24` to `2026-04-20`
- business_days: `20`
- status: `PASS`
- initial_equity: `1,000,000`
- final_equity: `973,280`
- return: `-26,720`
- return_rate: `-2.672%`
- realized_pnl: `-23,020`
- unrealized_pnl: `-3,700`
- BUY plan: `59`
- SELL plan: `9` derived from PM REDUCE/EXIT
- BUY execution: `5`
- SELL execution: `9`
- PM: `ADD 7`, `EXIT 3`, `HOLD 25`, `REDUCE 6`
- current_positions: `2`
- review/block findings: `0`

Runtime: `PASS`

Performance: `NEGATIVE_RETURN_OBSERVED`

Strategy: not evaluated by Runtime.

### Range 20BD

- run_id: `runtime-test-historical-extended-smoke-20260726T043951394342Z`
- period: `2022-08-01` to `2022-08-29`
- business_days: `20`
- status: `PASS`
- initial_equity: `1,000,000`
- final_equity: `989,310`
- return: `-10,690`
- return_rate: `-1.069%`
- realized_pnl: `-8,600`
- unrealized_pnl: `-2,090`
- BUY plan: `37`
- SELL plan: `2` derived from PM EXIT
- BUY execution: `3`
- SELL execution: `2`
- PM: `ADD 2`, `EXIT 2`, `HOLD 24`, `REDUCE 0`
- current_positions: `1`
- review/block findings: `0`

Runtime: `PASS`

Performance: `NEGATIVE_RETURN_OBSERVED`

### Bear 20BD

Post-fix Bear 20BD revalidation was skipped by user decision. Old Bear results remain reference evidence and are not part of the formal post-fix baseline.

## Active 245BD Handoff

- run_id: `runtime-test-historical-extended-smoke-20260726T053732539035Z`
- requested_start_date: `2022-09-01`
- requested_end_date: `2023-08-30`
- requested_business_days: `245`
- initial_cash: `1,000,000`
- status: `RUNNING`
- completed_business_days: `188`
- first_completed_business_date: `2022-09-01`
- latest_completed_business_date: `2023-06-08`
- next_job: `2023-06-09:market_refresh`

No final summary exists yet in the run directory. Phase20 does not treat any partial 245BD value as final Performance.

The 245BD run is handed off to Phase21. Codex did not start, stop, resume, or mutate this run for this closure.

The active 245BD Historical Run is not only a pending long-run validation. Its completed run-scoped evidence will be used as the primary diagnostic dataset for Phase21 Strategy and Performance Improvement.

現在実行中の245BD / 1年Historical Runは、Phase20の最終成績確認に加え、Phase21におけるPM・保有・資金配分・銘柄選定・再投資・集中度の主要調査データとして使用する。

Phase21での利用範囲:

- 現行システムの1年間の収益構造
- PM判断の寄与
- 銘柄保持期間
- 利益保持・利益消失
- 損失拡大
- ADD / REDUCE / EXITの効果
- Capital Deployment
- 現金保持と投資比率
- ポジション数とslot利用
- 売却後の再投資
- BUY候補からExecutionまでの脱落
- 銘柄・セクター集中
- 市場局面ごとの成績
- Benchmark比較

The 245BD Historical Run is the primary diagnostic evidence source for Phase21, but it is not the sole acceptance period and must not be used in a way that introduces future leakage, performance-result imitation, or single-period overfitting.

The 245BD data may be used for:

- post-run diagnosis
- counterfactual analysis
- attribution
- hypothesis generation
- experiment design
- holdout evaluation planning

It must not be used for:

- Candidate / Opportunity / PM Runtime input contamination
- future return as Runtime decision evidence
- unconditional relabeling from BUY/SELL outcomes
- Portfolio PnL or cash as model features
- direct threshold tuning to final performance
- symbol-specific or date-specific exceptions
- one-year-only optimization
- excluding unfavorable periods or trades

## Performance Judgment

Post-fix formal 20BD evidence:

| Regime | Period | Return | BUY Execution | SELL Execution |
|---|---|---:|---:|---:|
| Bull | 2026-03-24 to 2026-04-20 | -2.672% | 5 | 9 |
| Range | 2022-08-01 to 2022-08-29 | -1.069% | 3 | 2 |

The annual return target is `+50%`.

The corrected Bull and Range results are both negative. The 245BD result is still needed for long-run formal evaluation, but Phase21 performance improvement is already required.

## Current Strategy Issues

The following are Phase21 investigation targets, not Phase20 changes:

- PM HOLD / ADD / REDUCE / EXIT outcome quality
- profit retention and profit disappearance
- loss holding duration
- ADD becoming loss averaging
- EXIT and REDUCE timing
- position holding period
- capital deployment and max position constraint
- cash utilization and reinvestment
- BUY plan to execution drop-off
- Candidate / Opportunity ranking quality
- benchmark and sector-relative performance

## Performance Observability Gaps

The following metrics remain incomplete or sometimes `NOT_AVAILABLE`:

- Daily Equity Curve
- Maximum Drawdown
- Turnover
- Cash Ratio
- Cash Utilization
- Gross Exposure
- Single-name Concentration
- Benchmark
- Sector Exposure
- lot-level realized PnL

Phase21 should complete metric authority before changing strategy logic where missing evidence would affect interpretation.

## Non-changed Scope

Phase20 did not change:

- Candidate AI model
- Opportunity AI model
- Position Management model
- Accepted Generation
- Training
- Calibration
- BUY threshold
- SELL threshold
- Capital Deployment Policy parameters
- `target_investment_ratio`
- `max_positions`
- `max_position_weight`
- Safety Policy
- Production Broker implementation

## Phase21 Objective

Phase21: `Strategy and Performance Improvement`

Objective:

```text
現行Runtime Contract / Safety Contract / PIT Contractを維持したまま、
年率+50%目標との差をEvidence-firstで定量化し、
収益構造を分解し、
有効な戦略改善を実験・比較・採用する。
```

Phase21 does not declare that +50% annual return has been achieved. It establishes controlled, evidence-first improvement toward that target.

## Phase21 Workstreams

1. Phase21-A 245BD Long-run Finalization and Diagnostic Dataset Certification
2. Phase21-B Performance Authority and Metric Completion
3. Phase21-C PM Attribution
4. Phase21-D Position Holding Attribution
5. Phase21-E Capital Deployment Audit
6. Phase21-F Candidate / Opportunity Ranking Quality
7. Phase21-G Improvement Experiment Contract
8. Phase21-H+ Evidence-based improvement experiments

## Phase21-A Diagnostic Dataset Certification

Phase21-A must certify the 245BD run not only as a completed long-run result but also as a run-scoped diagnostic dataset.

Certification targets:

- run identity
- start/end dates
- completed business days
- final state hash
- daily evidence completeness
- position campaigns
- PM decision snapshots
- BUY / SELL plans
- pending lifecycle
- submit evidence
- execution evidence
- realized slices
- current valuation
- cash
- market value
- positions
- benchmark snapshots
- sector evidence
- review / block findings

Minimum extracted diagnostic views:

- `daily_portfolio_state`
- `position_campaign_attribution`
- `pm_decision_attribution`
- `capital_deployment_timeline`
- `execution_and_realized_slice_attribution`
- `missing_metric_inventory`
- `diagnostic_dataset_certification`

Phase21-A deliverables:

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

## Phase21 Validation Separation

The 245BD run is the diagnostic period, not the only acceptance period.

Phase21 experiments must separate:

- Diagnostic period: this 245BD run
- Development / counterfactual period: explicitly separated period
- Validation period: unused period
- Regime checks: Bull, Bear or downtrend, Range
- Final holdout: period not used for improvement selection

Hypotheses may be generated from the 245BD data, but improvement effectiveness must not be accepted using only the same diagnostic data.

## Phase21 Contracts

Phase21 must preserve:

- Production/Demo/Historical common Runtime Contract
- PIT Authority
- No Future Leakage
- Fail-closed
- Broker Safety
- No unauthorized Production write
- Accepted Generation Authority
- Evidence Traceability
- Run-scoped Historical Authority

Phase21 must not:

- mix backtest results into training input
- use PnL directly as Runtime model input
- use future return as decision-time evidence
- overfit to Bull / Range periods
- add symbol-specific or date-specific exceptions
- select only favorable results
- change multiple parameters in one experiment
- discard unfavorable runs

## Required Reading for Phase21

All paths below exist at Phase20 closure:

- `docs/phase_reports/phase20_final_summary_and_phase21_handoff.md`
- `docs/phase_reports/phase20_to_phase21_chatgpt_handoff.md`
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

## Final Status

`PHASE20_CLOSURE_COMPLETE_WITH_PERFORMANCE_IMPROVEMENT_REQUIRED`

Phase21 may start.
