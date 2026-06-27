# Phase10-Q Order Lifecycle / Fill Monitor Design

- status: DESIGN_COMPLETE
- created_at: 2026-06-28
- scope: design only
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

Demo 発注実装前に、注文送信後の lifecycle と fill monitor を設計した。

作成:

```text
docs/02_architecture/order_lifecycle_fill_monitor_design.md
```

今回は設計のみ。Demo 発注、Production 発注、発注 API、取消 API、訂正 API、第二暗証番号 API、unlock 相当処理は実行していない。

## 2. Lifecycle

定義した lifecycle:

```text
PREPARED
SUBMISSION_BLOCKED
SUBMITTED
ACCEPTED
REJECTED
WAITING_FILL
PARTIALLY_FILLED
FILLED
EXPIRED
CANCELED
UNKNOWN_STATUS
REQUIRES_HUMAN_REVIEW
```

Runtime state mapping:

```text
ORDER_SUBMITTED
WAITING_FILL
PARTIALLY_FILLED
FILLED
MONITORING
HALT
```

`HALT` は Phase10 runtime 上の自動進行停止であり、Phase11 Safety emergency stop ではない。

## 3. Fill Monitor Inputs

Inputs:

```text
CLMOrderList
CLMOrderListDetail
CLMGenbutuKabuList
latest Broker Snapshot
runtime order command / order result
internal ephemeral order number
```

Order detail requires:

```text
sOrderNumber
sEigyouDay
```

Plaintext order number is internal ephemeral only and must not be persisted.

## 4. Fill Monitor Output

Designed output includes:

- runtime_id
- environment
- order_number_hash
- issue_code
- side
- lifecycle
- ordered_quantity
- filled_quantity
- remaining_quantity
- average_fill_price
- fills with execution_id_hash
- position_confirmed
- requires_human_review
- reason

Raw order id / execution id plaintext is prohibited.

## 5. Partial Fill / Terminal State Handling

Partial fill:

- stay in `PARTIALLY_FILLED`
- keep polling on schedule
- no replacement order
- no automatic cancel
- stuck partial fill becomes human review

Rejected:

- classify `ORDER_REJECTED`
- runtime moves to `HALT`
- human review required

Expired:

- classify `ORDER_EXPIRED`
- runtime moves to `HALT`
- human review required

Canceled:

- classify `ORDER_CANCELED`
- runtime moves to `HALT`
- human review required

Unknown:

- classify `UNKNOWN_ORDER_STATUS`
- runtime moves to `HALT`
- human review required

## 6. Polling

Base polling schedule:

```text
09:05
09:30
10:30
12:35
14:45
15:20
```

Order-immediate short polling:

```text
30s
60s
120s
fixed small count
```

Automatic retry, cancel, correction, or replacement order is prohibited.

## 7. Broker Snapshot Relationship

Broker Snapshot is source of truth.

Roles:

- Order Detail is fill event evidence.
- Positions are final confirmation.
- Broker Snapshot consolidates broker state and health.
- Ledger is synchronized from broker-derived events in a later phase only.

Phase10-Q does not update Broker Snapshot or Paper Ledger.

## 8. Demo / Production Policy

Demo:

- demo fill monitor tracks demo order after future demo submission.
- broker position is source of truth when demo fill occurs.
- Paper Test2 evaluation uses 1,000,000 JPY.
- demo buying power 20,000,000 JPY is upper bound only.

Production:

- same monitor.
- broker actual order/execution/position is truth.
- automatic retry is prohibited.
- human review required for rejected, expired, canceled, unknown, mismatch, stale, API error.
- production order execution remains prohibited until readiness audit.

## 9. Redaction

Never persist:

- raw response
- raw order id
- raw execution id
- request body
- second password
- account/customer id
- virtual URL
- auth id
- private key

Allowed:

- order number hash
- execution id hash
- lifecycle classification
- issue code
- side
- quantity
- price
- timestamps

## 10. Verification

```text
JSON validation: PASS
secret canary: PASS
forbidden CLMID audit: PASS_DESIGN_ONLY_AND_EXISTING_DENYLIST_REFERENCES
no runtime mutation confirmation: PASS
```

Forbidden order CLMIDs are mentioned only as design/prohibition context or existing denylist references. They were not implemented, allowlisted, or executed.

## 11. Result

Completion judgement:

```text
DESIGN_COMPLETE
```

Next:

```text
Demo Order Executor implementation can proceed only after mock lifecycle/fill monitor schema work.
```

