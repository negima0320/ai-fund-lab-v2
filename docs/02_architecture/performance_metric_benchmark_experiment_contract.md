# Performance Metric / Benchmark / Experiment Comparison Contract

Contract versions:

```text
performance_metric_contract_version = phase20_b_performance_metric_contract.v1
benchmark_contract_version = phase20_b_benchmark_contract.v1
experiment_comparison_contract_version = phase20_b_experiment_comparison_contract.v1
```

## 1. Purpose

This document defines the official Performance Metric, Benchmark, and Experiment Comparison contracts for AI Fund Lab v2 Phase20 analysis.

The contract fixes:

- what each metric means
- which artifact is authoritative
- which unit is used
- how open positions, ADD, REDUCE, EXIT, and partial realization are handled
- when runs are comparable
- how missing evidence is reported
- how post-hoc outcomes are separated from Runtime decision inputs

## 2. Scope

This contract applies to Historical Runtime performance analysis, beginning with the Phase20 diagnostic baseline run:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

It also applies to future Phase20 comparison runs unless a later contract version supersedes it.

## 3. Non-goals

This contract does not:

- change AI, Opportunity, BUY, HOLD, ADD, REDUCE, EXIT, PM, Risk, Capital Allocation, Runtime, Broker, Training, Calibration, Validation, or Accepted Generation logic
- authorize Broker access or order placement
- authorize benchmark or sector data fetching
- authorize use of performance results as Training, Calibration, Validation, Accepted Generation, or Runtime decision authority
- convert post-hoc attribution into Runtime features

## 4. Authority Model

Primary authorities:

| Area | Authority |
|---|---|
| Run event scope | `reports/runtime_tests/runs/<RUN_ID>/run_state.json` and run-scoped daily evidence |
| Runtime Test summary | `reports/runtime_tests/summaries/<SUMMARY_ID>/summary.json` |
| BUY AI lineage | `.runtime/runtime_state/accepted_buy_ai_bundle.json` and accepted generation manifest |
| Execution fills | canonical performance events from `runtime_v2.ledger.performance_events`, evidence type `execution_equivalent` |
| Current equity | `persistent_ledger/state.json` content captured or evidenced by run-scoped current valuation evidence |
| PM counts | run-scoped `sell_planning/position_management_evidence.json` and summary |
| REDUCE/EXIT linkage | summary `reduce_exit.items` plus run-scoped SELL/Execution evidence |

Forbidden authorities:

- shared `.runtime` scans across dates for run event counts
- latest path, mtime, max date, manual path, legacy fallback, or Promotion Candidate fallback as BUY AI authority
- missing current position interpreted as zero
- missing benchmark or sector data interpreted as cash or zero return

## 5. Metric Status Taxonomy

| Status | Meaning |
|---|---|
| `AVAILABLE` | Metric value is already present in accepted run evidence. |
| `DERIVABLE_EXACT` | Metric can be computed exactly from authoritative artifacts without approximation. |
| `DERIVABLE_APPROXIMATE` | Metric can be estimated from authoritative artifacts, but the unit is not exact, usually due to missing stable lot evidence. |
| `DERIVABLE_PARTIAL` | Metric can be computed for a subset, such as open positions or closed slices only. |
| `MISSING` | Required source artifact or contract is absent. |
| `NOT_AVAILABLE` | Artifact is intentionally unavailable in the current test level or profile. |
| `NOT_APPLICABLE` | Metric does not apply to the run or environment. |
| `AUTHORITY_CONFLICT` | Multiple sources disagree or the available source is not valid authority. |

Every metric output must include:

```text
value
status
confidence_class
authority
limitations
warnings
contract_version
```

All metric records must include the following fields. When a value is not applicable, the field must still be present with `NOT_APPLICABLE` or an empty structured value, not omitted:

```text
metric_name
metric_id
description
purpose
unit
calculation_formula
numerator
denominator
time_basis
aggregation_level
authority
source_artifacts
required_fields
join_keys
open_position_handling
partial_execution_handling
ADD_handling
REDUCE_handling
EXIT_handling
missing_data_policy
precision
rounding
status
confidence_class
temporal_safety
known_limitations
```

Canonical metric registry:

| Metric | Metric ID | Unit | Primary formula / definition | Status |
|---|---|---:|---|---|
| Initial Equity | `core.initial_equity` | JPY | Initial equity from run plan/summary | `AVAILABLE` |
| Final Equity | `core.final_equity` | JPY | Final `cash + market_value` | `AVAILABLE` |
| Total Return | `core.total_return` | JPY | `final_equity - initial_equity` | `AVAILABLE` |
| Return Rate | `core.return_rate` | ratio | `total_return / initial_equity` | `AVAILABLE` |
| Realized PnL | `core.realized_pnl` | JPY | Average-cost realized slices from canonical executions | `AVAILABLE` |
| Unrealized PnL | `core.unrealized_pnl` | JPY | Open market value minus cost basis | `AVAILABLE` |
| Total PnL | `core.total_pnl` | JPY | `realized_pnl + unrealized_pnl` | `AVAILABLE` |
| Daily Return | `core.daily_return` | ratio | Daily equity change over previous completed business day | `DERIVABLE_EXACT` |
| Cumulative Return | `core.cumulative_return` | ratio | `equity[d] / initial_equity - 1` | `DERIVABLE_EXACT` |
| Annualized Return | `core.annualized_return` | ratio | CAGR-style 252 business-day annualization | `DERIVABLE_EXACT` with warning |
| Daily Equity Curve | `risk.daily_equity_curve` | JPY series | Valid daily equity snapshots | `DERIVABLE_EXACT` |
| Peak Equity | `risk.peak_equity` | JPY | Running max of equity | `DERIVABLE_EXACT` |
| Drawdown Amount | `risk.drawdown_amount` | JPY | `equity - peak_equity` | `DERIVABLE_EXACT` |
| Drawdown Rate | `risk.drawdown_rate` | ratio | `drawdown_amount / peak_equity` | `DERIVABLE_EXACT` |
| Maximum Drawdown | `risk.maximum_drawdown` | ratio | Minimum drawdown rate | `DERIVABLE_EXACT` |
| Drawdown Start Date | `risk.drawdown_start_date` | date | Peak date before MDD trough | `DERIVABLE_EXACT` |
| Drawdown Bottom Date | `risk.drawdown_bottom_date` | date | Trough date of MDD | `DERIVABLE_EXACT` |
| Recovery Date | `risk.recovery_date` | date | First later date equity recovers to peak | `DERIVABLE_EXACT` or `MISSING` if unrecovered |
| Recovery Duration | `risk.recovery_duration` | business days | Business days bottom to recovery | `DERIVABLE_EXACT` or `MISSING` |
| Volatility | `risk.volatility` | ratio | Std dev of daily returns | `DERIVABLE_EXACT` |
| Downside Volatility | `risk.downside_volatility` | ratio | Std dev of negative daily returns | `DERIVABLE_EXACT` |
| Gross Exposure | `capital.gross_exposure` | ratio | Gross open market value / equity | `DERIVABLE_EXACT` |
| Net Exposure | `capital.net_exposure` | ratio | Long minus short exposure / equity | `DERIVABLE_EXACT` for long-only |
| Cash Ratio | `capital.cash_ratio` | ratio | `cash / equity` | `DERIVABLE_EXACT` |
| Cash Utilization | `capital.cash_utilization` | ratio | `1 - cash_ratio` | `DERIVABLE_EXACT` |
| Average Exposure | `capital.average_exposure` | ratio | Mean daily gross exposure | `DERIVABLE_EXACT` |
| Maximum Exposure | `capital.maximum_exposure` | ratio | Max daily gross exposure | `DERIVABLE_EXACT` |
| Single-name concentration | `capital.single_name_concentration` | ratio | Max symbol market value / equity | `DERIVABLE_EXACT` |
| Sector concentration | `capital.sector_concentration` | ratio | Max sector market value / equity | `MISSING` |
| BUY Count | `activity.buy_count` | count | Count canonical BUY executions | `AVAILABLE` |
| SELL Count | `activity.sell_count` | count | Count canonical SELL executions | `AVAILABLE` |
| Order Count | `activity.order_count` | count | Count accepted submitted order records | `DERIVABLE_EXACT` |
| Execution Count | `activity.execution_count` | count | Count canonical execution events | `AVAILABLE` |
| Turnover | `activity.turnover_primary` | ratio | Sum absolute executed notional / average equity | `DERIVABLE_EXACT` |
| Average Trade Notional | `activity.average_trade_notional` | JPY | Mean canonical execution notional | `DERIVABLE_EXACT` |
| Median Trade Notional | `activity.median_trade_notional` | JPY | Median canonical execution notional | `DERIVABLE_EXACT` |
| Holding Period | `activity.holding_period` | business days | Position/capital/realized-slice holding periods | `DERIVABLE_APPROXIMATE` |
| Position Count | `activity.position_count` | count | Daily open position count | `DERIVABLE_EXACT` |
| Average Position Count | `activity.average_position_count` | count | Mean daily open position count | `DERIVABLE_EXACT` |
| Win Rate | `outcome.win_rate` | ratio | Winning realized slices / realized slices | `DERIVABLE_APPROXIMATE` |
| Loss Rate | `outcome.loss_rate` | ratio | Losing realized slices / realized slices | `DERIVABLE_APPROXIMATE` |
| Breakeven Rate | `outcome.breakeven_rate` | ratio | Breakeven realized slices / realized slices | `DERIVABLE_APPROXIMATE` |
| Profit Factor | `outcome.profit_factor` | ratio | Gross realized gains / abs(gross losses) | `DERIVABLE_APPROXIMATE` |
| Payoff Ratio | `outcome.payoff_ratio` | ratio | Average win / abs(average loss) | `DERIVABLE_APPROXIMATE` |
| Average Win | `outcome.average_win` | JPY | Mean positive realized slice PnL | `DERIVABLE_APPROXIMATE` |
| Average Loss | `outcome.average_loss` | JPY | Mean negative realized slice PnL | `DERIVABLE_APPROXIMATE` |
| Median Win | `outcome.median_win` | JPY | Median positive realized slice PnL | `DERIVABLE_APPROXIMATE` |
| Median Loss | `outcome.median_loss` | JPY | Median negative realized slice PnL | `DERIVABLE_APPROXIMATE` |
| Largest Win | `outcome.largest_win` | JPY | Max realized slice gain | `DERIVABLE_APPROXIMATE` |
| Largest Loss | `outcome.largest_loss` | JPY | Min realized slice loss | `DERIVABLE_APPROXIMATE` |
| Expectancy | `outcome.expectancy` | JPY | Mean realized slice PnL | `DERIVABLE_APPROXIMATE` |
| Loss Concentration | `outcome.loss_concentration` | ratio | Largest loss / total loss magnitude | `DERIVABLE_APPROXIMATE` |
| Symbol-level PnL Contribution | `outcome.symbol_pnl_contribution` | JPY | Realized plus unrealized PnL by symbol | `DERIVABLE_PARTIAL` |
| Sector-level PnL Contribution | `outcome.sector_pnl_contribution` | JPY | PnL by sector | `MISSING` |
| HOLD Count | `pm.hold_count` | count | Count PM HOLD decisions | `AVAILABLE` |
| ADD Count | `pm.add_count` | count | Count PM ADD decisions | `AVAILABLE` |
| REDUCE Count | `pm.reduce_count` | count | Count PM REDUCE decisions | `AVAILABLE` |
| EXIT Count | `pm.exit_count` | count | Count PM EXIT decisions | `AVAILABLE` |
| HOLD continuation return | `pm.hold_continuation_return` | ratio | Post-HOLD return until next event | `DERIVABLE_PARTIAL` |
| ADD incremental return | `pm.add_incremental_return` | ratio | Post-ADD return on added notional | `DERIVABLE_APPROXIMATE` |
| REDUCE loss avoided | `pm.reduce_loss_avoided` | JPY | Post-hoc counterfactual | `DERIVABLE_PARTIAL` |
| REDUCE profit missed | `pm.reduce_profit_missed` | JPY | Post-hoc counterfactual | `DERIVABLE_PARTIAL` |
| EXIT loss avoided | `pm.exit_loss_avoided` | JPY | Post-hoc counterfactual | `DERIVABLE_PARTIAL` |
| EXIT profit missed | `pm.exit_profit_missed` | JPY | Post-hoc counterfactual | `DERIVABLE_PARTIAL` |
| PM decision hit rate | `pm.decision_hit_rate` | ratio | Rule-fixed post-hoc directional success | `DERIVABLE_PARTIAL` |

