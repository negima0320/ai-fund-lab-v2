# Position Management Feature Input Contract

Status: Phase19-BU accepted runtime contract

This contract applies to Historical, Demo, and Production Runtime v2. It completes the Position Management feature input boundary without changing Position Management thresholds, EXIT / REDUCE policy, Opportunity score semantics, BUY policy, SELL policy, or mode-specific behavior.

## Authority

Position Management may consume only:

- Runtime Current for held-position state.
- Position Feature Artifact: `.runtime/operations/feature_artifacts/<feature_date>/position_feature_input.parquet`.
- Opportunity context artifact accepted by the Runtime Opportunity contract.

The PM adapter must not recalculate market technical features. Technical feature authority is the canonical Feature Refresh / Market Feature pipeline. The PM position feature artifact copies canonical technical columns from `candidate_features.parquet` for the same `feature_date` and `code`, and records source artifact and hash evidence.

## Required Features

For held positions, the following PM feature columns are required:

- `price_momentum_return_5d`
- `price_momentum_return_20d`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `volume_momentum_ratio_5d`
- `volatility_return_std_20d`

Required operational/provenance fields:

- `target_date`
- `feature_as_of_date`
- `code`
- `feature_source_artifact`
- `feature_source_hash`
- `required_features`
- `optional_features`
- `missing_features`
- `defaulted_features`
- `temporal_validation_status`

Required position state fields remain governed by the PM input contract and Current contract.

## Optional Features

`no_position_reason` is optional. It is used only for explicit no-position evidence and is not a scoring feature.

No PM scoring feature may be implicitly defaulted by the Runtime PM producer. `defaulted_features` must be empty for held-position inference.

## Temporal Contract

All PM feature rows must satisfy:

- `target_date <= feature_date`
- `feature_as_of_date <= feature_date`
- `data_until <= feature_date` when present
- `position_state_as_of <= feature_date` when present
- no future observations after `feature_date`

Historical mode may choose historical `business_date` and `feature_date`, but the PM feature schema and validation behavior must remain identical to Demo and Production.

## Fail-Closed Rules

When Current has held positions, Runtime must return `REVIEW_REQUIRED` and must not run PM inference if:

- a required PM feature column is missing
- a required technical value is missing or non-finite
- a held symbol has no PM feature row for the selected `feature_date`
- duplicate `target_date` / `code` rows exist
- `missing_features` lists any required feature
- `defaulted_features` is non-empty
- temporal validation fails or the artifact is stale

Existing equivalent Runtime reasons may be used, including:

- `pm_feature_required_columns_missing`
- `pm_feature_required_feature_missing`
- `pm_feature_rows_missing_for_current_positions`
- `pm_feature_contract_validation_failed`

## Decision Evidence

`position_management_decisions.json` must expose:

- `feature_contract_version`
- `feature_source_artifact`
- `feature_source_hash`
- `required_feature_validation`
- `optional_feature_status`
- `defaulted_features`
- `used_feature_snapshot`
- `temporal_validation_status`

## Production Commonness

The same PM producer, Feature Refresh path, PM input validation path, PM inference path, Sell Planning consumer path, and Submit guard path are used by Historical, Demo, and Production. Historical-specific feature completion, test-only fixture completion, and symbol-specific bypasses are prohibited.
