# Phase12-X Broker Issue Code Normalization Review

## Status

```text
PHASE12X_BROKER_ISSUE_CODE_NORMALIZATION_REVIEW_COMPLETE
```

This phase was investigation and design review only.

No implementation change, no Demo order retry, no `CLMKabuNewOrder` call, no Production order, no LINE send, no AI retraining, and no backtest rerun were executed in Phase12-X.

## Background

Phase12-W completed the `CLMKabuNewOrder` request / response codec work and moved the Demo BUY retry from protocol errors to a broker business reject:

```text
code=92560
side=BUY
quantity=100
limit_price=5410
p_errno=0
sResultCode=11104
classification=BUSINESS_REJECT
official meaning=銘柄がありません / 銘柄マスタレコードなし
Broker Orders/Executions/Positions=0
```

The remaining issue is likely not request sequencing or second password mapping. It is likely the issue-code representation passed to Tachibana Broker.

## Finding 1: What 92560 Is

`92560` is the J-Quants / internal operations code for the selected security.

Observed local artifacts:

```text
.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet
.runtime/operations/feature_refresh/2026-06-29/jquants/listed_issues/listed_info_for_feature.parquet
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
.runtime/operations/feature_artifacts/2026-06-26/candidate_features.parquet
.runtime/operations/order_plan/2026-06-29/order_plan.json
```

For `92560`, listed information showed:

```text
Code: 92560
CoName: サクシード
Market: グロース
ProdCat: 011
```

`ProdCat=011` is consistent with an ordinary domestic listed stock in the current candidate path. The code is correctly used by J-Quants, feature refresh, candidate AI, opportunity selection, and the Order Plan primary code.

Conclusion:

```text
92560 = internal / J-Quants / feature / Order Plan code
```

This code should remain unchanged in AI, J-Quants, feature, candidate, and Order Plan primary fields.

## Finding 2: Tachibana Broker Issue Code Format

The Tachibana `CLMKabuNewOrder` request uses `sIssueCode` together with `sSizyouC`.

Official Tachibana examples for `CLMKabuNewOrder` use four-character issue codes such as:

```text
sIssueCode=6501
sSizyouC=00
```

The current request path passes the Order Plan `issue_code` directly into the broker order command. For the Phase12-W BUY retry, this meant:

```text
Order Plan issue_code=92560
Broker request sIssueCode=92560
```

Given the broker reject:

```text
sResultCode=11104
銘柄がありません / 銘柄マスタレコードなし
```

and the Tachibana examples, the broker-facing issue code candidate for this ordinary stock is:

```text
internal / J-Quants code: 92560
broker sIssueCode: 9256
```

Conclusion:

```text
Tachibana CLMKabuNewOrder should receive broker issue code 9256 for this security, not internal code 92560.
```

## Finding 3: Existing Internal Display-Code Precedent

Existing local code already contains a display-code convention for J-Quants-style codes:

```text
93670 -> 9367
148A0 -> 148A
```

This supports the interpretation that a trailing `0` can be removed when converting a J-Quants code to a market display / broker-facing issue code.

However, this must not be implemented as an unconditional string truncation. The conversion must be guarded by listed information, product category, code shape, and fail-closed behavior.

## Finding 4: Read-only Broker Lookup

A read-only broker quote lookup was performed for:

```text
92560
9256
92560,9256
```

Result:

```text
normalized_quote_count=0
normalized_issue_codes=[]
```

This was inconclusive: neither representation returned a normalized quote through the tested read-only quote path. No order endpoint was called and no raw response or secret was saved.

The lookup does not disprove the `92560 -> 9256` conversion. It only means the quote endpoint did not provide a usable confirmation for this candidate during the review.

## Recommended Normalization Boundary

The conversion must be isolated at the Order Plan to Broker Request boundary.

Do not change:

```text
J-Quants code
feature code
candidate code
Order Plan primary code
AI input/output code
ledger internal code
```

