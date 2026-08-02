# Phase24-A Performance Evaluation Contract

## 1. Primary Judgment

`PHASE24_A_PERFORMANCE_EVALUATION_CONTRACT_COMPLETE`

Phase24-A defines the Performance Evaluation Contract for Phase24. It does not perform performance improvement, Runtime repair, Strategy parameter change, threshold change, source repair, or preflight repair.

Phase24 inherits the Phase20-B metric / benchmark / experiment comparison contract and tightens it for Phase24 governance:

- Performance evidence is post-hoc diagnostic evidence.
- Runtime correctness and Performance evaluation are separate axes.
- Missing metrics are never zero-filled.
- Benchmark-relative metrics remain `MISSING` until an approved benchmark source exists.
- One experiment changes one hypothesis by default.
- Runtime PnL, Paper Ledger, selected/bought flags, cash, portfolio value, broker snapshots, test result, audit result, future price, and future return must not become learning, Runtime, Calibration, Validation, or automatic promotion authority.

## 2. Scope

In scope:

- Evaluation metrics and metric status rules.
- Benchmark contract.
- Baseline contract.
- Experiment comparison contract.
- Attribution contract.
- Phase24 performance gap inventory.
- Operator Runtime Matrix for future evaluations.
- Runtime correctness / performance responsibility boundary.

Out of scope:

- Runtime modification.
- Authority modification.
- Strategy, PM, Position Sizing, Market Context, Cash Ratio, threshold, or configuration changes.
- Corporate Event, source, preflight, or benchmark source repair.
- Runtime execution, fresh-run, resume, Broker Write, Runtime Switch, J-Quants fetch, or Accepted Generation promotion.

Reviewed documents:

- `docs/phase_reports/phase23_to_phase24_chatgpt_handoff.md`
- `docs/phase_reports/phase23_final_summary_and_phase24_handoff.md`
- `docs/phase_reports/phase23_bv_phase21_design_conformance_full_architecture_runtime_evidence_closure_review.md`
- `docs/phase_reports/phase24_a0_bu_post_repair_close_runtime_revalidation_entry_gate_preparation.md`
- `docs/phase_reports/phase24_a0r1_historical_10bd_plan_preflight_source_readiness_root_cause_audit.md`
- `docs/phase_reports/phase24_a0r2_canonical_fresh_run_dry_run_and_post_reset_planning_gate_verification.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/01_requirements/strategy_performance_acceptance_contract.md`
- `docs/03_operations/runtime_test_command_guide.md`
- Performance-related Phase20 reports.

## 3. Evaluation Metrics

Contract versions:

```text
phase24_performance_evaluation_contract_version = phase24_a_performance_evaluation_contract.v1
base_metric_contract = phase20_b_performance_metric_contract.v1
base_benchmark_contract = phase20_b_benchmark_contract.v1
base_experiment_contract = phase20_b_experiment_comparison_contract.v1
```

Metric status taxonomy:

| Status | Meaning |
|---|---|
| `AVAILABLE` | Value exists in authoritative run evidence. |
| `DERIVABLE_EXACT` | Can be computed exactly from authoritative artifacts. |
| `DERIVABLE_APPROXIMATE` | Can be computed from authoritative artifacts, but the unit is approximate, usually due to missing stable lot IDs. |
| `DERIVABLE_PARTIAL` | Can be computed only for a subset or with known coverage gaps. |
| `MISSING` | Required authority/source/evidence does not exist. |
| `NOT_AVAILABLE` | Intentionally unavailable at current test level/profile. |
| `NOT_APPLICABLE` | Not applicable to the run. |
| `AUTHORITY_CONFLICT` | Multiple candidate authorities conflict or source is invalid. |
| `POST_HOC_ATTRIBUTION_ONLY` | Diagnostic outcome only; forbidden as Runtime/Training/Calibration/Validation authority. |

Every metric output must include:

