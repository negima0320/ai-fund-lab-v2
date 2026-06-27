# Tachibana Demo Order API Design

作成日: 2026-06-28

## 1. Purpose

本書は Tachibana demo 環境での売買リハーサルに向けた Order API 設計をまとめる。

Phase10-P は設計のみであり、demo 発注、production 発注、発注 API 実行、訂正 API 実行、取消 API 実行、第二暗証番号 API 実行、unlock 相当処理は行わない。

## 2. References

確認した公式資料:

- `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_compress_v4r9.js`

既存設計:

- `docs/02_architecture/production_runtime_architecture.md`
- `docs/02_architecture/tachibana_readonly_api_design.md`
- `docs/phase_reports/phase10n_runtime_state_machine_skeleton.md`
- `docs/phase_reports/phase10o_order_executor_interface_safety_separation.md`

## 3. Confirmed CLMID Candidates

Demo order rehearsal で設計対象にする CLMID:

| Purpose | CLMID | Phase10-P status |
|---|---|---|
| 株式新規注文 | `CLMKabuNewOrder` | design only |
| 注文一覧 | `CLMOrderList` | already read-only implemented |
| 注文約定一覧詳細 | `CLMOrderListDetail` | already read-only implemented |
| 保有銘柄一覧 | `CLMGenbutuKabuList` | already read-only implemented |
| 売却可能数量 | `CLMZanUriKanousuu` | candidate, not implemented |
| 買余力 | `CLMZanKaiKanougaku` | already read-only implemented |
| 株式取消注文 | `CLMKabuCancelOrder` | design only, not implemented |
| 株式一括取消 | `CLMKabuCancelOrderAll` | design only, not implemented |
| 株式訂正注文 | `CLMKabuCorrectOrder` | out of Phase10-P implementation |

Phase10-P では `CLMKabuNewOrder`, `CLMKabuCancelOrder`, `CLMKabuCancelOrderAll`, `CLMKabuCorrectOrder` を allowlist に追加しない。

Production ではすべて禁止を維持する。

## 4. Cash Equity Buy / Sell Request Shape

現物買い / 現物売りは `CLMKabuNewOrder` を REQUEST 仮想 URL に送る。

Phase10-P の初期設計では現物取引のみを対象にし、信用新規、信用返済、現引、現渡、逆指値は対象外とする。

### 4.1 Required Fields

現物買い / 売りの要求項目:

| Field | Meaning | Initial design |
|---|---|---|
| `sCLMID` | 機能ID | `CLMKabuNewOrder` |
| `sZyoutoekiKazeiC` | 譲渡益課税区分 | 初期は特定口座 `1` を候補。口座設定と照合必須 |
| `sIssueCode` | 銘柄コード | `OrderCommand.issue_code` |
| `sSizyouC` | 市場 | 初期は東証 `00` |
| `sBaibaiKubun` | 売買区分 | 売 `1`, 買 `3` |
| `sCondition` | 執行条件 | 初期は指定なし `0` |
| `sOrderPrice` | 注文値段 | 成行 `0`, 指値は価格文字列 |
| `sOrderSuryou` | 注文株数 | 100株単位で丸める |
| `sGenkinShinyouKubun` | 現金信用区分 | 現物 `0` |
| `sOrderExpireDay` | 注文期日 | 初期は当日 `0` |
| `sGyakusasiOrderType` | 逆指値注文種別 | 通常 `0` |
| `sGyakusasiZyouken` | 逆指値条件 | 通常 `0` |
| `sGyakusasiPrice` | 逆指値値段 | 通常 `*` |
| `sTatebiType` | 建日種類 | 現物は `*` |
| `sTategyokuZyoutoekiKazeiC` | 建玉譲渡益課税区分 | 現物は `*` |
| `sSecondPassword` | 第二パスワード | 必須。Phase10-Pでは取得・保存・送信しない |

### 4.2 Side Mapping

Runtime `OrderCommand.side` mapping:

| Runtime side | Tachibana field |
|---|---|
| `BUY` | `sBaibaiKubun=3` |
| `SELL` | `sBaibaiKubun=1` |

### 4.3 Price Mapping

Runtime `PriceType` mapping:

| Runtime price_type | Tachibana field |
|---|---|
| `MARKET` | `sOrderPrice=0` |
| `LIMIT` | `sOrderPrice=<limit_price>` |

初期 demo rehearsal では、予期しない約定を避けるため、買いは指値を第一候補にする。成行は別途明示承認が必要。

## 5. Second Password / Order Authorization

公式仕様上、株式新規注文、訂正、取消には `sSecondPassword` が含まれる。

Phase10-P の扱い:

- 第二暗証番号は読み込まない。
- 第二暗証番号は `.env`、report、log、stdout、snapshot に保存しない。
- 第二暗証番号 API や unlock 相当処理は実装しない。
- Demo order implementation phase では、専用 secret loader、redaction、明示 approval、demo-only guard を設計してから扱う。

注文実装前提:

- `sSecondPassword` が未設定なら executor は必ず `BLOCKED_AUTHORIZATION_MISSING` とする。
- Production では第二暗証番号が設定されていても発注禁止。

