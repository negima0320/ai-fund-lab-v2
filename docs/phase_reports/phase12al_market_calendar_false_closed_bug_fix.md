# Phase12-AL Market Calendar False Closed Bug Fix

## Status

```text
PHASE12AL_MARKET_CALENDAR_FALSE_CLOSED_BUG_FIX_COMPLETE
```

## Issue

`2026-07-01` is a normal Wednesday business day, but Operations Runtime treated it as:

```text
market_closed=true
SKIPPED_MARKET_CLOSED
```

This caused Daily Plan, Approval, Demo Submit, Fill Monitor, Safety Monitor, and Daily Report to follow the market-closed path.

## Root Cause

The J-Quants trading calendar artifact existed, so Operations used:

```text
calendar_source=jquants_trading_calendar
```

However, the local calendar artifact did not contain `2026-07-01`. The previous logic treated a missing date inside an otherwise loaded J-Quants calendar as non-business day:

```text
calendar record missing -> business_day=false
market_closed_reason=TRADING_CALENDAR_DATE_MISSING
```

That was too strict for a partial or stale local trading calendar.

## Fix

Updated:

```text
src/ai_fund_lab_v2/operations/market_calendar.py
```

New behavior:

```text
J-Quants calendar record exists
  -> use J-Quants HolDiv

J-Quants calendar is loaded but target date is missing
  -> fallback to weekday / JP market holiday table
  -> calendar_source=jquants_trading_calendar_partial_fallback

No J-Quants calendar loaded
  -> fallback
```

The fix prevents a partial J-Quants calendar from falsely closing normal weekdays.

## Calendar Verification

Using `.runtime/operations`:

| Date | Expected | Result | Source |
|---|---:|---:|---|
| 2026-06-30 | business day | `market_closed=false` | `jquants_trading_calendar` |
| 2026-07-01 | business day | `market_closed=false` | `jquants_trading_calendar_partial_fallback` |
| 2026-07-02 | business day | `market_closed=false` | `jquants_trading_calendar_partial_fallback` |
| 2026-07-04 | weekend | `market_closed=true` | `jquants_trading_calendar_partial_fallback` |
| 2026-07-05 | weekend | `market_closed=true` | `jquants_trading_calendar_partial_fallback` |

## 2026-07-01 Regeneration

Regenerated without deleting existing artifacts:

```text
python3 scripts/run_market_refresh.py --trade-date 2026-07-01 --root .runtime/operations
python3 scripts/run_daily_plan.py --trade-date 2026-07-01 --root .runtime/operations
python3 scripts/run_approval_prepare.py --trade-date 2026-07-01 --root .runtime/operations --auto-demo-approval --approver-label phase12al_calendar_fix
python3 scripts/run_demo_submit.py --trade-date 2026-07-01 --root .runtime/operations
python3 scripts/run_fill_monitor.py --trade-date 2026-07-01 --root .runtime/operations
python3 scripts/run_safety_monitor.py --trade-date 2026-07-01 --root .runtime/operations
python3 scripts/run_reconcile.py --trade-date 2026-07-01 --root .runtime/operations
python3 scripts/run_operation_audit.py --root .runtime/operations
python3 scripts/run_daily_report.py --trade-date 2026-07-01 --root .runtime/operations
```

Results:

```text
market_refresh=PASS
daily_plan=PASS
approval=APPROVED
demo_submit=PASS
fill_monitor=PASS
safety_monitor=PASS
reconcile=REVIEW_REQUIRED
operation_audit=PASS
daily_report_generated=true
market_status=OPEN
```

`run_demo_submit.py` was executed without `--execute-demo-order`, so no demo order was sent.

## Notes

Daily Report final command returned `BLOCK` because `demo_special_fill_simulation` was regenerated as a no-op `BLOCK` when simulation was not enabled and no 9000-series waiting buy order existed. This is not a market calendar false-closed condition. The Daily Report content now shows:

```text
Market Calendar: OPEN / next business day 2026-07-02
```

## Safety

```text
demo_order_executed=false
production_order_executed=false
line_send_executed=false
discord_send_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
phase9_changed=false
launchd_changed=false
```

## Tests

```text
python3 -m pytest tests/phase12/test_market_calendar.py -q
5 passed

python3 -m pytest tests/phase12/test_market_calendar.py tests/phase12/test_market_closed_safe_skip.py -q
9 passed

python3 -m pytest tests/phase12 -q
77 passed

py_compile
PASS
```

