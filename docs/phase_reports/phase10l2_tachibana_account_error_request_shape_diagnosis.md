# Phase10-L2 Tachibana Account Error / Request Shape Diagnosis

- status: FAIL_CLOSED_WITH_PROTOCOL_ERROR_CLASSIFICATION
- created_at: 2026-06-27
- scope: account / balance error classification and request shape diagnosis only
- live_account_balance_diagnosis_run_count: 1
- environment: demo

## 1. Summary

Phase10-L2 investigated why `CLMZanKaiSummary` and `CLMZanKaiKanougaku` returned only protocol/error keys instead of business amount fields.

Result:

```text
live_account_balance_diagnosis=FAILED_READONLY
login=PASS
logout=PASS
account_api_called=true
balance_api_called=true
orders_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
paper_ledger_updated=false
paper_test2_ledger_initialized=false
```

The previous Phase10-L mapping fix remains valid, but the live response still did not include business amount fields. Phase10-L2 now treats this as fail-closed because both target responses contained non-zero protocol error classification.

The error body and error number value were not saved. Only safe classifications were persisted.

## 2. Official Request Shape Review

References checked:

- `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_compress_v4r9.js`
- `https://www.e-shiten.jp/e_api/mfds_json_api_request_post.js`

Confirmed request shapes:

```text
CLMZanKaiSummary:
  sCLMID=CLMZanKaiSummary

CLMZanKaiKanougaku:
  sCLMID=CLMZanKaiKanougaku
  sIssueCode=""
  sSizyouC=""
```

The current request builder sends these CLMIDs through the REQUEST URL, uses POST, includes `p_no` and `p_sd_date`, and applies the v4r9 codec. `CLMZanKaiKanougaku` includes the official compatibility fields `sIssueCode` and `sSizyouC`.

The official sample script does not make a separate content-type requirement explicit. The current transport sends JSON-compatible POST payloads with v4r9 encoded keys.

## 3. Implemented Diagnosis

Updated `src/ai_fund_lab_v2/broker/tachibana_account_smoke.py`:

- Added `classify_protocol_error`.
- Added `diagnose_account_request_shape`.
- Added `classify_account_balance_issue`.
- Changed account/balance smoke to fail closed when protocol error classification is present, even if `sResultCode` is empty.

Saved protocol/error classification only:

```text
p_errno_present
p_errno_numeric
p_errno_zero
p_errno_digit_length
p_err_present
p_err_empty
p_err_length_bucket
p_err_classification
protocol_error_present
```

Not saved:

```text
p_errno value
p_err body
raw response
auth id
private key
virtual URL
account/customer id plaintext
API response body
```

## 4. Live Diagnosis Result

Executed once:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_account_balance_smoke --run-demo-account-balance --report-filename phase10l2_tachibana_account_error_diagnosis_result.json --source phase10l2_account_error_request_shape_diagnosis
```

Result:

```text
status=FAILED_READONLY
executed=true
environment=demo
login=PASS
logout=PASS
account_api_called=true
balance_api_called=true
positions_api_called=false
orders_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
```

Both `CLMZanKaiSummary` and `CLMZanKaiKanougaku` had:

```text
p_errno_present=true
p_errno_numeric=true
p_errno_zero=false
p_errno_digit_length=1
p_err_present=true
p_err_empty=false
p_err_length_bucket=medium
p_err_classification=present_nonempty
protocol_error_present=true
```

The value of `p_errno` and the body of `p_err` were not persisted.

## 5. Request Shape Diagnosis

`CLMZanKaiSummary`:

```text
sclmid_supported=true
endpoint_type=request_url
http_method=POST
payload_compressed=true
p_no_present=true
p_sd_date_present=true
sIssueCode_present=false
sSizyouC_present=false
encoded_key_names=288,290,333
values_saved=false
```

`CLMZanKaiKanougaku`:

```text
sclmid_supported=true
endpoint_type=request_url
http_method=POST
payload_compressed=true
p_no_present=true
p_sd_date_present=true
sIssueCode_present=true
sSizyouC_present=true
encoded_key_names=288,290,333,473,731
values_saved=false
```

This does not currently support `REQUEST_SHAPE_MISSING_FIELD` as the primary cause.

## 6. Cause Classification

Current classification:

```text
primary=UNKNOWN_PROTOCOL_ERROR
candidates=UNKNOWN_PROTOCOL_ERROR, DEMO_API_LIMITATION, ACCOUNT_PERMISSION_OR_STATE
request_shape_missing=false
protocol_error_present=true
business_fields_present=false
```

Rejected or weakened candidates:

```text
REQUEST_SHAPE_MISSING_FIELD=false
SESSION_URL_TYPE_MISMATCH=not_supported_by_current_evidence
NORMALIZER_FIELD_MAPPING=not_primary_after_phase10l_mapping_fix
```

The remaining likely causes are a protocol/API-side error condition, demo account/API limitation, or account permission/state condition. The exact protocol error value is intentionally not available in the report because saving it was prohibited.

## 7. Paper Test 2 Initial Cash Re-judgement

The normalized account/balance values remain zero because business amount fields were absent:

```text
cash_available=0
buying_power=0
withdrawable_cash=0
margin_buying_power=0
ipo_buying_power=0
nisa_growth_capacity=0
```

This is not a confirmed zero-cash account state. Paper Test 2 initial cash remains:

```text
paper_test2_initial_cash_candidate_status=UNRESOLVED_ACCOUNT_API_PROTOCOL_ERROR
```

Do not initialize Paper Test 2 with 0 JPY from this account/balance API result.

## 8. Verification

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py -q
```

Result:

```text
87 passed
```

JSON validation:

```text
reports/phase_reports/phase10l2_tachibana_account_error_request_shape_diagnosis.json
reports/phase_reports/phase10l2_tachibana_account_error_diagnosis_result.json
```

Safety checks:

```text
secret canary: PASS
no forbidden CLMID audit: PASS
paper_ledger_updated=false
broker_snapshot_updated=false
```

## 9. Result

Phase10-L2 safely narrowed the account/balance discrepancy to a protocol/error response, not an immediate field-mapping gap or missing request-builder field.

Recommended next step:

```text
Phase10-L3 should compare the official browser sample POST behavior and current Python POST behavior at the transport boundary, especially content-type/body serialization and any account API precondition, while continuing to avoid raw p_err/p_errno persistence.
```
