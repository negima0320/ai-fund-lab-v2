# Phase10-R Fill Monitor Schema / Lifecycle Mock Implementation

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: mock-only schema / normalizer / classifier / runtime integration
- live_api_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- broker_order_api_called: false
- cancel_api_called: false
- correction_api_called: false
- second_password_api_called: false
- broker_snapshot_updated: false
- paper_ledger_updated: false

## 1. Summary

Phase10-Q の設計に基づき、Order Lifecycle / Fill Monitor を mock-only で実装した。

追加:

```text
src/ai_fund_lab_v2/runtime/fill_event.py
src/ai_fund_lab_v2/runtime/fill_monitor.py
tests/runtime/test_fill_monitor_lifecycle.py
```

更新:

```text
src/ai_fund_lab_v2/runtime/state_machine.py
src/ai_fund_lab_v2/runtime/__init__.py
```

今回は schema / classifier / runtime 連携のみ。実 API 接続、Demo 発注、Production 発注、Broker Snapshot 更新、Paper Ledger 更新は行っていない。

## 2. Lifecycle Enum

実装した `OrderLifecycle`:

```text
PREPARED
SUBMISSION_BLOCKED
SUBMITTED
ACCEPTED
WAITING_FILL
PARTIALLY_FILLED
FILLED
REJECTED
EXPIRED
CANCELED
UNKNOWN_STATUS
REQUIRES_HUMAN_REVIEW
```

## 3. Fill Event Schema

`FillEvent` fields:

```text
runtime_id
environment
issue_code
side
order_quantity
filled_quantity
remaining_quantity
average_fill_price
latest_fill_price
order_status
lifecycle_status
order_number_hash
execution_id_hash
observed_at
source
raw_ids_saved=false
```

Plaintext order number and plaintext execution id are rejected. Hashes must use the `sha256:` prefix when present.

## 4. Fill Monitor Result Schema

`FillMonitorResult` fields:

```text
status
lifecycle_status
runtime_next_state
filled
partially_filled
rejected
expired
canceled
requires_human_review
reason
events
```

The result does not include broker API call flags because this phase is mock-only and has no side effects.

## 5. Classifier

Implemented classifications:

- order list empty -> `REQUIRES_HUMAN_REVIEW`
- accepted waiting -> `WAITING_FILL`
- partial fill -> `PARTIALLY_FILLED`
- full fill -> `FILLED`
- rejected -> `REJECTED`
- expired -> `EXPIRED`
- canceled -> `CANCELED`
- unknown -> `UNKNOWN_STATUS`
- position mismatch -> `REQUIRES_HUMAN_REVIEW`

Fill extraction:

- `fills[]` / `aYakuzyouSikkouList`
- quantity from `quantity` / `sYakuzyouSuryou`
- price from `price` / `sYakuzyouPrice`
- average fill price as weighted average

## 6. Runtime Integration

Added:

```text
RuntimeStateMachine.transition_after_fill_monitor()
```

Mapping:

```text
ACCEPTED / WAITING_FILL -> WAITING_FILL
PARTIALLY_FILLED -> PARTIALLY_FILLED
FILLED -> FILLED
REJECTED / EXPIRED / CANCELED / UNKNOWN_STATUS / REQUIRES_HUMAN_REVIEW -> HALT
```

`HALT` here is runtime auto-progression stop, not Phase11 Safety emergency stop.

## 7. Redaction

Implemented:

- `raw_ids_saved=true` is rejected.
- short/plaintext order id is rejected.
- plaintext execution id hash is rejected.
- result serialization does not include `raw_order_id` or `raw_execution_id`.
- raw response is not stored.

## 8. Test Coverage

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/runtime/test_fill_monitor_lifecycle.py tests/runtime/test_runtime_state_machine.py tests/runtime/test_order_executor_interface.py tests/broker/test_broker_runtime_paths.py -q
```

Result:

```text
39 passed
```

Covered:

- accepted waiting
- partial fill
- full fill
- rejected
- expired
- canceled
- unknown -> HALT
- order list empty -> human review
- position mismatch
- plaintext id rejected
- runtime state mapping
- no Broker API call flags in mock result

## 9. Verification

```text
JSON validation: PASS
secret canary: PASS
forbidden CLMID audit: PASS_DESIGN_ONLY_AND_EXISTING_DENYLIST_REFERENCES
no runtime mutation confirmation: PASS
```

## 10. Result

Completion judgement:

```text
IMPLEMENTED
```

Next:

```text
Demo Order Executor implementation can proceed after request builder / authorization mock-only work.
```

