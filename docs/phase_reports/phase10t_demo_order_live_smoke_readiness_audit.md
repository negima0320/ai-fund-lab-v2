# Phase10-T Demo Order Live Smoke Readiness Audit

- status: AUDITED
- created_at: 2026-06-28
- readiness: NOT_READY
- scope: audit only
- live_api_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- broker_order_api_called: false
- second_password_api_called: false
- broker_snapshot_updated: false
- paper_ledger_updated: false

## 1. Summary

Phase10-S で追加した mock-only order request builder / authorization gate / DemoOrderExecutor dry-run readiness を監査した。

結論:

```text
readiness = NOT_READY
```

理由は、Demo order live smoke に必要な実行入口と secret loader がまだ存在しないため。

Phase10-S の状態は意図通り安全:

- `CLMKabuNewOrder` request shape は mock-only で生成できる。
- `DemoOrderExecutor` は `DRY_RUN_READY` まで。
- `ProductionOrderExecutor` は `BLOCKED_PRODUCTION_PROHIBITED`。
- 第二暗証番号は presence / missing のみ扱い、値は扱わない。
- `CLMKabuNewOrder` は read-only client allowlist に入っていない。

## 2. Readiness Verdict

Current verdict:

```text
NOT_READY
```

Blocking gaps:

1. Live smoke CLI /明示フラグが未実装。
2. Default SKIPPED を保証する demo order live smoke runner が未実装。
3. 第二暗証番号の local secret loader が未実装。
4. `sSecondPassword` を redacted request assembly に安全注入する経路が未実装。
5. `CLMKabuNewOrder` を demo-only / one-shot / approved scope に限定して transport する executor が未実装。
6. 発注後の order id hash / order list / detail / fill monitor / positions / broker snapshot 連携が未実装。
7. redacted order submit result schema が未実装。

## 3. Demo Environment Guard

Current:

- `OrderApprovalGate` は production を `BLOCKED_PRODUCTION_PROHIBITED` にする。
- `ProductionOrderExecutor.submit()` は production command を常に `BLOCKED_PRODUCTION_PROHIBITED` にする。
- `TachibanaCashStockOrderRequest.production_allowed=true` は拒否される。

Missing before live smoke:

- Live smoke CLI 側で `environment=demo` 以外を拒否する guard。
- Broker settings 側で demo-only order mode を固定する guard。
- production URL / production settings での order smoke 起動禁止。

Judgement:

```text
PARTIAL_PASS
```

## 4. Explicit Flag / Default Skip

Required:

```text
--run-demo-order-live-smoke
```

Current:

- Phase10-S は CLI / runner を実装していない。
- default SKIPPED を返す live order smoke result schema も未実装。

Judgement:

```text
NOT_READY
```

Required before READY:

- `tachibana_demo_order_live_smoke.py` または同等 CLI を作る。
- 明示フラグなしは `SKIPPED / executed=false`。
- 明示フラグありでも demo / approval / second password presence / max notional が揃わなければ BLOCKED。

## 5. Approval

Current:

`OrderApprovalScope` fields:

```text
approval_id
environment
issue_code
side
quantity
max_notional
expires_at
```

Implemented checks:

- approval missing
- live_order_allowed=false
- environment mismatch
- issue_code mismatch
- side mismatch
- quantity mismatch
- max_notional exceeded
- expires_at expired
- production prohibited

Judgement:

```text
PASS
```

Before live smoke:

- CLI must load or receive approval scope explicitly.
- Approval scope must be serialized without secrets.
- `approval_id` must appear in redacted manifest only.

## 6. Second Password

Current:

- `.env.example` has empty `TACHIBANA_API_SECOND_PASSWORD_FILE=`.
- `TachibanaCashStockOrderRequest` has `second_password_present`.
- `OrderApprovalGate` returns `BLOCKED_SECOND_PASSWORD_MISSING` when missing.
- `sSecondPassword` is intentionally omitted from mock payload.

Missing:

- local file existence/readability classifier for second password.
- value redaction and zero logging guarantee for order request assembly.
- redacted `sSecondPassword` insertion into live request.
- tests proving the value never appears in stdout/log/report/result.

Judgement:

```text
NOT_READY
```

## 7. Order Content Limits

Recommended first live smoke order:

```text
environment: demo
side: BUY only
order_type: CASH_EQUITY only
price_type: LIMIT
quantity: 100 shares
max_notional: <= 250,000 JPY
evaluation_cash_basis: 1,000,000 JPY
broker_cash_upper_bound: 20,000,000 JPY
market_code: 00
time_in_force: day
```

Reasoning:

