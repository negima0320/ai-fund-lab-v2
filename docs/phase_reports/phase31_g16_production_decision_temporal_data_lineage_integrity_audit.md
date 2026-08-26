# Phase31-G16 - Production Decision Temporal / Data-Lineage Integrity Audit

## Scope

Task type: READ-ONLY PRODUCTION CORRECTNESS AUDIT.

Target run:

`runtime-test-historical-extended-smoke-20260822T174358377089Z`

No implementation, Strategy/PM/BUY/SELL change, tuning, config change, fresh-run,
resume, replay, or Historical rerun was executed by this audit.

The target run was still running while this report was prepared. The audit used a
read-only snapshot of already-materialized artifacts. The latest completed day
observed for the final snapshot was:

- run_state.status: `RUNNING`
- completed_count: `178`
- latest_completed_business_day: `2023-06-22`
- next_job: `2023-06-23:market_refresh`

For the original G16 comparison boundary:

- PRE window: `2022-10-03` through `2023-03-23` (`116` completed days)
- POST window observed: `2023-03-24` through `2023-06-22` (`62` completed days)

The run was not paused, advanced, resumed, or otherwise interfered with.

## Primary Judgment

`PHASE31_G16_NON_DECISION_GAPS_FOUND_NO_PERFORMANCE_CONTAMINATION`

The production-equivalent Strategy decision lineage is mapped and no evidence was
found that future prices, future returns, later corporate/financial outcomes,
runtime test results, audit reports, paper-ledger PnL, or Historical performance
results were consumed as Strategy decision inputs.

One non-decision lineage gap remains: the corporate-event artifact declares the
earnings-calendar source as `CURRENT_SNAPSHOT_CALENDAR_ONLY` and
`earnings_calendar_historical_pit_compliant = false`. In the target run snapshot
audited here, however, this path produced `event_count = 0` and
`future_event_count = 0` on all PRE/POST days, so no decision or performance
contamination was observed from that gap.

## Canonical Decision Lineage

| Decision surface | Canonical producer / artifact | Source category | Temporal binding | Audit result |
| --- | --- | --- | --- | --- |
| Market Context / regime | `strategy/market_context.json`, produced by Strategy market context over Historical as-of view | Allowed PIT market data and derived technical state | Business date and selected feature date are same-day PIT runtime dates; no future-row flags observed | PASS |
| Candidate BUY AI | `runtime_v2/buy_ai/producer.py`, artifacts under runtime Strategy/BUY evidence | Allowed PIT feature frame plus static model artifact; schema/producer record explicit anti-leakage fields | Feature date bound to the business date; candidate evidence reports `future_information_used = false` and `historical_outcome_used_as_runtime_input = false` | PASS |
| Candidate ranking / expected edge | Opportunity ranking consumed by BUY quality and planning | Allowed derived PIT model inference, not later realized outcome | Runtime artifact is generated from PIT feature input and static trained model; runtime does not consume validation outcomes as live features | PASS |
| BUY quality | `strategy/buy_quality_decisions.json` | Allowed Strategy state, candidate scores, portfolio policy, corporate-event safety evidence | Same business date Strategy graph; scanned positive future/evidence-as-input flags were zero | PASS |
| Portfolio construction | `strategy/portfolio_construction.json` | Allowed current portfolio/cash operational state and PIT BUY evidence | Current holdings/cash are legitimate decision-time state, not alpha/outcome labels | PASS |
| Position sizing | `strategy/position_sizing.json` | Allowed portfolio policy, cash/exposure state, candidate/BUY evidence | Same business date Strategy graph | PASS |
| Position management / canonical SELL state | `strategy/position_management.json` and `sell_planning/position_management_evidence.json` | Allowed current position state, PIT technical features, PM semantic evidence | PM input contracts reject future/outcome/report fields; current holdings are runtime state | PASS |
| ADD / REDUCE / EXIT planning | `strategy/runtime_planning.json`, sell planning artifacts | Allowed Strategy decisions plus current ledger/position state | No evidence that Historical performance or audit verdicts feed the Strategy decision | PASS |
| Corporate events / financial publication | `strategy/corporate_event.json` and `strategy/corporate_event.py` | Financial/disclosure rows filtered by decision-time availability; earnings calendar is current-snapshot calendar-only | Future event counters were zero in the target run; non-PIT calendar authority is a non-decision gap in this snapshot | PASS_WITH_NON_DECISION_GAP |
| Runtime evidence and reports | report/status/test artifacts | Reporting/status only | Not consumed as Strategy alpha or decision data source | PASS |

## Artifact Evidence

Sampled dates:

