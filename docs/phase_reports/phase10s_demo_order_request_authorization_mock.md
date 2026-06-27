# Phase10-S Demo Order Request / Authorization Mock Foundation

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: mock-only request schema / authorization gate / executor dry-run readiness
- live_api_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- broker_order_api_called: false
- second_password_api_called: false
- broker_snapshot_updated: false
- paper_ledger_updated: false

## 1. Summary

Phase10-P / Q / R の設計に基づき、Tachibana demo 現物注文に必要な request shape と approval gate を mock-only で実装した。

追加:

```text
src/ai_fund_lab_v2/broker/tachibana_order_request.py
src/ai_fund_lab_v2/runtime/order_authorization.py
tests/broker/test_tachibana_order_request_builder.py
tests/runtime/test_order_authorization.py
```

更新:

```text
.env.example
src/ai_fund_lab_v2/broker/__init__.py
src/ai_fund_lab_v2/runtime/__init__.py
src/ai_fund_lab_v2/runtime/order_command.py
src/ai_fund_lab_v2/runtime/order_executor.py
tests/runtime/test_order_executor_interface.py
```

今回は request builder / authorization / executor dry-run readiness のみ。`CLMKabuNewOrder` の実送信経路は実装していない。

## 2. Tachibana Cash Stock Order Request

`TachibanaCashStockOrderRequest` を追加した。

Fields:

```text
issue_code
side
quantity
market_code
cash_margin_type
order_price
order_price_type
account_type
time_in_force
condition
reverse_order_type
reverse_trigger_condition
reverse_price
margin_position_day_type
margin_position_tax_type
second_password_required
second_password_present
production_allowed
```

`production_allowed=true` は Phase10-S では拒否する。

## 3. CLMKabuNewOrder Mock Builder

`TachibanaCashStockOrderRequestBuilder` を追加した。

Generated mock fields:

```text
p_no
p_sd_date
sCLMID=CLMKabuNewOrder
sZyoutoekiKazeiC
sIssueCode
sSizyouC
sBaibaiKubun
sCondition
sOrderPrice
sOrderSuryou
sGenkinShinyouKubun
sOrderExpireDay
sGyakusasiOrderType
sGyakusasiZyouken
sGyakusasiPrice
sTatebiType
sTategyokuZyoutoekiKazeiC
```

Mapping:

```text
BUY  -> sBaibaiKubun=3
SELL -> sBaibaiKubun=1
CASH_EQUITY -> sGenkinShinyouKubun=0
MARKET -> sOrderPrice=0
LIMIT -> sOrderPrice=<limit_price>
```

`p_no` は builder instance 単位で単調増加する。

## 4. Second Password Handling

Phase10-S では第二暗証番号の値を扱わない。

Implemented:

- `second_password_present` の boolean のみ保持
- `sSecondPassword` は mock payload に含めない
- safe summary には `second_password_value_saved=false`
- `.env.example` には `TACHIBANA_API_SECOND_PASSWORD_FILE=` の空値のみ追加

Not implemented:

- 第二暗証番号の値読み込み
- 第二暗証番号 API
- unlock 相当処理
- 発注 request への第二暗証番号送信

## 5. Approval Gate

`OrderApprovalGate` / `OrderApprovalScope` / `OrderAuthorizationResult` を追加した。

Approval scope:

```text
approval_id
environment
issue_code
side
quantity
max_notional
expires_at
```

Statuses:

```text
APPROVED
BLOCKED_NO_APPROVAL
BLOCKED_LIVE_ORDER_DISABLED
BLOCKED_APPROVAL_SCOPE_MISMATCH
BLOCKED_APPROVAL_EXPIRED
BLOCKED_SECOND_PASSWORD_MISSING
BLOCKED_PRODUCTION_PROHIBITED
```

Production は approval や second password presence に関係なく prohibited。

## 6. Demo Order Executor

`DemoOrderExecutor.submit()` は authorization result を受け取れる。

Behavior:

```text
live_order_allowed=false -> BLOCKED_LIVE_ORDER_DISABLED
approval missing -> BLOCKED_NO_APPROVAL
approval scope mismatch -> BLOCKED_APPROVAL_SCOPE_MISMATCH
second password missing -> BLOCKED_SECOND_PASSWORD_MISSING
authorization approved + dry_run=true -> DRY_RUN_READY
authorization approved + dry_run=false -> BLOCKED_EXECUTOR_STUB
```

`DRY_RUN_READY` でも `submitted=false`。Broker API は呼ばない。

## 7. Production Order Executor

Production は Phase10-S でも完全禁止。

```text
ProductionOrderExecutor.submit() -> BLOCKED_PRODUCTION_PROHIBITED
```

## 8. Redaction

Confirmed:

- second password value is never stored
- `sSecondPassword` is omitted from mock payload
- raw order id is not part of `OrderResult`
- broker order id requires hash if ever present
- raw response is not stored
- Broker API call flag remains false

## 9. Test Coverage

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_tachibana_order_request_builder.py tests/runtime/test_order_authorization.py tests/runtime/test_order_executor_interface.py tests/runtime/test_runtime_state_machine.py tests/runtime/test_fill_monitor_lifecycle.py tests/broker/test_broker_runtime_paths.py -q
```

Result:

```text
55 passed
```

Covered:

- buy request shape
- sell request shape
- market order price `0`
- limit order price
- p_no monotonic sequence
- second password missing block
- approval missing block
- approval scope mismatch block
- demo dry-run ready
- production blocked
- no broker API call

## 10. Verification

- JSON validation: PASS
- secret canary: PASS
- forbidden CLMID audit: PASS_WITH_MOCK_ORDER_BUILDER_ONLY
- no runtime mutation confirmation: PASS

`CLMKabuNewOrder` appears only in mock request builder/tests/docs and remains outside read-only client allowlist / transport execution path.

## 11. Completion Judgement

Phase10-S is complete.

Demo 発注に必要な request shape と approval gate は mock-only で実装済み。DemoOrderExecutor は dry-run ready まで進めるが、実発注経路は閉じたまま。

Next phase can implement demo order executor transport only after explicit approval, demo-only guard, second-password secret loader/redaction, and no-production audit are defined.
