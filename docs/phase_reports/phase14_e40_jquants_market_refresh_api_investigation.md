# Phase14-E40 J-Quants Market Refresh API Investigation

## Summary

- phase: Phase14-E40
- objective: Investigate why Runtime v2 Market Refresh stopped with `carryover_stale` and why `market_data_refresh_detail.json` shows many `JQuantsClientError` failures.
- scope: Investigation only.
- code_changed: false
- broker_write_executed: false
- submit_executed: false
- notification_sent: false
- launchd_changed: false
- final_judgement: PHASE14E40_JQUANTS_MARKET_REFRESH_API_INVESTIGATION_COMPLETE

## Finding

E39 stopped safely because Runtime v2 selected `2026-07-07` as the latest available feature date for decision date `2026-07-09`, and the carryover freshness lag became 2 business days while the allowed limit is 1.

The immediate stale-carryover cause is:

- `2026-07-08` market refresh failed.
- `2026-07-09` market refresh failed.
- Existing usable market data remained at `2026-07-07`.
- `feature_artifacts/2026-07-08` and `feature_artifacts/2026-07-09` were not generated.

The deeper API investigation result is:

- Runtime v2 is using the existing J-Quants refresh stack.
- `fetch_mode=per-date` is an intentional design inherited from Phase9-I3.
- The local evidence does not support "per-date is wrong" as the primary cause.
- The recent concrete client failure is `url_error`, not HTTP 400 / 401 / 403 / 429.
- The current manifest status `API_PARAM_ERROR` is misleading for the 2026-07-08 and 2026-07-09 runs because the client log shows URL-level failures.

## Runtime v2 Call Path

Runtime v2 Market Refresh path:

1. `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`
2. `run_runtime_v2_market_refresh_pipeline(...)`
3. dynamic import of `ai_fund_lab_v2.operations.market_refresh`
4. `run_operations_market_refresh(...)`
5. `run_market_data_refresh(...)`
6. `JQuantsAPIFetcher`
7. `JQuantsClient`
8. J-Quants endpoints:
   - `/v2/equities/bars/daily`
   - `/v2/equities/master`
   - `/v2/markets/calendar`

`run_operations_market_refresh(...)` currently calls:

- `from_date = trade_date - 140 calendar days` when not explicitly provided.
- `fetch_mode = "per-date"` by default.
- raw output root: `.runtime/operations/jquants/raw`
- normalized output root: `.runtime/operations/jquants/raw_normalized`
- detail root: `.runtime/operations/jquants/market_data_refresh_detail`

## Is fetch_mode=per-date Correct?

Yes, based on the existing Phase9 evidence.

Phase9-I3 explicitly diagnosed that:

- daily_quotes range fetch with `from` / `to` returned HTTP 400.
- daily_quotes single-date fetch with `date=YYYY-MM-DD` succeeded.
- recommended fetch mode became `per-date`.

Runtime v2 is therefore following the known-good Phase9 decision for daily quotes.

Additional current evidence:

- `2026-07-06` Runtime v2 market refresh succeeded with `fetch_mode=per-date`.
- `2026-07-07` Runtime v2 market refresh succeeded with `fetch_mode=per-date`.
- `2026-07-07` fetched:
  - daily_quotes: 422,336 rows
  - listed_info: 4,437 rows
  - trading_calendar: 141 rows

Therefore, `fetch_mode=per-date` itself is not the confirmed root cause.

## E39 / E35 Artifact Evidence

### 2026-07-07

- status: `MARKET_DATA_READY_FOR_LATEST_AVAILABLE`
- fetch_mode: `per-date`
- from_date: `2026-02-17`
- to_date: `2026-07-07`
- latest_successful_daily_quotes_date: `2026-07-07`
- latest_normalized_daily_quotes_date: `2026-07-07`
- failed_dates: 0
- blocked_reasons: []

### 2026-07-08

- status: `API_PARAM_ERROR`
- fetch_mode: `per-date`
- from_date: `2026-02-18`
- to_date: `2026-07-08`
- latest_successful_daily_quotes_date: empty
- latest_normalized_daily_quotes_date: `2026-07-07`
- failed_dates: 100
- first failed_dates:
  - `2026-02-18:JQuantsClientError`
  - `2026-02-19:JQuantsClientError`
- last failed_dates:
  - `2026-07-06:JQuantsClientError`
  - `2026-07-07:JQuantsClientError`
- not_yet_available_dates:
  - `2026-07-08`
- blocked_reasons:
  - `api_fetch_failed:JQuantsClientError`
  - `data_until_before_decision_for`

### 2026-07-09

- status: `API_PARAM_ERROR`
- fetch_mode: `per-date`
- from_date: `2026-02-19`
- to_date: `2026-07-09`
- latest_successful_daily_quotes_date: empty
- latest_normalized_daily_quotes_date: `2026-07-07`
- failed_dates: 100
- first failed_dates:
  - `2026-02-19:JQuantsClientError`
  - `2026-02-20:JQuantsClientError`
- last failed_dates:
  - `2026-07-07:JQuantsClientError`
  - `2026-07-08:JQuantsClientError`
- not_yet_available_dates:
  - `2026-07-09`
- blocked_reasons:
  - `api_fetch_failed:JQuantsClientError`
  - `data_until_before_decision_for`

## J-Quants Client Log Evidence

The manifest only records `JQuantsClientError`, but `.runtime/logs/jquants_client.log` records the client-level status.

Observed status counts:

- `url_error`: 1,113
- `400`: 121

Recent E39-related logs on `2026-07-09` show:

