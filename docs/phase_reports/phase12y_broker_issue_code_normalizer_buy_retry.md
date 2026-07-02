# Phase12-Y Broker Issue Code Normalizer + Demo BUY Retry

## Status

```text
PHASE12Y_BROKER_ISSUE_CODE_NORMALIZER_BUY_RETRY_COMPLETE
```

Phase12-Y implemented a Broker Issue Code Normalizer at the Order Plan to Broker Request boundary and executed one authorized Demo BUY retry.

Production order, Production unlock, LINE send, AI retraining, backtest, raw request save, raw response save, secret save, and Phase9 changes were not executed.

## Implementation

Added:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py
```

Responsibilities:

```text
internal / J-Quants code
↓
broker issue code
```

The normalizer is fail-closed and requires:

```text
listed info exists
current listed status is confirmable
product category is allowed
security type is present
market maps to broker market code
code shape is supported
```

Implemented current safe rule:

```text
JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR
92560 -> 9256
```

This rule is restricted to ordinary-stock product category `011` and mapped TSE markets such as `グロース`, `プライム`, and `スタンダード`.

## Boundary

The Order Plan remains unchanged:

```text
issue_code=92560
code=92560
```

Only the broker request boundary uses:

```text
broker_issue_code=9256
sIssueCode=9256
sSizyouC=00
```

The submit artifact records redacted normalization metadata:

```text
internal_code=92560
broker_issue_code=9256
normalization_rule=JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR
normalization_status=PASS
market=グロース
broker_market_code=00
product_category=011
security_type=011
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

## Dummy Request Confirmation

Dummy encoded request confirmation:

```text
internal_code=92560
broker_issue_code=9256
encoded key 473=9256
logical sIssueCode key present=false
```

This confirms that the encoded broker request contains broker-facing issue code `9256` and does not include uncompressed `sIssueCode`.

## Demo BUY Retry

New approval:

```text
approval_id=operation_approval_2026-06-29_ce33c45dd1fc
run_id=operation_2026-06-29_operation_approval_2026-06-29_ce33c45dd1fc_buy_2026-06-29_92560_001
retry_parent=Phase12-W
```

Order:

```text
internal_code=92560
broker_issue_code=9256
side=BUY
quantity=100
limit_price=5410
expected_notional=541000
```

Result:

```text
submit_status=PASS
row_status=ORDER_ACCEPTED
clm_kabu_new_order_called=true
demo_order_executed=true
broker_order_api_called=true
p_errno=0
sResultCode=0
sWarningCode=0
order_number_present=true
business_classification=ACCEPTED
broker_order_id_hash_saved=true
raw_order_id_saved=false
raw_response_saved=false
secret_saved=false
```

The previous `11104 銘柄がありません / 銘柄マスタレコードなし` reject was resolved by using broker issue code `9256`.

## Broker Read-only Confirmation

After submit, broker read-only refresh passed.

```text
broker_orders_count=1
broker_executions_count=0
broker_positions_count=0
```

Broker order summary:

```text
issue_code=9256
side=3
quantity=100
price=5410.0000
executed_quantity=0
remaining_quantity=100
status=未約定
```

## BUY Fill Status

Fill Monitor:

```text
status=PASS
classification=AVAILABLE
lifecycle=ACCEPTED
broker_orders_count=1
broker_executions_count=0
```

The BUY order was accepted but not filled during this check window.

## SELL Lifecycle

SELL lifecycle was not started because the BUY order was not filled.

```text
buy_filled=false
sell_executed=false
reason=BUY_NOT_FILLED_YET
```

This matches the Phase12-Y condition:

```text
BUY filledならSELL lifecycle開始
```

## Reconcile / Report / Audit

```text
Preflight after submit: PASS
Fill Monitor: PASS
Reconcile: PASS
Daily Report: PASS
Operation Audit: PASS
```

Reconciliation saw the broker order and no execution / position yet:

```text
orders_count=1
executions_count=0
positions_count=0
classification=PASS
```

Daily Report generated successfully after rerunning it serially. One earlier parallel run read a JSON artifact while another process was writing it and failed with `JSONDecodeError`; the serial rerun passed.

## Tests

Executed:

```text
python3 -m pytest tests/broker/test_broker_issue_code_normalizer.py tests/broker/test_broker_request_issue_code_mapping.py -q
python3 -m pytest tests/phase12 -q
python3 -m pytest tests/broker/test_broker_issue_code_normalizer.py tests/broker/test_broker_request_issue_code_mapping.py tests/phase12 -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/broker/issue_code_normalizer.py src/ai_fund_lab_v2/operations/operations.py
python3 -m json.tool .runtime/operations/submitted_orders/2026-06-29/submitted_orders.json
python3 scripts/run_operation_audit.py
```

Results:

```text
new broker tests: 7 passed
phase12 tests: 42 passed
combined targeted tests: 49 passed
py_compile: PASS
submitted_orders JSON validation: PASS
operation audit: PASS
```

## Safety Confirmation

```text
production_order_executed=false
production_unlock_executed=false
line_send_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
phase9_changed=false
```

## Remaining Gaps

- BUY is accepted but not filled yet.
- SELL lifecycle remains pending until broker execution / position appears.
- Persistent Demo Ledger has accepted order history, but execution and position history remain zero until fill.
- Historical demo ledger rows from earlier phases still include prior rejected attempts; current Phase12-Y submitted order uses `retry_parent=Phase12-W`.
