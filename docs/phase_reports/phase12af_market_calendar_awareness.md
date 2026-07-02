# Phase12-AF Market Calendar Awareness

## Status

```text
PHASE12AF_MARKET_CALENDAR_AWARENESS_COMPLETE
```

Phase12-AF added Market Calendar Awareness and Market Closed Safe Skip to Operations Runtime.

Codex did not execute launchctl bootstrap / bootout, Demo order, Production order, Production unlock, LINE actual send, AI retraining, backtest, raw request save, raw response save, secret save, or Phase9 artifact / launchd / CLI changes.

## MarketCalendar

Added:

```text
src/ai_fund_lab_v2/operations/market_calendar.py
```

API:

```text
resolve_operation_date(date, root)
is_business_day(date, root)
previous_business_day(date)
next_business_day(date)
market_closed_reason(date)
```

Artifact shape:

```json
{
  "trade_date": "YYYY-MM-DD",
  "is_business_day": true,
  "market_closed": false,
  "market_closed_reason": "",
  "calendar_source": "jquants_trading_calendar or fallback",
  "latest_available_market_date": "YYYY-MM-DD",
  "previous_business_day": "YYYY-MM-DD",
  "next_business_day": "YYYY-MM-DD"
}
```

## calendar_source

Priority:

```text
1. J-Quants trading_calendar under .runtime/operations
2. fallback Japanese market holiday calendar
```

If J-Quants calendar exists but lacks adjacent future dates, current-day judgement still uses J-Quants while previous / next business day falls back safely.

## Business Day Behavior

On market open days, the existing Operations flow remains unchanged:

```text
market_refresh
daily_plan
approval_prepare
preflight
demo_submit
fill_monitor
safety_monitor
reconcile
operation_audit
daily_report
```

Artifacts include `market_calendar.market_closed=false`.

## Market Closed Behavior

On market closed days:

```text
run_market_refresh.py -> SKIPPED_MARKET_CLOSED
run_daily_plan.py -> SKIPPED_MARKET_CLOSED, buy_item_count=0, sell_item_count=0
run_approval_prepare.py -> SKIPPED_MARKET_CLOSED, demo_order_allowed=false, no approval artifact
run_demo_submit.py -> SKIPPED_MARKET_CLOSED, demo_order_executed=false, clm_kabu_new_order_called=false
run_demo_special_fill_simulation.py -> SKIPPED_MARKET_CLOSED, simulated_fill=false
run_preflight.py -> PASS_MARKET_CLOSED_READONLY_ONLY, submit_allowed=false
run_fill_monitor.py -> PASS_MARKET_CLOSED_MONITOR_ONLY
run_safety_monitor.py -> PASS_MARKET_CLOSED_SYSTEM_ONLY
run_reconcile.py -> PASS_MARKET_CLOSED_RECONCILE_ONLY
run_daily_report.py -> PASS with Market Status: CLOSED
run_operation_audit.py -> PASS_MARKET_CLOSED if no order trace exists
```

Order-related artifacts include:

```json
{
  "submit_allowed": false,
  "demo_order_executed": false,
  "clm_kabu_new_order_called": false,
  "skip_reason": "MARKET_CLOSED"
}
```

## Daily Report / Blog

Daily Report and generated markdown include:

```text
Market Status: CLOSED
Reason: ...
AI Decision: skipped
Orders: skipped
市場休場日のため、AI判断・発注・約定処理はありません。Broker read-only / Safety / Ledger確認のみ実施しました。
```

LINE payload generation remains file-only; LINE actual send remains disabled.

## Operation Audit

Operation Audit now records:

```json
{
  "market_closed_safe_skip": true,
  "orders_blocked_on_market_closed": true,
  "demo_special_fill_blocked_on_market_closed": true
}
```

If a market-closed artifact contains `demo_order_executed=true`, `broker_order_api_called=true`, `clm_kabu_new_order_called=true`, or `demo_special_fill_simulation_used=true`, audit status becomes `BLOCK`.

## Runbook

Updated:

```text
docs/operations/demo_daily_operation_runbook.md
```

The runbook now documents Market Closed Safe Skip and the per-CLI closed-day statuses.

## Tests

Executed:

```bash
python3 -m pytest tests/phase12/test_market_calendar.py tests/phase12/test_market_closed_safe_skip.py tests/phase12/test_market_closed_daily_report.py -q
python3 -m pytest tests/phase12 -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/operations/market_calendar.py src/ai_fund_lab_v2/operations/operations.py
```

Results:

```text
targeted pytest: 8 passed
phase12 pytest: 63 passed
py_compile: PASS
```

## Remaining Gaps

```text
fallback calendar is intentionally limited and should be refreshed from J-Quants for long-term operation
market holiday source should be periodically audited against J-Quants trading_calendar
first real launchd market-closed day not yet observed
```

