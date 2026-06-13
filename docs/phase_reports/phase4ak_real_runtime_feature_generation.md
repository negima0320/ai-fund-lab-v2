# Phase4-AK Real Runtime Feature Generation

## Purpose

Phase4-AK runs Candidate Feature Generation against the isolated `real_runtime` normalized daily quotes produced in Phase4-AJ.

This phase generates feature rows, validates the feature schema, runs leakage audit, records feature statistics, and decides readiness for label generation.

Phase4-AK does not generate labels, build datasets, train models, infer, backtest, trade, run Paper Trading, promote data, switch readers, call Broker APIs, place orders, or update Portfolio state.

## Input

```text
.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet
reports/candidate_ai/full_range/phase4aj_real_runtime_normalized_summary.json
```

Required Phase4-AJ readiness:

```text
READY_FOR_REAL_RUNTIME_FEATURE_GENERATION
```

## Generated Feature Scope

Phase4-AK uses only the designed Candidate AI price, volume, trend, volatility, liquidity, missing flag, and universe eligibility features.

Generated feature columns include:

```text
price_momentum_return_5d
price_momentum_return_20d
price_momentum_return_60d
volume_momentum_ratio_5d
volume_momentum_ratio_1d_20d
volatility_return_std_20d
trend_close_over_ma_20d
trend_ma_5_20_ratio
trend_ma_20_60_ratio
liquidity_avg_volume_20d
missing_flags_insufficient_history
missing_flags_price
missing_flags_volume
universe_eligible
excluded_reason
```

The output is one cross-sectional feature table at the latest normalized date.

## Lookback Rule

Feature generation uses the latest 60 available normalized business-day rows per code.

- `as_of_date = target_date = latest normalized date`
- only rows with `Date <= as_of_date` are used
- codes with fewer than 60 rows are marked `universe_eligible=false`
- codes missing latest date, price, or volume are excluded with `excluded_reason`

`price_momentum_return_60d` uses the earliest close in the available 60-row window as the comparison point. Phase4-AL may refine label windows, but feature rows still cannot use future information.

## Output

Runtime outputs:

```text
.runtime/candidate_ai/features/
.runtime/candidate_ai/manifests/
.runtime/candidate_ai/audit/
```

Phase report outputs:

```text
reports/candidate_ai/full_range/phase4ak_real_runtime_feature_generation_summary.json
reports/phase_reports/phase4ak_real_runtime_feature_generation_audit.json
docs/phase_reports/phase4ak_real_runtime_feature_generation_audit.md
```

## Leakage Guard

Phase4-AK forbids feature columns containing:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
candidate_label
backtest result
trade result
portfolio
order
pnl
```

`label_generation_executed` remains `false`.

## Readiness

Success readiness:

```text
READY_FOR_LABEL_GENERATION
```

Blocking statuses:

- `BLOCKED_BY_SCHEMA_VALIDATION`
- `BLOCKED_BY_LEAKAGE_AUDIT`
- `BLOCKED_BY_FEATURE_GENERATION`
- `BLOCKED_BY_OUTPUT_PATH_SAFETY`

## Next Phase

Recommended next phase:

```text
Phase4-AL Label Generation
```

Phase4-AL may generate future labels such as `future_return_*`, `future_max_return_*`, `future_max_drawdown_*`, `top_decile_*`, and `downside_bad_*`, but only in a physically and logically separate label table.