- Buy-only avoids accidental sell of nonexistent / mismatched holdings.
- Limit order avoids uncontrolled market execution.
- 100 shares is the minimum ordinary lot assumption for initial smoke.
- Demo broker buying power is only an upper-bound guard; sizing is based on Paper Test2 evaluation cash.

Current implementation:

- request builder supports buy/sell and market/limit.
- No live smoke policy object exists yet to force first-smoke buy-only / limit-only / minimum-size constraints.

Judgement:

```text
PARTIAL_PASS
```

## 8. Post-submit Confirmation Flow

Required flow:

```text
login
order submit
order list
order detail
fill monitor
positions
broker snapshot
logout
```

Current:

- read-only order list / detail / positions / snapshot exist from earlier phases.
- fill monitor mock lifecycle exists.
- live order submit result schema is not implemented.
- raw order id plaintext persistence guard for live submit result is not implemented.

Judgement:

```text
PARTIAL_PASS
```

Before READY:

- hash-only broker order id helper in submit normalizer.
- order submit result containing only redacted fields.
- one-shot post-submit read-only reconciliation plan in runner.

## 9. Forbidden CLMID Audit

Current read-only denylist:

```text
CLMKabuNewOrder
CLMKabuCorrectOrder
CLMKabuCancelOrder
CLMKabuCancelOrderAll
CLMAuthCheckSecondPassword
CLMAuthStkLoginRequest
```

Current status:

- `CLMKabuNewOrder` appears only in mock builder/tests/docs.
- `CLMKabuNewOrder` is not in `READ_ONLY_CLMIDS`.
- `TachibanaRequestBuilder.build("CLMKabuNewOrder")` is tested to reject.
- No cancel/correct/second-password-check/unlock execution path exists.

Judgement:

```text
PASS_WITH_MOCK_ORDER_BUILDER_ONLY
```

Before live smoke:

- A separate demo-order allow path must be created outside read-only client.
- That allow path must allow only `CLMKabuNewOrder` for demo one-shot smoke.
- Cancel/correct/second-password-check CLMIDs must remain prohibited.

## 10. Rollback / Human Review

Policy for first demo live smoke:

- no automatic cancel
- no automatic retry
- no automatic re-order
- rejected / unknown -> HALT
- partial fill -> continue monitor or human review
- mismatch -> HALT / human review

Current:

- Fill monitor maps rejected / expired / canceled / unknown / human review to `HALT`.
- No live smoke runner exists to enforce no retry/no cancel/no re-order.

Judgement:

```text
PARTIAL_PASS
```

## 11. Runtime Integration

Current:

- `transition_after_order_result()` moves to `ORDER_SUBMITTED` only when `submitted=true`.
- `DRY_RUN_READY` has `submitted=false`, so it does not advance to `ORDER_SUBMITTED`.
- Fill monitor maps lifecycle to `WAITING_FILL`, `PARTIALLY_FILLED`, `FILLED`, or `HALT`.
- manifests include mutation flags defaulted to false.

Missing:

- live order result schema with `submitted=true` only after redacted broker acceptance.
- manifest field for redacted order result.
- live smoke runner that writes immutable redacted run manifest.

Judgement:

```text
PARTIAL_PASS
```

## 12. Required Work Before READY

Minimum next implementation items:

1. `TachibanaDemoOrderLiveSmokeResult` schema.
2. Demo order live smoke CLI with default `SKIPPED / executed=false`.
3. `--run-demo-order-live-smoke` explicit flag.
4. Demo-only guard in CLI and executor.
5. second password local secret loader with redaction tests.
6. live request assembler that inserts `sSecondPassword` only at the final transport boundary.
7. one-shot `CLMKabuNewOrder` demo-only transport path.
8. redacted order submit normalizer.
9. order id hash-only storage.
10. post-submit `CLMOrderList -> CLMOrderListDetail -> FillMonitor -> positions` flow.
11. no retry / no cancel / no re-order enforcement.
12. secret canary and forbidden CLMID audit covering generated result JSON.

## 13. Verification

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_order_request_builder.py tests/runtime/test_order_authorization.py tests/runtime/test_order_executor_interface.py tests/runtime/test_fill_monitor_lifecycle.py -q
```

Result:

```text
42 passed
```

Additional checks:

- JSON validation: PASS
- secret canary: PASS
- forbidden CLMID audit: PASS_WITH_MOCK_ORDER_BUILDER_ONLY
- no runtime mutation confirmation: PASS

## 14. Completion Judgement

Phase10-T audit is complete.

```text
readiness = NOT_READY
```

The system is safe in its current state and not capable of live demo order submission. The next phase should implement the missing live-smoke-only runner and secret-redacted final request boundary before any one-shot demo order smoke is allowed.
