# Phase27-A1 100BD Evidence Inventory and Attribution Readiness Audit

## Judgment

```text
PHASE27_A1_EVIDENCE_INVENTORY_COMPLETE_ATTRIBUTION_READY_WITH_LIMITATIONS
```

Task classification:

```text
Phase: Phase27
Task ID: Phase27-A1
Task Type: Observability Only / Read-only Investigation
Parent Task: Phase27-A 100BD Baseline Attribution and Performance Diagnosis
Implementation Changed: false
Strategy Changed: false
Historical Test Executed: false
```

## Scope

This task audited whether the official Phase26 100BD baseline has enough
run-scoped evidence for Phase27-A attribution. It did not perform performance
tuning, Strategy changes, BUY Quality changes, Position Sizing changes,
Planning changes, Submit Guard changes, Safety changes, re-entry rule changes,
symbol-specific changes, period-specific changes, fresh-run, resume, or
Historical rerun.

Baseline:

```text
run_id: runtime-test-historical-smoke-20260804T074611098414Z
period: 2023-01-04 through 2023-05-31
business_days: 100
evidence_root: reports/runtime_tests/runs/runtime-test-historical-smoke-20260804T074611098414Z/
performance_report: reports/runtime_tests/runs/runtime-test-historical-smoke-20260804T074611098414Z/performance_report/
```

## Required Reading Confirmation

Reviewed before this audit:

- `docs/phase_reports/phase26_to_phase27_chatgpt_handoff.md`
- `docs/phase_reports/phase26_l_final_closure_consolidation_and_phase27_execution_handoff.md`
- `docs/phase_reports/phase26_final_summary_and_phase27_handoff.md`
- `docs/phase_reports/phase26_k_final_architecture_conformance_responsibility_fulfillment_and_closure_review.md`
- `docs/phase_reports/phase26_i_production_runtime_performance_analysis_toolkit.md`
- `docs/phase_reports/phase26_j_runtime_evaluation_integrity_repair.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/phase_reports/phase26_g_adaptive_buy_quality_authority_design_and_architecture_sot_amendment.md`
- `docs/phase_reports/phase26_h_production_common_adaptive_buy_quality_authority_implementation.md`
- `docs/phase_reports/phase26_hr_buy_quality_eligible_consumer_end_to_end_audit_and_repair.md`
- `docs/phase_reports/phase26_hr2_portfolio_construction_zero_weight_vs_actual_buy_authority_divergence_audit_and_repair.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

## Baseline Evidence Completeness

All 100 business-date directories exist from `2023-01-04` through
`2023-05-31`.

The following required daily artifacts are present on all 100 business dates:

| Artifact | Present Days | Judgment |
|---|---:|---|
| `strategy/market_context.json` | 100 | AVAILABLE_AND_USABLE |
| `strategy/portfolio_policy.json` | 100 | AVAILABLE_AND_USABLE |
| `strategy/buy_quality_decisions.json` | 100 | AVAILABLE_AND_USABLE |
| `strategy/portfolio_construction.json` | 100 | AVAILABLE_AND_USABLE |
| `strategy/position_sizing.json` | 100 | AVAILABLE_AND_USABLE |
| `strategy/runtime_planning.json` | 100 | AVAILABLE_AND_USABLE |
| `morning/strategy_planning_authority_evidence.json` | 100 | AVAILABLE_AND_USABLE |
| `morning/pending_generation_evidence.json` | 100 | AVAILABLE_AND_USABLE |
| `execution/fills.json` | 100 | AVAILABLE_WITH_LIMITATION |
| `execution/realized_slices.json` | 100 | AVAILABLE_AND_USABLE |
| `execution/submitted_order_authority.json` | 100 | AVAILABLE_WITH_LIMITATION |
| `positions/position_campaigns.json` | 100 | AVAILABLE_AND_USABLE |
| `current_valuation_refresh/valuation_projection.json` | 100 | AVAILABLE_AND_USABLE |

Performance report artifacts are present:

```text
performance_summary.json
trade_history.csv
trade_with_quality.csv
symbol_statistics.csv
quality_statistics.csv
rank_statistics.csv
equity_curve.csv
drawdown.csv
cash_exposure.csv
cash_exposure_statistics.csv
holding_period.csv
reentry_statistics.csv
```

## Evidence Inventory

| Evidence Name | Producer | Canonical Artifact Path | Scope | Date Bound | Generation Bound | Symbol Key | Campaign Key | Order / Fill Key | Primary Consumer | Phase27 Use | Completeness | Known Ambiguity | Missing Join Key | Judgment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Historical Evaluation Authority | Runtime Test fresh-run authority resolver | `historical_evaluation_authority.json` | Run | Yes | Yes | N/A | N/A | N/A | Strategy input manifest | Accepted Generation / PIT boundary | Complete | Historical mode does not compare accepted_at to historical date by design | None | AVAILABLE_AND_USABLE |
| Market Context | Strategy materialization | `daily/<date>/strategy/market_context.json` | Run daily | Yes | Via input manifest | N/A | N/A | N/A | Portfolio Policy, BUY Quality | Market vs exposure attribution | Complete | Need downstream aggregation for market-context buckets | None | AVAILABLE_AND_USABLE |
| Candidate evidence | Candidate AI, referenced by strategy input manifest | `daily/<date>/strategy/input_manifest.json` refs plus downstream source ids | Run daily refs | Yes | Yes | `source_candidate_id`, symbol | N/A | N/A | Opportunity, BUY Quality, PC | Candidate-to-BUY lineage | Partial | Full candidate universe artifact is referenced as `.runtime/...` path, not copied as a run-scoped daily artifact | Canonical daily candidate rank / full candidate row | AVAILABLE_WITH_LIMITATION |
| Candidate Rank | Candidate AI / downstream copied lineage | Downstream `input_candidate_order` in PC/PS examples | Run daily derived | Yes | Yes | symbol, source_candidate_id | N/A | N/A | PC / attribution | Candidate-rank analysis | Partial | `input_candidate_order` exists for selected rows; full candidate rank distribution is not fully materialized run-scoped | Full candidate-rank universe | AVAILABLE_WITH_LIMITATION |
| Opportunity Ranking | Opportunity AI / runtime BUY producer | Downstream copied lineage in `buy_quality_decisions.json`, `portfolio_construction.json`, `position_sizing.json`, `runtime_planning.json` | Run daily derived | Yes | Yes | symbol, source_opportunity_id, row hash | N/A | N/A | BUY Quality, PC, PS, Planning | Rank attribution | Strong for bought/planned/quality rows | Source path remains `.runtime/...`, but rank, score, hash and ids are copied into run-scoped artifacts | Full raw source row if not copied | AVAILABLE_AND_USABLE |
| Portfolio Policy | Strategy materialization | `daily/<date>/strategy/portfolio_policy.json` | Run daily | Yes | Via input manifest | N/A | N/A | N/A | PC / PS | Cash/exposure diagnosis | Complete | None found | None | AVAILABLE_AND_USABLE |
| Adaptive BUY Quality | Production Strategy BUY Quality Resolver | `daily/<date>/strategy/buy_quality_decisions.json` | Run daily | Yes | Yes | symbol, quality_decision_id | N/A | N/A | PC, PS, Planning | Quality attribution | Complete, 5000 decisions | Fill artifact does not carry quality_decision_id directly in this pre-repair run | Fill-level quality_decision_id | AVAILABLE_AND_USABLE |
| Portfolio Construction | Strategy materialization | `daily/<date>/strategy/portfolio_construction.json` | Run daily | Yes | Yes | symbol, member_id | N/A | N/A | Position Sizing | Selected/not-selected path | Complete, 5006 members | Some non-selected current-position rows show `UNRESOLVED` plus downstream NO_ACTION; reason is explicit enough for readiness | None for row-level PC | AVAILABLE_AND_USABLE |
| Position Sizing | Strategy materialization | `daily/<date>/strategy/position_sizing.json` | Run daily | Yes | Yes | symbol, position_reference | N/A | N/A | Runtime Planning | Notional/quantity attribution | Complete | `positions_sized` is a count, rows are in `positions` | None | AVAILABLE_AND_USABLE |
| Runtime Planning | Strategy materialization | `daily/<date>/strategy/runtime_planning.json` | Run daily | Yes | Yes | symbol, planning_id | N/A | planning_id | Strategy Planning Authority | BUY/no-order reasons | Complete, 522 plans | Rows absent for some Quality REJECT exclusions | Planning row for pure rejects | AVAILABLE_WITH_LIMITATION |
| Formal Morning Planning | Runtime planning authority | `daily/<date>/morning/strategy_planning_authority_evidence.json` | Run daily | Yes | Yes | security_code | N/A | planning_id | Pending / Approval / Submit | Canonical morning bridge | Complete | `planning_output`, `submit_input` can be empty; lineage items still prove pending generation | Pending item id | AVAILABLE_WITH_LIMITATION |
| Pending / Approval | Runtime pending materialization | `daily/<date>/morning/pending_generation_evidence.json`, SPA evidence paths | Run daily | Yes | Yes | security_code | N/A | planning_id / pending_plan_id | Submit | Planning-to-submit bridge | Present | Pending path metadata exists; item IDs are not preserved into fills | pending_item_id in fill | AVAILABLE_WITH_LIMITATION |
| Submit / Order | Historical submit authority | `daily/<date>/execution/submitted_order_authority.json` | Run daily | Yes | Yes | symbol via execution references | N/A | execution reference / order id | Execution | Submitted order count and execution reference | Present | Minimal per-order metadata in checked artifact | Full submitted quantity by order item | AVAILABLE_WITH_LIMITATION |
| Execution Fill | Historical execution | `daily/<date>/execution/fills.json` | Run daily | Yes | Indirect | symbol | position_campaign_id | order_id, execution_id | Ledger/current/performance | Trade history, campaigns | Present, 25 BUY / 45 SELL | All BUY fills in existing artifact have `pending_item_id`, `order_plan_item_id`, `quality_decision_id` missing | pending_item_id, order_plan_item_id, quality_decision_id | AVAILABLE_WITH_LIMITATION |
| BUY Fill Lineage Replay | Phase26-J runtime summary repair | `final_summary.json.buy_fill_lineage_validation` | Run | Yes | Indirect | symbol | position_campaign_id | execution_id | Evaluation / attribution | Bridge validation | PASS | Existing artifacts were not rewritten; replay evidence says missing lineage is resolvable from run-scoped submit guard evidence | Direct fields in original fill rows | AVAILABLE_WITH_LIMITATION |
| Position Campaign | Runtime current / lifecycle | `daily/<date>/positions/position_campaigns.json` | Run daily | Yes | N/A | symbol | position_campaign_id | N/A | Performance toolkit | Re-entry / campaign attribution | Complete | Campaign PnL is best consumed through toolkit outputs plus realized slices | None material | AVAILABLE_AND_USABLE |
| Realized Slices | Execution / ledger projection | `daily/<date>/execution/realized_slices.json` | Run daily | Yes | N/A | symbol | position_campaign_id | fill/execution-derived | Performance summary | PF, realized PnL, exits | Complete, 45 slices | None found | None | AVAILABLE_AND_USABLE |
| Valuation / Current | Current valuation refresh | `daily/<date>/current_valuation_refresh/*` | Run daily | Yes | N/A | symbol where positions exist | position_campaign_id where present | N/A | Performance summary | Equity/cash/exposure | Complete | Current realized field is non-canonical for net evaluation PnL per Phase26-J | None for valuation | AVAILABLE_AND_USABLE |
| Performance Report | Phase26-I toolkit | `performance_report/*` | Run | Yes | N/A | symbol / campaign / rank / quality | campaign | N/A | Human review | Phase27-A attribution | Complete | Post-hoc only; must not feed Strategy | None | AVAILABLE_AND_USABLE |

## Candidate-to-BUY Lineage Samples

These samples prove that actual BUYs can be traced from Strategy evidence to
fills. `pending_item_id` and `order_plan_item_id` are missing inside the fill
rows, so the join is usable with limitation through business date, symbol,
side, quantity, notional, planning lineage, and campaign.

| Case | Date | Symbol | Candidate Rank Field | Opportunity Rank | Quality Action | Quality Score | Quality Adj | Target Weight | Target Notional | Planned Qty | Filled Qty | Fill Notional | Campaign | Limitation |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| High-rank bought | 2023-01-04 | 76470 | 2 | 1 | REDUCED_ALLOCATION_ONLY | 0.766406 | 0.766406 | 0.117515 | 117,515 | 4,100 | 4,100 | 114,800 | `pc-66d9ba285c89ec9b-76470-0001` | Fill lacks pending/order-plan/quality ids |
| Low-rank bought | 2023-03-02 | 76920 | 7 | 6 | REDUCED_ALLOCATION_ONLY | 0.707118 | 0.707118 | 0.127281 | 127,717.57 | 300 | 300 | 102,510 | `pc-66d9ba285c89ec9b-76920-0002` | Fill lacks pending/order-plan/quality ids |
| Quality FULL | 2023-01-04 | 83060 | 4 | 4 | FULL_ALLOCATION_ELIGIBLE | 0.752931 | 1.0 | 0.153333 | 153,333 | 100 | 100 | 89,400 | `pc-66d9ba285c89ec9b-83060-0001` | Fill lacks pending/order-plan/quality ids |
| Quality REDUCED | 2023-01-04 | 76470 | 2 | 1 | REDUCED_ALLOCATION_ONLY | 0.766406 | 0.766406 | 0.117515 | 117,515 | 4,100 | 4,100 | 114,800 | `pc-66d9ba285c89ec9b-76470-0001` | Fill lacks pending/order-plan/quality ids |
| Re-entry 93180 | 2023-01-31 | 93180 | 1 | 3 | FULL_ALLOCATION_ELIGIBLE | 0.741708 | 1.0 | 0.18 | 181,116 | 60,300 | 60,300 | 120,600 | `pc-66d9ba285c89ec9b-93180-0002` | Fill lacks pending/order-plan/quality ids |
| Re-entry 76920 | 2023-03-02 | 76920 | 7 | 6 | REDUCED_ALLOCATION_ONLY | 0.707118 | 0.707118 | 0.127281 | 127,717.57 | 300 | 300 | 102,510 | `pc-66d9ba285c89ec9b-76920-0002` | Fill lacks pending/order-plan/quality ids |

Accepted Generation for the sampled rows:

```text
phase19_aq_accepted_generation_641e6e313543f013
```

## High-rank Not-bought Readiness

High-rank not-bought analysis is possible, but not perfect.

Observed readiness:

- Quality decisions exist for the daily ranked population.
- Portfolio Construction carries membership intent, opportunity rank, quality
  fields, target weight, and reason codes.
- Position Sizing carries target notional, quantity status, reference price,
  quality adjustment, and lot/minimum-notional outcomes.
- Runtime Planning carries explicit no-order reasons when a row reaches
  planning.

Known limitations:

- Some high-rank rejected candidates do not have Runtime Planning rows because
  they are excluded before planning. Their final non-buy reason must be taken
  from Quality / PC / PS, not inferred.
- Full candidate universe and candidate rank source artifact is referenced but
  not copied as a run-scoped daily candidate artifact.

Examples:

| Date | Symbol | Rank | Quality Action | PC Membership | PC Target Weight | PS Qty | PS Status | RP Intent | Final Explicit Reason |
|---|---:|---:|---|---|---:|---:|---|---|---|
| 2023-01-04 | 93180 | 3 | REJECT | EXCLUDE | 0.0 | 0 | RESOLVED_ZERO_DELTA | missing | QUALITY_REJECT / EXCLUDE |
| 2023-01-05 | 76470 | 1 | REDUCED_ALLOCATION_ONLY | UNRESOLVED | 0.0 | 0 | RESOLVED_ZERO_DELTA | NO_ACTION | no_action_strategy_intent; current_position_zero_delta_maps_to_no_action |
| 2023-01-05 | 83060 | 2 | REDUCED_ALLOCATION_ONLY | UNRESOLVED | 0.0 | 0 | RESOLVED_ZERO_DELTA | NO_ACTION | no_action_strategy_intent; current_position_zero_delta_maps_to_no_action |
| 2023-01-05 | 94320 | 3 | REDUCED_ALLOCATION_ONLY | UNRESOLVED | 0.0 | 0 | RESOLVED_ZERO_DELTA | NO_ACTION | no_action_strategy_intent; current_position_zero_delta_maps_to_no_action |

## Cash / Exposure Readiness

Cash and exposure attribution is ready with moderate limitations.

Available:

- `market_context.json` and `portfolio_policy.json` for all 100 dates.
- `position_sizing.json` with target gross exposure, total equity, target
  notional, quantity, reference price, lot decisions, and residual cash ratio.
- `runtime_planning.json` with planned BUY/no-order mapping.
- `execution/fills.json` and `realized_slices.json` for executed BUY/SELL.
- `current_valuation_refresh/*` for daily cash, valuation, and equity.
- `performance_report/cash_exposure.csv` and
  `cash_exposure_statistics.csv`.

Existing performance summary:

```text
Final Cash Ratio: 65.96518312376851%
Average Cash Ratio: 50.10779329090453%
Median Cash Ratio: 49.94864086811498%
Min Cash Ratio: 24.191021186729342%
Max Cash Ratio: 72.54128554750813%
Average Position Count: 3.66
```

Limitation:

Daily joining of Market Context, target exposure, quality action counts,
planned notional, executed notional, SELL proceeds, lot constraints, and safety
blocks is feasible, but not yet emitted as a single canonical attribution table.
Phase27-A can build that table from run-scoped artifacts without changing
Strategy.

## Re-entry and Campaign Readiness

Re-entry and campaign attribution is ready.

`performance_report/reentry_statistics.csv` identifies:

| Symbol | Entry Count | Exit Count | Re-entry Count | Avg Re-entry Interval | PnL |
|---:|---:|---:|---:|---:|---:|
| 93180 | 6 | 6 | 5 | 3.0 | -120,600 |
| 76920 | 3 | 3 | 2 | 2.0 | -28,290 |

Campaign IDs are present in fills and trade history, including:

```text
pc-66d9ba285c89ec9b-93180-0001
pc-66d9ba285c89ec9b-93180-0002
pc-66d9ba285c89ec9b-93180-0003
pc-66d9ba285c89ec9b-76920-0001
pc-66d9ba285c89ec9b-76920-0002
```

This task does not conclude that re-entry caused losses; it confirms that
Phase27-A can analyze that hypothesis.

## Phase26-I Toolkit Audit

All toolkit scripts are under `tools/performance_analysis/` and require
`--run-id`. `common.py` resolves the run under `reports/runtime_tests/runs` and
does not read `.runtime`.

| CLI | Required Input | Output | Run-scoped | Uses `.runtime` | Known Limitation | Phase27-A Usability |
|---|---|---|---|---|---|---|
| `01_summary.py` | run daily evidence | `performance_summary.json` | Yes | No | Summary-level only | Usable |
| `02_trade_history.py` | fills / realized slices / campaigns | `trade_history.csv` | Yes | No | Fill lineage ids missing in source run | Usable with limitation |
| `03_trade_with_quality.py` | trade history + strategy quality/rank | `trade_with_quality.csv` | Yes | No | Joins by run-scoped bridge, not direct fill quality id | Usable with limitation |
| `04_symbol_statistics.py` | trade history | `symbol_statistics.csv` | Yes | No | Post-hoc only | Usable |
| `05_quality_statistics.py` | trade_with_quality | `quality_statistics.csv` | Yes | No | BUY Quality attribution only for bought trades | Usable |
| `06_rank_statistics.py` | trade_with_quality | `rank_statistics.csv` | Yes | No | Bought-trade rank attribution, not full not-bought universe | Usable |
| `07_equity_curve.py` | valuation evidence | `equity_curve.csv` | Yes | No | None material | Usable |
| `08_drawdown.py` | equity curve | `drawdown.csv` | Yes | No | None material | Usable |
| `09_profit_factor.py` | realized slices / trade history | summary update | Yes | No | Realized PF; open PnL separate | Usable |
| `10_cash_exposure.py` | valuation/current evidence | `cash_exposure.csv`, stats | Yes | No | Does not include market context / quality counts in same table | Usable with limitation |
| `11_holding_period.py` | campaigns / trade history | `holding_period.csv` | Yes | No | Campaign-level details may need daily campaign artifact for deeper joins | Usable |
| `12_reentry_analysis.py` | campaigns / trade history | `reentry_statistics.csv` | Yes | No | Symbol summary, not full event chain table | Usable |

Safety boundary:

```text
Future Information Risk: not found in toolkit code path
Performance Result Feedback Risk: not found
Strategy Input Added: false
```

## Analysis Readiness by Phase27-A Topic

| Topic | Judgment | Notes |
|---|---|---|
| Total Return | AVAILABLE_AND_USABLE | `performance_summary.json`, final summary PnL reconciliation |
| Profit Factor | AVAILABLE_AND_USABLE | `performance_summary.json`, realized slices |
| Maximum Drawdown | AVAILABLE_AND_USABLE | `drawdown.csv`, equity curve |
| Win Rate | AVAILABLE_AND_USABLE | trade history / summary |
| Equity Curve | AVAILABLE_AND_USABLE | `equity_curve.csv` |
| Cash / Exposure progression | AVAILABLE_AND_USABLE | `cash_exposure.csv` plus daily valuation |
| Market Context by Cash / Exposure | AVAILABLE_WITH_LIMITATION | Inputs exist; combined table not yet materialized |
| Opportunity Rank performance | AVAILABLE_AND_USABLE | Bought attribution ready; not-bought requires daily joins |
| Candidate Rank performance | AVAILABLE_WITH_LIMITATION | Candidate source ids and selected order exist; full candidate-rank universe not copied |
| Quality Action performance | AVAILABLE_AND_USABLE | Quality stats and trade_with_quality |
| Quality Score bucket performance | AVAILABLE_AND_USABLE | Existing quality stats plus daily quality decisions |
| Bought vs Not Bought comparison | AVAILABLE_WITH_LIMITATION | Possible for quality/opportunity/PC/PS/RP; candidate universe incomplete run-scoped |
| Symbol performance | AVAILABLE_AND_USABLE | symbol stats |
| Position Campaign performance | AVAILABLE_AND_USABLE | trade history / campaigns / holding period |
| Re-entry performance | AVAILABLE_AND_USABLE | reentry stats and campaign ids |
| Holding Period | AVAILABLE_AND_USABLE | holding_period.csv |
| EXIT / REDUCE performance | AVAILABLE_WITH_LIMITATION | SELL fills and realized slices exist; action taxonomy needs PM/sell planning join |
| Position Sizing vs actual notional | AVAILABLE_AND_USABLE | PS target notional / fill notional join |
| Rank / Quality / Notional relation | AVAILABLE_AND_USABLE | trade_with_quality plus PS |
| Performance Root Cause Ranking | AVAILABLE_WITH_LIMITATION | Requires Phase27-A synthesis; A1 only confirms inputs |

## Main Limitations for Phase27-A

1. BUY fill rows in the existing baseline are pre-repair artifacts with
   `pending_item_id`, `order_plan_item_id`, and `quality_decision_id` missing.
   Phase26-J replay validates lineage as recoverable from run-scoped evidence,
   but the original fill rows remain limited.
2. Candidate and Opportunity source paths are recorded as `.runtime/...` in
   input manifests. Opportunity rank, score, ids, and hashes are copied into
   run-scoped downstream artifacts. Full candidate universe / candidate rank
   rows are not fully copied as canonical run-scoped daily artifacts.
3. High-rank not-bought cases are analyzable only when the row reaches Quality,
   PC, PS, or Runtime Planning. Pure upstream candidate exclusions require
   copied candidate artifacts that are not present in the run evidence.
4. Cash/exposure decomposition is feasible but not yet a single canonical
   joined report; Phase27-A should build it as read-only analysis output.

## Final Decision

Phase27-A attribution can proceed using the official 100BD baseline. The
evidence is broadly complete and run-scoped, with limitations around direct
fill item ids and full candidate universe materialization.

```text
Phase27-A Readiness: READY_WITH_LIMITATIONS
Implementation Needed Before Phase27-A: false
Recommended Next Task: Phase27-A2 baseline attribution table generation and hypothesis-specific evidence extraction
```
