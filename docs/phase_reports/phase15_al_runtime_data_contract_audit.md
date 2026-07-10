# Phase15-AL Runtime Data Contract Audit

Date: 2026-07-10

## Objective

Phase15-AL audits AI Fund Lab v2 Runtime Data Contracts after Phase15-AK identified a Candidate AI feature schema mismatch.

This phase does not change implementation and does not execute Morning, Submit, Execution, Broker Write, orders, notification send, or launchd.

The audit target is:

```text
Producer
↓
Schema
↓
Artifact
↓
Consumer
```

## Final Judgment

```text
RUNTIME_DATA_CONTRACT_GAPS_FOUND
```

The Decision Chains are increasingly connected, but multiple Producer / Consumer schema contracts are not yet acceptance-ready.

## Executive Summary

Primary finding:

- Runtime Feature Refresh currently proves artifact existence, not consumer-specific schema readiness.

Confirmed gaps:

- Candidate AI formal model requires 13 model features; selected Runtime feature artifact contains only 6 of the stripped required columns.
- Opportunity AI can silently add missing model feature columns as `NaN` through `ensure_model_feature_columns()`, then preprocessing may continue. This is a hidden fallback risk.
- Opportunity feature artifact already contains `feature__...` columns, while Opportunity inference prefixes selected feature columns again, creating `feature__feature__...` risk.
- Position Management AI accepts minimal Current-derived holding fields and defaults/falls back for several fields; schema validation is partial.
- Safety has the clearest data readiness behavior: missing/stale evidence becomes `REVIEW_REQUIRED`, but Step1 lacked Broker/Market/Current freshness.
- Version contracts exist as strings, but there is no single Runtime Data Contract gate that verifies feature schema version + model version + artifact schema before Morning.

## 1. Data Contract Matrix

| Producer | Artifact | Consumer | Expected Schema | Actual Schema | Match | Gap | Severity |
|---|---|---|---|---|---|---|---|
| Market Refresh | `.runtime/runtime_state/market/<date>/market_evidence.json` | Safety Evaluation | `generated_at/as_of/business_date`, `market_summary` or `candidate_universe_market_summary`, `quotes` | Missing for 2026-07-10 | No | `PRODUCER_MISSING`, `STALE_ARTIFACT` | HIGH |
| Feature Refresh | `.runtime/operations/feature_artifacts/<date>/candidate_features.parquet` | Candidate AI | 13 formal model features after stripping `feature__`; key columns `target_date`, `code`; eligibility fields | 6 of 13 required model features present; 7 missing | No | `SCHEMA_MISMATCH`, `COLUMN_MISSING`, `COLUMN_RENAME` | BLOCKER |
| Feature Refresh | `.runtime/operations/feature_artifacts/<date>/opportunity_feature_input.parquet` | Opportunity AI | J-Quants features that become `feature__...` plus Candidate features | Artifact already contains `feature__...`; Opportunity prefixes again; many model features would be missing before `ensure_model_feature_columns()` | No | `CONSUMER_MISMATCH`, `VALIDATION_MISSING`, hidden NaN fallback | HIGH |
| Candidate AI | `.runtime/runtime_state/buy_ai/<date>/candidate_decisions.json` | Opportunity AI | `target_date`, `code`, `candidate_score`, `candidate_rank`, `candidate_reason`, model/source fields | Not generated in AJ due Candidate feature schema failure | No | upstream `SCHEMA_MISMATCH` | HIGH |
| Opportunity AI | `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json` | Morning Planning | `schema_version=runtime_v2_opportunity_ranking_v1`, `rankings[]`, symbol/rank/score/reason/confidence | Not generated in AJ due Candidate failure | Not reached | upstream gap | HIGH |
| Capital Deployment Policy | `configs/runtime_v2/capital_deployment.json` | Morning / Submit Guard | policy source/version/hash, exposure/sizing constraints | Loads and validates PASS | Yes | none in AL scope | LOW |
| Current Projection | `.runtime/persistent_ledger/state.json` | Position Management AI | positions with symbol/quantity and price or valuation fields | Exists; position keys include `symbol`, `quantity`, `average_price`, `market_value`; stale date 2026-07-09 | Partial | `STALE_ARTIFACT`; PM defaults missing optional fields | MEDIUM |
| Feature Refresh / Opportunity AI | opportunity + feature artifacts | Position Management AI | holding columns + Opportunity columns + feature columns | PM input feature artifact has 0 rows for 2026-07-08; opportunity dependency not generated for 2026-07-10 | Partial | `PRODUCER_MISSING`, `STALE_ARTIFACT` | HIGH |
| Broker ReadOnly | `.runtime/runtime_state/broker_readonly/<date>/*.json` | Safety / Submit SELL Guard | generated_at/snapshot_at, broker mode, positions, available quantity evidence | Missing for 2026-07-10 Safety; 2026-07-09 stale snapshot exists | No | `STALE_ARTIFACT`, `PRODUCER_MISSING` | HIGH |
| Persistent Ledger | orders/executions jsonl | Safety Evaluation | JSONL orders/executions filtered by business date | Present as files; Safety did not flag missing orders/executions | Partial | readiness depends on date contents | MEDIUM |
| Runtime State | `.runtime/runtime_state/current_state.json` | Safety Evaluation | generated/updated date, runtime safety state | stale/missing in Safety report | No | `RUNTIME_STATE`, `STALE_ARTIFACT` | MEDIUM |
| Safety Evaluation | `reports/safety/phase11/<date>_safety_report.json` | Safety Refresh | `schema_version=phase11_safety_report_v2`, business_date, environment, generated/expires, decision | Generated for 2026-07-10 and consumed | Yes | REVIEW_REQUIRED by evidence, not schema | LOW |
| Safety Refresh | `.runtime/runtime_state/safety/latest_safety_decision.json` | Morning / SELL / Submit | RuntimeSafetyDecision fields and block flags | Generated; decision `REVIEW_REQUIRED`, block flags true | Yes | not AL schema gap | LOW |

