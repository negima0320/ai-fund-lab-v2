# Order Lifecycle / Fill Monitor Design

作成日: 2026-06-28

## 1. Purpose

本書は Tachibana demo 発注実装前に、注文送信後の lifecycle と fill monitor を設計する。

Phase10-Q は設計のみであり、実 API 接続、demo 発注、production 発注、発注 API、取消 API、訂正 API、第二暗証番号 API、unlock 相当処理は行わない。

## 2. Scope

対象:

- Order Lifecycle
- Fill Monitor
- Runtime State Machine 連携
- Polling schedule
- Broker Snapshot との関係
- error classification
- Demo rehearsal policy
- Production policy

対象外:

- broker order API 実装
- cancel / correction 実装
- Paper Ledger 更新
- Broker Snapshot 更新
- Safety Layer 本体
- 自動再発注
- 自動取消
- 自動売却

## 3. Order Lifecycle

注文 lifecycle:

| Lifecycle | Meaning | Runtime state relation |
|---|---|---|
| `PREPARED` | order command 作成済み | `ORDER_PREPARED` |
| `SUBMISSION_BLOCKED` | executor / approval / guard で送信せず | `ORDER_PREPARED` 維持 |
| `SUBMITTED` | executor が送信済みとして扱う | `ORDER_SUBMITTED` |
| `ACCEPTED` | broker が受付済み | `WAITING_FILL` |
| `REJECTED` | broker が受付拒否または受付エラー | `HALT` or human review |
| `WAITING_FILL` | 未約定で有効注文 | `WAITING_FILL` |
| `PARTIALLY_FILLED` | 一部約定 | `PARTIALLY_FILLED` |
| `FILLED` | 全部約定 | `FILLED` |
| `EXPIRED` | 一部または全部失効 | `HALT` or human review |
| `CANCELED` | 取消済み | `HALT` or human review |
| `UNKNOWN_STATUS` | 状態不明 | `HALT` |
| `REQUIRES_HUMAN_REVIEW` | 手動確認必須 | `HALT` |

Phase10-Q では lifecycle enum を設計するのみで実装しない。

## 4. Tachibana Status Mapping

`CLMOrderList` / `CLMOrderListDetail` の状態を lifecycle に写像する。

候補 mapping:

| Tachibana status code | Meaning | Lifecycle |
|---|---|---|
| `0` | 受付未済 | `SUBMITTED` or `WAITING_FILL` |
| `1` | 未約定 | `WAITING_FILL` |
| `2` | 受付エラー | `REJECTED` |
| `3` | 訂正中 | `REQUIRES_HUMAN_REVIEW` |
| `4` | 訂正完了 | `REQUIRES_HUMAN_REVIEW` |
| `5` | 訂正失敗 | `REQUIRES_HUMAN_REVIEW` |
| `6` | 取消中 | `REQUIRES_HUMAN_REVIEW` |
| `7` | 取消完了 | `CANCELED` |
| `8` | 取消失敗 | `REQUIRES_HUMAN_REVIEW` |
| `9` | 一部約定 | `PARTIALLY_FILLED` |
| `10` | 全部約定 | `FILLED` |
| `11` | 一部失効 | `EXPIRED` or `PARTIALLY_FILLED` with expiry |
| `12` | 全部失効 | `EXPIRED` |
| `13` | 発注待ち | `WAITING_FILL` |
| `14` | 無効 | `REJECTED` |
| `19` | 繰越失効 | `EXPIRED` |
| unknown | unknown | `UNKNOWN_STATUS` |

`sOrderYakuzyouStatus` mapping:

| Value | Meaning | Lifecycle hint |
|---|---|---|
| `0` | 未約定 | `WAITING_FILL` |
| `1` | 一部約定 | `PARTIALLY_FILLED` |
| `2` | 全部約定 | `FILLED` |
| `3` | 約定中 | `PARTIALLY_FILLED` or `WAITING_FILL` |

When status code and execution status conflict, fill monitor should classify `REQUIRES_HUMAN_REVIEW` and not infer a ledger mutation.

## 5. Fill Monitor Inputs

Fill Monitor inputs:

- `CLMOrderList`
- `CLMOrderListDetail`
- `CLMGenbutuKabuList`
- latest Broker Snapshot
- runtime order command / order result schema
- internal ephemeral order number, if available after submission

`CLMOrderListDetail` requires:

- `sOrderNumber`
- `sEigyouDay`

These values may be needed internally to request details, but plaintext must not be persisted in reports, manifests, or snapshots.

## 6. Fill Monitor Output Schema

Proposed normalized output:

```json
{
  "runtime_id": "runtime_x",
  "environment": "demo",
  "order_number_hash": "sha256:...",
  "issue_code": "7203",
  "side": "BUY",
  "lifecycle": "PARTIALLY_FILLED",
  "ordered_quantity": "100",
  "filled_quantity": "50",
  "remaining_quantity": "50",
  "average_fill_price": "2000",
  "fills": [
    {
      "execution_id_hash": "sha256:...",
      "quantity": "50",
      "price": "2000",
      "executed_at": "YYYYMMDDHHMMSS"
    }
  ],
  "position_confirmed": false,
  "requires_human_review": false,
  "reason": ""
}
```

Never include:

- plaintext order number
- plaintext execution id
- raw response
- raw request body
- account/customer id
- virtual URL
- auth id
- private key
- second password

## 7. Execution Extraction

Execution extraction source:

- `CLMOrderListDetail.aYakuzyouSikkouList`

Candidate fields:

- `sYakuzyouSuryou` -> fill quantity
- `sYakuzyouPrice` -> fill price
- `sYakuzyouDate` -> executed_at and execution hash material

