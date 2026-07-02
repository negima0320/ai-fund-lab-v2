# Phase12-U sSecondPassword Request-side Codec Fix + BUY Retry

## Status

`PHASE12U_BUY_RETRY_REJECTED_BY_BROKER`

Phase12-Uでは、Phase12-Tで特定した第二暗証番号のrequest-side codec不整合を修正し、guardがPASSしたためDemo BUY wire retryを1回実行した。

実装上の主修正:

- `sSecondPassword` のrequest-side compressed keyを公式compress定義から `698` と確定。
- `sSecondPasswordOmit` は引き続き `699`。
- `DemoOrderBrokerTransport` のhard-coded `encoded["699"]` injectionを撤去。
- 第二暗証番号はlogical field `sSecondPassword` として最終payloadに注入し、codec経由で `698` へ変換する。

BUY retryは `CLMKabuNewOrder` まで到達したが、正規化結果は `REJECTED_OR_UNKNOWN` だった。post-submit read-only確認でもBroker orders / executions / positionsは0のため、BUY accepted / filledとは判断せず、SELL lifecycleには進んでいない。

Production注文、Production Unlock、信用取引、LINE実送信、AI再学習、Backtest、raw request / raw response保存、secret保存は行っていない。

## Official Codec Finding

公式 `mfds_json_api_compress_v4r9.js` の `_pa_col` 配列を確認した。

既存codecは公式配列indexに `+1` した値をcompressed keyとして持っている。

確認例:

| Field | Official index | Existing compressed key |
| --- | ---: | ---: |
| `sCLMID` | 332 | 333 |
| `p_no` | 287 | 288 |
| `p_sd_date` | 289 | 290 |

第二暗証番号関連:

| Field | Official index | Request-side compressed key |
| --- | ---: | ---: |
| `sSecondPassword` | 697 | `698` |
| `sSecondPasswordOmit` | 698 | `699` |

結論:

```text
sSecondPassword request-side compressed key = 698
sSecondPasswordOmit = 699
```

したがって、`699`を第二暗証番号値として使う旧実装は誤り。

## Implementation Changes

Changed:

- `src/ai_fund_lab_v2/broker/tachibana_codec.py`
  - `TACHIBANA_V4R9_COLUMNS["sSecondPassword"] = 698` を追加。
- `src/ai_fund_lab_v2/broker/transport.py`
  - `sSecondPassword` をpopして `encoded["699"]` へ手挿しする処理を撤去。
  - Demo order payloadも通常どおり `codec.encode_request(payload)` に通す。
- `tests/broker/test_tachibana_second_password_codec.py`
  - request-side key `698` の確認。
  - `699=sSecondPasswordOmit` をpassword値として使わない確認。
  - dummy secretのredacted summary保存禁止確認。
  - production fail closed確認。

Not changed:

- Phase9 artifacts / launchd / CLI
- Production Broker Source of Truth方針
- AI学習 / Backtest / LINE送信

## Secret Redaction

確認:

```text
TACHIBANA_API_SECOND_PASSWORD_FILE present=true
value_saved=false
secret_value_logged=false
secret_hash_saved=false
secret_length_saved=false
raw_request_saved=false
raw_response_saved=false
```

dummy secret tests confirm:

- logical final payload contains `sSecondPassword`
- encoded payload contains key `698`
- encoded payload does not use key `699` as password
- safe summary contains only `second_password_present=true`
- safe summary does not contain dummy value/hash/length

実secret値は表示・保存していない。

## Retry Guard

Pre-retry read-only refresh:

```text
status=PASS
Broker Orders=0
Broker Executions=0
Broker Positions=0
Buying Power=20,000,000
Broker Actual Equity=20,000,000
Current Exposure=0
```

Approval:

```text
approval_id=operation_approval_2026-06-29_c120c471ec8c
status=APPROVED
demo_order_allowed=true
production_order_allowed=false
max_notional=600000
```

Safety:

```text
status=ALLOW
```

Retry parent:

```text
phase=Phase12-Q
business_date=2026-06-29
item_id=buy_2026-06-29_92560_001
status=REJECTED_OR_UNKNOWN
accepted=false
rejected=true
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

Persistent Demo Ledger before retry:

```text
order_history_count=1
accepted_order_count=0
rejected_order_count=1
execution_history_count=0
position_history_count=0
```

No duplicate accepted/active order was present.

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
| run_id | `operation_2026-06-29_operation_approval_2026-06-29_c120c471ec8c_buy_2026-06-29_92560_001` |
| approval_id | `operation_approval_2026-06-29_c120c471ec8c` |
| broker_order_api_called | true |
| clm_kabu_new_order_called | true |
| normalized status | `REJECTED_OR_UNKNOWN` |
| accepted | false |
| rejected | true |
| p_errno | `0` |
| p_err_classification | `BROKER_REJECTED_OR_UNKNOWN` |
| broker_order_ref_hash | empty |
| demo_order_submitted / accepted | false |
| raw_request_saved | false |
| raw_response_saved | false |
| secret_saved | false |

Interpretation:

- Phase12-Sの `SECOND_PASSWORD_FIELD_OR_VALUE_ERROR` は再発していない。
- `p_no` sequence errorも再発していない。
- ただしBroker order idが得られず、post-submit read-onlyでも注文/約定/保有が0のため、acceptedとは扱わない。
- 次フェーズでは、`p_errno=0` かつorder idなしのresponse shape / normalizerを調査する必要がある。

## Post-submit Read-only

Post-submit market refresh:

```text
status=PASS
Broker Orders=0
Broker Executions=0
Broker Positions=0
```

Broker read-only snapshotで注文受付・約定・保有反映は確認できなかった。

## Fill / Reconcile / Report / Audit

| Step | Result |
| --- | --- |
| Fill Monitor | PASS, lifecycle=`REJECTED`, human review required |
| Safety Monitor | PASS |
| Reconcile | PASS |
| Daily Report | PASS |
| Operation Audit | PASS |

Daily Report / Operation AuditではArrow CPU情報のsandbox警告が標準出力に出たが、artifact生成とstatusはPASS。

## SELL Lifecycle

SELLは未試行。

理由:

```text
BUY accepted=false
BUY filled=false
Broker positions=0
```

Phase12-Uのルールどおり、BUYが `FILLED` かつBroker positionsへ反映された場合のみSELLへ進むため、今回はSELLを送信していない。

## Tests

Executed:

```bash
python3 -m pytest tests/broker/test_tachibana_second_password_codec.py tests/broker/test_tachibana_order_request_builder.py tests/phase12/test_demo_order_wire_unlock_guards.py -q
```

Result:

```text
18 passed
```

Executed:

```bash
PYTHONPYCACHEPREFIX=.tmp_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/broker/tachibana_codec.py \
  src/ai_fund_lab_v2/broker/transport.py \
  tests/broker/test_tachibana_second_password_codec.py
```

Result: PASS.

Note: plain `python3 -m py_compile ...` attempted to write pyc files under the macOS user cache outside the workspace and failed with `PermissionError`; rerun with workspace-local `PYTHONPYCACHEPREFIX` passed.

## Remaining Gaps

1. `p_errno=0` with no broker order id / no Broker order list entry must be investigated.
2. `normalize_redacted_order_submit_result()` may need an order response shape update once the accepted/rejected response fields are understood without saving raw response.
3. Demo lifecycle remains blocked before SELL until BUY accepted/fill can be confirmed through read-only Broker state.

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

