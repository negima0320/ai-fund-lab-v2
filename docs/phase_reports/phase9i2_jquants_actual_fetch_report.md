# Phase9-I2 J-Quants Actual Fetch Report

- judgment: FETCH_FAILED
- refresh_runner_status: PARTIAL
- jquants_api_fetch_attempted: True
- data_until: 2026-06-01
- readiness_status: NOT_READY

## Executed Command

```bash
python3 scripts/run_phase9i_market_data_refresh.py --from-date 2026-06-02 --to-date 2026-06-16 --no-dry-run --allow-api-fetch --backup-existing --markdown-report-path docs/phase_reports/phase9i2_jquants_actual_fetch_report.md --json-report-path reports/phase_reports/phase9i2_jquants_actual_fetch_report.json
```

## Freshness After Attempt

- raw daily_quotes latest: 2026-06-01
- normalized daily_quotes latest: 2026-06-01
- listed_info latest: 2026-06-01
- trading_calendar latest: 2026-06-07
- raw daily_quote response latest: 2026-06-12

## Endpoint Results

| endpoint | status | existing_latest | fetched_rows | rows | max_date |
| --- | --- | ---: | ---: | ---: | ---: |
| daily_quotes | FAILED | 2026-06-01 | 0 | 0 |  |
| listed_info | FAILED | 2026-06-01 | 0 | 0 |  |
| trading_calendar | FAILED | 2026-06-07 | 0 | 0 |  |

## Failure Classification

- endpoint_error
- http_400_bad_request_or_out_of_range

## Blocked Reasons

- api_fetch_failed:JQuantsClientError
- data_until_before_decision_for

## Warnings

- none

## Safety Confirmation

- secret_leakage_detected: False
- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- paper_ledger_fill_executed: False
- virtual_fill_executed: False
- feature_generation_executed: False
- model_retraining_executed: False
- inference_executed: False
- live_order_allowed: False
