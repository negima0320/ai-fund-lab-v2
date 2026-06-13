# Phase4-BC Long History Feature Regeneration

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_LABEL_REGENERATION`
- feature_row_count: `5066399`
- eligible_count: `4784948`
- excluded_count: `281451`
- target_date range: `2021-06-14` to `2026-06-12`
- target_date_count: `1222`
- feature_column_count: `13`
- schema_validation_status: `OK`
- leakage_audit_status: `OK`
- forbidden_feature_detected: `False`
- future_column_detected: `False`
- label_column_detected: `False`
- purpose: regenerate historical Candidate feature table from Phase4-BB long-history normalized data.

## Scope

Phase4-BC performs feature regeneration and feature quality audit only.

- label_generation_executed: `False`
- dataset_rebuild_executed: `False`
- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`
- promotion_performed: `False`
- reader_switch_performed: `False`

## Input

- `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet`
- `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/manifest.json`
- `reports/candidate_ai/full_range/phase4bb_long_history_normalized_summary.json`

## Output

- `.runtime/candidate_ai/features/`
- `.runtime/candidate_ai/manifests/`
- `.runtime/candidate_ai/audit/`
- `reports/candidate_ai/full_range/phase4bc_long_history_feature_regeneration_summary.json`
- `reports/phase_reports/phase4bc_long_history_feature_regeneration_audit.json`

## Feature Scope

Phase4-BC regenerates the existing 13 implemented features only:

- `price_momentum_return_5d`
- `price_momentum_return_20d`
- `price_momentum_return_60d`
- `volume_momentum_ratio_5d`
- `volume_momentum_ratio_1d_20d`
- `volatility_return_std_20d`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `trend_ma_20_60_ratio`
- `liquidity_avg_volume_20d`
- `missing_flags_insufficient_history`
- `missing_flags_price`
- `missing_flags_volume`

No new feature expansion is performed in this phase.

## Quality Gate

The quality gate checks Train / Validation / Test separately.

- Train: `2021-09-09` to `2024-12-31`
- Validation: `2025-01-01` to `2025-12-31`
- Test: `2026-01-01` to `2026-05-15`

The Train split must have:

- `all_null_feature_count_train = 0`
- feature variance available
- no forbidden future or label columns
- schema validation `OK`
- leakage audit `OK`

This directly verifies that the Phase4-AT training-period null/constant issue is resolved by long-history coverage.

## Quality Gate Result

Train:

- all_null_feature_count_train: `0`
- constant_feature_count_train: `0`
- near_constant_feature_count_train: `0`
- high_null_feature_count_train: `0`
- feature_variance_available_train: `True`
- major feature non-null rate: `0.990079`

Validation:

- all_null_feature_count_validation: `0`
- constant_feature_count_validation: `0`
- high_null_feature_count_validation: `0`

Test:

- all_null_feature_count_test: `0`
- constant_feature_count_test: `0`
- high_null_feature_count_test: `0`

AT issue:

- at_null_constant_problem_resolved: `True`

## Readiness

Success readiness:

- `READY_FOR_LONG_HISTORY_LABEL_REGENERATION`

Next phase:

- Phase4-BD Long History Label Regeneration.