## 6. Equity Contract

Definition:

```text
equity = cash + market_value_of_open_runtime_owned_positions
```

Runtime implementation authority:

- `runtime_owned_fill_projection` projects Runtime-owned filled positions into Current.
- Current state uses `total_equity = projected_cash + market_value`.
- Current valuation refresh updates `current_price`, `market_value`, `unrealized_pnl`, `valuation_as_of`, and `source_market_date` without changing quantity or average price.

Snapshot timing:

```text
equity_snapshot_timing = end_of_business_date_after_execution_and_current_valuation_refresh
```

For Historical Runtime tests, the daily equity snapshot must be taken after:

1. execution stage
2. ledger/current apply
3. current valuation refresh

If current valuation refresh did not execute or is not PASS, the daily equity value is `MISSING` or `AUTHORITY_CONFLICT`; it must not be interpolated.

Policies:

| Item | Contract |
|---|---|
| Valuation timing | End-of-business-date after execution and current valuation refresh. |
| Business-date boundary | Use `completed_business_days` from run state. |
| Market price source | Run-scoped current valuation evidence and its market evidence authority. |
| Stale price | Report as warning or `MISSING`; no silent carry-forward unless evidence explicitly says valid carryover. |
| Unpriced position | `MISSING` or `AUTHORITY_CONFLICT`; do not value at zero. |
| Pending order | Excluded from executed equity. May be reported separately as committed exposure only if reserved cash evidence exists. |
| Realized PnL | Included through cash effects and `realized_pnl` field. |
| Fees/tax | Currently not included unless evidence provides them. Report fee/tax treatment as `NOT_AVAILABLE` for Phase20 baseline. |
| Cash mutation | Based on canonical execution cash effects. |
| Execution timing | Business-date execution equivalent; Historical fill model uses the accepted Runtime evidence. |

