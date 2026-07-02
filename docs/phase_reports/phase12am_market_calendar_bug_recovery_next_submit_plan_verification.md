# Phase12-AM Market Calendar Bug Recovery / Next Morning Submit Plan Verification

## Status

```text
PHASE12AM_MARKET_CALENDAR_BUG_RECOVERY_NEXT_SUBMIT_PLAN_VERIFICATION_COMPLETE
```

## Objective

Verify that the `2026-07-02` morning Demo Submit uses the regenerated `2026-07-01` Order Plan / Approval, not the stale `2026-06-30` Order Plan.

No demo order, production order, notification send, AI retraining, or backtest was executed.

## Finding Before Fix

`tools/launchd/com.aifundlab.operations.demo_submit.plist` does not pass `--trade-date`.

Therefore, launchd on `2026-07-02` starts:

```text
python3 scripts/run_demo_submit.py --root .runtime/operations --execute-demo-order --second-password-present
```

The CLI default date is `date.today()`. Before this recovery fix, `run_demo_submit()` loaded:

```text
.runtime/operations/order_plan/<trade_date>/order_plan.json
.runtime/operations/approval_artifact/<trade_date>/approval_artifact.json
```

So a `2026-07-02` morning run would try to read `2026-07-02` plan/approval. It did not explicitly select the previous business day's `2026-07-01` plan.

## Recovery Fix

Updated:

```text
src/ai_fund_lab_v2/operations/operations.py
```

`run_demo_submit()` now separates:

```text
submit_run_date = trade_date
order_plan_source_date = trade_date if same-day plan+approval exists else previous_business_day
approval_source_date = order_plan_source_date
```

For `2026-07-02` morning, because no same-day `2026-07-02` Order Plan exists and `previous_business_day=2026-07-01`, submit uses:

```text
.runtime/operations/order_plan/2026-07-01/order_plan.json
.runtime/operations/approval_artifact/2026-07-01/approval_artifact.json
```

The submitted artifact records:

```text
submit_run_date=2026-07-02
order_plan_source_date=2026-07-01
approval_source_date=2026-07-01
uses_previous_business_day_order_plan=true
```

## Regenerated Artifacts

Regenerated / verified:

```text
python3 scripts/run_daily_plan.py --trade-date 2026-07-01 --root .runtime/operations
python3 scripts/run_approval_prepare.py --trade-date 2026-07-01 --root .runtime/operations --auto-demo-approval --approver-label phase12am_next_morning_submit_verification
python3 scripts/run_demo_submit.py --trade-date 2026-07-02 --root .runtime/operations
```

Results:

```text
2026-07-01 order_plan.status=PASS
2026-07-01 buy_item_count=5
2026-07-01 approval_artifact.status=APPROVED
2026-07-02 dry_run_submit.status=PASS
demo_order_submitted=false
broker_order_api_called=false
clm_kabu_new_order_called=false
production_order_submitted=false
```

## Approval Validity

```text
approval_id=operation_approval_2026-07-01_d28a4d34e9c4
approval_expires_at=2026-07-02T04:38:45.563582+00:00
```

This is `2026-07-02 13:38:45 JST`, so it covers the planned `2026-07-02 08:50 JST` demo submit window.

## BUY Candidates

| internal code | broker issue code | name | market | quantity | limit_price | expected_notional |
|---|---|---|---|---:|---:|---:|
| 42650 | 4265 | Ｉｎｓｔｉｔｕｔｉｏｎ　ｆｏｒ　ａ　Ｇｌｏｂａｌ　Ｓｏｃｉｅｔｙ | グロース | 100 | 0 | 0 |
| 41790 | 4179 | ジーネクスト | グロース | 100 | 0 | 0 |
| 29620 | 2962 | テクニスコ | スタンダード | 100 | 0 | 0 |
| 23930 | 2393 | 日本ケアサプライ | スタンダード | 100 | 0 | 0 |
| 61660 | 6166 | 中村超硬 | グロース | 100 | 0 | 0 |

`limit_price=0` and `expected_notional=0` are not sent in dry-run. Wire execution remains disabled in this phase. The execute path still performs positive price/notional normalization before a broker request.

## Launchd Verification

`tools/launchd/com.aifundlab.operations.demo_submit.plist`:

```text
--root .runtime/operations
--execute-demo-order
--second-password-present
```

No `--trade-date` is specified. On `2026-07-02`, the CLI default run date is `2026-07-02`; `run_demo_submit()` then resolves the source plan to `2026-07-01` using the previous business day rule.

## 2026-06-30 Non-Use

The dry-run artifact confirms:

```text
order_plan_source_date=2026-07-01
approval_source_date=2026-07-01
```

No submitted item came from the `2026-06-30` Order Plan.

## Tests

```text
python3 -m pytest tests/phase12/test_phase12_demo_submit_guard.py -q
7 passed

python3 -m pytest tests/phase12 -q
78 passed

py_compile
PASS
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
launchctl_changed=false
```