Recommended boundary:

```text
Order Plan item
  internal_code / code / issue_code = 92560
  market = グロース
  product_category = 011

Broker request preparation
  broker_issue_code = 9256
  sIssueCode = 9256
  sSizyouC = 00
```

The operations layer should keep using internal code for identity and reporting. The broker adapter / request preparation boundary should produce broker-specific fields.

## Candidate Conversion Rules

### Rule: Ordinary Domestic Stock, J-Quants 5-char Trailing Zero

Apply only when all conditions are true:

```text
listed_info exists
listed_info confirms current listed security
ProdCat=011 or explicitly allowed ordinary-stock category
internal code length is 5
last character is 0
first 4 characters are numeric or valid listed alphanumeric issue code
market can be mapped to Tachibana sSizyouC
```

Then:

```text
broker_issue_code = internal_code without trailing 0
92560 -> 9256
148A0 -> 148A
```

### Fail Closed Conditions

Fail closed when any of the following are true:

```text
listed_info missing
current listing cannot be confirmed
product category is not allowed for operations
code length is not supported
5-character code does not end with 0
market cannot be mapped to broker market code
broker_issue_code is empty or malformed
normalization result conflicts with existing artifact identity
```

### Product / Security Exceptions

ETF, REIT, preferred shares, special listed products, or non-standard code shapes must not be normalized by a blanket trailing-character deletion rule.

For Phase12-Y, only the ordinary-stock case needed by the current BUY retry should be enabled. Additional product types should remain blocked or review-required until explicitly designed.

## Request Artifact / Audit Design

Before broker submission, the redacted submit artifact should record:

```text
internal_code=92560
broker_issue_code=9256
code_normalization_rule=JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR
code_normalization_status=PASS
market=グロース
broker_market_code=00
product_category=011
raw_request_saved=false
raw_response_saved=false
secret_saved=false
```

The artifact must not save:

```text
raw request
raw response
secret
session token
account id
plaintext broker order id
```

If normalization fails, the submit path should not call `CLMKabuNewOrder`. It should emit a fail-closed artifact such as:

```text
submit_status=BLOCK
block_reason=BROKER_ISSUE_CODE_NORMALIZATION_FAILED
```

## Phase12-Y Minimal Tasks

1. Add a broker issue-code normalizer with listed-info-aware fail-closed behavior.
2. Preserve `code` / `issue_code` as internal J-Quants code in Order Plan and operations artifacts.
3. Add `broker_issue_code` only at the broker request boundary.
4. Wire `broker_issue_code=9256` into `CLMKabuNewOrder` `sIssueCode` for the current `92560` ordinary-stock case.
5. Record redacted normalization metadata in submit artifacts and operation audit.
6. Add unit tests for:
   - `92560 -> 9256`
   - `148A0 -> 148A` if alphanumeric ordinary-stock codes are supported
   - non-trailing-zero 5-character code fails closed
   - missing listed info fails closed
   - disallowed product category fails closed
   - encoded dummy request contains `sIssueCode=9256`
7. Keep read-only broker lookup optional and non-authoritative unless a stable issue master endpoint is confirmed.
8. Use a new `approval_id`, new `run_id`, and `retry_parent=Phase12-W` before any future Demo BUY retry.
9. Retry Demo BUY wire execution only after Phase12-Y implementation tests and preflight pass.

## Judgement

`92560 -> 9256` is the correct next design direction for the current BUY retry candidate because:

```text
92560 is confirmed as J-Quants / internal code
the security is ordinary stock-like with ProdCat=011
existing local display-code precedent removes trailing 0
Tachibana order examples use four-character sIssueCode values
the broker reject means the broker could not find 92560 in its issue master
```

This should be implemented narrowly and fail closed. It should not become a broad rule that blindly strips the last character from every code.

## Prohibited Actions Confirmation

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
```