## 7. Return Contract

Core formulas:

```text
simple_return = (final_equity - initial_equity) / initial_equity
daily_return[d] = (equity[d] - equity[previous_completed_business_day]) / equity[previous_completed_business_day]
cumulative_return[d] = (equity[d] / initial_equity) - 1
total_return_amount = final_equity - initial_equity
total_pnl = realized_pnl + unrealized_pnl
```

Annualized return:

```text
annualized_return = (final_equity / initial_equity) ** (business_days_per_year / observation_days) - 1
business_days_per_year = 252
```

Minimum observation policy:

| Item | Value |
|---|---|
| Minimum for display | 20 completed business days |
| Minimum for judgment vs +50% target | 252 completed business days |
| Warning threshold | `< 60` business days |

20BD annualized return may be displayed with `SHORT_PERIOD_UNRELIABLE` warning. It must not be used to prove or disprove the +50% annual target.

Benchmark-relative return and excess return require the Benchmark Contract data. Until benchmark data exists, status is `MISSING`.

## 8. Drawdown Contract

Drawdown must use mark-to-market equity including open positions.

Definitions:

```text
peak_equity[d] = max(equity[date] for date <= d)
drawdown_amount[d] = equity[d] - peak_equity[d]
drawdown_rate[d] = drawdown_amount[d] / peak_equity[d]
maximum_drawdown = min(drawdown_rate[d])
drawdown_start_date = date of peak preceding maximum_drawdown trough
drawdown_bottom_date = date of trough
recovery_date = first later date where equity >= prior peak
recovery_duration = business days from bottom to recovery
```

Missing equity policy:

```text
missing_equity_day_policy = FAIL_CLOSED_FOR_OFFICIAL_METRIC
diagnostic_policy = SKIP_WITH_WARNING only when explicitly requested
```

No implicit interpolation is allowed.

## 9. Exposure and Cash Contract

Definitions:

```text
gross_exposure = sum(abs(open_position_market_value)) / total_equity
net_exposure = sum(long_market_value - short_market_value) / total_equity
cash_ratio = cash / total_equity
cash_utilization = 1 - cash_ratio
single_name_weight[symbol] = market_value[symbol] / total_equity
single_name_concentration = max(single_name_weight)
```

AI Fund Lab v2 Phase20 baseline is cash-equity-only long-only Historical Runtime. Therefore:

```text
net_exposure = gross_exposure
```

only when:

