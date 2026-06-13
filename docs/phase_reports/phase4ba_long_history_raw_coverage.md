# Phase4-BA Long History Raw Coverage Audit

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_NORMALIZED_REBUILD`
- fetched date range: `2021-06-14` to `2026-06-12`
- fetched_business_day_count: `1222`
- row/code count: `5261207` / `5019`
- raw_response_file_count: `1305`
- request_manifest_count: `1374`
- failed dates: `['2021-06-01', '2021-06-02', '2021-06-03', '2021-06-04', '2021-06-07', '2021-06-08', '2021-06-09', '2021-06-10', '2021-06-11']`
- boundary_failed_dates: `['2021-06-01', '2021-06-02', '2021-06-03', '2021-06-04', '2021-06-07', '2021-06-08', '2021-06-09', '2021-06-10', '2021-06-11']`
- non_boundary_failed_dates: `[]`
- first_trainable_target_date: `2021-09-09`
- last_label_target_date: `2026-05-15`
- formal_training_coverage_sufficient: `True`

## Boundary Failure Policy

Treat 2021-06-01 through 2021-06-11 failures as expected unavailable start-boundary dates. They do not block normalization if 60-business-day lookback and 20-business-day label horizon coverage remain sufficient.

## Split Coverage

- train_target_date_count_estimate: `812`
- validation_target_date_count_estimate: `243`
- test_target_date_count_estimate: `87`

## Safety

- secret_value_detected: `False`
- api/fetch/normalized/feature/label/dataset/training/inference/backtest/trading: `False`

## Recommended Next Action

Proceed to Phase4-BB Long History Normalized Rebuild using isolated real_runtime normalized output paths.