If execution id is not explicit, use a stable hash over internal ephemeral fields such as order number, execution timestamp, quantity, and price. Persist only the hash.

Average fill price:

```text
sum(fill_quantity * fill_price) / sum(fill_quantity)
```

If `filled_quantity` from detail and sum of execution list disagree, classify as `REQUIRES_HUMAN_REVIEW`.

## 8. Position Confirmation

Position confirmation source:

- `CLMGenbutuKabuList`

Buy confirmation:

- filled quantity should appear in broker cash positions after settlement or near-real-time holding update if API reflects it.
- If filled but position is not reflected yet, classify as `FILLED_POSITION_PENDING_CONFIRMATION`.

Sell confirmation:

- broker position quantity should decrease by fill quantity.
- If filled but quantity is unchanged, classify as `POSITION_MISMATCH`.

Position mismatch does not trigger automatic order, cancel, or correction.

## 9. Runtime State Machine Integration

Runtime state mapping:

| Lifecycle | Runtime State |
|---|---|
| `PREPARED` | `ORDER_PREPARED` |
| `SUBMISSION_BLOCKED` | `ORDER_PREPARED` |
| `SUBMITTED` | `ORDER_SUBMITTED` |
| `ACCEPTED` | `WAITING_FILL` |
| `WAITING_FILL` | `WAITING_FILL` |
| `PARTIALLY_FILLED` | `PARTIALLY_FILLED` |
| `FILLED` | `FILLED` |
| `REJECTED` | `HALT` |
| `EXPIRED` | `HALT` |
| `CANCELED` | `HALT` |
| `UNKNOWN_STATUS` | `HALT` |
| `REQUIRES_HUMAN_REVIEW` | `HALT` |

`HALT` in Phase10 runtime means operational flow cannot proceed automatically. It is not Safety Layer emergency stop. Phase11 may add richer Safety state.

## 10. Polling Design

Base polling schedule:

| Time | Purpose |
|---|---|
| 09:05 | first post-open fill check |
| 09:30 | early session confirmation |
| 10:30 | morning reconciliation |
| 12:35 | post-lunch reopen check |
| 14:45 | near-close reconciliation |
| 15:20 | final intraday order status |

Short-cycle polling after order submission:

- 30s / 60s / 120s after submission, up to a small fixed count.
- Purpose is observation only.
- Automatic retry is prohibited.
- Automatic cancel is prohibited.
- If API unavailable, classify and require human review.

## 11. Broker Snapshot Relationship

Broker Snapshot is source of truth.

Roles:

- `CLMOrderList`: order state first pass
- `CLMOrderListDetail`: fill event evidence
- `CLMGenbutuKabuList`: final position confirmation
- Broker Snapshot: consolidated broker state and health

Paper Ledger:

- Does not drive broker state.
- In production/demo order flow, it may receive synchronized broker-derived events in a later phase.
- Phase10-Q does not update it.

## 12. Error Handling

Error classifications:

| Condition | Classification | Action |
|---|---|---|
| order list empty after submission | `ORDER_LIST_EMPTY_AFTER_SUBMISSION` | human review |
| detail missing | `ORDER_DETAIL_MISSING` | human review |
| position mismatch | `POSITION_MISMATCH` | human review |
| partial fill unchanged for long period | `PARTIAL_FILL_STUCK` | human review |
| rejected | `ORDER_REJECTED` | human review |
| expired | `ORDER_EXPIRED` | human review |
| canceled | `ORDER_CANCELED` | human review |
| API unavailable | `BROKER_API_UNAVAILABLE` | human review |
| stale snapshot | `STALE_BROKER_SNAPSHOT` | human review |
| p_no/session error | `SESSION_SEQUENCE_OR_AUTH_ERROR` | human review |
| unknown status | `UNKNOWN_ORDER_STATUS` | human review |

All error paths are fail closed from the runtime perspective. No automatic retry, cancel, correction, or replacement order is performed.

## 13. Demo Rehearsal Policy

Demo order rehearsal:

- Same lifecycle and fill monitor as production.
- Demo broker state is observed through read-only APIs after order submission.
- If demo fill occurs, broker position is source of truth.
- Paper Test2 evaluation remains based on 1,000,000 JPY.
- Demo account buying power 20,000,000 JPY is an upper bound only.

Demo fill monitor may produce reports, but must not mutate Paper Ledger in Phase10-Q.

## 14. Production Policy

Production uses the same monitor.

Production rules:

- broker actual order/execution/position is truth.
- automatic retry is prohibited.
- automatic cancel is prohibited.
- human review is required for rejected, expired, canceled, unknown, mismatch, stale, or API error states.
- plaintext order id and execution id remain prohibited in reports.

Production order execution remains prohibited until a production readiness audit explicitly enables it.

## 15. Redaction

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

Persist only:

- hashes for order/execution identifiers
- lifecycle classification
- non-secret result/status codes
- issue code
- side
- quantity
- price
- timestamps

## 16. Future Implementation Steps

Recommended sequence:

1. Add `OrderLifecycle` enum and fill monitor schema, mock-only.
2. Add order list/detail lifecycle classifier tests.
3. Add execution extraction tests.
4. Add identifier hashing tests.
5. Add demo fill monitor dry run using mock transport only.
6. Only then design demo order execution smoke separately.

## 17. Completion Criteria

Phase10-Q complete when:

- Order lifecycle is defined.
- Fill monitor inputs / outputs are defined.
- Runtime state transitions are defined.
- Partial fill / rejected / expired / canceled handling is defined.
- Polling schedule is defined.
- Broker Snapshot relationship is defined.
- Demo and production policies are clear.
- No runtime mutation or API execution occurred.

