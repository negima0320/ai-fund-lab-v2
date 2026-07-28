# Phase22-L Benchmark / Sector Authority and Market Context Resolution

## Primary Judgment

`PHASE22_L_MARKET_CONTEXT_AUTHORITY_RESOLVED`

Market Context authority is resolved with a J-Quants-derived equal-weight market proxy, explicit sector authority, explicit trend/breadth/volatility metrics, fixed thresholds, PIT/failure/bootstrap contracts, and runtime-preserving read-only artifact extensions.

## Reviewed SoT

- Phase22-L task instructions.
- Existing Phase22-A Market Context producer/schema/tests.
- Phase22-B through Phase22-K downstream artifact compatibility tests.
- Existing runtime planning regression tests.
- J-Quants normalized daily quote path contract and listed issues path contract already used by Phase22-A.

## Benchmark Source Inventory

TOPIX, TOPIX Core30, TOPIX 500, Nikkei225, and JPX Prime150 remain non-authoritative for Phase22-L because this repo does not expose PIT index level, constituent history, weight history, or redistribution-safe lineage through the local J-Quants artifact contract.

The selected authority is `JQUANTS_LISTED_COMMON_EQUAL_WEIGHT_MARKET_PROXY`, constructed only from J-Quants daily quotes available at or before `business_date`. It is explicitly not a TOPIX equivalent.

## Universe Inventory

The benchmark universe is `listed_common_equities_with_pit_daily_quotes`: securities with valid PIT daily quote rows, valid close values, and sufficient lookback to compute the configured return window. The Strategy universe benchmark remains separated conceptually and must continue to apply Strategy eligibility filters before use downstream.

## Sector Source Inventory

Sector authority is `jquants_listed_info`, preferring 33-sector fields and allowing 17-sector fields where 33-sector is unavailable. Sector benchmarks are equal-weight proxies from constituent stock returns. Market-wide substitution is forbidden when sector source is unavailable.

## Existing Feature Inventory

The existing Market Context producer already computes 5d/20d equal-weight returns, 20d positive breadth, 20d equal-weight realized volatility proxy, and sector return dispersion. Phase22-L preserves these and adds explicit authority, metric, coverage, confidence, regime, config hash, and sector context fields.

## Selected Benchmark Authority

- Source: J-Quants-derived market proxy.
- Universe: listed common equities with PIT daily quotes.
- Price source: adjusted close preferred daily quotes when present.
- Weighting: equal weight.
- Minimum coverage: `0.70`.
- External index fallback: forbidden.

## Selected Sector Authority

- Source: J-Quants listed info.
- Level: 33-sector preferred, 17-sector allowed.
- Construction: equal-weight sector proxy from constituent returns.
- Minimum constituents: `2` in short-test artifact config.
- Minimum coverage: `0.70`.
- Market-wide substitution: forbidden.

## Trend Metric

Metric: `return_20d_equal_weight`.

Thresholds:

- `BULL`: `return_20d_equal_weight >= 0.02`.
- `BEAR`: `return_20d_equal_weight <= -0.02`.
- `RECOVERY`: positive 20d and positive 5d without bull threshold breach.
- `CORRECTION`: negative 20d and negative 5d without bear threshold breach.
- `RANGE`: otherwise.

## Breadth Metric

Metric: `breadth_20d_positive_ratio`.

Thresholds:

- `STRONG`: `>= 0.60`.
- `WEAK`: `<= 0.40`.
- `NEUTRAL`: otherwise.

Artifact lineage includes eligible count, valid count, and benchmark coverage.

## Volatility Metric

Metric: `volatility_20d_equal_weight`.

The artifact keeps the existing daily realized proxy for compatibility. Minimum observations are `20`; insufficient observations produce `REVIEW_REQUIRED`, not a `NORMAL` fallback.

Thresholds:

- `HIGH`: `>= 0.04`.
- `LOW`: `<= 0.005`.
- `NORMAL`: otherwise.

## Threshold Rationale

Thresholds are rule-defined and operational, not PnL-optimized. Breadth uses majority/supermajority bands, trend uses symmetric 20d return bands, and volatility preserves the existing daily realized proxy scale.

## Regime Taxonomy

The resolved taxonomy is `BULL`, `RANGE`, `BEAR`, `CORRECTION`, `RECOVERY`, `HIGH_VOLATILITY`, and `UNCERTAIN`. `HIGH_VOLATILITY` is an overlay in `regime_state`; the original `trend_regime` remains available for downstream compatibility.

## Confidence / Uncertainty

Confidence uses benchmark coverage and observation coverage, with a conflict penalty. Source shortage, coverage shortage, or metric conflict is not rounded into a false regime. `UNCERTAIN` and `REVIEW_REQUIRED` remain formal states.

## Config Contract

Added `configs/strategy/market_context.json` with explicit benchmark, sector, trend, breadth, volatility, regime, confidence, uncertainty, PIT, failure, and bootstrap contracts. Implicit defaults remain forbidden for Phase22-L authority use.

## Artifact Update

`strategy_market_context.v1` remains the schema version for compatibility. The producer now emits benchmark identity, metric values/states, breadth counts, volatility observation count, `regime_state`, `regime_reason_codes`, `sector_contexts`, `config_hash`, and `authority_policy`.

## PIT Contract

The producer blocks future quote rows. The config forbids latest fallback and previous-day context copy. Historical classification must not use current-value backfill when historical PIT classification is unavailable.

## Failure / Bootstrap Contract

Missing benchmark source, benchmark coverage shortfall, metric insufficiency, or missing config yields `REVIEW_REQUIRED`. Future source rows, hash mismatch, unsupported taxonomy, invalid config, latest fallback, and previous-day copy block.

Bootstrap remains `DRAFT`, `REVIEW_REQUIRED`, and `NOT_ELIGIBLE`; fixed fallback values are forbidden.

## Downstream Compatibility

Portfolio Policy, Dynamic Position Count, Dynamic Cash / Exposure, Position Sizing, Position Management, and Runtime Planning remain compatible with existing `trend_regime`, `market_breadth`, and `volatility_regime` fields. Runtime consumer eligibility is not promoted.

## Shadow Comparison

Runtime behavior changed: `false`.

The new benchmark/regime can be compared against existing proxy fields inside the artifact, but it is not consumed by runtime planning in Phase22-L.

## Tests

- `python3 -m pytest tests/strategy/test_phase22_l_market_context_resolution.py`: 5 passed.
- `python3 -m pytest tests/strategy/test_phase22_a_market_context.py ... tests/strategy/test_phase22_l_market_context_resolution.py`: 109 passed.
- `python3 -m pytest tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py tests/runtime_v2/test_phase19_bn_pm_opportunity_model_authority.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase15h_capital_deployment_policy.py`: 17 passed.
- `python3 -m compileall -q src/ai_fund_lab_v2/strategy tests/strategy tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py`: PASS.

## Long Tests Not Executed

5BD, 20BD, 200BD, 1-year, 3-year, and long runtime smoke tests were not executed.

## Blocking Gaps

None for Phase22-L authority resolution.

## Non-blocking Gaps

Historical sector classification PIT availability must be audited with production data inventory before any runtime consumer eligibility promotion.

## Next Gate

Phase22-M: Observability / Attribution.

Market Context blocker resolved: YES.
Phase22-M entry ready: YES.
Runtime switch ready: NO.
Legacy retirement ready: NO.