`2022-10-03`, `2022-10-04`, `2023-02-13`, `2023-03-06`,
`2023-03-13`, `2023-03-23`, `2023-03-24`, `2023-03-31`,
`2023-04-05`, `2023-04-11`, `2023-04-12`, `2023-05-10`,
`2023-05-12`, `2023-05-15`, `2023-05-19`, `2023-05-22`,
`2023-06-01`, `2023-06-20`, `2023-06-22`.

Observed common artifact shape:

- `market_refresh/historical_asof_view.json`: `status = PASS`,
  `reason = historical_asof_view_ready`
- `market_refresh/feature_refresh/latest_features.json`: present
- `strategy/input_manifest.json`: `business_date = feature_date =
  selected_feature_date`
- `strategy/input_manifest.json`: `future_rows_consumed = false`
- `data_readiness/data_readiness.json`: `selected_feature_date = business_date`

Full PRE/POST scan of `latest_features.json` found no positive/non-false values
for:

- `audit_result_used_for_ai`
- `broker_snapshot_used_for_ai`
- `cash_portfolio_pnl_used_for_ai`
- `paper_ledger_used_for_ai`
- `safety_result_used_for_ai`
- `future_information_used`
- `future_data_used`
- `historical_result_input_used`
- `test_result_used_as_strategy_input`
- `historical_outcome_used_as_runtime_input`

Counts:

- PRE latest-feature days scanned: `116`
- POST latest-feature days scanned: `62`
- Non-false evidence-as-AI-input flags: `0`

Full PRE/POST scan of primary Strategy artifacts found no positive/non-false
values for future/evidence contamination flags in:

- `strategy/market_context.json`
- `strategy/buy_quality_decisions.json`
- `strategy/runtime_planning.json`
- `strategy/portfolio_construction.json`
- `strategy/position_management.json`
- `strategy/position_sizing.json`
- `strategy/corporate_event.json`
- `strategy/technical_features.json`
- `strategy/strategy_intelligence.json`
- `sell_planning/position_management_evidence.json`
- `morning/strategy_planning_authority_evidence.json`
- `data_readiness/data_readiness.json`

Positive contamination flags:

- PRE: `0`
- POST: `0`

## Static Source Audit

Static search across `src/ai_fund_lab_v2` found `160` files containing one or
more high-risk terms such as future-return labels, backtest references,
paper-ledger references, runtime-test references, or audit-result references.
These matches were classified by role.

Material production-relevant reviewed categories:

- Historical as-of authority:
  `src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py`
- Data Readiness:
  `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- BUY AI runtime producer:
  `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- Candidate AI schema / leakage contract:
  `src/ai_fund_lab_v2/candidate_ai/schemas.py`
- PM AI inference input contract:
  `src/ai_fund_lab_v2/position_management_ai/inference.py`
- PM runtime producer:
  `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- Corporate event authority:
  `src/ai_fund_lab_v2/strategy/corporate_event.py`
- Corporate-action adjustment authority:
  `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`
- Strategy planning authority:
  `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- Submit / execution surfaces:
  `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
  and `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- Runtime reports and status:
  `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`,
  `src/ai_fund_lab_v2/runtime_v2/system_status.py`,
  `src/ai_fund_lab_v2/runtime_v2/ai_status.py`
- Training, validation, backtest, calibration, and paper-trading modules:
  not production Strategy data-source consumers in this target runtime path.

No production Strategy consumer was found that uses Historical performance,
test/audit verdicts, paper-ledger PnL, future returns, or future price movement
as Strategy input.

## Temporal Authority Findings

### Historical As-of

`runtime_v2/historical_support/asof.py` materializes logical views with
decision-time filters and records `future_rows_excluded_count`. It fail-closes
if a logical view contains data whose logical maximum date exceeds the business
date. This is the primary production boundary preventing future rows from
entering the runtime market-data view.

### Data Readiness

`runtime_v2/data_readiness.py` records and checks `selected_feature_date`. In
the audited target artifacts, `selected_feature_date = business_date` on the
sampled days and no future feature-row consumption was observed.

### Candidate / PM Features

Candidate and PM input contracts explicitly forbid future/outcome/report/test
terms as live features. Runtime artifacts also carry explicit false flags for
future information and Historical outcome usage as runtime inputs.

### Corporate / Financial Events

Financial events are filtered by disclosure/announcement date at or before the
business date. Future-dated announcement or availability evidence is treated as
a violation. In the target run:

- PRE corporate-event days scanned: `116`
- POST corporate-event days scanned: `62`
- `event_count`: `0` on all scanned days
- `future_event_count`: `0` on all scanned days
- non-PIT earnings-calendar authority days: `178`

The non-PIT earnings-calendar authority is therefore recorded as a lineage gap,
but not as observed Strategy decision contamination in this run snapshot.

## PRE / POST Comparison

No temporal or lineage behavior change was found at the
`2023-03-24` boundary that explains PRE outperformance or POST degradation by
future-information leakage.