```text
metric_id
metric_name
value
unit
status
confidence_class
definition
calculation_formula
authority
producer
consumer
source_artifacts
missing_data_policy
temporal_safety
limitations
warnings
contract_version
```

Metric registry:

| Metric | Definition | Calculation | Authority | Producer | Consumer | Missing handling |
|---|---|---|---|---|---|---|
| Initial equity | Equity at run start | From plan/fresh-run initial state; normally initial cash + initial positions market value | Plan / fresh-run summary | Runtime Test runner | Performance summary, baseline comparison | `MISSING` if plan authority absent |
| Final equity | End equity after final completed day valuation | `cash + market_value` | Final Current / final summary / run-scoped valuation | Runtime current valuation / close | Return, drawdown, baseline | `AUTHORITY_CONFLICT` if final hashes or valuation disagree |
| Total return | Absolute PnL over period | `final_equity - initial_equity` | Initial/final equity authority | Performance summarizer | Operator review | `MISSING` if either equity missing |
| Total return rate | Period return ratio | `total_return / initial_equity` | Initial/final equity authority | Performance summarizer | Operator review | `MISSING`; never infer denominator |
| Annualized return | 252BD annualized return display | `(final_equity / initial_equity) ** (252 / completed_business_days) - 1` | Equity curve / completed business days | Performance summarizer | Diagnostic only until sufficient horizon | Display with `SHORT_PERIOD_UNRELIABLE` under 60BD; no +50% judgment under 252BD |
| CAGR | Multi-period annual growth rate | Same compounding formula, using actual completed business-day count; official CAGR only at >=252BD | Equity curve | Performance summarizer | Long-run evaluation | `NOT_AVAILABLE` for very short runs; warning under 252BD |
| Max drawdown | Worst mark-to-market drawdown | `min((equity[d] - running_peak[d]) / running_peak[d])` | Daily equity curve | Performance summarizer | Risk review | `MISSING` if daily equity incomplete; no interpolation |
| Volatility | Return variability | Std dev of daily returns, annualized by `sqrt(252)` for annual display | Daily equity curve | Performance summarizer | Risk review | `MISSING` if fewer than two daily returns |
| Sharpe ratio | Return per unit volatility | Mean daily excess return over cash diagnostic baseline / std daily returns * `sqrt(252)` | Daily equity curve; cash benchmark only as explicit diagnostic | Performance summarizer | Risk-adjusted review | `MISSING` if volatility unavailable; label cash baseline explicitly |
| Sortino ratio | Return per downside volatility | Mean daily excess return / downside std of negative daily returns * `sqrt(252)` | Daily equity curve | Performance summarizer | Downside-risk review | `MISSING` if no downside sample or insufficient observations |
| Win rate | Share of winning realized outcome units | Winning realized slices / realized slices | `realized_slices.json` or average-cost realized PnL evidence | Execution / performance observability | Trade outcome review | `DERIVABLE_APPROXIMATE`; `MISSING` if no slice authority |
| Profit factor | Gross realized gains vs losses | `sum(winning_slice_pnl) / abs(sum(losing_slice_pnl))` | Realized slices | Performance summarizer | Trade outcome review | `DERIVABLE_APPROXIMATE`; if no losses, report structured `NOT_APPLICABLE`/infinite policy, not zero |
| Payoff ratio | Average win vs average loss | `avg(win_pnl) / abs(avg(loss_pnl))` | Realized slices | Performance summarizer | Trade quality review | `DERIVABLE_APPROXIMATE`; missing if no win/loss unit |
| Turnover | Trading activity relative to equity | `sum(abs(executed_gross_notional)) / average_equity` | Canonical execution evidence and equity curve | Execution / performance summarizer | Cost/risk review | `MISSING` if execution notional or average equity missing |
| Cash utilization | Deployed capital ratio | `1 - cash / equity` | Daily Current / valuation | Runtime current valuation / summarizer | Zero deployment / cash drag review | `MISSING` if cash/equity absent; no zero fill |
| Gross exposure | Absolute market exposure | `sum(abs(open_position_market_value)) / equity` | Current valuation / positions | Runtime valuation | Risk and concentration review | `MISSING` if unpriced position |
| Net exposure | Directional exposure | `(long_market_value - short_market_value) / equity`; equals gross only in proven long-only cash-equity runs | Current valuation / positions | Runtime valuation | Risk review | `AUTHORITY_CONFLICT` if short/margin status unknown |
| Holding period | Time capital is held | Position campaign / lifecycle business-day duration; capital-weighted optional | Position campaign evidence / executions | Performance observability | PM and entry/exit review | `DERIVABLE_PARTIAL` without stable lot IDs |
| Trade count | Number of canonical execution events/orders | Count by side and action from run-scoped execution evidence | Execution fills / run evidence | Runtime execution | Activity review | `MISSING` if execution evidence absent |
| BUY_NEW | New position buys | Count and notional of BUY executions that open new symbol campaign | Execution + position campaign | Runtime execution / performance observability | Entry quality review | `MISSING` if action classification absent |
| BUY_ADD | Additional buys | Count and notional of ADD executions increasing an existing campaign | PM / execution / campaign evidence | Runtime execution / PM | ADD quality review | `MISSING` if ADD linkage absent |
| SELL_REDUCE | Partial sell | Count/notional where position remains open after sell | PM / sell planning / execution | Sell planning / execution | Profit capture and risk review | `NOT_AVAILABLE` until runtime verified; `MISSING` if linkage absent |
| SELL_EXIT | Full position exit | Count/notional where symbol campaign closes | PM / sell planning / execution | Sell planning / execution | Exit quality review | `MISSING` if campaign close linkage absent |
| Realized PnL | Closed/sold-quantity PnL | Average-cost realized slices from canonical executions | Execution / ledger realized slices | Runtime execution / performance observability | Return, win/loss, loss attribution | Fees/tax/slippage `NOT_AVAILABLE`; do not assume zero unless evidence says profile excludes them |
| Unrealized PnL | Open-position mark-to-market PnL | Open market value minus cost basis | Current valuation / final current | Runtime current valuation | Return and open risk review | `MISSING` if valuation missing |