- all positions are long
- no margin, short, derivative, or borrowed position evidence exists
- Runtime environment is cash-equity-only

Pending order treatment:

- Primary exposure uses executed exposure only.
- Committed exposure may be reported separately if pending notional and reserved cash evidence are present.
- If reserved cash is absent, do not infer it.

Sector concentration is `MISSING` until sector mapping exists.

## 10. Turnover Contract

Primary turnover:

```text
turnover_primary = sum(abs(executed_gross_notional)) / average_equity
average_equity = arithmetic mean of valid daily equity snapshots in the period
```

Rationale:

- Canonical execution events are available.
- This definition captures BUY, ADD, REDUCE, and EXIT activity.
- It does not assume matched BUY/SELL pairs.

Secondary diagnostic:

```text
turnover_two_sided = min(total_buy_notional, total_sell_notional) / average_equity
```

This is optional and must not replace the primary metric.

Policies:

- BUY and SELL are both included.
- Partial execution uses filled quantity only.
- ADD is included as BUY notional.
- REDUCE and EXIT are included as SELL notional.
- Fees/tax are excluded until evidence exists.

## 11. Trade Unit and Win/Loss Contract

Because the system supports ADD, REDUCE, EXIT, partial sell, remaining position, and open position, a simple BUY-to-SELL one-to-one trade unit is prohibited.

Official units:

| Unit | Use | Status in Phase20 baseline |
|---|---|---|
| `realized_slice` | Win/loss for each SELL quantity against average cost at that time | `DERIVABLE_APPROXIMATE` |
| `symbol_campaign` | From first BUY for a symbol to final EXIT or end-of-run open state | `DERIVABLE_PARTIAL` |
| `position_lifecycle` | From position open to final full close | `DERIVABLE_PARTIAL` |
| `lot` | Broker-compatible exact lot | `MISSING` until stable lot ID exists |

Win/loss:

```text
win = realized_slice_pnl > tolerance
loss = realized_slice_pnl < -tolerance
breakeven = abs(realized_slice_pnl) <= tolerance
open = symbol has remaining quantity at final equity snapshot
```

If stable lot evidence is absent, Win Rate and Profit Factor must be reported as approximate or partial, not as exact trade statistics.

## 12. Holding Period Contract

Holding period units:

| Metric | Definition | Status |
|---|---|---|
| Position lifecycle holding period | First BUY date to final EXIT date or run end | `DERIVABLE_PARTIAL` |
| Capital-weighted holding period | Sum(notional held * business days) / sum(notional) | `DERIVABLE_APPROXIMATE` |
| Realized slice holding period | SELL date minus inferred average-cost pool start | `DERIVABLE_APPROXIMATE` |
| Open position age | First BUY date to final completed business date | `DERIVABLE_PARTIAL` |
| Lot-specific holding period | Stable lot open date to close date | `MISSING` |

Business days are the primary basis. Calendar days may be displayed as secondary diagnostics.

## 13. Realized and Unrealized PnL Contract

Definitions:

```text
realized_pnl = sum((sell_price - average_cost_before_sell) * sell_quantity)
unrealized_pnl = sum(open_position_market_value - open_position_quantity * average_price)
total_pnl = realized_pnl + unrealized_pnl
closed_position_pnl = realized_pnl for fully closed symbol campaigns
open_position_pnl = unrealized_pnl plus any realized slices for still-open symbol campaigns
```

Implementation authority:

- Runtime-owned fill projection computes realized PnL using average cost from canonical execution events.
- Open position unrealized PnL uses market value minus cost basis.
- Historical execution equivalent records carry `price`, `quantity`, `business_date`, `side`, and `cash_effect`.

Cost basis method:

```text
current_phase20_baseline_cost_basis = average_cost_pool
```

FIFO, tax-lot, and broker-compatible lot accounting are not available unless future evidence adds stable lot IDs.

Partial SELL:

- Realized PnL is computed for sold quantity against average cost.
- Remaining quantity keeps average price in Current.
- Open unrealized PnL is computed only for remaining quantity.

## 14. Position Management Attribution Contract

PM metrics are decision metrics, not proof of causality by themselves.

Definitions:

| Metric | Definition | Temporal class |
|---|---|---|
| HOLD Count | Count of PM decisions with `HOLD` | Decision-time |
| ADD Count | Count of PM decisions with `ADD` | Decision-time |
| REDUCE Count | Count of PM decisions with `REDUCE` | Decision-time |
| EXIT Count | Count of PM decisions with `EXIT` | Decision-time |
| HOLD continuation return | Post-decision return until next PM decision, sell, or run end | Post-hoc attribution only |
| ADD incremental return | Return on added notional after ADD | Post-hoc attribution only; approximate without lot ID |
| REDUCE loss avoided | Counterfactual difference between sold quantity and later price path | Post-hoc attribution only |
| REDUCE profit missed | Counterfactual upside forgone after REDUCE | Post-hoc attribution only |
| EXIT loss avoided | Counterfactual loss avoided after full exit | Post-hoc attribution only |
| EXIT profit missed | Counterfactual upside forgone after full exit | Post-hoc attribution only |
| PM decision hit rate | Directional success by post-hoc rule fixed before calculation | Post-hoc diagnostic only |

These metrics must not be used as Runtime PM input unless separately promoted through a future approved feature/AI contract.

## 15. Benchmark Contract

Benchmark evidence is currently `MISSING`; this section defines the contract only.

Primary benchmark:

```text
benchmark_id = TOPIX_TOTAL_OR_PRICE_RETURN_JQUANTS_COMPATIBLE
benchmark_name = TOPIX
status = MISSING_UNTIL_JQUANTS_COMPATIBLE_SOURCE_CONFIRMED
```

TOPIX is selected as the primary benchmark because the strategy trades broad Japanese equities and TOPIX is broader than Nikkei 225. It is not usable until a repository-approved, preferably J-Quants-derived or J-Quants-compatible source is confirmed.

Secondary benchmarks:

| Benchmark | Status | Use |
|---|---|---|
| Cash | `DERIVABLE_EXACT` | Opportunity cost / no-risk baseline. |
| Nikkei 225 | `MISSING` | Large-cap price index diagnostic only if approved source exists. |
| Equal-weighted eligible universe | `MISSING` | Universe-relative diagnostic; requires eligible universe and survivorship-safe returns. |

Benchmark fields:

```text
benchmark_id
benchmark_name
data_source
price_field
return_type
dividend_treatment
business_date
start_date
end_date
initial_normalization_value
benchmark_equity_curve
relative_return
excess_return
tracking_difference
```

Alignment:

- Benchmark start equity is normalized to strategy initial equity.
- Start date and end date must match completed business days.
- Missing benchmark date is `MISSING`; do not forward-fill unless the benchmark contract explicitly marks a non-trading holiday alignment.

## 16. Market Regime Contract

Phase20-B does not implement regime classification.

Future post-hoc regime fields:

```text
regime_id
input_benchmark
lookback_window
classification_formula
threshold
business_date
minimum_observations
missing_data_behavior
temporal_class = POST_HOC_ATTRIBUTION_ONLY
```

Allowed labels:

```text
UPTREND
DOWNTREND
RANGE
HIGH_VOLATILITY
LOW_VOLATILITY
RISK_ON
RISK_OFF
```

Runtime-use regimes require a separate approved Runtime Feature or AI contract. Phase20 performance outcomes do not automatically authorize regime features.

## 17. Sector Contract

Sector evidence is currently `MISSING`.

Required future fields:

```text
sector_taxonomy
source
effective_date
symbol
sector
classification_version
unknown_sector_policy
sector_concentration
sector_pnl_contribution
sector_benchmark_return
```

Unknown sector handling:

- Use `UNKNOWN_SECTOR`, not zero or cash.
- Sector concentration is unavailable if any material position has unknown sector unless a coverage threshold is explicitly approved.

## 18. Experiment Comparison Contract

Required experiment record:

```text
experiment_id
baseline_run_id
candidate_run_id
code_revision
config_revision
accepted_generation_id
dataset_revision_id
test_profile
business_dates
initial_cash
initial_positions
broker_environment
market_data_snapshot
feature_snapshot
random_seed
external_effect_policy
runtime_architecture_version
performance_metric_contract_version
benchmark_contract_version
experiment_comparison_contract_version
changed_component
change_description
```

Comparability:

| Status | Meaning |
|---|---|
| `COMPARABLE` | Required fixed conditions match, one declared variable changed, all core evidence PASS. |
| `COMPARABLE_WITH_CAVEATS` | Minor non-causal or documented evidence gaps exist; caveats must be listed. |
| `NOT_COMPARABLE` | Required fixed conditions differ, run incomplete, lifecycle inconsistency, leakage, or metric contract mismatch. |

## 19. Experiment Isolation Rules

Fixed conditions:

- same business dates
- same market data snapshot
- same initial cash
- same initial positions
- same test profile
- same broker environment
- same Runtime Architecture contract
- same external-effect policy
- same metric contract
- same benchmark contract

Allowed changes:

- exactly one declared target by default, such as Opportunity threshold only, ADD policy only, EXIT threshold only, Position sizing only, or Risk cap only
- multiple changes only when explicitly classified as multi-factor and not causally attributable

Comparison is prohibited when:

- business dates differ
- initial cash differs
- Accepted Generation differs without recording
- market snapshot differs
- Runtime Contract differs
- metric definition differs
- run is incomplete
- lifecycle consistency fails
- future leakage exists

## 20. Missing Data Contract

Missing data is never zero.

Policies:

- Missing current position is not zero position.
- Missing benchmark return is not zero return.
- Missing sector is `UNKNOWN_SECTOR`.
- Missing trade-level PnL is not breakeven.
- Missing daily equity blocks official drawdown unless diagnostic skip is explicitly requested.

## 21. Precision and Rounding Contract

Internal precision:

| Field | Internal precision |
|---|---|
| Yen | full numeric precision from source artifact |
| Share quantity | full numeric precision from source artifact; lot validity checked separately |
| Ratio | full floating precision |
| Percentage | ratio * 100 at display time |

Display rounding:

| Field | Display |
|---|---|
| Yen | nearest yen unless source has decimals |
| Quantity | no unnecessary decimals |
| Ratio | 6 decimals in machine output |
| Percentage | 2 decimal places in human output |

Comparison tolerance:

```text
absolute_yen_tolerance = 1e-6 for machine recomputation
ratio_tolerance = 1e-9
```

Hash-stable serialization must use sorted JSON keys and no display-rounded values for machine comparison.

## 22. Temporal Integrity

Metric outputs must classify each input as one of:

```text
DECISION_TIME_INFORMATION
RUN_TIME_STATE
END_OF_DAY_VALUATION
POST_HOC_FUTURE_OUTCOME
COUNTERFACTUAL_OUTCOME
```

The following are always `POST_HOC_ATTRIBUTION_ONLY`:

- MFE
- MAE
- post-HOLD return
- post-ADD return
- post-REDUCE return
- post-EXIT return
- profit missed
- loss avoided
- counterfactual hold return

They must not be used as Training, Calibration, Validation, Accepted Generation, or Runtime decision input.

## 23. Contract Versioning

Current versions:

```text
performance_metric_contract_version = phase20_b_performance_metric_contract.v1
benchmark_contract_version = phase20_b_benchmark_contract.v1
experiment_comparison_contract_version = phase20_b_experiment_comparison_contract.v1
```

Rules:

- Definition changes require a new version.
- Past run values must not be overwritten silently.
- Results computed under different contract versions are `NOT_COMPARABLE` or `COMPARABLE_WITH_CAVEATS`.
- Reports must record all three contract versions.

## 24. Current Known Gaps

- Benchmark index data is missing.
- Sector mapping and sector return data are missing.
- Stable broker-compatible lot ID is missing for exact lot-level win/loss and holding period.
- Fees, tax, slippage, and partial-fill realism are not official Phase20 baseline inputs.
- Full candidate-universe exclusion evidence is not confirmed below persisted Top50.
- PM threshold/confidence evidence is not formalized.

## 25. Acceptance Criteria

Phase20-B is accepted when:

- core return metrics are defined
- equity timing is defined
- drawdown is defined
- exposure and cash metrics are defined
- turnover is defined
- missing-data policy is defined
- metric status taxonomy is defined
- experiment comparability is defined
- benchmark contract is defined even while benchmark data remains missing
- no Runtime Authority conflict is introduced
- no future leakage is introduced
- no Runtime, AI, PM, Risk, Capital Allocation, Training, Calibration, Validation, Accepted Generation, Broker, or Runtime State mutation is required