- `/v2/equities/bars/daily status=url_error error_type=url_error`
- repeated pagination failures with `pages_fetched=0`
- target dates from `2026-02-19` through `2026-07-09`
- `/v2/equities/master status=url_error error_type=url_error`

Recent E35/E39-related logs on `2026-07-08` show the same URL-level failure pattern.

This points to URL-level connectivity or transport failure during the recent runs, not a confirmed API parameter rejection, authentication rejection, permission rejection, or rate limit rejection.

## Why 2026-02-18 onward all failed

This is a consequence of the current per-date refresh window, not evidence that all historical dates are unavailable.

For a target trade date, `run_operations_market_refresh(...)` defaults `from_date` to `trade_date - 140 calendar days`.

Therefore:

- 2026-07-08 run attempted dates from 2026-02-18 to 2026-07-08.
- 2026-07-09 run attempted dates from 2026-02-19 to 2026-07-09.

When the J-Quants client could not reach the endpoint, every attempted per-date request failed with `JQuantsClientError`. This produced a full list of failed dates even though the existing local parquet already contained data through `2026-07-07`.

## Phase9 / Phase10 Difference

Phase9 did not use a different J-Quants API strategy for daily quotes after Phase9-I3. It also used per-date daily quote fetching.

Key difference:

- Phase9-I3 fixed daily_quotes to `date=YYYY-MM-DD` per-date fetch after range fetch produced HTTP 400.
- Runtime v2 uses the same core `paper_trading.market_data_refresh` and `data_sources.jquants.client` modules.
- Current Runtime v2 output path differs:
  - Phase9: `.runtime/data/...`
  - Runtime v2 operations: `.runtime/operations/jquants/...`
- Runtime v2 adds feature-date / carryover policy around the refresh result.

Therefore, the evidence indicates the recent failure is not because Runtime v2 bypassed the existing J-Quants modules. Runtime v2 is using them.

## API Spec Change vs Runtime Implementation Issue

Evidence does not currently prove a J-Quants API spec change.

Observed facts:

- Per-date fetch worked locally on 2026-07-06 and 2026-07-07.
- Phase9-I3 documents per-date as the correct daily_quotes mode.
- Recent failure status is `url_error`.
- `url_error` is raised from `urllib.error.URLError` in `JQuantsClient.get(...)`.

Most likely classification:

- primary: runtime environment / network / URL reachability issue during 2026-07-08 and 2026-07-09 runs
- secondary: manifest classification gap, because URL-level failures are collapsed into `JQuantsClientError` and then labeled `API_PARAM_ERROR`
- not confirmed: J-Quants API parameter change
- not confirmed: authentication error
- not confirmed: rate limit

## Concrete Error Cause Classification

| Candidate | Evidence | Classification |
| --- | --- | --- |
| Authentication / credential | No recent `401` / `403` in client log; recent failures are `url_error`. | Not supported by current evidence |
| Date parameter issue | `per-date` succeeded on 2026-07-06 and 2026-07-07; Phase9-I3 established `date=YYYY-MM-DD`. | Not primary |
| Range parameter issue | Historical Phase9-I3 issue, but current fetch mode is not range. | Not current cause |
| Rate limit | No recent `429`; retry policy would classify separately. | Not supported |
| J-Quants data not yet published | Explains current-day `not_yet_available`, but not 100 previous business dates. | Partial only |
| Network / DNS / URL reachability | Recent client log shows repeated `status=url_error`. | Strongly supported |
| Runtime not using existing module | Runtime v2 calls `operations.market_refresh` -> `paper_trading.market_data_refresh` -> `JQuantsClient`. | False |
| Manifest classification issue | `url_error` becomes `JQuantsClientError`; per-date failed all dates; status becomes `API_PARAM_ERROR`. | Confirmed gap |

## Impact

E39 correctly stopped rather than using stale data beyond the freshness contract.

Operationally:

- No feature artifacts were generated for `2026-07-08` or `2026-07-09`.
- `2026-07-09` Morning cannot proceed safely with fresh-enough features.
- Existing `2026-07-07` artifacts remain usable only within the carryover limit.
- Since freshness lag is now 2 business days, the current behavior should remain `REVIEW_REQUIRED` / `BLOCKED`.

## Recommendations

No code change was made in this phase, but the next fix/design phase should consider:

1. Improve manifest classification:
   - distinguish `url_error`, `timeout`, `http_400`, `auth_error`, `rate_limit`
   - avoid labeling URL failures as `API_PARAM_ERROR`

2. Add a diagnostics-only J-Quants preflight:
   - no data mutation
   - single lightweight endpoint call
   - redacted status output
   - clear classification: connectivity / auth / parameter / rate-limit

3. Reduce per-date failure noise:
   - if the first few historical per-date calls fail with the same URL-level error, fail fast
   - preserve evidence without attempting 100 dates unnecessarily

4. Preserve per-date daily quotes unless new evidence proves it invalid:
   - Phase9-I3 and 2026-07-07 local success both support per-date daily quote fetch.

5. Keep E36 carryover behavior:
   - stale carryover must not silently become `NO_SIGNAL`.
   - stale market data should remain `REVIEW_REQUIRED` / `BLOCKED`.

## Acceptance Check

- Runtime v2 Market Refresh call path investigated: PASS
- `fetch_mode=per-date` reviewed against Phase9 evidence: PASS
- 2026-02-18/19 onward failures explained as refresh window plus URL-level failure: PASS
- Phase9/Phase10 difference reviewed: PASS
- Existing J-Quants modules usage confirmed: PASS
- API spec change vs Runtime issue classified: PASS
- Concrete error class identified from client log: PASS
- Runtime code changed: NO
- Production order: NO
- Notification sent: NO
- launchd changed: NO