## 6. Order Acceptance / Follow-up Flow

注文後の想定 flow:

1. login
2. broker snapshot read-only
3. order command build
4. approval check
5. demo-only guard
6. `CLMKabuNewOrder`
7. response normalize
8. order id hash only保存
9. `CLMOrderList`
10. `CLMOrderListDetail`
11. `CLMGenbutuKabuList`
12. logout

`CLMKabuNewOrder` response のうち、保存候補:

- result code
- result classification
- warning code
- warning classification
- order number hash
- business day
- accepted timestamp
- estimated settlement amount

保存禁止:

- plaintext order number
- raw response
- request body values containing second password
- account/customer id
- virtual URL
- auth id
- private key

## 7. Order List / Detail / Execution Monitoring

受付確認:

- `CLMOrderList` で注文番号 hash に対応する候補を照合する。
- API response 内の plaintext order number は即 hash 化し、runtime report には plaintext を出さない。

詳細確認:

- `CLMOrderListDetail` は `sOrderNumber` と `sEigyouDay` が必須。
- Phase10-P では設計のみ。実装時は plaintext order number を内部 ephemeral に限定する。

約定確認:

- `CLMOrderList` の状態コード / 約定ステータスを first pass とする。
- `CLMOrderListDetail` の約定リストを normalized execution event として扱う。
- `CLMGenbutuKabuList` で保有数量の反映を確認する。

Initial classification:

- `ORDER_ACCEPTED`
- `ORDER_REJECTED`
- `WAITING_FILL`
- `PARTIALLY_FILLED`
- `FILLED`
- `EXPIRED`
- `CANCELED`
- `UNKNOWN_ORDER_STATE`

## 8. Cancel API Policy

`CLMKabuCancelOrder` と `CLMKabuCancelOrderAll` は Phase10-P では設計のみ。

実装しない理由:

- 第二暗証番号が必要。
- 誤取消の影響が大きい。
- 訂正取消可否フラグとの照合が必要。
- Fill monitor と Safety Layer が先に必要。

Phase10-P では cancel executor、cancel CLI、cancel request builder、cancel allowlist を追加しない。

## 9. Demo-only Guard

Demo order implementation phase の必須条件:

- environment is `demo`
- production allow flag remains false
- live_order_allowed is true
- explicit demo approval exists
- second password secret is loaded without logging
- order command is cash equity only
- quantity is positive and lot-rounded
- issue code is explicit
- market code is allowlisted
- price_type is allowlisted
- broker cash upper bound is observed
- evaluation cash basis is observed
- no raw response persistence
- order id hash only

Phase10-P ではこの guard を設計するだけで実装しない。

## 10. Production Prohibition

Production order implementation remains prohibited.

Production executor policy:

- default deny
- no production order allowlist
- no production second password loading
- no production order CLI
- no production request builder for order APIs
- any production order attempt must return blocked result

Production readiness is a later audit phase and must include separate human approval, Safety Layer, operational runbook, and rollback plan.

## 11. Capital / Quantity Design

Paper Test2 evaluation cash:

```text
1,000,000 JPY
```

Demo broker buying power:

```text
20,000,000 JPY
```

Design:

- Order sizing uses evaluation cash, not demo broker full buying power.
- Demo broker buying power is upper bound only.
- Quantity is rounded down to lot size.
- Initial lot size is 100 shares.
- For buy orders, estimated notional must be less than or equal to evaluation cash allocation and broker cash upper bound.
- For sell orders, quantity must be less than or equal to broker confirmed sellable quantity or current holding quantity after read-only verification.

Example formula:

```text
max_quantity = floor(evaluation_cash_allocation / limit_price / lot_size) * lot_size
```

If max quantity is 0, order preparation returns `BLOCKED_LOT_SIZE_OR_CASH`.

## 12. Redaction

Never store:

- raw response
- raw request body
- `sSecondPassword`
- auth id
- private key
- virtual URL
- account/customer id
- plaintext order number
- plaintext execution id

Allowed:

- hash of order number
- hash of execution id
- non-secret result code
- non-secret status classification
- issue code
- side
- quantity
- price
- order status
- execution status

## 13. Phase Split

Recommended next split:

- Phase10-Q: demo order request builder design / mock only
- Phase10-R: demo order executor mock and approval plumbing
- Phase10-S: demo buy/sell smoke with one tiny order, if explicitly approved
- Phase10-T: fill monitor integration
- Phase10-U: production readiness audit
- Phase11: Safety Layer

The exact labels may be adjusted, but demo order execution must not be introduced before mock tests, second password redaction, demo-only guard, and production prohibition tests exist.

## 14. Completion Criteria

Phase10-P complete when:

- Demo発注に必要な API / CLMID / パラメータが明確。
- 注文、受付、約定、保有確認の流れが明確。
- 取消 API は設計のみで未実装。
- 第二暗証番号の扱いが明確。
- Demo order implementation prerequisites are clear.
- Production prohibition is maintained.
- Secrets and order identifiers are redacted by design.