## 2. Candidate AI Contract

### Expected Schema

Formal model:

```text
model_path=.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl
model_type=lightgbm.LGBMClassifier
feature_column_count=13
```

Model feature list:

```text
feature__liquidity_avg_volume_20d
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
feature__price_momentum_return_20d
feature__price_momentum_return_5d
feature__price_momentum_return_60d
feature__trend_close_over_ma_20d
feature__trend_ma_20_60_ratio
feature__trend_ma_5_20_ratio
feature__volatility_return_std_20d
feature__volume_momentum_ratio_1d_20d
feature__volume_momentum_ratio_5d
```

Runtime Candidate adapter strips `feature__` before indexing:

```text
column.replace("feature__", "", 1)
```

### Actual Schema

Artifact:

```text
.runtime/operations/feature_artifacts/2026-07-08/candidate_features.parquet
rows=4370
target_date=2026-07-08
```

Present required model columns after prefix-strip:

```text
liquidity_avg_volume_20d
price_momentum_return_20d
price_momentum_return_5d
trend_close_over_ma_20d
volatility_return_std_20d
volume_momentum_ratio_5d
```

Missing required columns:

```text
missing_flags_insufficient_history
missing_flags_price
missing_flags_volume
price_momentum_return_60d
trend_ma_20_60_ratio
trend_ma_5_20_ratio
volume_momentum_ratio_1d_20d
```

Observed rename risk:

```text
missing_flags_insufficient_lookback
```

exists in the artifact, while the model requires:

```text
missing_flags_insufficient_history
```

### Candidate Classification

| Finding | Classification | Severity |
|---|---|---|
| Formal model requires columns not in feature artifact | `SCHEMA_MISMATCH`, `COLUMN_MISSING` | BLOCKER |
| `insufficient_history` vs `insufficient_lookback` | `COLUMN_RENAME` | HIGH |
| Missing model columns surface as raw `KeyError` / HALT | `VALIDATION_MISSING` in adapter | HIGH |
| Feature artifact version not verified against model feature list before Morning | `VERSION_MISMATCH` risk | HIGH |

