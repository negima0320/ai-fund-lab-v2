# AI Fund Lab vNext Phase4-I Real Feature Dry-run Readiness Audit

## Audit Result

- phase: `Phase4-I Real Feature Dry-run Readiness Audit`
- status: `complete`
- readiness_status: `BLOCKED_BY_DATA_WINDOW`
- readiness_reason: All rows were excluded by insufficient_lookback; current dry-run window does not provide enough per-code history.

## Dry-run Review

- row_count: `10`
- eligible_count: `0`
- excluded_count: `10`
- excluded_reason_counts: `{'insufficient_lookback': 10}`
- schema_validation_status: `OK`
- leakage_audit_status: `OK`
- storage_format: `parquet`
- normalized_as_of_date: `2026-06-01`
- window_start_date: `2026-06-01`

## Feature Completeness

- generated_feature_columns: `['liquidity_avg_volume_20d', 'missing_flags_insufficient_lookback', 'price_momentum_return_20d', 'price_momentum_return_5d', 'trend_close_over_ma_20d', 'volatility_return_std_20d', 'volume_momentum_ratio_5d']`
- missing_feature_columns: `[]`
- null_counts: `{'liquidity_avg_volume_20d': 10, 'missing_flags_insufficient_lookback': 0, 'price_momentum_return_20d': 10, 'price_momentum_return_5d': 10, 'trend_close_over_ma_20d': 10, 'volatility_return_std_20d': 10, 'volume_momentum_ratio_5d': 10}`

## Cause Analysis

- likely_cause: Expected dry-run limitation: current input window contains too few per-code rows for MIN_LOOKBACK_ROWS=21.

## Next Actions

- Select an as_of_date with enough historical normalized data behind it.
- Ensure lookback_business_days >= 60 for broader dry-run.
- Increase max_rows to at least code_count x lookback rows.
- Ensure reader preserves enough per-code history before feature generation.

## Forbidden Scope

Label generation, dataset builder, Candidate AI body, training, inference, backtest, trading, broker live access, ordering, and portfolio auto-update are not implemented.

## pytest

`python3 scripts/audit_phase4i_real_feature_readiness.py && python3 -m pytest tests/test_phase4i_real_feature_readiness.py && python3 -m pytest -q`
