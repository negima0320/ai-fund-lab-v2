# Phase4-AW Long History Fetch Dry-run

## Purpose

Phase4-AW generates a dry-run request sequence for long history daily quotes fetch. It does not read credentials, initialize an HTTP client, call J-Quants, fetch raw data, rebuild normalized data, generate features or labels, rebuild datasets, train, infer, backtest, trade, promote, or switch readers.

## Summary

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_CONTROLLED_FETCH`
- target fetch range: `2021-03-09` to `2026-06-12`
- business_day_count: `1374`
- request_count: `1374`
- estimated_request_count: `1374`
- request_count_match: `True`
- calendar_source: `calendar_placeholder_weekday`
- storage_estimate_mb: `3254.77`
- requests_artifact_path: `reports/candidate_ai/full_range/phase4aw_long_history_fetch_dry_run_requests.json`

## Request Template

- endpoint: `/v2/equities/bars/daily`
- method: `GET`
- params.date: target business date
- params.code: None
- params.pagination_key: None

## Policies

- rate_limit_policy: Use configured J-Quants Light plan limit of 60 req/min; schedule at most one daily quote request per trading date and retain retry/backoff on 429 without logging secrets.
- resume_policy: Generate one request manifest per target_date, skip succeeded manifests, rerun failed/missing manifests, keep partial responses isolated, and never overwrite mock normalized paths.
- manifest_policy: Store request, response, normalization, feature, label, dataset, and training manifests under .runtime and reports with source_snapshot_id links.

## Scope Guard

- api_call_performed: `False`
- credential_read_performed: `False`
- http_client_initialized: `False`
- fetch_executed: `False`
- raw_data_modified: `False`
- normalized_data_modified: `False`
- mock_path_unchanged: `True`
- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`

## Recommended Next Action

Phase4-AX Long History Controlled Fetch: execute the approved request sequence with J-Quants credentials.
