# Phase17-M Historical Consumer Wiring and Feature Temporal Authority Closure

## Final Judgment

`PHASE17_M_FEATURE_SCHEMA_REVIEW_REQUIRED`

Phase17-M closed the consumer wiring gaps found after Phase17-L. Historical as-of data is now wired into Market Refresh and Feature Refresh as run-scoped verified derived logical input, and the Runner now fails closed before Runtime invocation when Feature Date Contracts are not accepted.

The 5BD Clean Rerun must still not start yet, because the current 2026-07-06 and 2026-07-07 Feature Date Contracts are `REVIEW_REQUIRED`.

## Failure Classification

The failed run `runtime-test-historical-smoke-20260714T040238998774Z` is classified as:

- `HISTORICAL_ASOF_CONSUMER_WIRING_GAP`
- `HISTORICAL_FEATURE_INPUT_TEMPORAL_LEAKAGE_RISK`
- `FEATURE_DATE_CONTRACT_REVIEW_REQUIRED`

This is not a Runtime Core defect.

## As-of Consumer Wiring

Before Phase17-M, Historical as-of evidence was generated but Market Refresh still consumed the physical parquet:

- physical max date: `2026-07-10`
- business date: `2026-07-06`
- readiness: `INVALID`
- blocked reason: `future_row_detected`

Now Historical Market Refresh materializes verified logical inputs under:

`reports/runtime_tests/runs/<run_id>/daily/<business_date>/<job>/inputs/historical_asof/<business_date>/`

The logical inputs retain physical source path/hash, cutoff, logical max date, future-row exclusion count, run identity, and manifest hash. Physical canonical files are not modified.

## Feature Temporal Authority

Feature Refresh now receives the logical normalized OHLCV and listed issues inputs in Historical mode. Feature artifact resolution is guarded:

- artifact date must be `<= selected_feature_date`
- artifact date must be `<= business_date`
- violation becomes `TEMPORAL_CONTRACT_VIOLATION`

The prior 2026-07-06 evidence used `target_data_until=2026-07-10` and `feature_artifacts/2026-07-10`, which is now formally invalid for that business date.

## Feature Date Contract Review

Current 5BD status:

| business_date | expected feature_date | status | reason |
| --- | --- | --- | --- |
| 2026-07-06 | 2026-07-06 | REVIEW_REQUIRED | consumer_schema_review_required:candidate,opportunity |
| 2026-07-07 | 2026-07-07 | REVIEW_REQUIRED | consumer_schema_review_required:candidate,opportunity |
| 2026-07-08 | 2026-07-07 | PASS | carryover |
| 2026-07-09 | 2026-07-08 | PASS | carryover |
| 2026-07-10 | 2026-07-10 | PASS | accepted |

The 2026-07-06/07 candidate artifacts miss current required columns such as `missing_flags_insufficient_history`, `price_momentum_return_60d`, and `trend_ma_5_20_ratio`. Opportunity artifacts use `feature__` prefixed columns rather than the accepted unprefixed Runtime consumer schema. This was not converted to PASS.

## Plan and Run Gates

Runner `plan` now blocks:

- `REVIEW_REQUIRED`
- `BLOCKED`
- `HALT`
- missing materialized contract
- missing contract hash
- profile value used as authority
- selected feature date mismatch

Actual read-only plan for the current 5BD window returns:

`exit_code=70 PRECONDITION_FAILURE`

`run` also revalidates the plan before invoking Runtime CLI.

## Failed Run Freeze

Created:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260714T040238998774Z/failure_summary.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260714T040238998774Z/validation/failure_validation.json`

The run was not resumed. No reset, rollback, restore, 5BD rerun, feature generation, canonical update, J-Quants fetch, submit, execution, Demo submit, or Production access was executed.

## Tests

- Phase17-M tests: 4 passed.
- Phase17-K + Phase17-L tests: 17 passed.
- Related Market Refresh/Data Readiness regression: 18 passed, 2 existing fixture failures stop on `market_evidence_missing` before the target stage.
- Actual 5BD plan gate: expected `PRECONDITION_FAILURE`, exit code 70.

## Blocking

5BD Clean Rerun is blocked until the 2026-07-06 and 2026-07-07 Feature Date Contracts are accepted as `PASS` through a formal schema acceptance or regeneration review.

## Recommended Next

Recommended next prefix: `Phase17-M-FS`

Work Name: `Historical 5BD Feature Schema Acceptance or Regeneration Review`
