# Phase9-J Feature Artifact Refresh Plan

## Purpose

Phase9-J refreshes Phase9 daily-operation feature artifacts using the latest available J-Quants-derived market data.

Current market data basis:

```text
requested_to_date: 2026-06-16
latest_available_date: 2026-06-15
target_data_until: 2026-06-15
decision_for=2026-06-15: READY
decision_for=2026-06-16: NOT_READY
```

Phase9-J performs feature freshness audit and optional feature artifact generation only.

It does not perform:

```text
AI retraining
inference
OrderPlan generation
Paper Ledger fill
virtual fill
Broker order
OpenD startup
unlock_trade
full backtest
```

## Current Freshness Context

Phase9-I3 updated J-Quants-derived market data to:

```text
normalized daily_quotes: 2026-06-15
listed_info: 2026-06-16
trading_calendar: 2026-06-16
data_until: 2026-06-15
```

Existing Candidate / Opportunity / Position / Capital artifacts may still be older than `2026-06-15`. Phase9-J therefore treats freshness as a first-class audit target before Phase9-K model manifest / retrain review.

## Target Artifacts

Phase9-J handles these artifacts:

```text
Candidate AI feature artifact
Opportunity AI feature input artifact
Position Management AI feature input artifact
Capital Allocation policy input artifact
```

Output root:

```text
.runtime/phase9/features/2026-06-15/
```

Files:

```text
candidate_features.parquet
opportunity_feature_input.parquet
position_feature_input.parquet
capital_policy_input.parquet
```

## Source Data Refs

Primary inputs:

```text
.runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet
.runtime/data/raw/jquants/listed_issues/data.parquet
```

These sources are J-Quants-derived. No Paper Ledger, Broker Snapshot, realized PnL, backtest result, cash, portfolio value, selected symbol, or bought symbol is used as a training or feature source in Phase9-J.

## Generation Method

### Candidate AI

Uses existing Candidate Feature Builder logic:

```text
ai_fund_lab_v2.candidate_ai.feature_builder.build_candidate_features_mock_with_audit
```

Input rows are normalized daily quotes filtered to:

```text
target_date <= target_data_until
```

Output rows use:

```text
as_of_date = target_data_until
target_date = target_data_until
data_until = target_data_until
```

### Opportunity AI

Phase9-J does not run Opportunity inference.

It creates an Opportunity feature input artifact from Candidate features by prefixing the J-Quants-derived feature columns with `feature__`.

This artifact is an input table for later model eligibility / inference phases, not a trading recommendation.

### Position Management AI

Phase9-J does not read Broker holdings and does not update Paper Ledger.

If no Phase9 holdings input is available, it writes an empty but schema-valid Position feature input artifact. This keeps freshness accounting explicit without inventing positions.

### Capital Allocation Policy Input

Phase9-J does not run Capital Allocation decisions.

It writes a policy input artifact containing references to the Candidate / Opportunity / Position artifacts. Actual allocation decisions remain a later phase.

## Feature Schema Hash

Each artifact records:

```text
feature_schema_hash
```

The hash is derived from the ordered artifact column list. It is intended for Phase9-K model manifest / eligibility review.

## Future Leakage Prevention

For every artifact:

```text
target_date <= target_data_until
as_of_date <= target_data_until
data_until <= target_data_until
```

Rows after `target_data_until` are treated as leakage and produce:

```text
FEATURE_SCHEMA_REVIEW_REQUIRED
```

## Existing Artifact Safety

Phase9-J does not overwrite Phase4 / Phase5 / Phase6 / Phase7 historical artifacts.

Phase9 outputs are versioned by `target_data_until` under:

```text
.runtime/phase9/features/<target_data_until>/
.runtime/phase9/feature_refresh/<target_data_until>/
```

## Modes

Dry-run:

```bash
python3 scripts/run_phase9j_feature_refresh.py \
  --target-data-until 2026-06-15
```

Behavior:

```text
audit existing Phase9 feature artifacts
do not generate features
do not overwrite files
write manifest/report
```

Execute:

```bash
python3 scripts/run_phase9j_feature_refresh.py \
  --target-data-until 2026-06-15 \
  --execute
```

Behavior:

```text
generate Phase9 feature artifacts
write manifest/report
fail closed on invalid source data
do not run retraining or inference
```

## Manifest

Manifest path:

```text
.runtime/phase9/feature_refresh/2026-06-15/feature_refresh_manifest.json
```

Records:

```text
run_id
target_data_until
ai_name
status
source_data_refs
output_artifact_refs
row_count
min_date
max_date
feature_schema_hash
required_columns_status
future_leakage_check_status
warnings
blocked_reasons
created_at
```

## Report

Report paths:

```text
docs/phase_reports/phase9j_feature_refresh_report.md
reports/phase_reports/phase9j_feature_refresh_report.json
```

## Status

Possible statuses:

```text
FEATURES_READY
FEATURE_REFRESH_REQUIRED
FEATURE_SCHEMA_REVIEW_REQUIRED
FEATURE_REFRESH_FAILED
```

## Phase9-K Handoff

Phase9-K should use Phase9-J manifest fields to evaluate:

```text
model_version
train_until
data_until
feature_schema_hash
leakage_audit_status
retrain_mode
model eligibility
```

Phase9-K may decide whether retrain is required. Phase9-J does not retrain models.
