# Phase12-V CLMKabuNewOrder Request / Response Schema Investigation

## Status

`PHASE12V_CLMKABUNEWORDER_REQUEST_RESPONSE_SCHEMA_INVESTIGATION_COMPLETE`

Phase12-Vでは、Phase12-U後に残った以下の状態を調査した。

```text
p_errno=0
CLMKabuNewOrder called=true
Broker Orders=0
Broker Executions=0
Broker Positions=0
Demo画面にも注文なし
BUY accepted / fill未確認
```

今回は調査・設計レビューのみであり、Demo注文再試行、`CLMKabuNewOrder`呼び出し、Production注文、Production Unlock、LINE実送信、AI再学習、Backtest、raw request / raw response / secret保存は行っていない。

## Reviewed Sources

- `docs/phase_reports/phase12u_second_password_codec_fix_buy_retry.md`
- `docs/phase_reports/phase12t_second_password_field_mapping_fix_review.md`
- `docs/phase_reports/phase12s_request_sequence_demo_ledger_buy_retry.md`
- `docs/phase_reports/phase12q_demo_buy_sell_full_lifecycle_wire_execution.md`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- `src/ai_fund_lab_v2/broker/tachibana_codec.py`
- `src/ai_fund_lab_v2/broker/normalizer.py`
- `src/ai_fund_lab_v2/operations/`
- Official Tachibana API reference:
  - `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
  - `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
  - `https://www.e-shiten.jp/e_api/mfds_json_api_compress_v4r9.js`

## Request Schema Findings

Official `CLMKabuNewOrder` cash buy example:

```text
sCLMID=CLMKabuNewOrder
sZyoutoekiKazeiC=1
sIssueCode=<code>
sSizyouC=00
sBaibaiKubun=3
sCondition=0
sOrderPrice=0 or limit price
sOrderSuryou=<quantity>
sGenkinShinyouKubun=0
sOrderExpireDay=0
sGyakusasiOrderType=0
sGyakusasiZyouken=0
sGyakusasiPrice=*
sTatebiType=*
sTategyokuZyoutoekiKazeiC=*
sSecondPassword=<second password>
```

The current builder creates the expected logical fields for a cash equity BUY:

| Field | Current value | Official meaning | Finding |
| --- | --- | --- | --- |
| `sCLMID` | `CLMKabuNewOrder` | function ID | OK |
| `sZyoutoekiKazeiC` | `1` | 特定口座 | OK as initial assumption |
| `sIssueCode` | `92560` | 銘柄コード | OK |
| `sSizyouC` | `00` | 東証 | OK |
| `sBaibaiKubun` | `3` | 買 | OK |
| `sCondition` | `0` | 指定なし | OK |
| `sOrderPrice` | `5410` | 指値価格 | OK shape as price string |
| `sOrderSuryou` | `100` | 注文株数 | OK |
| `sGenkinShinyouKubun` | `0` | 現物 | OK |
| `sOrderExpireDay` | `0` | 当日 | OK |
| `sGyakusasiOrderType` | `0` | 通常 | OK |
| `sGyakusasiZyouken` | `0` | 指定なし | OK |
| `sGyakusasiPrice` | `*` | 指定なし | OK |
| `sTatebiType` | `*` | 現物/新規では指定なし | OK |
| `sTategyokuZyoutoekiKazeiC` | `*` | 現引/現渡以外 | OK |
| `sSecondPassword` | final boundary only | 第二暗証番号 | OK after Phase12-U |

Logical request shape itself is mostly aligned with the official cash buy example.

### Request-side Codec Gap

The important finding is at the compression boundary.

Official v4r9 compressed keys:

| Field | Official compressed key | Current local codec |
| --- | ---: | ---: |
| `sCLMID` | 333 | 333 |
| `p_no` | 288 | 288 |
| `p_sd_date` | 290 | 290 |
| `sIssueCode` | 473 | 473 |
| `sSizyouC` | 731 | 731 |
| `sOrderPrice` | 650 | 650 |
| `sOrderSuryou` | 658 | 658 |
| `sOrderExpireDay` | 624 | 624 |
| `sSecondPassword` | 698 | 698 |
| `sZyoutoekiKazeiC` | 929 | missing |
| `sBaibaiKubun` | 323 | missing |
| `sCondition` | 336 | missing |
| `sGenkinShinyouKubun` | 397 | missing |
| `sGyakusasiOrderType` | 402 | missing |
| `sGyakusasiZyouken` | 406 | missing |
| `sGyakusasiPrice` | 403 | missing |
| `sTatebiType` | 793 | missing |
| `sTategyokuZyoutoekiKazeiC` | 798 | missing |

