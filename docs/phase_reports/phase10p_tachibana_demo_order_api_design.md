# Phase10-P Tachibana Demo Order API Design

- status: DESIGN_COMPLETE
- created_at: 2026-06-28
- scope: design only
- demo_order_submitted: false
- production_order_submitted: false
- broker_order_api_called: false
- correction_api_called: false
- cancel_api_called: false
- second_password_api_called: false
- broker_snapshot_updated: false
- paper_ledger_updated: false

## 1. Summary

Tachibana demo order rehearsal に向け、発注 API の設計を行った。

作成:

```text
docs/02_architecture/tachibana_demo_order_api_design.md
```

今回は設計のみ。Demo 発注、Production 発注、発注 API 実行、訂正 API 実行、取消 API 実行、第二暗証番号 API 実行は行っていない。

## 2. Official Reference Findings

確認した公式資料:

- `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_compress_v4r9.js`

確認事項:

- 株式新規注文は `CLMKabuNewOrder`。
- 現物買い / 売りは同じ CLMID を使い、`sBaibaiKubun` で売買を分ける。
- 現物は `sGenkinShinyouKubun=0`。
- 市場は初期設計では東証 `sSizyouC=00`。
- 成行は `sOrderPrice=0`、指値は価格値。
- 株式新規注文、訂正、取消には `sSecondPassword` がある。
- 注文一覧は `CLMOrderList`。
- 注文約定一覧詳細は `CLMOrderListDetail`。
- 取消は `CLMKabuCancelOrder` / `CLMKabuCancelOrderAll`。

## 3. Design Outcome

Demo order implementation candidate:

```text
CLMKabuNewOrder
```

Read-only follow-up:

```text
CLMOrderList
CLMOrderListDetail
CLMGenbutuKabuList
```

Optional pre-check candidate:

```text
CLMZanUriKanousuu
```

Design-only / not implemented:

```text
CLMKabuCancelOrder
CLMKabuCancelOrderAll
CLMKabuCorrectOrder
```

Production:

```text
completely prohibited
```

## 4. Cash Equity Request Mapping

Initial supported scope:

- cash equity buy
- cash equity sell
- normal order only
- market / limit
- day order
- no margin
- no reverse limit
- no correction
- no cancel implementation

Mapping:

| Runtime | Tachibana |
|---|---|
| BUY | `sBaibaiKubun=3` |
| SELL | `sBaibaiKubun=1` |
| CASH_EQUITY | `sGenkinShinyouKubun=0` |
| MARKET | `sOrderPrice=0` |
| LIMIT | `sOrderPrice=<limit_price>` |
| day order | `sOrderExpireDay=0` |
| normal order | `sGyakusasiOrderType=0` |

## 5. Authorization

`sSecondPassword` is required for order/correction/cancel request shapes.

Phase10-P policy:

- do not load second password
- do not save second password
- do not send second password
- do not implement second password API
- do not implement unlock_trade

Future demo implementation must add a dedicated secret loader and redaction tests first.

## 6. Order Flow

Future demo order flow:

```text
login
read-only broker snapshot
order command build
explicit demo approval
demo-only guard
CLMKabuNewOrder
redacted acceptance summary
CLMOrderList
CLMOrderListDetail
CLMGenbutuKabuList
logout
```

Phase10-P does not execute this flow.

## 7. Capital Policy

Evaluation cash:

```text
1000000
```

Demo broker buying power:

```text
20000000
```

Order sizing uses evaluation cash. Demo broker buying power is an upper bound only.

Initial quantity policy:

```text
floor(evaluation_cash_allocation / limit_price / lot_size) * lot_size
```

Initial lot size:

```text
100
```

## 8. Redaction

Plaintext values never saved:

- raw response
- request body containing second password
- second password
- auth id
- private key
- virtual URL
- account/customer id
- order number
- execution id

Allowed:

- order number hash
- execution id hash
- non-secret result/status classification
- issue code
- side
- quantity
- price

## 9. Safety Separation

Safety Layer remains Phase11 responsibility.

Phase10-P does not implement:

- Safety Manager
- Emergency Stop
- stop-loss
- duplicate order guard
- broker divergence guard
- quote stale guard
- cash buffer guard
- daily loss guard
- recovery

Runtime may receive future Safety output, but this phase only designs order API requirements.

## 10. Verification

```text
JSON validation: PASS
secret canary: PASS
forbidden CLMID audit: PASS_DESIGN_ONLY_REFERENCES
no runtime mutation confirmation: PASS
```

Forbidden order CLMIDs appear only in design documents / existing denylist context. They were not implemented, allowlisted, or executed.

## 11. Result

Completion judgement:

```text
DESIGN_COMPLETE
```

Next:

```text
demo order request builder / mock-only phase
```

