# Phase20-A Performance Baseline and Attribution Evidence Inventory

## 1. Executive Summary

Phase20-A inventories the evidence available for Performance Baseline and Attribution analysis after Phase19 Runtime Acceptance.

Final judgment:

```text
PHASE20_A_EVIDENCE_INVENTORY_COMPLETE_WITH_DERIVABLE_GAPS
```

The 20BD Historical Smoke run is valid Runtime evidence and remains:

```text
run_id = runtime-test-historical-smoke-20260721T213848054826Z
Runtime judgment = PASS
Performance judgment = NEGATIVE_RETURN_OBSERVED
Initial equity = 1,000,000
Final equity = 955,100
Total return = -44,900 (-4.49%)
Realized PnL = -51,300
Unrealized PnL = +6,400
BUY executions = 5
SELL executions = 7
PM distribution = HOLD 30 / ADD 9 / REDUCE 4 / EXIT 3
Lifecycle consistency = PASS
```

This is not a Runtime failure. Phase20-B can compute a basic performance baseline from the existing summary, run-scoped daily evidence, and final summary. Several richer attribution metrics are derivable, but benchmark, sector attribution, lot-level realized PnL, and full counterfactual analysis require additional observability or formal contracts.

## 2. Scope and Non-goals

Scope:

- Inventory Phase20 performance evidence.
- Classify each item as `AVAILABLE`, `DERIVABLE`, `MISSING`, `NOT_AVAILABLE`, `NOT_APPLICABLE`, or `AUTHORITY_CONFLICT`.
- Identify artifact authority and join keys.
- Separate Runtime correctness from Strategy Performance.
- Preserve Phase19-BY Run Authority rules.

Non-goals:

- No AI, Opportunity, BUY, HOLD, ADD, REDUCE, EXIT, PM, Risk, Capital Allocation, or Runtime logic changes.
- No training, calibration, validation, Accepted Generation creation, Runtime transition, Broker access, order placement, long Historical Smoke, or full backtest.
- No use of performance results as Training, Calibration, Validation, or Accepted Generation authority.

## 3. Reviewed Architecture and Phase Reports

Reviewed Architecture SoT:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/ai_training_and_generation_lifecycle.md`
- `docs/02_architecture/ai_generation_artifact_contract.md`
- `docs/01_requirements/phase_roadmap.md`

Reviewed handoff and closure reports:

- `docs/phase_reports/phase18_final_summary_and_phase19_handoff.md`
- `docs/phase_reports/phase18_to_phase19_chatgpt_handoff.md`
- `docs/phase_reports/phase18_u_final_independent_contract_closure_review.md`
- `docs/phase_reports/phase18_af_autonomous_ai_operations_architecture_final_consistency_amendment.md`
- `docs/phase_reports/phase19_bx_final_independent_implementation_review.md`
- `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`
- `docs/phase_reports/phase19_final_summary_and_phase20_handoff.md`
- `docs/phase_reports/phase19_to_phase20_chatgpt_handoff.md`

Key constraints carried forward:

- Runtime BUY AI authority is the current `COMMITTED` Accepted Generation only.
- Runtime owns Current, Pending, Ledger, PM, Safety, Broker boundary, cash, positions, submit, execution, and reporting.
- Generation owns Dataset, Split, Candidate, Opportunity, Calibration, Validation, Baseline/Freshness, hashes, and authority decision.
- BUY Lifecycle Gate controls BUY planning or scoped BUY block only; SELL continuity is separately evaluated.
- Latest path, mtime, max-date, manual path, legacy fallback, and Promotion Candidate fallback are not Runtime BUY authority.

## 4. Reviewed Accepted Generation Authority

Pointer:

```text
.runtime/runtime_state/accepted_buy_ai_bundle.json
```

Observed:

```text
accepted_generation_id = phase19_aq_accepted_generation_641e6e313543f013
transaction_state = COMMITTED
aggregate_hash = b97d3ccb14448b6ac721afcd93acedbabf4275712bb07816f13c322b2045480b
manifest_hash = dbaf3c10f1f9f0d0c414a4fee23153a3fd4acd2efa48463de5866872aa5931e2
accepted_at = 2026-07-20T00:00:00+09:00
effective_from = 2026-07-20T00:00:00+09:00
```

Manifest:

```text
.runtime/ai_lifecycle/generations/phase19_aq_accepted_generation_641e6e313543f013/accepted_generation_manifest.json
```

Reviewed bindings:

- Candidate model, scaler, calibration, validation refs and hashes are manifest-bound.
- Opportunity model, scaler, calibration, validation refs and hashes are manifest-bound.
- Dataset revision IDs are bound.
- Freshness taxonomy is separated into raw, normalized, dataset, label-safe, training, accepted-generation age, runtime-loaded generation, and inference-feature freshness.
- Training cutoff is `2024-12-02`; calibration cutoff is `2025-12-01`; validation cutoff is `2026-03-03`; label-safe cutoff is `2026-06-04`.

Phase20 may use this generation identity for attribution lineage. It must not use performance results to alter this authority.

## 5. Reviewed Runtime Test Runs

20BD baseline run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T213848054826Z/
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T213848054826Z-20260721T221640818568Z/summary.json
```

