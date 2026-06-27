# Phase9R-B Tachibana Demo Account State Check

- status: PASS_WITH_WARNINGS
- created_at: 2026-06-27
- today: 2026-06-27 (Sat)
- target_start_date: 2026-06-29 (Mon)
- scope: read-only account state check

## 1. Summary

Phase9R-B used the existing Phase10 read-only Broker Snapshot CLI to refresh the Tachibana demo account state once.

Executed flow:

```text
login
account / balance
positions
orders
executions / history
quote
logout
atomic latest broker snapshot write
```

Result:

```text
status=PASS_WITH_WARNINGS
executed=true
run_count=1
environment=demo
snapshot_written=true
```

Warnings are expected for the current demo state:

```text
executions=SKIPPED_NO_ORDERS
quotes=PASS_WITH_EMPTY_RESULT
```

No Paper Ledger was updated. Paper Test 1 archive was not created. Paper Test 2 ledger was not initialized.

## 2. Command

The explicit read-only snapshot run used the existing CLI:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_broker_snapshot --run-demo-snapshot --report-filename phase9r_b_tachibana_demo_account_state_check_snapshot_run.json --source phase9r_b_demo_account_state_check
```

The command printed only sanitized summary fields:

```text
executed=true
status=PASS_WITH_WARNINGS
report_path=reports/phase_reports/phase9r_b_tachibana_demo_account_state_check_snapshot_run.json
snapshot_path=.runtime/broker/tachibana/demo/latest_broker_snapshot.json
```

## 3. Snapshot

Updated snapshot:

```text
.runtime/broker/tachibana/demo/latest_broker_snapshot.json
```

Snapshot metadata:

```text
schema_version=tachibana_broker_snapshot_v1
environment=demo
generated_at=2026-06-27T09:15:38.483016+00:00
source=phase9r_b_demo_account_state_check
session_status=PASS
snapshot_sha256=2806ee92879d92c7a3a9703eab7199c2b5b67cf1f2fab6cfa9a9ef7e3bbbb768
```

Health:

```text
login=PASS
account=PASS
positions=PASS count=0
orders=PASS count=0
executions=SKIPPED_NO_ORDERS count=0
quotes=PASS_WITH_EMPTY_RESULT count=0
logout=PASS
api_errors=0
```

The normalized account/balance payload currently carries `source=mock`. This is a normalizer source label from the existing model; the snapshot CLI report confirms that the explicit demo run executed and wrote the snapshot.

## 4. Account / Balance

Normalized account values:

```text
currency=JPY
cash_available=0
buying_power=0
withdrawable_cash=0
total_assets=0
```

Normalized buying power values:

```text
currency=JPY
cash_available=0
buying_power=0
withdrawable_cash=0
total_assets=0
```

Paper Test 2 implication:

```text
initial_cash=0
initial_buying_power=0
monday_order_registration_status=NO_AVAILABLE_CASH
```

Paper Test 1 cash must not be substituted.

## 5. Positions / Orders / Executions / Quotes

Positions:

```text
positions_count=0
initial_positions=[]
```

Orders:

```text
orders_count=0
initial_orders_must_be_empty=true
```

Executions:

```text
executions_count=0
executions_status=SKIPPED_NO_ORDERS
```

Quotes:

```text
quotes_count=0
quotes_status=PASS_WITH_EMPTY_RESULT
```

## 6. Initial State Candidate

Paper Test 2 initial state candidate:

```text
paper_test_id=paper_test2_2026-06-29
start_date=2026-06-29
source_snapshot=.runtime/broker/tachibana/demo/latest_broker_snapshot.json
initial_cash=0
initial_buying_power=0
initial_positions=[]
initial_orders_must_be_empty=true
monday_order_registration_status=NO_AVAILABLE_CASH
```

Reasoning:

- Demo account snapshot has no positions.
- Demo account snapshot has no orders.
- Demo account snapshot has no executions.
- Normalized cash and buying power are both 0.
- Phase9R-A requires fail-closed behavior when available cash is 0.

## 7. Security / Redaction

Snapshot and reports do not store:

- raw response
- auth id value
- private key content
- virtual URL
- account/customer id plaintext
- order number plaintext
- execution id plaintext

The sanitizer redacted the `auth_identifier_saved` key value in the redaction-status object. This is conservative and does not expose an auth identifier.

## 8. Verification

JSON validation:

```text
python3 -m json.tool reports/phase_reports/phase9r_b_tachibana_demo_account_state_check_snapshot_run.json
python3 -m json.tool .runtime/broker/tachibana/demo/latest_broker_snapshot.json
python3 -m json.tool reports/phase_reports/phase9r_b_tachibana_demo_account_state_check.json
python3 -m json.tool reports/phase_reports/phase9r_b_demo_initial_state_candidate.json
```

Required safety checks:

```text
secret canary: PASS
no forbidden CLMID audit: PASS
snapshot schema validation: PASS
```

## 9. Result

Phase9R-B confirms that the current Tachibana demo account state is suitable for a safe Paper Test 2 initialization candidate, but the candidate has no available cash.

Next recommended step:

```text
Phase9R-C should create the Paper Test 1 archive manifest and Paper Test 2 initialization preflight, without creating a ledger unless the operator accepts the zero-cash initial state.
```
