# Phase4-AV Long History Fetch Plan for Formal Candidate Training

## Purpose

Phase4-AV creates a no-live long history fetch plan for formal Candidate AI training. It does not call APIs, fetch data, rebuild normalized data, generate features or labels, rebuild datasets, train, infer, backtest, trade, promote, or switch readers.

## Plan Summary

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_FETCH_DRY_RUN`
- current history: `2026-03-02` to `2026-05-29` (`60` business days)
- required training range: `2021-06-01` to `2026-05-15`
- preferred fetch range: `2021-03-09` to `2026-06-12`
- lookback_business_days: `60`
- label_horizon_business_days: `20`
- estimated_fetch_business_day_count: `1374`
- estimated_request_count: `1374`
- storage_estimate_mb: `3254.77`

## Split Plan

- Train: `2021-06-01` to `2024-12-31`
- Validation: `2025-01-01` to `2025-12-31`
- Test: `2026-01-01` to `2026-05-15`

## Endpoint And Storage

- endpoint: `/v2/equities/bars/daily`
- raw_output_path: `.runtime/data/raw/jquants/equities_bars_daily`
- normalized_output_path: `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily`

## Policies

- rate_limit_policy: Use configured J-Quants Light plan limit of 60 req/min; schedule at most one daily quote request per trading date and retain retry/backoff on 429 without logging secrets.
- resume_policy: Generate one request manifest per target_date, skip succeeded manifests, rerun failed/missing manifests, keep partial responses isolated, and never overwrite mock normalized paths.
- manifest_policy: Store request, response, normalization, feature, label, dataset, and training manifests under .runtime and reports with source_snapshot_id links.

## Re-execution Plan After Long History Fetch

- Phase4-AW Long History Fetch Dry-run: generate request sequence without API calls.
- Controlled raw fetch after dry-run approval: fetch daily quotes only into .runtime/data/raw/jquants/equities_bars_daily.
- Rebuild isolated real_runtime normalized history; do not promote and do not switch readers.
- Rebuild historical Candidate features with 60d lookback quality gate.
- Regenerate labels using a 20d future horizon and keep labels physically separated from features.
- Rebuild dataset with time-series split and exclude target_dates without full lookback/horizon coverage.
- Run formal Candidate training only after leakage, schema, and coverage audits pass.

## Scope Guard

- api_call_performed: `False`
- fetch_executed: `False`
- normalized_rebuild_executed: `False`
- feature_generation_executed: `False`
- label_generation_executed: `False`
- dataset_rebuild_executed: `False`
- training_executed: `False`
- inference_executed: `False`
- backtest_executed: `False`
- trading_executed: `False`

## Recommended Next Action

Phase4-AW Long History Fetch Dry-run: generate the request sequence without calling J-Quants API.

