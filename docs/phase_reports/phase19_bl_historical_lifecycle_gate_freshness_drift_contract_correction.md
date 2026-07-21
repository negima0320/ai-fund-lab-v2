# Phase19-BL Historical Lifecycle Gate Freshness / Drift Contract Correction

## Final Judgment

```text
PHASE19_BL_CONTRACT_FIXED_LEGITIMATE_REVIEW_REMAINS
```

The Lifecycle Gate contract bug was corrected. Historical replay no longer treats Accepted Generation source coverage metadata as proof of future Runtime consumption, and drift checks no longer compute PSI or population ratios across incompatible baseline/current semantics.

The 2026-07-06 read-only re-evaluation still returns `REVIEW_REQUIRED`, but for explicit contract reasons:

- prediction semantics mismatch
- feature population scope mismatch
- population scope mismatch

This is a legitimate review state, not the previous false `source_data_after_business_date` / invalid PSI comparison.

## Root Cause

Three Lifecycle Gate contracts were mixed:

1. Freshness used generation-time source coverage (`raw_data_max_date_at_generation`, `normalized_data_max_date_at_generation`) as though it were target-date Runtime consumption.
2. Prediction drift computed PSI without proving that baseline and Runtime scores shared the same metric, transformation stage, calibration state, and population scope.
3. Feature drift and population ratio used different baseline/current populations, including validation-window aggregate baseline vs single-day Runtime CandidateTop50.

## Freshness Authority

Before:

```text
decision_date = 2026-07-06
raw_data_max_date_at_generation = 2026-07-14
normalized_data_max_date_at_generation = 2026-07-14
reason_codes = source_data_after_business_date
```

After:

```text
actual_consumed_source_max_date = 2026-07-06
inference_feature_date = 2026-07-06
reason_codes = []
freshness_status = PASS
```

Generation metadata remains recorded, but is not future-consumption authority.

## Prediction Semantics

Before:

```text
baseline prediction range ~= -0.249 to 0.698
runtime opportunity score range ~= 13 to 19220
PSI computed anyway
```

After:

```text
prediction_distribution_drift = BASELINE_CURRENT_SEMANTICS_MISMATCH
PSI = not computed
```

## Feature Semantics

Before:

```text
current feature_distribution_values = [1.0, 1.0, ...]
```

After:

Runtime current feature evidence is built from the target-date opportunity feature artifact and accepted feature order, with `feature__` alias handling. In read-only verification, values are no longer the fixed Candidate-score array.

Feature PSI is still skipped because the baseline is validation-window aggregate and Runtime current is single-day CandidateTop50.

## Population Scope

Before:

```text
baseline candidate population = 1940
runtime candidate population = 50
current_to_baseline_population_ratio computed
```

After:

```text
candidate_population_drift = BASELINE_CURRENT_POPULATION_SCOPE_MISMATCH
ratio = not computed
```

## BUY / SELL

The gate preserves Phase18/19 separation:

```text
BUY Planning = BLOCK
BUY Submit = BLOCK
SELL Planning = PASS
SELL Submit authorization = PASS
Current refresh = PASS
Valuation refresh = PASS
```

## Regression

```text
py_compile = PASS
pytest = 38 passed
```

## Non-mutation

This phase did not mutate shared Runtime Trading State, Accepted Generation, Runtime Pointer, Registry, Broker, Pending, or Ledger.

## Remaining Legitimate REVIEW_REQUIRED Findings

The 2026-07-06 replay remains `REVIEW_REQUIRED` because the currently materialized baseline/current comparison contract is not yet equivalent:

- baseline prediction semantics: `standardized_score`
- current prediction semantics: `runtime_opportunity_score`
- baseline population scope: `CandidateTop50_validation_window_aggregate`
- current population scope: `CandidateTop50_single_business_day`

Next work should materialize a Runtime-compatible daily baseline/current comparison contract or adjust the baseline artifact to include like-for-like Runtime observation scopes without using future trading outcomes.