## 3. Opportunity AI Contract

### Expected Inputs

Opportunity AI consumes:

```text
Candidate Artifact
+
opportunity_feature_input.parquet
```

Model:

```text
model_path=models/opportunity_ai/phase5e/opportunity_model.pkl
model_version=opportunity_model_phase5e_v1
feature_column_count=16
```

Required model features include Candidate features plus market/price-volume features:

```text
feature__candidate_rank
feature__candidate_reason
feature__candidate_score
feature__liquidity_avg_volume_20d
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
feature__price_momentum_return_20d
feature__price_momentum_return_5d
feature__price_momentum_return_60d
feature__trend_close_over_ma_20d
feature__trend_ma_20_60_ratio
feature__trend_ma_5_20_ratio
feature__volatility_return_std_20d
feature__volume_momentum_ratio_1d_20d
feature__volume_momentum_ratio_5d
```

### Actual Feature Artifact

```text
.runtime/operations/feature_artifacts/2026-07-08/opportunity_feature_input.parquet
rows=4370
columns include:
feature__price_momentum_return_5d
feature__price_momentum_return_20d
feature__volume_momentum_ratio_5d
feature__volatility_return_std_20d
feature__trend_close_over_ma_20d
feature__liquidity_avg_volume_20d
```

Opportunity inference selects J-Quants feature columns and prefixes them:

```text
columns={column: f"feature__{column}" for column in jq_feature_columns}
```

For an artifact column already named `feature__price_momentum_return_5d`, this creates:

```text
feature__feature__price_momentum_return_5d
```

Then:

```text
ensure_model_feature_columns()
```

adds missing model feature columns as `NaN`.

### Opportunity Classification

| Finding | Classification | Severity |
|---|---|---|
| Opportunity feature artifact appears already prefixed but consumer prefixes again | `CONSUMER_MISMATCH` | HIGH |
| Missing model features are added as NaN | `VALIDATION_MISSING`, hidden fallback risk | HIGH |
| Candidate artifact missing in AJ blocks Opportunity | upstream `SCHEMA_MISMATCH` | HIGH |
| No hard readiness gate for `missing_model_feature_count > 0` | `SCHEMA_VALIDATION_MISSING` | HIGH |

## 4. Position Management AI Contract

### Expected Inputs

Runtime PM producer builds holding snapshot from Current:

```text
Current
↓
current_holdings_snapshot.csv
↓
Position Management AI
```

Required holding columns:

```text
target_date
code
entry_price or current_return
current_price
holding_days
position_size
peak_return
```

PM also consumes:

```text
Opportunity inference output
Feature artifact
```

Expected Opportunity columns include:

```text
target_date
code
expected_edge_score
buy_rank
downside_risk_score
risk_guard_status
candidate_score
candidate_rank
buy_reason
no_buy_reason
calibration_policy_name
```

### Actual Inputs

Current observed:

```text
path=.runtime/persistent_ledger/state.json
as_of=2026-07-09
updated_at=2026-07-09
position_count=5
position keys=symbol, quantity, average_price, market_value, unrealized_pnl, source, as_of
```

Runtime PM adapter can derive:

- `code` from `symbol`
- `position_size` from `quantity`
- `entry_price` from `average_price`
- `current_price` from `market_value / quantity` or `average_price`
- `holding_days=0` if absent
- `peak_return=current_return` if absent

Actual `position_feature_input.parquet`:

```text
rows=0
columns=target_date, entry_date, code, holding_days, current_price, unrealized_return, feature_version, data_until, created_at, no_position_reason
```

### PM Classification

