# Phase9-W Unified Runner Market Refresh and Date Resolution

- status: PASS

## Root Cause

- date_semantics: Unified Runner used latest_available_quote_date as decision_for/data_target_date, so a 2026-06-18 run could execute as 2026-06-17 when canonical quotes were stale.
- market_refresh: --allow-api-fetch previously only blocked with MARKET_DATA_REFRESH_NOT_CONNECTED_BLOCKED and did not execute market refresh inside Unified Runner.
- stale_handling: stale_price_source could still progress into normal tracker/blog flow.

## Actual Environment

```json
{
  "resolved_jst_today": "2026-06-18",
  "raw_response_file_count": 1305,
  "raw_response_2026_06_18_file_count": 0,
  "raw_table": {
    "exists": true,
    "min_date": "2026-06-01",
    "max_date": "2026-06-24",
    "target_row_count": 4445,
    "row_count": 80049,
    "holding_close_count": 0
  },
  "canonical_normalized": {
    "exists": true,
    "min_date": "2021-06-14",
    "max_date": "2026-06-24",
    "target_row_count": 4215,
    "row_count": 5100126,
    "holding_close_count": 5
  },
  "valuation_quotes_path_expected": ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet"
}
```

## Checks

- PASS: date_without_arg_resolves_to_jst_today 2026-06-18
- PASS: allow_api_fetch_calls_market_refresh 1
- PASS: canonical_normalized_updates_to_target 2026-06-18
- PASS: stale_valuation_blocks_runner UNIFIED_DAILY_RUNNER_BLOCKED
- PASS: stale_tracker_not_updated SKIPPED_BLOCKED
- PASS: stale_blog_is_marked BLOG_REPORT_V2_STALE_PRICE_SOURCE
- PASS: scheduler_not_changed
- PASS: broker_order_not_called
- PASS: ledger_manual_mutation_not_done

## Forbidden Actions

- Broker order / OpenD / unlock_trade / real trade / scheduler change / manual ledger mutation were not executed.