Observation minimums:

| Use | Minimum |
|---|---:|
| Display period return | 1 completed business day with valid equity |
| Display annualized return with warning | 20 completed business days |
| Remove short-period warning | 60 completed business days |
| Judge against annual +50% target | 252 completed business days |
| Multi-period robustness | Alternate periods and out-of-period windows |

## 4. Benchmark Contract

Primary benchmark:

```text
benchmark_id = TOPIX_TOTAL_OR_PRICE_RETURN_JQUANTS_COMPATIBLE
benchmark_name = TOPIX
status = MISSING_UNTIL_JQUANTS_COMPATIBLE_SOURCE_CONFIRMED
```

Benchmark rules:

| Item | Contract |
|---|---|
| Benchmark source | Approved J-Quants-compatible benchmark source only. |
| Historical benchmark authority | PIT benchmark time series aligned to completed business days. |
| Benchmark return | Benchmark equity curve normalized to strategy initial equity, then period return. |
| Relative return | `strategy_return - benchmark_return` over identical completed business dates. |
| Excess return | Same as relative return unless a separate risk-free benchmark is approved. |
| Benchmark availability | `AVAILABLE` only when source, date coverage, return type, and hash/lineage are recorded. |
| Missing benchmark | Report `MISSING`; do not substitute cash, zero return, or TOPIX proxy. |
| Secondary benchmarks | Cash diagnostic `DERIVABLE_EXACT`; Nikkei 225 and equal-weight eligible universe remain `MISSING` until approved. |

Current Phase24 status:

- TOPIX benchmark remains `MISSING`.
- Cash can be used only as explicit no-risk/opportunity-cost diagnostic.
- Cash must not be described as TOPIX or market benchmark.

## 5. Baseline Contract

A Phase24 baseline is immutable only when all identity fields and evidence hashes are recorded.

