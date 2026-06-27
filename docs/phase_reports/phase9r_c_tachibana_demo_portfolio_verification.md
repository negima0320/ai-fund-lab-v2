# Phase9R-C Tachibana Demo Portfolio Verification

- status: PASS_WITH_WARNINGS
- created_at: 2026-06-27
- target_start_date: 2026-06-29
- scope: Tachibana demo portfolio verification before Paper Test 2
- environment: demo

## 1. Summary

Phase9R-C regenerated the Tachibana demo Broker Snapshot after the Phase10-L5 `p_no` monotonic sequence fix.

Executed read-only flow:

```text
login
account / balance
positions
orders
executions / history
logout
atomic latest broker snapshot write
```

Quotes were intentionally skipped for this portfolio-only verification:

```text
quotes_requested=false
quotes_status=SKIPPED_NOT_REQUESTED
```

Result:

```text
status=PASS_WITH_WARNINGS
executed=true
environment=demo
snapshot_written=true
paper_ledger_updated=false
paper_test2_ledger_initialized=false
```

The warning is expected:

```text
executions=SKIPPED_NO_ORDERS
```

## 2. Snapshot

Updated snapshot:

```text
.runtime/broker/tachibana/demo/latest_broker_snapshot.json
```

Snapshot metadata:

```text
schema_version=tachibana_broker_snapshot_v1
environment=demo
generated_at=2026-06-27T11:08:47.454712+00:00
source=phase9r_c_demo_portfolio_verification
session_status=PASS
snapshot_sha256=fc20dd3a9a471f7296d285f1c99f7f69d8203a05b935657f2a12496682346b2a
```

Health:

```text
login=PASS
account=PASS
positions=PASS raw_count=7 effective_count=0
orders=PASS count=0
executions=SKIPPED_NO_ORDERS count=0
quotes=SKIPPED_NOT_REQUESTED count=0
logout=PASS
```

## 3. Account

Account / balance:

```text
buying_power=20000000
cash_available=17989000
withdrawable_cash=17989000
```

Additional values:

```text
ipo_buying_power=17989000
margin_buying_power=54512121
nisa_growth_capacity=2400000
total_assets=20000000
```

## 4. Positions

The positions APIs returned 7 normalized rows, but all rows are empty placeholders:

```text
issue_code=""
issue_name=""
quantity=0
average_price=0
market_value=0
unrealized_pnl=0
```

Effective positions:

```text
initial_positions=[]
effective_positions_count=0
```

No live holdings are confirmed in the demo account.

## 5. Orders / Executions

Orders:

```text
count=0
initial_orders=[]
```

Executions:

```text
count=0
status=SKIPPED_NO_ORDERS
```

## 6. Paper Test 2 Initial State Candidate

Paper Test 2 can use the latest demo snapshot as the initial state basis.

Candidate:

```text
paper_test_id=paper_test2_2026-06-29
start_date=2026-06-29
initial_cash=20000000
initial_buying_power=20000000
initial_withdrawable_cash=17989000
initial_positions=[]
initial_orders=[]
orders_must_be_empty=true
positions_effective_count=0
snapshot_sha256=fc20dd3a9a471f7296d285f1c99f7f69d8203a05b935657f2a12496682346b2a
```

No Paper Ledger or Paper Test 2 Ledger was created or updated in this phase.

## 7. Security / Redaction

Not saved:

```text
raw response
auth id
private key
virtual URL
account/customer id plaintext
order number plaintext
execution id plaintext
request body values
```

Redaction status in the latest snapshot:

```text
raw_response_saved=false
virtual_url_saved=false
auth_identifier_saved=false
private_secret_saved=false
account_customer_id_saved=false
order_number_plaintext_saved=false
execution_id_plaintext_saved=false
```

## 8. Verification

JSON validation:

```text
python3 -m json.tool reports/phase_reports/phase9r_c_tachibana_demo_portfolio_verification_snapshot_run.json
python3 -m json.tool .runtime/broker/tachibana/demo/latest_broker_snapshot.json
python3 -m json.tool reports/phase_reports/phase9r_c_tachibana_demo_portfolio_verification.json
python3 -m json.tool reports/phase_reports/phase9r_c_demo_initial_state_candidate.json
```

Safety checks:

```text
secret canary: PASS
no forbidden CLMID audit: PASS
snapshot schema validation: PASS
target_pytest=98 passed
```

## 9. Result

Demo account portfolio is verified:

```text
cash/buying_power available=true
effective_positions_count=0
orders_count=0
executions_count=0
```

Paper Test 2 initial state is ready to be initialized in a later phase, with no ledger mutation performed in Phase9R-C.