Current encoded dummy payload after Phase12-U still contains uncompressed logical keys:

```text
sBaibaiKubun
sCondition
sGenkinShinyouKubun
sGyakusasiOrderType
sGyakusasiPrice
sGyakusasiZyouken
sTatebiType
sTategyokuZyoutoekiKazeiC
sZyoutoekiKazeiC
```

This means the actual request likely mixed compressed numeric keys with uncompressed logical keys. The official compress sample states clients should compress before sending. Therefore, even though the logical builder shape is close, the request-side codec is incomplete for order submission.

## Response Schema Findings

Official `CLMKabuNewOrder` success response:

```text
sCLMID=CLMKabuNewOrder
sResultCode=0
sResultText=""
sWarningCode=0
sWarningText=""
sOrderNumber=<order number>
sEigyouDay=<YYYYMMDD>
sOrderUkewatasiKingaku=<amount>
sOrderTesuryou=<fee>
sOrderSyouhizei=<tax>
sKinri=-
sOrderDate=<YYYYMMDDHHMMSS>
```

Field semantics:

| Field | Meaning |
| --- | --- |
| `sResultCode` | business result code; `0` means normal |
| `sResultText` | text for result code |
| `sWarningCode` | business warning code; `0` means normal |
| `sWarningText` | text for warning code |
| `sOrderNumber` | order number, unique together with business day |
| `sEigyouDay` | business day |
| `sOrderDate` | order timestamp |

`p_errno=0` should be treated as protocol/API transport success only. It is not sufficient evidence of order acceptance. For order acceptance, the normalized response should require:

```text
p_errno is absent or 0
sResultCode == 0
sOrderNumber present
```

Warnings should be recorded by classification/presence only unless they are safe to persist as normalized non-secret business fields.

## Normalizer Findings

Current `normalize_redacted_order_submit_result()`:

```text
order_id = sOrderNumber or sOrderOrderNumber or order_number
result_code = sResultCode or p_errno or ""
accepted = result_code in {"", "0"} and bool(order_id or raw.get("accepted"))
```

What it handles:

- It will accept `sOrderNumber` if decoded and present.
- It prevents false accepted status when `p_errno=0` but no order id exists.
- It does not save raw response.

Gaps:

- It does not preserve safe business result metadata such as `sResultCode` presence/value class, `sWarningCode` presence/value class, `sEigyouDay` presence, or fee/amount presence.
- It does not classify nonzero `sResultCode` / `sWarningCode` as `BUSINESS_REJECT` / `BUSINESS_WARNING`.
- The local codec lacks several response fields from the official success response:
  - `sEigyouDay=369`
  - `sOrderUkewatasiKingaku=672`
  - `sOrderTesuryou=669`
  - `sOrderSyouhizei=660`
  - `sKinri=518`
- The local codec has `sOrderNumber=643`, so the most important acceptance ID should decode if the Broker returned it under the official compressed key.

Given Phase12-U had no order id and Broker orders remained zero, the normalizer's `REJECTED_OR_UNKNOWN` classification is conservative and appropriate. The bigger immediate issue is likely request encoding completeness, not only response normalization.

## Broker Orders=0 / Demo画面注文なし Hypotheses

| Hypothesis | Judgement | Basis |
| --- | --- | --- |
| A. Request required fields are business-rejected but normalizer misses detail | Likely | Missing compressed mappings can make required order fields invisible or invalid to Broker business layer |
| B. Request field values are wrong | Possible but secondary | Logical values match official cash buy example; account/NISA assumptions still need account-specific verification |
| C. price_type / limit_price invalid | Less likely | Official allows nonzero order price as limit price; `5410` shape is valid |
| D. market/account/order区分 invalid | Possible | `sZyoutoekiKazeiC=1`, `sSizyouC=00`, `sGenkinShinyouKubun=0` are official values, but account-specific constraints remain possible |
| E. Demo requires an extra fixed field | Not found | Official request example does not show extra front/channel field |
| F. `p_errno=0` means API/protocol success only | Highly likely | Official order success response also requires `sResultCode=0` and `sOrderNumber` |
| G. Order list API search condition wrong | Unlikely as primary | User confirmed Demo screen has no order; post-submit read-only orders=0 aligns with actual unaccepted order |
| H. Demo screen delay | Unlikely | User confirmed no Demo screen order; read-only refresh also remained zero |

