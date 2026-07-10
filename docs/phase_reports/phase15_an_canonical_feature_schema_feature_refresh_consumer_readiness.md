# Phase15-AN Canonical Feature Schema / Feature Refresh Consumer Readiness

Date: 2026-07-10

## Objective

Phase15-AN implements the Phase15-AM Runtime Data Contract remediation plan for Feature Refresh.

The scope is:

```text
Feature Refresh
↓
Canonical Schema
↓
Artifact
↓
Consumer Ready
```

This phase does not change AI models, AI training, ranking logic, PM decision logic, Broker Write, orders, notification real send, launchd, or Current.

## Final Judgment

```text
PHASE15AN_CANONICAL_FEATURE_SCHEMA_FEATURE_REFRESH_CONSUMER_READINESS_COMPLETE
```

## Summary

Feature Refresh is no longer accepted by artifact existence alone.

Implemented:

- Canonical Runtime feature schema registry for Candidate, Opportunity, and PM feature inputs.
- Candidate formal 13-column schema readiness validation.
- Canonical rename detection for `missing_flags_insufficient_lookback` vs `missing_flags_insufficient_history`.
- Opportunity prefix policy validation: Runtime feature artifacts must be unprefixed; prefixed artifact columns are `REVIEW_REQUIRED`.
- PM readiness validation: if Current has positions, `position_feature_input.parquet` may not be 0 rows.
- Consumer readiness artifact:

```text
.runtime/operations/feature_consumer_readiness/<feature_date>.json
```

- Feature date contract / market refresh manifest fields:

```text
consumer_ready
schema_version
candidate_schema_status
candidate_missing_columns
opportunity_schema_status
pm_schema_status
consumer_readiness_artifact_path
```

## Implementation

### New Module

```text
src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py
```

Defines:

- `CANONICAL_SCHEMA_VERSION`
- `CANDIDATE_REQUIRED_COLUMNS`
- `OPPORTUNITY_REQUIRED_COLUMNS`
- `PM_REQUIRED_COLUMNS`
- `validate_feature_consumer_readiness()`
- `write_feature_consumer_readiness()`

### Updated Runtime Boundary

```text
src/ai_fund_lab_v2/runtime_v2/market_refresh/feature_date_contract.py
```

`resolve_feature_date_contract()` now validates consumer readiness after required artifacts exist.

If artifact files exist but consumer schemas are not ready:

```text
status=REVIEW_REQUIRED
reason=consumer_schema_review_required:<consumer>
```

### Updated Market Refresh Result

```text
src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py
```

`RuntimeV2MarketRefreshResult` now exposes consumer readiness fields so CLI manifests can show why Feature Refresh is not consumer-ready.

### Updated Morning Propagation

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
```

Morning stage details now include the same consumer readiness fields from Feature Date Contract.

## Canonical Candidate Schema

Candidate Feature artifact must contain the formal model 13 columns, unprefixed:

```text
liquidity_avg_volume_20d
missing_flags_insufficient_history
missing_flags_price
missing_flags_volume
price_momentum_return_20d
price_momentum_return_5d
price_momentum_return_60d
trend_close_over_ma_20d
trend_ma_20_60_ratio
trend_ma_5_20_ratio
volatility_return_std_20d
volume_momentum_ratio_1d_20d
volume_momentum_ratio_5d
```

Plus required key columns:

```text
target_date
code
```

## Column Rename Policy

Canonical:

```text
missing_flags_insufficient_history
```

Legacy / mismatch:

```text
missing_flags_insufficient_lookback
```

Runtime adapters do not silently rename this column. If an artifact contains the legacy alias without the canonical column, readiness is `REVIEW_REQUIRED`.

## Opportunity Prefix Policy

Phase15-AM decision implemented:

```text
Artifact columns are unprefixed.
Consumers map to model-level feature__ columns internally exactly once.
```

If `opportunity_feature_input.parquet` contains `feature__...` columns under this schema, readiness is `REVIEW_REQUIRED`.

This prevents:

```text
feature__
↓
feature__feature__
```

## PM Feature Policy

`position_feature_input.parquet` must satisfy:

- required columns: `target_date`, `code`
- if Current has positions, row count must be greater than 0
- if Current has no positions, 0 rows are allowed only with `no_position_reason`

This closes the Phase15-AL gap:

```text
Current has positions
↓
PM feature 0 rows
↓
previously ambiguous
↓
now REVIEW_REQUIRED
```

## Consumer Readiness Matrix

| Consumer | Ready Condition | Review Required Condition | Manifest Field |
|---|---|---|---|
| Candidate AI | all canonical required columns present | missing columns or alias mismatch | `candidate_schema_status`, `candidate_missing_columns` |
| Opportunity AI | required columns present and no prefixed artifact columns | missing columns or `feature__...` artifact columns | `opportunity_schema_status` |
| Position Management AI | PM required columns present and Current / row count consistent | Current positions with 0 rows, missing columns, empty no-position artifact without reason | `pm_schema_status` |

## Runtime Hidden Fallback Prevention

The new readiness check blocks:

```text
artifact exists -> PASS
```

when schema is not consumer-ready.

The new readiness check does not do:

```text
missing -> default -> continue
missing -> silent rename -> continue
missing -> NaN -> continue
```

## Regression

Added:

```text
tests/runtime_v2/test_phase15an_feature_consumer_readiness.py
```

Coverage:

- Candidate 13 columns -> READY
- Candidate 1 missing column -> `REVIEW_REQUIRED`
- Candidate rename mismatch -> `REVIEW_REQUIRED`
- Opportunity prefixed artifact column -> `REVIEW_REQUIRED`
- PM Current positions + 0 rows -> `REVIEW_REQUIRED`
- Market Refresh contract / manifest records `consumer_ready`

Updated representative existing fixtures to satisfy the canonical schema:

- `tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py`
- `tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py`
- `tests/runtime_v2/test_phase14e41_jquants_connectivity_error_classification.py`
- `tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py`

## Verification

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15an_feature_consumer_readiness.py tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/runtime_v2/test_phase14e41_jquants_connectivity_error_classification.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py tests/runtime_v2/test_phase15af_position_management_runtime_connection.py
```

Result:

```text
26 passed
```

Executed:

```text
env PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15an python3 -m compileall src/ai_fund_lab_v2/runtime_v2/market_refresh src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py tests/runtime_v2/test_phase15an_feature_consumer_readiness.py
```

Result:

```text
PASS
```

## Acceptance

Closed in this phase:

```text
Feature Refresh
↓
Canonical Schema
↓
Consumer Ready
```

Remaining for later phases:

- Candidate / Opportunity controlled validation inside AI producer path when schema mismatch reaches the AI boundary.
- PM derived/defaulted field manifesting inside Position Management path.
- Runtime Data Readiness Gate before Morning / SELL Planning.
- Pending lifecycle remediation for stale approved Pending.

## Prohibited Actions Confirmation

This phase did not perform:

- AI model change
- AI retraining
- AI logic change
- Opportunity ranking logic change
- PM decision logic change
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd change
- Current edit

## Completion String

```text
PHASE15AN_CANONICAL_FEATURE_SCHEMA_FEATURE_REFRESH_CONSUMER_READINESS_COMPLETE
```