| Finding | Classification | Severity |
|---|---|---|
| Current is stale for 2026-07-10 | `STALE_ARTIFACT` | HIGH |
| PM depends on Opportunity output that was not generated in AJ | upstream `PRODUCER_MISSING` | HIGH |
| PM feature input has 0 rows | `PRODUCER_MISSING` / possibly valid no-position artifact only if Current empty, but Current has positions | HIGH |
| PM adapter derives/defaults holding fields | hidden fallback risk if not manifested | MEDIUM |
| PM validates minimal key columns but not a versioned Runtime PM input contract | `SCHEMA_VALIDATION_MISSING` | MEDIUM |

## 5. Safety Data Contract

Safety Evaluation expects:

```text
Current
Broker snapshot
Market evidence
Orders
Executions
Runtime State
Manual stop state
```

Observed Phase15-AJ Safety report:

```text
overall_decision=REVIEW_REQUIRED
missing_evidence=["broker_snapshot", "market"]
stale_evidence=["current", "runtime_state"]
broker_snapshot_freshness=missing
quote_freshness=missing
production_equivalent=false
```

Safety data contract behavior is correct:

- missing evidence does not become ALLOW
- stale evidence becomes REVIEW_REQUIRED
- BUY/SELL/SUBMIT are blocked

Gap is readiness, not hidden fallback.

## 6. Feature Refresh Contract

Feature Refresh currently guarantees these artifact names:

```text
candidate_features.parquet
opportunity_feature_input.parquet
position_feature_input.parquet
capital_policy_input.parquet
```

Evidence from tests and runtime code shows `market_refresh` checks artifact presence.

Missing contract:

```text
artifact exists
```

is not enough. Each artifact must satisfy its consumer schema:

- Candidate formal model feature list
- Opportunity model feature list
- Position Management input schema
- Capital Deployment input or explicit policy source contract

Current gap:

```text
Feature Refresh artifact presence PASS can coexist with AI schema FAIL.
```

## 7. Version Contract Audit

| Component | Version Field | Observed | Gap |
|---|---|---|---|
| Candidate feature artifact | `feature_version` | present in parquet | Not checked against model feature list |
| Candidate formal model | `model_version` | model payload version was null in inspected artifact; model type present | Version weak; feature list is the real contract |
| Candidate Runtime artifact | `schema_version=runtime_v2_candidate_decision_v1` | defined | Not generated in AJ due schema failure |
| Opportunity model | `opportunity_model_phase5e_v1` | present | Requires 16 features; missing features can be filled with NaN |
| Opportunity Runtime artifact | `schema_version=runtime_v2_opportunity_ranking_v1` | defined | Not generated in AJ |
| PM inference | `position_management_policy_phase6a_v1`, `position_management_feature_v1` | defined | Runtime input does not verify version readiness before inference |
| Safety report | `phase11_safety_report_v2` | present | PASS for schema |
| Runtime manifest | `schema_version=1` | present | Does not provide unified Data Contract readiness |

## 8. Hidden Fallback Audit

| Pattern | Found? | Location | Classification | Severity |
|---|---:|---|---|---|
| Missing Candidate column -> default -> continue | No | Candidate AI | Candidate HALTed instead | INFO |
| Missing Candidate column -> controlled REVIEW_REQUIRED | No | Candidate AI adapter | `VALIDATION_MISSING` | HIGH |
| Missing Opportunity model feature -> NaN -> continue | Yes | `ensure_model_feature_columns()` | hidden fallback risk | HIGH |
| Opportunity prefixed column -> double prefix | Yes | Opportunity feature consumer | `CONSUMER_MISMATCH` | HIGH |
| PM missing holding days -> default 0 | Yes | PM Runtime adapter | acceptable only if manifested | MEDIUM |
| PM missing peak_return -> current_return | Yes | PM inference | hidden fallback risk | MEDIUM |
| Safety missing evidence -> ALLOW | No | Safety Evaluation | fail-closed works | PASS |

## 9. Schema Validation Audit