Required baseline fields:

| Field | Contract |
|---|---|
| Runtime version | Source commit, dirty flag, Runtime architecture version, command version. |
| Accepted Generation | Accepted generation id, transaction state, manifest hash, aggregate hash. |
| Strategy version | Strategy source commit/config hashes and relevant artifact contract versions. |
| Configuration hash | Runtime profile, Strategy config, Safety config, external-effect policy. |
| Authority hash | Run-scoped source manifests, accepted bundle, final state hashes, plan hash. |
| Date range | Requested and completed business dates. |
| Business day count | Requested, resolved, completed, and valid metric observation count. |
| Run profile | Profile id and profile file hash. |
| Run command | Exact command, including initial cash and mutation confirmation flags for actual Operator runs. |
| Run ID | Runtime Test run id. |
| Evidence hash | Run directory hash, final summary hash, summary evidence hash when generated. |
| Initial state | Cash, buying power, initial positions, pending, open orders, executions, realized/unrealized PnL. |
| External effects | Broker write, external delivery, J-Quants fetch, Tachibana API flags. |
| Metric contract | Metric, benchmark, and experiment contract versions. |

Baseline comparison requires:

- Same metric contract.
- Same benchmark contract.
- Same date window unless explicitly classified as cross-period robustness, not direct A/B.
- Same initial cash and initial position policy.
- Same external-effect policy.
- Same Runtime / Strategy authority unless the experiment explicitly declares the changed component.

Phase23-BT 10BD evidence is a Runtime correctness baseline and short performance seed. It is not sufficient statistical performance acceptance.

## 6. Experiment Contract

Core rule:

```text
1 hypothesis
1 declared change
1 comparison contract
```

Every experiment record must include:

| Field | Required content |
|---|---|
| Before | Baseline run id, metrics, evidence hash, authority identities. |
| After | Candidate run id, metrics, evidence hash, authority identities. |
| Changed component | Exactly one default target: Market Context, Portfolio Policy, Capital Deployment, Portfolio Construction, Position Sizing, PM, Candidate, Opportunity, or source/authority only if the task is explicitly not a performance experiment. |
| Change reason | Hypothesis stated before execution. |
| Expected effect | Metric movement expected and why. |
| Side effects | Known risk: drawdown, turnover, concentration, cash drag, execution count, source coverage. |
| Regression scope | Runtime correctness, Authority, Safety, PIT, NO_LEAKAGE, benchmark/metric contract, close validation. |
| Evaluation period | Business dates, profile, observation count, regime label when available. |
| Comparison method | `COMPARABLE`, `COMPARABLE_WITH_CAVEATS`, or `NOT_COMPARABLE`. |

Experiment comparison is `NOT_COMPARABLE` if:

- Runtime correctness fails.
- Authority, PIT, Safety, or leakage gate fails.
- Business dates differ for direct A/B.
- Initial cash or initial positions differ without explicit classification.
- Metric definitions differ.
- More than one causal component changes without multi-factor label.
- Benchmark/source change is mixed with Strategy logic change.

Performance improvement cannot be accepted solely on return. Drawdown, volatility, turnover, exposure, concentration, cash utilization, and out-of-period behavior must be reviewed.

## 7. Attribution Contract

Attribution is post-hoc diagnostic. It may motivate a review or future hypothesis, but it must not become Runtime or Training authority without a separate approved contract.