Run-scoped evidence includes:

- `run_state.json`
- `plan.json`
- `fresh_run_summary.json`
- `final_summary.json`
- `daily/<DATE>/market_refresh/`
- `daily/<DATE>/data_readiness/`
- `daily/<DATE>/morning/`
- `daily/<DATE>/sell_planning/`
- `daily/<DATE>/submit/`
- `daily/<DATE>/execution/`
- `daily/<DATE>/current_valuation_refresh/`
- `daily/<DATE>/runtime_state_refresh/`

1BD BY confirmation run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260721T224645728185Z/
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T224645728185Z-20260721T230200658392Z/summary.json
```

The 1BD run confirms the corrected summarize authority. It is not strategy performance evidence.

## 6. Artifact Inventory

| Artifact | Status | Authority | Scope | Principal fields | Join keys | Phase20 use |
|---|---|---|---|---|---|---|
| 20BD `run_state.json` | AVAILABLE | Run state | Run-scoped immutable evidence | `completed_business_days`, `status`, `run_id` | `run_id`, `business_date` | Event aggregation boundary |
| 20BD `plan.json` | AVAILABLE | Runtime Test plan | Run-scoped immutable evidence | business dates, initial cash, external-effect policy | `run_id`, `business_date` | Test profile, initial assumptions |
| 20BD summary `summary.json` | AVAILABLE | Runtime Test summarize output | Summary evidence | performance, trading, PM, lifecycle, current positions | `run_id`, `business_date`, `symbol` | Baseline metrics and counts |
| 20BD daily stage evidence | AVAILABLE | Run-scoped copied evidence | Run-scoped | manifests, CLI results, stage evidence | `run_id`, `business_date`, stage | Stage-level lineage |
| Candidate decisions | DERIVABLE | Accepted Generation-bound Runtime output | Shared `.runtime` detail with date semantics | candidate rows/count, feature date, schema status | `business_date`, `symbol`, generation | Candidate attribution detail, with BY caution |
| Opportunity rankings | DERIVABLE | Accepted Generation-bound Runtime output | Shared `.runtime` detail with date semantics | `rankings`, score, rank, confidence, reason | `business_date`, `symbol`, rank | BUY attribution and missed-candidate comparison |
| Opportunity inference parquet | DERIVABLE | Runtime BUY AI output | Shared `.runtime` detail with date semantics | Top50 opportunity rows | `target_date`, `code` | Full candidate/ranking analysis |
| BUY planning evidence | AVAILABLE | Run-scoped morning evidence | Run-scoped | selected symbols, sizing, eligibility, policy | `business_date`, `symbol` | BUY attribution |
| BUY order plan body | DERIVABLE_WITH_GAP | Runtime morning artifact | Shared history path referenced by run evidence | item quantity/price/policy | `business_date`, `order_plan_item_id`, `symbol` | BUY execution linkage; incomplete if shared state overwritten |
| Approval | DERIVABLE_WITH_GAP | Runtime approval artifact | Shared history path referenced by run evidence | approval id/status/item ids | `approval_id`, `pending_plan_id` | Plan-to-submit linkage |
| Submit manifest | AVAILABLE | Run-scoped submit evidence | Run-scoped | runtime_test_run_id, policy, safety, generated artifacts | `run_id`, `business_date`, `pending_plan_id` | Submit boundary |
| Execution manifest | AVAILABLE | Run-scoped execution evidence | Run-scoped | runtime_test_run_id, generated artifacts, safety | `run_id`, `business_date` | Execution boundary |
| Ledger append evidence | AVAILABLE | Run-scoped execution evidence | Run-scoped | append status by ledger stream | `business_date`, ledger stream | Ledger update verification |
| Persistent ledger current files | AUTHORITY_CONFLICT_FOR_20BD_EVENTS | Shared Runtime Current | Shared mutable final state | orders/executions/positions/cash/state | order/execution/symbol | Detail only when final hashes match; not 20BD count authority after BY |
| PM evidence | AVAILABLE | Run-scoped sell planning evidence | Run-scoped | PM decision counts, status, feature source | `run_id`, `business_date`, `symbol` | PM distribution and temporal checks |
| PM decision detail | DERIVABLE_WITH_GAP | PM artifact referenced by run evidence | Shared date detail | decisions and reasons | `business_date`, `symbol` | HOLD/ADD/REDUCE/EXIT attribution |
| SELL planning manifest | AVAILABLE | Run-scoped sell planning evidence | Run-scoped wrapper | source manifest path, runtime_test_run_id | `run_id`, `business_date` | SELL stage lineage |
| SELL order plan body | DERIVABLE_WITH_CAUTION | Runtime sell history artifact | Shared date detail | SELL items, source decisions | `business_date`, `symbol`, item id | REDUCE/EXIT analysis; count authority remains summary/run |
| Current valuation evidence | AVAILABLE | Run-scoped valuation evidence | Run-scoped | valuation apply status, market date, PnL status | `business_date`, `symbol` | Daily equity/valuation derivation |
| Market refresh evidence | AVAILABLE | Run-scoped market evidence | Run-scoped | latest available market date, as-of view | `business_date`, market date | Temporal integrity |
| Feature refresh evidence | AVAILABLE | Run-scoped feature evidence | Run-scoped | candidate feature path, data_until, jquants_only | `business_date`, feature date | Leakage audit |
| Trade attribution | AVAILABLE | Summary output | Summary evidence | sell_trades, reduce/exit linkage | `business_date`, `symbol` | SELL attribution seed |
| Benchmark / sector returns | MISSING | Not present in Phase20-A evidence | N/A | N/A | date, sector, index | Market regime and relative performance |

## 7. Authority Matrix

| Area | Primary authority | Secondary/detail authority | Forbidden authority |
|---|---|---|---|
| Run event counts | `reports/runtime_tests/runs/<RUN_ID>/run_state.json` and run-scoped evidence | `summary.json` produced from run-scoped evidence | Shared `.runtime` scan across dates |
| Final 20BD performance | 20BD summary and 20BD final summary | Run daily valuation evidence | 1BD final state or current shared `.runtime` after later runs |
| BUY AI authority | COMMITTED Accepted Generation pointer and manifest | Generation-bound runtime output | latest, mtime, manual path, legacy fallback |
| Candidate/Opportunity detail | Generation-bound buy_ai artifacts for same business date | Parquet/CSV detail with hash/date checks | unrelated date or post-run latest selection |
| PM event counts | Run-scoped sell planning PM evidence | Summary PM distribution | shared PM directories without completed-day filtering |
| SELL event counts | Run-scoped sell planning/submit/execution evidence | Summary lifecycle consistency | shared sell pipeline scan without run filtering |
| Ledger/current consistency | Summary lifecycle check and final hashes | Run-scoped execution/valuation evidence | treating missing current as zero position |

## 8. Run-scoped vs Shared Artifact Matrix

Run-scoped artifacts are authoritative for the 20BD run. Shared `.runtime` artifacts are detail references only when their business date, runtime identity, and final hash context are compatible.

| Artifact group | Run-scoped? | Shared? | Phase20 handling |
|---|---:|---:|---|
| `run_state`, `plan`, `fresh_run_summary`, `final_summary` | yes | no | Use as primary |
| Daily CLI result and runtime manifest copies | yes | source path references shared original | Use run copy as primary |
| Market/feature refresh copies | yes | yes | Use run copy for temporal status |
| Morning planning evidence | yes | yes | Use run copy for selected symbols and sizing |
| BUY AI rankings | no copied artifact found in daily run evidence | yes | Use with caution as date-bound detail, not event count authority |
| PM evidence | yes | yes | Use run copy for counts/status |
| PM decisions body | partial via summary/run evidence; detail may be shared | yes | Derivable with caution |
| SELL order plans | wrapper copied; body may be shared | yes | Use summary for counts, shared body for inspected detail only |
| Persistent ledger current files | no stable 20BD copy in inspected top-level evidence | yes mutable | Do not use as 20BD count authority after later 1BD run |

## 9. Performance Metric Availability Matrix

| Metric | Status | Authority / derivation |
|---|---|---|
| Initial Equity | AVAILABLE | 20BD `summary.performance.initial_equity` |
| Final Equity | AVAILABLE | 20BD `summary.performance.final_equity` |
| Total Return | AVAILABLE | `final_equity - initial_equity`; already in summary |
| Return Rate | AVAILABLE | 20BD summary |
| Realized PnL | AVAILABLE | 20BD summary, method `current_state.realized_pnl` |
| Unrealized PnL | AVAILABLE | 20BD summary |
| Daily Equity Curve | DERIVABLE | Daily `current_valuation_refresh` manifests and valuation evidence; requires extraction |
| Maximum Drawdown | DERIVABLE | Daily equity curve after extraction |
| Gross Exposure | DERIVABLE | Daily market value / equity from valuation/current evidence |
| Net Exposure | DERIVABLE | Cash-equity-only long book: same as gross exposure if no shorts; confirm from positions |
| Cash Ratio | DERIVABLE | Daily cash / equity from current/valuation evidence |
| Cash Utilization | DERIVABLE | 1 - cash ratio |
| Turnover | DERIVABLE | Absolute traded notional / equity from execution evidence |
| BUY Count | AVAILABLE | 20BD summary `trading.buy_execution_count = 5` |
| SELL Count | AVAILABLE | 20BD summary `trading.sell_execution_count = 7` |
| Holding Period | DERIVABLE_WITH_GAP | Needs position open/close linkage by symbol and quantities; no stable lot id observed |
| Win Rate | DERIVABLE_WITH_GAP | Closed SELL PnL per realized lot required; summary has aggregate realized PnL |
| Profit Factor | DERIVABLE_WITH_GAP | Requires per-trade realized gains/losses |
| Average Win | DERIVABLE_WITH_GAP | Requires per-trade realized gains |
| Average Loss | DERIVABLE_WITH_GAP | Requires per-trade realized losses |
| Largest Win | DERIVABLE_WITH_GAP | Requires per-trade realized gains |
| Largest Loss | DERIVABLE_WITH_GAP | Requires per-trade realized losses |
| Loss Concentration | DERIVABLE_WITH_GAP | Requires symbol-level realized/unrealized PnL |
| Symbol-level PnL Contribution | DERIVABLE_WITH_GAP | Final open positions available; closed realized by symbol needs ledger/SELL attribution extraction |
| Sector-level PnL Contribution | MISSING | Sector mapping and sector return attribution not present in reviewed evidence |

## 10. Trade and Position Joinability Matrix

| Lifecycle edge | Status | Candidate keys | Notes |
|---|---|---|---|
| Candidate -> Opportunity | AVAILABLE | `business_date`, `symbol/code`, `candidate_rank`, generation | Opportunity rankings include candidate rank/score |
| Opportunity -> BUY Decision | AVAILABLE | `business_date`, `symbol`, `buy_rank`, eligibility evidence | Morning planning evidence includes opportunity eligibility |
| BUY Decision -> Plan | AVAILABLE | `business_date`, `symbol`, selected symbols, sizing | Plan item IDs may require shared body |
| Plan -> Approval | DERIVABLE_WITH_GAP | `order_plan_id`, `approval_id`, `pending_plan_id` | Approval body may be source-path detail |
| Approval -> Submit | DERIVABLE | `pending_plan_id`, approved item IDs, submit manifest | Submit wrapper is run-scoped |
| Submit -> Execution | DERIVABLE | `pending_item_id`, `order_id`, `business_date`, symbol | Execution evidence exists; exact body may require source manifests |
| Execution -> Ledger | AVAILABLE | execution stage, ledger append evidence | Append success is run-scoped |
| Ledger -> Current Position | AVAILABLE_FOR_CONSISTENCY | summary lifecycle `LEDGER_TO_CURRENT` | Mutable shared ledger not current 20BD detail authority after later run |
| Current Position -> PM Decision | AVAILABLE | `business_date`, `symbol`, PM evidence | PM counts in run-scoped evidence |
| PM REDUCE/EXIT -> SELL Plan | AVAILABLE | `business_date`, `symbol`, source decision | Summary reduce/exit items provide linkage |
| SELL Plan -> Execution | AVAILABLE | `business_date`, `symbol`, submitted SELL count | Summary lifecycle PASS |
| Execution -> Final Position | AVAILABLE_FOR_CONSISTENCY | final summary hashes and summary positions | Lot-level open/closed attribution incomplete |

## 11. BUY Attribution Readiness

Available or derivable for 20BD initial BUYs:

- `symbol`
- purchase date
- estimated purchase price and quantity from morning planning evidence
- capital allocated / estimated amount
- opportunity score / rank / reason from eligibility and rankings
- candidate score / candidate rank from opportunity rankings
- generation lineage from Accepted Generation
- feature date and business date
- closed/open status from final positions and SELL attribution

Gaps:

- Stable lot ID was not observed in the inspected ledger/state samples.
- Full all-candidate exclusion reasons are only partially available. Opportunity Top50 exists; full universe below Top50 is not confirmed.
- Post-purchase MFE/MAE and ending return are derivable from market/valuation data but not precomputed.
- Confidence exists in `opportunity_rankings.json`; calibration result is manifest-bound, but per-row calibrated probability semantics need extraction before use.

## 12. HOLD / ADD Attribution Readiness

Available:

- PM decision counts by date from 20BD summary.
- PM reasons distribution from 20BD summary.
- Run-scoped PM evidence per date with feature source, feature date, current source, and temporal validation status.
- HOLD and ADD are explicit PM decisions, not merely absence of SELL.

Derivable:

- Per-symbol HOLD/ADD decision detail from PM decision artifacts when compatible with run date.
- Post-decision returns, MFE, MAE from market data and valuation evidence.
- ADD concentration change from current/position quantities if position histories are reconstructed.

Gaps:

- Incremental PnL from ADD needs lot/quantity-level attribution that is not yet formalized.
- Thresholds/confidence for PM decisions are not summarized as a metric contract.

## 13. REDUCE / EXIT Attribution Readiness

Available:

- REDUCE count `4` and EXIT count `3`.
- Summary `reduce_exit.items` includes business date, symbol, source decision, quantity, position quantity before, sellable quantity, reduce ratio, expected remaining quantity, and quantity contract version.
- SELL plan/submit/execution lifecycle consistency is PASS.

Derivable:

- Execution price and realized PnL by sale from execution/ledger details.
- Remaining quantity after each REDUCE/EXIT from summary and current evidence.
- Post-sale price series and counterfactual hold return from market data as post-hoc evaluation.

Gaps:

- Loss avoided, profit missed, and timing lag are not precomputed.
- Counterfactual hold return must be clearly labeled post-hoc and cannot become Runtime decision input.

## 14. Market Regime Readiness

Status:

```text
MARKET_REGIME_READINESS = MISSING_FOR_BENCHMARK_AND_SECTOR_ANALYSIS
```

Available:

- Run-scoped market refresh and historical as-of evidence.
- J-Quants-derived quote/feature artifacts for traded symbols.

Missing in reviewed evidence:

- TOPIX returns.
- Nikkei 225 returns.
- Benchmark-relative return.
- Market volatility classification.
- Uptrend/downtrend/range labels.
- Large-cap/small-cap, growth/value regime labels.
- Sector return time series.

Phase20-A did not fetch external data or implement benchmark logic.

## 15. Risk Attribution Readiness

Available or derivable:

- Symbol concentration from daily/final position market values.
- Cash utilization from daily equity/cash.
- Gross exposure and single-name allocation from daily valuation/current evidence.
- ADD-driven concentration changes after reconstructing daily positions.
- Price-band concentration from traded symbol price levels.

Missing or incomplete:

- Sector concentration requires sector mapping.
- Liquidity and gap risk need volume/price history extraction and metric definitions.
- Loss concentration needs symbol-level realized and unrealized PnL attribution.

## 16. Existing Analysis Artifact Audit

Reviewed:

- 20BD `summary.json`
- 20BD `summary.txt`
- 20BD `final_summary.json`
- Phase19-BX review JSON
- Phase19-BY correction JSON
- 1BD BY `summary.json`

Already computed:

- Total return.
- Return percent.
- Realized/unrealized PnL aggregate.
- BUY/SELL execution counts.
- PM distribution and reason distribution.
- REDUCE/EXIT linkage.
- Lifecycle consistency.
- External-effect boundary.
- Final positions.

Not yet formalized:

- Benchmark comparison.
- Experiment comparison schema.
- Daily equity curve metric contract.
- Drawdown/Sharpe/Sortino.
- Per-lot realized PnL.
- Sector attribution.
- Counterfactual REDUCE/EXIT evaluation.

## 17. Temporal Integrity and Leakage Audit

Reviewed temporal fields:

- Accepted Generation `accepted_at` and `effective_from`: `2026-07-20T00:00:00+09:00`.
- Generation-bound cutoffs: training `2024-12-02`, calibration `2025-12-01`, validation `2026-03-03`, label-safe cutoff `2026-06-04`.
- Run business dates: `2026-06-17` to `2026-07-14`.
- Run-scoped `historical_asof_view.json` records `future_rows_excluded_from_consumer`.
- Feature refresh evidence records `data_until`, `business_date`, and `jquants_only`.
- Opportunity inference audit records forbidden/future/leakage column counts.

Risk assessment:

- No blocking leakage evidence was found in reviewed artifacts.
- Data files may contain rows beyond a consumer date; this is not leakage unless the consumer used future rows.
- Phase20 analysis may use future price series only for post-hoc attribution, MFE/MAE, drawdown, and counterfactual review, never as Runtime decision input or training authority.

## 18. Missing Evidence

Missing or insufficient for full Phase20 attribution:

- Formal Performance Metric Contract.
- Benchmark Contract.
- Experiment Comparison Contract.
- Benchmark index time series and sector return artifacts.
- Stable lot-level realized PnL attribution.
- Complete per-trade win/loss table.
- Full all-universe candidate exclusion evidence below persisted Top50.
- PM threshold/confidence metric contract.
- Formal daily equity curve artifact.
- Sector mapping and sector concentration evidence.
- Counterfactual hold-return artifact for REDUCE/EXIT.

## 19. Derivable Metrics

Derivable with short read-only extraction:

- Daily equity curve from daily valuation/current evidence.
- Maximum drawdown from daily equity curve.
- Cash ratio and cash utilization from daily cash/equity.
- Gross exposure and single-name concentration from daily market value/equity.
- Turnover from execution notional.
- BUY attribution table from planning evidence plus opportunity rankings.
- REDUCE/EXIT table from summary plus execution evidence.
- Holding period approximation by symbol and quantity changes, with caveat about missing lot ID.
- Symbol-level open PnL from final positions.
- Partial symbol-level closed PnL if execution/ledger records can be reconstructed per symbol.

## 20. Authority Conflicts

No blocking authority conflict was found for the high-level 20BD baseline.

Non-blocking authority cautions:

- Shared `.runtime` currently reflects a later 1BD run for some Current/Ledger artifacts. It must not be used as 20BD event-count authority.
- Some run-scoped files are wrappers whose `source_manifest_path` points to shared `.runtime` paths. The copied run evidence remains authority; source paths are references, not automatic current truth.
- BUY AI ranking artifacts are shared date-scoped details, not run event-count authority. They are usable for attribution only with date/generation checks.

## 21. Gap Classification

| Gap | Classification | Impact |
|---|---|---|
| BX-F01 metric/benchmark/experiment contracts not formalized | EVIDENCE_OBSERVABILITY / CONTRACT_MISMATCH | First follow-up before optimization comparison |
| Benchmark and sector data missing | MARKET_REGIME / EVIDENCE_OBSERVABILITY | Blocks benchmark-relative attribution |
| Lot-level realized PnL not formalized | EVIDENCE_OBSERVABILITY | Limits win rate/profit factor precision |
| Full candidate-universe exclusion not confirmed | OPPORTUNITY_RANKING / EVIDENCE_OBSERVABILITY | Limits opportunity-quality analysis |
| PM confidence/threshold metrics not summarized | POSITION_MANAGEMENT / EVIDENCE_OBSERVABILITY | Limits HOLD/ADD/REDUCE diagnostics |
| Negative 20BD return | STRATEGY_PERFORMANCE | Analysis target; not Runtime failure |

No Runtime implementation defect was identified by Phase20-A.

## 22. Recommended Next Analysis Sequence

1. Create Phase20-B Performance Metric / Benchmark / Experiment Comparison Contract.
2. Build a read-only 20BD baseline extraction table from run-scoped evidence.
3. Compute daily equity curve, drawdown, exposure, cash utilization, and turnover.
4. Build BUY attribution table joining selected symbols, sizing, opportunity rank/score, and final/closed outcome.
5. Build PM attribution table for HOLD/ADD/REDUCE/EXIT with per-decision post-hoc returns.
6. Add benchmark and sector evidence only after the benchmark contract is approved.
7. Only after attribution identifies a grounded target, decide whether the issue is Strategy Performance, Opportunity Ranking, BUY Policy, PM, Risk/Capital Allocation, Test Profile, Evidence/Observability, or Runtime implementation.

## 23. Final Judgment

```text
PHASE20_A_EVIDENCE_INVENTORY_COMPLETE_WITH_DERIVABLE_GAPS
```

Phase20 can proceed to baseline metric contract and read-only baseline extraction. It should not change AI, PM, Risk, Capital Allocation, Runtime Architecture, or Accepted Generation authority yet.