The same Strategy artifact families, feature-date bindings, false future-use
flags, and evidence-as-input false flags were observed on both sides of the
boundary.

## Required Output

### PRIMARY_JUDGMENT

`PHASE31_G16_NON_DECISION_GAPS_FOUND_NO_PERFORMANCE_CONTAMINATION`

### TARGET_RUN_ID

`runtime-test-historical-extended-smoke-20260822T174358377089Z`

### SNAPSHOT_LATEST_COMPLETED_DATE

`2023-06-22`

### CANONICAL_DECISION_LINEAGE_MAPPED

`YES`

### MARKET_CONTEXT_TEMPORAL_INTEGRITY

`PASS`

### CANDIDATE_AI_TEMPORAL_INTEGRITY

`PASS`

### BUY_QUALITY_TEMPORAL_INTEGRITY

`PASS`

### PORTFOLIO_CONSTRUCTION_TEMPORAL_INTEGRITY

`PASS`

### POSITION_MANAGEMENT_TEMPORAL_INTEGRITY

`PASS`

### SELL_SEMANTIC_TEMPORAL_INTEGRITY

`PASS`

### CORPORATE_EVENT_PIT_INTEGRITY

`PASS`

### CORPORATE_EVENT_NON_DECISION_LINEAGE_GAP

`YES`

### FINANCIAL_PUBLICATION_PIT_INTEGRITY

`PASS`

### REGIME_TEMPORAL_INTEGRITY

`PASS`

### EVIDENCE_DATA_SOURCE_INTEGRITY

`PASS`

### DERIVED_FEATURE_LINEAGE_AUDITED

`YES`

### CONTAMINATED_DERIVED_FEATURE_COUNT

`0`

### UNRESOLVED_DERIVED_FEATURE_COUNT

`0`

### FUTURE_MARKET_PRICE_INPUT_COUNT

`0`

### FUTURE_RETURN_INPUT_COUNT

`0`

### FUTURE_FEATURE_ROW_INPUT_COUNT

`0`

### ILLEGAL_SAME_DAY_CLOSE_INPUT_COUNT

`0`

### FUTURE_REGIME_INPUT_COUNT

`0`

### FUTURE_CORPORATE_EVENT_INPUT_COUNT

`0`

### LATER_PUBLISHED_FINANCIAL_INPUT_COUNT

`0`

### FUTURE_MFE_MAE_PEAK_TROUGH_INPUT_COUNT

`0`

### PAPER_LEDGER_AS_ALPHA_INPUT_COUNT

`0`

### BROKER_STATE_AS_ALPHA_INPUT_COUNT

`0`

### CASH_PORTFOLIO_PNL_AS_ALPHA_INPUT_COUNT

`0`

### RUNTIME_EVIDENCE_AS_STRATEGY_DATA_SOURCE_COUNT

`0`

### HISTORICAL_EVIDENCE_AS_STRATEGY_DATA_SOURCE_COUNT

`0`

### AUDIT_RESULT_AS_STRATEGY_DATA_SOURCE_COUNT

`0`

### PERFORMANCE_REPORT_AS_STRATEGY_DATA_SOURCE_COUNT

`0`

### TEST_RESULT_AS_STRATEGY_DATA_SOURCE_COUNT

`0`

### STATIC_FORBIDDEN_SOURCE_MATCHES

`160 source files contained high-risk terms; reviewed and classified`

### PRODUCTION_RELEVANT_FORBIDDEN_MATCHES

`0 confirmed forbidden production Strategy inputs`

### PRE_FUTURE_INPUT_COUNT

`0`

### POST_FUTURE_INPUT_COUNT

`0`

### TEMPORAL_OR_LINEAGE_BEHAVIOR_CHANGED_PRE_POST

`NO`

### PRE_PERFORMANCE_ADVANTAGE_EXPLAINED_BY_INFORMATION_LEAKAGE

`NO`

### POST_PERFORMANCE_DEGRADATION_EXPLAINED_BY_LEAKAGE_REMOVAL

`NO`

### UNRESOLVED_CRITICAL_LINEAGE_COUNT

`0`

### PERFORMANCE_EVIDENCE_STATUS

`MINOR_NON_DECISION_LINEAGE_GAPS_PERFORMANCE_EVIDENCE_STILL_VALID`

### PERFORMANCE_QUARANTINE_REQUIRED

`NO`

### IMPLEMENTATION_CHANGED

`NO`

### FRESH_RUN_EXECUTED

`NO`

### RESUME_EXECUTED

`NO`

### REPLAY_EXECUTED

`NO`

### LONG_HISTORICAL_EXECUTED

`NO`

### RECOMMENDATION

Continue using the current run as performance evidence. Track the non-PIT
earnings-calendar authority as a non-decision lineage gap, but do not quarantine
the observed performance evidence unless a future artifact shows nonzero
decision-time event consumption from that source.

