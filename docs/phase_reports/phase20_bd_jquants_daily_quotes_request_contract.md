# Phase20-BD J-Quants Daily Quotes Request Contract Correction

## Final Status

```text
PHASE20_BD_JQUANTS_DAILY_QUOTES_REQUEST_CONTRACT_CORRECTED
```

No five-year J-Quants acquisition, Historical Run, Training, Calibration, Broker connection, Demo order, or Production order was executed by Codex. Runtime common OHLCV was not mutated.

## Observed Failure

Two Phase20-BC acquisition runs failed on the first request with HTTP 400:

| Run | First Request Window | Status | Legacy request_count | Legacy page_count |
| --- | --- | --- | ---: | ---: |
| jquants-acquisition-20210420-20260714 | 2021-04-20 to 2021-04-30 | HTTP 400 | 0 | 0 |
| jquants-acquisition-20210701-20210702 | 2021-07-01 to 2021-07-02 | HTTP 400 | 0 | 0 |

The second run showed that the issue was not limited to 2021-04 data availability.

## Request Shape Finding

Phase20-BC acquisition used the monthly chunk directly as a daily quotes range request:

```text
GET /v2/equities/bars/daily?from=<chunk.start_date>&to=<chunk.end_date>
```

Existing Runtime daily refresh uses the successful per-date path:

```text
JQuantsAPIFetcher.fetch_daily_quotes_for_date(target_date)
-> JQuantsClient.fetch_all_daily_quotes(date=target_date)
-> GET /v2/equities/bars/daily?date=YYYY-MM-DD
```

## Correction

The acquisition request contract is now:

```text
phase20_bd_jquants_daily_quotes_request.v1
```

Contract:

```text
GET /v2/equities/bars/daily?date=YYYY-MM-DD
pagination_key=<only when present>
```

Monthly/weekly/day chunks remain planning and resume units, but each chunk now expands into date-level request states. `from` and `to` are prohibited for this daily quotes acquisition path.

## State and Resume

Each chunk now stores per-date request state:

```text
request_date
status
request_count
page_count
row_count
content_hash
error
retry_count
http_status
```

Resume skips completed date requests and continues remaining dates. Old Phase20-BC failed runs do not have `request_contract_version`, so they are blocked as:

```text
ACQUISITION_LEGACY_RUN_INCOMPATIBLE_WITH_UPDATED_REQUEST_CONTRACT
```

A new run_id is required.

## HTTP 400 Detail

J-Quants HTTPError diagnostics now preserve secret-safe response detail:

```text
http_status
response_content_type
response_body
request_parameter_names
```

API keys, authorization headers, and secret-bearing environment values are not persisted.

## Request Count Semantics

HTTP 400 is non-retryable, but it is still one sent request:

```text
HTTP 400 -> request_count=1, page_count=0, retry_count=0
```

Retryable classes remain bounded:

```text
API_RATE_LIMIT
API_SERVER_ERROR
API_NETWORK_ERROR
```

Non-retryable:

```text
API_AUTH_ERROR
API_PARAM_ERROR
```

## Evidence

Evidence root:

```text
reports/phase20_bd_jquants_daily_quotes_request_contract/
```

Machine-readable report:

```text
reports/phase_reports/phase20_bd_jquants_daily_quotes_request_contract.json
```

## Validation

Executed:

```text
py_compile PASS
targeted pytest PASS: 13 passed
```

Additional checks:

```text
CLI help PASS
JSON validation PASS
git diff --check PASS
```

## User Validation Commands

Single business day probe:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition run \
  --start-date 2026-07-01 \
  --end-date 2026-07-01 \
  --run-id jquants-acquisition-20260701-bd-probe \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```

Expected:

```text
ACQUISITION_SOURCE_READY
row_count > 0
request_count >= 1
runtime_market_data_mutated = false
```

Only after the single-day probe succeeds:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition plan \
  --start-date 2021-07-01 \
  --end-date 2026-07-14 \
  --run-id jquants-acquisition-20210701-20260714-bd \
  --write-evidence \
  --json
```

```bash
PYTHONPATH=src python3 scripts/runtime_test.py market-data-acquisition run \
  --start-date 2021-07-01 \
  --end-date 2026-07-14 \
  --run-id jquants-acquisition-20210701-20260714-bd \
  --confirm \
  --yes-i-understand-this-fetches-large-market-data \
  --write-evidence \
  --json
```