| Attribution area | Definition | Current evidence status | Use |
|---|---|---|---|
| Market Context | Market state and source context at decision time | Available in Strategy / source manifests for inspected runs; benchmark/regime incomplete | Entry/regime review |
| Portfolio Policy | Target cash, exposure, position count, permission/posture | Available in Strategy/Runtime evidence where generated | Zero deployment/cash drag review |
| Capital Deployment | Translation of policy and opportunity into deployable capital | Available/derivable from planning evidence | Cash utilization and sizing review |
| Portfolio Construction | Selected targets and integrated Strategy intent | Available in Strategy/Planning evidence | Entry and concentration review |
| Position Sizing | Quantity/notional/weight decision | Available in planning/pending evidence | Sizing and exposure review |
| Position Management | HOLD/ADD/REDUCE/EXIT decisions | Available for counts; outcome metrics post-hoc/partial | PM quality review |
| Cash Drag | Undeployed cash vs equity and opportunity | Derivable from daily equity/cash | Zero deployment/cash utilization review |
| Entry | BUY_NEW price, rank, source context, subsequent return | Partially derivable; post-entry outcome post-hoc only | Entry quality review |
| Exit | SELL_EXIT realized PnL and post-exit path | Realized available; post-exit counterfactual post-hoc | Profit capture/loss review |
| ADD | BUY_ADD incremental exposure and later outcome | Partially derivable; exact lot outcome missing | ADD quality review |
| REDUCE | Partial sell outcome/counterfactual | Runtime verification incomplete; post-hoc only | Future PM review |
| Market Regime | Up/down/range/high-vol labels | Missing until benchmark/regime contract source exists | Future benchmark/regime attribution |
| Benchmark difference | Strategy return minus benchmark | Missing until TOPIX source approved | Future relative performance review |

Post-hoc attribution labels:

- `DECISION_TIME_EVIDENCE`
- `RUNTIME_OUTCOME`
- `POST_HOC_ATTRIBUTION_ONLY`
- `COUNTERFACTUAL_DIAGNOSTIC_ONLY`
- `MISSING_AUTHORITY`

## 8. Performance Gap Inventory

| Gap ID | Name | Purpose | Evaluation method | Evidence | Improvement candidates |
|---|---|---|---|---|---|
| `P24-GAP-01` | Zero Deployment | Explain no-order / no-buy periods | Daily cash utilization, target position count, policy posture, candidate/opportunity breadth | Plan, Strategy shadow, Portfolio Policy, pending/no-order evidence | Policy threshold review, opportunity breadth review, no-order reason classification |
| `P24-GAP-02` | Cash Utilization | Measure under/over deployment | Cash ratio, gross exposure, average/max exposure, unused buying power | Daily Current, valuation, position sizing, capital deployment | Target cash/exposure hypothesis, position count hypothesis |
| `P24-GAP-03` | Entry Quality | Determine whether BUY_NEW entries are poor, late, or under-supported | Entry price vs post-entry path, rank/confidence, market context, subsequent drawdown | BUY_NEW executions, Candidate/Opportunity, source manifests, valuation | Entry threshold/ranking hypothesis after baseline |
| `P24-GAP-04` | PM ADD Quality | Determine whether ADD improves or worsens campaigns | ADD notional, post-ADD return, campaign PnL, drawdown after ADD | PM decisions, BUY_ADD executions, position campaigns | ADD threshold, ADD sizing, ADD timing hypothesis |
| `P24-GAP-05` | SELL / Profit Capture | Assess whether exits/reduces capture gains or avoid losses | SELL_EXIT realized PnL, post-exit path, profit giveback, open PnL | SELL planning, executions, realized slices, valuation | EXIT trigger, REDUCE verification, profit protection hypothesis |
| `P24-GAP-06` | Loss Attribution | Explain realized/unrealized losses by component | Symbol/campaign PnL, drawdown date, entry/ADD/hold/exit chain | Realized slices, position campaigns, equity curve | Loss cut, concentration, PM timing hypothesis |
| `P24-GAP-07` | Strategy Profile | Determine which horizon/profile is meaningful | 10BD/20BD/60BD/200BD/1Y/3Y matrix, regime coverage | Operator runs, summaries, final hashes | Profile-specific evaluation plan, not profile-specific logic |

## 9. Operator Runtime Matrix

Runtime execution remains Operator-owned. This matrix defines future evaluation intent only.

