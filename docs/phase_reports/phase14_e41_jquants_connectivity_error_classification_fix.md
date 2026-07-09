# Phase14-E41 J-Quants Connectivity / Error Classification Fix

## Summary

- phase: Phase14-E41
- objective: Fix J-Quants connectivity/error classification so URL/network failures are not mislabeled as API parameter errors.
- code_changed: true
- broker_submit_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- final_judgement: PHASE14E41_JQUANTS_CONNECTIVITY_ERROR_CLASSIFICATION_FIXED

## Root Cause Candidate

E40 showed that the E39 Market Refresh failure was not supported by evidence as an API parameter error.

Observed E40 facts:

- Runtime v2 used the existing J-Quants refresh stack.
- `fetch_mode=per-date` is still the correct daily quotes design from Phase9-I3.
- 2026-07-06 and 2026-07-07 had successful per-date refreshes.
- 2026-07-08 and 2026-07-09 client logs showed repeated `status=url_error`.

Root cause candidate:

- primary: URL reachability / execution environment / transient network failure
- secondary: classification gap where `url_error` became `JQuantsClientError` and then `API_PARAM_ERROR`

## Implementation

### J-Quants Client

Updated `src/ai_fund_lab_v2/data_sources/jquants/client.py`.

`JQuantsClientError` now carries secret-safe diagnostics:

- endpoint
- date
- from_date
- to_date
- error_class
- network_error_type
- http_status
- url_host

The client classifies:

- HTTP 400 -> `API_PARAM_ERROR`
- HTTP 401 / 403 -> `API_AUTH_ERROR`
- HTTP 429 -> `API_RATE_LIMIT`
- HTTP 5xx -> `API_SERVER_ERROR`
- `URLError` / timeout -> `API_NETWORK_ERROR`
- unknown HTTP/non-HTTP -> `UNKNOWN_API_ERROR`

For network errors, `network_error_type` is classified as:

- dns
- ssl
- timeout
- connection_refused
- network_unreachable
- OSError subclass name
- generic URL error type

No token, API key, full URL query, raw request, or raw response is stored.

### Market Refresh

Updated `src/ai_fund_lab_v2/paper_trading/market_data_refresh.py`.

Market refresh now emits:

- `api_error_classification`
- `api_error_diagnostics`
- `next_action`

New taxonomy:

- `API_PARAM_ERROR`
- `API_AUTH_ERROR`
- `API_NETWORK_ERROR`
- `API_RATE_LIMIT`
- `API_SERVER_ERROR`
- `MARKET_DATA_NOT_YET_AVAILABLE`
- `DATA_FRESHNESS_BLOCKED`
- `UNKNOWN_API_ERROR`

`url_error` no longer becomes `API_PARAM_ERROR`.

Operator `next_action` examples:

- `API_NETWORK_ERROR` -> `check_network_connectivity`
- `API_AUTH_ERROR` -> `refresh_token`
- `API_RATE_LIMIT` -> `retry_later`
- `API_PARAM_ERROR` -> `review_api_parameters`
- `API_SERVER_ERROR` -> `check_api_status`
- `DATA_FRESHNESS_BLOCKED` -> `retry_later`

### Operations / Carryover

Updated `src/ai_fund_lab_v2/operations/market_refresh.py`.

Network/API classification remains compatible with feature-date carryover:

- network error + latest available within freshness limit -> carryover can still pass with warning/blocker evidence
- network error + freshness limit exceeded -> blocked
- blocker reason is no longer `API_PARAM_ERROR`; it can include `API_NETWORK_ERROR` and `DATA_FRESHNESS_BLOCKED`

The carryover freshness limit was not changed.

## Connectivity Diagnostic

Read-only diagnostic was executed without exposing secrets.

### Sandbox Network

Inside the restricted sandbox:

- base_url_host: `api.jquants.com`
- DNS: `FAIL`
- error_type: `gaierror`
- HTTPS: not run because DNS failed

### Approved External Network Diagnostic

With approved network execution:

- base_url_host: `api.jquants.com`
- DNS: `PASS`
- HTTPS connect: `PASS`
- address_count: 3
- TLS version: `TLSv1.2`

Interpretation:

- The local OS/network can currently resolve and connect to J-Quants.
- The sandbox cannot.
- E39's `url_error` pattern is consistent with URL reachability / execution environment / transient connectivity failure, not confirmed API parameter failure.

## Actual Market Refresh Re-run

Executed Runtime v2 market_refresh once with J-Quants read API only:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job market_refresh \
  --business-date 2026-07-09 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked \
  --market-refresh-allow-api-fetch true
```

Result:

- exit_code: 0
- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-market_refresh-2026-07-09-20260708T214255.998390+0000.json`
- status: PASS
- latest_available_market_date: `2026-07-08`
- requested_feature_date: `2026-07-09`
- selected_feature_date: `2026-07-08`
- carryover_used: true
- freshness_lag_business_days: 1
- blocked_reasons: []
- feature_refresh_executed: true
- generated feature artifacts:
  - `.runtime/operations/feature_artifacts/2026-07-08/candidate_features.parquet`
  - `.runtime/operations/feature_artifacts/2026-07-08/opportunity_feature_input.parquet`
  - `.runtime/operations/feature_artifacts/2026-07-08/position_feature_input.parquet`
  - `.runtime/operations/feature_artifacts/2026-07-08/capital_policy_input.parquet`

Market data refresh detail after re-run:

- status: `PARTIAL_AVAILABLE`
- latest_successful_daily_quotes_date: `2026-07-08`
- latest_normalized_daily_quotes_date: `2026-07-08`
- failed_dates: 0
- not_yet_available_dates:
  - `2026-07-09`
- api_error_classification: `DATA_FRESHNESS_BLOCKED`
- next_action: `retry_later`

This confirms that the prior URL failure was not reproduced under the approved network environment, and that 2026-07-08 market data is now available.

## Redaction Policy

Stored diagnostics are intentionally limited to:

- endpoint path
- date/from/to
- error class
- network error type
- HTTP status
- URL host

Explicitly not stored:

- API key
- token
- authorization header
- full URL query
- raw request
- raw response
- secret path

## Tests

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase14e41_jquants_connectivity_error_classification.py
```

Result:

- 4 passed

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase14e41_jquants_connectivity_error_classification.py \
  tests/paper_trading/test_phase9i_market_data_refresh.py \
  tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py \
  tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py
```

Result:

- 18 passed

Executed:

```text
python3 -m pytest tests/runtime_v2
```

Result:

- 345 passed

## Acceptance

- url_error is not classified as API_PARAM_ERROR: PASS
- network/connectivity errors are classified as API_NETWORK_ERROR: PASS
- API parameter errors remain API_PARAM_ERROR: PASS
- redacted diagnostics are emitted: PASS
- `next_action` is emitted: PASS
- carryover policy remains unchanged: PASS
- stale carryover still blocks: PASS
- tests/runtime_v2 PASS: PASS
- Broker Submit: NOT EXECUTED
- Production order: NOT EXECUTED
- Notification real send: NOT EXECUTED
- launchd/plist change: NOT EXECUTED

