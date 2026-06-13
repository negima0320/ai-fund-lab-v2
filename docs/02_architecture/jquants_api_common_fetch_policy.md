# J-Quants API Common Fetch Policy

## Purpose

This document defines the shared J-Quants API fetch policy used by data foundation and Phase4 real-runtime fetch scripts.

The goal is to avoid per-script ad hoc behavior for rate limit, retry, date range handling, pagination, and secret safety.

## Scope

This policy applies to J-Quants read-only market data fetches.

It does not implement:

- normalized rebuild
- feature generation
- label generation
- dataset build
- training
- inference
- backtest
- trading
- broker API
- ordering

## Rate Limit Policy

J-Quants Light plan is treated as a maximum of 60 requests per minute.

The shared policy is:

- Do not sleep a fixed 1 second before every request.
- Track requests in a rolling 60-second window.
- If fewer than 60 requests are active in the window, proceed immediately.
- If the next request would exceed 60 requests/min, wait until the oldest request exits the window.
- Record the policy in summaries and manifests as `rate_limit_policy`.

This allows safe bursts below the 60/min cap while still respecting the plan limit.

## Retry Policy

The shared retry policy classifies failures as follows:

| Status | Category | Retry |
| --- | --- | --- |
| 429 | rate limit / retryable | yes, wait 60 seconds |
| 500-599 | server error / retryable | yes, bounded retry |
| timeout | transient / retryable | yes, bounded retry |
| url_error | transient / retryable | yes, bounded retry |
| 400 | bad request or out-of-range | no |
| 401/403 | credential/auth error | no |

HTTP 400 must not be retried indefinitely. It usually means request format, unavailable date range, or endpoint constraints must be inspected before resume.

HTTP 401/403 must be treated as credential or auth failure.

All retry errors must be sanitized before logs, summary, manifest, or report output.

## Endpoint Capability

Each endpoint exposes capability metadata:

| Endpoint | date | from/to | code | pagination | preferred strategy |
| --- | --- | --- | --- | --- | --- |
| `/v2/equities/bars/daily` | yes | yes | yes | yes | range fetch when supported |
| `/v2/equities/master` | yes | no | yes | yes | date-by-date |
| `/v2/markets/calendar` | yes | yes | no | yes | range fetch |
| `/v2/fins/summary` | yes | no | yes | yes | date-by-date |

Scripts should read endpoint capability rather than hard-code parameter assumptions.

## Date / Range Strategy

When an endpoint supports `from` / `to` and range fetch is preferred, request builders should use range fetch before date-by-date fallback.

When an endpoint does not support range fetch, request builders should use date-by-date fetch.

Pagination must be handled with the common `pagination_key` convention for all endpoints that expose it.

## Manifest Fields

Fetch summaries and run manifests should be able to include:

- `rate_limit_policy`
- `retry_policy`
- `endpoint_capability`

These fields must contain policy metadata only. They must not include API keys, tokens, authorization headers, request URLs containing credentials, or secret values.

## Secret Safety

The shared policy never requires secret values for manifest generation.

Allowed:

- `secret_present: true/false`
- short non-reversible secret fingerprint if already used by a phase

Forbidden:

- `JQUANTS_API_KEY`
- `x-api-key` value
- `Authorization` value
- refresh token
- id token
- password
- cookie

## Current Integration

The common policy is implemented in:

- `src/ai_fund_lab_v2/data/jquants_fetch_policy.py`

`JQuantsClient` uses it for:

- rolling-window rate limit
- retry classification
- endpoint parameter construction
- manifest-ready policy metadata

Phase4 fetch scripts can record the same policy metadata in their summaries and manifests.