| Horizon | Purpose | Evaluation target | Expected lifecycle | Minimum evidence |
|---|---|---|---|---|
| 10BD | Revalidate Phase23-BT comparable lifecycle and short performance seed | BUY_NEW, BUY_ADD, SELL_EXIT, Close, cash/ledger/valuation | `fresh-run -> validate -> close -> summarize` after entry gates | Complete run evidence, final summary, daily valuation, executions, Strategy/source manifests |
| 20BD | Short stability baseline | More trades, PM distribution, early drawdown, cash utilization | Same canonical fresh-run lifecycle | Daily equity curve, realized slices, PM decisions, benchmark snapshots even if MISSING |
| 60BD | Minimum useful risk/volatility review | Volatility, drawdown, exposure, PM repetition | Same lifecycle, archive full run directory | Valid daily equity, complete source/PIT authority, performance summary |
| 200BD | Long baseline before annual target discussion | Return, drawdown, cash drag, concentration, turnover | Same lifecycle; Operator-owned long run | Full daily evidence, summary evidence, source/benchmark status, final hashes |
| 1 year / 252BD | First official annual target evaluation | CAGR/annualized return, max drawdown, benchmark-relative if available | Same lifecycle; no Runtime/Strategy changes during baseline | Complete 252BD evidence, benchmark if approved, metric status matrix |
| 3 years | Robustness and regime diversity | Out-of-period, regime, stability, overfit detection | Multiple fixed-contract runs | Period-separated baselines, benchmark/regime/sector evidence when available |

No horizon alone authorizes Strategy change. Controlled Strategy Change requires an Experiment Contract record.

## 10. Runtime / Performance Responsibility Boundary

Runtime correctness failures are not Performance metrics:

| Not Performance | Classification |
|---|---|
| HALT | Runtime / lifecycle failure |
| Authority欠損 | Authority / source gate failure |
| Cash不整合 | Accounting / Runtime correctness failure |
| Ledger不整合 | Accounting / Runtime correctness failure |
| Future leakage | PIT / NO_LEAKAGE failure |
| Safety violation | Safety failure |

Performance targets:

| Performance area | Examples |
|---|---|
| Cash utilization | Underdeployment, cash drag, target exposure behavior |
| Entry quality | BUY_NEW timing, rank/confidence, entry drawdown |
| PM quality | HOLD/ADD/REDUCE/EXIT outcome diagnostics |
| Drawdown | Peak-to-trough loss, recovery duration |
| Return | Total return, CAGR, realized/unrealized PnL |
| Benchmark difference | Relative return after benchmark source approval |
| Holding period | Campaign duration, open age, realized slice duration |
| Concentration | Single-name/sector exposure where authority exists |
| Opportunity quality | Ranking/selection vs post-hoc outcome, diagnostic only |

Performance evidence can trigger a review or hypothesis. It must not bypass Runtime, Safety, Authority, PIT, NO_LEAKAGE, Accepted Generation, or model-quality contracts.

## 11. Risks

- Short-window annualized return can look dramatic and must carry warnings.
- Benchmark absence can lead to false market-relative conclusions; relative metrics remain `MISSING`.
- Missing fees/tax/slippage must not be treated as zero unless the test profile explicitly states the fill model excludes them.
- Realized-slice win/loss is approximate until stable lot IDs exist.
- Post-hoc attribution can accidentally become overfit logic; experiment changes must be pre-declared.
- A0 source/preflight and Corporate Event entry-gate issues remain outside this Performance Contract and must not be papered over by performance reports.
- Historical-only performance fixes are prohibited.

## 12. Recommended Next Task

Recommended next task:

`Phase24-B Entry Gate Close Revalidation And Performance Baseline Run Approval Review`

Preconditions:

- Resolve or formally review A0R2 source/preflight and Corporate Event entry gate gaps.
- Operator explicitly authorizes any Runtime execution.
- The run command records baseline identity fields and contract versions.

After an Operator-approved run exists, run read-only `summarize --scope performance`, `--scope positions`, and `--scope lifecycle` to populate Phase24 baseline metrics under this contract.
