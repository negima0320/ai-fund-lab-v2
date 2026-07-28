# Phase22-QE — Strategy Shadow Input Materialization and Portfolio Policy Authority Repair

## Executive Summary

Primary Judgment: `PHASE22_QE_CRITICAL_INPUT_MATERIALIZATION_REPAIRED_OPERATOR_VALIDATION_REQUIRED`

QE repaired the three QD Critical Data Gaps that directly blocked Strategy Shadow calculation input materialization: Price Volatility, PM Technical Features, and Portfolio Policy config authority. The repair is production-common and does not execute Runtime Switch, broker access/write, lifecycle promotion, consumer eligibility promotion, or a new 5BD runtime.

## QD Critical Gap Recap

- `QD-GAP-01`: Price Volatility materialization missing.
- `QD-GAP-02`: PM Technical Features materialization missing.
- `QD-GAP-03`: `configs/strategy/portfolio_policy.json` missing and silently defaulted in Shadow Runtime.

## Price Volatility Contract

Price Volatility is now a formal Strategy input materialization from J-Quants `equities_bars_daily`. It uses PIT rows at or before the selected feature date, adjusted close when present, 20 daily returns, 21 minimum observations, no annualization, no future rows, no latest fallback, and no fixed/zero fallback.

Evidence: `reports/phase22_qe_strategy_shadow_input_materialization_and_portfolio_policy_authority_repair/price_volatility_contract.json`.

## Price Volatility Materialization

Implemented in `src/ai_fund_lab_v2/strategy/input_materialization.py`. Shadow Runtime writes `price_volatility.json` under the daily strategy directory and Position Sizing joins resolved volatility by security code before sizing.

## PM Technical Feature Contract

QE reuses the Runtime PM feature contract columns: `price_momentum_return_5d`, `price_momentum_return_20d`, `trend_close_over_ma_20d`, `trend_ma_5_20_ratio`, `volume_momentum_ratio_5d`, and `volatility_return_std_20d`. It does not introduce PnL, broker, cash, selected/bought/sold, audit, or future-return inputs.

## PM Technical Feature Materialization

Shadow Runtime writes `technical_features.json` and passes it to Position Management as a real source summary with path/hash. Empty held positions are not treated as a missing technical feature error by the materializer; the broader empty-current runtime blocker remains separate.

## Portfolio Policy Authority Decision

QE selected Option A: create formal `configs/strategy/portfolio_policy.json`. No existing alternative config or Accepted Generation authority was evidenced for the intent policy, and the code already treats `policy_config` as a required input.

## Silent Default Removal

`shadow_runtime._portfolio_policy_config()` no longer constructs BALANCED/MAINTAIN/NEUTRAL when the config file is missing. Missing config resolves to explicit `missing_portfolio_policy_config_authority` / `UNRESOLVED` behavior through Portfolio Policy producer input.

## Source Lineage

Input Manifest now records `strategy_input_sources.price_volatility`, `technical_features`, and `portfolio_policy_config`. Source Manifest also records the three sources with physical paths, hashes, PIT status, coverage status, and reason codes.

## PIT Validation

Price and technical feature rows are filtered to the selected feature date. Future source rows are counted but not consumed. PIT violations remain distinct from missing/source review classification.

## Downstream Wiring

- Price Volatility: directly consumed by Position Sizing.
- PM Technical Features: directly consumed by Position Management; downstream Portfolio Construction/Capital Deployment see it through PM artifact status and lineage.
- Portfolio Policy Config: direct authority for Portfolio Policy and summary lineage for Portfolio Construction and Capital Deployment.

## Status Contract Integration

QC status separation is preserved. DRAFT / NOT_ELIGIBLE remains separate from calculation result. Missing inputs remain `REVIEW_REQUIRED` / `UNRESOLVED`, not numeric zero.

## Empty Portfolio Handling

QE only fixes Technical Features materialization semantics for empty held positions. It does not repair the broader existing Runtime empty-current readiness failure.

## Production Commonality

The repair is common to production, demo, and historical because it reads canonical J-Quants operations data and static Strategy config. No historical date override, fixture-only value, Runtime Switch, Pending, Submit, Execution, Ledger, Current, or Broker path was changed.

## Modified Files

Evidence: `reports/phase22_qe_strategy_shadow_input_materialization_and_portfolio_policy_authority_repair/modified_files.json`.

## Test Results

- `tests/strategy/test_phase22_qe_input_materialization.py`: 7 passed.
- `tests/strategy`: 145 passed.
- `compileall`: PASS.
- Targeted runtime regression: 17 passed, 1 known existing failure.

Evidence: `reports/phase22_qe_strategy_shadow_input_materialization_and_portfolio_policy_authority_repair/test_results.json`.

## Known Existing Runtime Failure

`tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py::test_phase17_x_data_readiness_accepts_pending_safety_authority_and_empty_current_pm` still fails with `REVIEW_REQUIRED` instead of expected `READY`. This was already identified by QD and was not repaired by QE.

## Remaining Blockers

QE intentionally preserves:

- Corporate Event PARTIAL coverage policy.
- Historical Accepted Generation effective_from / PIT authority.
- Initial empty portfolio end-to-end readiness.
- Runtime Planning quantity/membership mapping.
- Existing Runtime empty-current readiness failure.

## Operator Validation Requirements

A fresh operator 5BD run is required. Codex did not run it. Operator should confirm all daily Strategy Shadow evidence includes `price_volatility.json`, `technical_features.json`, portfolio policy config authority pointers, source hashes, PIT status, and that Runtime Switch and broker write remain false.

Operator command, not run by Codex:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --start-date 2026-07-06 --business-days 5 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

## Phase22 Closure Eligibility

Phase22 closure remains NO. Phase23 ready remains NO. Runtime Switch ready remains NO. Strategy production ready remains NO.

## Recommended Next Task

Recommended next task: operator 5BD validation review for QE evidence, followed by a separate repair task for the remaining Corporate Event / Accepted Generation / empty-current blockers.