Most likely cause:

```text
The order logical payload is mostly correct, but the request-side v4r9 codec is incomplete for CLMKabuNewOrder.
Several required order fields are still sent as uncompressed logical keys while other fields are compressed.
The Broker returns protocol p_errno=0, but the business order is not accepted; no sOrderNumber is returned and orders/executions/positions remain zero.
```

## Safe Validation Plan For Phase12-W

Allowed before retry:

- official schema vs local request shape diff
- dummy request shape test
- encoded key completeness test
- redacted key presence test
- response normalizer fixture tests
- no raw value persistence

Forbidden before retry:

- real secret display
- raw request save
- raw response save
- Demo retry before tests pass
- Production order

Recommended validation:

1. Add all official `CLMKabuNewOrder` request field mappings to the codec.
2. Add response mappings for official success response fields.
3. Add a dummy encoded order request test asserting no uncompressed order logical keys remain after encoding.
4. Add normalizer tests:
   - `p_errno=0`, `sResultCode=0`, `sOrderNumber` present -> accepted
   - `p_errno=0`, `sResultCode=0`, `sOrderNumber` absent -> rejected/unknown
   - `p_errno=0`, `sResultCode!=0` -> business reject
   - `sWarningCode!=0` -> accepted with warning/review, only safe warning classification
5. Add a redacted response-shape diagnostic that stores field presence/classes only:
   - `sResultCode_present`
   - `sResultCode_zero`
   - `sWarningCode_present`
   - `sWarningCode_zero`
   - `sOrderNumber_present`
   - `sEigyouDay_present`
   - `order_id_hash_saved`
   - `raw_response_saved=false`
6. Only after these pass, prepare Phase12-W retry with new approval/run and `retry_parent=Phase12-U`.

## Required Phase12-W Tasks

Priority 1:

- Complete request-side codec mapping for all `CLMKabuNewOrder` required fields:
  - `sZyoutoekiKazeiC=929`
  - `sBaibaiKubun=323`
  - `sCondition=336`
  - `sGenkinShinyouKubun=397`
  - `sGyakusasiOrderType=402`
  - `sGyakusasiZyouken=406`
  - `sGyakusasiPrice=403`
  - `sTatebiType=793`
  - `sTategyokuZyoutoekiKazeiC=798`
  - optional margin repayment fields if later needed: `aCLMKabuHensaiData=64`, `sTategyokuNumber=796`, `sTatebiZyuni=794`

Priority 2:

- Complete response mapping for official success fields:
  - `sEigyouDay=369`
  - `sOrderUkewatasiKingaku=672`
  - `sOrderTesuryou=669`
  - `sOrderSyouhizei=660`
  - `sKinri=518`
  - confirm existing `sOrderNumber=643`, `sOrderDate=623`, `sResultCode=688`, `sWarningCode=876`

Priority 3:

- Extend `normalize_redacted_order_submit_result()` to classify:
  - `ACCEPTED`
  - `BUSINESS_REJECT`
  - `ACCEPTED_WITH_WARNING_REVIEW`
  - `REJECTED_OR_UNKNOWN`
- Keep order number hash-only; no plaintext order id in reports.

Priority 4:

- Add dummy request/response tests and redacted shape tests.
- Run targeted pytest / py_compile / JSON validation.
- If guards pass, run Phase12-W BUY Demo retry with:
  - new approval_id
  - new run_id
  - `retry_parent=Phase12-U`
  - pre-retry Broker orders/executions/positions zero check
  - Persistent Demo Ledger duplicate active order check
  - SELL only if BUY is filled and Broker positions reflect it

## Blocking Issues

- Request-side order codec is incomplete for required `CLMKabuNewOrder` fields.
- `p_errno=0` must not be treated as order acceptance without `sResultCode=0` and `sOrderNumber`.
- Response normalizer lacks business reject / warning presence classification.

## Safety Confirmation

```text
implementation_changed=false
demo_order_wire_execution=false
clm_kabu_new_order_called=false
demo_order_executed=false
production_order_executed=false
line_send_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
phase9_modified=false
```

