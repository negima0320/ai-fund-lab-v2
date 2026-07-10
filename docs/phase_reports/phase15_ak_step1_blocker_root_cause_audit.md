# Phase15-AK Step1 Blocker Root Cause Audit

Date: 2026-07-10

## Objective

Phase15-AK audits the root causes of the Phase15-AJ Step1 Morning Acceptance stop.

This phase does not modify implementation and does not re-run Morning.

The audit separates three systems:

```text
A. Candidate AI Feature Contract
B. Safety REVIEW_REQUIRED Root Cause
C. Pending Lifecycle
```

## Evidence Checked

- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-morning-2026-07-10-20260710T011051.828366+0000.json`
- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-safety_evaluation-2026-07-10-20260710T010956.084553+0000.json`
- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-safety_refresh-2026-07-10-20260710T011001.895038+0000.json`
- `reports/safety/phase11/2026-07-10_safety_report.json`
- `.runtime/runtime_state/safety/latest_safety_decision.json`
- `.runtime/operations/feature_artifacts/2026-07-08/candidate_features.parquet`
- `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-sell_planning-2026-07-09-20260709T024852.974006+0000.json`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `scripts/run_phase4bg_formal_candidate_inference.py`
- `scripts/build_phase4ak_real_runtime_features.py`
- `scripts/build_phase4bc_long_history_features.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

## Executive Summary

Phase15-AJ did not fail because Submit or Broker Write was attempted. It failed before OrderPlan/Pending/Approval evidence could be produced.

Root causes:

1. Candidate AI feature schema mismatch:
   - The formal Candidate AI model expects 13 feature columns using `feature__...` model names.
   - Runtime strips the `feature__` prefix before reading the parquet.
   - The selected feature artifact has only 6 of the 13 required stripped columns.
   - Missing columns caused an unhandled `KeyError`, which surfaced as Morning `HALT`.

2. Safety evidence incomplete:
   - Runtime Safety Evaluation correctly produced `REVIEW_REQUIRED`.
   - Missing evidence: `broker_snapshot`, `market`.
   - Stale evidence: `current`, `runtime_state`.
   - Safety blocked BUY/SELL/SUBMIT.

3. Pending lifecycle unresolved:
   - A stale 2026-07-09 SELL Pending remains `APPROVED`.
   - It was produced by the 2026-07-09 SELL Planning run.
   - It was not consumed because Submit did not consume it.
   - Submit has a target-date guard, but Morning preflight does not automatically expire/cancel old Pending.

Final root-cause judgment:

```text
STEP1_BLOCKER_ROOT_CAUSE_IDENTIFIED
```

## A. Candidate AI Feature Contract Audit

### A1. Missing Columns

Morning halted with:

```text
['missing_flags_insufficient_history', 'missing_flags_price', 'missing_flags_volume',
 'price_momentum_return_60d', 'trend_ma_20_60_ratio', 'trend_ma_5_20_ratio',
 'volume_momentum_ratio_1d_20d'] not in index
```

The formal model stores feature names with `feature__` prefix. Runtime Candidate inference strips that prefix before indexing the feature parquet:

```python
frame[[column.replace("feature__", "", 1) for column in feature_columns]]
```

| Missing Column | Required By | Data Type | Required | Failure Stage |
|---|---|---|---:|---|
| `missing_flags_insufficient_history` | Candidate AI model feature `feature__missing_flags_insufficient_history` | bool / numeric-castable | Yes | Candidate AI `_feature_matrix` |
| `missing_flags_price` | Candidate AI model feature `feature__missing_flags_price` | bool / numeric-castable | Yes | Candidate AI `_feature_matrix` |
| `missing_flags_volume` | Candidate AI model feature `feature__missing_flags_volume` | bool / numeric-castable | Yes | Candidate AI `_feature_matrix` |
| `price_momentum_return_60d` | Candidate AI model feature `feature__price_momentum_return_60d` | float | Yes | Candidate AI `_feature_matrix` |
| `trend_ma_20_60_ratio` | Candidate AI model feature `feature__trend_ma_20_60_ratio` | float | Yes | Candidate AI `_feature_matrix` |
| `trend_ma_5_20_ratio` | Candidate AI model feature `feature__trend_ma_5_20_ratio` | float | Yes | Candidate AI `_feature_matrix` |
| `volume_momentum_ratio_1d_20d` | Candidate AI model feature `feature__volume_momentum_ratio_1d_20d` | float | Yes | Candidate AI `_feature_matrix` |

### A2. Candidate AI Formal Input Schema

Formal model:

```text
path=.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl
model_type=lightgbm.LGBMClassifier
feature_column_count=13
```

Model feature columns:

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

Runtime indexing columns after prefix-strip:

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

Actual artifact:

```text
path=.runtime/operations/feature_artifacts/2026-07-08/candidate_features.parquet
rows=4370
target_date=2026-07-08
columns_count=26
```

Present required columns:

| Column | Dtype | Null Count |
|---|---|---:|
| `liquidity_avg_volume_20d` | float64 | 55 |
| `price_momentum_return_20d` | float64 | 55 |
| `price_momentum_return_5d` | float64 | 55 |
| `trend_close_over_ma_20d` | float64 | 55 |
| `volatility_return_std_20d` | float64 | 55 |
| `volume_momentum_ratio_5d` | float64 | 55 |

Missing required columns are exactly the seven columns listed above.

### A3. Feature Producer Matrix

| Column | Expected Producer | CLI Job | Artifact | Produced? | Gap |
|---|---|---|---|---|---|
| `missing_flags_insufficient_history` | Candidate Feature Refresh / long-history feature builder | `market_refresh` -> feature refresh | `candidate_features.parquet` | No | `FEATURE_SCHEMA_MISMATCH` / possible `COLUMN_RENAME` from `missing_flags_insufficient_lookback` |
| `missing_flags_price` | Candidate Feature Refresh / long-history feature builder | `market_refresh` -> feature refresh | `candidate_features.parquet` | No | `FEATURE_SCHEMA_MISMATCH` |
| `missing_flags_volume` | Candidate Feature Refresh / long-history feature builder | `market_refresh` -> feature refresh | `candidate_features.parquet` | No | `FEATURE_SCHEMA_MISMATCH` |
| `price_momentum_return_60d` | Candidate Feature Refresh / long-history feature builder | `market_refresh` -> feature refresh | `candidate_features.parquet` | No | `COLUMN_PRODUCER_MISSING` or stale producer version |
| `trend_ma_20_60_ratio` | Candidate Feature Refresh / long-history feature builder | `market_refresh` -> feature refresh | `candidate_features.parquet` | No | `COLUMN_PRODUCER_MISSING` or stale producer version |
| `trend_ma_5_20_ratio` | Candidate Feature Refresh / long-history feature builder | `market_refresh` -> feature refresh | `candidate_features.parquet` | No | `COLUMN_PRODUCER_MISSING` or stale producer version |
| `volume_momentum_ratio_1d_20d` | Candidate Feature Refresh / long-history feature builder | `market_refresh` -> feature refresh | `candidate_features.parquet` | No | `COLUMN_PRODUCER_MISSING` or stale producer version |

Relevant evidence:

- `scripts/build_phase4ak_real_runtime_features.py` defines all seven missing columns.
- `scripts/build_phase4bc_long_history_features.py` also builds the missing long-history fields.
- The current `.runtime/operations/feature_artifacts/2026-07-08/candidate_features.parquet` does not contain them.
- `.runtime/operations/feature_refresh/2026-07-09/latest_features.json` points to `.runtime/operations/feature_artifacts/2026-07-08/candidate_features.parquet` and reports `latest_available_market_date=2026-07-08`.
- `.runtime/operations/feature_refresh/2026-07-08/feature_refresh_manifest.json` was not present in the inspected root.

### A4. Gap Classification

| Gap | Classification | Evidence |
|---|---|---|
| Formal Candidate model requires seven columns absent from selected artifact | `FEATURE_SCHEMA_MISMATCH` | Model feature list vs parquet columns |
| `missing_flags_insufficient_history` absent while artifact has `missing_flags_insufficient_lookback` | `COLUMN_RENAME` | Actual parquet column list |
| Long-history columns absent despite feature builders defining them | `FEATURE_REFRESH_STALE` / `COLUMN_PRODUCER_MISSING` | Feature artifact selected from 2026-07-08 lacks columns |
| Morning surfaced this as `HALT` rather than `REVIEW_REQUIRED` artifact | `BUY_AI_ADAPTER` | Candidate producer did not catch `KeyError` around `_feature_matrix` |

### A5. Runtime Responsibility

Runtime must not fill missing AI features with:

```text
default value
mean
zero
false
hidden fallback
runtime local feature generation
```

Observed:

- Runtime did not silently impute the missing values.
- Runtime did not generate fake Candidate artifacts.
- Runtime did, however, allow a raw `KeyError` to become an unexpected `HALT` rather than a controlled `REVIEW_REQUIRED` with missing-column evidence.

Required direction:

- Data Pipeline must produce the formal Candidate AI schema.
- BUY AI adapter should classify schema mismatch as `REVIEW_REQUIRED`, not unexpected `HALT`.
- Runtime must not invent missing feature values.

## B. Safety REVIEW_REQUIRED Root Cause Audit

### B1. Safety Evidence

Safety Evaluation manifest:

```text
path=.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-safety_evaluation-2026-07-10-20260710T010956.084553+0000.json
final_state=REVIEW_REQUIRED
exit_code=20
reason=missing evidence: broker_snapshot, market
safety_evaluation_status=REVIEW_REQUIRED
```

Phase11 Safety Report:

```text
path=reports/safety/phase11/2026-07-10_safety_report.json
schema_version=phase11_safety_report_v2
business_date=2026-07-10
environment=demo
overall_decision=REVIEW_REQUIRED
generated_at=2026-07-10T01:09:56.087920+00:00
expires_at=2026-07-10T05:09:56.085407+00:00
```

Runtime Safety Decision:

```text
path=.runtime/runtime_state/safety/latest_safety_decision.json
decision=REVIEW_REQUIRED
reason=BROKER_SNAPSHOT_MISSING; QUOTE_MISSING_FOR_MONITOR; POSITION_WITHOUT_BROKER_SNAPSHOT
review_required=true
block_buy=true
block_sell=true
block_submit=true
halt_runtime=false
safety_status=PASS
```

### B2. REVIEW_REQUIRED Reason Decomposition

| Evidence | Observed | Classification | Owner Component |
|---|---|---|---|
| `broker_snapshot` | missing | `BROKER_STALE` / broker evidence missing | Broker ReadOnly |
| `market` | missing at `.runtime/runtime_state/market/2026-07-10/market_evidence.json` | `MARKET_STALE` / market evidence missing | Market Refresh |
| quotes | `quote_freshness=missing` | `MARKET_STALE` | Market Refresh / Quote evidence |
| Current | `current_as_of=2026-07-09`; stale | `CURRENT_STALE` | Current Projection / Acceptance preflight |
| Runtime State | `.runtime/runtime_state/current_state.json`; stale/missing | `RUNTIME_STATE` | Runtime State |
| Manual stop | old lock source detected but not root blocker in final reason | `MANUAL_STOP` evidence present | Safety / Operator |

Blocked actions:

```text
broker_order_api
demo_order_submit
production_order_submit
auto_sell
auto_recovery
auto_cancel
auto_retry
correction
cancel
retry
new_buy_without_human_review
```

Allowed actions:

```text
read_only_broker_sync
quote_polling
audit
report_generation
human_review
review_buy_opportunity
review_sell_or_hold_decision
```

Safety root cause:

```text
Safety is working as designed: missing Broker / Market evidence and stale Current / Runtime State produce REVIEW_REQUIRED and block BUY/SELL/SUBMIT.
```

This is not a Runtime hidden allow bug.

## C. Pending Lifecycle Audit

### C1. Current Pending

Observed:

```text
path=.runtime/pending_order_plan/pending_order_plan.json
pending_plan_id=pending-order-plan-50fd2eb10e0ea01f
state=APPROVED
created_at=2026-07-09
plan_created_date=2026-07-09
intended_submit_date=2026-07-09
target_session_date=2026-07-09
approval_status=APPROVED
approval_expires_at=2026-07-09T15:00:00+09:00
consume.consumed=false
items_count=5
side=SELL for all items
source_order_plan.path=.runtime/runtime_state/sell_pipeline/2026-07-09/order_plan.json
```

Producer:

```text
manifest=.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-sell_planning-2026-07-09-20260709T024852.974006+0000.json
job=sell_planning
exit_code=0
```

### C2. Why It Remained

Evidence:

- Pending was generated and approved by SELL Planning.
- It was not consumed: `consume.consumed=false`.
- Submit did not consume it.
- Submit has guard:

```text
if pending.target_session_date != business_date:
    return "pending target_session_date mismatch"
```

Therefore, a later 2026-07-10 Submit should be blocked from consuming the stale 2026-07-09 Pending.

However:

- Morning preflight does not automatically expire or cancel stale Pending.
- No inspected lifecycle evidence shows transition from `APPROVED` to `EXPIRED`, `BLOCKED`, `REVIEW_REQUIRED`, or `CONSUMED`.

### C3. Expected vs Current Lifecycle

Expected:

```text
OrderPlan
↓
Pending
↓
Approval
↓
Submit
↓
Consumed
↓
History

or

Expired / Cancelled / Review Required before next session
```

Current:

```text
SELL OrderPlan 2026-07-09
↓
Pending APPROVED 2026-07-09
↓
Submit not consumed
↓
Still APPROVED on 2026-07-10
```

Lifecycle root cause:

```text
Pending expiry / carryover review is not closed before Morning Acceptance.
```

This is a Runtime state hygiene / Acceptance preflight gap, not the direct cause of the Candidate AI HALT.

## Root Cause Matrix

| Blocker | Immediate Cause | Root Cause | Owner Component | Runtime Bug? | Data Issue? | Design Gap? | Required Fix |
|---|---|---|---|---:|---:|---:|---|
| Candidate AI HALT | `KeyError` for seven missing feature columns | Formal Candidate model input schema does not match selected runtime feature artifact | Feature Refresh / Candidate AI adapter | Partial | Yes | Yes | Produce formal Candidate feature schema; adapter should emit `REVIEW_REQUIRED` on schema mismatch, not unexpected `HALT`. |
| Safety REVIEW_REQUIRED | Missing broker snapshot and market evidence; stale Current/runtime_state | Preflight evidence was not refreshed for 2026-07-10 | Broker ReadOnly / Market Refresh / Current / Runtime State | No | Yes | No | Refresh Broker ReadOnly and Market evidence; rerun Safety Evaluation/Refresh only. |
| Stale Pending | 2026-07-09 approved SELL Pending remains unconsumed | Pending lifecycle lacks pre-Morning stale pending expiry/carryover resolution in current Acceptance procedure | Pending Lifecycle / Acceptance Procedure | Partial | No | Yes | Add explicit stale Pending review/expiry/cancel/consume procedure before Morning retry. |
| Missing Candidate Artifact | Candidate producer did not write artifact before exception | Schema mismatch surfaced before controlled artifact payload was written | BUY AI adapter | Yes | Yes | Yes | Catch feature schema mismatch and write REVIEW_REQUIRED Candidate/Opportunity artifacts. |
| Missing OrderPlan/Pending/Approval | Morning HALTed before Planning | Upstream Candidate AI HALT and Safety REVIEW_REQUIRED blocked valid planning | Morning Planning | No | Upstream | No | Fix upstream evidence/schema first; do not bypass Planning. |

## Fix Priority

### Runtime Implementation Fix

- BUY AI adapter should catch missing feature columns and produce controlled `REVIEW_REQUIRED` artifacts:
  - `candidate_decisions.json`
  - `opportunity_rankings.json` with dependency reason
  - manifest fields with missing columns
- Pending lifecycle should expose an explicit stale Pending handling path before new Morning:
  - `APPROVED` stale -> `EXPIRED` or `REVIEW_REQUIRED`
  - no direct edit to Current or Pending

### Data Pipeline Fix

- Feature Refresh must produce Candidate AI formal model schema for the selected feature date.
- At minimum, selected `candidate_features.parquet` must include:
  - `missing_flags_insufficient_history`
  - `missing_flags_price`
  - `missing_flags_volume`
  - `price_momentum_return_60d`
  - `trend_ma_20_60_ratio`
  - `trend_ma_5_20_ratio`
  - `volume_momentum_ratio_1d_20d`
- Market evidence must exist at:
  - `.runtime/runtime_state/market/2026-07-10/market_evidence.json`
- Broker ReadOnly snapshot must exist for 2026-07-10.
- Current/runtime_state freshness must be restored or explicitly classified.

### Acceptance Procedure

Before retrying Step1:

1. Refresh Broker ReadOnly / Market evidence.
2. Re-run Safety Evaluation / Safety Refresh only.
3. Resolve or explicitly classify stale 2026-07-09 Pending.
4. Verify Candidate feature schema against the formal model before Morning.
5. Retry Morning only after Safety and feature schema are acceptable.

### Future

- Full automated Recovery apply path.
- Operator Review apply path.
- richer feature schema registry shared by model artifact and Feature Refresh.

## What This Is Not

This is not:

- Submit failure
- Broker Write failure
- Production endpoint issue
- Notification issue
- Capital Deployment Policy issue
- Hidden max order amount regression

Policy evidence in the Morning manifest was `PASS`:

```text
capital_deployment_policy_source=configs/runtime_v2/capital_deployment.json
capital_deployment_policy_version=capital_deployment_v1
policy_validation_status=PASS
```

## Final Judgment

```text
STEP1_BLOCKER_ROOT_CAUSE_IDENTIFIED
```

## Completion String

```text
PHASE15AK_STEP1_BLOCKER_ROOT_CAUSE_AUDIT_COMPLETE
```
