# Phase17-B1I-C Canonical Historical Data, Point-in-time, and Feature Readiness

## Judgment

Final judgment: `PHASE17_B1I_C_POINT_IN_TIME_DATA_REQUIRED`

Secondary judgment: `PHASE17_B1I_C_CANONICAL_DATA_REFRESH_REQUIRED`

Normal Runtime v2 / normal Feature Producer readiness was reviewed, but feature generation was not executed. The Historical Runtime 5BD run was not started.

## Scope Guard

- runtime_v2_modification: `False`
- alternate_runtime_or_feature_producer: `False`
- historical_only_feature_logic: `False`
- training_artifact_fallback: `False`
- hand_generated_or_copied_features: `False`
- tachibana_or_submit_or_broker_write: `False`
- ai_retraining: `False`
- Runtime v2 changed: `False`
- Feature Producer changed: `False`
- Current/Ledger/Pending/Runtime State mutated: `False`

## Canonical Authority Decision

| Authority | Status | Physical path / identity | PIT rule |
| --- | --- | --- | --- |
| OHLCV | `PASS` | `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` | Only rows with target_date <= historical market_data_as_of / feature_cutoff may be visible. |
| Trading Calendar | `POINT_IN_TIME_DATA_REQUIRED` | `.runtime/data/raw/jquants/trading_calendar/data.parquet; .runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` | Calendar visible at calendar_as_of; no weekday fallback for official historical 5BD acceptance. |
| Listed Issues / PIT Universe | `POINT_IN_TIME_DATA_REQUIRED` | `.runtime/data/raw/jquants/listed_issues/data.parquet; .runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` | Use latest listed snapshot with Date/target_date <= listed_issues_as_of and <= universe_as_of; future listed status is forbidden. |
| Corporate Action | `POINT_IN_TIME_DATA_REQUIRED` | `No standalone accepted corporate action table found; adjusted OHLCV fields/AdjFactor exist in raw quotes only` | Corporate actions must be visible only at corporate_action_as_of; adjusted-price-only policy requires explicit acceptance before use. |
| Valuation Price | `PASS_CONDITIONAL` | `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` | Use close where target_date <= valuation_as_of; no forward fill across missing official market dates without calendar approval. |
| Historical Fill Price | `POINT_IN_TIME_DATA_REQUIRED` | `No accepted historical fill-price authority/manifest found` | Fill price must use fill_cutoff and historical broker policy; no hand-filled prices. |

OHLCV is usable as the canonical normalized historical source. Trading Calendar, Listed Issues/PIT Universe, Corporate Action, and Historical Fill Price are not yet accepted as complete point-in-time authorities for official Historical Runtime execution.

## Point-in-time Fields

- `business_date`: historical business date under Runtime v2 clock
- `market_data_as_of`: latest visible canonical OHLCV target_date for the decision
- `calendar_as_of`: latest visible trading-calendar publication/snapshot date
- `listed_issues_as_of`: latest visible listed-issues snapshot date
- `universe_as_of`: same or stricter than listed_issues_as_of for universe hard gate
- `corporate_action_as_of`: latest visible corporate-action event/snapshot date
- `feature_cutoff`: max source date allowed for normal Feature Producer inputs
- `decision_cutoff`: max feature/data timestamp allowed for AI/planning decision
- `valuation_as_of`: max price date allowed for valuation
- `fill_cutoff`: max price/tick date allowed for Historical Broker fill simulation

## Gates

| Gate | Status |
| --- | --- |
| `canonical_authority` | `FAIL` |
| `trading_calendar` | `FAIL` |
| `listed_issues_pit_universe` | `FAIL` |
| `corporate_action` | `FAIL` |
| `feature_schema` | `PASS_FOR_EXISTING_RUNTIME_ARTIFACTS` |
| `normal_feature_producer` | `PASS` |
| `no_training_artifact` | `PASS` |
| `no_future_data` | `PASS_FOR_INSPECTED_EXISTING_ARTIFACTS` |
| `run_identity` | `PASS_NO_HISTORICAL_RUN_STARTED` |
| `feature_generation_allowed` | `False` |

Because not all required gates are PASS, normal Feature Producer execution is not permitted in this phase.

## 2026-07-09 Feature Missing Cause

- Requested artifact dir: `.runtime/operations/feature_artifacts/2026-07-09`
- Missing requested files: `candidate_features.parquet, opportunity_feature_input.parquet, position_feature_input.parquet, capital_policy_input.parquet`
- Carryover used: `True`, selected feature date: `2026-07-08`
- Feature refresh was `dry_run=true`, `execute=false`, `feature_generation_executed=false`.
- Market refresh readiness for 2026-07-09 was `NOT_READY` with `data_until_before_decision_for`.

Conclusion: 2026-07-09 artifacts are absent because the normal run carried over 2026-07-08 artifacts; this phase did not fill, copy, or regenerate them.

## 5BD Window Readiness

| Business date | Feature artifact dir exists | Missing files |
| --- | --- | --- |
| 2026-07-06 | `True` | `` |
| 2026-07-07 | `True` | `` |
| 2026-07-08 | `True` | `` |
| 2026-07-09 | `False` | `candidate_features.parquet, opportunity_feature_input.parquet, position_feature_input.parquet, capital_policy_input.parquet` |
| 2026-07-10 | `True` | `` |

The candidate 5BD window remains `2026-07-06` to `2026-07-10`, but official 5BD entry is blocked until canonical PIT authorities pass and 2026-07-09 feature readiness is resolved through the normal producer path.

## Evidence

- `reports/phase17_b1i_c_canonical_point_in_time_feature_readiness/canonical_authority_manifest.json`
- `reports/phase17_b1i_c_canonical_point_in_time_feature_readiness/point_in_time_readiness.json`
- `reports/phase17_b1i_c_canonical_point_in_time_feature_readiness/feature_readiness_report.json`
- `reports/phase17_b1i_c_canonical_point_in_time_feature_readiness/missing_2026_07_09_analysis.json`
- `reports/phase17_b1i_c_canonical_point_in_time_feature_readiness/five_bd_window_readiness.json`
- `reports/phase17_b1i_c_canonical_point_in_time_feature_readiness/source_profiles.json`
- `reports/phase17_b1i_c_canonical_point_in_time_feature_readiness/state_hashes_read_only_evidence.json`
- `reports/phase_reports/phase17_b1i_c_canonical_point_in_time_feature_readiness.json`

## Next

Recommended next work: provide and formally accept canonical PIT Trading Calendar, Listed Issues/Universe, Corporate Action policy/table, and Historical Fill Price authority; then proceed to `Phase17-B1I-D 5BD Entry Gate Revalidation`.
