# Phase10-L5 Tachibana p_no Monotonic Sequence Fix

- status: PASS
- created_at: 2026-06-27
- scope: p_no sequence fix and account/balance read-only recheck
- live_account_balance_run_count: 1
- environment: demo

## 1. Summary

Phase10-L5 fixed the `p_no` monotonic sequence bug identified in Phase10-L4.

Result:

```text
p_no_sequence_fix_applied=true
account_balance_live_smoke=PASS
login=PASS
logout=PASS
protocol_error_present=false
business_fields_present=true
orders_api_called=false
executions_api_called=false
quotes_api_called=false
paper_ledger_updated=false
paper_test2_ledger_initialized=false
```

The previous error:

```text
p_errno=6
p_err=引数（p_no:[1] <= 前要求.p_no:[1]）エラー。
```

is resolved for account/balance read-only smoke.

## 2. Fix

Updated `src/ai_fund_lab_v2/broker/client.py`:

- `TachibanaReadOnlyClient` now initializes and retains one `TachibanaRequestBuilder`.
- The `request_builder` property no longer creates a fresh builder per access.
- Consecutive requests on the same client now consume increasing `p_no` values.

Updated read-only runner clients that switch transport after login:

- `tachibana_account_smoke.py`
- `tachibana_positions_smoke.py`
- `tachibana_orders_smoke.py`
- `tachibana_executions_history_smoke.py`
- `tachibana_quote_smoke.py`
- `tachibana_broker_snapshot.py`

These now pass the same builder into REQUEST/PRICE clients so the session sequence is shared across login, read-only calls, and logout.

## 3. Mock Test Coverage

Added/updated tests for:

```text
same client consecutive requests produce p_no=1,2,3
login -> account -> balance -> logout produces p_no=1,2,3,4
injected builder is respected across transport clients
separate clients may start independent sequences
default account/balance smoke remains skipped
```

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_client_mock.py tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py -q
```

Result:

```text
106 passed
```

## 4. Live Account / Balance Recheck

Default skip check:

```text
status=SKIPPED
executed=false
```

Explicit live smoke executed once:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_account_balance_smoke --run-demo-account-balance --report-filename phase10l5_tachibana_account_balance_smoke_result.json --source phase10l5_p_no_monotonic_sequence_fix
```

Result:

```text
status=PASS
executed=true
environment=demo
login=PASS
logout=PASS
account_api_called=true
balance_api_called=true
orders_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
```

Protocol error diagnosis:

```text
CLMZanKaiSummary protocol_error_present=false
CLMZanKaiKanougaku protocol_error_present=false
p_errno_zero=true
p_err_empty=true
```

## 5. Normalized Account / Balance

`CLMZanKaiSummary` normalized values:

```text
buying_power=20000000
cash_available=17989000
withdrawable_cash=17989000
ipo_buying_power=17989000
margin_buying_power=54512121
nisa_growth_capacity=2400000
total_assets=20000000
```

`CLMZanKaiKanougaku` normalized values:

```text
buying_power=20000000
cash_available=20000000
nisa_growth_capacity=2400000
total_assets=20000000
```

These match the previously observed Web display candidates:

```text
現物株式買付=20000000
出金=17989000
IPO購入=17989000
信用新規建て=54512121
```

## 6. Paper Test 2 Initial Cash Candidate

Paper Test 2 initial funding can now be judged from API data.

Recommended candidate:

```text
initial_cash=20000000
initial_buying_power=20000000
initial_withdrawable_cash=17989000
initial_margin_buying_power=54512121
initial_ipo_buying_power=17989000
initial_nisa_growth_capacity=2400000
status=READY_FOR_PAPER_TEST2_INITIALIZATION_DECISION
```

No Paper Ledger or Paper Test 2 Ledger was created or updated in Phase10-L5.

## 7. Verification

JSON validation:

```text
reports/phase_reports/phase10l5_tachibana_p_no_monotonic_sequence_fix.json
reports/phase_reports/phase10l5_tachibana_account_balance_smoke_result.json
reports/phase_reports/phase10l5_tachibana_account_balance_default_skipped.json
```

Safety checks:

```text
secret canary: PASS
no forbidden CLMID audit: PASS
production_connected=false
orders_api_called=false
executions_api_called=false
quotes_api_called=false
paper_ledger_updated=false
paper_test2_ledger_initialized=false
raw_response_saved=false
```

## 8. Result

Phase10-L5 fixed the sequence bug and confirmed account/balance read-only retrieval from Tachibana demo.

Next recommended step:

```text
Regenerate the demo Broker Snapshot in a separate phase/run so the latest runtime snapshot reflects the fixed account/balance values, then proceed with Paper Test 2 initialization decisions.
```