| Component | Validation Present | Gap |
|---|---|---|
| Candidate feature table generic validation | Yes, `validate_feature_table()` | Validates general column prefixes, not formal model feature list readiness |
| Candidate Runtime producer | Partial | Does leakage audit; no missing model-column check before `_feature_matrix` |
| Opportunity Runtime inference | Partial | Audits leakage; missing model features are counted but not blocking |
| PM Runtime inference | Partial | Requires basic key columns; many fields are optional/defaulted |
| Safety Evaluation | Strong | Missing/stale evidence becomes REVIEW_REQUIRED |
| Market Refresh | Partial | Artifact presence check, not consumer schema validation |
| Morning preflight | Partial | Does not run Data Contract readiness gate before Candidate AI |

Required classification:

```text
SCHEMA_VALIDATION_MISSING
```

applies to Candidate model feature list, Opportunity model feature list, PM input readiness, and Feature Refresh consumer-specific validation.

## 10. Runtime Data Readiness Before Morning

Required before Step1 Morning retry:

| Area | Ready Check | Current Status |
|---|---|---|
| Market | `.runtime/runtime_state/market/<date>/market_evidence.json` exists and fresh | NOT READY |
| Feature | selected feature artifacts match Candidate/Opportunity/PM schemas | NOT READY |
| Candidate | formal model feature list satisfied by selected candidate feature artifact | NOT READY |
| Opportunity | Candidate artifact exists; opportunity feature columns match model without hidden NaN fill | NOT READY |
| PM | Current fresh; PM feature/opportunity inputs exist for date | NOT READY for SELL path |
| Safety | Safety Decision exists, unexpired, and ALLOW or explicit REVIEW_REQUIRED | REVIEW_REQUIRED |
| Pending | no stale approved Pending before new Morning | NOT READY |

## 11. Root Cause Classification

| Finding | Classification | Severity |
|---|---|---|
| Candidate formal model vs selected `candidate_features.parquet` mismatch | `SCHEMA_MISMATCH` | BLOCKER |
| Seven Candidate required columns missing | `COLUMN_MISSING` | BLOCKER |
| `missing_flags_insufficient_lookback` vs `missing_flags_insufficient_history` | `COLUMN_RENAME` | HIGH |
| Feature artifact selected from 2026-07-08 while Step1 is 2026-07-10 | `STALE_ARTIFACT` / carryover requires explicit acceptance | HIGH |
| Opportunity feature double-prefix risk | `CONSUMER_MISMATCH` | HIGH |
| Opportunity missing features filled with NaN | `VALIDATION_MISSING` / hidden fallback | HIGH |
| PM feature input 0 rows while Current has positions | `PRODUCER_MISSING` or wrong artifact for PM | HIGH |
| Market evidence missing for Safety | `PRODUCER_MISSING` | HIGH |
| Broker snapshot missing for Safety | `PRODUCER_MISSING` | HIGH |
| No unified Runtime Data Contract gate | `VALIDATION_MISSING` | BLOCKER |

## Required Fix Direction

This phase does not implement fixes.

Required next work should separate:

### Runtime Implementation

- Add a Data Contract readiness gate before Morning.
- Candidate adapter should emit controlled `REVIEW_REQUIRED` artifact on missing model columns.
- Opportunity inference should fail or REVIEW_REQUIRED on missing model feature columns instead of silently adding NaN.
- PM producer should manifest every derived/defaulted holding field.

### Data Pipeline

- Feature Refresh must generate the formal Candidate AI schema.
- Feature Refresh must produce Opportunity input in the consumer-expected prefix convention.
- Feature Refresh must produce PM feature input consistent with Current positions or explicitly mark no-position.
- Market evidence and Broker ReadOnly evidence must be fresh for Safety.

### Acceptance Procedure

- Verify Data Readiness before Morning:
  - model feature list vs artifact columns
  - feature date contract
  - Safety evidence
  - stale Pending

## Prohibited Actions Confirmation

This phase did not perform:

- Runtime implementation change
- Morning execution
- Submit
- Execution
- Broker Write
- Demo order
- Production order
- Notification send
- launchd change

## Completion String

```text
PHASE15AL_RUNTIME_DATA_CONTRACT_AUDIT_COMPLETE
```
