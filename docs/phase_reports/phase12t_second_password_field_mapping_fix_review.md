# Phase12-T Second Password Field Mapping Fix Review

## Status

`PHASE12T_SECOND_PASSWORD_FIELD_MAPPING_FIX_REVIEW_COMPLETE`

Phase12-Tでは、Phase12-SのBUY retryで発生したBroker reject:

```text
SECOND_PASSWORD_FIELD_OR_VALUE_ERROR
p_errno=-1
```

について、第二暗証番号のrequest field mapping / v4r9 schema / compressed key / final injection boundaryを調査した。

今回は設計レビューのみであり、Demo注文再試行、`CLMKabuNewOrder`呼び出し、Production注文、Production Unlock、LINE実送信、AI再学習、Backtest再実行、raw request / raw response保存、secret保存は行っていない。

## Reviewed Sources

- `docs/phase_reports/phase12s_request_sequence_demo_ledger_buy_retry.md`
- `docs/phase_reports/phase12r_demo_order_sequence_fix_investigation.md`
- `docs/02_architecture/tachibana_demo_order_api_design.md`
- `src/ai_fund_lab_v2/broker/tachibana_order_request.py`
- `src/ai_fund_lab_v2/broker/transport.py`
- `src/ai_fund_lab_v2/broker/tachibana_codec.py`
- `src/ai_fund_lab_v2/broker/secrets.py`
- `src/ai_fund_lab_v2/broker/demo_order.py`
- `tests/phase12/test_demo_order_wire_unlock_guards.py`
- `tests/broker/test_tachibana_order_request_builder.py`
- Tachibana official API reference:
  - `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
  - `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`

Official reference text was checked read-only. The check found `CLMKabuNewOrder` and `sSecondPassword` in the request examples. It found no occurrence of `p_sSecondPassword`, `sPassword`, or `p_sPassword` in the same reference text.

## Schema Findings

### Field Name

The official request example for `CLMKabuNewOrder` uses:

```text
sSecondPassword
```

The existing Phase10/Phase12 design documents also identify `sSecondPassword` as the required second-password field for stock new order / correction / cancel flows.

The reviewed candidate names were:

| Candidate | Finding |
| --- | --- |
| `sSecondPassword` | Confirmed in official reference and existing design |
| `p_sSecondPassword` | Not found in official reference text |
| `sPassword` | Not found in official reference text |
| `p_sPassword` | Not found in official reference text |
| `Password` | Appears only as substring of `sSecondPassword`, not as an independent order field |

Therefore, the logical request field name should remain `sSecondPassword`.

### Request Hierarchy

The official examples show `sSecondPassword` as a top-level request payload field for `CLMKabuNewOrder`, alongside the other order request fields. No nested object boundary was found.

### Required / Optional

Existing design treats `sSecondPassword` as required for order submission. Phase12-S reached the Broker order endpoint but was rejected with second-password classification, so Phase12-U should continue to treat it as required and fail closed if absent.

### Demo / Production Difference

No evidence was found that Demo uses a different logical field name. Demo / Production switching should remain in Runtime Config -> Broker Factory / Adapter / Transport. Operations logic should not gain `if demo` / `if production` branches.

### Compressed Key

The current local v4r9 codec contains:

```text
sSecondPasswordOmit -> 699
```

but does not contain:

```text
sSecondPassword -> <compressed id>
```

`sSecondPasswordOmit` is a login acknowledgement/account flag and is not the order second password itself. The official HTML/reference text confirms the logical field name but the compressed key for the order request field was not safely confirmed in this review.

This means the current use of compressed key `699` for the actual second-password value is not proven and is likely wrong.

## Existing Implementation Findings

### Secret Loader

`TachibanaSecretLoader.classify_second_password_file()` records only safe booleans:

```text
file_configured
file_exists
file_readable
nonempty
present
value_loaded=false
value_saved=false
```

`load_second_password_value_for_demo_order_only()` loads the value only at the final demo-order boundary. It does not return a status object containing the value. The existing test confirms the dummy value is not present in `status.to_dict()`.

Finding: the loader boundary is acceptable for Phase12-U, provided the value remains ephemeral and is cleared after payload assembly.

### Request Builder

`TachibanaCashStockOrderRequestBuilder.build()` intentionally omits `sSecondPassword` for safe mock / dry-run shapes.

`build_final_payload_with_second_password()` adds:

```text
payload["sSecondPassword"] = second_password_value
```

only after validating the value is nonempty.

Finding: the builder is using the correct logical field name and the correct final injection boundary.

### Demo Order Adapter

`TachibanaDemoOrderAdapter.submit_cash_stock_order()`:

- requires demo environment
- loads normal Tachibana secrets
- shares the session-scoped request sequence manager
- creates a final payload with `sSecondPassword`
- clears `second_password_value` in `finally`
- normalizes the broker response without saving raw response text

Finding: the adapter does not appear to be the primary source of the Phase12-S second-password rejection.

### Transport

`DemoOrderBrokerTransport._encode_order_payload()` currently does:

```text
second_password = payload_to_encode.pop("sSecondPassword", None)
encoded = codec.encode_request(payload_to_encode)
encoded["699"] = str(second_password)
```

This bypasses the codec for `sSecondPassword` and manually injects compressed key `699`.

Finding: this is the strongest suspect. In the existing codec, `699` is mapped to `sSecondPasswordOmit`, not to `sSecondPassword`. If the Broker expects a different compressed key, or expects the logical key to be encoded by the correct order-request schema, the Broker would see the order second password as missing/NULL even though the local transport inserted a value under key `699`.

### Redaction / Artifact Safety

The current normalizer stores:

```text
p_errno
p_err_classification
raw_order_id_saved=false
raw_response_saved=false
```

and intentionally does not store `p_err` body text.

Finding: Phase12-S preserved the correct artifact safety posture.

## Failure Hypotheses

| Hypothesis | Judgement | Basis |
| --- | --- | --- |
| A. Field name differs from v4r9 | Unlikely | Official reference and existing design use `sSecondPassword` |
| B. Compressed key conversion is wrong | Most likely | Current transport hard-codes `699`, while codec maps `699` to `sSecondPasswordOmit` |
| C. Secret loader reads value but builder does not receive it | Unlikely | Final builder inserts `sSecondPassword`; tests cover dummy injection |
| D. Builder receives value but transport drops/misroutes it | Highly likely | Transport pops `sSecondPassword` before codec and rewrites it as `699` |
| E. Empty string is sent | Possible but not primary | Loader rejects empty file; Phase12-S preflight reported second password present |
| F. `p_sPassword` / `sSecondPassword` mix-up | Unlikely | Official reference did not show `p_sPassword`; current builder uses `sSecondPassword` |
| G. Login password field is being used instead | Unlikely | No independent `sPassword` order field was found |
| H. Demo requires a different field name | Not supported | No official evidence found |

Most likely cause:

```text
The logical field name is correct, but the transport's compressed-key mapping is wrong.
The order second password is being sent under key 699, which the local v4r9 mapping identifies as sSecondPasswordOmit, not sSecondPassword.
```

## Safe Validation Plan For Phase12-U

Phase12-U should validate payload shape without exposing or persisting the real second password.

Allowed validation:

- dummy secret unit test
- `second_password_present=true` boolean
- redacted payload shape
- key presence check
- official schema key comparison
- compressed-key mapping test using a dummy value

Forbidden validation:

- display real secret value
- save real secret value
- save real secret hash
- save real secret length
- save raw request body
- save raw response body

Recommended validation order:

1. Identify the official compressed key for request-side `sSecondPassword`.
2. Add a context-specific order request encoding test with dummy secret.
3. Confirm safe summary reports only presence and never value/hash/length.
4. Confirm artifacts do not contain `sSecondPassword`, dummy secret value, raw payload, or raw response.
5. Confirm production environment remains fail closed.
6. Only after tests pass, prepare a new retry with a new approval_id / run_id and `retry_parent=Phase12-S rejected artifact`.

## Required Phase12-U Tasks

Priority 1:

- Resolve the official v4r9 compressed key for request-side `sSecondPassword`.
- Remove the hard-coded `encoded["699"]` path unless `699` is independently proven to be the correct request-side key.
- Add `sSecondPassword` to the correct order-request encode mapping, or introduce a context-specific request encoder for order payloads.
- Preserve `sSecondPassword` injection only at the final demo-order boundary.

Priority 2:

- Add dummy-secret unit tests for:
  - final logical payload contains `sSecondPassword`
  - encoded order payload contains the correct compressed key
  - encoded order payload does not contain `sSecondPassword` if compression is enabled
  - safe summaries and artifacts store only presence booleans
  - value/hash/length/raw request/raw response are not saved

Priority 3:

- Add production fail-closed tests for the corrected path.
- Add a diagnostic artifact that records only:
  - `second_password_present=true`
  - `second_password_encoded_key_present=true`
  - `second_password_value_saved=false`
  - `raw_request_saved=false`
  - `raw_response_saved=false`

Priority 4:

- If and only if Phase12-U tests and guards pass, run a new Demo retry with:
  - new `approval_id`
  - new `run_id`
  - `retry_parent=Phase12-S rejected artifact`
  - same-day broker read-only zero-state check
  - Persistent Demo Ledger duplicate-order check

## Blocking Issues

- The correct compressed key for request-side `sSecondPassword` is unresolved in local code.
- The current hard-coded `699` conflicts with existing local mapping for `sSecondPasswordOmit`.
- A new Demo retry should not be attempted until the compressed key mapping is corrected and covered by dummy-secret tests.

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

