# Phase10-U Demo Order Live Smoke Foundation

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: default skipped / dry-run readiness / secret-presence gate / no live submit
- live_api_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- clmkabu_new_order_executed: false
- broker_order_api_called: false
- second_password_api_called: false
- broker_snapshot_updated: false
- paper_ledger_updated: false

## 1. Summary

Phase10-T の `NOT_READY` 項目のうち、Demo order live smoke の直前準備を mock/dry-run foundation として実装した。

追加:

```text
src/ai_fund_lab_v2/broker/tachibana_demo_order_smoke.py
src/ai_fund_lab_v2/cli/tachibana_demo_order_live_smoke.py
tests/broker/test_tachibana_demo_order_smoke_foundation.py
tests/cli/test_tachibana_demo_order_live_smoke_cli.py
```

更新:

```text
src/ai_fund_lab_v2/broker/settings.py
src/ai_fund_lab_v2/broker/secrets.py
src/ai_fund_lab_v2/broker/tachibana_order_request.py
src/ai_fund_lab_v2/broker/__init__.py
```

Phase10-U では実発注は不可能なまま。

## 2. Demo Order Live Smoke CLI

Added:

```text
python3 -m ai_fund_lab_v2.cli.tachibana_demo_order_live_smoke
```

Behavior:

```text
default -> SKIPPED / executed=false
--run-demo-order-live-smoke without --dry-run -> BLOCKED_LIVE_SUBMIT_NOT_IMPLEMENTED
--run-demo-order-live-smoke --dry-run -> dry-run readiness path only
```

No transport is executed in Phase10-U.

## 3. Second Password Local Secret Loader

Added:

```text
TachibanaSecretLoader.classify_second_password_file()
TachibanaSecondPasswordStatus
```

The loader reports only:

```text
file_configured
file_exists
file_readable
nonempty
present
value_loaded=false
value_saved=false
failure_classification
```

It does not return the second password value. Reports include presence/missing only.

## 4. Final Order Payload Assembly

Added:

```text
TachibanaCashStockOrderRequestBuilder.build_final_payload_summary()
```

In Phase10-U:

- `CLMKabuNewOrder` shape can be summarized.
- dry-run does not inject `sSecondPassword`.
- raw payload is not saved.
- broker API is not called.
- p_no remains monotonic in the order builder.

## 5. Demo-only Transport Path

Current:

- production environment is blocked by `BrokerSettings.require_demo_environment()`.
- `ProductionOrderExecutor` remains `BLOCKED_PRODUCTION_PROHIBITED`.
- live submit is `BLOCKED_LIVE_SUBMIT_NOT_IMPLEMENTED`.
- dry-run uses `DemoOrderExecutor` and never calls transport.

`CLMKabuNewOrder` is still not in read-only allowlist and is not executable through `HttpPostBrokerTransport`.

## 6. Redacted Order Submit Result Normalizer

Added:

```text
normalize_redacted_order_submit_result()
RedactedOrderSubmitResult
```

Properties:

- broker order id is hash-only.
- plaintext order id is not persisted.
- raw response is not persisted.
- `p_errno` / `p_err` may be included when supplied, without raw response.

## 7. Post-submit Reconciliation Skeleton

Dry-run result includes a skeleton:

```text
order_list: NOT_EXECUTED
order_detail: NOT_EXECUTED
positions: NOT_EXECUTED
fill_monitor: NOT_EXECUTED
broker_snapshot: NOT_EXECUTED
```

No read-only follow-up API is called in Phase10-U.

## 8. Test Coverage

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_demo_order_smoke_foundation.py tests/cli/test_tachibana_demo_order_live_smoke_cli.py tests/broker/test_tachibana_order_request_builder.py tests/runtime/test_order_authorization.py -q
```

Result:

```text
26 passed
```

Covered:

- default skipped
- dry-run ready
- missing second password blocks
- expired approval blocks
- production blocks
- live submit impossible in Phase10-U
- raw secret not saved
- raw payload not saved
- redacted order id hash-only normalizer

## 9. Verification

- JSON validation: PASS
- secret canary: PASS
- forbidden CLMID audit: PASS_WITH_MOCK_AND_BLOCKED_LIVE_FOUNDATION_ONLY
- no runtime mutation confirmation: PASS

## 10. Completion Judgement

Phase10-U is complete.

```text
readiness_for_phase10v = READY_FOR_ONE_SHOT_DEMO_ORDER_SMOKE_IMPLEMENTATION
actual_demo_order_submission_possible_now = false
```

The next phase may implement an explicitly approved, minimum quantity, one-shot demo order smoke. Phase10-U itself still cannot submit an order.
