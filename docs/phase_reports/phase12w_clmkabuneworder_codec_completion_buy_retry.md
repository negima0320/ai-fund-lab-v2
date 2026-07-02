# Phase12-W CLMKabuNewOrder Codec Completion + BUY Retry

## Status

`PHASE12W_BUY_RETRY_REJECTED_BY_BROKER`

Phase12-Wでは、Phase12-Vで特定した `CLMKabuNewOrder` request-side codec不足を修正し、response normalizerを拡張した。targeted testsとretry guardがPASSしたため、Demo BUY wire retryを1回実行した。

結果、Phase12-Uの「`p_errno=0` だがorder numberなし」という曖昧状態は改善し、今回はredacted normalized responseで業務rejectを分類できた。

```text
p_errno=0
sResultCode=11104
business_classification=BUSINESS_REJECT
order_number_present=false
Broker Orders=0
Broker Executions=0
Broker Positions=0
```

公式コード表では `11104` は:

```text
株式新規注文
銘柄がありません
銘柄マスタレコードなし
```

だった。したがって、codec completion後の最有力残課題はBroker向け銘柄コード表現/銘柄マスタ照合である。

Production注文、Production Unlock、信用取引、LINE実送信、AI再学習、Backtest、raw request / raw response保存、secret保存は行っていない。

## Implementation Changes

### Request Codec Mapping

Added official v4r9 compressed keys:

| Field | Key |
| --- | ---: |
| `sZyoutoekiKazeiC` | 929 |
| `sBaibaiKubun` | 323 |
| `sCondition` | 336 |
| `sGenkinShinyouKubun` | 397 |
| `sGyakusasiOrderType` | 402 |
| `sGyakusasiZyouken` | 406 |
| `sGyakusasiPrice` | 403 |
| `sTatebiType` | 793 |
| `sTategyokuZyoutoekiKazeiC` | 798 |
| `aCLMKabuHensaiData` | 64 |
| `sTategyokuNumber` | 796 |
| `sTatebiZyuni` | 794 |

Maintained:

```text
sSecondPassword=698
sSecondPasswordOmit=699
```

`699` is not used as password.

### Response Codec Mapping

Added official success response fields:

| Field | Key |
| --- | ---: |
| `sEigyouDay` | 369 |
| `sOrderUkewatasiKingaku` | 672 |
| `sOrderTesuryou` | 669 |
| `sOrderSyouhizei` | 660 |
| `sKinri` | 518 |

Already present:

```text
sResultCode=688
sResultText=689
sWarningCode=876
sWarningText=877
sOrderNumber=643
sOrderDate=623
```

### Response Normalizer

`normalize_redacted_order_submit_result()` now records redacted presence/classification fields:

```text
result_code_present
result_code_value
result_code_zero
warning_code_present
warning_code_value
warning_code_zero
order_number_present
business_classification
accepted_with_warning
eigyou_day_present
```

Acceptance now requires:

```text
p_errno absent or 0
sResultCode == 0
sOrderNumber present
```

`p_errno=0` alone is not accepted.

Classifications added:

```text
PROTOCOL_ERROR
BUSINESS_REJECT
BUSINESS_WARNING_REVIEW
ORDER_NUMBER_MISSING_AFTER_SUCCESS_RESULT
```

Plain order number is never saved; only hash is saved if present.

### Retry Parent Fix

`_retry_parent_from_submit()` was updated from the old hard-coded `Phase12-Q` label to `Phase12-U` for this retry chain. The current submitted order artifact and latest Persistent Demo Ledger order history line were corrected for metadata only.

## Encoded Dummy Request Validation

Dummy order:

```text
code=92560
side=BUY
quantity=100
limit_price=5410
second_password=dummy-secret
```

Validation:

```text
uncompressed_order_keys_remaining=[]
sSecondPassword_request_key=698
sSecondPasswordOmit_as_password=false
required field present=true
cash/margin field for cash equity: sGenkinShinyouKubun=0
```

## Retry Guard

Pre-retry read-only:

```text
Broker Orders=0
Broker Executions=0
Broker Positions=0
Buying Power=20,000,000
Broker Actual Equity=20,000,000
Current Exposure=0
```

Approval:

```text
approval_id=operation_approval_2026-06-29_8913ebb65961
status=APPROVED
demo_order_allowed=true
production_order_allowed=false
max_notional=600000
```

Safety:

```text
status=ALLOW
```

Second password:

```text
present=true
value_saved=false
hash_saved=false
length_saved=false
```

Retry parent:

```text
phase=Phase12-U
business_date=2026-06-29
item_id=buy_2026-06-29_92560_001
status=REJECTED_OR_UNKNOWN
accepted=false
rejected=true
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

## BUY Retry

Command:

```bash
python3 scripts/run_demo_submit.py --trade-date 2026-06-29 --root .runtime/operations --execute-demo-order
```

Order:

| Field | Value |
| --- | --- |
| code | `92560` |
| side | `BUY` |
| quantity | `100` |
| limit_price | `5410` |
| expected_notional | `541000` |
| order_type | `CASH_EQUITY` |
| price_type | `LIMIT` |

Result:

| Field | Value |
| --- | --- |
| run_id | `operation_2026-06-29_operation_approval_2026-06-29_8913ebb65961_buy_2026-06-29_92560_001` |
| approval_id | `operation_approval_2026-06-29_8913ebb65961` |
| broker_order_api_called | true |
| clm_kabu_new_order_called | true |
| status | `REJECTED_OR_UNKNOWN` |
| accepted | false |
| rejected | true |
| p_errno | `0` |
| result_code_present | true |
| result_code_value | `11104` |
| warning_code_present | true |
| warning_code_value | empty |
| order_number_present | false |
| business_classification | `BUSINESS_REJECT` |
| p_err_classification | `BUSINESS_REJECT` |
| raw_request_saved | false |
| raw_response_saved | false |
| secret_saved | false |

Interpretation:

- `p_no` sequence issue: not reproduced.
- second password field issue: not reproduced.
- mixed compressed/uncompressed order field issue: fixed by test and codec completion.
- Broker now returns a business reject code.
- Official code table indicates `11104 = 銘柄がありません / 銘柄マスタレコードなし`.

## Post-submit Read-only

Post-submit read-only refresh:

```text
status=PASS
Broker Orders=0
Broker Executions=0
Broker Positions=0
```

No accepted order, fill, or position was confirmed.

## Fill / Reconcile / Report / Audit

| Step | Result |
| --- | --- |
| Fill Monitor | PASS, lifecycle=`REJECTED`, requires_human_review=true |
| Safety Monitor | PASS |
| Reconcile | PASS |
| Daily Report | PASS |
| Operation Audit | PASS |

Daily Report / Operation Audit emitted Arrow CPU info warnings in the sandbox, but both completed with PASS and wrote artifacts.

## SELL Lifecycle

SELL was not attempted.

Reason:

```text
BUY accepted=false
BUY filled=false
Broker positions=0
```

The Phase12 rule remains: SELL only after BUY is `FILLED` and Broker positions reflect the position.

## Tests

Executed:

```bash
python3 -m pytest \
  tests/broker/test_tachibana_order_codec_completion.py \
  tests/broker/test_tachibana_order_response_normalizer.py \
  tests/broker/test_tachibana_second_password_codec.py \
  tests/broker/test_tachibana_order_request_builder.py \
  tests/phase12/test_demo_order_wire_unlock_guards.py -q
```

Result:

```text
25 passed
```

Executed:

```bash
PYTHONPYCACHEPREFIX=.tmp_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/broker/tachibana_codec.py \
  src/ai_fund_lab_v2/broker/tachibana_order_request.py \
  tests/broker/test_tachibana_order_codec_completion.py \
  tests/broker/test_tachibana_order_response_normalizer.py
```

Result: PASS.

## Remaining Gaps

1. Broker business reject `11104` must be resolved before another retry.
2. Most likely next issue is Broker issue code normalization or Broker symbol/master lookup. The runtime used `92560`; Tachibana may require the exchange/order issue code format used in its master, potentially `9256` rather than J-Quants-style `92560`.
3. Add a read-only/safe broker issue-code normalization audit before Phase12-X retry.

## Safety Confirmation

```text
production_order_executed=false
production_unlock_executed=false
line_send_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
secret_value_logged=false
secret_hash_saved=false
secret_length_saved=false
phase9_modified=false
```

