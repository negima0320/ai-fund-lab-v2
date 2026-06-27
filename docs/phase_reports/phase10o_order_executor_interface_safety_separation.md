# Phase10-O Order Executor Interface and Safety Separation

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: interface / schema / mock executors only
- demo_order_submitted: false
- production_order_submitted: false
- broker_order_api_called: false
- paper_ledger_updated: false
- broker_snapshot_updated: false

## 1. Summary

Phase10-O では、Phase10-N の Runtime Foundation に Paper / Demo / Production の Order Executor を差し込むための interface と schema を追加した。

今回は interface / schema / mock executor のみであり、Demo 発注、Production 発注、Broker order API、訂正、取消、第二暗証番号、unlock 相当処理は実装・実行していない。

Safety Layer 本体は Phase11 に分離したままにしている。

## 2. Implemented Files

追加:

```text
src/ai_fund_lab_v2/runtime/order_command.py
src/ai_fund_lab_v2/runtime/order_executor.py
src/ai_fund_lab_v2/runtime/approval.py
tests/runtime/test_order_executor_interface.py
```

更新:

```text
src/ai_fund_lab_v2/runtime/order_executor_interface.py
src/ai_fund_lab_v2/runtime/state_machine.py
src/ai_fund_lab_v2/runtime/__init__.py
```

## 3. Order Command Schema

`OrderCommand` fields:

```text
runtime_id
environment
paper_test_id
issue_code
side
quantity
order_type
price_type
limit_price
evaluation_cash_basis
broker_cash_upper_bound
approval_required
approval_id
live_order_allowed
```

Money fields are serialized as strings to keep JSON stable.

## 4. Order Result Schema

`OrderResult` fields:

```text
status
submitted
accepted
rejected
skipped
reason
broker_order_id_hash
```

Plaintext broker order id is not part of the schema.

Supported status values:

```text
PAPER_ONLY_SUBMITTED
BLOCKED_NO_APPROVAL
BLOCKED_LIVE_ORDER_DISABLED
BLOCKED_EXECUTOR_STUB
REJECTED_INVALID_COMMAND
```

## 5. Approval Interface

Approval helpers:

```text
paper_auto_approval()
explicit_demo_approval()
explicit_production_approval()
default_deny()
```

Policy:

- Paper: auto paper approval.
- Demo: explicit demo approval required.
- Production: explicit production approval required.
- Default: deny.

## 6. Executor Behavior

Paper:

```text
PaperOrderExecutor.submit()
status=PAPER_ONLY_SUBMITTED
submitted=true
accepted=true
reason=paper_only_no_broker_api
```

Demo:

```text
DemoOrderExecutor default = BLOCKED_LIVE_ORDER_DISABLED
missing approval = BLOCKED_NO_APPROVAL
approved live flag = BLOCKED_EXECUTOR_STUB
```

Production:

```text
ProductionOrderExecutor default = BLOCKED_LIVE_ORDER_DISABLED
missing approval = BLOCKED_NO_APPROVAL
approved live flag = BLOCKED_EXECUTOR_STUB
```

`BLOCKED_EXECUTOR_STUB` means Phase10-O did not call any broker order API. It is a schema rehearsal only.

## 7. Runtime State Integration

`RuntimeStateMachine.transition_after_order_result()` was added.

Behavior:

- Current state must be `ORDER_PREPARED`.
- Executor result must have `submitted=true`.
- If executor blocks, runtime stays in `ORDER_PREPARED`.
- On paper-only submitted result, runtime can transition to `ORDER_SUBMITTED`.

This keeps Runtime Foundation schema-aware without adding broker execution behavior.

## 8. Safety Separation

Phase10-O does not implement:

- Safety Manager
- Safety State Machine
- Emergency Stop
- Duplicate Order Guard
- Broker Divergence Guard
- Quote Stale Guard
- Cash Buffer Guard
- Daily Loss Guard
- stop-loss logic
- recovery logic
- Safety Report

Runtime package has no `safety.py` and no Safety guard placeholder. Phase11 owns the Safety Layer.

Runtime may receive a future Safety result through a later interface, but Phase10-O contains no Safety judgement logic.

## 9. Test Coverage

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/runtime/test_runtime_state_machine.py tests/runtime/test_order_executor_interface.py tests/broker/test_broker_runtime_paths.py -q
```

Result:

```text
25 passed
```

Covered:

- Paper executor returns paper-only result.
- Demo executor blocked by default.
- Production executor blocked by default.
- `live_order_allowed=false` blocks.
- Missing approval blocks.
- Approved Demo / Production still use stub and do not submit.
- Raw broker order id is not present in result schema.
- Runtime can enter `ORDER_SUBMITTED` only from executor result schema with `submitted=true`.
- Runtime does not enter `ORDER_SUBMITTED` when executor blocks.
- Safety logic is not implemented in Phase10 runtime package.

## 10. Verification

```text
JSON validation: PASS
secret canary: PASS
forbidden CLMID audit: PASS
no runtime mutation confirmation: PASS
```

## 11. Result

Completion judgement:

```text
IMPLEMENTED
```

Next:

```text
Phase10-P or dedicated demo order API design phase
```

