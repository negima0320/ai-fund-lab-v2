# Phase20-ZA Historical Candidate Feature Rows Empty Root Cause

## Status

```text
PHASE20_ZA_CANDIDATE_FEATURE_ROWS_EMPTY_ROOT_CAUSE_COMPLETE
```

## Scope

Target run:

```text
runtime-test-historical-extended-smoke-20260722T221713173889Z
```

Target stop:

```text
business_date = 2026-03-24
job = morning
exit_code = 20
buy_ai_status = REVIEW_REQUIRED
buy_ai_reason = candidate_feature_rows_empty
candidate_count = 0
opportunity_count = 0
```

This phase investigated evidence only. No fresh-run, resume, BEAR/RANGE run, Broker connection, Training, Calibration, model retraining, PM change, Safety change, or Accepted Generation change was executed.

## Root Cause

Final classification:

```text
ALL_ROWS_MISSING_HISTORY
```

Direct mechanism:

```text
4310 candidate feature rows
-> target_date == 2026-03-24 keeps 4310
-> universe_eligible == true keeps 0
-> Candidate producer emits candidate_feature_rows_empty
```

The historical as-of market input for `2026-03-24` contains only 25 business dates from `2026-02-16` to `2026-03-24`. The Candidate feature builder requires 60 rows for 60BD momentum / trend features. Therefore every row is marked:

```text
missing_flags_insufficient_history = true
missing_flags_price = true
universe_eligible = false
excluded_reason contains insufficient_lookback
```

This is not a Safety/Pending/PM issue.

## Input Statistics

Target feature artifact:

```text
.runtime/operations/feature_artifacts/2026-03-24/candidate_features.parquet
```

Key statistics:

```text
total row count = 4310
target_date = 2026-03-24
as_of_date = 2026-03-24
data_until = 2026-03-24
code dtype = object
code examples = 13010, 13050, 13060, 13080, 13090, 130A0, 13110, 13190, 13200, 13210
```

Boolean counts:

```text
universe_eligible: false = 4310
is_current_listed: true = 4294, false = 16
has_current_name: true = 4294, false = 16
is_fresh_price: true = 4238, false = 72
is_allowed_product: true = 3761, false = 549
```

Missing / exclusion counts:

```text
missing_flags_insufficient_history: true = 4310
missing_flags_price: true = 4310
missing_flags_volume: false = 4215, true = 95

excluded_reason:
  insufficient_lookback = 3746
  insufficient_lookback,disallowed_product = 492
  insufficient_lookback,stale_price,disallowed_product = 41
  insufficient_lookback,not_current_listed,missing_name,stale_price,disallowed_product = 16
  insufficient_lookback,stale_price = 15
```

Required model feature completeness:

```text
required feature count = 13
rows complete across all required model features = 0
all-null numeric feature columns include 60BD/20BD momentum, trend, volatility, and liquidity fields
```

## Filter Pipeline

Candidate producer filter reproduction:

| Stage | Before | After | Dropped |
|---|---:|---:|---:|
| raw rows | 4310 | 4310 | 0 |
| target_date == feature_date | 4310 | 4310 | 0 |
| universe_eligible true | 4310 | 0 | 4310 |
| listing/product/freshness true | 0 | 0 | 0 |
| excluded_reason empty | 0 | 0 | 0 |
| missing_flags_insufficient_history false | 0 | 0 | 0 |
| missing_flags_price false | 0 | 0 | 0 |
| missing_flags_volume false | 0 | 0 | 0 |
| required feature non-null | 0 | 0 | 0 |
| finite numeric model input | 0 | 0 | 0 |
| model input construction | 0 | 0 | 0 |

First zero stage:

```text
universe_eligible true
```

## Normal Day Comparison

Control run:

```text
runtime-test-historical-extended-smoke-20260722T215152074231Z
business_date = 2026-06-16
```

Control feature artifact:

```text
reports/runtime_tests/backups/backup-historical-extended-smoke-20260722T215144136456Z/state/operations/feature_artifacts/2026-06-16/candidate_features.parquet
```

Comparison:

| Item | 2026-03-24 Target | 2026-06-16 Control |
|---|---:|---:|
| Input rows | 4310 | 4364 |
| universe_eligible true | 0 | 3676 |
| Required-feature complete rows | 0 | 4180 |
| Producer model input rows | 0 | 3676 |
| Candidate output count | 0 | 50 |
| BUY AI status | REVIEW_REQUIRED | PASS |

Source OHLCV coverage:

| Item | 2026-03-24 Target | 2026-06-16 Control |
|---|---:|---:|
| Oldest date | 2026-02-16 | 2026-02-16 |
| Latest date | 2026-03-24 | 2026-06-16 |
| Business date count | 25 | 81 |
| Median per-symbol history | 25 | 81 |
| Satisfies 60BD warmup | false | true |

The direct difference is not schema readiness or model readiness. It is warmup/history sufficiency before Candidate inference.

## Date Contract

Observed contract:

```text
business_date = 2026-03-24
feature_date = 2026-03-24
target_date = 2026-03-24
as_of_date = 2026-03-24
data_until = 2026-03-24
```

Candidate producer behavior:

```text
candidate_features.parquet rows where target_date == feature_date
```

The target artifact has same-date rows and passes future leakage checks. No target_date or as_of_date mismatch was found. No Historical-only Candidate producer date interpretation was found.

## Code Path

Source:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

Function:

```text
_produce_candidate_artifact
```

Relevant path:

```text
latest = frame[frame["target_date"].astype(str) == feature_date]
latest = latest[latest["universe_eligible"].fillna(False).astype(bool)]
latest = latest[latest["excluded_reason"].fillna("").astype(str).eq("")]
if latest.empty:
    reason = candidate_feature_rows_empty
```

The empty condition is reached after the `universe_eligible` filter.

## Judgment

```text
EXPECTED_FAIL_CLOSED_FOR_INELIGIBLE_CANDIDATE_FEATURE_TABLE
```

Candidate producer behavior is correct fail-closed behavior for an ineligible Candidate feature table. The immediate stop is expected once all rows are marked ineligible. The upstream issue is that the selected BULL Campaign start date does not provide sufficient pre-start historical warmup in the available historical as-of input.

## Repair Need

Runtime / Candidate producer repair:

```text
not required
```

Do not convert `candidate_feature_rows_empty` to READY_EMPTY. Do not skip the review-required stop. Do not relax filters. Do not change PM, Safety, Pending, models, or Accepted Generation.

Campaign planning implication:

```text
Future campaign periods must satisfy Candidate feature warmup availability before fresh-run execution.
```

## Validation

Executed:

```bash
PYTHONPATH=src python3 scripts/inspect_phase20_za_candidate_filter_pipeline.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase20_za_candidate_filter_pipeline.py
```

Result:

```text
inspection script: PASS
targeted pytest: 1 passed
```

## Acceptance

- ROOT_CAUSE_IDENTIFIED: PASS
- FILTER_STAGE_REPRODUCED: PASS
- FIRST_ZERO_STAGE_IDENTIFIED: PASS
- NORMAL_DAY_COMPARED: PASS
- PM_UNCHANGED: PASS
- SAFETY_UNCHANGED: PASS
- ACCEPTED_GENERATION_UNCHANGED: PASS
- LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED: PASS

## Final Judgment

```text
PHASE20_ZA_CANDIDATE_FEATURE_ROWS_EMPTY_ROOT_CAUSE_COMPLETE
```
